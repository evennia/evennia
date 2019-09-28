"""
This module implements the main Evennia server process, the core of
the game engine.

This module should be started with the 'twistd' executable since it
sets up all the networking features.  (this is done automatically
by game/evennia.py).

"""
import sys
import os
import time

from os.path import dirname, abspath
from twisted.application import internet, service
from twisted.internet import protocol, reactor
from twisted.python.log import ILogObserver

import django

django.setup()
from django.conf import settings

import evennia

evennia._init()

from evennia.utils.utils import get_evennia_version, mod_import, make_iter
from evennia.server.portal.portalsessionhandler import PORTAL_SESSIONS
from evennia.utils import logger
from evennia.server.webserver import EvenniaReverseProxyResource
from django.db import connection


# we don't need a connection to the database so close it right away
try:
    connection.close()
except Exception:
    pass

PORTAL_SERVICES_PLUGIN_MODULES = [
    mod_import(module) for module in make_iter(settings.PORTAL_SERVICES_PLUGIN_MODULES)
]
LOCKDOWN_MODE = settings.LOCKDOWN_MODE

# -------------------------------------------------------------
# Evennia Portal settings
# -------------------------------------------------------------

VERSION = get_evennia_version()

SERVERNAME = settings.SERVERNAME

PORTAL_RESTART = os.path.join(settings.GAME_DIR, "server", "portal.restart")

TELNET_PORTS = settings.TELNET_PORTS
SSL_PORTS = settings.SSL_PORTS
SSH_PORTS = settings.SSH_PORTS
WEBSERVER_PORTS = settings.WEBSERVER_PORTS
WEBSOCKET_CLIENT_PORT = settings.WEBSOCKET_CLIENT_PORT

TELNET_INTERFACES = ["127.0.0.1"] if LOCKDOWN_MODE else settings.TELNET_INTERFACES
SSL_INTERFACES = ["127.0.0.1"] if LOCKDOWN_MODE else settings.SSL_INTERFACES
SSH_INTERFACES = ["127.0.0.1"] if LOCKDOWN_MODE else settings.SSH_INTERFACES
WEBSERVER_INTERFACES = ["127.0.0.1"] if LOCKDOWN_MODE else settings.WEBSERVER_INTERFACES
WEBSOCKET_CLIENT_INTERFACE = "127.0.0.1" if LOCKDOWN_MODE else settings.WEBSOCKET_CLIENT_INTERFACE
WEBSOCKET_CLIENT_URL = settings.WEBSOCKET_CLIENT_URL

TELNET_ENABLED = settings.TELNET_ENABLED and TELNET_PORTS and TELNET_INTERFACES
SSL_ENABLED = settings.SSL_ENABLED and SSL_PORTS and SSL_INTERFACES
SSH_ENABLED = settings.SSH_ENABLED and SSH_PORTS and SSH_INTERFACES
WEBSERVER_ENABLED = settings.WEBSERVER_ENABLED and WEBSERVER_PORTS and WEBSERVER_INTERFACES
WEBCLIENT_ENABLED = settings.WEBCLIENT_ENABLED
WEBSOCKET_CLIENT_ENABLED = (
    settings.WEBSOCKET_CLIENT_ENABLED and WEBSOCKET_CLIENT_PORT and WEBSOCKET_CLIENT_INTERFACE
)

AMP_HOST = settings.AMP_HOST
AMP_PORT = settings.AMP_PORT
AMP_INTERFACE = settings.AMP_INTERFACE
AMP_ENABLED = AMP_HOST and AMP_PORT and AMP_INTERFACE

INFO_DICT = {
    "servername": SERVERNAME,
    "version": VERSION,
    "errors": "",
    "info": "",
    "lockdown_mode": "",
    "amp": "",
    "telnet": [],
    "telnet_ssl": [],
    "ssh": [],
    "webclient": [],
    "webserver_proxy": [],
    "webserver_internal": [],
}

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
        sys.path.append(".")

        # create a store of services
        self.services = service.MultiService()
        self.services.setServiceParent(application)
        self.amp_protocol = None  # set by amp factory
        self.sessions = PORTAL_SESSIONS
        self.sessions.portal = self
        self.process_id = os.getpid()

        self.server_process_id = None
        self.server_restart_mode = "shutdown"
        self.server_info_dict = {}

        self.start_time = time.time()

        # in non-interactive portal mode, this gets overwritten by
        # cmdline sent by the evennia launcher
        self.server_twistd_cmd = self._get_backup_server_twistd_cmd()

        # set a callback if the server is killed abruptly,
        # by Ctrl-C, reboot etc.
        reactor.addSystemEventTrigger(
            "before", "shutdown", self.shutdown, _reactor_stopping=True, _stop_server=True
        )

    def _get_backup_server_twistd_cmd(self):
        """
        For interactive Portal mode there is no way to get the server cmdline from the launcher, so
        we need to guess it here (it's very likely to not change)

        Returns:
            server_twistd_cmd (list): An instruction for starting the server, to pass to Popen.
        """
        server_twistd_cmd = [
            "twistd",
            "--python={}".format(os.path.join(dirname(dirname(abspath(__file__))), "server.py")),
        ]
        if os.name != "nt":
            gamedir = os.getcwd()
            server_twistd_cmd.append(
                "--pidfile={}".format(os.path.join(gamedir, "server", "server.pid"))
            )
        return server_twistd_cmd

    def get_info_dict(self):
        "Return the Portal info, for display."
        return INFO_DICT

    def shutdown(self, _reactor_stopping=False, _stop_server=False):
        """
        Shuts down the server from inside it.

        Args:
            _reactor_stopping (bool, optional): This is set if server
                is already in the process of shutting down; in this case
                we don't need to stop it again.
            _stop_server (bool, optional): Only used in portal-interactive mode;
                makes sure to stop the Server cleanly.

        Note that restarting (regardless of the setting) will not work
        if the Portal is currently running in daemon mode. In that
        case it always needs to be restarted manually.

        """
        if _reactor_stopping and hasattr(self, "shutdown_complete"):
            # we get here due to us calling reactor.stop below. No need
            # to do the shutdown procedure again.
            return

        self.sessions.disconnect_all()
        if _stop_server:
            self.amp_protocol.stop_server(mode="shutdown")

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
application = service.Application("Portal")

# custom logging

if "--nodaemon" not in sys.argv:
    logfile = logger.WeeklyLogFile(
        os.path.basename(settings.PORTAL_LOG_FILE), os.path.dirname(settings.PORTAL_LOG_FILE)
    )
    application.setComponent(ILogObserver, logger.PortalLogObserver(logfile).emit)

# The main Portal server program. This sets up the database
# and is where we store all the other services.
PORTAL = Portal(application)

if LOCKDOWN_MODE:

    INFO_DICT["lockdown_mode"] = "  LOCKDOWN_MODE active: Only local connections."

if AMP_ENABLED:

    # The AMP protocol handles the communication between
    # the portal and the mud server. Only reason to ever deactivate
    # it would be during testing and debugging.

    from evennia.server.portal import amp_server

    INFO_DICT["amp"] = "amp: %s" % AMP_PORT

    factory = amp_server.AMPServerFactory(PORTAL)
    amp_service = internet.TCPServer(AMP_PORT, factory, interface=AMP_INTERFACE)
    amp_service.setName("PortalAMPServer")
    PORTAL.services.addService(amp_service)


# We group all the various services under the same twisted app.
# These will gradually be started as they are initialized below.

if TELNET_ENABLED:

    # Start telnet game connections

    from evennia.server.portal import telnet

    for interface in TELNET_INTERFACES:
        ifacestr = ""
        if interface not in ("0.0.0.0", "::") or len(TELNET_INTERFACES) > 1:
            ifacestr = "-%s" % interface
        for port in TELNET_PORTS:
            pstring = "%s:%s" % (ifacestr, port)
            factory = telnet.TelnetServerFactory()
            factory.noisy = False
            factory.protocol = telnet.TelnetProtocol
            factory.sessionhandler = PORTAL_SESSIONS
            telnet_service = internet.TCPServer(port, factory, interface=interface)
            telnet_service.setName("EvenniaTelnet%s" % pstring)
            PORTAL.services.addService(telnet_service)

            INFO_DICT["telnet"].append("telnet%s: %s" % (ifacestr, port))


if SSL_ENABLED:

    # Start Telnet+SSL game connection (requires PyOpenSSL).

    from evennia.server.portal import telnet_ssl

    for interface in SSL_INTERFACES:
        ifacestr = ""
        if interface not in ("0.0.0.0", "::") or len(SSL_INTERFACES) > 1:
            ifacestr = "-%s" % interface
        for port in SSL_PORTS:
            pstring = "%s:%s" % (ifacestr, port)
            factory = protocol.ServerFactory()
            factory.noisy = False
            factory.sessionhandler = PORTAL_SESSIONS
            factory.protocol = telnet_ssl.SSLProtocol

            ssl_context = telnet_ssl.getSSLContext()
            if ssl_context:
                ssl_service = internet.SSLServer(
                    port, factory, telnet_ssl.getSSLContext(), interface=interface
                )
                ssl_service.setName("EvenniaSSL%s" % pstring)
                PORTAL.services.addService(ssl_service)

                INFO_DICT["telnet_ssl"].append("telnet+ssl%s: %s" % (ifacestr, port))
            else:
                INFO_DICT["telnet_ssl"].append(
                    "telnet+ssl%s: %s (deactivated - keys/cert unset)" % (ifacestr, port)
                )


if SSH_ENABLED:

    # Start SSH game connections. Will create a keypair in
    # evennia/game if necessary.

    from evennia.server.portal import ssh

    for interface in SSH_INTERFACES:
        ifacestr = ""
        if interface not in ("0.0.0.0", "::") or len(SSH_INTERFACES) > 1:
            ifacestr = "-%s" % interface
        for port in SSH_PORTS:
            pstring = "%s:%s" % (ifacestr, port)
            factory = ssh.makeFactory(
                {
                    "protocolFactory": ssh.SshProtocol,
                    "protocolArgs": (),
                    "sessions": PORTAL_SESSIONS,
                }
            )
            factory.noisy = False
            ssh_service = internet.TCPServer(port, factory, interface=interface)
            ssh_service.setName("EvenniaSSH%s" % pstring)
            PORTAL.services.addService(ssh_service)

            INFO_DICT["ssh"].append("ssh%s: %s" % (ifacestr, port))


if WEBSERVER_ENABLED:
    from evennia.server.webserver import Website

    # Start a reverse proxy to relay data to the Server-side webserver

    websocket_started = False
    for interface in WEBSERVER_INTERFACES:
        ifacestr = ""
        if interface not in ("0.0.0.0", "::") or len(WEBSERVER_INTERFACES) > 1:
            ifacestr = "-%s" % interface
        for proxyport, serverport in WEBSERVER_PORTS:
            web_root = EvenniaReverseProxyResource("127.0.0.1", serverport, "")
            webclientstr = ""
            if WEBCLIENT_ENABLED:
                # create ajax client processes at /webclientdata
                from evennia.server.portal import webclient_ajax

                ajax_webclient = webclient_ajax.AjaxWebClient()
                ajax_webclient.sessionhandler = PORTAL_SESSIONS
                web_root.putChild(b"webclientdata", ajax_webclient)
                webclientstr = "webclient (ajax only)"

                if WEBSOCKET_CLIENT_ENABLED and not websocket_started:
                    # start websocket client port for the webclient
                    # we only support one websocket client
                    from evennia.server.portal import webclient
                    from autobahn.twisted.websocket import WebSocketServerFactory

                    w_interface = WEBSOCKET_CLIENT_INTERFACE
                    w_ifacestr = ""
                    if w_interface not in ("0.0.0.0", "::") or len(WEBSERVER_INTERFACES) > 1:
                        w_ifacestr = "-%s" % interface
                    port = WEBSOCKET_CLIENT_PORT

                    class Websocket(WebSocketServerFactory):
                        "Only here for better naming in logs"
                        pass

                    factory = Websocket()
                    factory.noisy = False
                    factory.protocol = webclient.WebSocketClient
                    factory.sessionhandler = PORTAL_SESSIONS
                    websocket_service = internet.TCPServer(port, factory, interface=w_interface)
                    websocket_service.setName("EvenniaWebSocket%s:%s" % (w_ifacestr, port))
                    PORTAL.services.addService(websocket_service)
                    websocket_started = True
                    webclientstr = "webclient-websocket%s: %s" % (w_ifacestr, port)
                INFO_DICT["webclient"].append(webclientstr)

            web_root = Website(web_root, logPath=settings.HTTP_LOG_FILE)
            web_root.is_portal = True
            proxy_service = internet.TCPServer(proxyport, web_root, interface=interface)
            proxy_service.setName("EvenniaWebProxy%s:%s" % (ifacestr, proxyport))
            PORTAL.services.addService(proxy_service)
            INFO_DICT["webserver_proxy"].append("webserver-proxy%s: %s" % (ifacestr, proxyport))
            INFO_DICT["webserver_internal"].append("webserver: %s" % serverport)


for plugin_module in PORTAL_SERVICES_PLUGIN_MODULES:
    # external plugin services to start
    plugin_module.start_plugin_services(PORTAL)
