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

(function () {
"use strict"


var options = {};
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
        return history[history.length - 1 - history_pos];
    };
    var add = function (input) {
        // add a new entry to history, don't repeat latest
        if (input && input != history[history.length-2]) {
            if (history.length >= history_max) {
                history.shift(); // kill oldest entry
            }
            history[history.length-1] = input;
            history[history.length] = '';
        };
        // reset the position to the last history entry
        history_pos = 0;
    };
    var end = function () {
        // move to the end of the history stack
        history_pos = 0;
        return history[history.length -1];
    }

    var scratch = function (input) {
        // Put the input into the last history entry (which is normally empty)
        // without making the array larger as with add.
        // Allows for in-progress editing to be saved.
        history[history.length-1] = input;
    }

    return {back: back,
            fwd: fwd,
            add: add,
            end: end,
            scratch: scratch}
}();

function openPopup(dialogname, content) {
    var dialog = $(dialogname);
    if (!dialog.length) {
        console.log("Dialog " + renderto + " not found.");
        return;
    }

    if (content) {
        var contentel = dialog.find(".dialogcontent");
        contentel.html(content);
    }
    dialog.show();
}

function closePopup(dialogname) {
    var dialog = $(dialogname);
    dialog.hide();
}

function togglePopup(dialogname, content) {
    var dialog = $(dialogname);
    if (dialog.css('display') == 'none') {
        openPopup(dialogname, content);
    } else {
        closePopup(dialogname);
    }
}

//
// GUI Event Handlers
//

// Grab text from inputline and send to Evennia
function doSendText() {
    if (!Evennia.isConnected()) {
        var reconnect = confirm("Not currently connected. Reconnect?");
        if (reconnect) {
            onText(["Attempting to reconnnect..."], {cls: "sys"});
            Evennia.connect();
        }
        // Don't try to send anything until the connection is back.
        return;
    }
    var inputfield = $("#inputfield");
    var outtext = inputfield.val();
    var lines = outtext.trim().replace(/[\r]+/,"\n").replace(/[\n]+/, "\n").split("\n");
    for (var i = 0; i < lines.length; i++) {
        var line = lines[i].trim();
        if (line.length > 7 && line.substr(0, 7) == "##send ") {
            // send a specific oob instruction ["cmdname",[args],{kwargs}]
            line = line.slice(7);
            var cmdarr = JSON.parse(line);
            var cmdname = cmdarr[0];
            var args = cmdarr[1];
            var kwargs = cmdarr[2];
            log(cmdname, args, kwargs);
            Evennia.msg(cmdname, args, kwargs);
        } else {
            input_history.add(line);
            inputfield.val("");
            Evennia.msg("text", [line], {});
        }
    }
}

// Opens the options dialog
function doOpenOptions() {
    if (!Evennia.isConnected()) {
        alert("You need to be connected.");
        return;
    }

    togglePopup("#optionsdialog");
}

// Closes the currently open dialog
function doCloseDialog(event) {
    var dialog = $(event.target).closest(".dialog");
    dialog.hide();
}

// catch all keyboard input, handle special chars
function onKeydown (event) {
    var code = event.which;
    var history_entry = null;
    var inputfield = $("#inputfield");
    inputfield.focus();

    if (code === 13) { // Enter key sends text
        doSendText();
        event.preventDefault();
    }
    else if (inputfield[0].selectionStart == inputfield.val().length) {
        // Only process up/down arrow if cursor is at the end of the line.
        if (code === 38) { // Arrow up
            history_entry = input_history.back();
        }
        else if (code === 40) { // Arrow down
            history_entry = input_history.fwd();
        }
    }

    if (code === 27) { // Escape key
        closePopup("#optionsdialog");
        closePopup("#helpdialog");
    }

    if (history_entry !== null) {
        // Doing a history navigation; replace the text in the input.
        inputfield.val(history_entry);
        event.preventDefault();
    }
    else {
        // Save the current contents of the input to the history scratch area.
        setTimeout(function () {
            // Need to wait until after the key-up to capture the value.
            input_history.scratch(inputfield.val());
            input_history.end();
        }, 0);
    }
};

function onKeyPress (event) {
    // Prevent carriage returns inside the input area.
    if (event.which === 13) {
        event.preventDefault();
    }
}

var resizeInputField = function () {
    var min_height = 50;
    var max_height = 300;
    var prev_text_len = 0;

    // Check to see if we should change the height of the input area
    return function () {
        var inputfield = $("#inputfield");
        var scrollh = inputfield.prop("scrollHeight");
        var clienth = inputfield.prop("clientHeight");
        var newh = 0;
        var curr_text_len = inputfield.val().length;

        if (scrollh > clienth && scrollh <= max_height) {
            // Need to make it bigger
            newh = scrollh;
        }
        else if (curr_text_len < prev_text_len) {
            // There is less text in the field; try to make it smaller
            // To avoid repaints, we draw the text in an offscreen element and
            // determine its dimensions.
            var sizer = $('#inputsizer')
                .css("width", inputfield.prop("clientWidth"))
                .text(inputfield.val());
            newh = sizer.prop("scrollHeight");
        }

        if (newh != 0) {
            newh = Math.min(newh, max_height);
            if (clienth != newh) {
                inputfield.css("height", newh + "px");
                doWindowResize();
            }
        }
        prev_text_len = curr_text_len;
    }
}();

// Handle resizing of client
function doWindowResize() {
    var formh = $('#inputform').outerHeight(true);
    var message_scrollh = $("#messagewindow").prop("scrollHeight");
    $("#messagewindow")
        .css({"bottom": formh}) // leave space for the input form
        .scrollTop(message_scrollh); // keep the output window scrolled to the bottom
}

// Handle text coming from the server
function onText(args, kwargs) {
    // append message to previous ones, then scroll so latest is at
    // the bottom. Send 'cls' kwarg to modify the output class.
    var renderto = "main";
    if (kwargs["type"] == "help") {
        if (("helppopup" in options) && (options["helppopup"])) {
            renderto = "#helpdialog";
        }
    }

    if (renderto == "main") {
        var mwin = $("#messagewindow");
        var cls = kwargs == null ? 'out' : kwargs['cls'];
        mwin.append("<div class='" + cls + "'>" + args[0] + "</div>");
        mwin.animate({
            scrollTop: document.getElementById("messagewindow").scrollHeight
        }, 0);

        onNewLine(args[0], null);
    } else {
        openPopup(renderto, args[0]);
    }
}

// Handle prompt output from the server
function onPrompt(args, kwargs) {
    // show prompt
    $('#prompt')
        .addClass("out")
        .html(args[0]);
    doWindowResize();

    // also display the prompt in the output window if gagging is disabled
    if (("gagprompt" in options) && (!options["gagprompt"])) {
        onText(args, kwargs);
    }
}

// Called when the user logged in
function onLoggedIn() {
    Evennia.msg("webclient_options", [], {});
}

// Called when a setting changed
function onGotOptions(args, kwargs) {
    options = kwargs;

    $.each(kwargs, function(key, value) {
        var elem = $("[data-setting='" + key + "']");
        if (elem.length === 0) {
            console.log("Could not find option: " + key);
        } else {
            elem.prop('checked', value);
        };
    });
}

// Called when the user changed a setting from the interface
function onOptionCheckboxChanged() {
    var name = $(this).data("setting");
    var value = this.checked;

    var changedoptions = {};
    changedoptions[name] = value;
    Evennia.msg("webclient_options", [], changedoptions);

    options[name] = value;
}

// Silences events we don't do anything with.
function onSilence(cmdname, args, kwargs) {}

// Handle the server connection closing
function onConnectionClose(conn_name, evt) {
    onText(["The connection was closed or lost."], {'cls': 'err'});
}

// Handle unrecognized commands from server
function onDefault(cmdname, args, kwargs) {
    var mwin = $("#messagewindow");
    mwin.append(
            "<div class='msg err'>"
            + "Error or Unhandled event:<br>"
            + cmdname + ", "
            + JSON.stringify(args) + ", "
            + JSON.stringify(kwargs) + "<p></div>");
    mwin.scrollTop(mwin[0].scrollHeight);
}

// Ask if user really wants to exit session when closing
// the tab or reloading the page. Note: the message is not shown
// in Firefox, there it's a standard error.
function onBeforeUnload() {
    return "You are about to leave the game. Please confirm.";
}

// Notifications
var unread = 0;
var originalTitle = document.title;
var focused = true;
var favico;

function onBlur(e) {
  focused = false;
}

// Notifications for unfocused window
function onFocus(e) {
  focused = true;
  document.title = originalTitle;
  unread = 0;
  favico.badge(0);
}

function onNewLine(text, originator) {
  if(!focused) {
    // Changes unfocused browser tab title to number of unread messages
    unread++;
    favico.badge(unread);
    document.title = "(" + unread + ") " + originalTitle;

    if (("notification_popup" in options) && (options["notification_popup"])) {
        Notification.requestPermission().then(function(result) {
            if(result === "granted") {
            var title = originalTitle === "" ? "Evennia" : originalTitle;
            var options = {
                body: text.replace(/(<([^>]+)>)/ig,""),
                icon: "/static/website/images/evennia_logo.png"
            }

            var n = new Notification(title, options);
            n.onclick = function(e) {
                e.preventDefault();
                 window.focus();
                 this.close();
            }
          }
        });
    }
    if (("notification_sound" in options) && (options["notification_sound"])) {
        var audio = new Audio("/static/webclient/media/notification.wav");
        audio.play();
    }
  }
}

// User clicked on a dialog to drag it
function doStartDragDialog(event) {
    var dialog = $(event.target).closest(".dialog");
    dialog.css('cursor', 'move');

    var position = dialog.offset();
    var diffx = event.pageX;
    var diffy = event.pageY;

    var drag = function(event) {
        var y = position.top + event.pageY - diffy;
        var x = position.left + event.pageX - diffx;
        dialog.offset({top: y, left: x});
    };

    var undrag = function() {
        $(document).unbind("mousemove", drag);
        $(document).unbind("mouseup", undrag);
        dialog.css('cursor', '');
    }

    $(document).bind("mousemove", drag);
    $(document).bind("mouseup", undrag);
}

//
// Register Events
//

// Event when client finishes loading
$(document).ready(function() {

    Notification.requestPermission();

    favico = new Favico({
      animation: 'none'
    });

    // Event when client window changes
    $(window).bind("resize", doWindowResize);

    $(window).blur(onBlur);
    $(window).focus(onFocus);

    //$(document).on("visibilitychange", onVisibilityChange);

    $("#inputfield").bind("resize", doWindowResize)
        .keypress(onKeyPress)
        .bind("paste", resizeInputField)
        .bind("cut", resizeInputField);

    // Event when any key is pressed
    $(document).keydown(onKeydown)
        .keyup(resizeInputField);

    // Pressing the send button
    $("#inputsend").bind("click", doSendText);

    // Pressing the settings button
    $("#optionsbutton").bind("click", doOpenOptions);

    // Checking a checkbox in the settings dialog
    $("[data-setting]").bind("change", onOptionCheckboxChanged);

    // Pressing the close button on a dialog
    $(".dialogclose").bind("click", doCloseDialog);

    // Makes dialogs draggable
    $(".dialogtitle").bind("mousedown", doStartDragDialog);

    // This is safe to call, it will always only
    // initialize once.
    Evennia.init();
    // register listeners
    Evennia.emitter.on("text", onText);
    Evennia.emitter.on("prompt", onPrompt);
    Evennia.emitter.on("default", onDefault);
    Evennia.emitter.on("connection_close", onConnectionClose);
    Evennia.emitter.on("logged_in", onLoggedIn);
    Evennia.emitter.on("webclient_options", onGotOptions);
    // silence currently unused events
    Evennia.emitter.on("connection_open", onSilence);
    Evennia.emitter.on("connection_error", onSilence);

    // Handle pressing the send button
    $("#inputsend").bind("click", doSendText);
    // Event when closing window (have to have Evennia initialized)
    $(window).bind("beforeunload", onBeforeUnload);
    $(window).bind("unload", Evennia.connection.close);

    doWindowResize();
    // set an idle timer to send idle every 3 minutes,
    // to avoid proxy servers timing out on us
    setInterval(function() {
        // Connect to server
        Evennia.msg("text", ["idle"], {});
    },
    60000*3
    );


});

})();
