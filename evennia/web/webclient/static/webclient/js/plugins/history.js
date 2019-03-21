/*
 *
 * Evennia Webclient Command History plugin
 *
 */
let history_plugin = (function () {

    // Manage history for input line
    var history_max = 21;
    var history = new Array();
    var history_pos = 0;

    history[0] = ''; // the very latest input is empty for new entry.

    //
    // move back in the history
    var back = function () {
        // step backwards in history stack
        history_pos = Math.min(++history_pos, history.length - 1);
        return history[history.length - 1 - history_pos];
    }

    //
    // move forward in the history
    var fwd = function () {
        // step forwards in history stack
        history_pos = Math.max(--history_pos, 0);
        return history[history.length - 1 - history_pos];
    }

    //
    // add a new history line
    var add = function (input) {
        // add a new entry to history, don't repeat latest
        if (input && input != history[history.length-2]) {
            if (history.length >= history_max) {
                history.shift(); // kill oldest entry
            }
            history[history.length-1] = input;
            history[history.length] = '';
        }
        history_pos = 0;
    }

    //
    // Add input to the scratch line
    var scratch = function (input) {
        // Put the input into the last history entry (which is normally empty)
        // without making the array larger as with add.
        // Allows for in-progress editing to be saved.
        history[history.length-1] = input;
    }

    // Public

    //
    // Handle up arrow and down arrow events.
    var onKeydown = function(event) {
        var code = event.which;
        var history_entry = null;
        var inputfield = $('.inputfield:focus');

        // Only process up/down arrow if cursor is at the end of the line.
        if (code === 38 && event.shiftKey) { // Arrow up
            history_entry = back();
        }
        else if (code === 40 && event.shiftKey) { // Arrow down
            history_entry = fwd();
        }

        // are we processing an up or down history event?
        if (history_entry !== null) {
            // Doing a history navigation; replace the text in the input and move the cursor to the end of the new value
            inputfield.val('');
            inputfield.blur().focus().val(history_entry);
            event.preventDefault();
            return true;
        }

        return false;
    }

    //
    // Listen for onSend lines to add to history
    var onSend = function (line) {
        add(line);
        return null;
    }

    //
    // Init function
    var init = function () {
        console.log('History Plugin Initialized.');
    } 

    return {
        init: init,
        onKeydown: onKeydown,
        onSend: onSend,
    }
})()
plugin_handler.add('history', history_plugin);
