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

Like was the case for the website, you override the webclient from your game directory. You need to add/modify a file in the matching directory location within one of the _overrides directories.

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
* `default_in.js` Defines onKeydown. <enter> key or mouse clicking the arrow will send the currently typed text.
* `default_out.js` Defines onText, onPrompt, and onUnknownCmd.  Generates HTML output for the user.
* `default_unload.js` Defines onBeforeUnload.  Prompts the user to confirm that they meant to leave/close the game.
* `history.js` Defines onKeydown and onSend. Creates a history of past sent commands, and uses arrow keys to peruse.
* `notifications.js` Defines onText. Generates browser notification events for each new message while the tab is hidden. 
* `oob.js` Defines onSend. Allows the user to test/send Out Of Band json messages to the server.
* `options.js` Defines most callbacks. Provides a popup-based UI to coordinate options settings with the server.
* `popups.js` Provides default popups/Dialog UI for other plugins to use. 
* `splithandler.js` Defines onText. Provides a powerful multi-window UI extension to automatically separate out screen real-estate by type of message. 

# Writing your own Plugins

So, you love the functionality of the webclient, but your game has specific types of text that need to be separated out into its own space, visually.  The splithandler.js plugin provides a means to do this, but you don't want to have to force every player to set up their own layout every time they use the client.

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

```python
class Documentation:
    RATING = "Unknown"
```