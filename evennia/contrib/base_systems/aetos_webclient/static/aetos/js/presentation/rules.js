/*
 * Aetos presentation rules.  Addendum C.14, RULE-001.
 *
 * Highlight, Substitute, Filter and Collapse -- four ways to change how output
 * *looks*, and no way at all to change what happened.
 *
 * THE RULE THE WHOLE FILE EXISTS TO ENFORCE. A rule produces presentation
 * metadata. It never touches the canonical event, the store, or the input a
 * trigger sees. E0 already makes that structurally true by handing the
 * presentation stage a copy; this file is what runs inside that stage, and it
 * is careful anyway -- defence in depth for a property that is very hard to
 * notice losing.
 *
 * WHY "HIDDEN" IS NOT "DELETED". A player who filters combat spam out of their
 * console has changed what they are looking at. They have not changed what
 * happened, and when they later need to know what killed them, the answer must
 * still be findable. So a filtered event stays in the canonical log, stays in
 * the history widget's search, stays reviewable, and stays in a developer
 * capture. The console simply does not draw it.
 *
 * This is the difference between Aetos and clients where "gag" means "throw
 * away". The word `gag` is avoided in the interface for the same reason: it
 * names the wrong mental model.
 *
 * SUBSTITUTION AND SPANS. Replacing text invalidates any offsets computed
 * against the original. Rather than carefully adjusting them -- which is where
 * this kind of code goes wrong -- a substitution that changes length simply
 * drops the spans. **Never stale offsets on altered text**: a highlight
 * pointing at the wrong words is worse than no highlight, because it asserts
 * something false about which part mattered.
 *
 * COLOUR IS NOT THE MEANING. A highlight may set a style token, and it always
 * also sets a label. A player who cannot distinguish the colours gets the same
 * information from the accessible name.
 */

(function (window) {
    "use strict";

    var KINDS = ["highlight", "substitute", "filter", "collapse"];

    /*
     * Bounds on patterns.  A.16, and the regex half of E4.
     *
     * JavaScript has no universal safe timeout for regex execution, so the only
     * real defence is refusing to run anything expensive. A pattern is matched
     * against one event's text, never against the transcript, and both are
     * bounded.
     */
    var MAX_PATTERN_LENGTH = 200;
    var MAX_INPUT_LENGTH = 4000;
    var MAX_RULES = 100;

    /*
     * Patterns that are cheap to write and catastrophic to run.
     *
     * Not a complete detector -- there is no complete detector -- so this
     * warns rather than refuses, and the real protection is the length bounds
     * above. Nested unbounded quantifiers are the classic shape.
     */
    var DANGEROUS = /(\([^)]*[+*][^)]*\)[+*])|(\[[^\]]*\][+*]){3,}/;

    function normalizeRule(raw) {
        if (!raw || typeof raw !== "object") {
            return null;
        }
        if (KINDS.indexOf(raw.kind) === -1) {
            return null;
        }
        var pattern = String(raw.pattern || "");
        if (!pattern || pattern.length > MAX_PATTERN_LENGTH) {
            return null;
        }

        return {
            id: String(raw.id || ""),
            kind: raw.kind,
            label: String(raw.label || "").slice(0, 80),
            pattern: pattern,
            regex: raw.regex === true,
            caseSensitive: raw.caseSensitive === true,
            // Only meaningful for `substitute`.
            replacement: String(raw.replacement || "").slice(0, MAX_PATTERN_LENGTH),
            // Only meaningful for `highlight`. A token, not a colour: the theme
            // decides what it looks like, and the label carries the meaning.
            style: String(raw.style || "mark").slice(0, 32),
            // Only meaningful for `filter` and `collapse`.
            category: String(raw.category || ""),
            enabled: raw.enabled !== false,
            group: String(raw.group || "").slice(0, 40)
        };
    }

    function compile(rule) {
        try {
            if (rule.regex) {
                if (DANGEROUS.test(rule.pattern)) {
                    // Compiled anyway -- the player asked for it and the bounds
                    // above cap the damage -- but flagged so the editor can
                    // warn and a diagnostic report can explain a slow session.
                    rule.warning = "This pattern may be slow on long lines.";
                }
                return new RegExp(rule.pattern, rule.caseSensitive ? "g" : "gi");
            }
            // A plain-text rule is escaped, so a player typing "cost: $5 (each)"
            // gets a literal match rather than a syntax error.
            var escaped = rule.pattern.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
            return new RegExp(escaped, rule.caseSensitive ? "g" : "gi");
        } catch (err) {
            rule.error = err.message;
            return null;
        }
    }

    function createRules(services) {
        var settings = services || {};
        var storage = settings.storage || null;

        var rules = [];
        var compiled = {};

        function load() {
            if (!storage) {
                return Promise.resolve([]);
            }
            return storage.all("display_rules").then(function (rows) {
                // `all` yields {key, value} wrappers, not the values. Reading
                // the wrapper produces objects with no `kind`, which normalize
                // then discards -- so every rule silently vanished on load
                // while save() reported success.
                rules = (rows || [])
                    .map(function (row) { return row.value; })
                    .slice(0, MAX_RULES)
                    .map(normalizeRule)
                    .filter(Boolean);
                compiled = {};
                rules.forEach(function (rule) { compiled[rule.id] = compile(rule); });
                return rules.slice();
            }).catch(function () { return []; });
        }

        function save(raw) {
            var rule = normalizeRule(raw);
            if (!rule) {
                return Promise.reject(new Error("A rule needs a kind and a pattern."));
            }
            if (!rule.id) {
                rule.id = rule.kind + ":" + rule.pattern.toLowerCase();
            }
            if (!storage) {
                return Promise.reject(new Error("No local storage available."));
            }
            var probe = compile(rule);
            if (!probe) {
                return Promise.reject(new Error("That pattern is not valid: " + rule.error));
            }
            // put(namespace, key, value) -- three arguments. The store's own
            // keyPath is "key", which the backend fills in; a two-argument call
            // writes a record with no key and IndexedDB rejects it.
            return storage.put("display_rules", rule.id, rule).then(function () {
                return load().then(function () { return rule; });
            });
        }

        function remove(id) {
            if (!storage) {
                return Promise.resolve(false);
            }
            return storage.remove("display_rules", id).then(function () {
                return load().then(function () { return true; });
            });
        }

        /*
         * Apply the rules to one event.
         *
         * Takes the canonical event and returns **presentation metadata**. The
         * event is not modified, and the caller receives a separate object --
         * so there is no way for a caller to accidentally hand the mutated
         * thing onward as though it were the record.
         */
        function present(event, activeGroups) {
            /*
             * The PLAIN text, not the markup.
             *
             * A player writes a rule for the words they can see. Matching
             * against the markup means a pattern anchored with `^` fails on any
             * coloured line, an offset computed here lands inside a tag, and --
             * the symptom that found this -- the console renders `displayText`
             * as text, so a highlight on a coloured line showed the player
             * `<span class="color-002">` and the MXP anchors verbatim.
             *
             * `plainText` falls back to `originalText` for an event that
             * predates it or has no markup, which is the same string.
             */
            var source = event.plainText === undefined
                ? event.originalText
                : event.plainText;
            var text = String(source || "").slice(0, MAX_INPUT_LENGTH);
            var result = {
                displayText: text,
                /*
                 * Whether a rule actually rewrote the text.
                 *
                 * The console used to infer this by comparing `displayText`
                 * with the original, which worked only while the two were the
                 * same string to begin with. Since `displayText` became the
                 * *plain* rendering, they differ on every line that carries any
                 * markup -- so the console took every coloured line as
                 * "substituted" and drew it as plain text. **The client lost
                 * ANSI colour entirely**, on every line, for a whole milestone,
                 * and no test noticed because they all assert on text.
                 *
                 * Stated as a fact rather than inferred from a comparison that
                 * happened to hold.
                 */
                substituted: false,
                spans: [],
                hiddenInView: false,
                collapsed: false,
                appliedRules: []
            };

            rules.forEach(function (rule) {
                if (!rule.enabled) {
                    return;
                }
                // A rule in a disabled group is off. `effective = rule.enabled
                // AND group.enabled` -- E3 owns the groups; this honours them.
                if (rule.group && activeGroups && activeGroups[rule.group] === false) {
                    return;
                }
                if (rule.category && event.category !== rule.category) {
                    return;
                }

                var expression = compiled[rule.id];
                if (!expression) {
                    return;
                }
                expression.lastIndex = 0;
                if (!expression.test(result.displayText)) {
                    return;
                }
                expression.lastIndex = 0;

                switch (rule.kind) {
                case "filter":
                    // Hidden from this view. Still in the log, still searchable,
                    // still reviewable, still captured.
                    result.hiddenInView = true;
                    break;

                case "collapse":
                    result.collapsed = true;
                    break;

                case "substitute":
                    var replaced = result.displayText.replace(
                        expression, rule.replacement);
                    result.substituted = replaced !== result.displayText;
                    if (replaced.length !== result.displayText.length) {
                        // Offsets computed against the old text no longer mean
                        // anything. Dropping them is correct; adjusting them is
                        // where this sort of code goes wrong, and a highlight
                        // pointing at the wrong words asserts something false
                        // about which part mattered.
                        result.spans = [];
                    }
                    result.displayText = replaced;
                    break;

                case "highlight":
                    var match;
                    expression.lastIndex = 0;
                    while ((match = expression.exec(result.displayText)) !== null) {
                        result.spans.push({
                            start: match.index,
                            end: match.index + match[0].length,
                            style: rule.style,
                            // The accessible name. Colour is decoration; this
                            // is what a screen reader announces, and what a
                            // colour-blind player reads instead of the tint.
                            label: rule.label || "highlighted"
                        });
                        if (match[0].length === 0) {
                            // A zero-width match would loop forever.
                            expression.lastIndex += 1;
                        }
                    }
                    break;

                default:
                    break;
                }

                result.appliedRules.push(rule.id);
            });

            // Sorted and de-overlapped, so rendering can walk them in order
            // without producing nested or crossing markup.
            result.spans.sort(function (a, b) { return a.start - b.start; });
            var merged = [];
            result.spans.forEach(function (span) {
                var last = merged[merged.length - 1];
                if (last && span.start < last.end) {
                    last.end = Math.max(last.end, span.end);
                    return;
                }
                merged.push(span);
            });
            result.spans = merged;

            return result;
        }

        return {
            load: load,
            save: save,
            remove: remove,
            present: present,
            all: function () { return rules.slice(); },
            count: function () { return rules.length; }
        };
    }

    window.AetosPresentationRules = {
        create: createRules,
        normalizeRule: normalizeRule,
        compile: compile,
        KINDS: KINDS.slice(),
        MAX_PATTERN_LENGTH: MAX_PATTERN_LENGTH,
        MAX_INPUT_LENGTH: MAX_INPUT_LENGTH,
        MAX_RULES: MAX_RULES,
        DANGEROUS: DANGEROUS
    };

})(window);
