/*
 *
 * Desktop Notifications Plugin
 *
 */
let notifications_plugin = (function () {
    // Notifications
    var unread = 0;
    var originalTitle = document.title;
    var focused = true;
    var favico;

    var onBlur = function (e) {
        focused = false;
    }

    //
    // Notifications for unfocused window
    var onFocus = function (e) {
        focused = true;
        document.title = originalTitle;
        unread = 0;
        favico.badge(0);
    }

    //
    // on receiving new text from the server, if we are not focused, send a notification to the desktop
    var onText = function (args, kwargs) {
        if(!focused) {
            // Changes unfocused browser tab title to number of unread messages
            unread++;
            favico.badge(unread);
            document.title = "(" + unread + ") " + originalTitle;
            if ("Notification" in window) {
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

        return false;
    }

    //
    // required init function
    var init = function () {
        if ("Notification" in window) {
            Notification.requestPermission();
        }

        favico = new Favico({
            animation: 'none'
        });

        $(window).blur(onBlur);
        $(window).focus(onFocus);

        console.log('Notifications Plugin Initialized.');
    }

    return {
        init: init,
        onText: onText,
    }
})()
plugin_handler.add('notifications', notifications_plugin);
