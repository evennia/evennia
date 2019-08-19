/*
 *
 * Evennia Options GUI plugin
 *
 * This code deals with all of the UI and events related to Options.
 *
 */
let options_plugin = (function () {
    //
    // addOptionsUI
    var addOptionsUI = function () {
        var content = [ // TODO  dynamically create this based on the options{} hash
            '<label><input type="checkbox" data-setting="gagprompt" value="value">Don\'t echo prompts to the main text area</label>',
            '<br />',
            '<label><input type="checkbox" data-setting="helppopup" value="value">Open help in popup window</label>',
            '<br />',
            '<hr />',
            '<label><input type="checkbox" data-setting="notification_popup" value="value">Popup notification</label>',
            '<br />',
            '<label><input type="checkbox" data-setting="notification_sound" value="value">Play a sound</label>',
            '<br />',
        ].join("\n");

        // Create a new options Dialog
        plugins['popups'].createDialog( 'optionsdialog', 'Options', content );
    }

    //
    // addHelpUI
    var addHelpUI = function () {
        // Create a new Help Dialog
        plugins['popups'].createDialog( 'helpdialog', 'Help', "" );
    }

    // addToolbarButton
    var addToolbarButton = function () {
       var optionsbutton = $( [
           '<button id="optionsbutton" type="button" aria-haspopup="true" aria-owns="#optionsdialog">',
           '&#x2699;',
           '<span class="sr-only sr-only-focusable">Settings</span>',
           '</button>',
           ].join("") );
       $('#toolbar').append( optionsbutton );
    }

    //
    // Opens the options dialog
    var doOpenOptions = function () {
        if (!Evennia.isConnected()) {
            alert("You need to be connected.");
            return;
        }

        plugins['popups'].togglePopup("#optionsdialog");
    }

    //
    // When the user changes a setting from the interface
    var onOptionCheckboxChanged = function () {
        var name = $(this).data("setting");
        var value = this.checked;

        var changedoptions = {};
        changedoptions[name] = value;
        Evennia.msg("webclient_options", [], changedoptions);

        options[name] = value;
    }

    // Public functions

    //
    // onKeydown check for 'ESC' key.
    var onKeydown = function (event) {
        var code = event.which;

        if (code === 27) { // Escape key
            if ($('#helpdialog').is(':visible')) {
                plugins['popups'].closePopup("#helpdialog");
                return true;
            }
            if ($('#optionsdialog').is(':visible')) {
                plugins['popups'].closePopup("#optionsdialog");
                return true;
            }
        }
        return false;
    }

    //
    // Called when options settings are sent from server
    var onGotOptions = function (args, kwargs) {
        options = kwargs;

        $.each(kwargs, function(key, value) {
            var elem = $("[data-setting='" + key + "']");
            if (elem.length === 0) {
                console.log("Could not find option: " + key);
                console.log(args);
                console.log(kwargs);
            } else {
                elem.prop('checked', value);
            };
        });
    }

    //
    // Called when the user logged in
    var onLoggedIn = function (args, kwargs) {
        $('#optionsbutton').removeClass('hidden');
        Evennia.msg("webclient_options", [], {});
    }

    //
    // Display a "prompt" command from the server
    var onPrompt = function (args, kwargs) {
        // also display the prompt in the output window if gagging is disabled
        if (("gagprompt" in options) && (!options["gagprompt"])) {
            plugin_handler.onText(args, kwargs);
        }

        // don't claim this Prompt as completed.
        return false;
    }

    //
    // Make sure to close any dialogs on connection lost
    var onConnectionClose = function () {
        $('#optionsbutton').addClass('hidden');
        plugins['popups'].closePopup("#optionsdialog");
        plugins['popups'].closePopup("#helpdialog");
    }

    //
    // Make sure to close any dialogs on connection lost
    var onText = function (args, kwargs) {
        // is helppopup set? and if so, does this Text have type 'help'?
        if ('helppopup' in options && options['helppopup'] ) {
            if (kwargs && ('type' in kwargs) && (kwargs['type'] == 'help') ) {
                $('#helpdialogcontent').prepend('<div>'+ args + '</div>');
                plugins['popups'].togglePopup("#helpdialog");
                return true;
            }
        }

        return false;
    }

    //
    // Register and init plugin
    var init = function () {
        // Add GUI components
        addOptionsUI();
        addHelpUI();

        // Add Options toolbar button.
        addToolbarButton();

        // Pressing the settings button
        $("#optionsbutton").bind("click", doOpenOptions);

        // Checking a checkbox in the settings dialog
        $("[data-setting]").bind("change", onOptionCheckboxChanged);

        console.log('Options Plugin Initialized.');
    }

    return {
        init: init,
        onKeydown: onKeydown,
        onLoggedIn: onLoggedIn,
        onGotOptions: onGotOptions,
        onPrompt: onPrompt,
        onConnectionClose: onConnectionClose,
        onText: onText,
    }
})()
plugin_handler.add('options', options_plugin);
