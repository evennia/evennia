/*
 * Evennia server-side-generated "raw" HTML message handler plugin
 *
 *     PLUGIN ORDER PREREQS:
 *          loaded after:
 *              webclient_gui.js
 *              option2.js
 *          loaded before:
 *
 *
 *     To use, at minimum, in evennia python code:
 *         target.msg( html="<div><span>...etc...</span></div>" )
 *
 *     or, if you prefer tagged routing (RECOMMENDED):
 *         target.msg( html=("<div><span>...etc...</span></div>",{'type':'tag'}) )
 *
 */
let html_plugin = (function () {
    //
    var html = function (args, kwargs) {
        let options = window.options;
        if( !("html" in options) || options["html"] === false ) { return; }

        var mwins = window.plugins["goldenlayout"].routeMessage(args, kwargs);
        mwins.forEach( function (mwin) {
            mwin.append(args[0]);
            mwin.scrollTop(mwin[0].scrollHeight);
        });
    }

    //
    var onOptionsUI = function (parentdiv) {
        let options = window.options;
        var checked;

        checked = options["html"] ? "checked='checked'" : "";
        var mmHtml = $( [ "<label>",
                               "<input type='checkbox' data-setting='html' " + checked + "'>",
                               " Prefer server-side generated direct-HTML messages over old-school ASCII text",
                               "</label>"
                             ].join("") );
        mmHtml.on("change", window.plugins["options2"].onOptionCheckboxChanged);

        parentdiv.append(mmHtml);
    }

    //
    // Mandatory plugin init function
    var init = function () {
        let options = window.options;
        options["html"]  = true;

        let Evennia = window.Evennia;
        Evennia.emitter.on("html",   html); // capture "image" commands
        console.log('HTML plugin initialized');
    }

    return {
        init: init,
        onOptionsUI: onOptionsUI,
    }
})();
plugin_handler.add("html_plugin", html_plugin);
