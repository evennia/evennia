"""
This module implements the main Evennia server process, the core of
the game engine.

This module should be started with the 'twistd' executable since it
sets up all the networking features.  (this is done automatically
by game/evennia.py).

"""
from __future__ import print_function
from builtins import object

import time
import sys
import os

from twisted.application import internet, service
from twisted.internet import protocol, reactor
from twisted.internet.task import LoopingCall
from twisted.web import server
import django
django.setup()
from django.conf import settings

import evennia
evennia._init()

from evennia.utils.utils import get_evennia_version, mod_import, make_iter
from evennia.server.portal.portalsessionhandler import PORTAL_SESSIONS
from evennia.server.webserver import EvenniaReverseProxyResource

PORTAL_SERVICES_PLUGIN_MODULES = [mod_import(module) for module in make_iter(settings.PORTAL_SERVICES_PLUGIN_MODULES)]
LOCKDOWN_MODE = settings.LOCKDOWN_MODE

PORTAL_PIDFILE = ""
if os.name == 'nt':
    # For Windows we need to handle pid files manually.
    PORTAL_PIDFILE = os.path.join(settings.GAME_DIR, "server", 'portal.pid')

# -------------------------------------------------------------
# Evennia Portal settings
# -------------------------------------------------------------

VERSION = get_evennia_version()

SERVERNAME = settings.SERVERNAME

PORTAL_RESTART = os.path.join(settings.GAME_DIR, "server", 'portal.restart')

TELNET_PORTS = settings.TELNET_PORTS
SSL_PORTS = settings.SSL_PORTS
SSH_PORTS = settings.SSH_PORTS
WEBSERVER_PORTS = settings.WEBSERVER_PORTS
WEBSOCKET_CLIENT_PORT = settings.WEBSOCKET_CLIENT_PORT

TELNET_INTERFACES = ['127.0.0.1'] if LOCKDOWN_MODE else settings.TELNET_INTERFACES
SSL_INTERFACES = ['127.0.0.1'] if LOCKDOWN_MODE else settings.SSL_INTERFACES
SSH_INTERFACES = ['127.0.0.1'] if LOCKDOWN_MODE else settings.SSH_INTERFACES
WEBSERVER_INTERFACES = ['127.0.0.1'] if LOCKDOWN_MODE else settings.WEBSERVER_INTERFACES
WEBSOCKET_CLIENT_INTERFACE = '127.0.0.1' if LOCKDOWN_MODE else settings.WEBSOCKET_CLIENT_INTERFACE
WEBSOCKET_CLIENT_URL = settings.WEBSOCKET_CLIENT_URL

TELNET_ENABLED = settings.TELNET_ENABLED and TELNET_PORTS and TELNET_INTERFACES
SSL_ENABLED = settings.SSL_ENABLED and SSL_PORTS and SSL_INTERFACES
SSH_ENABLED = settings.SSH_ENABLED and SSH_PORTS and SSH_INTERFACES
WEBSERVER_ENABLED = settings.WEBSERVER_ENABLED and WEBSERVER_PORTS and WEBSERVER_INTERFACES
WEBCLIENT_ENABLED = settings.WEBCLIENT_ENABLED
WEBSOCKET_CLIENT_ENABLED = settings.WEBSOCKET_CLIENT_ENABLED and WEBSOCKET_CLIENT_PORT and WEBSOCKET_CLIENT_INTERFACE

AMP_HOST = settings.AMP_HOST
AMP_PORT = settings.AMP_PORT
AMP_INTERFACE = settings.AMP_INTERFACE
AMP_ENABLED = AMP_HOST and AMP_PORT and AMP_INTERFACE


# Maintenance function - this is called repeatedly by the portal.

_IDLE_TIMEOUT = settings.IDLE_TIMEOUT


def _portal_maintenance():
    """
    The maintenance function handles repeated checks and updates that
    the server needs to do. It is called every minute.

    """
    # check for idle sessions
    now = time.time()

    reason = "Idle timeout exceeded, disconnecting."
    for session in [sess for sess in PORTAL_SESSIONS.values()
                    if (now - sess.cmd_last) > _IDLE_TIMEOUT]:
        session.disconnect(reason=reason)
        PORTAL_SESSIONS.disconnect(session)

if _IDLE_TIMEOUT > 0:
    # only start the maintenance task if we care about idling.
    _maintenance_task = LoopingCall(_portal_maintenance)
    _maintenance_task.start(60)  # called every minute


# -------------------------------------------------------------
# Portal Service object
# -------------------------------------------------------------
class Portal(object):

    """
    The main Portal server handler. This object sets up the database
    and tracks and interlinks all the twisted network services that
    make up Portal.

    """

    def __init__(self, application):
        """
        Setup the server.

        Args:
            application (Application): An instantiated Twisted application

        """
        sys.path.append('.')

        # create a store of services
        self.services = service.IServiceCollection(application)
        self.amp_protocol = None  # set by amp factory
        self.sessions = PORTAL_SESSIONS
        self.sessions.portal = self

        # set a callback if the server is killed abruptly,
        # by Ctrl-C, reboot etc.
        reactor.addSystemEventTrigger('before', 'shutdown', self.shutdown, _reactor_stopping=True)

        self.game_running = False

    def set_restart_mode(self, mode=None):
        """
        This manages the flag file that tells the runner if the server
        should be restarted or is shutting down.

        Args:
            mode (bool or None): Valid modes are True/False and None.
                If mode is None, no change will be done to the flag file.

        """
        if mode is None:
            return
        with open(PORTAL_RESTART, 'w') as f:
            print("writing mode=%(mode)s to %(portal_restart)s" % {'mode': mode, 'portal_restart': PORTAL_RESTART})
            f.write(str(mode))

    def shutdown(self, restart=None, _reactor_stopping=False):
        """
        Shuts down the server from inside it.

        Args:
            restart (bool or None, optional): True/False sets the
                flags so the server will be restarted or not. If None, the
                current flag setting (set at initialization or previous
                runs) is used.
            _reactor_stopping (bool, optional): This is set if server
                is already in the process of shutting down; in this case
                we don't need to stop it again.

        Note that restarting (regardless of the setting) will not work
        if the Portal is currently running in daemon mode. In that
        case it always needs to be restarted manually.

        """
        if _reactor_stopping and hasattr(self, "shutdown_complete"):
            # we get here due to us calling reactor.stop below. No need
            # to do the shutdown procedure again.
            return
        self.sessions.disconnect_all()
        self.set_restart_mode(restart)
        if os.name == 'nt' and os.path.exists(PORTAL_PIDFILE):
            # for Windows we need to remove pid files manually
            os.remove(PORTAL_PIDFILE)
        if not _reactor_stopping:
            # shutting down the reactor will trigger another signal. We set
            # a flag to avoid loops.
            self.shutdown_complete = True
            reactor.callLater(0, reactor.stop)

# -------------------------------------------------------------
#
# Start the Portal proxy server and add all active services
#
# -------------------------------------------------------------

# twistd requires us to define the variable 'application' so it knows
# what to execute from.
application = service.Application('Portal')

# The main Portal server program. This sets up the database
# and is where we store all the other services.
PORTAL = Portal(application)

print('-' * 50)
print(' %(servername)s Portal (%(version)s) started.' % {'servername': SERVERNAME, 'version': VERSION})
if LOCKDOWN_MODE:
    print('  LOCKDOWN_MODE active: Only local connections.')

if AMP_ENABLED:

    # The AMP protocol handles the communication between
    # the portal and the mud server. Only reason to ever deactivate
    # it would be during testing and debugging.

    from evennia.server import amp

    print('  amp (to Server): %s' % AMP_PORT)

    factory = amp.AmpClientFactory(PORTAL)
    amp_client = internet.TCPClient(AMP_HOST, AMP_PORT, factory)
    amp_client.setName('evennia_amp')
    PORTAL.services.addService(amp_client)


# We group all the various services under the same twisted app.
# These will gradually be started as they are initialized below.

if TELNET_ENABLED:

    # Start telnet game connections

    from evennia.server.portal import telnet

    for interface in TELNET_INTERFACES:
        ifacestr = ""
        if interface not in ('0.0.0.0', '::') or len(TELNET_INTERFACES) > 1:
            ifacestr = "-%s" % interface
        for port in TELNET_PORTS:
            pstring = "%s:%s" % (ifacestr, port)
            factory = protocol.ServerFactory()
            factory.noisy = False
            factory.protocol = telnet.TelnetProtocol
            factory.sessionhandler = PORTAL_SESSIONS
            telnet_service = internet.TCPServer(port, factory, interface=interface)
            telnet_service.setName('EvenniaTelnet%s' % pstring)
            PORTAL.services.addService(telnet_service)

            print('  telnet%s: %s' % (ifacestr, port))


if SSL_ENABLED:

    # Start SSL game connection (requires PyOpenSSL).

    from evennia.server.portal import ssl

    for interface in SSL_INTERFACES:
        ifacestr = ""
        if interface not in ('0.0.0.0', '::') or len(SSL_INTERFACES) > 1:
            ifacestr = "-%s" % interface
        for port in SSL_PORTS:
            pstring = "%s:%s" % (ifacestr, port)
            factory = protocol.ServerFactory()
            factory.noisy = False
            factory.sessionhandler = PORTAL_SESSIONS
            factory.protocol = ssl.SSLProtocol
            ssl_service = internet.SSLServer(port,
                                             factory,
                                             ssl.getSSLContext(),
                                             interface=interface)
            ssl_service.setName('EvenniaSSL%s' % pstring)
            PORTAL.services.addService(ssl_service)

            print("  ssl%s: %s" % (ifacestr, port))


if SSH_ENABLED:

    # Start SSH game connections. Will create a keypair in
    # evennia/game if necessary.

    from evennia.server.portal import ssh

    for interface in SSH_INTERFACES:
        ifacestr = ""
        if interface not in ('0.0.0.0', '::') or len(SSH_INTERFACES) > 1:
            ifacestr = "-%s" % interface
        for port in SSH_PORTS:
            pstring = "%s:%s" % (ifacestr, port)
            factory = ssh.makeFactory({'protocolFactory': ssh.SshProtocol,
                                       'protocolArgs': (),
                                       'sessions': PORTAL_SESSIONS})
            factory.noisy = False
            ssh_service = internet.TCPServer(port, factory, interface=interface)
            ssh_service.setName('EvenniaSSH%s' % pstring)
            PORTAL.services.addService(ssh_service)

            print("  ssh%s: %s" % (ifacestr, port))


if WEBSERVER_ENABLED:
    from evennia.server.webserver import Website

    # Start a reverse proxy to relay data to the Server-side webserver

    websocket_started = False
    for interface in WEBSERVER_INTERFACES:
        ifacestr = ""
        if interface not in ('0.0.0.0', '::') or len(WEBSERVER_INTERFACES) > 1:
            ifacestr = "-%s" % interface
        for proxyport, serverport in WEBSERVER_PORTS:
            pstring = "%s:%s<->%s" % (ifacestr, proxyport, serverport)
            web_root = EvenniaReverseProxyResource('127.0.0.1', serverport, '')
            webclientstr = ""
            if WEBCLIENT_ENABLED:
                # create ajax client processes at /webclientdata
                from evennia.server.portal import webclient_ajax

                webclient = webclient_ajax.WebClient()
                webclient.sessionhandler = PORTAL_SESSIONS
                web_root.putChild("webclientdata", webclient)
                webclientstr = "\n   + webclient (ajax only)"

                if WEBSOCKET_CLIENT_ENABLED and not websocket_started:
                    # start websocket client port for the webclient
                    # we only support one websocket client
                    from evennia.server.portal import webclient
                    from evennia.utils.txws import WebSocketFactory

                    interface = WEBSOCKET_CLIENT_INTERFACE
                    port = WEBSOCKET_CLIENT_PORT
                    ifacestr = ""
                    if interface not in ('0.0.0.0', '::'):
                        ifacestr = "-%s" % interface
                    pstring = "%s:%s" % (ifacestr, port)
                    factory = protocol.ServerFactory()
                    factory.noisy = False
                    factory.protocol = webclient.WebSocketClient
                    factory.sessionhandler = PORTAL_SESSIONS
                    websocket_service = internet.TCPServer(port, WebSocketFactory(factory), interface=interface)
                    websocket_service.setName('EvenniaWebSocket%s' % pstring)
                    PORTAL.services.addService(websocket_service)
                    websocket_started = True
                    webclientstr = "\n   + webclient%s" % pstring

            web_root = Website(web_root, logPath=settings.HTTP_LOG_FILE)
            proxy_service = internet.TCPServer(proxyport,
                                               web_root,
                                               interface=interface)
            proxy_service.setName('EvenniaWebProxy%s' % pstring)
            PORTAL.services.addService(proxy_service)
            print("  webproxy%s:%s (<-> %s)%s" % (ifacestr, proxyport, serverport, webclientstr))


for plugin_module in PORTAL_SERVICES_PLUGIN_MODULES:
    # external plugin services to start
    plugin_module.start_plugin_services(PORTAL)

print('-' * 50)  # end of terminal output

if os.name == 'nt':
    # Windows only: Set PID file manually
    with open(PORTAL_PIDFILE, 'w') as f:
        f.write(str(os.getpid()))
