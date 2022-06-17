/*
 *
 * Evennia Webclient default unload plugin
 *
 */
let unload_plugin = (function () {

    let onBeforeUnload = function () {
        return "You are about to leave the game. Please confirm.";
    }

    return {
        init: function () {},
        onBeforeUnload: onBeforeUnload,
    }
})();
plugin_handler.add('unload', unload_plugin);
