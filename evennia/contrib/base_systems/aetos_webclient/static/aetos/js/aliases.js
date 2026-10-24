/*
 * Aetos aliases.
 *
 * Shorthand a player defines for themselves:
 *
 *     hh              -> heal head
 *     gt sword        -> get sword from backpack
 *     tt Bob hello    -> tell Bob hello
 *
 * An alias is a text substitution, nothing more. The expanded text goes through
 * the ordinary command path, so an alias cannot do anything the player could not
 * type. Whether aliases may be used at all is the game's decision, declared in
 * the manifest (blueprint section 32).
 *
 * RECURSION IS THE DANGEROUS PART.
 *
 * Section 29 requires bounded expansion depth, and the reason is concrete: a
 * player who defines `a -> b` and later `b -> a` has built an infinite loop that
 * would hang their browser the next time they type `a`. They will not have
 * noticed, because each definition is reasonable on its own.
 *
 * So expansion is bounded two ways, because either alone is insufficient:
 *
 *   - a DEPTH limit, which stops long chains
 *   - a CYCLE check, which stops short loops immediately and reports them,
 *     rather than silently grinding to the depth limit every time
 */

(function (window) {
    "use strict";

    //: Maximum times an expansion may itself be expanded.
    var MAX_DEPTH = 10;

    var MAX_PATTERN_LENGTH = 40;
    var MAX_EXPANSION_LENGTH = 400;

    //: Positional placeholders. `$*` takes everything remaining, which is what a
    //: `tell` alias needs; `$1`..`$9` take single words.
    var POSITIONAL = /\$(\*|[1-9])/g;

    function normalizePattern(pattern) {
        // Aliases match on the first word, so a pattern containing spaces would
        // never fire. Trimming to the first token makes that obvious rather than
        // leaving a silently dead alias.
        return String(pattern || "").trim().split(/\s+/)[0].slice(0, MAX_PATTERN_LENGTH);
    }

    function createAliases(services) {
        var groups = services.groups || null;

        /*
         * Effective enabled-state.  C.15.
         *
         * Delegates to the automation groups module when one is present, and
         * falls back to the rule's own flag when it is not -- so a client
         * without the groups module behaves exactly as it did before them.
         */
        function allowed(rule) {
            if (groups && typeof groups.allows === "function") {
                return groups.allows(rule);
            }
            return !rule || rule.enabled !== false;
        }

        var storage = services.storage;
        var isAllowed = services.isAllowed || function () { return true; };
        var announce = services.announce || function () {};

        function normalize(alias) {
            var pattern = normalizePattern(alias.pattern);
            return {
                id: alias.id || pattern.toLowerCase(),
                pattern: pattern,
                expansion: String(alias.expansion || "").trim().slice(0, MAX_EXPANSION_LENGTH),
                enabled: alias.enabled !== false,
                group: String(alias.group || ""),
                // Aliases are case-insensitive by default: a player typing "HH"
                // in anger means the same thing as "hh".
                caseSensitive: alias.caseSensitive === true
            };
        }

        function save(alias) {
            if (!storage) {
                return window.Promise.resolve(null);
            }
            var record = normalize(alias);
            if (!record.pattern || !record.expansion) {
                return window.Promise.reject(
                    new Error("An alias needs both a pattern and an expansion."));
            }
            return storage.put("aliases", record.id, record).then(function () {
                return record;
            });
        }

        function remove(id) {
            return storage ? storage.remove("aliases", id) : window.Promise.resolve(false);
        }

        function all() {
            if (!storage) {
                return window.Promise.resolve([]);
            }
            return storage.all("aliases").then(function (rows) {
                return rows.map(function (row) { return row.value; });
            });
        }

        /*
         * Substitute positional arguments into an expansion.
         *
         * `$1`..`$9` take one word each; `$*` takes everything remaining. An
         * expansion using no placeholders keeps the arguments appended, so
         * `gt -> get` still lets `gt sword` mean `get sword`.
         */
        function substitute(expansion, args) {
            var used = false;

            /*
             * `$*` means "the arguments not already taken by a numbered
             * placeholder", not "all arguments".
             *
             * The difference matters for the common case. With `tell $1 $*`,
             * `tt Bob hello there` must produce "tell Bob hello there" -- if
             * `$*` meant all arguments it would produce "tell Bob Bob hello
             * there", repeating the recipient. An alias that mangles a tell is
             * worse than no alias.
             */
            var highestNumbered = 0;
            expansion.replace(POSITIONAL, function (match, which) {
                if (which !== "*") {
                    highestNumbered = Math.max(highestNumbered, parseInt(which, 10));
                }
                return match;
            });

            var result = expansion.replace(POSITIONAL, function (match, which) {
                used = true;
                if (which === "*") {
                    return args.slice(highestNumbered).join(" ");
                }
                var index = parseInt(which, 10) - 1;
                return args[index] === undefined ? "" : args[index];
            });

            // An expansion with no placeholders keeps the arguments, so a plain
            // `gt -> get` still lets `gt sword` mean `get sword`.
            if (!used && args.length) {
                result = result + " " + args.join(" ");
            }
            return result.replace(/\s+/g, " ").trim();
        }

        /*
         * Expand a line of input.
         *
         * Returns the expanded text, plus a report of what happened -- the
         * caller may want to tell the player their alias chain was cut short
         * rather than silently sending a half-expanded command.
         */
        function expand(input, aliasList) {
            var text = String(input || "").trim();
            var report = { expanded: false, depth: 0, truncated: false, cycle: null };

            if (!text || !isAllowed() || !aliasList || !aliasList.length) {
                return { text: text, report: report };
            }

            var byPattern = {};
            aliasList.forEach(function (alias) {
                // effective = rule.enabled AND group.enabled (C.15).
                // Consulted rather than reimplemented: five copies of a
                // two-term expression is five chances for one to drift.
                if (!allowed(alias)) {
                    return;
                }
                var key = alias.caseSensitive ? alias.pattern : alias.pattern.toLowerCase();
                byPattern[key] = alias;
            });

            // Cycle detection by identity, not by resulting text: `a -> b a`
            // legitimately produces different text each pass while still
            // looping forever.
            var seen = {};

            for (var depth = 0; depth < MAX_DEPTH; depth++) {
                var parts = text.split(/\s+/);
                var head = parts[0];
                var alias = byPattern[head] || byPattern[head.toLowerCase()];
                if (!alias) {
                    break;
                }
                if (seen[alias.id]) {
                    // Report rather than grinding silently to the depth limit
                    // every time the player uses this alias.
                    report.cycle = alias.pattern;
                    break;
                }
                seen[alias.id] = true;

                text = substitute(alias.expansion, parts.slice(1));
                report.expanded = true;
                report.depth = depth + 1;
            }

            if (report.depth >= MAX_DEPTH) {
                report.truncated = true;
            }
            return { text: text, report: report };
        }

        /*
         * Expand a line, loading the player's aliases first.
         *
         * Announces a cycle or a truncation: an alias that quietly stops
         * expanding is indistinguishable from one that is broken, and the player
         * needs to know which.
         */
        function expandInput(input) {
            if (!isAllowed()) {
                return window.Promise.resolve(String(input || "").trim());
            }
            return all().then(function (aliasList) {
                var result = expand(input, aliasList);
                if (result.report.cycle) {
                    announce(
                        "Alias " + result.report.cycle +
                        " refers back to itself; expansion stopped.");
                } else if (result.report.truncated) {
                    announce("Alias expansion stopped after " + MAX_DEPTH + " steps.");
                }
                return result.text;
            });
        }

        return {
            MAX_DEPTH: MAX_DEPTH,
            normalize: normalize,
            save: save,
            remove: remove,
            all: all,
            expand: expand,
            expandInput: expandInput,
            substitute: substitute
        };
    }

    window.AetosAliases = {
        create: createAliases,
        MAX_DEPTH: MAX_DEPTH
    };

})(window);
