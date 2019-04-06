/*
 *
 * Assignable "hot-buttons" Plugin
 *
 * This adds a bar of 9 buttons that can be shift-click assigned,
 * whatever text is in the bottom textinput buffer will be copied.
 * Once assigned, clicking the button again and have it execute those commands.
 *
 * It stores these commands as server side options.
 *
 * NOTE:  This is a CONTRIB.  To use this in your game:
 *
 *     Stop Evennia
 *
 *     Copy this file to mygame/web/static_overrides/webclient/js/plugins/hotbuttons.js
 *
 *     Copy evennia/web/webclient/templates/webclient/base.html to
 *          mygame/web/template_overrides/webclient/base.html
 *
 *     Edit  mygame/web/template_overrides/webclient/base.html to add:
 *          <script src={% static "webclient/js/plugins/hotbuttons.js" %} type="text/javascript"></script>
 *     before the goldenlayout.js plugin tags or after the splithandler.js <script></script> plugin tags
 *
 *     If you are using goldenlayout.js, uncomment the hotbuttons component in goldenlayout_default_config.js
 *
 *     Run:  evennia collectstatic (say "yes" to the overwrite prompt)
 *     Start Evennia
 *
 * REQUIRES: goldenlayout.js OR splithandler.js
 */
let hotbuttons = (function () {
    var dependenciesMet = false;

    var numButtons = 9;
    var commandCache = new Array;

    //
    // collect command text
    var assignButton = function(n, text) { // n is 1-based
        // make sure text has something in it
        if( text && text.length ) {
            // cache the command text
            commandCache[n] = text;

            // is there a space in the command, indicating "command argument" syntax?
            if( text.indexOf(" ") > 0 ) {
                // use the first word as the text on the button
                $("#assign_button"+n).text( text.slice(0, text.indexOf(" ")) );
            } else { 
                // use the single-word-text on the button
                $("#assign_button"+n).text( text );
            }
        }
    }

    //
    // Shift click a button to clear it
    var clearButton = function(n) {
        // change button text to "unassigned"
        $("#assign_button"+n).text( "unassigned" );
        // clear current command
        commandCache[n] = "unassigned";
    }

    //
    // actually send the command associated with the button that is clicked
    var sendImmediate = function(n) {
        var text = commandCache[n];
        if( text.length ) {
            Evennia.msg("text", [text], {});
        }
    }

    //
    // send, assign, or clear the button
    var hotButtonClicked = function(e) {
        var button = $("#assign_button"+e.data);
        if( button.text() == "unassigned" ) {
            // Assign the button and send the full button state to the server using a Webclient_Options event
            var input = $(".inputfield:last");
            if( input.length < 1 ) {
                input = $("#inputfield");
            }
            assignButton( e.data, input.val() );
            Evennia.msg("webclient_options", [], { "HotButtons": commandCache });
        } else {
            if( e.shiftKey ) {
                // Clear the button and send the full button state to the server using a Webclient_Options event
                clearButton(e.data);
                Evennia.msg("webclient_options", [], { "HotButtons": commandCache });
            } else {
                sendImmediate(e.data);
            }
        }
    }


    //
    // Add Buttons UI for SplitHandler
    var addButtonsUI = function () {
        var buttons = $( [
                "<div id='buttons' class='split split-vertical'>",
                " <div id='buttonsform'>",
                "  <div id='buttonscontrol' class='input-group'>",
                "   <button class='btn' id='assign_button0' type='button' value='button0'>unassigned</button>",
                "   <button class='btn' id='assign_button1' type='button' value='button1'>unassigned</button>",
                "   <button class='btn' id='assign_button2' type='button' value='button2'>unassigned</button>",
                "   <button class='btn' id='assign_button3' type='button' value='button3'>unassigned</button>",
                "   <button class='btn' id='assign_button4' type='button' value='button4'>unassigned</button>",
                "   <button class='btn' id='assign_button5' type='button' value='button5'>unassigned</button>",
                "   <button class='btn' id='assign_button6' type='button' value='button6'>unassigned</button>",
                "   <button class='btn' id='assign_button7' type='button' value='button7'>unassigned</button>",
                "   <button class='btn' id='assign_button8' type='button' value='button8'>unassigned</button>",
                "  </div>",
                " </div>",
                "</div>",
            ].join("\n") );

        // Add buttons in front of the existing #inputform
        $("#input").prev().replaceWith(buttons);

        Split(["#main","#buttons","#input"], {
            sizes: [85,5,10],
            direction: "vertical",
            gutterSize: 4,
            minSize: [150,20,50],
        });

        for( var n=0; n<numButtons; n++ ) { 
            commandCache.push("unassigned");
            $("#assign_button"+n).click( n, hotButtonClicked );
        }
    }


    //
    // Create and register the hotbuttons golden-layout component
    var buildComponent = function () {
        var myLayout = window.plugins["goldenlayout"].getGL();

        myLayout.registerComponent( "hotbuttons", function (container, componentState) {
            // build the buttons
            var div = $("<div class='input-group'>");

            var len = commandCache.length;
            for( var x=len; x < len + numButtons; x++ ) {
                commandCache.push("unassigned");

                // initialize button command cache and onClick handler
                var button = $("<button class='btn' id='assign_button"+x+"' type='button' value='button"+x+"'>");
                button.html("unassigned");
                button.click( x, hotButtonClicked );

                button.appendTo( div );
            }

            div.appendTo( container.getElement() );
        });
    }


    // Public

    //
    // Handle the HotButtons part of a Webclient_Options event
    var onGotOptions = function(args, kwargs) {
        if( dependenciesMet && kwargs["HotButtons"] ) {
            var buttonOptions = kwargs["HotButtons"];
            $.each( buttonOptions, function( key, value ) {
                assignButton(key, value);
            });
        }
    }


    //
    // Initialize me
    var init = function() {
        // Are we using splithandler?
        if( window.plugins["splithandler"] ) { 
            addButtonsUI();
            dependenciesMet = true;
        }
    }


    //
    //
    var postInit = function() {
        // Are we using GoldenLayout?
        if( window.plugins["goldenlayout"] ) {
            buildComponent();
            dependenciesMet = true;
        }
    }

    return {
        init: init,
        postInit: postInit,
        onGotOptions: onGotOptions,
    }
})();
window.plugin_handler.add("hotbuttons", hotbuttons);
