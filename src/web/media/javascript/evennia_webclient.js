/*

Evennia ajax webclient (javascript component)

The client is composed of several parts:
 templates/webclient.html - the main page
 webclient/views.py - the django view serving the template (based on urls.py pattern)
 src/server/webclient.py - the server component receiving requests from the client
 this file - the javascript component handling dynamic ajax content

This implements an ajax mud client for use with Evennia, using jQuery
for simplicity. It communicates with the Twisted server on the address
/webclientdata through POST requests. Each request must at least
contain the 'mode' of the request to be handled by the protocol:
 mode 'receive' - tell the server that we are ready to receive data. This is a
                  long-polling (comet-style) request since the server
                  will not reply until it actually has data available.
                  The returned data object has two variables 'msg' and 'data'
                  where msg should be output and 'data' is an arbitrary piece
                  of data the server and client understands (not used in default
                  client).
 mode 'input' - the user has input data on some form. The POST request
                should also contain variables 'msg' and 'data' where
                the 'msg' is a string and 'data' is an arbitrary piece
                of data from the client that the server knows how to
                deal with (not used in this example client).
 mode 'init' -  starts the connection. All setup the server is requered to do
                should happen at this point. The server returns a data object
                with the 'msg' property containing the server address.

 mode 'close' - closes the connection. The server closes the session and does
                cleanup at this point.
*/

// jQuery must be imported by the calling html page before this script
// There are plenty of help on using the jQuery library on http://jquery.com/


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


// Server communications

var CLIENT_HASH = '0'; // variable holding the client id

function webclient_receive(){
    // This starts an asynchronous long-polling request. It will either timeout
    // or receive data from the 'webclientdata' url. In both cases a new request will
    // immediately be started.

    $.ajax({
        type: "POST",
        url: "/webclientdata",
        async: true,             // Turns off browser loading indicator
        cache: false,            // Forces browser reload independent of cache
        timeout:30000,           // Timeout in ms. After this time a new long-poll will be started.
        dataType:"json",
        data: {mode:'receive', 'suid':CLIENT_HASH},

        // callback methods

        success: function(data){       // called when request to waitreceive completes
            msg_display("out", data.msg);  // Add response to the message area
            webclient_receive();              // immediately start a new request
        },
        error: function(XMLHttpRequest, textStatus, errorThrown){
            webclient_receive();              // A possible timeout. Resend request immediately
        },
    });
};

function webclient_input(arg, no_update){
    // Send an input from the player to the server
    // no_update is used for sending idle messages behind the scenes.

    var outmsg = typeof(arg) != 'undefined' ? arg : $("#inputfield").val();

    $.ajax({
        type: "POST",
        url: "/webclientdata",
        async: true,
        cache: false,
        timeout: 30000,
        data: {mode:'input', msg:outmsg, data:'NoData', 'suid':CLIENT_HASH},

        //callback methods

        success: function(data){
            //if (outmsg.length > 0 ) msg_display("inp", outmsg) // echo input on command line
            if (no_update == undefined) {
                history_add(outmsg);
                HISTORY_POS = 0;
                $('#inputform')[0].reset();                     // clear input field
            }
        },
        error: function(XMLHttpRequest, textStatus, errorThrown){
            msg_display("err", "Error: Server returned an error or timed out. Try resending or reloading the page.");
        },
    })
}

function webclient_init(){
    // Start the connection by making sure the server is ready

    $.ajax({
        type: "POST",
        url: "/webclientdata",
        async: true,
        cache: false,
        timeout: 50000,
        dataType:"json",
        data: {mode:'init', 'suid':CLIENT_HASH},

        // callback methods

        success: function(data){  // called when request to initdata completes
            $("#connecting").remove() // remove the "connecting ..." message.
            CLIENT_HASH = data.suid // unique id hash given from server

            // A small timeout to stop 'loading' indicator in Chrome
            setTimeout(function () {
                $("#playercount").fadeOut('slow', webclient_set_sizes);
            }, 10000);

            // Report success
            msg_display('sys',"Connected to " + data.msg + ".");

            // Wait for input
            webclient_receive();
        },
        error: function(XMLHttpRequest, textStatus, errorThrown){
            msg_display("err", "Connection error ..." + " (" + errorThrown + ")");
            setTimeout('webclient_receive()', 15000); // try again after 15 seconds
        },
    });
}

function webclient_close(){
    // Kill the connection and do house cleaning on the server.
    $.ajax({
        type: "POST",
        url: "/webclientdata",
        async: false,
        cache: false,
        timeout: 50000,
        dataType: "json",
        data: {mode: 'close', 'suid': CLIENT_HASH},

        success: function(data){
            CLIENT_HASH = '0';
            alert("Mud client connection was closed cleanly.");
        },
        error: function(XMLHttpRequest, textStatus, errorThrown){
            CLIENT_HASH = '0';
        }

    });
}

// Display messages

function msg_display(type, msg){
    // Add a div to the message window.
    // type gives the class of div to use.
    $("#messagewindow").append(
        "<div class='msg "+ type +"'>"+ msg +"</div>");
    // scroll message window to bottom
    $('#messagewindow').animate({scrollTop: $('#messagewindow')[0].scrollHeight});
}

// Input history mechanism

var HISTORY_MAX_LENGTH = 21
var HISTORY = new Array();
HISTORY[0] = '';
var HISTORY_POS = 0;

function history_step_back() {
    // step backwards in history stack
    HISTORY_POS = Math.min(++HISTORY_POS, HISTORY.length-1);
    return HISTORY[HISTORY.length-1 - HISTORY_POS];
}
function history_step_fwd() {
    // step forward in history stack
    HISTORY_POS = Math.max(--HISTORY_POS, 0);
    return HISTORY[HISTORY.length-1 - HISTORY_POS];
}
function history_add(input) {
    // add an entry to history
    if (input != HISTORY[HISTORY.length-1]) {
        if (HISTORY.length >= HISTORY_MAX_LENGTH) {
            HISTORY.shift(); // kill oldest history entry
        }
        HISTORY[HISTORY.length-1] = input;
        HISTORY[HISTORY.length] = '';
    }
}

// Catching keyboard shortcuts

$(document).keydown( function(event) {
    // Get the pressed key (normalized by jQuery)
    var code = event.which,
        inputField = $("#inputfield");

    // always focus input field no matter which key is pressed
    inputField.focus();

    // Special keys recognized by client

    //msg_display("out", "key code pressed: " + code); // debug

    if (code == 13) { // Enter Key
        webclient_input();
        event.preventDefault();
    }
    else {
        if (code == 38) { // arrow up 38
            inputField.val(history_step_back()).appendCaret();
        }
        else if (code == 40) { // arrow down 40
            inputField.val(history_step_fwd()).appendCaret();
        }
    }
});

// handler to avoid double-clicks until the ajax request finishes
$("#inputsend").one("click", webclient_input)

function webclient_set_sizes() {
    // Sets the size of the message window
    var win_h = $(document).height();
    //var win_w = $('#wrapper').width();
    var inp_h = $('#inputform').outerHeight(true);
    //var inp_w = $('#inputsend').outerWidth(true);

    $("#messagewindow").css({'height': win_h - inp_h - 1});
    //$("#inputfield").css({'width': win_w - inp_w - 20});
}


// Callback function - called when page has finished loading (gets things going)
$(document).ready(function(){
    // remove the "no javascript" warning, since we obviously have javascript
    $('#noscript').remove();
    // set sizes of elements and reposition them
    webclient_set_sizes();
    // a small timeout to stop 'loading' indicator in Chrome
    setTimeout(function () {
        webclient_init();
    }, 500);
    // set an idle timer to avoid proxy servers to time out on us (every 3 minutes)
    setInterval(function() {
        webclient_input("idle", true);
    }, 60000*3);
});

// Callback function - called when the browser window resizes
$(window).resize(function() {
    webclient_set_sizes();
});

// Callback function - called when page is closed or moved away from.
$(window).unload(function() {
    webclient_close();
});
