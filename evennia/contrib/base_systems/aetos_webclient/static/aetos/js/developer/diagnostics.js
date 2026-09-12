/*
 * Aetos diagnostic reports.  Addendum C.17.
 *
 * Everything a maintainer needs to understand a bug, and nothing that belongs
 * to the person reporting it.
 *
 * WHY THIS EXISTS. The alternative is a maintainer asking twelve questions --
 * which browser, which Evennia, which providers, was the manifest right, what
 * was the last thing that happened -- and a reporter answering them one at a
 * time over three days. Or, worse, pasting their whole console, which is how
 * private conversations end up in public issue trackers.
 *
 * WHAT IT CONTAINS. Versions, browser, enabled features, manifest capabilities,
 * widget list, connection state, recent event **types**, provider and binding
 * errors, validation findings.
 *
 * WHAT IT CANNOT CONTAIN. Notes, relationships, macros, aliases, triggers,
 * scripts, chat, tells, reminders, AAC history, accessibility preferences,
 * credentials. Not filtered out at the end -- never gathered. The report is
 * assembled from a fixed list of sources, none of which is the local data
 * store, so there is no path by which a note reaches it.
 *
 * ACCESSIBILITY PREFERENCES ARE EXCLUDED DELIBERATELY. A.73 and A.74: a bug
 * report that said `screenReader: true` would disclose a disability to whoever
 * reads the issue, and a player should never have to choose between reporting a
 * bug and keeping that to themselves. If a report is *about* an accessibility
 * feature, the reporter can say so in their own words.
 *
 * RECENT EVENT TYPES, NOT RECENT EVENTS. "12 combat, 3 tell, 1 room" tells a
 * maintainer the shape of what was happening. The text of the tells tells them
 * something that is none of their business.
 *
 * NOTHING IS SENT. The report is built locally and shown in full. Opening a
 * GitHub issue may prefill the body; it never submits.
 */

(function (window) {
    "use strict";

    //: How many recent events to summarise by type.
    var RECENT_WINDOW = 100;

    //: Errors kept for the report. Bounded, because a game with a broken
    //: provider produces one per sync and a report should be readable.
    var MAX_ERRORS = 20;

    /*
     * Accept a list or a function returning one.
     *
     * The widget list is not known when this module is created -- the registry
     * does not exist yet -- so the caller passes an accessor and it is called
     * at report time. An earlier version took an array and the caller assigned
     * over it afterwards, which did nothing at all: the closure still held the
     * empty array it was given.
     */
    function resolve(source) {
        try {
            var value = typeof source === "function" ? source() : source;
            return Array.isArray(value) ? value.slice() : [];
        } catch (err) {
            return [];
        }
    }

    function createDiagnostics(services) {
        var settings = services || {};
        var errors = [];

        /*
         * Record a client-side failure.
         *
         * Called from the pipeline's error handler and the provider paths. The
         * message and stack are kept; nothing else about the event is, because
         * the payload that caused it may contain game text.
         */
        function record(source, error, detail) {
            if (errors.length >= MAX_ERRORS) {
                return null;
            }
            var entry = {
                source: String(source || "unknown"),
                message: error && error.message ? String(error.message) : String(error),
                stack: error && error.stack ? String(error.stack).split("\n").slice(0, 6) : null,
                detail: detail ? String(detail) : null
            };
            errors.push(entry);
            return entry;
        }

        /*
         * Summarise the canonical log by category.
         *
         * Counts only. The shape of recent activity is diagnostic; its content
         * is the player's.
         */
        function recentEventTypes() {
            var log = settings.canonicalLog;
            if (!log || typeof log.all !== "function") {
                return {};
            }
            var counts = {};
            log.all().slice(-RECENT_WINDOW).forEach(function (event) {
                counts[event.category] = (counts[event.category] || 0) + 1;
            });
            return counts;
        }

        function browserSummary() {
            var nav = window.navigator || {};
            return {
                // The user-agent identifies the engine, which is what actually
                // matters for a rendering or ARIA bug.
                userAgent: String(nav.userAgent || "unknown"),
                language: String(nav.language || "unknown"),
                platform: String(nav.platform || "unknown"),
                viewport: (window.innerWidth || 0) + "x" + (window.innerHeight || 0),
                // Whether the OS asks for reduced motion is a rendering fact,
                // not a statement about the person -- every visitor has one of
                // these two values and it says nothing about them.
                prefersReducedMotion: !!(window.matchMedia &&
                    window.matchMedia("(prefers-reduced-motion: reduce)").matches)
            };
        }

        /*
         * Build the report.
         *
         * `options.includeOutput` adds recent game text, and is false unless the
         * developer explicitly asks -- an opt-in they can see the result of
         * before doing anything with it.
         */
        function build(options) {
            var opts = options || {};
            var store = settings.store;
            var manifest = (store && store.get("manifest")) || {};
            var connection = (store && store.get("connection")) || {};

            var report = {
                generated: "on request",
                aetos: {
                    protocol: manifest.protocol || null,
                    // What the client actually has loaded, which is more useful
                    // than a version string when somebody is running a patched
                    // copy.
                    modules: resolve(settings.modules)
                },
                browser: browserSummary(),
                connection: { state: connection.state || "unknown" },
                features: manifest.features || {},
                automation: manifest.automation || {},
                widgets: resolve(settings.widgets),
                recentEventTypes: recentEventTypes(),
                errors: errors.slice()
            };

            // Provider class names, only where the game opted in (C.17).
            if (manifest.diagnostics) {
                report.providers = manifest.diagnostics.providers || {};
                if (manifest.diagnostics.error) {
                    report.providerError = manifest.diagnostics.error;
                }
            } else {
                report.providers =
                    "not reported -- set AETOS_DIAGNOSTICS = True in the game to include";
            }

            // Validation findings, which are about the player's automation but
            // describe only its *shape* -- counts and messages, never patterns
            // or commands.
            if (opts.validation) {
                report.validation = {
                    checked: opts.validation.checked,
                    errors: opts.validation.errors,
                    warnings: opts.validation.warnings
                };
            }

            if (opts.includeOutput && settings.canonicalLog) {
                report.recentOutput = settings.canonicalLog.all()
                    .slice(-20)
                    .map(function (event) { return event.originalText; })
                    .filter(Boolean);
            }

            return report;
        }

        /*
         * What is in it, and what is not, in words.
         *
         * Shown beside the report, because a reporter about to paste this into
         * a public issue deserves to know what they are pasting without reading
         * every line of JSON.
         */
        function describe(report) {
            return {
                contains: [
                    "protocol and module versions",
                    "browser and viewport",
                    "which features your game exposes",
                    "which widgets are loaded",
                    "connection state",
                    "counts of recent events by kind",
                    "any errors Aetos recorded",
                    report.recentOutput ? "recent game output (you asked for this)" : null
                ].filter(Boolean),
                excludes: [
                    "passwords and authentication tokens",
                    "your notes, relationship tags and reminders",
                    "your macros, aliases, triggers and scripts",
                    "chat, tells and the text of what happened",
                    "your accessibility and AAC preferences",
                    "anything from your game's source"
                ]
            };
        }

        function toText(report) {
            return JSON.stringify(report, null, 2);
        }

        /*
         * Prefill a GitHub issue.
         *
         * Returns a URL. **It does not open or submit anything** -- the caller
         * shows it, and the developer decides. A tool that filed an issue on
         * somebody's behalf, with a payload they had not read, would be
         * indefensible however convenient.
         */
        function issueUrl(repository, report) {
            var title = "Aetos: ";
            var body = "**What happened**\n\n\n**Diagnostics**\n\n```json\n" +
                toText(report) + "\n```\n";
            return "https://github.com/" + String(repository) +
                "/issues/new?title=" + window.encodeURIComponent(title) +
                "&body=" + window.encodeURIComponent(body);
        }

        return {
            build: build,
            describe: describe,
            toText: toText,
            issueUrl: issueUrl,
            record: record,
            errorCount: function () { return errors.length; },
            clear: function () { errors = []; return true; }
        };
    }

    window.AetosDiagnostics = {
        create: createDiagnostics,
        RECENT_WINDOW: RECENT_WINDOW,
        MAX_ERRORS: MAX_ERRORS
    };

})(window);
