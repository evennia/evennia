/*
 *
 * Evennia Webclient default 'send-text-on-enter-key' IO plugin
 *
 */
let defaultin_plugin = (function () {

    //
    // handle the default <enter> key triggering onSend()
    var onKeydown = function (event) {
        // find where the key comes from
        var inputfield = $(".inputfield:focus");

        // check for important keys
        switch (event.which) {
            case 16:  // ignore shift
            case 17:  // ignore alt
            case 18:  // ignore control
            case 20:  // ignore caps lock
            case 144: // ignore num lock
                break;

            case 13: // Enter key
                var outtext = inputfield.val();
                if ( outtext && !event.shiftKey ) {  // Enter Key without shift --> send Mesg
                    var lines = outtext.trim().replace(/[\r]+/,"\n").replace(/[\n]+/, "\n").split("\n");
                    for (var i = 0; i < lines.length; i++) {
                        plugin_handler.onSend( lines[i].trim() );
                    }
                    inputfield.val('');
                    event.preventDefault();
                }
                inputfield.blur();
                break;

            // Anything else, focus() a textarea if needed, and allow the default event
            default:
                // is anything actually focused?  if not, focus the first .inputfield found in the DOM
                if( !inputfield.hasClass('inputfield') ) {
                    // :first only matters if dual_input or similar multi-input plugins are in use
                    $('.inputfield:last').focus();
                }
        }

        return true;
    }

    //
    // Mandatory plugin init function
    var init = function () {
        // Handle pressing the send button
        $("#inputsend")
            .bind("click", function (evnt) {
                // simulate a carriage return
                var e = $.Event( "keydown" );
                e.which = 13;
                $('.inputfield:last').trigger(e);
            });

        console.log('DefaultIn initialized');
    }

    return {
        init: init,
        onKeydown: onKeydown,
    }
})();
plugin_handler.add('defaultin', defaultin_plugin);
