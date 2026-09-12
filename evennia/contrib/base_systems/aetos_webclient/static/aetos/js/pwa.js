/*
 * Aetos progressive web app shell.  Milestone M20.
 *
 * Makes the client installable and makes a lost connection legible, without
 * pretending a MUD works offline.
 *
 * WHAT "OFFLINE" HONESTLY MEANS HERE.
 *
 * Nothing. A MUD is a live connection to a server; there is no offline mode and
 * there never will be. So the service worker caches the **shell** -- the
 * JavaScript, CSS and template that make up the client -- and nothing else.
 *
 * The value of that is narrow and real: a player whose train enters a tunnel
 * gets Aetos's own "reconnecting" state instead of the browser's dinosaur, and
 * when signal returns the client is already loaded and reconnects immediately
 * rather than re-downloading itself first. That is the whole benefit and it is
 * worth stating plainly, because "works offline" is exactly the sort of claim a
 * PWA invites and it would be false.
 *
 * GAME CONTENT IS NEVER CACHED.
 *
 * Not the transcript, not the room, not a sync payload, not a tell. A service
 * worker cache is a store like any other, and blueprint 2.3 says the game
 * server holds no player profile while section 63 says local data is the
 * player's and is enumerable. A cache quietly holding last night's conversation
 * would be neither -- invisible in the privacy panel, surviving a "clear all
 * data", and readable by anyone with the device.
 *
 * So the fetch handler only ever answers for same-origin static assets, and the
 * privacy panel can clear the cache like everything else.
 *
 * THE UPDATE TRAP, WHICH IS THE REASON MOST OF THIS CODE EXISTS.
 *
 * A service worker that serves stale JavaScript against an upgraded server is
 * worse than no service worker: the failure presents as features mysteriously
 * missing, which nobody diagnoses as a caching problem. `ASSET_VERSION` already
 * exists for exactly this reason on ordinary asset URLs, so the cache is keyed
 * by it -- a version bump orphans the old cache rather than merging into it.
 *
 * And an update is never applied silently mid-session. Reloading the client
 * under somebody who is in the middle of a fight, or a conversation, or a
 * sentence they are composing on the communication board, would be a data-loss
 * bug wearing a feature's clothes. Aetos says an update is ready and lets the
 * player choose when.
 */

(function (window, document) {
    "use strict";

    //: Where the worker lives. Scoped to the webclient path rather than the
    //: site root: a game's own pages are not Aetos's to intercept.
    var WORKER_URL = "aetos-service-worker.js";

    function createPwa(services) {
        var settings = services || {};
        var announce = settings.announce || function () {};

        var registration = null;
        var updateReady = false;
        var installPrompt = null;

        /*
         * Register the worker.
         *
         * Failure is not reported to the player. An unavailable service worker
         * costs them nothing they would notice -- the client works identically,
         * it just reloads from the network -- and a warning about a technology
         * they did not ask for would be noise.
         */
        function register() {
            if (!window.navigator || !window.navigator.serviceWorker) {
                return Promise.resolve(null);
            }
            if (window.location.protocol !== "https:" &&
                    window.location.hostname !== "localhost" &&
                    window.location.hostname !== "127.0.0.1") {
                // Service workers require a secure context. Not an error worth
                // surfacing: a game served over plain HTTP has bigger problems
                // and this is not the place to raise them.
                return Promise.resolve(null);
            }
            return window.navigator.serviceWorker.register(WORKER_URL)
                .then(function (reg) {
                    registration = reg;
                    watchForUpdates(reg);
                    return reg;
                })
                .catch(function () {
                    return null;
                });
        }

        /*
         * Notice a new version, and say so rather than acting on it.
         *
         * `skipWaiting` is deliberately not called here. The new worker waits
         * until the player reloads, which they do when it suits them.
         */
        function watchForUpdates(reg) {
            if (reg.waiting) {
                announceUpdate();
            }
            reg.addEventListener("updatefound", function () {
                var installing = reg.installing;
                if (!installing) {
                    return;
                }
                installing.addEventListener("statechange", function () {
                    if (installing.state === "installed" &&
                            window.navigator.serviceWorker.controller) {
                        announceUpdate();
                    }
                });
            });
        }

        function announceUpdate() {
            if (updateReady) {
                return;
            }
            updateReady = true;
            announce(
                "A new version of the client is ready. It will be used the next " +
                "time you reload -- nothing has changed yet.",
                { category: "system", priority: "important" }
            );
        }

        /*
         * Apply a waiting update, on request.
         *
         * The player asked, so the reload is expected rather than something
         * that happened to them.
         */
        function applyUpdate() {
            if (!registration || !registration.waiting) {
                return false;
            }
            registration.waiting.postMessage({ type: "aetos-skip-waiting" });
            window.location.reload();
            return true;
        }

        /* --- Installation ------------------------------------------------- */

        /*
         * Capture the install prompt rather than letting the browser show it.
         *
         * An unprompted "install this app?" banner over a game somebody is
         * playing is an interruption they did not ask for. Captured here, it
         * becomes a palette command they can find when they want it -- which is
         * also the only way a keyboard-only player could reach it, since the
         * browser's own banner is not always focusable.
         */
        function watchForInstall() {
            window.addEventListener("beforeinstallprompt", function (event) {
                event.preventDefault();
                installPrompt = event;
            });
            window.addEventListener("appinstalled", function () {
                installPrompt = null;
                announce("Aetos installed.", { category: "system" });
            });
        }

        function canInstall() {
            return installPrompt !== null;
        }

        function install() {
            if (!installPrompt) {
                return Promise.resolve(false);
            }
            var prompt = installPrompt;
            installPrompt = null;
            prompt.prompt();
            return prompt.userChoice.then(function (choice) {
                return choice && choice.outcome === "accepted";
            }).catch(function () {
                return false;
            });
        }

        /* --- Privacy ------------------------------------------------------ */

        /*
         * Delete every cache Aetos created.
         *
         * Wired into the privacy panel's "clear all data", because a cache the
         * panel does not clear is data a player was told they had deleted.
         */
        function clearCaches() {
            if (!window.caches || !window.caches.keys) {
                return Promise.resolve(0);
            }
            return window.caches.keys().then(function (names) {
                var ours = names.filter(function (name) {
                    return name.indexOf("aetos-") === 0;
                });
                return Promise.all(ours.map(function (name) {
                    return window.caches.delete(name);
                })).then(function () { return ours.length; });
            }).catch(function () { return 0; });
        }

        /*
         * What is cached, for the privacy panel.
         *
         * Counted rather than described: the panel says "17 client files", not
         * a list of URLs nobody wants to read. It matters only that the number
         * is real and that clearing it works.
         */
        function cacheSummary() {
            if (!window.caches || !window.caches.keys) {
                return Promise.resolve({ available: false, files: 0 });
            }
            return window.caches.keys().then(function (names) {
                var ours = names.filter(function (name) {
                    return name.indexOf("aetos-") === 0;
                });
                return Promise.all(ours.map(function (name) {
                    return window.caches.open(name).then(function (cache) {
                        return cache.keys();
                    }).then(function (keys) { return keys.length; });
                })).then(function (counts) {
                    return {
                        available: true,
                        // The version is read from the cache name rather than
                        // passed in: the worker owns it, and a copy here could
                        // disagree with what is actually cached -- which is the
                        // one thing a cache report must not do.
                        version: (ours[0] || "").replace("aetos-shell-", "") || null,
                        caches: ours.length,
                        files: counts.reduce(function (a, b) { return a + b; }, 0)
                    };
                });
            }).catch(function () {
                return { available: false, files: 0 };
            });
        }

        function start() {
            watchForInstall();
            return register();
        }

        return {
            start: start,
            register: register,
            applyUpdate: applyUpdate,
            updateAvailable: function () { return updateReady; },
            canInstall: canInstall,
            install: install,
            clearCaches: clearCaches,
            cacheSummary: cacheSummary
        };
    }

    window.AetosPwa = { create: createPwa, WORKER_URL: WORKER_URL };

})(window, document);
