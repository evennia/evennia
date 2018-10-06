/*
 *
 * Assignable 'hot-buttons' Plugin
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
 *     Run:  evennia collectstatic (say 'yes' to the overwrite prompt)
 *     Start Evennia
 */
plugin_handler.add('hotbuttons', (function () {

    var num_buttons = 9;
    var command_cache = new Array(num_buttons);

    //
    // Add Buttons
    var addButtonsUI = function () {
        var buttons = $( [
                          '<div id="buttons" class="split split-vertical">',
                          ' <div id="buttonsform" class="wrapper">',
                          '  <div id="buttonscontrol" class="input-group">',
                          '   <button class="btn" id="assign_button0" type="button" value="button0">unassigned</button>',
                          '   <button class="btn" id="assign_button1" type="button" value="button1">unassigned</button>',
                          '   <button class="btn" id="assign_button2" type="button" value="button2">unassigned</button>',
                          '   <button class="btn" id="assign_button3" type="button" value="button3">unassigned</button>',
                          '   <button class="btn" id="assign_button4" type="button" value="button4">unassigned</button>',
                          '   <button class="btn" id="assign_button5" type="button" value="button5">unassigned</button>',
                          '   <button class="btn" id="assign_button6" type="button" value="button6">unassigned</button>',
                          '   <button class="btn" id="assign_button7" type="button" value="button7">unassigned</button>',
                          '   <button class="btn" id="assign_button8" type="button" value="button8">unassigned</button>',
                          '  </div>',
                          ' </div>',
                          '</div>',
                         ].join("\n") );

        // Add buttons in front of the existing #inputform
        buttons.insertBefore('#inputform');
        $('#inputform').addClass('split split-vertical');

        Split(['#buttons','#inputform'], {
            direction: 'vertical',
            sizes: [50,50],
            gutterSize: 4,
            minSize: 150,
        });
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
            assignButton( e.data, $('#inputfield').val() );
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

    // Public

    //
    // Handle the HotButtons part of a Webclient_Options event
    var onGotOptions = function(args, kwargs) {
        console.log( args );
        console.log( kwargs );
        if( kwargs['HotButtons'] ) {
            var buttons = kwargs['HotButtons'];
            $.each( buttons, function( key, value ) {
                assignButton(key, value);
            });
        }
    }

    //
    // Initialize me
    var init = function() {

        // Add buttons to the UI
        addButtonsUI();

        // assign button cache
        for( var n=0; n<num_buttons; n++ ) { 
            command_cache[n] = "unassigned";
            $("#assign_button"+n).click( n, hotButtonClicked );
        }

        console.log("HotButtons Plugin Initialized.");
    }

    return {
        init: init,
        onGotOptions: onGotOptions,
    }
})());
