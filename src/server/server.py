"""
This module implements the main Evennia server process, the core of
the game engine. Only import this once! 

This module should be started with the 'twistd' executable since it
sets up all the networking features.  (this is done by
game/evennia.py).

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
from twisted.python import threadpool
from django.db import connection
from django.conf import settings
from src.utils import reloads
from src.config.models import ConfigValue
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
WEBSERVER_PORTS = settings.WEBSERVER_PORTS

TELNET_ENABLED = settings.TELNET_ENABLED and TELNET_PORTS
WEBSERVER_ENABLED = settings.WEBSERVER_ENABLED and WEBSERVER_PORTS
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
        reactor.addSystemEventTrigger('before', 'shutdown',self.shutdown, _abrupt=True)

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
        last_initial_setup_step = ConfigValue.objects.conf('last_initial_setup_step')
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
            print "  telnet: " + ", ".join([str(port) for port in TELNET_PORTS])        
        if WEBSERVER_ENABLED:
            clientstring = ""
            if WEBCLIENT_ENABLED:
                clientstring = '/client'
            print "  webserver%s: " % clientstring + ", ".join([str(port) for port in WEBSERVER_PORTS])

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

# twistd requires us to define the variable 'application' so it knows
# what to execute from.
application = service.Application('Evennia')

# The main evennia server program. This sets up the database 
# and is where we store all the other services.
EVENNIA = Evennia(application)

# We group all the various services under the same twisted app.
# These will gradually be started as they are initialized below. 

if TELNET_ENABLED:

    # start telnet game connections

    from src.server import telnet

    for port in TELNET_PORTS:
        factory = protocol.ServerFactory()
        factory.protocol = telnet.TelnetProtocol
        telnet_service = internet.TCPServer(port, factory)
        telnet_service.setName('Evennia%s' % port)
        EVENNIA.services.addService(telnet_service)

if WEBSERVER_ENABLED:

    # a django-compatible webserver.

    from src.server.webserver import DjangoWebRoot, WSGIWebServer#DjangoWebRoot

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
    for port in WEBSERVER_PORTS:
        # create the webserver
        webserver = WSGIWebServer(threads, port, web_site)
        #webserver = internet.TCPServer(port, web_site)
        #webserver = internet.SSLServer(port, web_site)
        webserver.setName('EvenniaWebServer%s' % port)
        EVENNIA.services.addService(webserver)


if IMC2_ENABLED:

    # IMC2 channel connections

    from src.imc2.connection import IMC2ClientFactory
    from src.imc2 import events as imc2_events
    imc2_factory = IMC2ClientFactory()
    svc = internet.TCPClient(settings.IMC2_SERVER_ADDRESS, 
                             settings.IMC2_SERVER_PORT, 
                             imc2_factory)
    svc.setName('IMC2')
    EVENNIA.services.addService(svc)
    imc2_events.add_events()

if IRC_ENABLED:

    # IRC channel connections

    from src.irc.connection import IRC_BotFactory
    irc = internet.TCPClient(settings.IRC_NETWORK, 
                             settings.IRC_PORT, 
                             IRC_BotFactory(settings.IRC_CHANNEL,
                                            settings.IRC_NETWORK,
                                            settings.IRC_NICKNAME))            
    irc.setName("%s:%s" % ("IRC", settings.IRC_CHANNEL))
    EVENNIA.services.addService(irc)
