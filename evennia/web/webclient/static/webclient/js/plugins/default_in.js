/*
 *
 * Evennia Webclient default 'send-text-on-enter-key' IO plugin
 *
 */
let defaultin_plugin = (function () {

    //
    // handle the default <enter> key triggering onSend()
    var onKeydown = function (event) {
	$("#inputfield").focus();
        if ( (event.which === 13) && (!event.shiftKey) ) {  // Enter Key without shift
            var inputfield = $("#inputfield");
            var outtext = inputfield.val();
            var lines = outtext.trim().replace(/[\r]+/,"\n").replace(/[\n]+/, "\n").split("\n");
            for (var i = 0; i < lines.length; i++) {
                plugin_handler.onSend( lines[i].trim() );
            }
            inputfield.val('');
            event.preventDefault();
        }

        return true;
    }

    //
    // Mandatory plugin init function
    var init = function () {
        // Handle pressing the send button
        $("#inputsend")
            .bind("click", function (event) {
                var e = $.Event( "keydown" );
                e.which = 13;
                $('#inputfield').trigger(e);
            });

        console.log('DefaultIn initialized');
    }

    return {
        init: init,
        onKeydown: onKeydown,
    }
})();
plugin_handler.add('defaultin', defaultin_plugin);
