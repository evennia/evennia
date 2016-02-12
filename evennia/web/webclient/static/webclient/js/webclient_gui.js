/*
 *
 * Evennia Webclient GUI component
 *
 * This is used in conjunction with the main evennia.js library, which
 * handles all the communication with the Server.
 *
 * The job of this code is to create listeners to subscribe to evennia
 * messages, via Evennia.emitter.on(cmdname, listener) and to handle
 * input from the user and send it to
 * Evennia.msg(cmdname, args, kwargs, [callback]).
 *
 */

//
// GUI Elements
//


//
// Manage history for input line
//
var inputlog = function() {
    var history_max = 21;
    var history = new Array();
    var history_pos = 0;

    history[0] = ''; // the very latest input is empty for new entry.

    var back = function () {
        // step backwards in history stack
        history_pos = Math.min(++history_pos, history.length - 1);
        return history[history.length - 1 - history_pos];
    };
    var fwd = function () {
        // step forwards in history stack
        history_pos = Math.max(--history_pos, 0);
        return history[history.length -1 - history_pos];
    };
    var add = function (input) {
        // add a new entry to history, don't repeat latest
        if (input != history[history.length-1]) {
            if (history.length >= history_max) {
                history.shift(); // kill oldest entry
            }
            history[history.length-1] = input;
            history[history.length] = '';
        };
    };
    return {back: back,
            fwd: fwd,
            add: add}
}();

$.fn.appendCaret = function() {
    /* jQuery extension that will forward the caret to the end of the input, and
       won't harm other elements (although calling this on multiple inputs might
       not have the expected consequences).

       Thanks to
       http://stackoverflow.com/questions/499126/jquery-set-cursor-position-in-text-area
       for the good starting point.  */
    return this.each(function() {
        var range,
            // Index at where to place the caret.
            end,
            self = this;

        if (self.setSelectionRange) {
            // other browsers
            end = self.value.length;
            self.focus();
            // NOTE: Need to delay the caret movement until after the callstack.
            setTimeout(function() {
                self.setSelectionRange(end, end);
            }, 0);
        }
        else if (self.createTextRange) {
            // IE
            end = self.value.length - 1;
            range = self.createTextRange();
            range.collapse(true);
            range.moveEnd('character', end);
            range.moveStart('character', end);
            // NOTE: I haven't tested to see if IE has the same problem as
            // W3C browsers seem to have in this context (needing to fire
            // select after callstack).
            range.select();
        }
    });
};


// GUI Event Handlers

$(document).keydown( function(event) {
    // catch all keyboard input, handle special chars
    var code = event.which;
    inputfield = $("#inputfield");
    inputfield.focus();

    if (code === 13) { // Enter key sends text
        outtext = inputfield.val();
        inputlog.add(outtext);
        inputfield.val("");
        log("sending outtext", outtext);
        Evennia.msg("text", [outtext], {});
        event.preventDefault()
    }
    else if (code === 38) { // Arrow up
        inputfield.val(inputlog.back()).appendCaret();
    }
    else if (code === 40) { // Arrow down
        inputfield.val(inputlog.fwd()).appendCaret();
    }

});

// client size setter

function set_window_size() {
    var winh = $(document).height();
    var formh = $('#inputform').outerHeight(true);
    $("#messagewindow").css({'height': winh - formh - 1});
}

// Event - called when window resizes
$(window).resize(set_window_size);


//
// Listeners
//

function doText(args, kwargs) {
    // append message to previous ones
    log("doText:", args, kwargs);
    $("#messagewindow").append(
            "<div class='msg out'>" + args[0] + "</div>");
    // scroll message window to bottom
    $("#messagewindow").animate({scrollTop: $('#messagewindow')[0].scrollHeight});
}

function doPrompt(args, kwargs) {
    // show prompt
    $('prompt').replaceWith(
           "<div id='prompt' class='msg out'>" + args[0] + "</div>");
}


$(document).ready(function() {
    // a small timeout to stop 'loading' indicator in Chrome
    Evennia.init()
    // register listeners
    log("register listeners ...");
    Evennia.emitter.on("text", doText);
    Evennia.emitter.on("prompt", doPrompt);
    set_window_size();

    // set an idle timer to avoid proxy servers to time out on us (every 3 minutes)
    setInterval(function() {
        log('Idle tick.');
        Evennia.msg("text", ["idle"], {});
    },
    60000*3
    );
});

