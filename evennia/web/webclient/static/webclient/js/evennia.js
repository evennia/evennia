/* 
 * Evennia webclient library. Load this into your <head> html page
 * template with 
 *
 * <script src="https://code.jquery.com/jquery-1.11.3.min.js"></script>
 * <script webclient/js/evennia.js</script>
 *
 * In your template you can then put elements with specific ids that
 * evennia will look for.  Evennia will via this library relay text to
 * specific divs if given, or to the "text" div if not. 
 *
 */

/* 
 * global vars 
 */
var websocket;

/*
 * Configuration variables
 * (set by the user)
 */

var echo_to_textarea = true;

/*
 * Evennia OOB command map; this holds custom js functions
 * that the OOB handler supports. Each key is the name
 * of a js callback function. External development is
 * done by adding functions func(data) to this object,
 * where data is the data object sent from the server.
 */

oob_commands = {
    "text": function(data) {
        // basic div redistributor making
        // use of the default text relay.
        // Use in combination with the
        // divclass oob argument to send
        // text to different DOM element classes.
        var msg = data.text;
        var divclass = data.divclass;
        toClass(divclass, msg);
    }
};

/*
 * Send text to given element class
 */
toClass = function(divclass, data) {
    // loop over all objects of divclass
    //console.log("toClass: " + divclass + " " + data);
    $("." + divclass).each(function() {
        switch (divclass) {
            case "textoutput": 
                // update the bottom of the normal text area
                // and scroll said area.
                var oldtext = $.trim($(this).val());
                $(this).val(oldtext + "\n" + data);
                //$(this).scrollTop($(this)[0].scrollHeight);
                break;
            case "lookoutput":
                // update the look text box
                $(this).val(data);
                break;
        }
    });
}

/*
 * Send data to Evennia. This data is always sent
 * as an JSON object. {key:arg, ...}
 *    key "cmd" - a text input command (in arg)
 *    other keys - interpreted as OOB command keys and their args
 *                 (can be an array)
 */
dataSend = function(classname, data) {
    // client -> Evennia. 
    var outdata = {classname: data}; // for testing 
    //websocket.send(JSON.stringify(data)) // send to Evennia
}

/*
 * Data coming from Evennia to client. This data 
 * is always on the form of a JSON object {key:arg}
 */
dataRecv = function(event) {
    // Evennia -> client
    var data = JSON.parse(event.data);
     
    // send to be printed in element class
    for (var cmdname in data) {
        if (data.hasOwnProperty(cmdname) &&  cmdname in oob_commands) {
            try {
                oob_commands[cmdname](data);
            }
            catch(error) {
                alert("Crash in function " + cmdname + "(data): " + error);
            }
        } 
    }
}

/*
 * Input history objects
 */

historyObj = function () {
    // history object storage
    return {"current": undefined, // save the current input
            "hpos": 0,   // position in history
            "store": []}   // history steore
}
addHistory = function(obj, lastentry) {
    // Add text to the history
    if (!obj.hasOwnProperty("input_history")) {
        // create a new history object
        obj.input_history = new historyObj();
    }
    if (lastentry && obj.input_history.store && obj.input_history.store[0] != lastentry) {
        // don't store duplicates.
        obj.input_history.store.unshift(lastentry);
        obj.input_history.hpos = -1;
        obj.input_history.current = undefined;
    }
}
getHistory = function(obj, lastentry, step) {
    // step +1 or -1 in history
    if (!obj.hasOwnProperty("input_history")) {
        // create a new history object
        obj.input_history = new historyObj();
    }
    var history = obj.input_history;
    var lhist = history.store.length;
    var hpos = history.hpos + step;

    if (typeof(obj.input_history.current) === "undefined") {
        obj.input_history.current = lastentry;
    }
    if (hpos < 0) {
        // get the current but remove the cached one so it
        // can be replaced.
        obj.input_history.hpos = -1; 
        var current = obj.input_history.current;
        obj.input_history.current = undefined;
        return current;
    }
    hpos = Math.max(0, Math.min(hpos, lhist-1));
    //console.log("lhist: " + lhist + " hpos: " + hpos + " current: " + obj.input_history.current);
    obj.input_history.hpos = hpos;
    return history.store[hpos];
}


/* 
 * Initialization
 */

initialize = function() {
    
    // register events

    // single line input
    $(".input_singleline").on("submit", function(event) {
        // input from the single-line input field
        event.preventDefault(); // stop form from switching page
        var field = $(this).find("input");
        var msg = field.val();
        addHistory(this, msg);
        field.val("");
        dataSend("inputfield", msg);
        if (echo_to_textarea) {
            // echo to textfield
            toClass("textoutput", msg);
            toClass("lookoutput", msg);
            toClass("listoutput", msg);
        }
    });

    $(".input_singleline :input").on("keyup", function(event) {
        switch (event.keyCode) {
            case 13: // Enter 
                event.preventDefault();
                $(this).trigger("submit"); 
                break
            case 38: // Up
                event.preventDefault();
                var lastentry = $(this).val();
                var hist = getHistory(this.form, lastentry, 1);
                if (hist) $(this).val(hist);
                break
            case 40: // Down
                event.preventDefault();
                var lastentry = $(this).val();
                var hist = getHistory(this.form, lastentry, -1);
                if (hist) $(this).val(hist);
                break
            default:
        }
    });

    // textarea input 
   

    $(".input_multiline").on("submit", function(event) {
        // input from the textarea input
        event.preventDefault(); // stop form from switching page
        var field = $(this).find("textarea");
        var msg = field.val(); 
        addHistory(this, msg);
        field.val("");
        dataSend("inputfield", msg);
        if (echo_to_textarea) {
            // echo to textfield
            toClass("textarea", msg);
            toClass("lookarea", msg);
            toClass("listarea", msg);
        }
    });

    $(".input_multiline :input").on("keyup", function(event) {
        // Ctrl + <key> commands
        if (event.ctrlKey) {
            switch (event.keyCode) {
                case 13: // Ctrl + Enter 
                    event.preventDefault();
                    $(this).trigger("submit"); 
                    break
                case 38: // Ctrl + Up
                    event.preventDefault();
                    var lastentry = $(this).val();
                    var hist = getHistory(this.form, lastentry, 1);
                    if (hist) $(this).val(hist);
                    break
                case 40: // Ctrl + Down
                    event.preventDefault();
                    var lastentry = $(this).val();
                    var hist = getHistory(this.form, lastentry, -1);
                    if (hist) $(this).val(hist);
                    break
                default:
            }
        }
    });

    //console.log("windowsize: " + $(window).height() + " footerheight: " + $('.footer').height())
    //$(window).on("resize", function(event) {
    //    $('.textoutput').css({height:($(window).height() - 120 + "px")});
    //});

    // resizing

    // make sure textarea fills surrounding div
    //$('.textoutput').css({height:($(window).height()-$('.footer').height())+'px'});
    //$('.textoutput').css({height:($(window).height() - 120 + "px")});


    // configurations
    $(".echo").on("change", function(event) {
        // configure echo on/off checkbox button
        event.preventDefault();
        echo_to_textarea = $(this).prop("checked");
    });
    
    // initialize the websocket connection
    //websocket = new WebSocket(wsurl);
    //websocket.onopen = function(event) {};
    //websocket.onclose = function(event) {};
    //websocket.onerror = function(event) {};
    //websocket.onmessage = dataOut;
    
}

/* 
 * Kick system into gear first when 
 * the document has loaded fully.
 */

$(document).ready(function() {
    // a small timeout to stop 'loading' indicator in Chrome
    setTimeout(function () {
        initialize();
    }, 500);
    // set an idle timer to avoid proxy servers to time out on us (every 3 minutes)
    setInterval(function() {
        dataSend("textinput", "idle");
    }, 60000*3);
});

