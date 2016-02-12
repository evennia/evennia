/*
Evenna webclient library

This javascript library handles all communication between Evennia and
whatever client front end is used.

The library will try to communicate with Evennia using websockets
(evennia/server/portal/webclient.py). However, if the web browser is
old and does not support websockets, it will instead fall back to a
long-polling (AJAX/COMET) type of connection (using
evennia/server/portal/webclient_ajax.py)

All messages is a valid JSON array on single form: ["cmdname",
kwargs], where kwargs is a JSON object that will be used as argument
to call the cmdname function.

This library makes the "Evennia" object available. It has the
following official functions:

   - Evennia.init(options)
        This can be called by the frontend to intialize the library. The
        argument is an js object with the following possible keys:
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
    - When receiving data from the Server (always [cmdname, kwargs]), this must be
        JSON-unpacked and the result redirected to Evennia.emit(data[0], data[1]).
An "emitter" object must have a function
    - emit(cmdname, kwargs) - this will be called by the backend.
    - The default emitter also has the following methods:
        - on(cmdname, listener) - this ties a listener to the backend. This function
            should be called as listener(kwargs) when the backend calls emit.
        - off(cmdname) - remove the listener for this cmdname.

*/

(function() {
    var cmdid = 0;
    var cmdmap = {};

    var Evennia = {

        debug: true,
        initialized: false,

        // Initialize.
        // startup Evennia emitter and connection.
        //
        // Args:
        //   opts (obj):
        //       emitter - custom emitter. If not given,
        //          will use a default emitter. Must have
        //          an "emit" function.
        //       connection - This defaults to using either
        //          a WebsocketConnection or a CometConnection
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
                if (!this.connection) {
                    this.connection = new AjaxCometConnection();
                }
            } else {
                this.connection = new AjaxCometConnection();
            }
            log('Evennia initialized.')
        },

        // Client -> Evennia.
        // Called by the frontend to send a command to Evennia.
        //
        // Args:
        //   cmdname (str): String identifier to call
        //   kwargs (obj): Data argument for calling as cmdname(kwargs)
        //   callback (func): If given, will be given an eventual return
        //      value from the backend.
        //
        msg: function (cmdname, args, kwargs, callback) {
            kwargs.cmdid = cmdid++;
            var outargs = args ? args : [];
            var outkwargs = kwargs ? kwargs : {};
            var data = [cmdname, outargs, outkwargs];

            if (typeof callback === 'function') {
                cmdmap[cmdid] = callback;
            }
            log('client msg sending: ', data);
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
    // the Server. An alternative can be overridden in Evennia.init.
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
            log("DefaultEmitter.emit:", cmdname, args, kwargs);
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
            log("DefaultEmitter.on", cmdname, listener);
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
        return {emit:emit, on:on, off:off}
    };

    // Websocket Connector
    //
    var WebsocketConnection = function () {
        log("Trying websocket");
        var websocket = new WebSocket(wsurl);
        // Handle Websocket open event
        websocket.onopen = function (event) {
            log('Websocket connection openened. ', event);
            Evennia.emit('socket:open', [], event);
        };
        // Handle Websocket close event
        websocket.onclose = function (event) {
            log('WebSocket connection closed.');
            Evennia.emit('socket:close', [], event);
        };
        // Handle websocket errors
        websocket.onerror = function (event) {
            log("Websocket error to ", wsurl, event);
            Evennia.emit('socket:error', [], event);
            if (websocket.readyState === websocket.CLOSED) {
                log("Websocket failed. Falling back to Ajax...");
                Evennia.connection = AjaxCometConnection();
            }
        };
        // Handle incoming websocket data [cmdname, kwargs]
        websocket.onmessage = function (event) {
            var data = event.data;
            if (typeof data !== 'string' && data.length < 0) {
                return;
            }
            // Parse the incoming data, send to emitter
            // Incoming data is on the form [cmdname, args, kwargs]
            data = JSON.parse(data);
            log("incoming " + data);
            Evennia.emit(data[0], data[1], data[2]);
        };
        websocket.msg = function(data) {
            // send data across the wire. Make sure to json it.
            websocket.send(JSON.stringify(data));
        };

        return websocket;
    };

    // AJAX/COMET Connector
    //
    AjaxCometConnection = function() {
        log("Trying ajax ...");
        var client_hash = '0';
        // Send Client -> Evennia. Called by Evennia.send.
        var msg = function(cmdname, args, kwargs) {
            $.ajax({type: "POST", url: "/webclientdata",
                   async: true, cache: false, timeout: 30000,
                   dataType: "json",
                   data: {mode:'input', msg: [cmdname, args, kwargs], 'suid': client_hash},
                   success: function(data) {},
                   error: function(req, stat, err) {
                       log("COMET: Server returned error. " + err);
                   }
           });
        };

        // Receive Evennia -> Client. This will start an asynchronous
        // Long-polling request. It will either timeout or receive data
        // from the 'webclientdata' url. Either way a new polling request
        // will immediately be started.
        var poll = function() {
            $.ajax({type: "POST", url: "/webclientdata",
                    async: true, cache: false, timeout: 30000,
                    dataType: "json",
                    data: {mode: 'receive', 'suid': client_hash},
                    success: function(data) {
                       Evennia.emit(data[0], data[1], data[2])
                    },
                    error: function() {
                        poll()  // timeout; immediately re-poll
                    }
            });
        };

        // Initialization will happen when this Connection is created.
        // We need to store the client id so Evennia knows to separate
        // the clients.
        $.ajax({type: "POST", url: "/webclientdata",
                async: true, cache: false, timeout: 50000,
                datatype: "json",
                success: function(data) {
                    client_hash = data.suid;
                    poll();
                },
                error: function(req, stat, err) {
                    log("Connection error: " + err);
                }
        });

        return {msg: msg, poll: poll};
    };

    window.Evennia = Evennia;

})(); // end of auto-calling Evennia object defintion

// helper logging function
// Args:
//   msg (str): Message to log to console.
//
function log() {
  if (Evennia.debug) {
    console.log(JSON.stringify(arguments));
  }
}

// Called when page has finished loading (kicks the client into gear)
$(document).ready(function() {
    setTimeout( function () {
        Evennia.init()
        },
        500
    );
});
