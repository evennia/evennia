# Webclient

# **Web client**

Evennia comes with a MUD client accessible from a normal web browser. During development you can try it at `http://localhost:4001/webclient`. The client consists of several parts, all under `evennia/web/webclient/`:

`templates/webclient/webclient.html` and `templates/webclient/base.html` are the very simplistic django html templates describing the webclient layout.

`static/webclient/js/evennia.js` is the main evennia javascript library. This handles all communication between Evennia and the client over websockets and via AJAX/COMET if the browser can't handle websockets. It will make the Evennia object available to the javascript namespace, which offers methods for sending and receiving data to/from the server transparently. This is intended to be used also if swapping out the gui front end.

`static/webclient/js/webclient_gui.js` is the default plugin manager. It adds the `plugins` and `plugin_manager` objects to the javascript namespace, coordinates the GUI operations between the various plugins, and uses the Evennia object library for all in/out.

`static/webclient/js/plugins` provides a default set of plugins that implement a "telnet-like" interface.

`static/webclient/css/webclient.css` is the CSS file for the client; it also defines things like how to display ANSI/Xterm256 colors etc.

The server-side webclient protocols are found in `evennia/server/portal/webclient.py` and `webclient_ajax.py` for the two types of connections. You can't (and should not need to) modify these.

## Customizing the web client

Like was the case for the website, you override the webclient from your game directory. You need to add/modify a file in the matching directory location within one of the _overrides directories.  These _override directories are NOT directly used by the web server when the game is running, the server copies everything web related in the Evennia folder over to `mygame/web/static/` and then copies in all of your _overrides.  This can cause some cases were you edit a file, but it doesn't seem to make any difference in the servers behavior.  **Before doing anything else, try shutting down the game and running `evennia collectstatic` from the command line then start it back up, clear your browser cache, and see if your edit shows up.**

Example: To change the utilized plugin list, you need to override base.html by copying
`evennia/web/webclient/templates/webclient/base.html` to `mygame/web/template_overrides/webclient/base.html` and  editing it to add your new plugin.

# Evennia Web Client API (from evennia.js)
* `Evennia.init( opts )`
* `Evennia.connect()`
* `Evennia.isConnected()`
* `Evennia.msg( cmdname, args, kwargs, callback )`
* `Evennia.emit( cmdname, args, kwargs )`
* `log()`

# Plugin Manager API (from webclient_gui.js)
* `options` Object, Stores key/value 'state' that can be used by plugins to coordinate behavior.
* `plugins` Object, key/value list of the all the loaded plugins.
* `plugin_handler` Object
  * `plugin_handler.add("name", plugin)`
  * `plugin_handler.onSend(string)`

# Plugin callbacks API
* `init()` -- The only required callback
* `boolean onKeydown(event)` This plugin listens for Keydown events
* `onBeforeUnload()` This plugin does something special just before the webclient page/tab is closed.
* `onLoggedIn(args, kwargs)` This plugin does something when the webclient first logs in.
* `onGotOptions(args, kwargs)` This plugin does something with options sent from the server.
* `boolean onText(args, kwargs)` This plugin does something with messages sent from the server.
* `boolean onPrompt(args, kwargs)` This plugin does something when the server sends a prompt.
* `boolean onUnknownCmd(cmdname, args, kwargs)` This plugin does something with "unknown commands".
* `onConnectionClose(args, kwargs)` This plugin does something when the webclient disconnects from the server.
* `newstring onSend(string)` This plugin examines/alters text that other plugins generate. **Use with caution**

The order of the plugins defined in `base.html` is important.  All the callbacks for each plugin will be executed in that order.  Functions marked "boolean" above must return true/false.  Returning true will short-circuit the execution, so no other plugins lower in the base.html list will have their callback for this event called.  This enables things like the up/down arrow keys for the history.js plugin to always occur before the default_in.js plugin adds that key to the current input buffer.

# Example/Default Plugins (plugins/*.js)
* `clienthelp.js` Defines onOptionsUI from the options2 plugin.  This is a mostly empty plugin to add some "How To" information for your game.
* `default_in.js` Defines onKeydown. <enter> key or mouse clicking the arrow will send the currently typed text.
* `default_out.js` Defines onText, onPrompt, and onUnknownCmd.  Generates HTML output for the user.
* `default_unload.js` Defines onBeforeUnload.  Prompts the user to confirm that they meant to leave/close the game.
* `font.js` Defines onOptionsUI. The plugin adds the ability to select your font and font size.
* `goldenlayout_default_config.js` Not actually a plugin, defines a global variable that goldenlayout uses to determine its window layout, known tag routing, etc.
* `goldenlayout.js` Defines onKeydown, onText and custom functions.  A very powerful "tabbed" window manager for drag-n-drop windows, text routing and more. 
* `history.js` Defines onKeydown and onSend. Creates a history of past sent commands, and uses arrow keys to peruse.
* `hotbuttons.js` Defines onGotOptions. A Disabled-by-default plugin that defines a button bar with user-assignable commands.
* `iframe.js` Defines onOptionsUI.  A goldenlayout-only plugin to create a restricted browsing sub-window for a side-by-side web/text interface, mostly an example of how to build new HTML "components" for goldenlayout.
* `message_routing.js` Defines onOptionsUI, onText, onKeydown.  This goldenlayout-only plugin implements regex matching to allow users to "tag" arbitrary text that matches, so that it gets routed to proper windows. Similar to "Spawn" functions for other clients.
* `multimedia.js` An basic plugin to allow the client to handle "image" "audio" and "video" messages from the server and display them as inline HTML.
* `notifications.js` Defines onText. Generates browser notification events for each new message while the tab is hidden.
* `oob.js` Defines onSend. Allows the user to test/send Out Of Band json messages to the server.
* `options.js` Defines most callbacks. Provides a popup-based UI to coordinate options settings with the server.
* `options2.js` Defines most callbacks. Provides a goldenlayout-based version of the options/settings tab.  Integrates with other plugins via the custom onOptionsUI callback.
* `popups.js` Provides default popups/Dialog UI for other plugins to use. 
* `splithandler.js` Defines onText. Provides an older, less-flexible alternative to goldenlayout for multi-window UI to automatically separate out screen real-estate by type of message. 

# Writing your own Plugins

So, you love the functionality of the webclient, but your game has specific types of text that need to be separated out into their own space, visually.  There are two plugins to help with this.  The Goldenlayout plugin framework, and the older Splithandler framework.

## GoldenLayout

GoldenLayout is a web framework that allows web developers and their users to create their own tabbed/windowed layouts.  Windows/tabs can be click-and-dragged from location to location by clicking on their titlebar and dragging until the "frame lines" appear.  Dragging a window onto another window's titlebar will create a tabbed "Stack".  The Evennia goldenlayout plugin defines 3 basic types of window:  The Main window, input windows and non-main text output windows.  The Main window and the first input window are unique in that they can't be "closed".

The most basic customization is to provide your users with a default layout other than just one Main output and the one starting input window.  This is done by modifying your server's goldenlayout_default_config.js.

Start by creating a new `mygame/web/static_overrides/webclient/js/plugins/goldenlayout_default_config.js` file, and adding the following JSON variable:

```
var goldenlayout_config = {
    content: [{
        type: 'column',
        content: [{
            type: 'row',
            content: [{
                type: 'column',
                content: [{
                    type: 'component',
                    componentName: 'Main',
                    isClosable: false,
                    tooltip: 'Main - drag to desired position.',
                    componentState: {
                        cssClass: 'content',
                        types: 'untagged',
                        updateMethod: 'newlines',
                    },
                }, {
                    type: 'component',
                    componentName: 'input',
                    id: 'inputComponent',
                    height: 10,
                    tooltip: 'Input - The last input in the layout is always the default.',
                }, {
                    type: 'component',
                    componentName: 'input',
                    id: 'inputComponent',
                    height: 10,
                    isClosable: false,
                    tooltip: 'Input - The last input in the layout is always the default.',
                }]
            },{
                type: 'column',
                content: [{
                    type: 'component',
                    componentName: 'evennia',
                    componentId: 'evennia',
                    title: 'example',
                    height: 60,
                    isClosable: false,
                    componentState: {
                        types: 'some-tag-here',
                        updateMethod: 'newlines',
                    },
                }, {
                    type: 'component',
                    componentName: 'evennia',
                    componentId: 'evennia',
                    title: 'sheet',
                    isClosable: false,
                    componentState: {
                        types: 'sheet',
                        updateMethod: 'replace',
                    },
                }],
            }],
        }]
    }]
};
```
This is a bit ugly, but hopefully, from the indentation, you can see that it creates a side-by-side (2-column) interface with 3 windows down the left side (The Main and 2 inputs) and a pair of windows on the right side for extra outputs.  Any text tagged with "some-tag-here" will flow to the bottom of the "example" window, and any text tagged "sheet" will replace the text already in the "sheet" window.  

Note:  GoldenLayout gets VERY confused and will break if you create two windows with the "Main" componentName.

Now, let's say you want to display text on each window using different CSS.  This is where new goldenlayout "components" come in.  Each component is like a blueprint that gets stamped out when you create a new instance of that component, once it is defined, it won't be easily altered.  You will need to define a new component, preferably in a new plugin file, and then add that into your page (either dynamically to the DOM via javascript, or by including the new plugin file into the base.html). 

First up, follow the directions in Customizing the Web Client section above to override the base.html.

Next, add the new plugin to your copy of base.html:
```
<script src={% static "webclient/js/plugins/myplugin.js" %} language="javascript" type="text/javascript"></script>
```
Remember, plugins are load-order dependent, so make sure the new `<script>` tag comes before the goldenlayout.js

Next, create a new plugin file `mygame/web/static_overrides/webclient/js/plugins/myplugin.js` and edit it.

```
let myplugin = (function () {
    //
    //
    var postInit = function() {
        var myLayout = window.plugins['goldenlayout'].getGL();

        // register our component and replace the default messagewindow
        myLayout.registerComponent( 'mycomponent', function (container, componentState) {
            let mycssdiv = $('<div>').addClass('myCSS');
            mycssdiv.attr('types', 'mytag');
            mycssdiv.attr('update_method', 'newlines');
            mycssdiv.appendTo( container.getElement() );
        });

        console.log("MyPlugin Initialized.");
    }

    return {
        init: function () {},
        postInit: postInit,
    }
})();
window.plugin_handler.add("myplugin", myplugin);
```
You can then add "mycomponent" to an item's componentName in your goldenlayout_default_config.js.

Make sure to stop your server, evennia collectstatic, and restart your server.  Then make sure to clear your browser cache before loading the webclient page.


## Older Splithandler
The splithandler.js plugin provides a means to do this, but you don't want to have to force every player to set up their own layout every time they use the client.

Let's create a `mygame/web/static_overrides/webclient/js/plugins/layout.js` plugin!

First up, follow the directions in Customizing the Web Client section above to override the base.html.

Next, add the new plugin to your copy of base.html:
```
<script src={% static "webclient/js/plugins/layout.js" %} language="javascript" type="text/javascript"></script>
```
Remember, plugins are load-order dependent, so make sure the new `<script>` tag comes after the splithandler.js

And finally create the layout.js file and add the minimum skeleton of a plugin to it:

```
// my new plugin
var my_plugin = (function () {
    let init = function () {
        console.log("myplugin! Hello World!");
    }

    return {
        init: init,
    }
})();
plugin_handler.add("myplugin", my_plugin);
```

Now, `evennia stop`, `evennia collectstatic`, and `evennia start` and then load the webclient up in your browser.
Enable developer options and look in the console, and you should see the message 'myplugin! Hello World!'

Since our layout.js plugin is going to use the splithandler, let's enhance this by adding a check to make sure the splithandler.js plugin has been loaded:

change the above init function to:
```
let init = function () {
    let splithandler = plugins['splithandler'];
    if( splithandler ) {
        console.log("MyPlugin initialized");
    } else {
        alert('MyPlugin requires the splithandler.js plugin. Please contact the game maintainer to correct this');
    }
}
```

And finally, the splithandler.js provides provides two functions to cut up the screen real-estate:
    `dynamic_split( pane_name_to_cut_apart, direction_of_split, new_pane_name1, new_pane_name2, text_flow_pane1, text_flow_pane2, array_of_split_percentages )`
and
    `set_pane_types( pane_to_set, array_of_known_message_types_to_assign)`

In this case, we'll cut it into 3 panes, 1 bigger, two smaller, and assign 'help' messages to the top-right pane:
```
let init = function () {
    let splithandler = plugins['splithandler'];
    if( splithandler ) {
        splithandler.dynamic_split("main","horizontal","left","right","linefeed","linefeed",[50,50]);
        splithandler.dynamic_split("right","vertical","help","misc","replace","replace",[50,50]);
        splithandler.set_pane_types('help', ['help']);

        console.log("MyPlugin initialized");
    } else {
        alert('MyPlugin requires the splithandler.js plugin. Please contact the game maintainer to correct this');
    }
}
```

`evennia stop`, `evennia collectstatic`, and `evennia start` once more, and force-reload your browser page to clear any cached version.  You should now have a nicely split layout.