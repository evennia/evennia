/*
 *
 * Golden Layout plugin
 *
 */
plugin_handler.add('goldenlayout', (function () {

    var myLayout;
    var input_component = null;
    var known_types = ['all', 'untagged'];
    var untagged = [];

    var config = {
        content: [{
            type: 'column',
            content: [{
                type: 'row',
                content: [{
                    type: 'column',
                    content: [{
                        type: 'component',
                        componentName: 'Main',
                        isClosable: false,
                        tooltip: 'Main - drag to desird position.',
                        componentState: {
                            types: 'untagged',
                            update_method: 'newlines',
                        },
                    }]
                }],
            }, {
                type: 'component',
                componentName: 'input',
                id: 'inputComponent',
                height: 12,
                tooltip: 'Input - The last input in the layout is always the default.',
            }, {
                type: 'component',
                componentName: 'input',
                id: 'inputComponent',
                height: 12,
                isClosable: false,
                tooltip: 'Input - The last input in the layout is always the default.',
            }]
        }]
    };


    var newTabConfig = {
        title: 'Untitled',
        type: 'component',
        componentName: 'evennia',
        componentState: {
            types: 'all',
            update_method: 'newlines',
        },
    };

    var newInputConfig = {
        title: 'input',
        type: 'component',
        componentName: 'input',
        id: 'inputComponent',
    };

    // helper function:  filter vals out of array
    function filter (vals, array) {
        let tmp = array.slice();
        for (let i=0; i<vals.length; i++) {
            let val = vals[i];
            while( tmp.indexOf(val) > -1 ) {
                tmp.splice( tmp.indexOf(val), 1 );
            }
        }
        return tmp;
    }


    //
    // Calculate all known_types minus the 'all' type,
    //     then filter out all types that have been mapped to a pane.
    var calculateUntaggedTypes = function () {
        // set initial untagged list
        untagged = filter( ['all', 'untagged'], known_types);
        // for each .content pane
        $('.content').each( function () {
            let types = $(this).attr('types');
            if ( typeof types !== "undefined" ) {
               untagged = filter( types.split(' '), untagged );
            }
        });
    }


    //
    //
    var closeRenameDropdown = function () {
        let content = $('#renamebox').parent().parent().parent().parent()[0];
        let title = $('#renameboxin').val();

        let components = myLayout.root.getItemsByType('component');

        components.forEach( function (component) {
           let element = component.tab.header.parent.element[0];
           if( element == content && component.tab.isActive ) {
               component.setTitle( title );
           }
        });

        myLayout.emit('stateChanged');
        $('#renamebox').remove();
    }


    //
    // Handle the renameDropdown
    var renameDropdown = function (evnt) {
        let element = $(evnt.data.contentItem.element);
        let content = element.find('.content');
        let title   = evnt.data.contentItem.config.title;
        let renamebox = document.getElementById('renamebox');

        // check that no other dropdown is open
        if( document.getElementById('typelist') ) {
            closeTypelistDropdown();
        }

        if( document.getElementById('updatelist') ) {
            closeUpdatelistDropdown();
        }

        if( !renamebox ) {
            renamebox = $('<div id="renamebox">');
            renamebox.append('<input type="textbox" id="renameboxin" value="'+title+'">');
            renamebox.insertBefore( content );
        } else {
            closeRenameDropdown();
        }
    }


    //
    //
    var closeTypelistDropdown = function () {
        let content = $('#typelist').parent().find('.content');
        let checkboxes = $('#typelist :input');

        let types = [];
        for (let i=0; i<checkboxes.length; i++ ) {
            let box = checkboxes[i];
            if( $(box).prop('checked') ) {
                types.push( $(box).val() );
            }
        }

        content.attr('types', types.join(' '));
        myLayout.emit('stateChanged');

        calculateUntaggedTypes();
        $('#typelist').remove();
    }


    //
    //
    var onSelectTypesClicked = function (evnt) {
        let element = $(evnt.data.contentItem.element);
        let content = element.find('.content');
        let selected_types = content.attr('types');
        let menu = $('<div id="typelist">');
        let div = $('<div class="typelistsub">');

        if( selected_types ) {
            selected_types = selected_types.split(' ');
        }
        for (let i=0; i<known_types.length;i++) {
            let type = known_types[i];
            let choice;
            if( selected_types && selected_types.includes(type) ) {
                choice = $('<label><input type="checkbox" value="'+type+'" checked="checked"/>'+type+'</label>');
            } else {
                choice = $('<label><input type="checkbox" value="'+type+'"/>'+type+'</label>');
            }
            choice.appendTo(div);
        }
        div.appendTo(menu);

        element.prepend(menu);
    }


    //
    // Handle the typeDropdown
    var typeDropdown = function (evnt) {
        let typelist = document.getElementById('typelist');

        // check that no other dropdown is open
        if( document.getElementById('renamebox') ) {
            closeRenameDropdown();
        }

        if( document.getElementById('updatelist') ) {
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
    var closeUpdatelistDropdown = function () {
        let content = $('#updatelist').parent().find('.content');
        let value   = $('input[name=upmethod]:checked').val();

        content.attr('update_method', value );
        myLayout.emit('stateChanged');
        $('#updatelist').remove();
    }


    //
    //
    var onUpdateMethodClicked = function (evnt) {
        let element = $(evnt.data.contentItem.element);
        let content = element.find('.content');
        let update_method = content.attr('update_method');
        let nlchecked = (update_method == 'newlines') ? 'checked="checked"' : '';
        let apchecked = (update_method == 'append')   ? 'checked="checked"' : '';
        let rpchecked = (update_method == 'replace')  ? 'checked="checked"' : '';

        let menu = $('<div id="updatelist">');
        let div = $('<div class="updatelistsub">');

        let newlines = $('<label><input type="radio" name="upmethod" value="newlines" '+nlchecked+'/>Newlines</label>');
        let append   = $('<label><input type="radio" name="upmethod" value="append" '+apchecked+'/>Append</label>');
        let replace  = $('<label><input type="radio" name="upmethod" value="replace" '+rpchecked+'/>Replace</label>');

        newlines.appendTo(div);
        append.appendTo(div);
        replace.appendTo(div);

        div.appendTo(menu);

        element.prepend(menu);
    }


    //
    // Handle the updateDropdown
    var updateDropdown = function (evnt) {
        let updatelist = document.getElementById('updatelist');

        // check that no other dropdown is open
        if( document.getElementById('renamebox') ) {
            closeRenameDropdown();
        }

        if( document.getElementById('typelist') ) {
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
        let renamebox  = document.getElementById('renamebox');
        let typelist   = document.getElementById('typelist');
        let updatelist = document.getElementById('updatelist');

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
        let components = myLayout.root.getItemsByType('component');
        components.forEach( function (component) {
            if( component.hasId('inputComponent') ) { return; } // ignore input components

            let text_div = component.container.getElement().children('.content');
            let types = text_div.attr('types');
            let update_method = text_div.attr('update_method');
            component.container.extendState({ 'types': types, 'update_method': update_method });
        });

        var state = JSON.stringify( myLayout.toConfig() );
        localStorage.setItem( 'evenniaGoldenLayoutSavedState', state );
    }


    //
    //
    var onTabCreate = function (tab) {
        //HTML for the typeDropdown
        let renameDropdownControl = $('<span class="lm_title" style="font-size: 1em;width: 1.5em;">\u2B57</span>');
        let typeDropdownControl   = $('<span class="lm_title" style="font-size: 1.5em;width: 1em;">&#11163;</span>');
        let updateDropdownControl = $('<span class="lm_title" style="font-size: 1.5em;width: 1em;">&#11163;</span>');
        let splitControl          = $('<span class="lm_title" style="font-size: 2em;width: 1em;">+</span>');

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

        if( tab.contentItem.config.componentName == "Main" ) {
            tab.element.prepend( $('#optionsbutton').clone(true).addClass('lm_title') );
        }

        tab.header.parent.on( 'activeContentItemChanged', onActiveTabChange );
    }


    //
    //
    var onInputCreate = function (tab) {
        //HTML for the typeDropdown
        let splitControl          = $('<span class="lm_title" style="font-size: 2em;width: 1em;">+</span>');

        // track adding a new tab
        splitControl.click( tab, function (evnt) {
            evnt.data.header.parent.addChild( newInputConfig );
        });

        // Add the typeDropdown to the header
        tab.element.append(  splitControl );

        tab.header.parent.on( 'activeContentItemChanged', onActiveTabChange );
    }

    //
    //
    var scrollAll = function () {
        let components = myLayout.root.getItemsByType('component');
        components.forEach( function (component) {
            if( component.hasId('inputComponent') ) { return; } // ignore input components

            let text_div = component.container.getElement().children('.content');
            let scrollHeight = text_div.prop('scrollHeight');
            let clientHeight = text_div.prop('clientHeight');
            text_div.scrollTop( scrollHeight - clientHeight );
        });
        myLayout.updateSize();
    }


    //
    //
    var routeMsg = function (text_div, txt, update_method) {
        if ( update_method == 'replace' ) {
            text_div.html(txt)
        } else if ( update_method == 'append' ) {
            text_div.append(txt);
        } else {  // line feed
            text_div.append('<div class="out">' + txt + '</div>');
        }
        let scrollHeight = text_div.prop('scrollHeight');
        let clientHeight = text_div.prop('clientHeight');
        text_div.scrollTop( scrollHeight - clientHeight );
    }


    //
    //
    var initComponent = function (div, container, state, default_types, update_method) {
        // set this container's content div types attribute
        if( state ) {
            div.attr('types', state.types);
            div.attr('update_method', state.update_method);
        } else {
            div.attr('types', default_types);
            div.attr('update_method', update_method);
        }
        div.appendTo( container.getElement() );
        container.on('tab', onTabCreate);
    }


    //
    // Public
    //


    //
    //
    var onKeydown = function(evnt) {
        var renamebox = document.getElementById('renamebox'); 
        if( renamebox ) {
            return true;
        }
        return false;
    }


    //
    //
    var onText = function (args, kwargs) {
        // If the message is not itself tagged, we'll assume it
        // should go into any panes with 'all' and 'untagged' set
        var msgtype = 'untagged';

        if ( kwargs && 'type' in kwargs ) {
            msgtype = kwargs['type'];
            if ( ! known_types.includes(msgtype) ) {
                // this is a new output type that can be mapped to panes
                console.log('detected new output type: ' + msgtype)
                known_types.push(msgtype);
                untagged.push(msgtype);
            }
        }

        let message_delivered = false;
        let components = myLayout.root.getItemsByType('component');

        components.forEach( function (component) {
            if( component.hasId('inputComponent') ) { return; } // ignore the input component

            let text_div = component.container.getElement().children('.content');
            let attr_types = text_div.attr('types');
            let pane_types = attr_types ? attr_types.split(' ') : [];
            let update_method = text_div.attr('update_method');
            let txt = args[0];

            // is this message type listed in this pane's types (or is this pane catching 'all')
            if( pane_types.includes(msgtype) || pane_types.includes('all') ) {
                routeMsg( text_div, txt, update_method );
                message_delivered = true;
            }

            // is this pane catching 'upmapped' messages?
            // And is this message type listed in the untagged types array?
            if( pane_types.includes("untagged") && untagged.includes(msgtype) ) {
                routeMsg( text_div, txt, update_method );
                message_delivered = true;
            }
        });

        if ( message_delivered ) {
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

        // Set the Event handler for when the client window changes size
        $(window).bind("resize", scrollAll);

        // Set Save State callback
        myLayout.on( 'stateChanged', onStateChanged );

        console.log('Golden Layout Plugin Initialized.');
    }


    //
    // required Init me
    var init = function (options) {
        // Set up our GoldenLayout instance built off of the default main-sub div
        var savedState = localStorage.getItem( 'evenniaGoldenLayoutSavedState' );
        var mainsub = document.getElementById('main-sub');

        if( savedState !== null ) {
            config = JSON.parse( savedState );
        }

        myLayout = new GoldenLayout( config, mainsub );

        $('#inputcontrol').remove(); // remove the cluttered, HTML-defined input divs

        // register our component and replace the default messagewindow with the Main component
        myLayout.registerComponent( 'Main', function (container, componentState) {
            let main = $('#messagewindow').addClass('content');
            initComponent(main, container, componentState, 'untagged', 'newlines' );
        });

        // register our new input component
        myLayout.registerComponent( 'input', function (container, componentState) {
            var inputfield = $('<textarea type="text" class="inputfield form-control"></textarea>');
            var button = $('<button type="button" class="inputsend">&gt;</button>');

            $('<div class="inputwrap">')
                .append( button )
                .append( inputfield )
                .appendTo( container.getElement() );

            button.bind('click', function (evnt) {
                // focus our textarea
                $( $(evnt.target).siblings('.inputfield')[0] ).focus();
                // fake a carriage return event
                var e = $.Event('keydown');
                e.which = 13;
                $( $(evnt.target).siblings('.inputfield')[0] ).trigger(e);
            });

            container.on('tab', onInputCreate);
        });

        myLayout.registerComponent( 'evennia', function (container, componentState) {
            let div = $('<div class="content"></div>');
            initComponent(div, container, componentState, 'all', 'newlines');
            container.on('destroy', calculateUntaggedTypes);
        });
    }


    return {
        init: init,
        postInit: postInit,
        onKeydown: onKeydown,
        onText: onText,
        getGL: function () { return myLayout },
        getConfig: function () { return config },
        setConfig: function (newconfig) { config = newconfig },
        addKnownType: function (newtype) { known_types.push(newtype) },
    }
})());
