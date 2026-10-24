/*
 * Aetos macros and the hotbar.
 *
 * A macro button holds one to five ordinary commands. Blueprint section 27 sets
 * five as a hard limit, and it is enforced here rather than merely documented:
 * the point of a macro is convenience, not a scripting language in disguise.
 *
 * MACROS ARE THE PLAYER'S, AND THE GAME'S PERMISSION IS REAL.
 *
 * Macro definitions are browser-local like everything else a player owns
 * (section 2.3). But whether macros may run at all is the *game's* decision,
 * declared in the manifest's automation policy (section 32). When a game sets
 * `macros: false` the hotbar does not appear and no macro can be run -- the
 * client honours the policy rather than quietly ignoring it.
 *
 * Every command still travels the ordinary command path through the shared
 * queue, so a macro can no more bypass a lock or a cooldown than typing the same
 * five lines by hand.
 */

(function (window, document) {
    "use strict";

    var MAX_COMMANDS = 5;
    var MAX_LABEL_LENGTH = 40;

    function createMacros(services) {
        var storage = services.storage;
        var queue = services.queue;
        var announce = services.announce || function () {};
        var confirm = services.confirm;
        var isAllowed = services.isAllowed || function () { return true; };

        function normalize(macro) {
            var commands = (macro.commands || [])
                .map(function (entry) { return String(entry || "").trim(); })
                .filter(Boolean)
                // The cap is applied on save, so an over-long macro cannot be
                // smuggled in by editing an exported profile and importing it.
                .slice(0, MAX_COMMANDS);
            return {
                id: macro.id || String(macro.label || "macro").trim().toLowerCase(),
                label: String(macro.label || "Macro").slice(0, MAX_LABEL_LENGTH),
                commands: commands,
                shortcut: macro.shortcut || null,
                delay: typeof macro.delay === "number" ? macro.delay : undefined,
                confirm: macro.confirm === true,
                order: typeof macro.order === "number" ? macro.order : 0
            };
        }

        function save(macro) {
            if (!storage) {
                return window.Promise.resolve(null);
            }
            var record = normalize(macro);
            if (!record.commands.length) {
                return window.Promise.reject(new Error("A macro needs at least one command."));
            }
            return storage.put("macros", record.id, record).then(function () {
                return record;
            });
        }

        function remove(id) {
            return storage ? storage.remove("macros", id) : window.Promise.resolve(false);
        }

        function all() {
            if (!storage) {
                return window.Promise.resolve([]);
            }
            return storage.all("macros").then(function (rows) {
                return rows.map(function (row) { return row.value; }).sort(function (a, b) {
                    if (a.order !== b.order) {
                        return a.order - b.order;
                    }
                    return String(a.label).localeCompare(String(b.label));
                });
            });
        }

        /*
         * Run a macro.
         *
         * Refuses when the game has disabled macros. Refusing loudly matters: a
         * button that silently does nothing reads as a broken client, whereas
         * "this game does not allow macros" is information.
         */
        function run(macro) {
            if (!isAllowed()) {
                announce("This game does not allow macros.");
                return false;
            }
            if (!macro || !(macro.commands || []).length) {
                return false;
            }

            function go() {
                return queue.run(macro.commands, {
                    label: macro.label,
                    delay: macro.delay,
                    completionMessage: macro.label + " finished."
                });
            }

            // Confirmation is per-macro and opt-in. A player who put "drop all"
            // on a button may want a second chance; one who put "north" does not
            // want to be asked every time.
            if (macro.confirm && confirm) {
                confirm({
                    title: "Run " + macro.label + "?",
                    description: macro.commands.join("\n"),
                    onConfirm: go
                });
                return true;
            }
            return go();
        }

        return {
            MAX_COMMANDS: MAX_COMMANDS,
            normalize: normalize,
            save: save,
            remove: remove,
            all: all,
            run: run
        };
    }

    /* ------------------------------------------------------------------
     * Hotbar widget
     * ------------------------------------------------------------------ */

    function createHotbarWidget(services) {
        var macros = services.macros;
        var editMacro = services.editMacro;
        var isAllowed = services.isAllowed || function () { return true; };

        return {
            id: "hotbar",
            accessibility: {
                landmarkLabel: "Macro hotbar",
                heading: "Hotbar",
                keyboardOperable: true,
                liveUpdates: false
            },
            displayName: "Hotbar",
            description: "Your macro buttons.",
            builtin: true,
            defaultRegion: "bottom",
            defaultSize: { height: 80 },
            subscriptions: ["manifest"],

            mount: function (context) {
                var bar = document.createElement("div");
                bar.className = "aetos-hotbar";
                // A toolbar role tells assistive technology these buttons belong
                // together, rather than being announced as unrelated controls.
                bar.setAttribute("role", "toolbar");
                bar.setAttribute("aria-label", "Macro buttons");

                var addButton = document.createElement("button");
                addButton.type = "button";
                addButton.className = "aetos-list__button";
                addButton.textContent = "+ New macro";
                addButton.addEventListener("click", function () { editMacro(null); });

                context.element.appendChild(bar);
                context.element.appendChild(addButton);
                context.barEl = bar;
                context.addEl = addButton;

                function refresh() {
                    var panel = context.element.closest
                        ? context.element.closest("[data-aetos-widget]")
                        : null;
                    // The game forbidding macros hides the whole widget. Showing
                    // a disabled hotbar would advertise a feature the player
                    // cannot use.
                    if (!isAllowed()) {
                        if (panel) {
                            panel.hidden = true;
                        }
                        return;
                    }
                    if (panel) {
                        panel.hidden = false;
                    }
                    macros.all().then(function (list) {
                        bar.textContent = "";
                        list.forEach(function (macro) {
                            var button = document.createElement("button");
                            button.type = "button";
                            button.className = "aetos-hotbar__button";
                            button.textContent = macro.label;
                            button.title = macro.commands.join("\n");
                            // The commands are part of the accessible name, so a
                            // screen-reader user knows what a button will do
                            // before pressing it.
                            button.setAttribute(
                                "aria-label",
                                macro.label + ": " + macro.commands.join(", "));
                            button.addEventListener("click", function () {
                                macros.run(macro);
                            });
                            window.AetosMenu.attach(button, function () {
                                return {
                                    trigger: button,
                                    label: macro.label,
                                    actions: [
                                        {
                                            group: "local",
                                            label: "Edit",
                                            run: function () { editMacro(macro); }
                                        },
                                        {
                                            group: "local",
                                            label: "Delete",
                                            run: function () {
                                                macros.remove(macro.id).then(refresh);
                                            }
                                        }
                                    ],
                                    onCommand: function () {}
                                };
                            });
                            bar.appendChild(button);
                        });
                    });
                }

                context.refresh = refresh;
                services.registerRefresh(refresh);
                refresh();
            },

            update: function (context) {
                // The manifest may arrive or change after mount; the hotbar's
                // visibility depends on it.
                if (context.refresh) {
                    context.refresh();
                }
            }
        };
    }

    window.AetosMacros = {
        create: createMacros,
        createWidget: createHotbarWidget,
        MAX_COMMANDS: MAX_COMMANDS
    };

})(window, document);
