/*
 *
 * Golden Layout plugin
 *
 */
let goldenlayout = (function () {

    var myLayout;
    var knownTypes = ["all", "untagged"];
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

        var state = JSON.stringify( myLayout.toConfig() );
        localStorage.setItem( "evenniaGoldenLayoutSavedState", state );
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
    var routeMsg = function (textDiv, txt, updateMethod) {
        if ( updateMethod === "replace" ) {
            textDiv.html(txt);
        } else if ( updateMethod === "append" ) {
            textDiv.append(txt);
        } else {  // line feed
            textDiv.append("<div class='out'>" + txt + "</div>");
        }
        let scrollHeight = textDiv.prop("scrollHeight");
        let clientHeight = textDiv.prop("clientHeight");
        textDiv.scrollTop( scrollHeight - clientHeight );
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
    // Public
    //


    //
    //
    var onKeydown = function(evnt) {
        var renamebox = document.getElementById("renamebox"); 
        if( renamebox ) {
            return true;
        }
        return false;
    }


    //
    //
    var onText = function (args, kwargs) {
        // If the message is not itself tagged, we"ll assume it
        // should go into any panes with "all" and "untagged" set
        var msgtype = "untagged";

        if ( kwargs && "type" in kwargs ) {
            msgtype = kwargs["type"];
            if ( ! knownTypes.includes(msgtype) ) {
                // this is a new output type that can be mapped to panes
                knownTypes.push(msgtype);
                untagged.push(msgtype);
            }
        }

        let messageDelivered = false;
        let components = myLayout.root.getItemsByType("component");

        components.forEach( function (component) {
            if( component.hasId("inputComponent") ) { return; } // ignore the input component

            let textDiv = component.container.getElement().children(".content");
            let attrTypes = textDiv.attr("types");
            let paneTypes = attrTypes ? attrTypes.split(" ") : [];
            let updateMethod = textDiv.attr("updateMethod");
            let txt = args[0];

            // is this message type listed in this pane"s types (or is this pane catching "all")
            if( paneTypes.includes(msgtype) || paneTypes.includes("all") ) {
                routeMsg( textDiv, txt, updateMethod );
                messageDelivered = true;
            }

            // is this pane catching "upmapped" messages?
            // And is this message type listed in the untagged types array?
            if( paneTypes.includes("untagged") && untagged.includes(msgtype) ) {
                routeMsg( textDiv, txt, updateMethod );
                messageDelivered = true;
            }
        });

        if ( messageDelivered ) {
            return true;
        }
        // unhandled message
        return false;
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
    // required Init me
    var init = function (options) {
        // Set up our GoldenLayout instance built off of the default main-sub div
        var savedState = localStorage.getItem( "evenniaGoldenLayoutSavedState" );
        var mainsub = document.getElementById("main-sub");

        if( savedState !== null ) {
            // Overwrite the global-variable configuration with the version from localstorage
            window.goldenlayout_config = JSON.parse( savedState );
        }

        myLayout = new GoldenLayout( window.goldenlayout_config, mainsub );

        $("#prompt").remove();       // remove the HTML-defined prompt div
        $("#inputcontrol").remove(); // remove the cluttered, HTML-defined input divs

        // register our component and replace the default messagewindow with the Main component
        myLayout.registerComponent( "Main", function (container, componentState) {
            let main = $("#messagewindow").addClass("content");
            initComponent(main, container, componentState, "untagged", "newlines" );
        });

        // register our new input component
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

        myLayout.registerComponent( "evennia", function (container, componentState) {
            let div = $("<div class='content'></div>");
            initComponent(div, container, componentState, "all", "newlines");
            container.on("destroy", calculateUntaggedTypes);
        });
    }


    return {
        init: init,
        postInit: postInit,
        onKeydown: onKeydown,
        onText: onText,
        getGL: function () { return myLayout; },
        addKnownType: function (newtype) { knownTypes.push(newtype); },
    }
}());
window.plugin_handler.add("goldenlayout", goldenlayout);
