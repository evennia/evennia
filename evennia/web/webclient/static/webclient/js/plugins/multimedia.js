/*
 *
 * Evennia Webclient multimedia outputs plugin
 *
 *     in evennia python code:
 *
 *         target.msg( image="URL" )
 *         target.msg( audio="URL" )
 *         target.msg( video="URL" )
 *
 */
let multimedia_plugin = (function () {
    //
    var image = function (args, kwargs) {
        var mwin = $("#messagewindow");
        mwin.append("<img src='"+ args[0] +"'/>");
        mwin.scrollTop(mwin[0].scrollHeight);
    }

    var audio = function (args, kwargs) {
        // create an HTML5 audio control (only .mp3 is fully compatible with all major browsers)
        var mwin = $("#messagewindow");
        mwin.append("<audio controls='' autoplay='' style='height:17px;width:175px'>" +
                    "<source src='"+ args[0] +"'/>" +
                    "</audio>");
        mwin.scrollTop(mwin[0].scrollHeight);
    }

    var video = function (args, kwargs) {
        // create an HTML5 video element (only h264 .mp4 is compatible with all major browsers)
        var mwin = $("#messagewindow");
        mwin.append("<video controls='' autoplay=''>" +
                    "<source src='"+ args[0] +"'/>" +
                    "</video>");
        mwin.scrollTop(mwin[0].scrollHeight);
    }

    //
    // Mandatory plugin init function
    var init = function () {
        Evennia = window.Evennia;
        Evennia.emitter.on('image', image); // capture "image" commands
        Evennia.emitter.on('audio', audio); // capture "audio" commands
        Evennia.emitter.on('video', video); // capture "video" commands
        console.log('Multimedia plugin initialized');
    }

    return {
        init: init,
    }
})();
plugin_handler.add('multimedia_plugin', multimedia_plugin);

