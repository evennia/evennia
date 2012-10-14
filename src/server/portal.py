"""
This module implements the main Evennia server process, the core of
the game engine.

This module should be started with the 'twistd' executable since it
sets up all the networking features.  (this is done automatically
by game/evennia.py).

"""
import sys
import os
if os.name == 'nt':
    # For Windows batchfile we need an extra path insertion here.
    sys.path.insert(0, os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))))

from twisted.application import internet, service
from twisted.internet import protocol, reactor
from twisted.web import server, static
from django.conf import settings
from src.utils.utils import get_evennia_version, mod_import, make_iter
from src.server.sessionhandler import PORTAL_SESSIONS

PORTAL_SERVICES_PLUGIN_MODULES = [mod_import(module) for module in make_iter(settings.PORTAL_SERVICES_PLUGIN_MODULES)]

if os.name == 'nt':
    # For Windows we need to handle pid files manually.
    PORTAL_PIDFILE = os.path.join(settings.GAME_DIR, 'portal.pid')

#------------------------------------------------------------
# Evennia Portal settings
#------------------------------------------------------------

VERSION = get_evennia_version()

SERVERNAME = settings.SERVERNAME

PORTAL_RESTART = os.path.join(settings.GAME_DIR, 'portal.restart')

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

AMP_HOST = settings.AMP_HOST
AMP_PORT = settings.AMP_PORT
AMP_ENABLED = AMP_HOST and AMP_PORT


#------------------------------------------------------------
# Portal Service object
#------------------------------------------------------------
class Portal(object):

    """
    The main Portal server handler. This object sets up the database and
    tracks and interlinks all the twisted network services that make up
    Portal.
    """

    def __init__(self, application):
        """
        Setup the server.

        application - an instantiated Twisted application

        """
        sys.path.append('.')

        # create a store of services
        self.services = service.IServiceCollection(application)
        self.amp_protocol = None # set by amp factory
        self.sessions = PORTAL_SESSIONS
        self.sessions.portal = self

        # set a callback if the server is killed abruptly,
        # by Ctrl-C, reboot etc.
        reactor.addSystemEventTrigger('before', 'shutdown', self.shutdown, _reactor_stopping=True)

        self.game_running = False

    def set_restart_mode(self, mode=None):
        """
        This manages the flag file that tells the runner if the server should
        be restarted or is shutting down. Valid modes are True/False and None.
        If mode is None, no change will be done to the flag file.
        """
        if mode == None:
            return
        f = open(PORTAL_RESTART, 'w')
        print "writing mode=%(mode)s to %(portal_restart)s" % {'mode': mode, 'portal_restart': PORTAL_RESTART}
        f.write(str(mode))
        f.close()

    def shutdown(self, restart=None, _reactor_stopping=False):
        """
        Shuts down the server from inside it.

        restart - True/False sets the flags so the server will be
                  restarted or not. If None, the current flag setting
                  (set at initialization or previous runs) is used.
        _reactor_stopping - this is set if server is already in the process of
                  shutting down; in this case we don't need to stop it again.

        Note that restarting (regardless of the setting) will not work
        if the Portal is currently running in daemon mode. In that
        case it always needs to be restarted manually.
        """
        if _reactor_stopping and hasattr(self, "shutdown_complete"):
            # we get here due to us calling reactor.stop below. No need
            # to do the shutdown procedure again.
            return
        self.set_restart_mode(restart)
        if os.name == 'nt' and os.path.exists(PORTAL_PIDFILE):
            # for Windows we need to remove pid files manually
            os.remove(PORTAL_PIDFILE)
        if not _reactor_stopping:
            # shutting down the reactor will trigger another signal. We set
            # a flag to avoid loops.
            self.shutdown_complete = True
            reactor.callLater(0, reactor.stop)

#------------------------------------------------------------
#
# Start the Portal proxy server and add all active services
#
#------------------------------------------------------------

# twistd requires us to define the variable 'application' so it knows
# what to execute from.
application = service.Application('Portal')

# The main Portal server program. This sets up the database
# and is where we store all the other services.
PORTAL = Portal(application)

print '-' * 50
print ' %(servername)s Portal (%(version)s) started.' % {'servername': SERVERNAME, 'version': VERSION}

if AMP_ENABLED:

    # The AMP protocol handles the communication between
    # the portal and the mud server. Only reason to ever deactivate
    # it would be during testing and debugging.

    from src.server import amp

    factory = amp.AmpClientFactory(PORTAL)
    amp_client = internet.TCPClient(AMP_HOST, AMP_PORT, factory)
    amp_client.setName('evennia_amp')
    PORTAL.services.addService(amp_client)

# We group all the various services under the same twisted app.
# These will gradually be started as they are initialized below.

if TELNET_ENABLED:

    # Start telnet game connections

    from src.server import telnet

    for interface in TELNET_INTERFACES:
        if ":" in interface:
            print "  iPv6 interfaces not yet supported"
            continue
        ifacestr = ""
        if interface != '0.0.0.0' or len(TELNET_INTERFACES) > 1:
            ifacestr = "-%s" % interface
        for port in TELNET_PORTS:
            pstring = "%s:%s" % (ifacestr, port)
            factory = protocol.ServerFactory()
            factory.protocol = telnet.TelnetProtocol
            factory.sessionhandler = PORTAL_SESSIONS
            telnet_service = internet.TCPServer(port, factory, interface=interface)
            telnet_service.setName('EvenniaTelnet%s' % pstring)
            PORTAL.services.addService(telnet_service)

            print '  telnet%s: %s' % (ifacestr, port)

if SSL_ENABLED:

    # Start SSL game connection (requires PyOpenSSL).

    from src.server import ssl

    for interface in SSL_INTERFACES:
        if ":" in interface:
            print "  iPv6 interfaces not yet supported"
            continue
        ifacestr = ""
        if interface != '0.0.0.0' or len(SSL_INTERFACES) > 1:
            ifacestr = "-%s" % interface
        for port in SSL_PORTS:
            pstring = "%s:%s" % (ifacestr, port)
            factory = protocol.ServerFactory()
            factory.sessionhandler = PORTAL_SESSIONS
            factory.protocol = ssl.SSLProtocol
            ssl_service = internet.SSLServer(port, factory, ssl.getSSLContext(), interface=interface)
            ssl_service.setName('EvenniaSSL%s' % pstring)
            PORTAL.services.addService(ssl_service)

            print "  ssl%s: %s" % (ifacestr, port)



if SSH_ENABLED:

    # Start SSH game connections. Will create a keypair in evennia/game if necessary.

    from src.server import ssh

    for interface in SSH_INTERFACES:
        if ":" in interface:
            print "  iPv6 interfaces not yet supported"
            continue
        ifacestr = ""
        if interface != '0.0.0.0' or len(SSH_INTERFACES) > 1:
            ifacestr = "-%s" % interface
        for port in SSH_PORTS:
            pstring = "%s:%s" % (ifacestr, port)
            factory = ssh.makeFactory({'protocolFactory':ssh.SshProtocol,
                                       'protocolArgs':(),
                                       'sessions':PORTAL_SESSIONS})
            ssh_service = internet.TCPServer(port, factory, interface=interface)
            ssh_service.setName('EvenniaSSH%s' % pstring)
            PORTAL.services.addService(ssh_service)

            print "  ssl%s: %s" % (ifacestr, port)

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

    webclientstr = ""
    if WEBCLIENT_ENABLED:
        # create ajax client processes at /webclientdata
        from src.server.webclient import WebClient
        webclient = WebClient()
        webclient.sessionhandler = PORTAL_SESSIONS
        web_root.putChild("webclientdata", webclient)

        webclientstr = "/client"

    web_site = server.Site(web_root, logPath=settings.HTTP_LOG_FILE)

    for interface in WEBSERVER_INTERFACES:
        if ":" in interface:
            print "  iPv6 interfaces not yet supported"
            continue
        ifacestr = ""
        if interface != '0.0.0.0' or len(WEBSERVER_INTERFACES) > 1:
            ifacestr = "-%s" % interface
        for port in WEBSERVER_PORTS:
            pstring = "%s:%s" % (ifacestr, port)
            # create the webserver
            webserver = WSGIWebServer(threads, port, web_site, interface=interface)
            webserver.setName('EvenniaWebServer%s' % pstring)
            PORTAL.services.addService(webserver)

            print "  webserver%s%s: %s" % (webclientstr, ifacestr, port)

for plugin_module in PORTAL_SERVICES_PLUGIN_MODULES:
    # external plugin services to start
    plugin_module.start_plugin_services(PORTAL)

print '-' * 50 # end of terminal output


if os.name == 'nt':
    # Windows only: Set PID file manually
    f = open(os.path.join(settings.GAME_DIR, 'portal.pid'), 'w')
    f.write(str(os.getpid()))
    f.close()
