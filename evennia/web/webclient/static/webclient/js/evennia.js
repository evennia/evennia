/*
Evenna webclient library

This javascript library handles all communication between Evennia and
whatever client front end is used.

The library will try to communicate with Evennia using websockets
(evennia/server/portal/webclient.py). However, if the web browser is
old and does not support websockets, it will instead fall back to a
long-polling (AJAX/COMET) type of connection (using
evennia/server/portal/webclient_ajax.py)

All messages are valid JSON arrays on this single form:

    ["cmdname", args, kwargs],

where args is an JSON array and kwargs is a JSON object. These will be both
used as arguments emitted to a callback named "cmdname" as cmdname(args, kwargs).

This library makes the "Evennia" object available. It has the
following official functions:

   - Evennia.init(options)
        This stores the connections/emitters and creates the websocket/ajax connection.
        This can be called as often as desired - the lib will still only be
        initialized once. The argument is an js object with the following possible keys:
            'connection': This defaults to Evennia.WebsocketConnection but
                can also be set to Evennia.CometConnection for backwards
                compatibility. See below.
            'emitter': An optional custom command handler for distributing
                data from the server to suitable listeners. If not given,
                a default will be used.
   - Evennia.msg(funcname, [args,...], callback)
        Send a command to the server. You can also provide a function
        to call with the return of the call (note that commands will
        not return anything unless specified to do so server-side).

A "connection" object must have the method
    - msg(data) - this should relay data to the Server. This function should itself handle
        the conversion to JSON before sending across the wire.
    - When receiving data from the Server (always data = [cmdname, args, kwargs]), this must be
        JSON-unpacked and the result redirected to Evennia.emit(data[0], data[1], data[2]).
An "emitter" object must have a function
    - emit(cmdname, args, kwargs) - this will be called by the backend and is expected to
        relay the data to its correct gui element.
    - The default emitter also has the following methods:
        - on(cmdname, listener) - this ties a listener to the backend. This function
            should be called as listener(args, kwargs) when the backend calls emit.
        - off(cmdname) - remove the listener for this cmdname.
*/

(function() {
    "use strict"
    var cmdid = 0;
    var cmdmap = {};

    var Evennia = {

        debug: true,
        initialized: false,

        // Initialize the Evennia object with emitter and connection.
        //
        // Args:
        //   opts (obj):
        //       emitter - custom emitter. If not given,
        //          will use a default emitter. Must have
        //          an "emit" function.
        //       connection - This defaults to using either
        //          a WebsocketConnection or a AjaxCometConnection
        //          depending on what the browser supports. If given
        //          it must have a 'msg' method and make use of
        //          Evennia.emit to return data to Client.
        //
        init: function(opts) {
            if (this.initialized) {
                // make it safe to call multiple times.
                return;
            }
            this.initialized = true;

            opts = opts || {};
            this.emitter = opts.emitter || new DefaultEmitter();

            if (opts.connection) {
               this.connection = opts.connection;
            }
            else if (window.WebSocket && wsactive) {
                this.connection = new WebsocketConnection();
            } else {
                this.connection = new AjaxCometConnection();
            }
            log('Evennia initialized.')
        },

        // Connect to the Evennia server.
        // Re-establishes the connection after it is lost.
        //
        connect: function() {
            if (this.connection.isOpen()) {
                // Already connected.
                return;
            }
            this.connection.connect();
            log('Evenna reconnecting.')
        },

        // Returns true if the connection is open.
        //
        isConnected: function () {
          return this.connection.isOpen();
        },

        // client -> Evennia.
        // called by the frontend to send a command to Evennia.
        //
        // args:
        //   cmdname (str): String identifier to call
        //   kwargs (obj): Data argument for calling as cmdname(kwargs)
        //   callback (func): If given, will be given an eventual return
        //      value from the backend.
        //
        msg: function (cmdname, args, kwargs, callback) {
            if (!cmdname) {
                return;
            }
            if (kwargs) {
                kwargs.cmdid = cmdid++;
            }
            var outargs = args ? args : [];
            var outkwargs = kwargs ? kwargs : {};
            var data = [cmdname, outargs, outkwargs];

            if (typeof callback === 'function') {
                cmdmap[cmdid] = callback;
            }
            this.connection.msg(data);

        },

        // Evennia -> Client.
        // Called by the backend to send the data to the
        // emitter, which in turn distributes it to its
        // listener(s).
        //
        // Args:
        //   event (event): Event received from Evennia
        //   args (array): Arguments to listener
        //   kwargs (obj): keyword-args to listener
        //
        emit: function (cmdname, args, kwargs) {
            if (kwargs.cmdid) {
                cmdmap[kwargs.cmdid].apply(this, [args, kwargs]);
                delete cmdmap[kwargs.cmdid];
            }
            else {
                this.emitter.emit(cmdname, args, kwargs);
            }
        },

    }; // end of evennia object


    // Basic emitter to distribute data being sent to the client from
    // the Server. An alternative can be overridden by giving it
    // in Evennia.init({emitter:myemitter})
    //
    var DefaultEmitter = function () {
        var listeners = {};
        // Emit data to all listeners tied to a given cmdname.
        // If the cmdname is not recognized, call a listener
        // named 'default' with arguments [cmdname, args, kwargs].
        // If no 'default' is found, ignore silently.
        //
        // Args:
        //   cmdname (str): Name of command, used to find
        //     all listeners to this call; each will be
        //     called as function(kwargs).
        //   kwargs (obj): Argument to the listener.
        //
        var emit = function (cmdname, args, kwargs) {
            if (listeners[cmdname]) {
                listeners[cmdname].apply(this, [args, kwargs]);
            }
            else if (listeners["default"]) {
                listeners["default"].apply(this, [cmdname, args, kwargs]);
            }
        };

        // Bind listener to event
        //
        // Args:
        //   cmdname (str): Name of event to handle.
        //   listener (function): Function taking one argument,
        //     to listen to cmdname events.
        //
        var on = function (cmdname, listener) {
            if (typeof(listener === 'function')) {
                listeners[cmdname] = listener;
            };
        };

        // remove handling of this cmdname
        //
        // Args:
        //   cmdname (str): Name of event to handle
        //
        var off = function (cmdname) {
            delete listeners[cmdname]
        };
        return {emit:emit, on:on, off:off};
    };

    // Websocket Connector
    //
    var WebsocketConnection = function () {
        log("Trying websocket ...");
        var open = false;
        var ever_open = false;
        var websocket = null;
        var wsurl = window.wsurl;
        var csessid = window.csessid;

        var connect = function() {
            if (websocket && websocket.readyState != websocket.CLOSED) {
                // No-op if a connection is already open.
                return;
            }
            // Important - we pass csessid tacked on the url
            websocket = new WebSocket(wsurl + '?' + csessid);

            // Handle Websocket open event
            websocket.onopen = function (event) {
                open = true;
                ever_open = true;
                Evennia.emit('connection_open', ["websocket"], event);
            };
            // Handle Websocket close event
            websocket.onclose = function (event) {
                if (ever_open) {
                    // only emit if websocket was ever open at all
                    Evennia.emit('connection_close', ["websocket"], event);
                }
                open = false;
            };
            // Handle websocket errors
            websocket.onerror = function (event) {
                if (websocket.readyState === websocket.CLOSED) {
                    if (ever_open) {
                        // only emit if websocket was ever open at all.
                        log("Websocket failed.")
                        Evennia.emit('connection_error', ["websocket"], event);
                    }
                    else {
                        // only fall back to AJAX if we never got an open socket.
                        log("Websocket failed. Falling back to Ajax...");
                        Evennia.connection = AjaxCometConnection();
                    }
                    open = false;
                }
            };
            // Handle incoming websocket data [cmdname, args, kwargs]
            websocket.onmessage = function (event) {
                var data = event.data;
                if (typeof data !== 'string' && data.length < 0) {
                    return;
                }
                // Parse the incoming data, send to emitter
                // Incoming data is on the form [cmdname, args, kwargs]
                data = JSON.parse(data);
                Evennia.emit(data[0], data[1], data[2]);
            };
        }

        var msg = function(data) {
            // send data across the wire. Make sure to json it.
            websocket.send(JSON.stringify(data));
        };

        var close = function() {
            // tell the server this connection is closing (usually
            // tied to when the client window is closed). This
            // Makes use of a websocket-protocol specific instruction.
            websocket.send(JSON.stringify(["websocket_close", [], {}]));
            open = false;
        }

        var isOpen = function() {
            return open;
        }

        connect();

        return {connect: connect, msg: msg, close: close, isOpen: isOpen};
    };

    // AJAX/COMET Connector
    //
    var AjaxCometConnection = function() {
        log("Trying ajax ...");
        var open = false;
        var stop_polling = false;
        var is_closing = false;
        var csessid = window.csessid;

        // initialize connection, send csessid
        var init = function() {
            $.ajax({type: "POST", url: "/webclientdata",
                    async: true, cache: false, timeout: 50000,
                    datatype: "json",
                    data: {mode: "init", csessid: csessid},

                    success: function(data) {
                        open = true;
                        data = JSON.parse(data);
                        log ("connection_open", ["AJAX/COMET"], data);
                        stop_polling = false;
                        poll();
                    },
                    error: function(req, stat, err) {
                        Evennia.emit("connection_error", ["AJAX/COMET init error"], err);
                        // Also emit a close event so that the COMET API mirrors the websocket API.
                        Evennia.emit("connection_close", ["AJAX/COMET init close"], err);
                        log("AJAX/COMET: Connection error: " + err);
                        stop_polling = true;
                    }
            });
        };

        // Send Client -> Evennia. Called by Evennia.msg
        var msg = function(data, inmode) {
            log("ajax.msg:", data, JSON.stringify(data));
            $.ajax({type: "POST", url: "/webclientdata",
                   async: true, cache: false, timeout: 30000,
                   dataType: "json",
                   data: {mode: inmode == null ? 'input' : inmode,
                          data: JSON.stringify(data), 'csessid': csessid},
                   success: function(req, stat, err) {
                       stop_polling = false;
                   },
                   error: function(req, stat, err) {
                       Evennia.emit("connection_error", ["AJAX/COMET send error"], err);
                       log("AJAX/COMET: Server returned error.",req,stat,err);
                       stop_polling = true;
                   }
           });
        };

        // Receive Evennia -> Client. This will start an asynchronous
        // Long-polling request. It will either timeout or receive data
        // from the 'webclientdata' url. Either way a new polling request
        // will immediately be started.
        var poll = function() {
            $.ajax({type: "POST", url: "/webclientdata",
                    async: true, cache: false, timeout: 60000,
                    dataType: "json",
                    data: {mode: 'receive', 'csessid': csessid},
                    success: function(data) {
                        // log("ajax data received:", data);
                        if (data[0] === "ajax_keepalive") {
                            // special ajax keepalive check - return immediately
                            msg("", "keepalive");
                        } else {
                            // not a keepalive
                            Evennia.emit(data[0], data[1], data[2]);
                        }
                        stop_polling = false;
                        poll(); // immiately start a new request
                    },
                    error: function(req, stat, err) {
                        if (stat !== "timeout") {
                            // Any other error besides a timeout is abnormal
                            Evennia.emit("connection_error", ["AJAX/COMET receive error"], err);
                            log("AJAX/COMET: Server returned error on receive.",req,stat,err);
                            stop_polling = true;
                        }
                        else {
                            // We'd expect to see a keepalive message rather than
                            // a timeout. Ping the server to see if it's still there.
                            msg(["text", ["idle"], {}], "input");
                        }

                        if (stop_polling) {
                            // An error of some kind occurred.
                            // Close the connection, if possible.
                            close();
                        }
                        else {
                            poll(); // timeout; immediately re-poll
                                    // don't trigger an emit event here,
                                    // this is normal for ajax/comet
                        }
                    }
            });
        };

        // Kill the connection and do house cleaning on the server.
        var close = function webclient_close(){
            if (is_closing || !(open)) {
                // Already closed or trying to close.
                return;
            }
            stop_polling = true;
            is_closing = true;
            $.ajax({
                type: "POST",
                url: "/webclientdata",
                async: true,
                cache: false,
                timeout: 50000,
                dataType: "json",
                data: {mode: 'close', 'csessid': csessid},

                success: function(data){
                    is_closing = false;
                    open = false;
                    Evennia.emit("connection_close", ["AJAX/COMET"], {});
                    log("AJAX/COMET connection closed cleanly.")
                },
                error: function(req, stat, err){
                    is_closing = false;
                    Evennia.emit("connection_error", ["AJAX/COMET close error"], err);
                    // Also emit a close event so that the COMET API mirrors the websocket API.
                    Evennia.emit("connection_close", ["AJAX/COMET close unclean"], err);
                    open = false;
                }
            });
        };

        var isOpen = function () {
            return !(is_closing || !(open));
        }

        // init
        init();

        return {connect: init, msg: msg, close: close, isOpen: isOpen};
    };

    window.Evennia = Evennia;

})(); // end of auto-calling Evennia object defintion

// helper logging function (requires a js dev-console in the browser)
function log() {
  if (Evennia.debug) {
    console.log(JSON.stringify(arguments));
  }
}

// Called when page has finished loading (kicks the client into gear)
$(document).ready(function() {
    setTimeout( function () {
        // the short timeout supposedly causes the load indicator
        // in Chrome to stop spinning
        Evennia.init()
        },
        500
    );
});
