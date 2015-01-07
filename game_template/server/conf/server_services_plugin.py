"""

Server plugin services

This plugin module can define user-created services for the Server to
start.

This module must handle all imports and setups required to start a
twisted service (see examples in evennia.server.server). It must also
contain a function start_plugin_services(application). Evennia will
call this function with the main Server application (so your services
can be added to it). The function should not return anything. Plugin
services are started last in the Server startup process.

"""


def start_plugin_services(server):
    """
    This hook is called by Evennia, last in the Server startup process.

    server - a reference to the main server application.
    """
    pass
