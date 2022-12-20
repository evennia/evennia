/*
 * Evennia example Webclient multimedia outputs plugin
 *
 *     PLUGIN ORDER PREREQS:
 *          loaded after:
 *              webclient_gui.js
 *              option2.js
 *          loaded before:
 *
 *
 *     To use, in evennia python code:
 *         target.msg( image="URL" )
 *         target.msg( audio="URL" )
 *         target.msg( video="URL" )
 *     or, if you prefer tagged routing:
 *         target.msg( image=("URL",{'type':'tag'}) )
 *
 *
 *   Note: users probably don't _want_ more than one pane to end up with multimedia tags...
 *         But to allow proper tagged message routing, this plugin doesn't explicitly deny it.
 */
let multimedia_plugin = (function () {
    //
    var image = function (args, kwargs) {
        let options = window.options;
        if( !("mm_image" in options) || options["mm_image"] === false ) { return; }

        var mwins = window.plugins["goldenlayout"].routeMessage(args, kwargs);
        mwins.forEach( function (mwin) {
            mwin.append("<img src='"+ args[0] +"'/>");
            mwin.scrollTop(mwin[0].scrollHeight);
        });
    }

    //
    var audio = function (args, kwargs) {
        let options = window.options;
        if( !("mm_audio" in options) || options["mm_audio"] === false ) { return; }

        // create an HTML5 audio control (only .mp3 is fully compatible with all major browsers)
        var mwins = window.plugins["goldenlayout"].routeMessage(args, kwargs);
        mwins.forEach( function (mwin) {
            mwin.append("<audio controls='' autoplay='' style='height:17px;width:175px'>" +
                        "<source src='"+ args[0] +"'/>" +
                        "</audio>");
            mwin.scrollTop(mwin[0].scrollHeight);
        });
    }

    //
    var video = function (args, kwargs) {
        let options = window.options;
        if( !("mm_video" in options) || options["mm_video"] === false ) { return; }

        // create an HTML5 video element (only h264 .mp4 is compatible with all major browsers)
        var mwins = window.plugins["goldenlayout"].routeMessage(args, kwargs);
        mwins.forEach( function (mwin) {
            mwin.append("<video controls='' autoplay=''>" +
                        "<source src='"+ args[0] +"'/>" +
                        "</video>");
            mwin.scrollTop(mwin[0].scrollHeight);
        });
    }

    //
    var onOptionsUI = function (parentdiv) {
        let options = window.options;
        var checked;

        checked = options["mm_image"] ? "checked='checked'" : "";
        var mmImage = $( [ "<label>",
                               "<input type='checkbox' data-setting='mm_image' " + checked + "'>",
                               " Enable multimedia image (png/gif/etc) messages",
                               "</label>"
                             ].join("") );

        checked = options["mm_audio"] ? "checked='checked'" : "";
        var mmAudio = $( [ "<label>",
                               "<input type='checkbox' data-setting='mm_audio' " + checked + "'>",
                               " Enable multimedia audio (mp3) messages",
                               "</label>"
                             ].join("") );

        checked = options["mm_video"] ? "checked='checked'" : "";
        var mmVideo = $( [ "<label>",
                               "<input type='checkbox' data-setting='mm_video' " + checked + "'>",
                               " Enable multimedia video (h264 .mp4) messages",
                               "</label>"
                             ].join("") );
        mmImage.on("change", window.plugins["options2"].onOptionCheckboxChanged);
        mmAudio.on("change", window.plugins["options2"].onOptionCheckboxChanged);
        mmVideo.on("change", window.plugins["options2"].onOptionCheckboxChanged);

        parentdiv.append(mmImage);
        parentdiv.append(mmAudio);
        parentdiv.append(mmVideo);
    }

    //
    // Mandatory plugin init function
    var init = function () {
        let options = window.options;
        options["mm_image"] = true;
        options["mm_audio"] = true;
        options["mm_video"] = true;

        let Evennia = window.Evennia;
        Evennia.emitter.on("image", image); // capture "image" commands
        Evennia.emitter.on("audio", audio); // capture "audio" commands
        Evennia.emitter.on("video", video); // capture "video" commands
        console.log('Multimedia plugin initialized');
    }

    return {
        init: init,
        onOptionsUI: onOptionsUI,
    }
})();
plugin_handler.add("multimedia_plugin", multimedia_plugin);
