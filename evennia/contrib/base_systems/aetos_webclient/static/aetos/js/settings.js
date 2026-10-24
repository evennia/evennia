/*
 * Aetos settings: automation editors and the privacy panel.
 *
 * Brings together the editor forms deferred from M12-M14 (macros, aliases,
 * triggers, timers, scripts) and the Privacy & Local Data panel required by
 * blueprint section 63.
 *
 * TWO PRINCIPLES SHAPE THIS FILE.
 *
 * 1. AN EDITOR IS NEVER OFFERED FOR SOMETHING THE GAME FORBIDS.
 *
 *    Section 32 is explicit: if scripting is disabled, no scripting editor
 *    appears. Not a disabled button, not an editor that refuses on save -- the
 *    entry is simply absent. Offering a form that cannot work wastes the
 *    player's time and misrepresents the game.
 *
 * 2. THE PRIVACY PANEL SHOWS WHAT IS ACTUALLY THERE.
 *
 *    Counts are read from storage rather than assumed, so the panel cannot
 *    drift from reality. A privacy screen that under-reports is worse than none,
 *    because it is actively reassuring about something it has not checked.
 */

(function (window, document) {
    "use strict";

    function createSettings(services) {
        var storage = services.storage;
        var profile = services.profile;
        var announce = services.announce || function () {};
        var dialog = services.dialog;

        /* --- Small helpers ------------------------------------------------ */

        function lines(value) {
            return String(value || "")
                .split("\n")
                .map(function (line) { return line.trim(); })
                .filter(Boolean);
        }

        function commaList(value) {
            return String(value || "")
                .split(",")
                .map(function (entry) { return entry.trim(); })
                .filter(Boolean);
        }

        function report(promise, what) {
            return promise.then(function (saved) {
                announce(what + " saved.");
                return saved;
            }).catch(function (err) {
                // The engines reject with useful messages; surfacing them beats
                // a generic failure the player cannot act on.
                announce(err.message);
                return null;
            });
        }

        /* --- Alias editor -------------------------------------------------- */

        function editAlias(existing) {
            var alias = existing || {};
            dialog.open({
                title: existing ? "Edit alias" : "New alias",
                description:
                    "The first word you type is replaced. Use $1 for one word " +
                    "and $* for the rest, so 'tell $1 $*' turns 'tt Bob hi there' " +
                    "into 'tell Bob hi there'.",
                fields: [
                    { name: "pattern", label: "When I type", value: alias.pattern || "" },
                    { name: "expansion", label: "Send instead", value: alias.expansion || "" }
                ],
                onSubmit: function (values) {
                    report(services.aliases.save({
                        id: alias.id,
                        pattern: values.pattern,
                        expansion: values.expansion
                    }), "Alias");
                }
            });
        }

        /* --- Trigger editor -------------------------------------------------- */

        function editTrigger(existing) {
            var trigger = existing || { kind: "text", mode: "contains" };
            dialog.open({
                title: existing ? "Edit trigger" : "New trigger",
                description:
                    "Runs commands when the game says something. Structured " +
                    "triggers are more reliable where a game exposes data -- " +
                    "text matching breaks when a game rewords a message.",
                fields: [
                    { name: "label", label: "Name", value: trigger.label || "" },
                    {
                        name: "pattern",
                        label: "When the game says (text triggers)",
                        value: trigger.pattern || ""
                    },
                    {
                        name: "regex",
                        label: "Treat as a regular expression",
                        type: "checkbox",
                        value: trigger.mode === "regex"
                    },
                    {
                        name: "commands",
                        label: "Then run (one command per line, max 5)",
                        type: "textarea",
                        value: (trigger.commands || []).join("\n")
                    }
                ],
                onSubmit: function (values) {
                    report(services.triggers.save({
                        id: trigger.id,
                        label: values.label,
                        kind: "text",
                        pattern: values.pattern,
                        mode: values.regex ? "regex" : "contains",
                        commands: lines(values.commands)
                    }).then(function (saved) {
                        services.reloadTriggers();
                        return saved;
                    }), "Trigger");
                }
            });
        }

        /* --- Timer editor ---------------------------------------------------- */

        function editTimer(existing) {
            var timer = existing || {};
            dialog.open({
                title: existing ? "Edit timer" : "New timer",
                description:
                    "Runs commands on a schedule, even while you are not typing. " +
                    "Your game has allowed this; be sure its rules permit " +
                    "unattended play.",
                fields: [
                    { name: "label", label: "Name", value: timer.label || "" },
                    {
                        name: "seconds",
                        label: "Every (seconds)",
                        value: String((timer.interval || 60000) / 1000)
                    },
                    {
                        name: "repeat",
                        label: "Repeat (otherwise runs once)",
                        type: "checkbox",
                        value: timer.repeat !== false
                    },
                    {
                        name: "commands",
                        label: "Run (one command per line, max 5)",
                        type: "textarea",
                        value: (timer.commands || []).join("\n")
                    }
                ],
                onSubmit: function (values) {
                    var seconds = parseFloat(values.seconds);
                    report(services.timers.save({
                        id: timer.id,
                        label: values.label,
                        interval: (isFinite(seconds) ? seconds : 60) * 1000,
                        repeat: values.repeat,
                        commands: lines(values.commands)
                    }).then(function (saved) {
                        if (saved) {
                            services.timers.start(saved);
                        }
                        return saved;
                    }), "Timer");
                }
            });
        }

        /* --- Script editor ---------------------------------------------------- */

        function editScript(existing) {
            var script = existing || {};
            dialog.open({
                title: existing ? "Edit script" : "New script",
                description:
                    "Aetos Script. Available: send, echo, resource, room, target, " +
                    "get, set. It cannot reach the web, your files, or the page -- " +
                    "only these.",
                fields: [
                    { name: "label", label: "Name", value: script.label || "" },
                    {
                        name: "source",
                        label: "Script",
                        type: "textarea",
                        rows: 12,
                        value: script.source ||
                            'if resource("health") < 0.3 then\n  send("quaff potion")\nend'
                    }
                ],
                onSubmit: function (values) {
                    // save() compiles, so a syntax error is reported here with
                    // its line rather than the first time the script runs.
                    report(services.scripting.save({
                        id: script.id,
                        label: values.label,
                        source: values.source
                    }), "Script");
                }
            });
        }




        /* --- Diagnostic report (E5) -------------------------------------- */

        /*
         * Build a report, show it in full, and let the developer decide.
         *
         * The whole point is that nothing leaves the browser until a person has
         * looked at it. A tool that filed an issue on somebody's behalf with a
         * payload they had not read would be indefensible however convenient.
         */
        function openDiagnostics(includeOutput) {
            var diagnostics = services.diagnostics;
            if (!diagnostics) {
                return null;
            }
            var report = diagnostics.build({ includeOutput: includeOutput === true });
            var summary = diagnostics.describe(report);
            var text = diagnostics.toText(report);

            var body = document.createElement("div");

            var intro = document.createElement("p");
            intro.className = "aetos-dialog__description";
            intro.textContent =
                "This describes your client so a maintainer can understand a " +
                "bug. Read it before you share it -- nothing has been sent.";
            body.appendChild(intro);

            [["Includes", summary.contains], ["Never includes", summary.excludes]]
                .forEach(function (entry) {
                    var heading = document.createElement("h3");
                    heading.className = "aetos-help__heading";
                    heading.textContent = entry[0];
                    body.appendChild(heading);

                    var list = document.createElement("ul");
                    list.className = "aetos-list";
                    entry[1].forEach(function (item) {
                        var row = document.createElement("li");
                        row.textContent = item;
                        list.appendChild(row);
                    });
                    body.appendChild(list);
                });

            var label = document.createElement("label");
            label.className = "aetos-visually-hidden";
            label.setAttribute("for", "aetos-diagnostics-text");
            label.textContent = "Diagnostic report";
            body.appendChild(label);

            // A textarea rather than a <pre>: it is selectable, scrollable,
            // keyboard-reachable and copyable with the keys everybody already
            // knows, without Aetos reimplementing any of that.
            var area = document.createElement("textarea");
            area.id = "aetos-diagnostics-text";
            area.className = "aetos-input aetos-diagnostics__text";
            area.rows = 12;
            area.readOnly = true;
            area.value = text;
            body.appendChild(area);

            var actions = [
                {
                    label: includeOutput ? "Rebuild without game text" : "Include recent game text",
                    run: function () { openDiagnostics(!includeOutput); }
                },
                {
                    label: "Copy",
                    run: function () {
                        area.select();
                        try {
                            document.execCommand("copy");
                            announce("Report copied.", {
                                category: "system", priority: "important" });
                        } catch (err) {
                            announce("Could not copy; select the text and copy it " +
                                "yourself.", { category: "system",
                                               priority: "important" });
                        }
                    }
                }
            ];

            dialog.open({
                title: "Diagnostic report",
                content: body,
                submitLabel: "Close",
                extraActions: actions,
                fields: [],
                onSubmit: function () {}
            });
            return report;
        }

        /* --- Validate all local automation (E4) -------------------------- */

        /*
         * Check everything at once.
         *
         * Runs entirely in this browser against the player's own configuration.
         * Nothing is uploaded -- the whole reason this data lives locally is
         * that it stays there, and a validator that phoned home to check a
         * regular expression would be an odd exception to that.
         */
        function validateAll() {
            var validator = services.validator;
            if (!validator) {
                return null;
            }
            // Async: half the engines read from IndexedDB.
            return validator.validateAll().then(function (results) {
            var body = document.createElement("div");

            var summary = document.createElement("p");
            summary.className = "aetos-dialog__description";
            summary.textContent = results.checked === 0
                ? "You have no automation to check yet."
                : results.checked + " item" + (results.checked === 1 ? "" : "s") +
                  " checked. " + results.errors + " error" +
                  (results.errors === 1 ? "" : "s") + ", " + results.warnings +
                  " warning" + (results.warnings === 1 ? "" : "s") + ".";
            body.appendChild(summary);

            var list = document.createElement("ul");
            list.className = "aetos-privacy__list";
            list.setAttribute("tabindex", "0");
            list.setAttribute("aria-label", "Validation results by kind");

            validator.summarize(results).forEach(function (entry) {
                var row = document.createElement("li");
                row.className = "aetos-privacy__row";
                var name = document.createElement("span");
                name.textContent = FRIENDLY_KINDS[entry.kind] || entry.kind;
                var value = document.createElement("span");
                value.className = "aetos-privacy__count";
                value.textContent = entry.text;
                row.appendChild(name);
                row.appendChild(value);
                list.appendChild(row);

                // The detail, so a player is not told "2 warnings" and left to
                // find them. A count without a location is a chore, not a
                // report.
                entry.bucket.items.forEach(function (item) {
                    item.findings.forEach(function (found) {
                        if (found.severity === "info") {
                            return;
                        }
                        var detail = document.createElement("li");
                        detail.className = "aetos-privacy__row aetos-validate__detail";
                        var label = document.createElement("span");
                        // Severity in words, never colour alone.
                        label.textContent = found.severity.toUpperCase() + ": " +
                            (item.name || "unnamed");
                        var message = document.createElement("span");
                        message.className = "aetos-privacy__count";
                        message.textContent = found.message;
                        detail.appendChild(label);
                        detail.appendChild(message);
                        list.appendChild(detail);
                    });
                });
            });

            body.appendChild(list);

            var privacy = document.createElement("p");
            privacy.className = "aetos-dialog__description";
            privacy.textContent =
                "Checked in this browser. Nothing was sent anywhere.";
            body.appendChild(privacy);

            dialog.open({
                title: "Validate automation",
                content: body,
                submitLabel: "Close",
                fields: [],
                onSubmit: function () {}
            });
            announce(
                results.errors
                    ? results.errors + " problems found."
                    : "Everything checks out.",
                { category: "system", priority: "important" }
            );
            return results;
            });
        }

        var FRIENDLY_KINDS = {
            trigger: "Triggers",
            alias: "Aliases",
            timer: "Timers",
            script: "Scripts",
            displayRule: "Display rules",
            macro: "Macros"
        };

        /* --- Automation groups (E3) ------------------------------------- */

        /*
         * One switch for a set of related automation.
         *
         * The list states, for every group, how many rules it currently
         * suppresses. A player looking at a trigger that is not firing needs to
         * know whether they turned it off or their group did -- those have
         * completely different fixes, and a rule that silently does nothing is
         * indistinguishable from a rule that is broken.
         */
        function openGroups() {
            var groups = services.groups;
            if (!groups) {
                return null;
            }

            var body = document.createElement("div");

            var explanation = document.createElement("p");
            explanation.className = "aetos-dialog__description";
            explanation.textContent =
                "A group switches related automation on and off together. A rule " +
                "runs only when both it and its group are enabled -- turning a " +
                "group on never re-enables a rule you switched off yourself.";
            body.appendChild(explanation);

            var notice = document.createElement("p");
            notice.className = "aetos-dialog__description";
            notice.textContent =
                "Nothing changes a group except you. Switching workspace does not, " +
                "and neither does anything the game sends.";
            body.appendChild(notice);

            var list = document.createElement("ul");
            list.className = "aetos-privacy__list";
            list.setAttribute("tabindex", "0");
            list.setAttribute("aria-label", "Automation groups");

            var all = groups.all();
            if (!all.length) {
                var empty = document.createElement("p");
                empty.className = "aetos-dialog__description";
                empty.textContent = "No groups yet.";
                body.appendChild(empty);
            }

            all.forEach(function (group) {
                var row = document.createElement("li");
                row.className = "aetos-privacy__row";

                var button = document.createElement("button");
                button.type = "button";
                button.className = "aetos-list__button";
                button.textContent = group.name;
                // Pressed state, not a colour: the switch has to be readable
                // to somebody who cannot see the styling.
                button.setAttribute("aria-pressed", group.enabled ? "true" : "false");
                button.addEventListener("click", function () {
                    groups.toggle(group.id, countMembers(group.id)).then(function () {
                        openGroups();
                    });
                });

                var state = document.createElement("span");
                state.className = "aetos-privacy__count";
                var members = countMembers(group.id);
                state.textContent = group.enabled
                    ? "on, " + members + (members === 1 ? " rule" : " rules")
                    : "off, " + members + (members === 1 ? " rule" : " rules") +
                        " suppressed";

                row.appendChild(button);
                row.appendChild(state);
                list.appendChild(row);
            });

            body.appendChild(list);

            dialog.open({
                title: "Automation groups",
                content: body,
                submitLabel: "New group",
                fields: [],
                onSubmit: function () { editGroup(null); }
            });
            return true;
        }

        /*
         * How many rules belong to a group.
         *
         * Counted across every automation surface rather than tracked, because
         * a count that is stored can disagree with reality and a count that is
         * derived cannot.
         */
        function countMembers(groupId) {
            var total = 0;
            [services.aliases, services.triggers, services.timers,
             services.scripting, services.displayRules].forEach(function (engine) {
                if (!engine || typeof engine.all !== "function") {
                    return;
                }
                try {
                    total += engine.all().filter(function (rule) {
                        return rule.group === groupId;
                    }).length;
                } catch (err) {
                    // An engine that fails to enumerate costs its own count,
                    // not the dialog.
                }
            });
            return total;
        }

        function editGroup(existing) {
            var group = existing || {};
            dialog.open({
                title: existing ? "Edit group" : "New group",
                description:
                    "Give the group a name you would recognise in a hurry -- " +
                    "Combat, Crafting, Roleplay. You assign rules to it when " +
                    "you edit them.",
                fields: [
                    { name: "name", label: "Name", value: group.name || "" },
                    {
                        name: "description",
                        label: "What it is for (optional)",
                        value: group.description || ""
                    },
                    {
                        name: "enabled",
                        label: "Enabled",
                        type: "checkbox",
                        value: group.enabled !== false
                    }
                ],
                onSubmit: function (values) {
                    report(services.groups.save({
                        id: group.id,
                        name: values.name,
                        description: values.description,
                        enabled: values.enabled
                    }), "Group");
                }
            });
        }

        /* --- Display rules (deferred from E2) ---------------------------- */

        /*
         * Highlight, substitute, filter and collapse.
         *
         * The description says plainly what these do and do not do, because
         * "filter" reads like "delete" to anyone who has used another client,
         * and the difference is the entire point.
         */
        function editDisplayRule(existing) {
            var rule = existing || { kind: "highlight" };
            dialog.open({
                title: existing ? "Edit display rule" : "New display rule",
                description:
                    "Changes how game output looks. It never changes what " +
                    "happened: a hidden line is still in your history, still " +
                    "searchable, and still triggers whatever was watching for it.",
                fields: [
                    { name: "label", label: "Name", value: rule.label || "" },
                    {
                        name: "kind",
                        label: "highlight, substitute, filter or collapse",
                        value: rule.kind || "highlight"
                    },
                    { name: "pattern", label: "When output contains", value: rule.pattern || "" },
                    {
                        name: "regex",
                        label: "Treat as a regular expression",
                        type: "checkbox",
                        value: rule.regex === true
                    },
                    {
                        name: "replacement",
                        label: "Replace with (substitute only)",
                        value: rule.replacement || ""
                    },
                    {
                        name: "group",
                        label: "Automation group (optional)",
                        value: rule.group || ""
                    }
                ],
                onSubmit: function (values) {
                    report(services.displayRules.save({
                        id: rule.id,
                        kind: values.kind,
                        label: values.label,
                        pattern: values.pattern,
                        regex: values.regex,
                        replacement: values.replacement,
                        group: values.group
                    }), "Display rule");
                }
            });
        }

        /* --- Privacy and local data --------------------------------------------
         *
         * Section 63. The player should be able to see exactly what is kept
         * about them, export it, and delete it.
         */

        var FRIENDLY_NAMES = {
            layouts: "Layouts",
            workspaces: "Workspaces",
            macros: "Macros",
            aliases: "Aliases",
            triggers: "Triggers and timers",
            scripts: "Scripts",
            variables: "Script variables",
            relationships: "Relationship tags",
            notes: "Notes",
            map_notes: "Map notes",
            map_pois: "Map points of interest",
            display_rules: "Display rules",
            reminders: "Reminders and tasks",
            themes: "Themes",
            keybindings: "Keybindings",
            preferences: "Preferences",
            automation_profiles: "Automation groups"
        };

        function openPrivacy() {
            storage.counts().then(function (counts) {
                var blocked = storage.isBlocked
                    ? storage.isBlocked()
                    : Promise.resolve(false);
                Promise.all([storage.isPersistent(), blocked]).then(function (state) {
                    var persistent = state[0];
                    var isBlocked = state[1];
                    var body = document.createElement("div");

                    var explanation = document.createElement("p");
                    explanation.className = "aetos-dialog__description";
                    /*
                     * Three cases, not two.
                     *
                     * "Blocked by another tab" and "this browser refuses to
                     * store anything" both land on the memory backend, but
                     * they have completely different fixes -- and a player
                     * told the wrong one goes looking in the wrong place.
                     */
                    if (persistent) {
                        explanation.textContent =
                            "Everything below is stored in this browser only. " +
                            "It is never sent to the game server.";
                    } else if (isBlocked) {
                        explanation.textContent =
                            "Aetos is open in another tab using an older version of " +
                            "its local database, so this tab cannot save anything. " +
                            "Close the other tab and reload this one -- nothing has " +
                            "been lost.";
                    } else {
                        explanation.textContent =
                            "This browser is not storing data (private mode or " +
                            "blocked storage), so nothing here will survive the session.";
                    }
                    body.appendChild(explanation);

                    var table = document.createElement("ul");
                    table.className = "aetos-privacy__list";
                    /*
                     * Focusable, because it scrolls.
                     *
                     * Arrow keys scroll whatever has focus, so a scrolling
                     * region outside the tab order cannot be scrolled by
                     * keyboard at all -- the player can see there is more and
                     * has no way to reach it. Found by axe as
                     * `scrollable-region-focusable`; invisible to anyone
                     * testing with a mouse wheel.
                     *
                     * A focusable region needs a name, or it is announced as
                     * an unlabelled group.
                     *
                     * The name goes on the <ul> without touching its role. An
                     * earlier attempt set role="group" here, which stripped the
                     * implicit `list` role and orphaned every <li> -- axe
                     * caught it immediately as `listitem`. A list can carry an
                     * accessible name perfectly well as a list.
                     */
                    table.setAttribute("tabindex", "0");
                    table.setAttribute("aria-label", "Stored data by category");
                    var total = 0;
                    storage.namespaces.forEach(function (namespace) {
                        var count = counts[namespace] || 0;
                        total += count;
                        var row = document.createElement("li");
                        row.className = "aetos-privacy__row";
                        var name = document.createElement("span");
                        name.textContent = FRIENDLY_NAMES[namespace] || namespace;
                        var value = document.createElement("span");
                        value.className = "aetos-privacy__count";
                        value.textContent = String(count);
                        row.appendChild(name);
                        row.appendChild(value);
                        table.appendChild(row);
                    });
                    body.appendChild(table);

                    var summary = document.createElement("p");
                    summary.className = "aetos-dialog__description";
                    summary.textContent = total === 0
                        ? "Nothing is stored yet."
                        : total + " item" + (total === 1 ? "" : "s") + " in total.";
                    body.appendChild(summary);

                    dialog.open({
                        title: "Privacy and local data",
                        content: body,
                        submitLabel: "Export everything",
                        extraActions: [
                            {
                                label: "Clear all Aetos data",
                                // Destructive, so it confirms. The confirmation
                                // names what will go, because "are you sure?"
                                // without specifics is not informed consent.
                                run: function () {
                                    dialog.open({
                                        title: "Clear all Aetos data?",
                                        description:
                                            "This deletes " + total + " stored item" +
                                            (total === 1 ? "" : "s") +
                                            " -- layouts, macros, notes, relationship " +
                                            "tags and the rest, plus any cached " +
                                            "copy of the client itself. " +
                                            "It cannot be undone. " +
                                            "Your game account is not affected, " +
                                            "and nothing belonging to other " +
                                            "software is touched.",
                                        submitLabel: "Delete everything",
                                        fields: [],
                                        onSubmit: function () {
                                            /*
                                             * The service worker's cache goes
                                             * too. A cache the panel does not
                                             * clear is data a player was told
                                             * they had deleted -- which is a
                                             * worse failure than not offering
                                             * to delete it at all.
                                             */
                                            var caches = services.pwa
                                                ? services.pwa.clearCaches()
                                                : Promise.resolve(0);
                                            Promise.all([
                                                storage.clearAll(),
                                                caches
                                            ]).then(function () {
                                                announce("All Aetos data cleared.");
                                            });
                                        }
                                    });
                                }
                            }
                        ],
                        fields: [],
                        onSubmit: function () {
                            exportProfile();
                        }
                    });
                });
            });
        }

        /* --- Export and import ------------------------------------------------- */

        function exportProfile() {
            profile.exportProfile(null, {
                timestamp: new Date().toISOString(),
                game: services.gameName
            }).then(function (data) {
                var text = profile.toJson(data);
                var blob = new window.Blob([text], { type: "application/json" });
                var url = window.URL.createObjectURL(blob);
                var link = document.createElement("a");
                link.href = url;
                link.download = "aetos-profile.json";
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                // Revoke on the next tick, not immediately: revoking before the
                // browser has started the download cancels it.
                window.setTimeout(function () { window.URL.revokeObjectURL(url); }, 1000);
                announce("Profile exported.");
            });
        }

        function importProfile() {
            var picker = document.createElement("input");
            picker.type = "file";
            picker.accept = "application/json,.json";
            picker.addEventListener("change", function () {
                var file = picker.files && picker.files[0];
                if (!file) {
                    return;
                }
                var reader = new window.FileReader();
                reader.onload = function () {
                    profile.importProfile(reader.result).then(function (result) {
                        // Report what was refused as well as what landed. An
                        // import that silently drops half a file is worse than
                        // one that says so.
                        var message = "Imported " + result.imported + " item" +
                            (result.imported === 1 ? "" : "s") + ".";
                        if (result.rejected) {
                            message += " " + result.rejected + " rejected.";
                        }
                        if (result.unknownNamespaces.length) {
                            message += " Unknown sections ignored: " +
                                result.unknownNamespaces.join(", ") + ".";
                        }
                        announce(message);
                    }).catch(function (err) {
                        announce("Import failed: " + err.message);
                    });
                };
                reader.readAsText(file);
            });
            picker.click();
        }

        /* --- Reminders and tasks (A5) ------------------------------------ */

        /*
         * The player's own list.
         *
         * Every entry here was typed by them. Aetos does not add to this list,
         * does not reorder it by what it thinks is urgent, and does not mark
         * anything done on their behalf -- a memory aid that edits itself is a
         * memory aid you cannot trust, and the person reaching for one is the
         * last person who should have to audit it.
         */
        function openReminders() {
            var cognitive = services.cognitive;
            if (!cognitive || !dialog) {
                return null;
            }

            var body = document.createElement("div");

            var explanation = document.createElement("p");
            explanation.className = "aetos-dialog__description";
            explanation.textContent =
                "Notes to yourself, kept in this browser. Aetos never adds one, " +
                "and never sends them anywhere.";
            body.appendChild(explanation);

            var list = document.createElement("ul");
            list.className = "aetos-privacy__list";
            list.setAttribute("tabindex", "0");
            list.setAttribute("aria-label", "Reminders and tasks");

            var items = cognitive.all();
            if (!items.length) {
                var empty = document.createElement("p");
                empty.className = "aetos-dialog__description";
                empty.textContent = "Nothing saved yet.";
                body.appendChild(empty);
            }

            items.forEach(function (item) {
                var row = document.createElement("li");
                row.className = "aetos-privacy__row";

                var toggle = document.createElement("button");
                toggle.type = "button";
                toggle.className = "aetos-list__button";
                toggle.textContent = item.text;
                // Done state as a pressed button rather than a strikethrough,
                // which is invisible to a screen reader and easy to miss.
                toggle.setAttribute("aria-pressed", item.completed ? "true" : "false");
                toggle.addEventListener("click", function () {
                    cognitive.complete(item.id, !item.completed).then(function () {
                        announce(item.completed ? "Reopened." : "Done.");
                        openReminders();
                    });
                });
                row.appendChild(toggle);

                var where = document.createElement("span");
                where.className = "aetos-privacy__count";
                where.textContent = item.trigger === "here" && item.locationName
                    ? "at " + item.locationName
                    : item.trigger;
                row.appendChild(where);

                var drop = document.createElement("button");
                drop.type = "button";
                drop.className = "aetos-list__button";
                drop.textContent = "Delete";
                // Named, because "Delete" repeated down a list is
                // indistinguishable when tabbed through out of context.
                drop.setAttribute("aria-label", "Delete: " + item.text);
                drop.addEventListener("click", function () {
                    cognitive.remove(item.id).then(function () {
                        announce("Deleted.");
                        openReminders();
                    });
                });
                row.appendChild(drop);

                list.appendChild(row);
            });
            body.appendChild(list);

            dialog.open({
                title: "Reminders and tasks",
                content: body,
                submitLabel: "Close",
                fields: [],
                onSubmit: function () {}
            });
            return items;
        }

        function editReminder(room) {
            var cognitive = services.cognitive;
            if (!cognitive || !dialog) {
                return null;
            }
            dialog.open({
                title: "New reminder",
                description:
                    "Choose when it should come back to you: 'pinned' keeps it in " +
                    "view, 'here' brings it up when you next enter this room, and " +
                    "'next-session' holds it until you next connect.",
                fields: [
                    { name: "text", label: "Remind me", value: "" },
                    { name: "trigger", label: "When (pinned, here, next-session)",
                      value: "pinned" },
                    { name: "kind", label: "Kind (reminder or task)", value: "reminder" }
                ],
                onSubmit: function (values) {
                    var here = values.trigger === "here" ? (room || {}) : {};
                    report(cognitive.save({
                        text: values.text,
                        trigger: values.trigger,
                        kind: values.kind,
                        locationId: here.id || null,
                        locationName: here.name || null
                    }), "Reminder");
                }
            });
            return true;
        }

        /* --- Reorient Me (A5) -------------------------------------------- */

        /*
         * The same facts the announcer speaks, on screen.
         *
         * Shown as well as spoken because "where am I" is not only a screen
         * reader question -- somebody who looked away for two minutes wants to
         * read it, and a summary that exists only as speech is unavailable to
         * anyone who has scrolled past it.
         */
        function openOrientation() {
            var orientation = services.orientation;
            if (!orientation || !dialog) {
                return null;
            }
            var summary = orientation.reorient();

            var body = document.createElement("div");
            if (!summary.sections.length) {
                var empty = document.createElement("p");
                empty.className = "aetos-dialog__description";
                empty.textContent = "Nothing is known yet.";
                body.appendChild(empty);
            }
            summary.sections.forEach(function (section) {
                var heading = document.createElement("h3");
                heading.className = "aetos-dialog__subheading";
                heading.textContent = section.title;
                body.appendChild(heading);

                var text = document.createElement("p");
                text.className = "aetos-dialog__description";
                // Same joiner as the spoken summary, so the two cannot drift.
                text.textContent = section.lines.join("; ");
                body.appendChild(text);
            });

            dialog.open({
                title: "Where am I",
                content: body,
                submitLabel: "Close",
                fields: [],
                onSubmit: function () {}
            });
            return summary;
        }

        /* --- Themes (M19) ------------------------------------------------ */

        /*
         * Pick a theme.
         *
         * The list says, for each theme, whether it currently meets contrast.
         * Not as a badge but as words, because "3 contrast problems" is
         * actionable and a red dot is not -- and because a colour-coded warning
         * about colour would be its own joke.
         */
        function openThemes() {
            var themes = services.themes;
            if (!themes || !dialog) {
                return null;
            }

            var body = document.createElement("div");

            var explanation = document.createElement("p");
            explanation.className = "aetos-dialog__description";
            explanation.textContent =
                "Themes change colours only, and are stored in this browser. Your " +
                "accessibility settings are applied afterwards, so a theme can never " +
                "undo high contrast or reduced motion.";
            body.appendChild(explanation);

            var list = document.createElement("ul");
            list.className = "aetos-privacy__list";
            list.setAttribute("tabindex", "0");
            list.setAttribute("aria-label", "Themes");

            var active = themes.active();
            themes.all().forEach(function (theme) {
                var row = document.createElement("li");
                row.className = "aetos-privacy__row";

                var choose = document.createElement("button");
                choose.type = "button";
                choose.className = "aetos-list__button";
                choose.textContent = theme.name;
                // Current state as pressed, not as a highlight: a themes dialog
                // is the one place a colour cue is least trustworthy.
                choose.setAttribute("aria-pressed", theme.id === active ? "true" : "false");
                choose.addEventListener("click", function () {
                    themes.apply(theme.id);
                    openThemes();
                });
                row.appendChild(choose);

                var note = document.createElement("span");
                note.className = "aetos-privacy__count";
                note.textContent = theme.builtin ? "built in" : "yours";
                row.appendChild(note);

                if (!theme.builtin) {
                    var drop = document.createElement("button");
                    drop.type = "button";
                    drop.className = "aetos-list__button";
                    drop.textContent = "Delete";
                    drop.setAttribute("aria-label", "Delete theme: " + theme.name);
                    drop.addEventListener("click", function () {
                        themes.remove(theme.id).then(function () {
                            announce("Theme deleted.");
                            openThemes();
                        });
                    });
                    row.appendChild(drop);
                }

                list.appendChild(row);
            });
            body.appendChild(list);

            dialog.open({
                title: "Themes",
                content: body,
                submitLabel: "Close",
                fields: [],
                extraActions: [
                    {
                        label: "New theme",
                        run: function () { editTheme(null); }
                    }
                ],
                onSubmit: function () {}
            });
            return themes.all();
        }

        /*
         * Build a theme, with its contrast report.
         *
         * A11Y-VIS-003 requires validation to be part of acceptance. It is
         * enforced as a **warning**, not a refusal: a player who wants a theme
         * Aetos considers unwise is entitled to have it, and overruling
         * somebody about their own eyes would be the worse failure. What they
         * are not entitled to is not being told -- and neither is whoever they
         * later send the exported file to.
         */
        function editTheme(existing) {
            var themes = services.themes;
            if (!themes || !dialog) {
                return null;
            }
            var theme = existing || { name: "", tokens: {} };
            var tokens = window.AetosThemes.TOKENS;
            var labels = window.AetosThemes.LABELS;
            var current = themes.effectiveTokens(theme);

            var fields = [{ name: "name", label: "Theme name", value: theme.name || "" }];
            tokens.forEach(function (token) {
                fields.push({
                    name: token,
                    // The label, not the variable name. An editor that reads
                    // "--aetos-text-muted" is an editor for whoever wrote it.
                    label: labels[token] + " (hex, e.g. #1b1f26)",
                    value: (theme.tokens && theme.tokens[token]) || current[token] || ""
                });
            });

            dialog.open({
                title: existing ? "Edit theme" : "New theme",
                description:
                    "Colours only, as hex values. Aetos checks eleven pairs against " +
                    "WCAG AA and tells you which fail -- it will still save a theme " +
                    "that does not pass, because that is your decision to make.",
                fields: fields,
                onSubmit: function (values) {
                    var built = { id: theme.id, name: values.name, tokens: {} };
                    tokens.forEach(function (token) {
                        if (values[token]) {
                            built.tokens[token] = values[token];
                        }
                    });
                    themes.save(built).then(function (result) {
                        var failures = result.contrast.failures;
                        if (!failures.length) {
                            announce(
                                "Theme saved. All " + result.contrast.checked +
                                " contrast checks passed.",
                                { category: "system", priority: "important" }
                            );
                            return;
                        }
                        announce(
                            "Theme saved with " + failures.length +
                            (failures.length === 1 ? " contrast problem." : " contrast problems."),
                            { category: "system", priority: "important" }
                        );
                        showContrastReport(result.theme, result.contrast);
                    }).catch(function (err) {
                        announce(err.message);
                    });
                }
            });
            return true;
        }

        /*
         * Say exactly which pairs fail and why.
         *
         * A ratio on its own tells somebody they are wrong without telling them
         * what to change. Naming the pair and what it is *for* is the
         * difference between a warning that gets fixed and one that gets
         * dismissed.
         */
        function showContrastReport(theme, report) {
            if (!dialog || !window.AetosContrast) {
                return null;
            }
            var body = document.createElement("div");

            var summary = document.createElement("p");
            summary.className = "aetos-dialog__description";
            summary.textContent = theme.name + ": " + report.failures.length + " of " +
                report.checked + " contrast checks failed. The theme has been saved.";
            body.appendChild(summary);

            var list = document.createElement("ul");
            list.className = "aetos-privacy__list";
            list.setAttribute("tabindex", "0");
            list.setAttribute("aria-label", "Contrast problems");
            window.AetosContrast.describe(report.failures).forEach(function (line) {
                var row = document.createElement("li");
                row.className = "aetos-privacy__row";
                row.textContent = line;
                list.appendChild(row);
            });
            body.appendChild(list);

            var advice = document.createElement("p");
            advice.className = "aetos-dialog__description";
            advice.textContent =
                "A pair below its threshold is hard or impossible to read for some " +
                "people. If you export this theme and share it, they will get these " +
                "colours too.";
            body.appendChild(advice);

            dialog.open({
                title: "Contrast check",
                content: body,
                submitLabel: "Keep it anyway",
                fields: [],
                extraActions: [
                    {
                        label: "Edit the theme",
                        run: function () { editTheme(theme); }
                    }
                ],
                onSubmit: function () {}
            });
            return report;
        }

        /* --- Symbol packs (A7) ------------------------------------------- */

        /*
         * Install and inspect AAC symbol packs.
         *
         * The panel leads with coverage rather than with the pack's name,
         * because "which words have no picture" is the question that decides
         * whether a pack is usable -- and it is the one a player would
         * otherwise answer by running into a blank key mid-sentence.
         */
        function openSymbolPacks() {
            var symbols = services.symbols;
            if (!symbols || !dialog) {
                return null;
            }

            var body = document.createElement("div");

            var explanation = document.createElement("p");
            explanation.className = "aetos-dialog__description";
            explanation.textContent =
                "Aetos ships no symbol artwork, so every key shows its word until " +
                "you install a pack. Which set suits you depends on your game's " +
                "licensing and on which symbols you already know, so that choice " +
                "is yours rather than ours.";
            body.appendChild(explanation);

            var installed = symbols.allPacks();
            var active = symbols.activePack();

            if (!installed.length) {
                var none = document.createElement("p");
                none.className = "aetos-dialog__description";
                none.textContent = "No packs installed.";
                body.appendChild(none);
            }

            var list = document.createElement("ul");
            list.className = "aetos-privacy__list";
            list.setAttribute("tabindex", "0");
            list.setAttribute("aria-label", "Installed symbol packs");

            installed.forEach(function (pack) {
                var row = document.createElement("li");
                row.className = "aetos-privacy__row";

                var choose = document.createElement("button");
                choose.type = "button";
                choose.className = "aetos-list__button";
                choose.textContent = pack.name;
                choose.setAttribute(
                    "aria-pressed",
                    active && active.id === pack.id ? "true" : "false"
                );
                choose.addEventListener("click", function () {
                    symbols.usePack(active && active.id === pack.id ? null : pack.id);
                    openSymbolPacks();
                });
                row.appendChild(choose);

                var terms = document.createElement("span");
                terms.className = "aetos-privacy__count";
                terms.textContent = pack.count + " symbols, " + pack.license;
                row.appendChild(terms);

                list.appendChild(row);
            });
            body.appendChild(list);

            if (active) {
                var missing = symbols.missingConcepts();

                var coverage = document.createElement("p");
                coverage.className = "aetos-dialog__description";
                coverage.textContent = missing.length
                    ? missing.length + " words have no picture in this pack and will " +
                      "show as text: " + missing.join(", ") + "."
                    : "Every word in the board has a picture in this pack.";
                body.appendChild(coverage);

                /*
                 * Said plainly rather than left for somebody to notice: a pack
                 * of remote URLs tells its host, every time the board renders,
                 * that this browser is showing a communication board.
                 */
                var privacy = document.createElement("p");
                privacy.className = "aetos-dialog__description";
                privacy.textContent = symbols.packSelfContained()
                    ? "This pack is self-contained. Showing the board sends no " +
                      "requests to anybody."
                    : "This pack loads its pictures from a website, which tells " +
                      "that site whenever you use the board. A self-contained pack " +
                      "does not.";
                body.appendChild(privacy);

                if (active.attribution) {
                    var credit = document.createElement("p");
                    credit.className = "aetos-dialog__description";
                    credit.textContent = active.attribution;
                    body.appendChild(credit);
                }
            }

            dialog.open({
                title: "Symbol packs",
                content: body,
                submitLabel: "Close",
                fields: [],
                extraActions: [
                    { label: "Install a pack file", run: function () { importSymbolPack(); } }
                ],
                onSubmit: function () {}
            });
            return installed;
        }

        /*
         * Read a pack file the player chose.
         *
         * Same shape as the M5 profile importer: a local file, never a
         * download. Reports what it refused as well as what it took.
         */
        function importSymbolPack() {
            var symbols = services.symbols;
            if (!symbols) {
                return null;
            }
            var picker = document.createElement("input");
            picker.type = "file";
            picker.accept = "application/json,.json";
            picker.addEventListener("change", function () {
                var file = picker.files && picker.files[0];
                if (!file) {
                    return;
                }
                var reader = new window.FileReader();
                reader.onload = function () {
                    var result = symbols.importPack(String(reader.result));
                    if (!result.ok) {
                        announce(result.error, {
                            category: "system", priority: "important"
                        });
                        return;
                    }
                    symbols.usePack(result.id);
                    var message = "Installed " + result.name + ": " +
                        result.accepted + " symbols.";
                    if (result.refused) {
                        message += " " + result.refused + " refused.";
                    }
                    var missing = symbols.missingConcepts().length;
                    if (missing) {
                        message += " " + missing + " words have no picture and will " +
                            "show as text.";
                    }
                    announce(message, { category: "system", priority: "important" });
                    openSymbolPacks();
                };
                reader.readAsText(file);
            });
            picker.click();
            return true;
        }

        return {
            editAlias: editAlias,
            editTrigger: editTrigger,
            editTimer: editTimer,
            editScript: editScript,
            validateAll: validateAll,
            openDiagnostics: openDiagnostics,
            openGroups: openGroups,
            editGroup: editGroup,
            editDisplayRule: editDisplayRule,
            openPrivacy: openPrivacy,
            openReminders: openReminders,
            openSymbolPacks: openSymbolPacks,
            importSymbolPack: importSymbolPack,
            openThemes: openThemes,
            editTheme: editTheme,
            showContrastReport: showContrastReport,
            editReminder: editReminder,
            openOrientation: openOrientation,
            exportProfile: exportProfile,
            importProfile: importProfile
        };
    }

    window.AetosSettings = { create: createSettings };

})(window, document);
