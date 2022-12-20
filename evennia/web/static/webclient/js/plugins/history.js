/*
 *
 * Evennia Webclient Command History plugin
 *
 */
let history = (function () {

    // Manage history for input line
    var historyMax = 21;
    var history = new Array();
    var historyPos = 0;

    history[0] = ""; // the very latest input is empty for new entry.

    //
    // move back in the history
    var back = function () {
        // step backwards in history stack
        historyPos = Math.min(++historyPos, history.length - 1);
        return history[history.length - 1 - historyPos];
    }

    //
    // move forward in the history
    var fwd = function () {
        // step forwards in history stack
        historyPos = Math.max(--historyPos, 0);
        return history[history.length - 1 - historyPos];
    }

    //
    // add a new history line
    var add = function (input) {
        // add a new entry to history, don't repeat latest
        if (input && input != history[history.length-2]) {
            if (history.length >= historyMax) {
                history.shift(); // kill oldest entry
            }
            history[history.length-1] = input;
            history[history.length] = "";
        }
    }

    // Public

    //
    // Handle up arrow and down arrow events.
    var onKeydown = function(event) {
        var code = event.which;
        var historyEntry = null;
        var startingPos = historyPos;

        // Only process up/down arrow if cursor is at the end of the line.
        if (code === 38 && event.shiftKey) { // Shift + Arrow up
            historyEntry = back();
        }
        else if (code === 40 && event.shiftKey) { // Shift + Arrow down
            historyEntry = fwd();
        }

        // are we processing an up or down history event?
        if (historyEntry !== null) {
            // Doing a history navigation; replace the text in the input and
            // move the cursor to the end of the new value
            var inputfield = $(".inputfield:focus");
            if( inputfield.length < 1 ) { // focus the default (last), if nothing focused
                inputfield = $(".inputfield:last");
            }
            if( inputfield.length < 1 ) { // pre-goldenlayout backwards compatibility
                inputfield = $("#inputfield");
            }

            // store any partially typed line as a new history item before replacement
            var line = inputfield.val();
            if( line !== "" && startingPos === 0 ) {
                add(line);
            }

            inputfield.val("");
            inputfield.blur().focus().val(historyEntry);
            event.preventDefault();
            return true;
        }

        return false;
    }

    //
    // Listen for onSend lines to add to history
    var onSend = function (line) {
        add(line);
        historyPos = 0;
        return null;
    }

    return {
        init: function () {},
        onKeydown: onKeydown,
        onSend: onSend,
    }
}());
window.plugin_handler.add("history", history);
