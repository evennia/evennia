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

A


messages sent to the client is one of two modes:
  OOB("func1",args, "func2",args, ...)  - OOB command executions, this will
                                        call unique javascript functions
                                        func1(args), func2(args) etc.
  text - any other text is considered a normal text output in the main output window.

*/

//
// Custom OOB functions
// functions defined here can be called by name by the server. For
// example input OOB{"echo":(args),{kwargs}} will trigger a function named
// echo(args, kwargs). The commands the server understands is set by
// settings.OOB_PLUGIN_MODULES

(function() {
  var id = 0;
  var map = {};

  var Evennia = {
    debug: true,
    // called by the frontend to send a command to the backend
    cmd: function (cmd, params, callback) {
      var msg = params ? [cmd, [params], {}] : [cmd, [], {}];
      params.id = id++;

      log('cmd called with following args:', cmd, params, callback);

      websocket.send('OOB' + JSON.stringify(msg));

      if (typeof callback === 'function') {
        map[id] = callback;
      }
    },

    // called by the backend to emit an event to the global emitter
    emit: function (event, data) {
      if (data.id) {
        map[data.id].apply(this, [event, data]);
        delete map[data.id];
      }
      Evennia.emitter.emit(event, data);
    },

    // startup Evennia emitter and connection
    init: function (opts) {
      opts = opts || {};
      Evennia.emitter = opts.emitter || new Emitter();
      Evennia.websocket = new Connection();
    }
  };

  // wrapper for websocket setup
  var Connection = function () {
    var websocket = new WebSocket(wsurl);
    websocket.onopen = function (event) {
      Evennia.emit('socket:open', event);
    };
    websocket.onclose = function (event) {
      log('WebSocket connection closed.')
      Evennia.emit('socket:close', event);
    };
    websocket.onmessage = function (event) {
      if (typeof event.data !== 'string' && event.data.length < 0) {
        return;
      }

      // only acceptable mode is OOB
      var mode = event.data.substr(0, 3);

      if (mode === 'OOB') {
        // parse the rest of the response
        var res = JSON.parse(event.data.substr(3));
        log(res);
        var cmd = res[0];
        var args = res[1];
        Evennia.emit(cmd, args[0]);
      }
    };
    websocket.onerror = function (event) {
      log("Websocket error to ", wsurl, event);
      Evennia.emit('socket:error', data);
    };

    return websocket;
  }

  // basic emitter, can be overridden in evennia init
  var Emitter = function () {
    var map = {};

    // emit to listeners of given event
    var emit = function (event, params) {
      log('emit', event, params);
      if (map[event] && map[event] === Array) {
        map[event].forEach(function (val) {
          val.apply(this, params);
        });
      }
    };

    // bind listener to event, only allow one instance of handler
    var on = function (event, handler) {
      if (!map[event]) {
        map[event] = [];
      }
      if (map[event].indexOf(handler) >= 0) {
        return;
      }
      map[event].push(handler);
    };

    // remove handler from event
    var off = function (event, handler) {
      if (map[event]) {
        var listener = map[event].indexOf(handler);
        if (listener >= 0) {
          map[event].splice(listener, 1);
        }
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

function log() {
  if (Evennia.debug) {
    console.log(arguments);
  }
}

// Callback function - called when page has finished loading (kicks the client into gear)
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
