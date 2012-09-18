"""

This plugin module can define user-created services for the Server to start.

To use, copy this module up one level to game/gamesrc/conf/ and set
settings.SERVER_SERVICES_PLUGIN_MODULE to point to this module.

This module must handle all imports and setups required to start a twisted
services (see examples in src/server/server.py). It must also contain a
function start_plugin_services(application). Evennia will call this function
with the main Server application (so your services can be added to it). The
function should not return anything. Plugin services are started last in
the Server startup process.

"""

def start_plugin_services(server):
    """
    This hook is called by Evennia, last in the Server startup process.

    server - a reference to the main server application.
    """
    pass
