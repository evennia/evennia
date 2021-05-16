/*
 * IFrame plugin
 * REQUIRES: goldenlayout.js
 */
let iframe = (function () {

    var url = window.location.origin;

    //
    // Create iframe component
    var createIframeComponent = function () {
        var myLayout = window.plugins["goldenlayout"].getGL();

        myLayout.registerComponent( "iframe", function (container, componentState) {
            // build the iframe
            var div = $('<iframe src="' + url + '">');
            div.css("width", "100%");
            div.css("height", "inherit");
            div.appendTo( container.getElement() );
        });
    }


    // handler for the "iframe" button
    var onOpenIframe = function () {
        var iframeComponent = {
            title: url,
            type: "component",
            componentName: "iframe",
            componentState: {
            },
        };

        // Create a new GoldenLayout tab filled with the iframeComponent above
        var myLayout = window.plugins["goldenlayout"].getGL();
        var main = myLayout.root.getItemsByType("stack")[0].getActiveContentItem();
        main.parent.addChild( iframeComponent ); 
    }

    // Public

    var onOptionsUI = function (parentdiv) {
        var iframebutton = $('<input type="button" value="Open Game Website" />');
	iframebutton.on('click', onOpenIframe);

        parentdiv.append( '<div style="font-weight: bold">Restricted Browser-in-Browser:</div>' );
        parentdiv.append( iframebutton );
    }

    //
    //
    var postInit = function() {
        // Are we using GoldenLayout?
        if( window.plugins["goldenlayout"] ) {
            createIframeComponent();

            $("#iframebutton").bind("click", onOpenIframe);
        }
        console.log('IFrame plugin Loaded');
    }

    return {
        init: function () {},
        postInit: postInit,
	onOptionsUI: onOptionsUI,
    }
})();
window.plugin_handler.add("iframe", iframe);
