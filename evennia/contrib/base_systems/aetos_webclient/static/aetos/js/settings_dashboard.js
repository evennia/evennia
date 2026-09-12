/*
 * Aetos settings dashboard.
 *
 * Gary: *"consolidate the settings into a nice settings dashboard and lets
 * expose for admins and deves appropriate settings and for players only a sub
 * set of settings appropriate for players"*.
 *
 * WHAT IT REPLACES. Nothing, in the sense that every destination here already
 * existed. What did not exist was any way to find them: privacy, themes,
 * automation groups, reminders, symbol packs and diagnostics were each a
 * command-palette entry and nothing else, so reaching any of them meant knowing
 * to press Ctrl+K and knowing what to type. That is the discovery problem A9
 * answered for the accessibility options, one layer up.
 *
 * TWO AUDIENCES, ONE HONEST GATE.
 *
 * The developer section appears only when the game has set
 * `AETOS_DIAGNOSTICS = True`, which reaches the client as a `diagnostics` key
 * in the manifest. That is a **game-wide** switch a developer sets in
 * settings.py, not a per-account permission -- everybody on that game sees the
 * developer tools or nobody does.
 *
 * It is deliberately not dressed up as a permission. **This grants no
 * authority.** The inspector shows a player their own session; the diagnostics
 * report names the game's own provider classes, which is why a game opts into
 * it. Hiding a section is a tidiness decision, and pretending it were a security
 * boundary would be the more dangerous mistake -- somebody would eventually rely
 * on it.
 *
 * Per-account gating is planned and needs the server to say so: a field in the
 * manifest marking the session as staff. When that arrives it feeds
 * `developerToolsAvailable()` and nothing else here changes.
 *
 * WHAT MAKES SOMETHING A PLAYER SETTING. It changes this player's own client
 * and nothing else. What makes something a developer setting is that it
 * describes the *game's* configuration -- its providers, its manifest, its
 * event pipeline -- which is information about somebody else's software that a
 * player has no use for and, on a live game, no business receiving.
 */

(function (window, document) {
    "use strict";

    function createSettingsDashboard(services) {
        var dialog = services.dialog;
        var settings = services.settings || {};
        var manifest = services.manifest || function () { return null; };
        var automationAllowed = services.automationAllowed || function () { return true; };
        var accessibilityPanel = services.accessibilityPanel || null;
        var inspector = services.inspector || null;
        var announce = services.announce || function () {};

        /*
         * Whether this game exposes its own configuration to the client.
         *
         * The manifest carries a `diagnostics` key only when the game set
         * `AETOS_DIAGNOSTICS`. Absent means the handshake has not happened yet
         * or the game declined -- either way, no developer section, which is
         * the safe direction to be wrong in.
         */
        function developerToolsAvailable() {
            var current = manifest();
            return !!(current && current.diagnostics);
        }

        /*
         * The destinations, in two groups.
         *
         * `when` is asked at open time rather than at build time, because the
         * manifest arrives after boot and a game's automation policy can differ from
         * the defaults. A row that would do nothing is not shown.
         */
        function sections() {
            return [
                {
                    heading: "Your client",
                    detail: "Everything here changes your client and is stored in "
                        + "this browser. None of it is sent to the game.",
                    entries: [
                        {
                            label: "Display and accessibility",
                            detail: "Text size, sound, contrast, motion and announcements.",
                            when: function () { return !!accessibilityPanel; },
                            run: function () { accessibilityPanel.toggleOptions(); }
                        },
                        {
                            label: "Themes",
                            detail: "Colour schemes, checked for contrast before they apply.",
                            when: function () { return !!settings.openThemes; },
                            run: function () { settings.openThemes(); }
                        },
                        {
                            label: "Automation groups",
                            detail: "Switch sets of your macros, aliases and triggers on "
                                + "and off together.",
                            when: function () {
                                return !!settings.openGroups
                                    && (automationAllowed("macros")
                                        || automationAllowed("aliases")
                                        || automationAllowed("triggers"));
                            },
                            run: function () { settings.openGroups(); }
                        },
                        {
                            label: "Reminders",
                            detail: "Notes to yourself, surfaced when you come back.",
                            when: function () { return !!settings.openReminders; },
                            run: function () { settings.openReminders(); }
                        },
                        {
                            label: "Symbol packs",
                            detail: "Picture sets for the word board.",
                            when: function () { return !!settings.openSymbolPacks; },
                            run: function () { settings.openSymbolPacks(); }
                        },
                        {
                            label: "Privacy and your data",
                            detail: "What is stored in this browser, counted, with a way "
                                + "to delete all of it.",
                            when: function () { return !!settings.openPrivacy; },
                            run: function () { settings.openPrivacy(); }
                        },
                        {
                            label: "Export your profile",
                            detail: "Everything you have set up, as one file you can keep.",
                            when: function () { return !!settings.exportProfile; },
                            run: function () { settings.exportProfile(); }
                        },
                        {
                            label: "Import a profile",
                            detail: "Restore a profile from a file.",
                            when: function () { return !!settings.importProfile; },
                            run: function () { settings.importProfile(); }
                        }
                    ]
                },
                {
                    heading: "For game developers",
                    detail: "Shown because this game set AETOS_DIAGNOSTICS. These "
                        + "describe the game's own configuration rather than your "
                        + "client, and none of them grants any authority.",
                    when: developerToolsAvailable,
                    entries: [
                        {
                            label: "Developer inspector",
                            detail: "Live protocol, providers, state, events and layout.",
                            when: function () { return !!inspector; },
                            run: function () { inspector.open(); }
                        },
                        {
                            label: "Diagnostics report",
                            detail: "A report to paste into a bug report. Names classes "
                                + "and slots, never values.",
                            when: function () { return !!settings.openDiagnostics; },
                            run: function () { settings.openDiagnostics(false); }
                        },
                        {
                            label: "Validate all automation",
                            detail: "Check every alias, trigger, timer and script at once.",
                            when: function () { return !!settings.validateAll; },
                            run: function () { settings.validateAll(); }
                        },
                        {
                            label: "Contrast report",
                            detail: "Every theme token pair, measured against WCAG.",
                            when: function () { return !!settings.showContrastReport; },
                            run: function () { settings.showContrastReport(); }
                        }
                    ]
                }
            ];
        }

        function buildEntry(entry) {
            var row = document.createElement("div");
            row.className = "aetos-settings__row";

            var button = document.createElement("button");
            button.type = "button";
            button.className = "aetos-list__button aetos-settings__button";
            button.textContent = entry.label;

            var detail = document.createElement("p");
            detail.className = "aetos-settings__detail";
            detail.id = "aetos-settings-" + entry.label.toLowerCase().replace(/[^a-z]+/g, "-");
            detail.textContent = entry.detail;

            // Described rather than named by the sentence: the button's name is
            // its label, and folding three lines into it would make every
            // screen reader read the paragraph before the word.
            button.setAttribute("aria-describedby", detail.id);

            button.addEventListener("click", function () {
                /*
                 * The dashboard closes before the destination opens.
                 *
                 * Two stacked modal dialogs is a focus trap inside a focus
                 * trap, and the way out of the inner one is not obvious from
                 * inside it.
                 */
                if (dialog && dialog.close) {
                    dialog.close(null);
                }
                entry.run();
            });

            row.appendChild(button);
            row.appendChild(detail);
            return row;
        }

        function buildContent() {
            var content = document.createElement("div");
            content.className = "aetos-settings";

            sections().forEach(function (section) {
                if (section.when && !section.when()) {
                    return;
                }
                var available = section.entries.filter(function (entry) {
                    return !entry.when || entry.when();
                });
                if (!available.length) {
                    return;
                }

                var group = document.createElement("section");
                group.className = "aetos-settings__group";

                var heading = document.createElement("h3");
                heading.className = "aetos-settings__heading";
                heading.textContent = section.heading;
                group.appendChild(heading);

                // A labelled group, so a screen reader announces which of the
                // two lists it has moved into.
                group.setAttribute("aria-label", section.heading);

                if (section.detail) {
                    var note = document.createElement("p");
                    note.className = "aetos-settings__detail";
                    note.textContent = section.detail;
                    group.appendChild(note);
                }

                available.forEach(function (entry) {
                    group.appendChild(buildEntry(entry));
                });
                content.appendChild(group);
            });

            return content;
        }

        function open() {
            if (!dialog || !dialog.open) {
                return false;
            }
            dialog.open({
                title: "Settings",
                description: "Everything you can configure, in one place. The command "
                    + "palette (Ctrl+K) still finds all of it by name.",
                content: buildContent(),
                dismissOnly: true
            });
            announce("Settings opened.");
            return true;
        }

        return {
            open: open,
            developerToolsAvailable: developerToolsAvailable,
            sections: sections
        };
    }

    window.AetosSettingsDashboard = { create: createSettingsDashboard };

})(window, document);
