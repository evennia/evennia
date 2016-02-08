/*
Evenna webclient library

This javascript library handles all communication between Evennia and
whatever client front end is used.


* Evennia - library communication

The library will try to communicate with Evennia using websockets
(evennia/server/portal/webclient.py). However, if the web browser is
old and does not support websockets, it will instead fall back to a
long-polling (AJAX/COMET) type of connection
(using evennia/server/portal/webclient_ajax.py)

All messages are valid JSON array on single form: ["funcname", arg, arg,, ...] 
This represents a JS function called as funcname(arg, arg, ...)

* Front-end interface

This library makes the "Evennia" object available. It has the following
functions:


   - Evennia.init(options)
        This must be called by the frontend to intialize the library. The
        argument is an js object with the following possible keys:
            'connection': Either 'websocket' or 'comet'.
            'cmdhandler': An optional custom command handler for
                managing outgoing commands from the server. If not
                supplied, the default will be used. It must have a msg() function.
   - Evennia.msg(funcname, [args,...], callback)
        Send a command to the server. You can also provide a function
        to call with the return of the call (not all commands will return
        anything, like 'text' type commands).




Evennia websocket webclient (javascript component)

The client is composed of two parts:
 - /server/portal/websocket_client.py - the portal-side component
 - this file - the javascript component handling dynamic content

messages sent to the client is one of two modes:
  OOB("func1",args, "func2",args, ...)  - OOB command executions, this will
                                        call unique javascript functions
                                        func1(args), func2(args) etc.
  text - any other text is considered a normal text output in the main output window.

*/

(function() {
  var cmdid = 0;
  var cmdmap = {};

  var Evennia = {
    debug: true,
    // Client -> Evennia. 
    // Called by the frontend to send a command to Evennia.
    //
    // Args:
    //   cmdname (str): String identifier to call
    //   kwargs (obj): Data argument for calling as cmdname(kwargs)
    //   callback (func): If given, will be given an eventual return
    //      value from the backend.
    // 
    send: function (cmdname, kwargs, callback) {
      kwargs.cmdid = cmdid++;
      var data = kwargs ? [cmdname, kwargs] : [cmdname, {}];

      if (typeof callback === 'function') {
        this.cmdmap[cmdid] = callback;
      }
      this.connection.send(JSON.stringify(kwargs));

      log('cmd called with following args:', cmd, params, callback);
    },

    // Evennia -> Client.
    // Called by the backend to emit an event to the global emitter
    //
    // Args:
    //   event (event): Event received from Evennia
    //   data (obj):  
    //
    emit: function (cmdname, data) {
      if (data.cmdid) {
        this.cmdmap[data.cmdid].apply(this, [data]);
        delete this.cmdmap[cmddata.cmdid];
      }
      else {
        this.emitter.emit(cmdname, data);
      }
    },

    // Initializer.
    // startup Evennia emitter and connection.
    //
    // Args:
    //   opts (obj): 
    //       emitter - custom emitter. If not given,
    //          will use a default emitter. Must have 
    //          an "emit" function.
    //       connection - This defaults to a WebsocketConnection,
    //          but could also be the CometConnection or another
    //          custom protocol. Must have a 'send' method and
    //            make use of Evennia.emit to return data to Client.
    //
    init: function (kwargs) {
      kwargs = kwargs || {};
      this.emitter = kwargs.emitter || new DefaultEmitter();
      this.connection = kwargs.connection || new WebsocketConnection();
    }
  };

  // Websocket Connector
  //
  var WebsocketConnection = function () {
    var websocket = new WebSocket(wsurl);
    // Handle Websocket open event
    this.websocket.onopen = function (event) {
      log('Websocket connection openened.');
      Evennia.emit('socket:open', event);
    };
    // Handle Websocket close event
    this.websocket.onclose = function (event) {
      log('WebSocket connection closed.');
      Evennia.emit('socket:close', event);
    };
    // Handle websocket errors
    this.websocket.onerror = function (event) {
      log("Websocket error to ", wsurl, event);
      Evennia.emit('socket:error', data);
    };
    // Handle incoming websocket data
    this.websocket.onmessage = function (event) {
      var data = event.data
      if (typeof data !== 'string' && data.length < 0) {
        return;
      }
      // Parse the incoming data, send to emitter
      // Incoming data is on the form [cmdname, kwargs]
      data = JSON.parse(data);
      Evennia.emit(data[0], data[1]]);
    };
    return websocket;
  }

  // AJAX/COMET Connector
  //
  CometConnection = function() {
  
  };
    
  // Basic emitter to distribute data being sent to the client from
  // the Server. An alternative can be overridden in Evennia.init.
  //
  var DefaultEmitter = function () {
    var cmdmap = {};

    // Emit data to all listeners tied to a given cmdname
    //
    // Args:
    //   cmdname (str): Name of command, used to find
    //     all listeners to this call; each will be
    //     called as function(kwargs).
    //   kwargs (obj): Argument to the listener.
    //
    var emit = function (cmdname, kwargs) {
      log('emit', cmdname, kwargs);

      if (this.cmdmap[cmdname]) {
        this.cmdmap[cmdname].apply(this, kwargs);
        };
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
      if typeof(listener === 'function') {
          this.cmdmap[cmdname] = listener;
      }
    };

    // remove handling of this cmdname
    //
    // Args:
    //   cmdname (str): Name of event to handle
    //
    var off = function (cmdname) {
      delete this.cmdmap[cmdname]
      }
    };

    return {
      emit: emit,
      on: on,
      off: off
    };
  };

  window.Evennia = Evennia;
})();

// helper logging function
// Args:
//   msg (str): Message to log to console.
//
function log(msg) {
  if (Evennia.debug) {
    console.log(msg);
  }
}

// Called when page has finished loading (kicks the client into gear)
$(document).ready(function(){
    // remove the "no javascript" warning, since we obviously have javascript
    $('#noscript').remove();

    // a small timeout to stop 'loading' indicator in Chrome
    setTimeout(function () {
      log('Evennia initialized...')
      Evennia.init();
    }, 500);
    // set an idle timer to avoid proxy servers to time out on us (every 3 minutes)
    setInterval(function() {
      log('Idle tick.');
    }, 60000*3);
});
