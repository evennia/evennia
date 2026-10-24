/*
 * Aetos compatibility shim.
 *
 * Evennia's `evennia.js` is written for the stock webclient page, which loads
 * jQuery. It uses jQuery in exactly one place -- the last statement of the file:
 *
 *     $(document).ready(function () {
 *         setTimeout(function () { Evennia.init() }, 500);
 *     });
 *
 * That is a convenience for the stock client, which never calls `Evennia.init()`
 * itself. Aetos does call it, with its own emitter, so the auto-init is
 * redundant here -- but the reference still throws if `$` is undefined.
 *
 * Loading an 87 KB jQuery from a CDN to satisfy one call would undo the whole
 * point of Aetos being self-contained, so this shim provides the minimum that
 * call needs: a `$(document).ready(fn)` that runs `fn` when the DOM is ready.
 *
 * Scope discipline:
 *
 *   - Only defined if `$` is absent. A game that legitimately loads jQuery for
 *     its own pages keeps the real one; this never shadows it.
 *   - Implements `ready` and nothing else. It is not a jQuery replacement, and
 *     must not grow into one. If Aetos ever appears to need more of jQuery, the
 *     right answer is to use the platform API instead.
 *
 * `Evennia.init()` is idempotent (it returns early when already initialised), so
 * the deferred call this enables is a harmless no-op after Aetos has booted.
 */

(function (window, document) {
    "use strict";

    if (typeof window.$ !== "undefined") {
        return;
    }

    function onReady(callback) {
        if (typeof callback !== "function") {
            return;
        }
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", function () { callback(); });
        } else {
            // Already past DOMContentLoaded; match jQuery's behaviour of still
            // running the callback rather than dropping it.
            window.setTimeout(callback, 0);
        }
    }

    window.$ = function () {
        return { ready: onReady };
    };

    // A few libraries feature-detect via jQuery.fn. Present but empty, so such a
    // check fails cleanly rather than throwing.
    window.$.fn = {};

})(window, document);
