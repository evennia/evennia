# Evennia Game Directory Client

Greg Taylor 2016

This contrib features a client for the [Evennia Game Directory]
(http://evennia-game-directory.appspot.com/), a listing of games built on 
Evennia. By listing your game on the directory, you make it easy for other 
people in the community to discover your creation.

*Note: Since this is still an early experiment, there is no notion of 
ownership for a game listing. As a consequence, we rely on the good behavior 
of our users in the early goings. If the directory is a success, we'll work 
on remedying this.*

## Listing your Game

To list your game, you'll need to enable the Evennia Game Directory client. 
Start by `cd`'ing to your game directory. From there, open up 
`server/conf/server_services_plugins.py`. It might look something like this 
if you don't have any other optional add-ons enabled:

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

        
To enable the client, import `EvenniaGameDirService` and fire it up after the
Evennia server has finished starting:

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
    from evennia.contrib.gamedir_client import EvenniaGameDirService
    
    
    def start_plugin_services(server):
        """
        This hook is called by Evennia, last in the Server startup process.
    
        server - a reference to the main server application.
        """
        gamedir_service = EvenniaGameDirService()
        server.services.addService(gamedir_service)


Next, configure your game listing by opening up `server/conf/settings.py` and
 using the following as a starting point:
 
    ######################################################################
    # Contrib config
    ######################################################################
    
    GAMEDIR_CLIENT = {
        'game_status': 'pre-alpha',
        'listing_contact': 'me@my-game.com',
        'telnet_hostname': 'my-game.com',
        'telnet_port': 1234,
    }

The following section in this README.md will go over all possible values.

At this point, you should be all set! Simply restart your game and check the 
server logs for errors. Your listing and some game state will be sent every 
half hour.

## Possible GAMEDIR_CLIENT settings

### game_status

Required: **Yes**
Must be one of: 'pre-alpha', 'alpha', 'beta', 'launched'

Describes the current state of your game.

### game_website

Required: No

The URL to your game's website, if you have one.

### listing_contact

Required: **Yes**

An email address for us to get in touch with in the event of a listing issue
or backwards-incompatible change.

### telnet_hostname

Required: **Yes**

The hostname that players can telnet into to play your game.

### telnet_port

Required: **Yes**

The port that the players can telnet into to play your game.

## What information is being reported?

In addition the the details listed in the previous section, we send some 
simple usage stats that don't currently get displayed. These will help the 
Evennia maintainers get a feel for some technical specifics for games out in 
the wild. 

## Troubleshooting

If you don't see your game appear on the listing, check your server logs. You
should see some error messages.  
