/*
 *
 * Evennia Webclient GUI component
 *
 * This is used in conjunction with the main evennia.js library, which
 * handles all the communication with the Server.
 *
 * The job of this code is to coordinate between listeners subscribed to
 * evennia messages and any registered plugins that want to process those
 * messages and send data back to Evennia
 *
 * This is done via Evennia.emitter.on(cmdname, listener) and calling
 * each plugin's init() function to give each plugin a chance to register
 * input handlers or other events on startup.
 *
 * Once a plugin has determined it wants to send a message back to the
 * server, it generates an onSend() function event which allows all
 * other plugins a chance to modify the event and then uses
 * Evennia.msg(cmdname, args, kwargs, [callback]) to finally send the data.
 *
 */

//
// Global Plugins system
//

var options = {}; // Global "settings" object that all plugins can use to
                  // save/pass data to each other and the server.
                  // format should match:
                  //  { 'plugin_name': { 'option_key': value, ... }, ... }

var plugins = {}; // Global plugin objects by name.
                  // Each must have an init() function.

//
// Global plugin_handler
//
var plugin_handler = (function () {
    "use strict"

    var ordered_plugins = new Array; // plugins in <html> loaded order

    //
    // Plugin Support Functions
    //

    // Add a new plugin
    var add = function (name, plugin) {
        plugins[name] = plugin;
        ordered_plugins.push( plugin );
    }


    //
    // GUI Event Handlers
    //

    // catch all keyboard input, handle special chars
    var onKeydown = function (event) {
        // cycle through each plugin's keydown
        for( let n=0; n < ordered_plugins.length; n++ ) {
            let plugin = ordered_plugins[n];
            // does this plugin handle keydown events?
            if( 'onKeydown' in plugin ) {
                // yes, does this plugin claim this event exclusively?
                if( plugin.onKeydown(event) ) {
                    // 'true' claims this event has been handled
                    return;
                }
            }
        }
        console.log('NO plugin handled this Keydown');
    }


    // Ask if user really wants to exit session when closing
    // the tab or reloading the page. Note: the message is not shown
    // in Firefox, there it's a standard error.
    var onBeforeUnload = function () {
        // cycle through each plugin to look for unload handlers
        for( let n=0; n < ordered_plugins.length; n++ ) {
            let plugin = ordered_plugins[n];
            if( 'onBeforeUnload' in plugin ) {
                plugin.onBeforeUnload();
            }
        }
    }


    //
    // Evennia Public Event Handlers
    //

    // Handle onLoggedIn from the server
    var onLoggedIn = function (args, kwargs) {
        for( let n=0; n < ordered_plugins.length; n++ ) {
            let plugin = ordered_plugins[n];
            if( 'onLoggedIn' in plugin ) {
                plugin.onLoggedIn(args, kwargs);
            }
        }
    }


    // Handle onGotOptions from the server
    var onGotOptions = function (args, kwargs) {
        // does any plugin handle Options?
        for( let n=0; n < ordered_plugins.length; n++ ) {
            let plugin = ordered_plugins[n];
            if( 'onGotOptions' in plugin ) {
                plugin.onGotOptions(args, kwargs);
            }
        }
    }


    // Handle text coming from the server
    var onText = function (args, kwargs) {
        // does this plugin handle this onText event?
        for( let n=0; n < ordered_plugins.length; n++ ) {
            let plugin = ordered_plugins[n];
            if( 'onText' in plugin ) {
                if( plugin.onText(args, kwargs) ) {
                    // True  -- means this plugin claims this Text exclusively.
                    return;
                }
            }
        }
        console.log('NO plugin handled this Text');
    }


    // Handle prompt output from the server
    var onPrompt = function (args, kwargs) {
        // does this plugin handle this onPrompt event?
        for( let n=0; n < ordered_plugins.length; n++ ) {
            let plugin = ordered_plugins[n];
            if( 'onPrompt' in plugin ) {
                if( plugin.onPrompt(args, kwargs) ) {
                    // True -- means this plugin claims this Prompt exclusively.
                    return;
                }
            }
        }
        console.log('NO plugin handled this Prompt');
    }


    // Handle unrecognized commands from server
    var onDefault = function (cmdname, args, kwargs) {
        // does this plugin handle this UnknownCmd?
        for( let n=0; n < ordered_plugins.length; n++ ) {
            let plugin = ordered_plugins[n];
            if( 'onUnknownCmd' in plugin ) {
                if( plugin.onUnknownCmd(args, kwargs) ) {
                    // True -- means this plugin claims this UnknownCmd exclusively.
                    return;
                }
            }
        }
        console.log('NO plugin handled this Unknown Evennia Command');
    }


    // Handle the server connection closing
    var onConnectionClose = function (args, kwargs) {
        // give every plugin a chance to do stuff onConnectionClose
        for( let n=0; n < ordered_plugins.length; n++ ) {
            let plugin = ordered_plugins[n];
            if( 'onConnectionClose' in plugin ) {
                plugin.onConnectionClose(args, kwargs);
            }
        }

        onText(["The connection was closed or lost."], {'cls': 'err'});
    }


    // Silences events we don't do anything with.
    var onSilence = function (cmdname, args, kwargs) {}


    //
    // Global onSend() function to iterate through all plugins before sending text to the server.
    // This can be called by other plugins for "Triggers", <enter>, and other automated sends
    //
    var onSend = function (line) {
        if (!Evennia.isConnected()) {
            var reconnect = confirm("Not currently connected. Reconnect?");
            if (reconnect) {
                onText(["Attempting to reconnnect..."], {cls: "sys"});
                Evennia.connect();
            }
            // Don't try to send anything until the connection is back.
            return;
        }

        // default output command
        var cmd = {
                command: "text",
                args: [ line ],
                kwargs: {}
              };

        // Give each plugin a chance to use/modify the outgoing command for aliases/history/etc
        for( let n=0; n < ordered_plugins.length; n++ ) {
            let plugin = ordered_plugins[n];
            if( 'onSend' in plugin ) {
                var outCmd = plugin.onSend(line);
                if( outCmd ) {
                    cmd = outCmd;
                }
            }
        }

        // console.log('sending: ' + cmd.command + ', [' + cmd.args[0].toString() + '], ' + cmd.kwargs.toString() );
        Evennia.msg(cmd.command, cmd.args, cmd.kwargs);
    }


    //
    // call each plugins' init function (the only required function)
    //
    var init = function () {
        for( let n=0; n < ordered_plugins.length; n++ ) {
            ordered_plugins[n].init();
        }
    }


    //
    // normally init() is all that is needed, but some cases may require a second
    // pass to avoid chicken/egg dependencies between two plugins.
    var postInit = function () {
        // does this plugin need postInit() to be called?
        for( let n=0; n < ordered_plugins.length; n++ ) {
            let plugin = ordered_plugins[n];
            if( 'postInit' in plugin ) {
                plugin.postInit();
            }
        }
    }


    return {
        add: add,
        onKeydown: onKeydown,
        onBeforeUnload: onBeforeUnload,
        onLoggedIn: onLoggedIn,
        onText: onText,
        onGotOptions: onGotOptions,
        onPrompt: onPrompt,
        onDefault: onDefault,
        onSilence: onSilence,
        onConnectionClose: onConnectionClose,
        onSend: onSend,
        init: init,
        postInit: postInit,
    }
})();


//
// Webclient Initialization
//

// Event when client finishes loading
$(document).ready(function() {
    // This is safe to call, it will always only
    // initialize once.
    Evennia.init();

    // register listeners
    Evennia.emitter.on("logged_in", plugin_handler.onLoggedIn);
    Evennia.emitter.on("text", plugin_handler.onText);
    Evennia.emitter.on("webclient_options", plugin_handler.onGotOptions);
    Evennia.emitter.on("prompt", plugin_handler.onPrompt);
    Evennia.emitter.on("default", plugin_handler.onDefault);
    Evennia.emitter.on("connection_close", plugin_handler.onConnectionClose);

    // silence currently unused events
    Evennia.emitter.on("connection_open", plugin_handler.onSilence);
    Evennia.emitter.on("connection_error", plugin_handler.onSilence);

    // Event when closing window (have to have Evennia initialized)
    $(window).bind("beforeunload", plugin_handler.onBeforeUnload);
    $(window).bind("unload", Evennia.connection.close);

    // Event when any key is pressed
    $(document).keydown(plugin_handler.onKeydown)

    // set an idle timer to send idle every 3 minutes,
    // to avoid proxy servers timing out on us
    setInterval( function() { // Connect to server
            Evennia.msg("text", ["idle"], {});
        },
        60000*3
    );

    // Initialize all plugins
    plugin_handler.init();

    // Finish Initializing any plugins that need a second stage
    plugin_handler.postInit();

    console.log("Completed Webclient setup");
});
