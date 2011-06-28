"""
This module implements the main Evennia server process, the core of
the game engine. Don't import this module directly! If you need to
access the server processes from code, instead go via the session-
handler: src.sessionhandler.SESSIONS.server

This module should be started with the 'twistd' executable since it
sets up all the networking features.  (this is done automatically
by game/evennia.py).

"""
import time
import sys
import os
if os.name == 'nt':
    # For Windows batchfile we need an extra path insertion here.
    sys.path.insert(0, os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))))

from twisted.application import internet, service
from twisted.internet import protocol, reactor, defer
from twisted.web import server, static
from django.db import connection
from django.conf import settings
from src.utils import reloads
from src.server.models import ServerConfig
from src.server.sessionhandler import SESSIONS
from src.server import initial_setup

from src.utils.utils import get_evennia_version
from src.comms import channelhandler


#------------------------------------------------------------
# Evennia Server settings 
#------------------------------------------------------------

SERVERNAME = settings.SERVERNAME
VERSION = get_evennia_version()

TELNET_PORTS = settings.TELNET_PORTS
SSL_PORTS = settings.SSL_PORTS
SSH_PORTS = settings.SSH_PORTS
WEBSERVER_PORTS = settings.WEBSERVER_PORTS

TELNET_INTERFACES = settings.TELNET_INTERFACES
SSL_INTERFACES = settings.SSL_INTERFACES
SSH_INTERFACES = settings.SSH_INTERFACES
WEBSERVER_INTERFACES = settings.WEBSERVER_INTERFACES

TELNET_ENABLED = settings.TELNET_ENABLED and TELNET_PORTS and TELNET_INTERFACES
SSL_ENABLED = settings.SSL_ENABLED and SSL_PORTS and SSL_INTERFACES
SSH_ENABLED = settings.SSH_ENABLED and SSH_PORTS and SSH_INTERFACES
WEBSERVER_ENABLED = settings.WEBSERVER_ENABLED and WEBSERVER_PORTS and WEBSERVER_INTERFACES
WEBCLIENT_ENABLED = settings.WEBCLIENT_ENABLED 
IMC2_ENABLED = settings.IMC2_ENABLED
IRC_ENABLED = settings.IRC_ENABLED

#------------------------------------------------------------
# Evennia Main Server object 
#------------------------------------------------------------
class Evennia(object):

    """
    The main Evennia server handler. This object sets up the database and
    tracks and interlinks all the twisted network services that make up
    evennia.
    """    
    
    def __init__(self, application):
        """
        Setup the server. 

        application - an instantiated Twisted application

        """        
        sys.path.append('.')
        
        # create a store of services
        self.services = service.IServiceCollection(application)

        print '\n' + '-'*50

        # Database-specific startup optimizations.
        self.sqlite3_prep()
                    
        # Run the initial setup if needed 
        self.run_initial_setup()

        # we have to null this here.
        SESSIONS.session_count(0)            
        # we link ourself to the sessionhandler so other modules don't have to 
        # re-import the server module itself (which would re-initialize it).
        SESSIONS.server = self

        self.start_time = time.time()

        # initialize channelhandler
        channelhandler.CHANNELHANDLER.update()
        
        # init all global scripts
        reloads.reload_scripts(init_mode=True)

        # Make info output to the terminal.         
        self.terminal_output()

        print '-'*50        

        # set a callback if the server is killed abruptly, 
        # by Ctrl-C, reboot etc.
        reactor.addSystemEventTrigger('before', 'shutdown', self.shutdown, _abrupt=True)

        self.game_running = True
                
    # Server startup methods

    def sqlite3_prep(self):
        """
        Optimize some SQLite stuff at startup since we
        can't save it to the database.
        """
        if (settings.DATABASE_ENGINE == "sqlite3"
            or hasattr(settings, 'DATABASE')   
            and settings.DATABASE.get('ENGINE', None) 
                == 'django.db.backends.sqlite3'):            
            cursor = connection.cursor()
            cursor.execute("PRAGMA cache_size=10000")
            cursor.execute("PRAGMA synchronous=OFF")
            cursor.execute("PRAGMA count_changes=OFF")
            cursor.execute("PRAGMA temp_store=2")

    def run_initial_setup(self):
        """
        This attempts to run the initial_setup script of the server.
        It returns if this is not the first time the server starts.
        """
        last_initial_setup_step = ServerConfig.objects.conf('last_initial_setup_step')
        if not last_initial_setup_step:
            # None is only returned if the config does not exist,
            # i.e. this is an empty DB that needs populating.
            print ' Server started for the first time. Setting defaults.'
            initial_setup.handle_setup(0)
            print '-'*50
        elif int(last_initial_setup_step) >= 0:
            # a positive value means the setup crashed on one of its
            # modules and setup will resume from this step, retrying
            # the last failed module. When all are finished, the step
            # is set to -1 to show it does not need to be run again.
            print ' Resuming initial setup from step %s.' % \
                last_initial_setup_step  
            initial_setup.handle_setup(int(last_initial_setup_step))
            print '-'*50

    def terminal_output(self):
        """
        Outputs server startup info to the terminal.
        """
        print ' %s (%s) started on port(s):' % (SERVERNAME, VERSION)        
        if TELNET_ENABLED:            
            ports = ", ".join([str(port) for port in TELNET_PORTS])
            ifaces = ",".join([" %s" % iface for iface in TELNET_INTERFACES if iface != '0.0.0.0'])
            print "  telnet%s: %s" % (ifaces, ports)
        if SSH_ENABLED:
            ports = ", ".join([str(port) for port in SSH_PORTS])
            ifaces = ",".join([" %s" % iface for iface in SSH_INTERFACES if iface != '0.0.0.0'])
            print "  ssh%s: %s" % (ifaces, ports)
        if SSL_ENABLED:
            ports = ", ".join([str(port) for port in SSL_PORTS])
            ifaces = ",".join([" %s" % iface for iface in SSL_INTERFACES if iface != '0.0.0.0'])
            print "  ssl%s: %s" % (ifaces, ports)
        if WEBSERVER_ENABLED:
            clientstring = ""
            if WEBCLIENT_ENABLED:
                clientstring = '/client'
            ports = ", ".join([str(port) for port in WEBSERVER_PORTS])
            ifaces = ",".join([" %s" % iface for iface in WEBSERVER_INTERFACES if iface != '0.0.0.0'])
            print "  webserver%s%s: %s" % (clientstring, ifaces, ports)

    def shutdown(self, message="{rThe server has been shutdown. Disconnecting.{n", _abrupt=False):
        """
        If called directly, this disconnects everyone cleanly and shuts down the
        reactor. If the server is killed by other means (Ctrl-C, reboot etc), this
        might be called as a callback, at which point the reactor is already dead
        and should not be tried to stop again (_abrupt=True).

        message - message to send to all connected sessions
        _abrupt - only to be used by internal callback_mechanism.
        """
        SESSIONS.disconnect_all_sessions(reason=message)
        if not _abrupt:
            reactor.callLater(0, reactor.stop)


#------------------------------------------------------------
#
# Start the Evennia game server and add all active services
#
#------------------------------------------------------------

# Tell the system the server is starting up; some things are not available yet
ServerConfig.objects.conf("server_starting_mode", True) 

# twistd requires us to define the variable 'application' so it knows
# what to execute from.
application = service.Application('Evennia')

# The main evennia server program. This sets up the database 
# and is where we store all the other services.
EVENNIA = Evennia(application)

# We group all the various services under the same twisted app.
# These will gradually be started as they are initialized below. 

if TELNET_ENABLED:

    # Start telnet game connections

    from src.server import telnet

    for interface in TELNET_INTERFACES:
        ifacestr = ""
        if interface != '0.0.0.0' or len(TELNET_INTERFACES) > 1:
            ifacestr = "-%s" % interface
        for port in TELNET_PORTS:        
            pstring = "%s:%s" % (ifacestr, port)
            factory = protocol.ServerFactory()
            factory.protocol = telnet.TelnetProtocol
            telnet_service = internet.TCPServer(port, factory, interface=interface)
            telnet_service.setName('EvenniaTelnet%s' % pstring)
            EVENNIA.services.addService(telnet_service)

if SSL_ENABLED:

    # Start SSL game connection (requires PyOpenSSL).

    from src.server import ssl

    for interface in SSL_INTERFACES:
        ifacestr = ""
        if interface != '0.0.0.0' or len(SSL_INTERFACES) > 1:
            ifacestr = "-%s" % interface
        for port in SSL_PORTS: 
            pstring = "%s:%s" % (ifacestr, port)
            factory = protocol.ServerFactory()
            factory.protocol = ssl.SSLProtocol
            ssl_service = internet.SSLServer(port, factory, ssl.getSSLContext(), interface=interface)
            ssl_service.setName('EvenniaSSL%s' % pstring)
            EVENNIA.services.addService(ssl_service)

if SSH_ENABLED:

    # Start SSH game connections. Will create a keypair in evennia/game if necessary.
    
    from src.server import ssh

    for interface in SSH_INTERFACES:
        ifacestr = ""
        if interface != '0.0.0.0' or len(SSH_INTERFACES) > 1:
            ifacestr = "-%s" % interface
        for port in SSH_PORTS:
            pstring = "%s:%s" % (ifacestr, port)
            factory = ssh.makeFactory({'protocolFactory':ssh.SshProtocol,
                                       'protocolArgs':()})        
            ssh_service = internet.TCPServer(port, factory, interface=interface)
            ssh_service.setName('EvenniaSSH%s' % pstring)
            EVENNIA.services.addService(ssh_service)

if WEBSERVER_ENABLED:

    # Start a django-compatible webserver.

    from twisted.python import threadpool
    from src.server.webserver import DjangoWebRoot, WSGIWebServer

    # start a thread pool and define the root url (/) as a wsgi resource 
    # recognized by Django
    threads = threadpool.ThreadPool()
    web_root = DjangoWebRoot(threads)
    # point our media resources to url /media 
    web_root.putChild("media", static.File(settings.MEDIA_ROOT))    

    if WEBCLIENT_ENABLED:    
        # create ajax client processes at /webclientdata
        from src.server.webclient import WebClient
        web_root.putChild("webclientdata", WebClient())

    web_site = server.Site(web_root, logPath=settings.HTTP_LOG_FILE)

    for interface in WEBSERVER_INTERFACES:
        ifacestr = ""
        if interface != '0.0.0.0' or len(WEBSERVER_INTERFACES) > 1:
            ifacestr = "-%s" % interface
        for port in WEBSERVER_PORTS:
            pstring = "%s:%s" % (ifacestr, port)
            # create the webserver
            webserver = WSGIWebServer(threads, port, web_site, interface=interface)
            webserver.setName('EvenniaWebServer%s' % pstring)
            EVENNIA.services.addService(webserver)

if IRC_ENABLED:

    # IRC channel connections

    from src.comms import irc 
    irc.connect_all()

if IMC2_ENABLED:

    # IMC2 channel connections

    from src.comms import imc2
    imc2.connect_all()

# clear server startup mode
ServerConfig.objects.conf("server_starting_mode", delete=True)
