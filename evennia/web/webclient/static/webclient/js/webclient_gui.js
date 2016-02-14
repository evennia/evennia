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


// Manage history for input line
var input_history = function() {
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
        if (input && input != history[history.length-1]) {
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

//
// GUI Event Handlers
//

// Grab text from inputline and send to Evennia
function doSendText() {
    inputfield = $("#inputfield");
    outtext = inputfield.val();
    input_history.add(outtext);
    inputfield.val("");
    Evennia.msg("text", [outtext], {});
}

// catch all keyboard input, handle special chars
function onKeydown (event) {
    var code = event.which;
    inputfield = $("#inputfield");
    inputfield.focus();

    if (code === 13) { // Enter key sends text
        doSendText();
        event.preventDefault();
    }
    else if (code === 38) { // Arrow up
        inputfield.val(input_history.back());
        event.preventDefault();
    }
    else if (code === 40) { // Arrow down
        inputfield.val(input_history.fwd());
        event.preventDefault();
    }
};

// Handle resizing of client
function doWindowResize() {
    var winh = $(document).height();
    var formh = $('#inputform').outerHeight(true);
    $("#messagewindow").css({'height': winh - formh - 1});
}

// Handle text coming from the server
function onText(args, kwargs) {
    // append message to previous ones, then scroll so latest is at
    // the bottom.
    mwin = $("#messagewindow");
    mwin.append("<div class='msg out'>" + args[0] + "</div>");
    mwin.scrollTop(mwin[0].scrollHeight);
}

// Handle prompt output from the server
function onPrompt(args, kwargs) {
    // show prompt
    $('prompt').replaceWith(
           "<div id='prompt' class='msg out'>" + args[0] + "</div>");
}

// Handler silencing events we don't do anything with.
function onSilence(cmdname, args, kwargs) {}

// Handler unrecognized commands from server
function onDefault(cmdname, args, kwargs) {
    mwin = $("#messagewindow");
    mwin.append(
            "<div class='msg err'>"
            + "Error or Unhandled event:<br>"
            + cmdname + ", "
            + JSON.stringify(args) + ", "
            + JSON.stringify(kwargs) + "<p></div>");
    mwin.scrollTop(mwin[0].scrollHeight);
}


//
// Register Events
//

// Event when client window changes
$(window).resize(doWindowResize);

// Evenit when any key is pressed
$(document).keydown(onKeydown);

// Event when client finishes loading
$(document).ready(function() {
    // This is safe to call, it will always only
    // initialize once.
    Evennia.init();
    // register listeners
    Evennia.emitter.on("text", onText);
    Evennia.emitter.on("prompt", onPrompt);
    Evennia.emitter.on("default", onDefault);
    // silence currently unused events
    Evennia.emitter.on("connection_open", onSilence);
    Evennia.emitter.on("connection_close", onSilence);

    // Event when closing window (have to have Evennia initialized)
    $(window).bind("beforeunload", Evennia.connection.close);

    // set an idle timer to send idle every 3 minutes,
    // to avoid proxy servers timing out on us
    setInterval(function() {
        // Connect to server
        Evennia.msg("text", ["idle"], {});
    },
    60000*3
    );
});

