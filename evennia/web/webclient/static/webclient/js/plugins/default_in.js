/*
 *
 * Evennia Webclient default "send-text-on-enter-key" IO plugin
 *
 */
let defaultin_plugin = (function () {

    //
    // handle the default <enter> key triggering onSend()
    var onKeydown = function (event) {
        // find where the key comes from
        var inputfield = $(".inputfield:focus");

        if( inputfield.length < 1 ) { // non-goldenlayout backwards compatibility
            inputfield = $("#inputfield:focus");
        }

        // check for important keys
        switch (event.which) {
            case  9:  // ignore tab key -- allows normal focus control
            case 16:  // ignore shift
            case 17:  // ignore alt
            case 18:  // ignore control
            case 20:  // ignore caps lock
            case 144: // ignore num lock
                break;

            case 13: // Enter key
                var outtext = inputfield.val() || ""; // Grab the text from which-ever inputfield is focused
                if ( !event.shiftKey ) {  // Enter Key without shift --> send Mesg
                    var lines = outtext.replace(/[\r]+/,"\n").replace(/[\n]+/, "\n").split("\n");
                    for (var i = 0; i < lines.length; i++) {
                        plugin_handler.onSend( lines[i] );
                    }
                    inputfield.val(""); // Clear this inputfield
                    event.preventDefault();

                    // enter key by itself should toggle focus
                    if( inputfield.length < 1 ) {
                        inputfield = $(".inputfield:last");
                        inputfield.focus();
                        if( inputfield.length < 1 ) { // non-goldenlayout backwards compatibility
                            $("#inputfield").focus();
                        }
                    } else {
                        inputfield.blur();
                    }
                } // else allow building a multi-line input command
                break;

            // Anything else, focus() a textarea if needed, and allow the default event
            default:
                // is an inputfield actually focused?
                if( inputfield.length < 1 ) {
                    // Nope, focus the last .inputfield found in the DOM (or #inputfield)
                    //     :last only matters if multi-input plugins are in use
                    inputfield = $(".inputfield:last");
                    inputfield.focus();
                    if( inputfield.length < 1 ) { // non-goldenlayout backwards compatibility
                        $("#inputfield").focus();
                    }
                }
        }

        return true;
    }

    //
    // Mandatory plugin init function
    var init = function () {
        // Handle pressing the send button, this only applies to non-goldenlayout setups
        $("#inputsend")
            .bind("click", function (evnt) {
                // simulate a carriage return
                var e = $.Event( "keydown" );
                e.which = 13;
                $("#inputfield").focus().trigger(e);
            });
    }

    return {
        init: init,
        onKeydown: onKeydown,
    }
})();
window.plugin_handler.add("defaultin", defaultin_plugin);
