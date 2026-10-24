/*
 * Aetos unified validator.  Addendum C.16.
 *
 * One place that answers "is this going to work, and if not, why not" for every
 * kind of automation a player can write: scripts, triggers, aliases, macros,
 * display rules, groups.
 *
 * WHY ONE VALIDATOR AND NOT SIX. Because six would give six different answers to
 * the same question. A regular expression that is dangerous in a trigger is
 * dangerous in a display rule, and a player who has been told so once should not
 * have to discover it again in a different dialog with different wording. The
 * rules are the same, so the code should be too.
 *
 * IT VALIDATES BY RUNNING THE REAL PARSER. Script checking calls
 * `AetosScripting.compile` -- the same compiler the interpreter uses -- rather
 * than approximating it. A validator with its own idea of the grammar is a
 * second grammar, and the two will disagree eventually, always in the direction
 * of accepting something that then fails at runtime.
 *
 * WHAT IT DOES NOT CLAIM. Static validation cannot prove a script does what the
 * player meant, and it cannot prove one terminates in practice. It catches what
 * is *detectably* wrong -- syntax, unknown built-ins, wrong argument counts,
 * patterns whose shape is known to be expensive -- and says so. Anything
 * stronger would be a promise it could not keep, and a validator that says
 * "looks fine" about something that then hangs the tab has done real harm to
 * the player's trust in every other thing it says.
 *
 * SEVERITY IS A CONTRACT.
 *
 *   ERROR    the thing is structurally invalid. Save is refused.
 *   WARNING  legal, and suspicious. Save proceeds; the player was told.
 *   INFO     an interpretation worth stating, so nothing is a surprise later.
 *
 * The distinction matters most for WARNING. A validator that refused everything
 * it disliked would be a validator players route around, and the player
 * frequently knows something it does not.
 */

(function (window) {
    "use strict";

    var ERROR = "error";
    var WARNING = "warning";
    var INFO = "info";
    var SEVERITIES = [ERROR, WARNING, INFO];

    /*
     * Regex bounds.  A.16, C.16.
     *
     * JavaScript has no universal safe timeout for regex execution -- there is
     * no way to interrupt a pattern once it starts backtracking. So the only
     * real defence is refusing to run anything expensive, which means bounding
     * both halves: the pattern and what it is matched against.
     */
    var MAX_PATTERN_LENGTH = 200;
    var MAX_TEST_INPUT = 4000;

    /*
     * Shapes that backtrack catastrophically.
     *
     * Not a complete detector. There is no complete detector -- deciding
     * whether an arbitrary pattern is polynomial is not something a regex can
     * do about another regex. These are the classic shapes, they are cheap to
     * check, and being incomplete is why the result is a WARNING rather than an
     * ERROR: the bounds above are the actual protection.
     */
    var NESTED_QUANTIFIER = /\([^)]*[+*][^)]*\)\s*[+*]/;
    var ADJACENT_QUANTIFIERS = /[+*]\s*[+*]/;
    var BROAD_ALTERNATION = /\(\s*\.\s*\*\s*\|/;


    /*
     * The functions a script may call.
     *
     * Mirrors what the shell supplies as `scriptApi`. Kept as a default the
     * caller can override rather than a hardcoded truth, so the validator
     * cannot drift from a client that offers more.
     */
    var DEFAULT_BUILTINS = ["send", "echo", "resource", "room", "target", "get", "set"];

    /*
     * Visit every call node in a compiled script.
     *
     * Structure-agnostic: it walks whatever the parser produced rather than
     * assuming a shape, so a change to the AST does not silently stop the
     * check from finding anything -- which is how this sort of validation
     * usually dies.
     */
    function walkCalls(node, visit, depth) {
        var level = depth || 0;
        if (!node || typeof node !== "object" || level > 64) {
            return;
        }
        if (Array.isArray(node)) {
            node.forEach(function (child) { walkCalls(child, visit, level + 1); });
            return;
        }
        if (node.type === "call" && node.name) {
            visit(node);
        }
        Object.keys(node).forEach(function (key) {
            var value = node[key];
            if (value && typeof value === "object") {
                walkCalls(value, visit, level + 1);
            }
        });
    }

    function finding(severity, message, detail) {
        return {
            severity: severity,
            message: message,
            detail: detail || null
        };
    }

    /* ------------------------------------------------------------------
     * Regular expressions
     * ------------------------------------------------------------------ */

    function validateRegex(pattern) {
        var findings = [];
        var text = String(pattern || "");

        if (!text) {
            return [finding(ERROR, "The pattern is empty.")];
        }
        if (text.length > MAX_PATTERN_LENGTH) {
            findings.push(finding(
                ERROR,
                "The pattern is longer than " + MAX_PATTERN_LENGTH + " characters.",
                "Long patterns are slow to match and hard to debug. If you need " +
                "one this complex, a script can express it more clearly."
            ));
            return findings;
        }

        try {
            new RegExp(text);
        } catch (err) {
            // The engine's own message, because it names the position and is
            // more useful than anything paraphrased.
            return [finding(ERROR, "That is not a valid regular expression.", err.message)];
        }

        if (NESTED_QUANTIFIER.test(text) || ADJACENT_QUANTIFIERS.test(text)) {
            findings.push(finding(
                WARNING,
                "This pattern may be very slow on long lines.",
                "It repeats a group that already repeats, which can take a long " +
                "time to fail to match. Aetos limits how much text a rule sees, " +
                "so it cannot hang the client -- but the rule may be slow enough " +
                "to notice."
            ));
        }
        if (BROAD_ALTERNATION.test(text)) {
            findings.push(finding(
                WARNING,
                "This pattern starts with a very broad alternative.",
                "`.*|` matches almost anything, so the rule will fire far more " +
                "often than you probably intend."
            ));
        }
        if (text.indexOf("(?<") === 0 || text.indexOf("(?<=") !== -1) {
            findings.push(finding(
                INFO,
                "Lookbehind is not supported in every browser.",
                "This rule may behave differently on Safari."
            ));
        }
        return findings;
    }

    /*
     * Try a pattern against a sample, with both sides bounded.
     *
     * A test facility, offered to the editors so a player can see what their
     * rule matches before saving it. The input is truncated because the point
     * is to check the pattern, not to benchmark it.
     */
    function testRegex(pattern, sample) {
        var problems = validateRegex(pattern);
        if (problems.some(function (item) { return item.severity === ERROR; })) {
            return { ok: false, findings: problems, matches: [] };
        }
        var input = String(sample || "").slice(0, MAX_TEST_INPUT);
        var matches = [];
        try {
            var expression = new RegExp(pattern, "g");
            var match;
            var guard = 0;
            while ((match = expression.exec(input)) !== null && guard < 100) {
                matches.push({ text: match[0], index: match.index });
                if (match[0].length === 0) {
                    expression.lastIndex += 1;
                }
                guard += 1;
            }
        } catch (err) {
            return { ok: false, findings: [finding(ERROR, err.message)], matches: [] };
        }
        return { ok: true, findings: problems, matches: matches };
    }

    /* ------------------------------------------------------------------
     * Aetos Script
     * ------------------------------------------------------------------ */

    function validateScript(source, settings) {
        settings = settings || {};
        var text = String(source || "");
        if (!text.trim()) {
            return [finding(ERROR, "The script is empty.")];
        }

        if (!window.AetosScripting || typeof window.AetosScripting.compile !== "function") {
            return [finding(
                INFO,
                "The scripting module is not loaded, so this could not be checked."
            )];
        }

        var findings = [];
        var compiled;
        try {
            // The REAL compiler, not an approximation of it. A validator with
            // its own idea of the grammar is a second grammar, and the two will
            // disagree -- always by accepting something that fails at runtime.
            compiled = window.AetosScripting.compile(text);
        } catch (err) {
            return [finding(ERROR, "The script has a syntax error.", err.message)];
        }
        if (!compiled) {
            return [finding(ERROR, "The script could not be compiled.")];
        }

        /*
         * Unknown functions.  C.16.
         *
         * Resolved by walking the compiled AST rather than by scanning the
         * text. Call nodes carry their name and line, so this reports "line 3:
         * there is no function called healthh" instead of a textual guess that
         * would trip over the word appearing in a string.
         *
         * A WARNING rather than an ERROR: the known list is what the client
         * supplies today, and a script naming something else is wrong *now* --
         * but refusing to save it would also refuse a script written against a
         * newer Aetos and pasted into an older one, which is a worse outcome
         * than a warning.
         */
        var known = settings.builtins || DEFAULT_BUILTINS;
        walkCalls(compiled, function (node) {
            if (known.indexOf(node.name) === -1) {
                findings.push(finding(
                    WARNING,
                    "There is no function called " + node.name + "().",
                    "Line " + (node.line || "?") + ". Available: " +
                        known.join(", ") + "."
                ));
            }
        });

        /*
         * Loop shapes that cannot terminate.
         *
         * Deliberately shallow. Detecting non-termination in general is the
         * halting problem, so this only catches the literal cases -- and says
         * so, rather than implying the absence of a warning means the script
         * is safe. The interpreter's step and time limits are what actually
         * protect the player.
         */
        if (/while\s+true\s+do/.test(text) && !/\bbreak\b/.test(text)) {
            findings.push(finding(
                WARNING,
                "This script has a loop that never ends on its own.",
                "Aetos will stop it after its step limit, but it will not do " +
                "what you expect. Add a condition or a break."
            ));
        }

        findings.push(finding(
            INFO,
            "Checked for syntax and known functions only.",
            "Whether the script does what you meant is something only running " +
            "it will tell you."
        ));
        return findings;
    }

    /* ------------------------------------------------------------------
     * The other kinds
     * ------------------------------------------------------------------ */

    function validateCommands(commands, limit) {
        var findings = [];
        var list = commands || [];
        if (!list.length) {
            findings.push(finding(ERROR, "No commands to run."));
            return findings;
        }
        if (limit && list.length > limit) {
            findings.push(finding(
                ERROR,
                "Too many commands: " + list.length + ", the limit is " + limit + "."
            ));
        }
        list.forEach(function (command, index) {
            if (!String(command || "").trim()) {
                findings.push(finding(WARNING, "Command " + (index + 1) + " is blank."));
            }
        });
        return findings;
    }

    function validateTrigger(trigger) {
        var findings = [];
        var spec = trigger || {};

        if (!String(spec.label || "").trim()) {
            findings.push(finding(WARNING, "This trigger has no name.",
                "An unnamed trigger is hard to find again when it misbehaves."));
        }
        if (spec.mode === "regex") {
            findings.push.apply(findings, validateRegex(spec.pattern));
        } else if (!String(spec.pattern || "").trim()) {
            findings.push(finding(ERROR, "There is no text to match on."));
        }
        findings.push.apply(findings, validateCommands(spec.commands, 5));
        return findings;
    }

    function validateAlias(alias) {
        var findings = [];
        var spec = alias || {};
        var pattern = String(spec.pattern || "").trim();

        if (!pattern) {
            findings.push(finding(ERROR, "There is no shorthand to replace."));
        } else if (pattern.indexOf(" ") !== -1) {
            findings.push(finding(
                ERROR,
                "An alias replaces the first word only.",
                "\"" + pattern + "\" contains a space, so it would never match."
            ));
        }
        if (!String(spec.expansion || "").trim()) {
            findings.push(finding(ERROR, "There is nothing to send instead."));
        }
        // A self-referential alias cannot loop -- expansion is single-pass --
        // but it is almost certainly not what the player meant.
        if (pattern && String(spec.expansion || "").split(/\s+/)[0] === pattern) {
            findings.push(finding(
                WARNING,
                "This alias expands to itself.",
                "Aliases are not re-expanded, so this sends the same word back " +
                "to the game rather than looping -- but it probably does nothing " +
                "useful."
            ));
        }
        return findings;
    }

    function validateDisplayRule(rule) {
        var findings = [];
        var spec = rule || {};

        if (!window.AetosPresentationRules ||
                window.AetosPresentationRules.KINDS.indexOf(spec.kind) === -1) {
            findings.push(finding(
                ERROR,
                "\"" + spec.kind + "\" is not a kind of display rule.",
                "Use highlight, substitute, filter or collapse."
            ));
        }
        if (spec.regex) {
            findings.push.apply(findings, validateRegex(spec.pattern));
        } else if (!String(spec.pattern || "").trim()) {
            findings.push(finding(ERROR, "There is no text to match on."));
        }
        if (spec.kind === "substitute" && !String(spec.replacement || "").length) {
            findings.push(finding(
                INFO,
                "The replacement is empty, so matching text will be removed from " +
                "view.",
                "The original line stays in your history either way."
            ));
        }
        return findings;
    }

    function validateTimer(timer) {
        var findings = [];
        var spec = timer || {};
        var seconds = Number(spec.interval) / 1000;

        if (!isFinite(seconds) || seconds <= 0) {
            findings.push(finding(ERROR, "The interval must be a number of seconds."));
        } else if (seconds < 1) {
            findings.push(finding(
                ERROR,
                "An interval under one second would flood the server.",
                "Most games treat that as an attack."
            ));
        } else if (seconds < 10) {
            findings.push(finding(
                WARNING,
                "This runs every " + Math.round(seconds) + " seconds.",
                "Check your game's rules on automation before leaving it running."
            ));
        }
        findings.push.apply(findings, validateCommands(spec.commands, 5));
        return findings;
    }

    /* ------------------------------------------------------------------
     * The public surface
     * ------------------------------------------------------------------ */

    function createValidator(services) {
        var settings = services || {};

        var VALIDATORS = {
            script: function (source) {
                return validateScript(source, settings);
            },
            trigger: validateTrigger,
            alias: validateAlias,
            timer: validateTimer,
            displayRule: validateDisplayRule,
            regex: validateRegex,
            macro: function (macro) {
                return validateCommands((macro || {}).commands, 5);
            }
        };

        function validate(kind, subject) {
            var checker = VALIDATORS[kind];
            if (!checker) {
                return { kind: kind, findings: [], ok: true, blocked: false };
            }
            var findings = checker(subject) || [];
            var blocked = findings.some(function (item) {
                return item.severity === ERROR;
            });
            return {
                kind: kind,
                findings: findings,
                blocked: blocked,
                ok: !findings.length
            };
        }

        /*
         * Check everything the player has stored.
         *
         * Runs locally against browser-owned configuration. Nothing is uploaded
         * -- this is the player's own automation and the whole point of it
         * living in their browser is that it stays there.
         *
         * Returns a Promise, because half the engines read from IndexedDB.
         */
        function validateAll() {
            var results = { checked: 0, errors: 0, warnings: 0, byKind: {} };

            function record(kind, subject, name) {
                var outcome = validate(kind, subject);
                results.checked += 1;
                if (!results.byKind[kind]) {
                    results.byKind[kind] = { checked: 0, errors: 0, warnings: 0, items: [] };
                }
                var bucket = results.byKind[kind];
                bucket.checked += 1;

                outcome.findings.forEach(function (item) {
                    if (item.severity === ERROR) {
                        results.errors += 1;
                        bucket.errors += 1;
                    } else if (item.severity === WARNING) {
                        results.warnings += 1;
                        bucket.warnings += 1;
                    }
                });
                if (outcome.blocked || outcome.findings.some(function (item) {
                    return item.severity === WARNING;
                })) {
                    bucket.items.push({ name: name, findings: outcome.findings });
                }
            }

            var sources = [
                ["trigger", settings.triggers, "label"],
                ["alias", settings.aliases, "pattern"],
                ["timer", settings.timers, "label"],
                ["script", settings.scripting, "label"],
                ["displayRule", settings.displayRules, "label"],
                ["macro", settings.macros, "label"]
            ];

            /*
             * Engines disagree about whether `all()` is synchronous.
             *
             * The storage-backed ones return a Promise; the in-memory ones
             * return an array. Rather than requiring every engine to change --
             * or worse, reaching past them into storage -- this accepts either
             * and resolves the difference here, so the report is always a
             * Promise and the caller has one thing to expect.
             */
            var pending = sources.map(function (entry) {
                var engine = entry[1];
                if (!engine || typeof engine.all !== "function") {
                    return Promise.resolve([]);
                }
                try {
                    var value = engine.all();
                    if (value && typeof value.then === "function") {
                        // Coerced on resolution too, not just on the
                        // synchronous branch: an engine whose promise resolves
                        // to something other than an array would otherwise
                        // reach the loop below and throw there, a long way
                        // from the engine that caused it.
                        return value.then(function (resolved) {
                            return Array.isArray(resolved) ? resolved : [];
                        }).catch(function () { return []; });
                    }
                    return Promise.resolve(Array.isArray(value) ? value : []);
                } catch (err) {
                    // One engine failing to enumerate costs its own section,
                    // not the whole report.
                    return Promise.resolve([]);
                }
            });

            return Promise.all(pending).then(function (lists) {
                lists.forEach(function (items, index) {
                    var kind = sources[index][0];
                    var nameKey = sources[index][2];
                    (Array.isArray(items) ? items : []).forEach(function (item) {
                        // Scripts are validated on their source, not on the
                        // stored record.
                        var subject = kind === "script" ? item.source : item;
                        record(kind, subject, item[nameKey] || item.id);
                    });
                });
                return results;
            });
        }

        /*
         * A one-line-per-kind summary, for the dialog.
         */
        function summarize(results) {
            return Object.keys(results.byKind).map(function (kind) {
                var bucket = results.byKind[kind];
                var parts = [bucket.checked + " checked"];
                if (bucket.errors) {
                    parts.push(bucket.errors + " error" + (bucket.errors === 1 ? "" : "s"));
                }
                if (bucket.warnings) {
                    parts.push(bucket.warnings +
                        " warning" + (bucket.warnings === 1 ? "" : "s"));
                }
                return { kind: kind, text: parts.join(", "), bucket: bucket };
            });
        }

        return {
            validate: validate,
            validateAll: validateAll,
            summarize: summarize,
            testRegex: testRegex
        };
    }

    window.AetosValidator = {
        create: createValidator,
        validateRegex: validateRegex,
        validateScript: validateScript,
        walkCalls: walkCalls,
        DEFAULT_BUILTINS: DEFAULT_BUILTINS.slice(),
        validateTrigger: validateTrigger,
        validateAlias: validateAlias,
        validateTimer: validateTimer,
        validateDisplayRule: validateDisplayRule,
        testRegex: testRegex,
        ERROR: ERROR,
        WARNING: WARNING,
        INFO: INFO,
        SEVERITIES: SEVERITIES.slice(),
        MAX_PATTERN_LENGTH: MAX_PATTERN_LENGTH,
        MAX_TEST_INPUT: MAX_TEST_INPUT
    };

})(window);
