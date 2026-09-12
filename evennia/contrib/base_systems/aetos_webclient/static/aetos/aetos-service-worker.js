/*
 * Aetos service worker.  Milestone M20.
 *
 * Caches the client's own static files so it loads instantly and fails
 * legibly. It caches **nothing else**, and the reasoning for every refusal is
 * below because a service worker is the one part of a web client that keeps
 * running after the page is gone.
 *
 * IT NEVER CACHES GAME CONTENT.
 *
 * Not the transcript, not a sync payload, not a tell, not a room description.
 * A cache is a data store, and blueprint section 63 requires the player's local
 * data to be enumerable and clearable. A worker quietly holding last night's
 * conversation would be invisible in the privacy panel, would survive "clear
 * all Aetos data", and would be readable by anyone who picks up the device.
 *
 * The enforcement is structural rather than a filter: the fetch handler
 * declines to handle anything that is not a same-origin GET for a path this
 * worker recognises as a client asset. There is no branch that could cache a
 * response from the game.
 *
 * IT NEVER TOUCHES THE WEBSOCKET.
 *
 * Service workers do not intercept WebSocket traffic, and nothing here tries
 * to. Evennia's transport is untouched, which is a constraint this project has
 * held since M1 and is not relaxing for a cache.
 *
 * STALE CODE IS THE REAL HAZARD.
 *
 * A worker serving yesterday's JavaScript against an upgraded server presents
 * as features mysteriously missing -- which nobody diagnoses as caching. So the
 * cache name carries `ASSET_VERSION`, and activation deletes every Aetos cache
 * that is not the current one. A version bump orphans the old cache instead of
 * merging into it.
 *
 * NETWORK FIRST, NOT CACHE FIRST.
 *
 * The opposite of the usual PWA advice, and deliberate. Cache-first is right
 * for an app whose assets are immutable and content-addressed; Aetos's are
 * neither, and a player on a working connection should be running the code the
 * server currently has. The cache is a fallback for when the network fails,
 * which is exactly the situation it was added for.
 */

/* global self, caches, fetch */

"use strict";

//: Replaced at serve time by the template tag, so the cache name changes with
//: every asset version. The literal is the development fallback.
var ASSET_VERSION = "__AETOS_ASSET_VERSION__";
var CACHE_NAME = "aetos-shell-" + ASSET_VERSION;

/*
 * Paths this worker will answer for.
 *
 * An allowlist of prefixes rather than "anything same-origin". A game's own
 * pages, its admin, its media and its API are not Aetos's to intercept, and a
 * worker that cached them would be making decisions on behalf of software it
 * knows nothing about.
 */
var CACHEABLE_PREFIXES = ["/static/aetos/", "/static/webclient/"];

function isCacheable(request) {
    if (request.method !== "GET") {
        return false;
    }
    var url;
    try {
        url = new URL(request.url);
    } catch (err) {
        return false;
    }
    if (url.origin !== self.location.origin) {
        return false;
    }
    return CACHEABLE_PREFIXES.some(function (prefix) {
        return url.pathname.indexOf(prefix) === 0;
    });
}

self.addEventListener("install", function (event) {
    /*
     * Nothing is pre-cached.
     *
     * A precache list is a second copy of the template's script tags, and the
     * two drift -- the copy goes stale, the worker caches a file that no longer
     * exists, and installation fails for everybody. Populating on first use
     * costs one uncached load and cannot disagree with reality.
     */
    event.waitUntil(self.skipWaiting ? Promise.resolve() : Promise.resolve());
});

self.addEventListener("activate", function (event) {
    event.waitUntil(
        caches.keys().then(function (names) {
            return Promise.all(names.map(function (name) {
                // Every Aetos cache except this version's. Other caches on the
                // origin belong to the game and are left alone.
                if (name.indexOf("aetos-") === 0 && name !== CACHE_NAME) {
                    return caches.delete(name);
                }
                return Promise.resolve(false);
            }));
        }).then(function () {
            return self.clients.claim();
        })
    );
});

self.addEventListener("fetch", function (event) {
    if (!isCacheable(event.request)) {
        // Not ours. The browser handles it exactly as if no worker existed.
        return;
    }

    event.respondWith(
        fetch(event.request).then(function (response) {
            /*
             * Only cache a clean success.
             *
             * A 404 or a 500 cached as though it were the file is a failure
             * that outlives its cause -- the server gets fixed and the client
             * keeps serving the error.
             */
            if (response && response.ok && response.type === "basic") {
                var copy = response.clone();
                caches.open(CACHE_NAME).then(function (cache) {
                    cache.put(event.request, copy);
                }).catch(function () {
                    // A full or unavailable cache is not worth failing a
                    // request over. The player gets the network response.
                });
            }
            return response;
        }).catch(function () {
            // Offline. This is the whole point of the worker: the client's own
            // reconnecting state rather than the browser's error page.
            return caches.match(event.request).then(function (cached) {
                return cached || Response.error();
            });
        })
    );
});

self.addEventListener("message", function (event) {
    /*
     * The only message handled, and only because the player asked.
     *
     * An update never applies itself mid-session: reloading under somebody in
     * the middle of a fight, or a sentence they are composing on the
     * communication board, would be a data-loss bug wearing a feature's
     * clothes.
     */
    if (event.data && event.data.type === "aetos-skip-waiting") {
        self.skipWaiting();
    }
});
