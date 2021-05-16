/*
 * Options 2.0
 * REQUIRES: goldenlayout.js
 */
let options2 = (function () {

    var optionsContainer = null ;

    //
    // When the user changes a setting from the interface
    var onOptionCheckboxChanged = function (evnt) {
        var name = $(evnt.target).data("setting");
        var value = $(evnt.target).is(":checked");
        options[name] = value;
        Evennia.msg("webclient_options", [], options);
    }

    //
    // Callback to display our basic OptionsUI
    var onOptionsUI = function (parentdiv) {
        var checked;

        checked = options["gagprompt"] ? "checked='checked'" : "";
        var gagprompt   = $( [ "<label>",
                               "<input type='checkbox' data-setting='gagprompt' " + checked + "'>",
                               " Don't echo prompts to the main text area",
                               "</label>"
                             ].join("") );

        checked = options["notification_popup"] ? "checked='checked'" : "";
        var notifypopup = $( [ "<label>",
                               "<input type='checkbox' data-setting='notification_popup' " + checked + "'>",
                               " Popup notification",
                               "</label>"
                             ].join("") );

        checked = options["notification_sound"] ? "checked='checked'" : "";
        var notifysound = $( [ "<label>",
                               "<input type='checkbox' data-setting='notification_sound' " + checked + "'>",
                               " Play a sound",
                               "</label>"
                             ].join("") );

        gagprompt.on("change", onOptionCheckboxChanged);
        notifypopup.on("change", onOptionCheckboxChanged);
        notifysound.on("change", onOptionCheckboxChanged);

        parentdiv.append(gagprompt);
        parentdiv.append(notifypopup);
        parentdiv.append(notifysound);
    }


    // handler for the "Options" button
    var onOpenCloseOptions = function () {
        var optionsComponent = {
            title: "Options",
            type: "component",
            componentName: "options",
            componentState: {
            },
        };

        // Create a new GoldenLayout tab filled with the optionsComponent above
        var myLayout = window.plugins["goldenlayout"].getGL();
        if( ! optionsContainer ) {
            // open new optionsComponent
            var main = myLayout.root.getItemsByType("stack")[0].getActiveContentItem();

            myLayout.on( "tabCreated", function( tab ) {
                if( tab.contentItem.componentName == "options" ) {
                    tab
                    .closeElement
                    .off("click")
                    .click( function () {
                        optionsContainer = null;
                        tab.contentItem.remove();
                        window.plugins["default_in"].setKeydownFocus(true);
                    });
                    optionsContainer = tab.contentItem;
                }
            });
            main.parent.addChild( optionsComponent );

            window.plugins["default_in"].setKeydownFocus(false);
        } else {
            optionsContainer.remove();
            optionsContainer = null;
        }
    }

    // Public

    //
    // Called when options settings are sent from server
    var onGotOptions = function (args, kwargs) {
        var addKnownType = window.plugins["goldenlayout"].addKnownType;

        $.each(kwargs, function(key, value) {
            options[key] = value;

            // for "available_server_tags", addKnownType for each value ["tag1", "tag2", ... ]
            if( (key === "available_server_tags") && addKnownType ) {
                $.each( value, addKnownType );
            }
        });
    }

    //
    // Create and register the "options" golden-layout component
    var onLayoutChanged = function () {
        var myLayout = window.plugins["goldenlayout"].getGL();

        myLayout.registerComponent( "options", function (container, componentState) {
            var plugins = window.plugins;
            optionsContainer = container.getElement();

            // build the buttons
            var div = $("<div class='accordion' style='overflow-y:scroll; height:inherit;'>");

            for( let plugin in plugins ) {
                if( "onOptionsUI" in plugins[plugin] ) {
                    var card = $("<div class='card'>");
                    var body = $("<div>");

                    plugins[plugin].onOptionsUI( body );

                    card.append(body); 
                    card.appendTo( div );
                }
            }

            div.appendTo( optionsContainer );
        });
    }

    //
    // Called when the user logged in
    var onLoggedIn = function (args, kwargs) {
        Evennia.msg("webclient_options", [], {});
    }

    //
    // Display a "prompt" command from the server
    var onPrompt = function (args, kwargs) {
        // display the prompt in the output window if gagging is disabled
        if( options["gagprompt"] == false ) {
            plugin_handler.onText(args, kwargs);
        }

        // don't claim this Prompt as completed.
        return false;
    }

    //
    //
    var init = function() {
        var optionsbutton = $("<button id='optionsbutton'>&#x2699;</button>");
        $("#toolbar").append( optionsbutton );
        options["gagprompt"] = true;
        options["notification_popup"] = true;
        options["notification_sound"] = true;
    }

    //
    //
    var postInit = function() {
        // Are we using GoldenLayout?
        if( window.plugins["goldenlayout"] ) {
            onLayoutChanged();

            $("#optionsbutton").bind("click", onOpenCloseOptions);
        }
        console.log("Options 2.0 Loaded");
    }

    return {
        init: init,
        postInit: postInit,
        onGotOptions: onGotOptions,
        onLayoutChanged: onLayoutChanged,
        onLoggedIn: onLoggedIn,
        onOptionsUI: onOptionsUI,
        onPrompt: onPrompt,
        onOptionCheckboxChanged: onOptionCheckboxChanged,
        onOpenCloseOptions: onOpenCloseOptions,
    }
})();
window.plugin_handler.add("options2", options2);
