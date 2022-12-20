/*
 *
 * Evennia Webclient default outputs plugin
 *
 */
let defaultout_plugin = (function () {

    //
    // By default add all unclaimed onText messages to the #messagewindow <div> and scroll
    var onText = function (args, kwargs) {
        // append message to default pane, then scroll so latest is at the bottom.
        var mwin = $("#messagewindow");
        var cls = kwargs == null ? 'out' : kwargs['cls'];
        mwin.append("<div class='" + cls + "'>" + args[0] + "</div>");
        var scrollHeight = mwin.parent().parent().prop("scrollHeight");
        mwin.parent().parent().animate({ scrollTop: scrollHeight }, 0);

        return true;
    }

    //
    // By default just show the prompt.
    var onPrompt = function (args, kwargs) {
        // show prompt on every input pane
        var prompts = $('.prompt');

        for( var x=0; x < prompts.length; x++ ) {
            var prmpt = $( prompts[x] );
            var sibling = prmpt.siblings().first();

            prmpt.addClass("out")
                .html(args[0])
                .css({'height':'1.5em'});

            sibling.css({'height':'calc(100% - 1.5em)'});
        }

        return true;
    }

    //
    // By default just show an error for the Unhandled Event.
    var onUnknownCmd = function (args, kwargs) {
        var mwin = $("#messagewindow");
        mwin.append(
            "<div class='msg err'>"
            + "Error or Unhandled event:<br>"
            + cmdname + ", "
            + JSON.stringify(args) + ", "
            + JSON.stringify(kwargs) + "<p></div>");
        mwin.scrollTop(mwin[0].scrollHeight);

        return true;
    }

    //
    // Mandatory plugin init function
    var init = function () {
        console.log('DefaultOut initialized');
    }

    return {
        init: init,
        onText: onText,
        onPrompt: onPrompt,
        onUnknownCmd: onUnknownCmd,
    }
})();
plugin_handler.add('defaultout', defaultout_plugin);
