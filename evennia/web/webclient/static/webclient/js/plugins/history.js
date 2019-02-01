/*
 *
 * Evennia Webclient Command History plugin
 *
 */
let history_plugin = (function () {

    // Manage history for input line
    var history_max = 20;
    var history = {};
    var history_pos = {};

    //
    // Add a new textarea to track history for.
    var track_history_for_id = function(id) {
        if( ! history.hasOwnProperty( id ) ) {
            history[id] = new Array;
            history_pos[id] = -1;
        } else {
            console.log('IGNORED -- already tracking history for that DOM element!');
        }
    }

    //
    // Return whichever inputfield (if any) is focused, out of the set we are tracking
    var get_focused_input = function () {
        let inputfield = $( document.activeElement );

        // is the focused element one of the ones we are tracking history for?
        if( history.hasOwnProperty( inputfield.attr('id') ) ) { 
            return inputfield;
        }
        return null;
    }

    //
    // move back from the history (to newer elements)
    var back = function (id) {
        // step back in history queue, to the most recently stored entry.
        if( history_pos[id] >= 0 ) {
            history_pos[id]--;

            // if we've stepped "before" the first element of our queue, return new, empty string
            if( history_pos[id] == -1 ) {
                return '';
            }
        }

        return history[id][ history_pos[id] ];
    }

    //
    // move forward into the history (to older elements)
    var fwd = function (id) {
        // step forward in history queue, restricted by bounds checking
        if( history_pos[id] < Math.min( history[id].length - 1, history_max - 1 ) ) {
            history_pos[id]++;
        }
        return history[id][ history_pos[id] ];
    }

    //
    // add a new history line
    var add = function (id, input) {
        // add a new entry to history, don't repeat latest
        if (input && input != history[id][0]) {
            // make sure to trim the history queue length to 'history_max'
            if (history[id].length + 1 >= history_max) {
                history[id].pop(); // remove oldest entry from queue
            }
            history[id].unshift(input); // add newest entry to beginning of queue
        }
        // reset the position to the beginning of the queue
        history_pos[id] = -1;
    }

    // Public

    //
    // Handle up arrow and down arrow events.
    var onKeydown = function(event) {
        var keycode = event.which;

        // Is one of the two input fields focused?
        let inputfield = get_focused_input();
        if( inputfield != null ) {
            let id = inputfield.attr('id')
            let history_entry = null; // check the keycode for up/down arrows
            if (keycode === 40) { // Arrow down
                history_entry = back(id);
            }
            else if (keycode === 38) { // Arrow up
                history_entry = fwd(id);
            }

            if (history_entry !== null) {
                // Performing a history navigation
                // replace the text in the input and move the cursor to the end of the new value
                inputfield.blur().focus().val(history_entry);
                event.preventDefault();
                return true;
            }
        }
        return false;
    }

    //
    // Listen for onSend lines to add to history
    var onSend = function (line) {
        let inputfield = get_focused_input();
        if( inputfield != null ) {
            add(inputfield.attr('id'), line);
        }
        return null; // we are not returning an altered input line
    }

    //
    // Init function
    var init = function () {
        track_history_for_id('inputfield'); // The default inputfield

        // check to see if the dual_input plugin is enabled.
        if( !(typeof plugins['dual_input'] === "undefined") ) {
            console.log('configuring history tracking for dual_input plugin');
            track_history_for_id('inputfield2');
        }

        console.log('History Plugin Initialized.');
    } 

    return {
        init: init,
        onKeydown: onKeydown,
        onSend: onSend,
    }
})()
plugin_handler.add('history', history_plugin);
