import os
import sys
import time
from os.path import abspath, dirname

from django.conf import settings
from django.db import connection
from twisted.application import internet, service
from twisted.application.service import MultiService
from twisted.internet import protocol, reactor
from twisted.internet.task import LoopingCall

import evennia
from evennia.utils.utils import (
    class_from_module,
    get_evennia_version,
    make_iter,
    mod_import,
)


class EvenniaPortalService(MultiService):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.amp_protocol = None
        self.server_process_id = None
        self.server_restart_mode = "shutdown"
        self.server_info_dict = dict()
        self.plugins = list()

        self.start_time = 0
        self._maintenance_count = 0
        self.maintenance_task = None

        self.info_dict = {
            "servername": settings.SERVERNAME,
            "version": get_evennia_version(),
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

        # in non-interactive portal mode, this gets overwritten by
        # cmdline sent by the evennia launcher
        self.server_twistd_cmd = self._get_backup_server_twistd_cmd()

    def portal_maintenance(self):
        """
        Repeated maintenance tasks for the portal.

        """

        self._maintenance_count += 1

        if self._maintenance_count % (60 * 7) == 0:
            # drop database connection every 7 hrs to avoid default timeouts on MySQL
            # (see https://github.com/evennia/evennia/issues/1376)
            connection.close()

    def privilegedStartService(self):
        self.start_time = time.time()
        self.maintenance_task = LoopingCall(self.portal_maintenance)
        self.maintenance_task.start(60, now=True)  # call every minute
        # set a callback if the server is killed abruptly,
        # by Ctrl-C, reboot etc.
        reactor.addSystemEventTrigger(
            "before", "shutdown", self.shutdown, _reactor_stopping=True, _stop_server=True
        )

        if settings.AMP_HOST and settings.AMP_PORT and settings.AMP_INTERFACE:
            self.register_amp()

        if settings.TELNET_ENABLED and settings.TELNET_PORTS and settings.TELNET_INTERFACES:
            self.register_telnet()

        if settings.SSL_ENABLED and settings.SSL_PORTS and settings.SSL_INTERFACES:
            self.register_ssl()

        if settings.SSH_ENABLED and settings.SSH_PORTS and settings.SSH_INTERFACES:
            self.register_ssh()

        if settings.WEBSERVER_ENABLED:
            self.register_webserver()

        if settings.LOCKDOWN_MODE:
            self.info_dict["lockdown_mode"] = "  LOCKDOWN_MODE active: Only local connections."

        self.register_plugins()

        super().privilegedStartService()

    def register_plugins(self):
        self.plugins.extend(
            mod_import(module) for module in make_iter(settings.PORTAL_SERVICES_PLUGIN_MODULES)
        )
        for plugin_module in self.plugins:
            # external plugin services to start
            if plugin_module:
                plugin_module.start_plugin_services(self)

    def check_lockdown(self, interfaces: list[str]):
        if settings.LOCKDOWN_MODE:
            return ["127.0.0.1"]
        return interfaces

    def register_ssl(self):
        # Start Telnet+SSL game connection (requires PyOpenSSL).

        from evennia.server.portal import telnet_ssl

        _ssl_protocol = class_from_module(settings.SSL_PROTOCOL_CLASS)

        interfaces = self.check_lockdown(settings.SSL_INTERFACES)

        for interface in interfaces:
            ifacestr = ""
            if interface not in ("0.0.0.0", "::") or len(interfaces) > 1:
                ifacestr = "-%s" % interface
            for port in settings.SSL_PORTS:
                pstring = "%s:%s" % (ifacestr, port)
                factory = protocol.ServerFactory()
                factory.noisy = False
                factory.sessionhandler = evennia.PORTAL_SESSION_HANDLER
                factory.protocol = _ssl_protocol

                ssl_context = telnet_ssl.getSSLContext()
                if ssl_context:
                    ssl_service = internet.SSLServer(
                        port, factory, telnet_ssl.getSSLContext(), interface=interface
                    )
                    ssl_service.setName("EvenniaSSL%s" % pstring)
                    ssl_service.setServiceParent(self)

                    self.info_dict["telnet_ssl"].append("telnet+ssl%s: %s" % (ifacestr, port))
                else:
                    self.info_dict["telnet_ssl"].append(
                        "telnet+ssl%s: %s (deactivated - keys/cert unset)" % (ifacestr, port)
                    )

    def register_ssh(self):
        # Start SSH game connections. Will create a keypair in
        # evennia/game if necessary.

        from evennia.server.portal import ssh

        _ssh_protocol = class_from_module(settings.SSH_PROTOCOL_CLASS)

        interfaces = self.check_lockdown(settings.SSH_INTERFACES)

        for interface in interfaces:
            ifacestr = ""
            if interface not in ("0.0.0.0", "::") or len(interfaces) > 1:
                ifacestr = "-%s" % interface
            for port in settings.SSH_PORTS:
                pstring = "%s:%s" % (ifacestr, port)
                factory = ssh.makeFactory(
                    {
                        "protocolFactory": _ssh_protocol,
                        "protocolArgs": (),
                        "sessions": evennia.PORTAL_SESSION_HANDLER,
                    }
                )
                factory.noisy = False
                ssh_service = internet.TCPServer(port, factory, interface=interface)
                ssh_service.setName("EvenniaSSH%s" % pstring)
                ssh_service.setServiceParent(self)

                self.info_dict["ssh"].append("ssh%s: %s" % (ifacestr, port))

    def register_webserver(self):
        from evennia.server.webserver import EvenniaReverseProxyResource, Website

        # Start a reverse proxy to relay data to the Server-side webserver
        interfaces = self.check_lockdown(settings.WEBSERVER_INTERFACES)
        websocket_started = False
        _websocket_protocol = class_from_module(settings.WEBSOCKET_PROTOCOL_CLASS)
        for interface in interfaces:
            ifacestr = ""
            if interface not in ("0.0.0.0", "::") or len(interfaces) > 1:
                ifacestr = "-%s" % interface

            for proxyport, serverport in settings.WEBSERVER_PORTS:
                web_root = EvenniaReverseProxyResource("127.0.0.1", serverport, "")
                webclientstr = ""
                if settings.WEBCLIENT_ENABLED:
                    # create ajax client processes at /webclientdata
                    ajax_class = class_from_module(settings.AJAX_CLIENT_CLASS)
                    ajax_webclient = ajax_class()
                    ajax_webclient.sessionhandler = evennia.PORTAL_SESSION_HANDLER
                    web_root.putChild(b"webclientdata", ajax_webclient)
                    webclientstr = "webclient (ajax only)"

                    if (
                        settings.WEBSOCKET_CLIENT_ENABLED
                        and settings.WEBSOCKET_CLIENT_PORT
                        and settings.WEBSOCKET_CLIENT_INTERFACE
                    ) and not websocket_started:
                        # start websocket client port for the webclient
                        # we only support one websocket client
                        from autobahn.twisted.websocket import WebSocketServerFactory

                        from evennia.server.portal import webclient  # noqa

                        w_interface = (
                            "127.0.0.1"
                            if settings.LOCKDOWN_MODE
                            else settings.WEBSOCKET_CLIENT_INTERFACE
                        )
                        w_ifacestr = ""
                        if (
                            w_interface not in ("0.0.0.0", "::")
                            or len(settings.WEBSERVER_INTERFACES) > 1
                        ):
                            w_ifacestr = "-%s" % w_interface
                        port = settings.WEBSOCKET_CLIENT_PORT

                        class Websocket(WebSocketServerFactory):
                            "Only here for better naming in logs"

                            pass

                        factory = Websocket()
                        factory.noisy = False
                        factory.protocol = _websocket_protocol
                        factory.sessionhandler = evennia.PORTAL_SESSION_HANDLER
                        websocket_service = internet.TCPServer(port, factory, interface=w_interface)
                        websocket_service.setName("EvenniaWebSocket%s:%s" % (w_ifacestr, port))
                        websocket_service.setServiceParent(self)
                        websocket_started = True
                        webclientstr = "webclient-websocket%s: %s" % (w_ifacestr, port)
                    self.info_dict["webclient"].append(webclientstr)

                try:
                    WEB_PLUGINS_MODULE = mod_import(settings.WEB_PLUGINS_MODULE)
                except ImportError:
                    WEB_PLUGINS_MODULE = None
                    self.info_dict["errors"] = (
                        "WARNING: settings.WEB_PLUGINS_MODULE not found - "
                        "copy 'evennia/game_template/server/conf/web_plugins.py to "
                        "mygame/server/conf."
                    )

                if WEB_PLUGINS_MODULE:
                    try:
                        web_root = WEB_PLUGINS_MODULE.at_webproxy_root_creation(web_root)
                    except Exception:
                        # Legacy user has not added an at_webproxy_root_creation function in existing
                        # web plugins file
                        self.info_dict["errors"] = (
                            "WARNING: WEB_PLUGINS_MODULE is enabled but at_webproxy_root_creation() "
                            "not found copy 'evennia/game_template/server/conf/web_plugins.py to "
                            "mygame/server/conf."
                        )
                web_root = Website(web_root, logPath=settings.HTTP_LOG_FILE)
                web_root.is_portal = True
                proxy_service = internet.TCPServer(proxyport, web_root, interface=interface)
                proxy_service.setName("EvenniaWebProxy%s:%s" % (ifacestr, proxyport))
                proxy_service.setServiceParent(self)
                self.info_dict["webserver_proxy"].append(
                    "webserver-proxy%s: %s" % (ifacestr, proxyport)
                )
                self.info_dict["webserver_internal"].append("webserver: %s" % serverport)

    def register_telnet(self):
        # Start telnet game connections

        from evennia.server.portal import telnet

        _telnet_protocol = class_from_module(settings.TELNET_PROTOCOL_CLASS)

        interfaces = self.check_lockdown(settings.TELNET_INTERFACES)

        for interface in interfaces:
            ifacestr = ""
            if interface not in ("0.0.0.0", "::") or len(interfaces) > 1:
                ifacestr = "-%s" % interface
            for port in settings.TELNET_PORTS:
                pstring = "%s:%s" % (ifacestr, port)
                factory = telnet.TelnetServerFactory()
                factory.noisy = False
                factory.protocol = _telnet_protocol
                factory.sessionhandler = evennia.PORTAL_SESSION_HANDLER
                telnet_service = internet.TCPServer(port, factory, interface=interface)
                telnet_service.setName("EvenniaTelnet%s" % pstring)
                telnet_service.setServiceParent(self)

                self.info_dict["telnet"].append("telnet%s: %s" % (ifacestr, port))

    def register_amp(self):
        # The AMP protocol handles the communication between
        # the portal and the mud server. Only reason to ever deactivate
        # it would be during testing and debugging.

        from evennia.server.portal import amp_server

        self.info_dict["amp"] = "amp: %s" % settings.AMP_PORT

        factory = amp_server.AMPServerFactory(self)
        amp_service = internet.TCPServer(
            settings.AMP_PORT, factory, interface=settings.AMP_INTERFACE
        )
        amp_service.setName("PortalAMPServer")
        amp_service.setServiceParent(self)

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
        """
        Return the Portal info, for display.

        """
        return self.info_dict

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

        evennia.PORTAL_SESSION_HANDLER.disconnect_all()
        if _stop_server:
            self.amp_protocol.stop_server(mode="shutdown")
        if not _reactor_stopping:
            # shutting down the reactor will trigger another signal. We set
            # a flag to avoid loops.
            self.shutdown_complete = True
            reactor.callLater(0, reactor.stop)
