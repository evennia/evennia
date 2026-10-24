/*
 * Aetos protocol capture.  Addendum C.12.
 *
 * Records a structured session so client behaviour can be reproduced later
 * without recreating the game situation that caused it.
 *
 * WHY THIS IS RELEASE-QUALITY TOOLING AND NOT A DEBUGGING LUXURY. The hardest
 * things in this client to test are the ones that depend on *sequence and
 * timing*: announcement prioritisation, flood control, Review Mode, reconnect
 * behaviour, threshold crossings. None of those can be exercised reliably
 * against a live game, because you cannot ask a MUD to produce twelve combat
 * messages in two seconds on demand, twice, identically.
 *
 * A capture can. That is why C.13 lists screen-reader bug reproduction among
 * the mandatory use cases: an accessibility defect that happened once is
 * otherwise a story rather than a test.
 *
 * WHAT IT RECORDS, AND WHAT IT REFUSES TO. Game traffic, yes: protocol version,
 * manifest, normalized inbound events, text, outbound commands, connection
 * markers, relative timings.
 *
 * The player's own data, never. Not notes, relationships, macros, aliases,
 * scripts, accessibility preferences, AAC preferences or reminders -- none of
 * which is protocol traffic in the first place, and all of which would turn a
 * bug report into a disclosure. The exclusion is structural: capture observes
 * the pipeline and the dispatcher, and neither of those ever carries local
 * data.
 *
 * PRIVACY IS NOT THE SAME AS SECRECY. A capture is meant to be shared with a
 * maintainer, so the honest thing is to say plainly what is in it rather than
 * to hope nobody looks. `describe()` produces that summary, and export refuses
 * to be silent about it.
 */

(function (window) {
    "use strict";

    //: Schema version. A replay engine that does not recognise this refuses the
    //: file rather than guessing at it -- a misread capture produces a
    //: convincing wrong answer, which is worse than no answer.
    var FORMAT_VERSION = 1;

    /*
     * How much to record.
     *
     * The default is the minimum that makes a state bug reproducible. Recording
     * everything by default would mean every casual capture carried game text
     * the developer then has to read before sharing.
     */
    var LEVELS = ["state", "state+text", "full"];
    var DEFAULT_LEVEL = "state+text";

    //: Hard cap. A capture left running overnight should not become the reason
    //: a tab dies (A.56 -- and say so rather than truncating quietly).
    var MAX_RECORDS = 20000;

    /*
     * Keys that must never appear in a captured payload.
     *
     * Belt and braces: the pipeline should never carry these, and if a game's
     * provider puts one in a payload anyway, it is redacted rather than
     * recorded. A developer capturing their own game should not have to audit
     * their own provider before sharing a bug report.
     */
    var SENSITIVE_KEYS = [
        "password", "passwd", "secret", "token", "api_key", "apikey",
        "private_key", "credential", "session_key", "sessionid", "csrf"
    ];

    function looksSensitive(key) {
        var lowered = String(key).toLowerCase();
        for (var i = 0; i < SENSITIVE_KEYS.length; i++) {
            if (lowered.indexOf(SENSITIVE_KEYS[i]) !== -1) {
                return true;
            }
        }
        return false;
    }

    /*
     * Copy a payload, redacting anything credential-shaped.
     *
     * Depth-limited, because a provider can hand back a recursive structure and
     * a capture that hangs the tab is worse than a capture that says it gave
     * up.
     */
    function sanitize(value, depth) {
        var level = depth || 0;
        if (level > 8 || value === null || typeof value !== "object") {
            return value;
        }
        if (Array.isArray(value)) {
            return value.slice(0, 500).map(function (entry) {
                return sanitize(entry, level + 1);
            });
        }
        var clean = {};
        Object.keys(value).forEach(function (key) {
            clean[key] = looksSensitive(key) ? "<redacted>" : sanitize(value[key], level + 1);
        });
        return clean;
    }

    function createCapture(services) {
        var settings = services || {};
        var now = settings.now || function () { return Date.now(); };

        var records = [];
        var recording = false;
        var startedAt = 0;
        var level = DEFAULT_LEVEL;
        var truncated = 0;

        function stamp() {
            return Math.max(0, Math.round(now() - startedAt));
        }

        function push(record) {
            if (!recording) {
                return null;
            }
            if (records.length >= MAX_RECORDS) {
                truncated += 1;
                return null;
            }
            record.t = stamp();
            records.push(record);
            return record;
        }

        /* --- Control ----------------------------------------------------- */

        function start(options) {
            var opts = options || {};
            level = LEVELS.indexOf(opts.level) === -1 ? DEFAULT_LEVEL : opts.level;
            records = [];
            truncated = 0;
            startedAt = now();
            recording = true;

            // The header is the first record rather than a wrapper object, so
            // the file stays append-only: a capture interrupted by a crashed
            // tab is still a valid, readable prefix.
            records.push({
                t: 0,
                kind: "meta",
                format: FORMAT_VERSION,
                level: level,
                protocol: settings.protocolVersion || null,
                aetos: settings.clientVersion || null
            });

            if (settings.manifest) {
                records.push({ t: 0, kind: "manifest", payload: sanitize(settings.manifest()) });
            }
            return true;
        }

        function stop() {
            recording = false;
            return records.length;
        }

        /* --- Recording --------------------------------------------------- */

        /*
         * An inbound event, taken from the pipeline.
         *
         * Deliberately fed from the *canonical* event rather than from the
         * transport, so a replay reproduces what the client decided the message
         * meant -- which is the layer bugs actually live in.
         */
        function recordInbound(event) {
            if (!recording) {
                return null;
            }
            var record = {
                kind: "in",
                category: event.category,
                id: event.id
            };
            if (event.structuredData) {
                record.payload = sanitize(event.structuredData);
            }
            if (event.originalText && level !== "state") {
                // Game text is excluded at "state" level, because a state bug
                // rarely needs it and a developer sharing a capture should not
                // have to redact their own roleplay first.
                record.text = event.originalText;
            }
            return push(record);
        }

        function recordOutbound(command) {
            if (!recording || level === "state") {
                return null;
            }
            return push({ kind: "out", command: String(command) });
        }

        function recordConnection(state) {
            return push({ kind: "connection", state: state });
        }

        /*
         * A human note in the timeline.
         *
         * "NVDA interrupted here" is worth more than any amount of inferred
         * timing, and it is the thing a tester can contribute that the client
         * cannot observe about itself. Markers do not affect replay.
         */
        function mark(note) {
            return push({ kind: "marker", note: String(note).slice(0, 200) });
        }

        /* --- Reading out -------------------------------------------------- */

        function toJsonl() {
            return records.map(function (record) {
                return JSON.stringify(record);
            }).join("\n");
        }

        /*
         * What this capture contains, in words.
         *
         * Shown before export, because a capture is meant to be handed to
         * somebody else and "trust me" is not a privacy model. Saying plainly
         * what is and is not in the file is what makes it safe to share
         * without reading all of it.
         */
        function describe() {
            var counts = {};
            records.forEach(function (record) {
                counts[record.kind] = (counts[record.kind] || 0) + 1;
            });
            return {
                format: FORMAT_VERSION,
                level: level,
                records: records.length,
                truncated: truncated,
                durationMs: records.length ? records[records.length - 1].t : 0,
                counts: counts,
                contains: [
                    "structured game state",
                    "resource and effect payloads",
                    level === "state" ? null : "game text you saw",
                    level === "state" ? null : "commands you sent",
                    "connection events"
                ].filter(Boolean),
                excludes: [
                    "passwords and authentication tokens",
                    "your notes and relationship tags",
                    "your macros, aliases, triggers and scripts",
                    "your accessibility and AAC preferences",
                    "anything stored only in this browser"
                ]
            };
        }

        return {
            start: start,
            stop: stop,
            recordInbound: recordInbound,
            recordOutbound: recordOutbound,
            recordConnection: recordConnection,
            mark: mark,
            toJsonl: toJsonl,
            describe: describe,
            records: function () { return records.slice(); },
            isRecording: function () { return recording; },
            level: function () { return level; }
        };
    }

    window.AetosCapture = {
        create: createCapture,
        sanitize: sanitize,
        looksSensitive: looksSensitive,
        FORMAT_VERSION: FORMAT_VERSION,
        LEVELS: LEVELS.slice(),
        MAX_RECORDS: MAX_RECORDS,
        SENSITIVE_KEYS: SENSITIVE_KEYS.slice()
    };

})(window);
