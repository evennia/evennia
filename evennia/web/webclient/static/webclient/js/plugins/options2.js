/*
 * Options 2.0
 * REQUIRES: goldenlayout.js
 */
let options2 = (function () {

    var onGagPrompt = function () { console.log('gagprompt') }
    var onNotifyPopup = function () { console.log('notifypopup') }
    var onNotifySound = function () { console.log('notifysound') }

    var onOptionsUI = function (parentdiv) {
        var gagprompt = $('<label><input type="checkbox" data-setting="gagprompt" value="value">Don\'t echo prompts to the main text area</label>');
        var notifypopup = $('<label><input type="checkbox" data-setting="notification_popup" value="value">Popup notification</label>');
        var notifysound = $('<label><input type="checkbox" data-setting="notification_sound" value="value">Play a sound</label>');

        gagprompt.on("change", onGagPrompt);
        notifypopup.on("change", onNotifyPopup);
        notifysound.on("change", onNotifySound);

        parentdiv.append(gagprompt);
        parentdiv.append(notifypopup);
        parentdiv.append(notifysound);
    }


    //
    // Create and register the "options" golden-layout component
    var createOptionsComponent = function () {
        var myLayout = window.plugins["goldenlayout"].getGL();

        myLayout.registerComponent( "options", function (container, componentState) {
            var plugins = window.plugins;

            // build the buttons
            var div = $("<div class='accordion' style='overflow-y:scroll; height:inherit;'>");

            for( let plugin in plugins ) {
                if( 'onOptionsUI' in plugins[plugin] ) {
                    var card = $("<div class='card'>");
                    var body = $("<div>");

                    plugins[plugin].onOptionsUI( body );

                    card.append(body); 
                    card.appendTo( div );
                }
            }

            div.appendTo( container.getElement() );
        });
    }


    // handler for the "Options" button
    var onOpenOptions = function () {
        var optionsComponent = {
            title: "Options",
            type: "component",
            componentName: "options",
            componentState: {
            },
        };

        // Create a new GoldenLayout tab filled with the optionsComponent above
        var myLayout = window.plugins["goldenlayout"].getGL();
        var main = myLayout.root.getItemsByType("stack")[0].getActiveContentItem();
        main.parent.addChild( optionsComponent ); 
    }

    // Public

    //
    // Handle the Webclient_Options event
    var onGotOptions = function(args, kwargs) {
        // Pressing the settings button
    }

    var init = function() {
        var optionsbutton = $('<button id="optionsbutton">&#x2699;</button>');
        $('#toolbar').append( optionsbutton );
        // Pressing the settings button
    }

    //
    //
    var postInit = function() {
        // Are we using GoldenLayout?
        if( window.plugins["goldenlayout"] ) {
            createOptionsComponent();

            $("#optionsbutton").bind("click", onOpenOptions);
        }
        console.log('Options2 Loaded');
    }

    return {
        init: init,
        postInit: postInit,
        onGotOptions: onGotOptions,
        onOptionsUI: onOptionsUI,
    }
})();
window.plugin_handler.add("options2", options2);
