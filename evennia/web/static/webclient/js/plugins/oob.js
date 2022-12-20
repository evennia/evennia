/*
 *
 * OOB Plugin
 * enables '##send { "command", [ args ], { kwargs } }' as a way to inject OOB instructions
 *
 */
let oob_plugin = (function () {

    //
    // Check outgoing text for handtyped/injected JSON OOB instruction
    var onSend = function (line) {
        if (line.length > 7 && line.substr(0, 7) == "##send ") {
            // send a specific oob instruction ["cmdname",[args],{kwargs}]
            line = line.slice(7);
            var cmdarr = JSON.parse(line);
            var cmdname = cmdarr[0];
            var args = cmdarr[1];
            var kwargs = cmdarr[2];
            log(cmdname, args, kwargs);
            return (cmdname, args, kwargs);
        }
    }

    //
    // init function
    var init = function () {
        console.log('OOB Plugin Initialized.');
    }

    return {
        init: init,
        onSend: onSend,
    }
})()
plugin_handler.add('oob', oob_plugin);
