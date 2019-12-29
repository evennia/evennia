/*
 *
 * Evennia Webclient help plugin
 *
 */
let clienthelp_plugin = (function () {
    //
    //
    //
    var onOptionsUI = function (parentdiv) {
        var help_text = $( [
            "<h3>Welcome to Evennia.</h3>",
            "<div>This client supports a bunch of features, including<div>",
            "<div>drag-and-drop window placement, multiple input windows, and per-window message routing.</div>",
            "<div>To get the full details, go to: <a href='http://evennia.com'>Evennia.com</a></div><br>",
        ].join(""));
        parentdiv.append(help_text);
    }

    return {
        init: function () {},
        onOptionsUI: onOptionsUI,
    }
})();
window.plugin_handler.add("clienthelp", clienthelp_plugin);
