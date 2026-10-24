/*
 * Aetos shortcut manager.  Addendum A.22, A.23.
 *
 * A11Y-KEY-002: no global character-only shortcuts.
 *
 * This is the requirement people are most surprised by, so it is worth stating
 * the reason plainly. In NVDA's browse mode and JAWS's virtual cursor, single
 * letters are navigation: `h` moves to the next heading, `b` to the next
 * button, `l` to the next list. A client that binds `i` to Inventory has not
 * added a convenient shortcut -- it has taken a letter away from someone's
 * ability to move around the page, and the collision is invisible to whoever
 * added the binding.
 *
 * So Aetos refuses to register a bare character globally. Not "discourages":
 * `register` throws. A player may opt in through preferences, and even then
 * Aetos never ships one as a default.
 *
 * TWO OTHER RULES THIS ENFORCES.
 *
 * A.23: no feature may exist *only* behind a shortcut. Every registration
 * names the palette command it duplicates, and a registration that names none
 * is rejected -- so a keyboard shortcut is always an accelerator for something
 * reachable another way, never the only door.
 *
 * A.23: every shortcut can be viewed, rebound, disabled and restored. A
 * binding that collides with the player's own assistive technology is not a
 * theoretical problem, and telling them to work around it is not an answer.
 */

(function (window, document) {
    "use strict";

    /*
     * Keys that are safe to bind alone, because no screen reader uses them for
     * structural navigation. Function keys and a few named keys.
     */
    var SAFE_BARE_KEYS = [
        "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
        "Escape", "Insert", "Pause"
    ];

    /*
     * Advisory conflict table (A.23).
     *
     * Deliberately incomplete and deliberately advisory. It cannot be
     * authoritative -- assistive technology is configurable, versions change,
     * and the player may have remapped things Aetos cannot see. Its job is to
     * warn before a player discovers the clash the hard way, not to forbid.
     * The player may always override.
     */
    var KNOWN_CONFLICTS = {
        "Ctrl+W": "Closes the browser tab.",
        "Ctrl+T": "Opens a new browser tab.",
        "Ctrl+N": "Opens a new browser window.",
        "Ctrl+P": "Prints, and is Say Prior Line in some screen readers.",
        "Ctrl+S": "Saves the page.",
        "Ctrl+F": "Browser find. Screen-reader users rely on it heavily.",
        "Ctrl+L": "Focuses the browser address bar.",
        "Ctrl+D": "Bookmarks the page.",
        "Insert": "The default NVDA and JAWS modifier key.",
        "CapsLock": "The laptop-layout NVDA and JAWS modifier key.",
        "NumpadInsert": "The desktop-layout screen-reader modifier.",
        "Ctrl+Alt+ArrowUp": "Table navigation in JAWS.",
        "Ctrl+Alt+ArrowDown": "Table navigation in JAWS.",
        "Ctrl+Alt+ArrowLeft": "Table navigation in JAWS.",
        "Ctrl+Alt+ArrowRight": "Table navigation in JAWS.",
        "Alt+Shift+M": "Orca modifier combinations vary by desktop."
    };

    //: Order matters: a binding string must be canonical so two spellings of
    //: the same combination compare equal.
    var MODIFIER_ORDER = ["Ctrl", "Alt", "Shift", "Meta"];

    /*
     * Turn an event or a string into one canonical form.
     *
     * "ctrl+shift+l", "Shift+Ctrl+L" and the event itself all become
     * "Ctrl+Shift+L", so a rebind cannot silently fail to match.
     */
    function normalize(binding) {
        if (!binding) {
            return "";
        }
        var modifiers = {};
        var key = "";

        if (typeof binding === "string") {
            binding.split("+").forEach(function (part) {
                var token = part.trim();
                if (!token) {
                    return;
                }
                var lower = token.toLowerCase();
                if (lower === "ctrl" || lower === "control") {
                    modifiers.Ctrl = true;
                } else if (lower === "alt" || lower === "option") {
                    modifiers.Alt = true;
                } else if (lower === "shift") {
                    modifiers.Shift = true;
                } else if (lower === "meta" || lower === "cmd" || lower === "command") {
                    modifiers.Meta = true;
                } else {
                    key = token;
                }
            });
        } else {
            if (binding.ctrlKey) { modifiers.Ctrl = true; }
            if (binding.altKey) { modifiers.Alt = true; }
            if (binding.shiftKey) { modifiers.Shift = true; }
            if (binding.metaKey) { modifiers.Meta = true; }
            key = binding.key || "";
        }

        if (!key) {
            return "";
        }
        // Single characters upper-case so "l" and "L" are the same binding;
        // named keys keep their spelling so "ArrowUp" is not mangled.
        key = key.length === 1 ? key.toUpperCase() : key;

        var parts = MODIFIER_ORDER.filter(function (name) { return modifiers[name]; });
        parts.push(key);
        return parts.join("+");
    }

    /*
     * Is this binding a bare printable character?
     *
     * Shift alone does not rescue it: NVDA and JAWS use shifted letters for
     * reverse structural navigation, so `Shift+H` is as unavailable as `H`.
     */
    function isBareCharacter(binding) {
        var canonical = normalize(binding);
        if (!canonical) {
            return false;
        }
        var parts = canonical.split("+");
        var key = parts[parts.length - 1];
        var modifiers = parts.slice(0, -1);

        if (SAFE_BARE_KEYS.indexOf(key) !== -1) {
            return false;
        }
        if (!modifiers.length) {
            return key.length === 1;
        }
        if (modifiers.length === 1 && modifiers[0] === "Shift") {
            return key.length === 1;
        }
        return false;
    }

    function conflictFor(binding) {
        return KNOWN_CONFLICTS[normalize(binding)] || null;
    }

    function createShortcutManager(services) {
        var settings = services || {};
        var storage = settings.storage || null;
        var preferences = settings.preferences || null;
        var onConflict = settings.onConflict || null;

        var commands = {};
        var bindings = {};
        var listening = false;

        function allowsBareCharacters() {
            if (!preferences || typeof preferences.value !== "function") {
                return false;
            }
            return preferences.value("keyboard.singleKeyShortcuts") === true;
        }

        /*
         * Register a shortcut.
         *
         * `paletteCommand` is required, not optional. A shortcut is an
         * accelerator for something already reachable; if there is no such
         * thing, the feature is hidden behind a keystroke and that is the
         * defect (A.23).
         */
        function register(definition) {
            var spec = definition || {};
            if (!spec.id || typeof spec.run !== "function") {
                throw new Error("Aetos shortcut needs an id and a run function");
            }
            if (!spec.paletteCommand) {
                throw new Error(
                    "Aetos shortcut " + spec.id + " must name the palette command it " +
                    "duplicates: no feature may exist only behind a shortcut"
                );
            }

            var canonical = normalize(spec.defaultBinding);
            if (!canonical) {
                throw new Error("Aetos shortcut " + spec.id + " has no usable binding");
            }
            if (isBareCharacter(canonical) && !allowsBareCharacters()) {
                throw new Error(
                    "Aetos shortcut " + spec.id + " requests the bare character " +
                    canonical + ". Screen readers use single characters for " +
                    "structural navigation, so Aetos never ships one as a default."
                );
            }

            commands[spec.id] = {
                id: spec.id,
                label: spec.label || spec.id,
                description: spec.description || "",
                defaultBinding: canonical,
                paletteCommand: spec.paletteCommand,
                run: spec.run,
                // A shortcut whose feature is unavailable does nothing rather
                // than erroring, so a policy-gated editor cannot be reached by
                // keystroke when its palette entry is absent.
                when: typeof spec.when === "function" ? spec.when : null
            };
            if (!Object.prototype.hasOwnProperty.call(bindings, spec.id)) {
                bindings[spec.id] = canonical;
            }
            return commands[spec.id];
        }

        /*
         * List every shortcut with its current state (A.23: "view").
         */
        function list() {
            return Object.keys(commands).map(function (id) {
                var command = commands[id];
                var binding = bindings[id];
                return {
                    id: id,
                    label: command.label,
                    description: command.description,
                    binding: binding,
                    defaultBinding: command.defaultBinding,
                    disabled: binding === null,
                    changed: binding !== command.defaultBinding,
                    conflict: binding ? conflictFor(binding) : null,
                    paletteCommand: command.paletteCommand
                };
            });
        }

        function bindingOwner(canonical, exceptId) {
            var owner = null;
            Object.keys(bindings).forEach(function (id) {
                if (id !== exceptId && bindings[id] === canonical) {
                    owner = id;
                }
            });
            return owner;
        }

        /*
         * Rebind. Returns a result object rather than throwing on a soft
         * problem, because a warning the player may override is not an error.
         */
        function rebind(id, binding) {
            if (!commands[id]) {
                return { ok: false, reason: "unknown shortcut " + id };
            }
            var canonical = normalize(binding);
            if (!canonical) {
                return { ok: false, reason: "unusable binding" };
            }
            if (isBareCharacter(canonical) && !allowsBareCharacters()) {
                return {
                    ok: false,
                    reason: canonical + " is a bare character. Screen readers use " +
                        "single characters to navigate. Enable single-key shortcuts " +
                        "in accessibility preferences if you are sure."
                };
            }

            var warnings = [];
            var known = conflictFor(canonical);
            if (known) {
                warnings.push(known);
            }
            var taken = bindingOwner(canonical, id);
            if (taken) {
                warnings.push("Already used by " + (commands[taken].label || taken) + ".");
            }

            if (warnings.length && onConflict) {
                onConflict({ id: id, binding: canonical, warnings: warnings });
            }

            // The player wins. The table is advisory, and someone who has
            // remapped their own screen reader knows their setup better than a
            // hardcoded list does.
            bindings[id] = canonical;
            if (taken) {
                bindings[taken] = null;
            }
            return { ok: true, binding: canonical, warnings: warnings };
        }

        function disable(id) {
            if (!commands[id]) {
                return false;
            }
            bindings[id] = null;
            persist();
            return true;
        }

        function restore(id) {
            if (!commands[id]) {
                return false;
            }
            bindings[id] = commands[id].defaultBinding;
            persist();
            return true;
        }

        function restoreAll() {
            Object.keys(commands).forEach(function (id) {
                bindings[id] = commands[id].defaultBinding;
            });
            persist();
            return true;
        }

        /* --- Persistence -------------------------------------------------- */

        function persist() {
            if (!storage) {
                return Promise.resolve(false);
            }
            var changed = {};
            Object.keys(bindings).forEach(function (id) {
                if (!commands[id] || bindings[id] !== commands[id].defaultBinding) {
                    changed[id] = bindings[id];
                }
            });
            return storage
                .put("keybindings", { id: "shortcuts", bindings: changed })
                .then(function () { return true; })
                .catch(function () { return false; });
        }

        /*
         * Load saved bindings.
         *
         * Only differences from the default are stored, so a later change to a
         * default reaches players who never rebound that shortcut -- rather
         * than every player being frozen on whatever default existed the first
         * time they loaded the client.
         */
        function load() {
            if (!storage) {
                return Promise.resolve(list());
            }
            return storage
                .get("keybindings", "shortcuts")
                .then(function (stored) {
                    var saved = (stored && stored.bindings) || {};
                    Object.keys(saved).forEach(function (id) {
                        var value = saved[id];
                        bindings[id] = value === null ? null : normalize(value);
                    });
                    return list();
                })
                .catch(function () { return list(); });
        }

        /* --- Dispatch ------------------------------------------------------ */

        function handle(event) {
            var canonical = normalize(event);
            if (!canonical) {
                return false;
            }
            var matched = null;
            Object.keys(bindings).forEach(function (id) {
                if (bindings[id] === canonical) {
                    matched = id;
                }
            });
            if (!matched) {
                return false;
            }
            var command = commands[matched];
            if (command.when) {
                try {
                    if (!command.when()) {
                        return false;
                    }
                } catch (err) {
                    return false;
                }
            }
            event.preventDefault();
            command.run();
            return true;
        }

        /*
         * Listen at the document, in the capture phase.
         *
         * Capture because a player's hands are in the command input, and a
         * shortcut that only works when focus happens to be elsewhere is a
         * shortcut nobody can rely on.
         */
        function listen(target) {
            if (listening) {
                return false;
            }
            listening = true;
            (target || document).addEventListener("keydown", handle, true);
            return true;
        }

        return {
            register: register,
            list: list,
            rebind: rebind,
            disable: disable,
            restore: restore,
            restoreAll: restoreAll,
            load: load,
            persist: persist,
            listen: listen,
            handle: handle,
            bindingFor: function (id) { return bindings[id] || null; }
        };
    }

    window.AetosShortcutManager = {
        create: createShortcutManager,
        normalize: normalize,
        isBareCharacter: isBareCharacter,
        conflictFor: conflictFor,
        SAFE_BARE_KEYS: SAFE_BARE_KEYS.slice(),
        KNOWN_CONFLICTS: KNOWN_CONFLICTS
    };

})(window, document);
