/*
 * Aetos protocol replay.  Addendum C.13.
 *
 * Feeds a captured session back through the client.
 *
 * THE ONE RULE THAT MAKES THIS WORTH HAVING: replay uses **the same seams as
 * live data**. Records go into `pipeline.ingest()`, exactly where the websocket
 * puts them. There is no parallel "fake UI" path, and there must never be one --
 * a harness that exercises different code from production tests the harness.
 *
 * That is also what makes replay a *testing* tool rather than a demo. If the
 * ordering guarantee from E0 holds during replay, it holds in production,
 * because it is the same pipeline object.
 *
 * WHAT REPLAY IS FOR. Everything that depends on sequence and timing and cannot
 * be produced on demand by a real game: announcement prioritisation and pacing,
 * flood control, Review Mode, reconnect, threshold crossings, map transitions,
 * and the reproduction of a screen-reader bug that happened once to somebody
 * else.
 *
 * DETERMINISM. Given the same capture, client version and preferences, the same
 * normalized state transitions. Anything clock-dependent takes an injectable
 * clock, because a test that depends on `Date.now()` is a test that fails on a
 * slow morning.
 *
 * Step mode matters more than it looks. Watching one event at a time is how you
 * find out that two announcements collapsed into one, or that a widget updated
 * before the state it was reading -- neither of which is visible at speed.
 */

(function (window) {
    "use strict";

    //: Playback speeds. `instant` skips waiting entirely; `step` waits for the
    //: caller to ask for each record.
    var SPEEDS = { "1x": 1, "2x": 2, "4x": 4, instant: 0 };

    function parseJsonl(text) {
        var records = [];
        var problems = [];
        String(text || "").split("\n").forEach(function (line, index) {
            var trimmed = line.trim();
            if (!trimmed) {
                return;
            }
            try {
                records.push(JSON.parse(trimmed));
            } catch (err) {
                // One malformed line must not cost the whole capture. A
                // truncated file -- which is what a crashed tab produces -- is
                // still worth replaying up to the point it stops.
                problems.push({ line: index + 1, error: err.message });
            }
        });
        return { records: records, problems: problems };
    }

    function createReplay(services) {
        var settings = services || {};
        var pipeline = settings.pipeline || null;
        var now = settings.now || function () { return Date.now(); };
        var schedule = settings.schedule || function (fn, ms) {
            return window.setTimeout(fn, ms);
        };
        var cancel = settings.cancel || function (handle) {
            window.clearTimeout(handle);
        };

        var records = [];
        var index = 0;
        var running = false;
        var handle = null;
        var speed = 1;
        var listeners = [];
        var meta = null;

        function notify(kind, detail) {
            listeners.forEach(function (listener) {
                try {
                    listener({ kind: kind, index: index, total: records.length, detail: detail });
                } catch (err) {
                    if (window.console) {
                        window.console.error("Aetos replay: listener failed", err);
                    }
                }
            });
        }

        /*
         * Load a capture.
         *
         * A format version the engine does not know is **refused**, not
         * best-guessed. A misread capture produces a convincing wrong answer,
         * and a convincing wrong answer during a bug hunt costs more than an
         * honest refusal.
         */
        function load(text) {
            var parsed = parseJsonl(text);
            var header = parsed.records[0];

            if (!header || header.kind !== "meta") {
                return { ok: false, reason: "Not an Aetos capture: no meta record." };
            }
            if (header.format !== window.AetosCapture.FORMAT_VERSION) {
                return {
                    ok: false,
                    reason: "Capture format " + header.format +
                        " cannot be replayed by this client (expects " +
                        window.AetosCapture.FORMAT_VERSION + ")."
                };
            }

            meta = header;
            records = parsed.records;
            index = 0;
            return {
                ok: true,
                meta: header,
                records: records.length,
                problems: parsed.problems
            };
        }

        /*
         * Apply one record.
         *
         * Inbound records go through `pipeline.ingest` -- the live seam. Nothing
         * here reaches into the store or a widget directly, which is the whole
         * point.
         *
         * Outbound records are NOT replayed as commands. A replay must never
         * send anything to a server: the capture is a recording of what a player
         * did, and re-issuing it would be acting on their behalf against a game
         * that has moved on. They are surfaced to listeners so a viewer can show
         * them in the timeline.
         */
        function apply(record) {
            if (!record) {
                return null;
            }
            switch (record.kind) {
            case "in":
                if (pipeline) {
                    pipeline.ingest({
                        kind: record.payload ? "sync" : "text",
                        category: record.category,
                        text: record.text || "",
                        payload: record.payload || null
                    });
                }
                break;
            case "out":
            case "marker":
            case "connection":
            case "manifest":
            case "meta":
                // Surfaced, not enacted.
                break;
            default:
                break;
            }
            notify("record", record);
            return record;
        }

        /* --- Transport ---------------------------------------------------- */

        function step() {
            if (index >= records.length) {
                running = false;
                notify("end");
                return null;
            }
            var record = records[index];
            index += 1;
            apply(record);
            return record;
        }

        function scheduleNext() {
            if (!running || index >= records.length) {
                running = false;
                notify("end");
                return;
            }
            var previous = records[index - 1];
            var next = records[index];
            var gap = Math.max(0, (next.t || 0) - ((previous && previous.t) || 0));
            var wait = speed > 0 ? gap / speed : 0;

            handle = schedule(function () {
                step();
                scheduleNext();
            }, wait);
        }

        function play(speedName) {
            if (!records.length) {
                return false;
            }
            speed = Object.prototype.hasOwnProperty.call(SPEEDS, speedName)
                ? SPEEDS[speedName]
                : 1;
            running = true;
            notify("play", { speed: speedName || "1x" });

            if (speed === 0) {
                // Instant: drain synchronously. Used by the browser QA suites,
                // where waiting out a three-minute combat log would make the
                // test useless.
                while (index < records.length) {
                    step();
                }
                running = false;
                notify("end");
                return true;
            }
            scheduleNext();
            return true;
        }

        function pause() {
            running = false;
            if (handle !== null) {
                cancel(handle);
                handle = null;
            }
            notify("pause");
            return true;
        }

        function reset() {
            pause();
            index = 0;
            notify("reset");
            return true;
        }

        function subscribe(listener) {
            if (typeof listener !== "function") {
                return function () {};
            }
            listeners.push(listener);
            return function () {
                var position = listeners.indexOf(listener);
                if (position !== -1) {
                    listeners.splice(position, 1);
                }
            };
        }

        return {
            load: load,
            play: play,
            pause: pause,
            step: step,
            reset: reset,
            subscribe: subscribe,
            meta: function () { return meta; },
            position: function () { return index; },
            total: function () { return records.length; },
            isRunning: function () { return running; }
        };
    }

    window.AetosReplay = {
        create: createReplay,
        parseJsonl: parseJsonl,
        SPEEDS: SPEEDS
    };

})(window);
