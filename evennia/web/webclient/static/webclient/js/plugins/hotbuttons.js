/*
 *
 * Assignable "hot-buttons" Plugin
 *
 * This adds a bar of 9 buttons that can be shift-click assigned whatever is in the textinput buffer, so you can simply
 * click the button again and have it execute those commands, instead of having to type it all out again and again.
 *
 * It stores these commands as server side options.
 *
 * NOTE:  This is a CONTRIB.  To use this in your game:
 *
 *     Stop Evennia
 *
 *     Copy this file to mygame/web/static_overrides/webclient/js/plugins/hotbuttons.js
 *     Copy evennia/web/webclient/templates/webclient/base.html to mygame/web/template_overrides/webclient/base.html
 *
 *     Edit  mygame/web/template_overrides/webclient/base.html to add:
 *          <script src={% static "webclient/js/plugins/hotbuttons.js" %} language="javascript" type="text/javascript"></script>
 *     after the other <script></script> plugin tags.
 *
 *     Run:  evennia collectstatic (say "yes" to the overwrite prompt)
 *     Start Evennia
 */
let hotbuttons = (function () {
    var dependencies_met = true; // To start, assume either splithandler or goldenlayout plugin is enabled.

    var num_buttons = 9;
    var command_cache = new Array;

    var hotButtonConfig = {
        content: [{
            type: "column",
            content: [{
                type: "row",
                content: [{
                    type: "column",
                    content: [{
                        type: "component",
                        componentName: "Main",
                        isClosable: false,
                        tooltip: "Main - drag to desird position.",
                        componentState: {
                            types: "untagged",
                            update_method: "newlines",
                        },
                    }]
                }],
            }, {
                type: "component",
                componentName: "hotbuttons",
                id: "inputComponent",
                height: 12,
                tooltip: "Input - The last input in the layout is always the default.",
            }, {
                type: "component",
                componentName: "input",
                id: "inputComponent",
                height: 12,
                tooltip: "Input - The last input in the layout is always the default.",
            }, {
                type: "component",
                componentName: "input",
                id: "inputComponent",
                height: 12,
                isClosable: false,
                tooltip: "Input - The last input in the layout is always the default.",
            }]
        }]
    };

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

        for( var n=0; n<num_buttons; n++ ) { 
            command_cache.push("unassigned");
            $("#assign_button"+n).click( n, hotButtonClicked );
        }
    }


    //
    // collect command text
    var assignButton = function(n, text) { // n is 1-based
        // make sure text has something in it
        if( text && text.length ) {
            // cache the command text
            command_cache[n] = text;

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
        command_cache[n] = "unassigned";
    }

    //
    // actually send the command associated with the button that is clicked
    var sendImmediate = function(n) {
        var text = command_cache[n];
        if( text.length ) {
            Evennia.msg("text", [text], {});
        }
    }

    //
    // send, assign, or clear the button
    var hotButtonClicked = function(e) {
        var button = $("#assign_button"+e.data);
        console.log("button " + e.data + " clicked");
        if( button.text() == "unassigned" ) {
            // Assign the button and send the full button state to the server using a Webclient_Options event
            var input = $(".inputfield:last");
            if( input.length < 1 ) {
                input = $("#inputfield");
            }
            assignButton( e.data, input.val() );
            Evennia.msg("webclient_options", [], { "HotButtons": command_cache });
        } else {
            if( e.shiftKey ) {
                // Clear the button and send the full button state to the server using a Webclient_Options event
                clearButton(e.data);
                Evennia.msg("webclient_options", [], { "HotButtons": command_cache });
            } else {
                sendImmediate(e.data);
            }
        }
    }


    //
    // Create and register the hotbuttons golden-layout component
    var buildComponent = function () {
        var myLayout = plugins["goldenlayout"].getGL();

        myLayout.registerComponent( "hotbuttons", function (container, componentState) {
            console.log("hotbuttons");

            // build the buttons
            var div = $("<div class='input-group'>");

            var len = command_cache.length;
            for( var x=len; x < len + num_buttons; x++ ) {
                command_cache.push("unassigned");

                // initialize button command cache and onClick handler
                button = $("<button class='btn' id='assign_button"+x+"' type='button' value='button"+x+"'>");
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
        if( dependencies_met && kwargs["HotButtons"] ) {
            var button_options = kwargs["HotButtons"];
            $.each( button_options, function( key, value ) {
                assignButton(key, value);
            });
        }
    }


    //
    // Initialize me
    var init = function() {
        // Are we using GoldenLayout?
        if( plugins["goldenlayout"] ) {
            // update goldenlayout"s global config
            plugins["goldenlayout"].setConfig( hotButtonConfig );
            // wait for postInit() to create the required component
            dependencies_met = true;
        }

        // Are we using splithandler?
        if( plugins["splithandler"] ) { 
            addButtonsUI();
            dependencies_met = true;
        }
    }


    //
    //
    var postInit = function() {
        if( dependencies_met ) {
            if( plugins["goldenlayout"] ) {
                buildComponent();
            }
 
            console.log("HotButtons Plugin Initialized.");
        } else {
            console.log("HotButtons Plugin Dependencies Not Met. No splithandler.js or goldenlayout.js plugin found.");
        }
    }

    return {
        init: init,
        postInit: postInit,
        onGotOptions: onGotOptions,
    }
})();
window.plugin_handler.add("hotbuttons", hotbuttons);
