/*
 * Aetos themes.  Milestone M19.  Addendum A.55, A11Y-VIS-003.
 *
 * A theme is a set of colour tokens, stored in this browser, applied by setting
 * custom properties on the document element.
 *
 * WHY TOKENS AND NOT A STYLESHEET. A theme that could ship CSS would be a theme
 * that could hide content, override a focus ring, animate something the player
 * asked not to be animated, or reintroduce every accessibility defect the
 * client spent a year removing. Tokens can only change colours, and every place
 * a colour is used already went through the "colour is never the only meaning"
 * rule. So a bad theme is illegible, which is recoverable and reported --
 * rather than broken, which is neither.
 *
 * THEMES NEVER TOUCH THE ACCESSIBILITY PRESETS. High contrast, reduced motion
 * and minimal stimulation are the player's *needs*; a theme is their taste. The
 * presets are applied after the theme and win, so choosing a theme can never
 * quietly undo an accommodation. A player who turned on high contrast and then
 * picked a pretty theme still has high contrast.
 *
 * VALIDATION IS PART OF ACCEPTANCE (A11Y-VIS-003), AND IT WARNS RATHER THAN
 * REFUSES. A player who wants a theme Aetos considers unwise is entitled to it.
 * What they are not entitled to is not being told -- and neither is whoever
 * they later send the exported file to.
 */

(function (window) {
    "use strict";

    var NAMESPACE = "themes";

    //: The tokens a theme may set. An allowlist, because a theme is data from
    //: an imported file as often as it is something the player typed, and
    //: "any custom property" would let one write `--aetos-space: 0` and
    //: collapse the entire layout.
    var TOKENS = [
        "--aetos-bg",
        "--aetos-panel",
        "--aetos-border",
        "--aetos-text",
        "--aetos-text-muted",
        "--aetos-accent",
        "--aetos-success",
        "--aetos-warning",
        "--aetos-danger",
        "--aetos-focus"
    ];

    //: Human labels, so the editor is not a list of variable names.
    var LABELS = {
        "--aetos-bg": "Background",
        "--aetos-panel": "Panel background",
        "--aetos-border": "Borders",
        "--aetos-text": "Text",
        "--aetos-text-muted": "Secondary text",
        "--aetos-accent": "Accent",
        "--aetos-success": "Success",
        "--aetos-warning": "Warning",
        "--aetos-danger": "Danger",
        "--aetos-focus": "Focus ring"
    };

    var MAX_THEMES = 40;
    var MAX_NAME = 60;

    /*
     * The themes Aetos ships.
     *
     * Both are checked by a test that reads the stylesheet and computes every
     * required ratio, because a palette chosen by eye passes for the person who
     * chose it. "Default" is empty on purpose: it means "whatever the
     * stylesheet says", so removing a theme restores the shipped look exactly
     * rather than a copy of it that can drift.
     */
    var BUILT_IN = [
        {
            id: "default",
            name: "Default",
            builtin: true,
            tokens: {}
        },
        {
            id: "paper",
            name: "Paper",
            builtin: true,
            // A light theme. Checked against the same eleven pairs as the dark
            // one -- light themes fail contrast just as readily, usually on the
            // muted text.
            tokens: {
                "--aetos-bg": "#f5f3ee",
                "--aetos-panel": "#ffffff",
                "--aetos-border": "#8a8377",
                "--aetos-text": "#22201c",
                "--aetos-text-muted": "#55504a",
                "--aetos-accent": "#1d5c8f",
                "--aetos-success": "#1c6b3a",
                "--aetos-warning": "#7a5200",
                "--aetos-danger": "#a32319",
                "--aetos-focus": "#1d5c8f"
            }
        }
    ];

    function normalize(raw) {
        if (!raw || typeof raw !== "object") {
            return null;
        }
        var name = String(raw.name || "").trim();
        if (!name) {
            return null;
        }
        var tokens = {};
        var source = raw.tokens && typeof raw.tokens === "object" ? raw.tokens : {};
        TOKENS.forEach(function (token) {
            var value = source[token];
            // Only well-formed hex survives. An unparseable colour is dropped
            // rather than passed to the browser, which would silently ignore
            // it and leave the author wondering which of their ten colours did
            // not take.
            if (window.AetosContrast && window.AetosContrast.parseColor(value)) {
                tokens[token] = String(value).trim().toLowerCase();
            }
        });
        return {
            id: String(raw.id || ("theme-" + name.toLowerCase().replace(/\s+/g, "-"))),
            name: name.slice(0, MAX_NAME),
            tokens: tokens,
            builtin: false
        };
    }

    function createThemes(services) {
        var settings = services || {};
        var storage = settings.storage || null;
        var announce = settings.announce || function () {};
        var root = settings.root || window.document.documentElement;

        var custom = [];
        var activeId = "default";

        function all() {
            return BUILT_IN.concat(custom);
        }

        function find(id) {
            var matches = all().filter(function (theme) { return theme.id === id; });
            return matches.length ? matches[0] : null;
        }

        function load() {
            if (!storage) {
                return Promise.resolve(all());
            }
            return storage.all(NAMESPACE).then(function (rows) {
                custom = (rows || [])
                    .map(function (row) { return row.value; })
                    .slice(0, MAX_THEMES)
                    .map(normalize)
                    .filter(Boolean);
                return storage.getBootPreference
                    ? storage.getBootPreference("theme", "default")
                    : "default";
            }).then(function (stored) {
                /*
                 * Applied from a boot preference rather than from IndexedDB
                 * alone, so the theme is in place before the first paint. A
                 * theme that arrives a beat late is a flash of the wrong
                 * colours on every load -- which for somebody using a dark
                 * theme because light hurts is not a cosmetic problem.
                 */
                apply(stored || "default", { silent: true });
                return all();
            }).catch(function () {
                return all();
            });
        }

        /*
         * Put a theme's colours on the document element.
         *
         * Only the tokens the theme sets. Everything else is *removed* rather
         * than left behind, so switching themes cannot leave one colour from
         * the previous one stranded -- a combination neither theme's author
         * ever looked at, and therefore one nobody validated.
         */
        function apply(id, options) {
            var opts = options || {};
            var theme = find(id) || find("default");

            TOKENS.forEach(function (token) {
                if (theme.tokens[token]) {
                    root.style.setProperty(token, theme.tokens[token]);
                } else {
                    root.style.removeProperty(token);
                }
            });

            activeId = theme.id;
            if (storage && storage.setBootPreference) {
                storage.setBootPreference("theme", theme.id);
            }
            if (!opts.silent) {
                announce("Theme: " + theme.name + ".", {
                    category: "system",
                    priority: "important"
                });
            }
            return theme;
        }

        /*
         * The colours a theme actually results in.
         *
         * A theme setting six of ten tokens inherits the other four, so
         * validating only what it declares would miss exactly the failures
         * that partial themes cause. Read back from the computed style, which
         * is what the player will really see.
         */
        function effectiveTokens(theme) {
            var computed = window.getComputedStyle(root);
            var result = {};
            TOKENS.forEach(function (token) {
                var value = (theme && theme.tokens[token]) ||
                    computed.getPropertyValue(token).trim();
                if (value) {
                    result[token] = value;
                }
            });
            return result;
        }

        function validate(theme) {
            if (!window.AetosContrast) {
                return { failures: [], checked: 0, passes: true };
            }
            return window.AetosContrast.validate(effectiveTokens(theme));
        }

        /*
         * Save a theme.
         *
         * The contrast report comes back with it, so the caller can show the
         * warning A11Y-VIS-003 requires. The save is **not** blocked on it: a
         * player who wants a theme Aetos considers unwise is entitled to have
         * it. Overruling somebody about their own eyes would be a worse failure
         * than the one being prevented.
         */
        function save(raw) {
            var theme = normalize(raw);
            if (!theme) {
                return Promise.reject(new Error("A theme needs a name."));
            }
            if (!storage) {
                return Promise.reject(new Error("No local storage available."));
            }
            if (custom.length >= MAX_THEMES && !find(theme.id)) {
                return Promise.reject(new Error("Too many themes saved."));
            }
            return storage.put(NAMESPACE, theme.id, theme).then(function () {
                return load();
            }).then(function () {
                return { theme: theme, contrast: validate(theme) };
            });
        }

        function remove(id) {
            var theme = find(id);
            if (!theme || theme.builtin) {
                // Built-ins are not deletable. A player who deleted the only
                // theme they could read would have no way back.
                return Promise.resolve(false);
            }
            if (!storage) {
                return Promise.resolve(false);
            }
            return storage.remove(NAMESPACE, id).then(function () {
                if (activeId === id) {
                    apply("default", { silent: true });
                }
                return load();
            }).then(function () { return true; });
        }

        return {
            load: load,
            all: all,
            find: find,
            apply: apply,
            save: save,
            remove: remove,
            validate: validate,
            effectiveTokens: effectiveTokens,
            active: function () { return activeId; }
        };
    }

    window.AetosThemes = {
        create: createThemes,
        normalize: normalize,
        TOKENS: TOKENS.slice(),
        LABELS: LABELS,
        BUILT_IN: BUILT_IN,
        NAMESPACE: NAMESPACE,
        MAX_THEMES: MAX_THEMES
    };

})(window);
