/*
 * Aetos timers.
 *
 * "after 30 seconds, do X" and "every 5 minutes, do X" (blueprint section 31).
 *
 * TIMERS ARE OFF BY DEFAULT.
 *
 * Unlike macros, a timer acts without the player being present at the keyboard.
 * That is close enough to unattended play that many games forbid it outright, so
 * `automation.timers` defaults to **false** and a game must opt in. The client
 * honours that: with timers disallowed, none can be created or fired.
 *
 * Everything a timer sends goes through the shared command queue, so the same
 * caps, ordering and stop-on-failure rules apply as to any other automation.
 */

(function (window) {
    "use strict";

    var MIN_INTERVAL = 1000;
    var MAX_INTERVAL = 24 * 60 * 60 * 1000;
    var MAX_COMMANDS = 5;
    var MAX_ACTIVE = 20;

    function createTimers(services) {
        var storage = services.storage;
        var queue = services.queue;
        var announce = services.announce || function () {};
        var isAllowed = services.isAllowed || function () { return false; };

        var running = {};

        function normalize(timer) {
            var commands = (timer.commands || [])
                .map(function (entry) { return String(entry || "").trim(); })
                .filter(Boolean)
                .slice(0, MAX_COMMANDS);
            var interval = Number(timer.interval);
            if (!isFinite(interval)) {
                interval = MIN_INTERVAL;
            }
            return {
                id: timer.id || String(timer.label || "timer").toLowerCase(),
                label: String(timer.label || "Timer").slice(0, 80),
                // Clamped rather than rejected: a player asking for 10ms wants
                // "as fast as allowed", not an error, and a game must not be
                // hammered because someone typed a zero too few.
                interval: Math.min(MAX_INTERVAL, Math.max(MIN_INTERVAL, interval)),
                repeat: timer.repeat === true,
                commands: commands,
                enabled: timer.enabled !== false,
                group: String(timer.group || "")
            };
        }

        function save(timer) {
            if (!storage) {
                return window.Promise.resolve(null);
            }
            var record = normalize(timer);
            if (!record.commands.length) {
                return window.Promise.reject(new Error("A timer needs at least one command."));
            }
            return storage.put("triggers", "timer:" + record.id, record).then(function () {
                return record;
            });
        }

        function all() {
            if (!storage) {
                return window.Promise.resolve([]);
            }
            return storage.all("triggers").then(function (rows) {
                return rows
                    .filter(function (row) { return String(row.key).indexOf("timer:") === 0; })
                    .map(function (row) { return row.value; });
            });
        }

        function remove(id) {
            stop(id);
            return storage
                ? storage.remove("triggers", "timer:" + id)
                : window.Promise.resolve(false);
        }

        function fire(timer) {
            if (!isAllowed()) {
                // Policy can change mid-session if the game reloads its
                // settings. A running timer must notice rather than keep going.
                stop(timer.id);
                announce("Timers are no longer allowed by this game; " +
                    timer.label + " stopped.");
                return;
            }
            queue.run(timer.commands, {
                label: timer.label,
                announceStart: false,
                announceCompletion: false
            });
        }

        function start(timer) {
            if (!isAllowed()) {
                announce("This game does not allow timers.");
                return false;
            }
            if (Object.keys(running).length >= MAX_ACTIVE) {
                announce("Too many timers are already running.");
                return false;
            }
            stop(timer.id);

            var handle;
            if (timer.repeat) {
                handle = window.setInterval(function () { fire(timer); }, timer.interval);
            } else {
                handle = window.setTimeout(function () {
                    fire(timer);
                    // A one-shot timer removes itself, so a stale entry cannot
                    // accumulate and look like it is still pending.
                    delete running[timer.id];
                }, timer.interval);
            }
            running[timer.id] = { handle: handle, repeat: timer.repeat, timer: timer };
            return true;
        }

        function stop(id) {
            var entry = running[id];
            if (!entry) {
                return false;
            }
            if (entry.repeat) {
                window.clearInterval(entry.handle);
            } else {
                window.clearTimeout(entry.handle);
            }
            delete running[id];
            return true;
        }

        function stopAll() {
            Object.keys(running).forEach(stop);
        }

        function active() {
            return Object.keys(running);
        }

        return {
            MIN_INTERVAL: MIN_INTERVAL,
            MAX_INTERVAL: MAX_INTERVAL,
            MAX_ACTIVE: MAX_ACTIVE,
            normalize: normalize,
            save: save,
            all: all,
            remove: remove,
            start: start,
            stop: stop,
            stopAll: stopAll,
            active: active
        };
    }

    window.AetosTimers = {
        create: createTimers,
        MIN_INTERVAL: MIN_INTERVAL,
        MAX_ACTIVE: MAX_ACTIVE
    };

})(window);
