/*
 * Aetos command queue.
 *
 * Every chained sequence of commands goes through here (blueprint section 28):
 * macros, click-to-walk routes, and later triggers and scripts. One queue rather
 * than one per feature, so the safety properties are implemented once instead of
 * being re-derived -- and forgotten -- by each caller.
 *
 * THE QUEUE GRANTS NO AUTHORITY.
 *
 * Each step is exactly the text a player could type, sent through the ordinary
 * dispatcher. A five-command macro is five ordinary commands, and the server
 * rules on each one. Nothing here bypasses a lock, a cooldown or a permission.
 *
 * Safety properties, each of which exists because the alternative is a player
 * ending up somewhere they did not choose:
 *
 *   - ORDER is preserved.
 *   - LENGTH is capped, so a runaway sequence cannot spam a game.
 *   - A FAILED STEP STOPS THE REST, when failure is detectable. Continuing to
 *     fire commands after a step failed is how a player walks into a room they
 *     never intended to enter.
 *   - DISCONNECT PAUSES rather than discarding, and queued commands are NOT
 *     dumped on reconnect without the caller asking (section 60).
 *   - DOUBLE EXECUTION is prevented: starting a sequence while one is running
 *     replaces it rather than interleaving two.
 */

(function (window) {
    "use strict";

    //: Hard cap from blueprint section 27. A macro is a convenience, not a
    //: scripting language; five is the documented limit.
    var MAX_MACRO_COMMANDS = 5;

    //: Ceiling on any queued sequence, including routes, which are longer.
    var MAX_QUEUE_LENGTH = 100;

    //: Default gap between commands. Zero would send a burst the server sees as
    //: one tick, which defeats any verification step.
    var DEFAULT_DELAY = 250;

    var MIN_DELAY = 0;
    var MAX_DELAY = 10000;

    function createQueue(services) {
        var send = services.send;
        var isConnected = services.isConnected || function () { return true; };
        var announce = services.announce || function () {};

        var active = null;

        function state() {
            if (!active) {
                return { running: false, remaining: 0, label: null, paused: false };
            }
            return {
                running: true,
                label: active.label,
                remaining: active.commands.length - active.index,
                total: active.commands.length,
                paused: active.paused === true
            };
        }

        function stop(reason, announceIt) {
            if (!active) {
                return false;
            }
            if (active.timer !== null) {
                window.clearTimeout(active.timer);
            }
            var finished = active;
            active = null;
            if (reason && announceIt !== false) {
                announce(reason);
            }
            if (finished.onFinish) {
                finished.onFinish({ completed: false, reason: reason });
            }
            return true;
        }

        function step() {
            if (!active) {
                return;
            }

            if (active.index >= active.commands.length) {
                var finished = active;
                active = null;
                if (finished.announceCompletion !== false) {
                    announce(finished.completionMessage || "Done.");
                }
                if (finished.onFinish) {
                    finished.onFinish({ completed: true });
                }
                return;
            }

            if (!isConnected()) {
                // Pause, not discard. The caller decides whether to resume;
                // silently firing the rest on reconnect could act on a world
                // that has moved on.
                active.paused = true;
                announce("Queued commands paused: disconnected.");
                return;
            }

            var command = active.commands[active.index];
            var before = active.verify ? active.verify.snapshot() : null;
            active.index += 1;
            send(command);

            active.timer = window.setTimeout(function () {
                if (!active) {
                    return;
                }
                active.timer = null;

                if (active.verify) {
                    var outcome = active.verify.check(before, command);
                    if (!outcome.ok) {
                        stop(outcome.reason || ("Stopped: " + command + " did not work."));
                        return;
                    }
                }
                step();
            }, active.delay);
        }

        /*
         * Run a sequence of commands.
         *
         * `verify` is optional. When given, it must expose `snapshot()` and
         * `check(before, command)`; the queue stops if a step reports failure.
         * Verification is structural -- did the world change as expected -- not
         * text matching, which would be fragile and language-specific.
         */
        function run(commands, options) {
            var opts = options || {};
            var list = (commands || [])
                .map(function (entry) { return String(entry || "").trim(); })
                .filter(Boolean)
                .slice(0, opts.maxLength || MAX_QUEUE_LENGTH);

            if (!list.length) {
                return false;
            }

            // Replace rather than interleave. Two sequences running at once
            // would produce an order neither caller intended.
            if (active) {
                stop(null, false);
            }

            active = {
                commands: list,
                index: 0,
                label: opts.label || null,
                delay: Math.min(MAX_DELAY, Math.max(MIN_DELAY,
                    opts.delay === undefined ? DEFAULT_DELAY : opts.delay)),
                verify: opts.verify || null,
                onFinish: opts.onFinish || null,
                completionMessage: opts.completionMessage,
                announceCompletion: opts.announceCompletion,
                timer: null,
                paused: false
            };

            if (opts.announceStart !== false) {
                announce((opts.label ? opts.label + ": " : "") +
                    "running " + list.length +
                    (list.length === 1 ? " command." : " commands."));
            }

            step();
            return true;
        }

        /*
         * Resume a sequence paused by a disconnect.
         *
         * Deliberately explicit. Section 60 forbids dumping accumulated commands
         * on reconnect without a policy, so reconnecting does not resume by
         * itself -- something must ask.
         */
        function resume() {
            if (!active || !active.paused) {
                return false;
            }
            if (!isConnected()) {
                return false;
            }
            active.paused = false;
            announce("Resuming queued commands.");
            step();
            return true;
        }

        function cancel() {
            return stop("Queued commands cancelled.");
        }

        return {
            MAX_MACRO_COMMANDS: MAX_MACRO_COMMANDS,
            MAX_QUEUE_LENGTH: MAX_QUEUE_LENGTH,
            run: run,
            cancel: cancel,
            resume: resume,
            stop: stop,
            state: state,
            isRunning: function () { return !!active; }
        };
    }

    window.AetosQueue = {
        create: createQueue,
        MAX_MACRO_COMMANDS: MAX_MACRO_COMMANDS,
        MAX_QUEUE_LENGTH: MAX_QUEUE_LENGTH,
        DEFAULT_DELAY: DEFAULT_DELAY
    };

})(window);
