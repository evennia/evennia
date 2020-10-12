/*
 *
 * Golden Layout plugin
 *
 */
let goldenlayout = (function () {

    var myLayout; // The actively used GoldenLayout API object.

    var evenniaGoldenLayouts = {}; // key/value storage Object for each selectable layout.
    var activeLayoutName = "default"; // The object key of the active evenniaGoldenLayout

    var knownTypes = ["all", "untagged", "testing"];
    var untagged = [];

    var newTabConfig = {
        title: "Untitled",
        type: "component",
        componentName: "evennia",
        tooltip: "Click and drag tabs to make new panes",
        componentState: {
            types: "all",
            updateMethod: "newlines",
        },
    };

    var newInputConfig = {
        title: "input",
        type: "component",
        componentName: "input",
        id: "inputComponent",
    };

    // helper function:  filter vals out of array
    function filter (vals, array) {
        if( Array.isArray( vals ) && Array.isArray( array ) ) {
            let tmp = array.slice();
            vals.forEach( function (val) {
                while( tmp.indexOf(val) > -1 ) {
                    tmp.splice( tmp.indexOf(val), 1 );
                }
            });
            return tmp;
        }
        // pass along whatever we got, since our arguments aren't right.
        return array;
    }


    //
    // Calculate all knownTypes minus the "all" type,
    //     then filter out all types that have been mapped to a pane.
    var calculateUntaggedTypes = function () {
        // set initial untagged list
        untagged = filter( ["all", "untagged"], knownTypes);
        // for each .content pane
        $(".content").each( function () {
            let types = $(this).attr("types");
            if ( typeof types !== "undefined" ) {
                let typesArray = types.split(" ");
                // add our types to known types so that the onText function don't add them to untagged later
                knownTypes = Array.from(new Set([...knownTypes, ...typesArray]));
                // remove our types from the untagged array                
                untagged = filter( typesArray, untagged );
            }
        });
    }


    //
    //
    var closeRenameDropdown = function () {
        let content = $("#renamebox").parent().parent().parent().parent()[0];
        let title = $("#renameboxin").val();

        let components = myLayout.root.getItemsByType("component");

        components.forEach( function (component) {
           let element = component.tab.header.parent.element[0];
           if( (element === content) && (component.tab.isActive) ) {
               component.setTitle( title );
           }
        });

        myLayout.emit("stateChanged");
        $("#renamebox").remove();
        window.plugins["default_in"].setKeydownFocus(true);
    }


    //
    //
    var closeTypelistDropdown = function () {
        let content = $("#typelist").parent().find(".content");
        let checkboxes = $("#typelist :input");

        let types = [];
        checkboxes.each( function (idx) {
            if( $(checkboxes[idx]).prop("checked") ) {
                types.push( $(checkboxes[idx]).val() );
            }
        });

        content.attr("types", types.join(" "));
        myLayout.emit("stateChanged");

        calculateUntaggedTypes();
        $("#typelist").remove();
    }


    //
    //
    var closeUpdatelistDropdown = function () {
        let content = $("#updatelist").parent().find(".content");
        let value   = $("input[name=upmethod]:checked").val();

        content.attr("updateMethod", value );
        myLayout.emit("stateChanged");
        $("#updatelist").remove();
    }


    //
    // Handle the renameDropdown
    var renameDropdown = function (evnt) {
        let element = $(evnt.data.contentItem.element);
        let content = element.find(".content");
        let title   = evnt.data.contentItem.config.title;
        let renamebox = document.getElementById("renamebox");

        // check that no other dropdown is open
        if( document.getElementById("typelist") ) {
            closeTypelistDropdown();
        }

        if( document.getElementById("updatelist") ) {
            closeUpdatelistDropdown();
        }

        if( !renamebox ) {
            renamebox = $("<div id='renamebox'>");
            renamebox.append("<input type='textbox' id='renameboxin' value='"+title+"'>");
            renamebox.insertBefore( content );
            window.plugins["default_in"].setKeydownFocus(false);
        } else {
            closeRenameDropdown();
        }
    }


    //
    //
    var onSelectTypesClicked = function (evnt) {
        let element = $(evnt.data.contentItem.element);
        let content = element.find(".content");
        let selectedTypes = content.attr("types");
        let menu = $("<div id='typelist'>");
        let div = $("<div class='typelistsub'>");

        if( selectedTypes ) {
            selectedTypes = selectedTypes.split(" ");
        }
        knownTypes.forEach( function (itype) {
            let choice;
            if( selectedTypes && selectedTypes.includes(itype) ) {
                choice = $("<label><input type='checkbox' value='"+itype+"' checked='checked'/>"+itype+"</label>");
            } else {
                choice = $("<label><input type='checkbox' value='"+itype+"'/>"+itype+"</label>");
            }
            choice.appendTo(div);
        });
        div.appendTo(menu);

        element.prepend(menu);
    }


    //
    // Handle the typeDropdown
    var typeDropdown = function (evnt) {
        let typelist = document.getElementById("typelist");

        // check that no other dropdown is open
        if( document.getElementById("renamebox") ) {
            closeRenameDropdown();
        }

        if( document.getElementById("updatelist") ) {
            closeUpdatelistDropdown();
        }

        if( !typelist ) {
            onSelectTypesClicked(evnt);
        } else {
            closeTypelistDropdown();
        }
    }


    //
    //
    var onUpdateMethodClicked = function (evnt) {
        let element = $(evnt.data.contentItem.element);
        let content = element.find(".content");
        let updateMethod = content.attr("updateMethod");
        let nlchecked = (updateMethod === "newlines") ? "checked='checked'" : "";
        let apchecked = (updateMethod === "append")   ? "checked='checked'" : "";
        let rpchecked = (updateMethod === "replace")  ? "checked='checked'" : "";

        let menu = $("<div id='updatelist'>");
        let div = $("<div class='updatelistsub'>");

        let newlines = $("<label><input type='radio' name='upmethod' value='newlines' "+nlchecked+"/>Newlines</label>");
        let append   = $("<label><input type='radio' name='upmethod' value='append' "+apchecked+"/>Append</label>");
        let replace  = $("<label><input type='radio' name='upmethod' value='replace' "+rpchecked+"/>Replace</label>");

        newlines.appendTo(div);
        append.appendTo(div);
        replace.appendTo(div);

        div.appendTo(menu);

        element.prepend(menu);
    }


    //
    // Handle the updateDropdown
    var updateDropdown = function (evnt) {
        let updatelist = document.getElementById("updatelist");

        // check that no other dropdown is open
        if( document.getElementById("renamebox") ) {
            closeRenameDropdown();
        }

        if( document.getElementById("typelist") ) {
            closeTypelistDropdown();
        }

        if( !updatelist ) {
            onUpdateMethodClicked(evnt);
        } else {
            closeUpdatelistDropdown();
        }
    }


    //
    //
    var onActiveTabChange = function (tab) {
        let renamebox  = document.getElementById("renamebox");
        let typelist   = document.getElementById("typelist");
        let updatelist = document.getElementById("updatelist");

        if( renamebox ) {
            closeRenameDropdown();
        }

        if( typelist ) {
            closeTypelistDropdown();
        }

        if( updatelist ) {
            closeUpdatelistDropdown();
        }
    }


    //
    //
    var resetUI = function (newLayout) {
        var mainsub = document.getElementById("main-sub");

        // rebuild the original HTML stacking
        var messageDiv = $("#messagewindow").detach();
        messageDiv.prependTo( mainsub );

        // out with the old
        myLayout.destroy();

        // in with the new
        myLayout = new GoldenLayout( newLayout, mainsub );

        // re-register our main, input and generic evennia components.
        registerComponents( myLayout );

        // call all other plugins to give them a chance to registerComponents.
        for( let plugin in window.plugins ) {
            if( "onLayoutChanged" in window.plugins[plugin] ) {
                window.plugins[plugin].onLayoutChanged();
            }
        }

        // finish the setup and actually start GoldenLayout
        myLayout.init();

        // work out which types are untagged based on our pre-configured layout
        calculateUntaggedTypes();

        // Set the Event handler for when the client window changes size
        $(window).bind("resize", scrollAll);

        // Set Save State callback
        myLayout.on( "stateChanged", onStateChanged );
    }


    //
    //
    var onSwitchLayout = function (evnt) {
        // get the new layout name from the select box
        var name = $('#layoutInput').val();

        // check to see if the layout is in the list of known layouts
        if( name in evenniaGoldenLayouts ) {
            console.log( evenniaGoldenLayouts );

            var newLayout = evenniaGoldenLayouts[name];
            activeLayoutName = name;

            // pull the trigger
            resetUI( newLayout );
        }
    }


    //
    //
    var onSaveLayout = function (evnt) {
        // get the name from the select box
        var name = $('#layoutName').val();
        var input = $('#layoutInput');

        if( name === "" ) { return; } // Can't save without a valid name

        // Is this name new or pre-existing?
        if( !(name in evenniaGoldenLayouts) ) {
            // add the new evenniaGoldenLayout to the listed dropdown options
            var option = $('<option value="'+name+'">'+name+'</option>');
            input.append(option);
        }

        // store the current layout to the local list of layouts
        evenniaGoldenLayouts[ name ] = myLayout.toConfig();
        activeLayoutName = name;

        // upload it to the server
        if( Evennia.isConnected() && myLayout.isInitialised ) {
            window.options["webclientActiveLayout"] = name;
            window.options["webclientLayouts"] = JSON.stringify( evenniaGoldenLayouts );
            console.log("Saving layout to server...");
            Evennia.msg("webclient_options", [], window.options);
        }
    }


    //
    // Save the GoldenLayout state to localstorage whenever it changes.
    var onStateChanged = function () {
        let components = myLayout.root.getItemsByType("component");
        components.forEach( function (component) {
            if( component.hasId("inputComponent") ) { return; } // ignore input components

            let textDiv = component.container.getElement().children(".content");
            let types = textDiv.attr("types");
            let updateMethod = textDiv.attr("updateMethod");
            component.container.extendState({ "types": types, "updateMethod": updateMethod });
        });

        // update localstorage
        localStorage.setItem( "evenniaGoldenLayoutSavedState", JSON.stringify(myLayout.toConfig()) );
        localStorage.getItem( "evenniaGoldenLayoutSavedStateName", JSON.stringify( activeLayoutName ) );
    }


    //
    //
    var onTabCreate = function (tab) {
        //HTML for the typeDropdown
        let renameDropdownControl = $("<span class='lm_title' style='font-size: 1.5em;width: 0.5em;'>&#129170;</span>");
        let typeDropdownControl   = $("<span class='lm_title' style='font-size: 1.0em;width: 1em;'>&#11201;</span>");
        let updateDropdownControl = $("<span class='lm_title' style='font-size: 1.0em;width: 1em;'>&#11208;</span>");
        let splitControl          = $("<span class='lm_title' style='font-size: 1.5em;width: 1em;'>+</span>");
        // track dropdowns when the associated control is clicked
        renameDropdownControl.click( tab, renameDropdown ); 

        typeDropdownControl.click( tab, typeDropdown );

        updateDropdownControl.click( tab, updateDropdown );

        // track adding a new tab
        splitControl.click( tab, function (evnt) {
            evnt.data.header.parent.addChild( newTabConfig );
        });

        // Add the typeDropdown to the header
        tab.element.prepend( renameDropdownControl );
        tab.element.append(  typeDropdownControl );
        tab.element.append(  updateDropdownControl );
        tab.element.append(  splitControl );

        if( tab.contentItem.config.componentName === "Main" ) {
            tab.element.prepend( $("#optionsbutton").clone(true).addClass("lm_title") );
        }

        tab.header.parent.on( "activeContentItemChanged", onActiveTabChange );
    }


    //
    //
    var onInputCreate = function (tab) {
        //HTML for the typeDropdown
        let splitControl          = $("<span class='lm_title' style='font-size: 1.5em;width: 1em;'>+</span>");

        // track adding a new tab
        splitControl.click( tab, function (evnt) {
            evnt.data.header.parent.addChild( newInputConfig );
        });

        // Add the typeDropdown to the header
        tab.element.append(  splitControl );

        tab.header.parent.on( "activeContentItemChanged", onActiveTabChange );
    }

    //
    //
    var scrollAll = function () {
        let components = myLayout.root.getItemsByType("component");
        components.forEach( function (component) {
            if( component.hasId("inputComponent") ) { return; } // ignore input components

            let textDiv = component.container.getElement().children(".content");
            let scrollHeight = textDiv.prop("scrollHeight");
            let clientHeight = textDiv.prop("clientHeight");
            textDiv.scrollTop( scrollHeight - clientHeight );
        });
        myLayout.updateSize();
    }


    //
    //
    var initComponent = function (div, container, state, defaultTypes, updateMethod) {
        // set this container"s content div types attribute
        if( state ) {
            div.attr("types", state.types);
            div.attr("updateMethod", state.updateMethod);
        } else {
            div.attr("types", defaultTypes);
            div.attr("updateMethod", updateMethod);
        }
        div.appendTo( container.getElement() );
        container.on("tab", onTabCreate);
    }


    //
    //
    var registerComponents = function (myLayout) {

        // register our component and replace the default messagewindow with the Main component
        myLayout.registerComponent( "Main", function (container, componentState) {
            let main = $("#messagewindow").addClass("content");
            initComponent(main, container, componentState, "untagged", "newlines" );
        });

        // register our input component
        myLayout.registerComponent( "input", function (container, componentState) {
            var promptfield = $("<div class='prompt'></div>");
            var formcontrol = $("<textarea type='text' class='inputfield form-control'></textarea>");
            var button = $("<button type='button' class='inputsend'>&gt;</button>");
 
            var inputfield = $("<div class='inputfieldwrapper'>")
                                .append( button )
                                .append( formcontrol );

            $("<div class='inputwrap'>")
                .append( promptfield )
                .append( inputfield )
                .appendTo( container.getElement() );

            button.bind("click", function (evnt) {
                // focus our textarea
                $( $(evnt.target).siblings(".inputfield")[0] ).focus();
                // fake a carriage return event
                var e = $.Event("keydown");
                e.which = 13;
                $( $(evnt.target).siblings(".inputfield")[0] ).trigger(e);
            });

            container.on("tab", onInputCreate);
        });

        // register the generic "evennia" component
        myLayout.registerComponent( "evennia", function (container, componentState) {
            let div = $("<div class='content'></div>");
            initComponent(div, container, componentState, "all", "newlines");
            container.on("destroy", calculateUntaggedTypes);
        });
    }


    //
    // Public
    //

    //
    // helper accessor for other plugins to add new known-message types
    var addKnownType = function (newtype) {
        if( knownTypes.includes(newtype) == false ) {
            knownTypes.push(newtype);
        }
    }


    //
    // Add new HTML message to an existing Div pane, while
    // honoring the pane's updateMethod and scroll state, etc.
    //
    var addMessageToPaneDiv = function (textDiv, message) {
        let atBottom = false;
        let updateMethod = textDiv.attr("updateMethod");

        if ( updateMethod === "replace" ) {
            textDiv.html(message);
        } else if ( updateMethod === "append" ) {
            textDiv.append(message);
        } else {  // line feed
            textDiv.append("<div class='out'>" + message + "</div>");
        }

        // Calculate the scrollback state.
        //
        // This check helps us avoid scrolling to the bottom when someone is
        // manually scrolled back, trying to read their backlog.
        // Auto-scrolling would force them to re-scroll to their previous scroll position.
        // Which, on fast updating games, destroys the utility of scrolling entirely.
        //
        //if( textDiv.scrollTop === (textDiv.scrollHeight - textDiv.offsetHeight) ) {
            atBottom = true;
        //}

        // if we are at the bottom of the window already, scroll to display the new content
        if( atBottom ) {
            let scrollHeight = textDiv.prop("scrollHeight");
            let clientHeight = textDiv.prop("clientHeight");
            textDiv.scrollTop( scrollHeight - clientHeight );
        }
    }


    //
    // returns an array of pane divs that the given message should be sent to
    //
    var routeMessage = function (args, kwargs) {
        // If the message is not itself tagged, we"ll assume it
        // should go into any panes with "all" and "untagged" set
        var divArray = [];
        var msgtype = "untagged";

        if ( kwargs && "type" in kwargs ) {
            msgtype = kwargs["type"];
            if ( ! knownTypes.includes(msgtype) ) {
                // this is a new output type that can be mapped to panes
                knownTypes.push(msgtype);
                untagged.push(msgtype);
            }
        }

        let components = myLayout.root.getItemsByType("component");
        components.forEach( function (component) {
            if( component.hasId("inputComponent") ) { return; } // ignore input components

            let destDiv = component.container.getElement().children(".content");
            let attrTypes = destDiv.attr("types");
            let paneTypes = attrTypes ? attrTypes.split(" ") : [];

            // is this message type listed in this pane"s types (or is this pane catching "all")
            if( paneTypes.includes(msgtype) || paneTypes.includes("all") ) {
                divArray.push(destDiv);
            }

            // is this pane catching "upmapped" messages?
            // And is this message type listed in the untagged types array?
            if( paneTypes.includes("untagged") && untagged.includes(msgtype) ) {
                divArray.push(destDiv);
            }
        });

        return divArray;
    }


    //
    //
    var onGotOptions = function (args, kwargs) {
        // Reset the UI if the JSON layout sent from the server doesn't match the client's current JSON
        if( "webclientLayouts" in kwargs ) {
            console.log("Got evennia GoldenLayouts");

            evenniaGoldenLayouts = JSON.parse( kwargs["webclientLayouts"] );
        }
    }


    //
    //
    var onOptionsUI = function (parentdiv) {
        var layoutInput = $('<select id="layoutInput" class="layoutInput">');
        var layoutName  = $('<input id="layoutName" type="text" class="layoutName">');
        var saveButton  = $('<input type="button" class="savelayout" value="Save UI Layout">');

        var layouts = Object.keys( evenniaGoldenLayouts );
        for (var x = 0; x < layouts.length; x++) {
            var option = $('<option value="'+layouts[x]+'">'+layouts[x]+'</option>');
            layoutInput.append(option);
        }

        layoutInput.val( activeLayoutName ); // current selection
        layoutName.val( activeLayoutName );

        // Layout selection on-change callback
        layoutInput.on('change', onSwitchLayout);
        saveButton.on('click',  onSaveLayout);

        // add the selection dialog control to our parentdiv
        parentdiv.append('<div style="font-weight: bold">UI Layout Selection (This list may be longer after login):</div>');
        parentdiv.append(layoutInput);
        parentdiv.append(layoutName);
        parentdiv.append(saveButton);
    }


    //
    //
    var onText = function (args, kwargs) {
        // are any panes set to receive this text message?
        var divs = routeMessage(args, kwargs);

        var msgHandled = false;
        divs.forEach( function (div) {
            let txt = args[0];
            // yes, so add this text message to the target div
            addMessageToPaneDiv( div, txt );
            msgHandled = true;
        });

        return msgHandled;
    }


    //
    //
    var postInit = function () {
        // finish the setup and actually start GoldenLayout
        myLayout.init();

        // work out which types are untagged based on our pre-configured layout
        calculateUntaggedTypes();

        // Set the Event handler for when the client window changes size
        $(window).bind("resize", scrollAll);

        // Set Save State callback
        myLayout.on( "stateChanged", onStateChanged );
    }


    //
    // required Init
    var init = function (options) {
        // Set up our GoldenLayout instance built off of the default main-sub div
        var savedState = localStorage.getItem( "evenniaGoldenLayoutSavedState" );
        var activeName = localStorage.getItem( "evenniaGoldenLayoutSavedStateName" );
        var mainsub = document.getElementById("main-sub");

        // pre-load the evenniaGoldenLayouts with the hard-coded default
        evenniaGoldenLayouts[ "default" ] = window.goldenlayout_config;

        if( activeName !== null ) {
            activeLayoutName = activeName;
        }

        if( savedState !== null ) {
            // Overwrite the global-variable configuration from 
            //     webclient/js/plugins/goldenlayout_default_config.js
            //         with the version from localstorage
            evenniaGoldenLayouts[ activeLayoutName ] = JSON.parse( savedState );
        }

        myLayout = new GoldenLayout( evenniaGoldenLayouts[activeLayoutName], mainsub );

        $("#prompt").remove();       // remove the HTML-defined prompt div
        $("#inputcontrol").remove(); // remove the cluttered, HTML-defined input divs

        registerComponents( myLayout );
    }

    return {
        init: init,
        postInit: postInit,
        onGotOptions: onGotOptions,
        onOptionsUI: onOptionsUI,
        onText: onText,
        getGL: function () { return myLayout; },
        addKnownType: addKnownType,
        onTabCreate: onTabCreate,
        routeMessage: routeMessage,
        addMessageToPaneDiv: addMessageToPaneDiv,
    }
}());
window.plugin_handler.add("goldenlayout", goldenlayout);
