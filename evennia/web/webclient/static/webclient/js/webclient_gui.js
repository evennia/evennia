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

var known_types = new Array();
    known_types.push('help');

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
  console.log("sending text");
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
    if (code === 9) {
      return;
    }

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
        if ($('#helpdialog').is(':visible')) {
          closePopup("#helpdialog");
        } else {
          closePopup("#optionsdialog");
        }
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
    return function() {
      var wrapper = $("#inputform")
      var input = $("#inputcontrol")
      var prompt = $("#prompt")

      input.height(wrapper.height() - (input.offset().top - wrapper.offset().top));
    }
}();

// Handle resizing of client
function doWindowResize() {
      resizeInputField();
      var resizable = $("[data-update-append]");
      var parents = resizable.closest(".split")
      parents.animate({
          scrollTop: parents.prop("scrollHeight")
      }, 0);
}

// Handle text coming from the server
function onText(args, kwargs) {
    var use_default_pane = true;

    if ( kwargs && 'type' in kwargs ) {
        var msgtype = kwargs['type'];
        if ( ! known_types.includes(msgtype) ) {
            // this is a new output type that can be mapped to panes
            console.log('detected new output type: ' + msgtype)
            known_types.push(msgtype);
        }

        if ( msgtype == 'help' ) {
            if (("helppopup" in options) && (options["helppopup"])) {
                openPopup("#helpdialog", args[0]);
                return;
            }
            // fall through to the default output

        } else {
            // pass this message to each pane that has this msgtype mapped
            if( SplitHandler ) {
                for ( var key in SplitHandler.split_panes) {
                    var pane = SplitHandler.split_panes[key];
                    // is this message type mapped to this pane?
                    if ( (pane['types'].length > 0) && pane['types'].includes(msgtype) ) {
                        // yes, so append/replace this pane's inner div with this message
                        if ( pane['update_method'] == 'replace' ) {
                            $('#'+key).html(args[0])
                        } else {
                            $('#'+key).append(args[0]);
                            var scrollHeight = $('#'+key).parent().prop("scrollHeight");
                            $('#'+key).parent().animate({ scrollTop: scrollHeight }, 0);
                        }
                        // record sending this message to a pane, no need to update the default div
                        use_default_pane = false;
                    }
                }
            }
        }
    }

    // append message to default pane, then scroll so latest is at the bottom.
    if(use_default_pane) {
        var mwin = $("#messagewindow");
        var cls = kwargs == null ? 'out' : kwargs['cls'];
        mwin.append("<div class='" + cls + "'>" + args[0] + "</div>");
        var scrollHeight = mwin.parent().parent().prop("scrollHeight");
        mwin.parent().parent().animate({ scrollTop: scrollHeight }, 0);

        onNewLine(args[0], null);
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
    $('#optionsbutton').removeClass('hidden');
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
    $('#optionsbutton').addClass('hidden');
    closePopup("#optionsdialog");
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
    if ("Notification" in window){
      if (("notification_popup" in options) && (options["notification_popup"])) {
          // There is a Promise-based API for this, but it’s not supported
          // in Safari and some older browsers:
          // https://developer.mozilla.org/en-US/docs/Web/API/Notification/requestPermission#Browser_compatibility
          Notification.requestPermission(function(result) {
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


function onSplitDialogClose() {
    var pane      = $("input[name=pane]:checked").attr("value");
    var direction = $("input[name=direction]:checked").attr("value");
    var flow1     = $("input[name=flow1]:checked").attr("value");
    var flow2     = $("input[name=flow2]:checked").attr("value");

    SplitHandler.dynamic_split( pane, direction, flow1, flow2 );

    closePopup("#splitdialog");
}


function onSplitDialog() {
    var dialog = $("#splitdialogcontent");
    dialog.empty();

    dialog.append("<h3>Split?</h3>");
    dialog.append('<input type="radio" name="direction" value="vertical" checked> top/bottom<br />');
    dialog.append('<input type="radio" name="direction" value="horizontal"> side-by-side<br />');

    dialog.append("<h3>Split Which Pane?</h3>");
    for ( var pane in SplitHandler.split_panes ) {
        dialog.append('<input type="radio" name="pane" value="'+ pane +'">'+ pane +'<br />');
    }

    dialog.append("<h3>New First Pane Flow</h3>");
    dialog.append('<input type="radio" name="flow1" value="append" checked>append<br />');
    dialog.append('<input type="radio" name="flow1" value="replace">replace<br />');

    dialog.append("<h3>New Second Pane Flow</h3>");
    dialog.append('<input type="radio" name="flow2" value="append" checked>append<br />');
    dialog.append('<input type="radio" name="flow2" value="replace">replace<br />');

    dialog.append('<div id="splitclose" class="button">Split It</div>');

    $("#splitclose").bind("click", onSplitDialogClose);

    openPopup("#splitdialog");
}

function onPaneControlDialogClose() {
    var pane = $("input[name=pane]:checked").attr("value");

    var types = new Array; 
    $('#splitdialogcontent input[type=checkbox]:checked').each(function() {
        types.push( $(this).attr('value') );
    });

    SplitHandler.set_pane_types( pane, types );

    closePopup("#splitdialog");
}

function onPaneControlDialog() {
    var dialog = $("#splitdialogcontent");
    dialog.empty();

    dialog.append("<h3>Set Which Pane?</h3>");
    for ( var pane in SplitHandler.split_panes ) {
        dialog.append('<input type="radio" name="pane" value="'+ pane +'">'+ pane +'<br />');
    }

    dialog.append("<h3>Which content types?</h3>");
    for ( var type in known_types ) {
        dialog.append('<input type="checkbox" value="'+ known_types[type] +'">'+ known_types[type] +'<br />');
    }

    dialog.append('<div id="paneclose" class="button">Make It So</div>');

    $("#paneclose").bind("click", onPaneControlDialogClose);

    openPopup("#splitdialog");
}

//
// Register Events
//

// Event when client finishes loading
$(document).ready(function() {

    if( SplitHandler ) {
      SplitHandler.init();
      $("#splitbutton").bind("click", onSplitDialog);
      $("#panebutton").bind("click", onPaneControlDialog);
    } else {
      $("#splitbutton").hide();
      $("#panebutton").hide();
    }

    if ("Notification" in window) {
      Notification.requestPermission();
    }

    favico = new Favico({
      animation: 'none'
    });

    // Event when client window changes
    $(window).bind("resize", doWindowResize);

    $(window).blur(onBlur);
    $(window).focus(onFocus);

    //$(document).on("visibilitychange", onVisibilityChange);

    $("[data-role-input]").bind("resize", doWindowResize)
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
    console.log("Completed GUI setup");


});

})();
