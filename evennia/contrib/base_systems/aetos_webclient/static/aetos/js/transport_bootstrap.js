/*
 * Aetos -- transport bootstrap.
 *
 * Defines the four globals `evennia.js` reads: `wsactive`, `csessid`, `wsurl`
 * and `cuid`. Their names and semantics match Evennia's stock webclient base
 * template exactly, because this file exists to feed Evennia's own transport
 * unchanged.
 *
 * WHY THIS IS A FILE AND NOT AN INLINE SCRIPT.
 *
 * Until M26 these four lines lived in an inline `<script>` in the page, which
 * is the obvious place for values the template renders. It was also the *only*
 * inline script in the entire client -- and one inline script is all it takes
 * to force a game into `script-src 'unsafe-inline'`, which is the same as
 * having no script policy at all.
 *
 * So the values come through `<meta>` tags instead and are read here. That is a
 * slightly longer way to say the same thing, and it buys the whole client a
 * real Content-Security-Policy. See `csp.py`.
 *
 * ORDERING. This script is deferred, like every other, and is listed before
 * `evennia.js`. Deferred scripts run in document order, so the globals exist
 * before anything reads them. `async` would not guarantee that, which is why
 * nothing here uses it.
 */

(function () {
    "use strict";

    /*
     * Read one transport parameter.
     *
     * Returns null rather than "" for a missing tag, so that a genuinely empty
     * value and an absent one can be told apart -- they mean different things
     * for `csessid`, where false and "" behave differently in `evennia.js`.
     */
    function meta(name) {
        var element = document.querySelector('meta[name="' + name + '"]');
        if (!element) {
            return null;
        }
        var content = element.getAttribute("content");
        return content === null || content === "" ? null : content;
    }

    window.wsactive = meta("aetos-websocket-active") === "true";

    // `false`, not "", when the view supplied no session id: `evennia.js`
    // tests it for truthiness and an empty string would be a different kind of
    // absent than the stock template produces.
    var sessid = meta("aetos-browser-sessid");
    window.csessid = sessid === null ? false : sessid;

    /*
     * An explicit `websocket_url` wins; otherwise it is built from this page's
     * hostname and the configured port, which is what the stock template does.
     *
     * The hostname comes from the page rather than from a setting on purpose: a
     * game reached through a proxy or an SSH tunnel is reached at the name the
     * player typed, not the one the server knows itself by.
     */
    var url = meta("aetos-websocket-url");
    window.wsurl = url !== null
        ? url
        : "ws://" + window.location.hostname + ":" + meta("aetos-websocket-port");

    /*
     * Distinguishes multiple tabs of the same browser session.
     *
     * Not a security value and deliberately not generated with `crypto`: it
     * only has to differ between two tabs of one browser, and Evennia treats it
     * as a label rather than as a credential.
     */
    window.cuid = (function () {
        function chunk() {
            return Math.random().toString(36).substring(2, 15);
        }
        return chunk() + chunk();
    })();
})();
