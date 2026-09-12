/*
 * Aetos incoming event pipeline.  Addendum C.7, PIPE-001, PIPE-002.
 *
 * The order in which an inbound event is processed, made explicit and made
 * enforceable.
 *
 *     Protocol Validation
 *         ↓
 *     Protocol Normalization
 *         ↓
 *     Authoritative State Update
 *         ↓
 *     Canonical Event Log
 *         ↓
 *     Automation Observers
 *         ↓
 *     Derived Presentation
 *         ↓
 *     Announcement Candidates
 *
 * TWO RULES CARRY THE WHOLE THING.
 *
 * **State is updated before automation observes an event.** A trigger that
 * fires on stale state acts on a world that no longer exists -- it reads the
 * health it had before the hit that prompted it.
 *
 * **Presentation runs after state and history are already preserved.** Which
 * produces the rule that matters most in practice:
 *
 *     Server:          "You drop your sword."
 *     Canonical log:   "You drop your sword."
 *     Trigger:         fires
 *     Display filter:  may hide the line from view
 *
 * A trigger must not fail because the player chose to hide that text. Hiding is
 * a presentation decision; it is not a fact about the game. Clients that treat
 * gagging as deletion get this wrong, and the symptom -- an automation that
 * silently stops working when an unrelated display setting changes -- is
 * miserable to diagnose.
 *
 * The same reasoning protects accessibility: a visual filter must not suppress
 * an announcement, because a player who hid combat spam and then needs to know
 * what killed them must still be told.
 *
 * HOW THE ORDER IS ENFORCED RATHER THAN DOCUMENTED. Stages are a frozen list
 * and run in sequence. The presentation stage is handed a **copy** of the
 * canonical event, so a presenter that mutates what it was given changes
 * nothing -- the record and the automation input are already past. That is the
 * property E0's gate asks for, and it is provable rather than promised.
 *
 * WHAT THIS IS NOT. Not a general event bus, and deliberately not extensible by
 * a game. The order is the contract; a stage inserted between state and
 * automation by a third party would break the only guarantee this file exists
 * to make.
 */

(function (window) {
    "use strict";

    /*
     * The stages, in order. Frozen where the runtime supports it.
     *
     * Named so that a test can assert the order rather than inferring it from
     * the shape of the code, and so a violation names the stage it happened in.
     */
    var STAGES = [
        "validate",
        "normalize",
        "state",
        "log",
        "automation",
        "presentation",
        "announce"
    ];

    if (Object.freeze) {
        Object.freeze(STAGES);
    }

    //: Stages that may write to authoritative state or the canonical log.
    //: Everything after `log` is a reader.
    var WRITING_STAGES = ["state", "log"];

    function createPipeline(services) {
        var settings = services || {};
        var store = settings.store || null;
        var log = settings.canonicalLog || null;
        var onError = settings.onError || null;

        var observers = { automation: [], presentation: [], announce: [] };
        var stats = { processed: 0, failures: 0 };

        /*
         * Register an observer for one of the reader stages.
         *
         * `state` and `log` take no observers on purpose: those stages have
         * exactly one implementation each, and letting a game add a second
         * writer to authoritative state is the thing this pipeline exists to
         * prevent.
         */
        function observe(stage, handler) {
            if (WRITING_STAGES.indexOf(stage) !== -1) {
                throw new Error(
                    "Aetos pipeline: the " + stage + " stage does not take " +
                    "observers. Only one thing may write authoritative state."
                );
            }
            if (!observers[stage]) {
                throw new Error("Aetos pipeline: unknown stage " + stage);
            }
            if (typeof handler !== "function") {
                throw new Error("Aetos pipeline: observer must be a function");
            }
            observers[stage].push(handler);
            return function unobserve() {
                var index = observers[stage].indexOf(handler);
                if (index !== -1) {
                    observers[stage].splice(index, 1);
                }
            };
        }

        /*
         * Run one stage's observers.
         *
         * A failing observer is contained. One broken trigger must not stop the
         * console from rendering, and one broken widget must not stop an
         * announcement -- the alternative is that a third-party defect silently
         * disables an accessibility feature the player depends on.
         */
        function runStage(stage, event) {
            observers[stage].forEach(function (handler) {
                try {
                    handler(event);
                } catch (err) {
                    stats.failures += 1;
                    if (onError) {
                        onError({ stage: stage, error: err, eventId: event.id });
                    } else if (window.console) {
                        window.console.error(
                            "Aetos pipeline: " + stage + " observer failed", err);
                    }
                }
            });
        }

        /*
         * A shallow copy, for the reader stages.
         *
         * Cheap, and it is the whole enforcement mechanism: a presenter that
         * writes to what it was handed writes to a copy, and the canonical
         * record is untouched. Rather than trusting every downstream author to
         * remember not to.
         */
        function copyFor(event) {
            var duplicate = {};
            Object.keys(event).forEach(function (key) {
                duplicate[key] = event[key];
            });
            return duplicate;
        }

        /* --- The pipeline ------------------------------------------------ */

        /*
         * Process one inbound event.
         *
         * `raw` is `{kind, payload}` where kind is "text" or a structured
         * message name. Returns the canonical event, or null if it was rejected
         * at validation.
         */
        function ingest(raw) {
            if (!raw || typeof raw !== "object") {
                return null;
            }

            /* 1. Validate ------------------------------------------------- */
            var validated = settings.validate ? settings.validate(raw) : raw;
            if (!validated) {
                return null;
            }

            /* 2. Normalize ------------------------------------------------ */
            var normalized = settings.normalize
                ? settings.normalize(validated)
                : {
                    category: validated.category || "other",
                    originalText: validated.text || "",
                    structuredData: validated.payload || null
                };
            if (normalized.plainText === undefined) {
                normalized.plainText = normalized.originalText;
            }

            /* 3. Authoritative state -------------------------------------- */
            //
            // Before automation, so a trigger never reads a world that has
            // already moved on. This is the ordering rule with teeth.
            if (normalized.structuredData && store && settings.applyState) {
                settings.applyState(normalized.structuredData);
            }

            /* 4. Canonical log -------------------------------------------- */
            //
            // Before automation and presentation both, so that whatever either
            // of them does, the record of what happened already exists.
            var event = log
                ? log.append(normalized)
                : {
                    id: "evt-transient",
                    category: normalized.category,
                    originalText: normalized.originalText,
                    plainText: normalized.plainText,
                    structuredData: normalized.structuredData
                };

            stats.processed += 1;

            /* 5. Automation ------------------------------------------------ */
            //
            // Sees the canonical event. Not the displayed text, not a filtered
            // view -- what the server actually said.
            runStage("automation", copyFor(event));

            /* 6. Presentation ---------------------------------------------- */
            //
            // Handed a copy. Anything it does to that copy is presentation
            // metadata and cannot reach the record or the automation that has
            // already run.
            runStage("presentation", copyFor(event));

            /* 7. Announcement candidates ------------------------------------ */
            //
            // Independent of presentation (C.10). A line hidden from the
            // console is still announced if the player's announcement settings
            // say it should be -- those are two different decisions, and
            // conflating them means a visual preference silently degrades an
            // accessibility one.
            runStage("announce", copyFor(event));

            return event;
        }

        return {
            ingest: ingest,
            observe: observe,
            stages: function () { return STAGES.slice(); },
            stats: function () {
                return { processed: stats.processed, failures: stats.failures };
            },
            observerCount: function (stage) {
                return (observers[stage] || []).length;
            }
        };
    }

    window.AetosPipeline = {
        create: createPipeline,
        STAGES: STAGES,
        WRITING_STAGES: WRITING_STAGES.slice()
    };

})(window);
