/*
 * Aetos developer inspector.  Addendum C.18.  Milestone M21.
 *
 * One place a game developer can see what Aetos actually believes: the
 * protocol, the manifest, which providers answered, which widgets loaded, the
 * current state, recent event types, errors and validation findings -- plus the
 * three actions that already existed and nobody could find (diagnostic report,
 * capture, replay).
 *
 * MOSTLY ASSEMBLY, AND THAT IS THE POINT.
 *
 * Almost nothing here is new capability. E1 built capture and replay, E4 the
 * validator, E5 the diagnostic report. What was missing was a place to reach
 * them from, and a developer debugging "why is my health bar empty" was
 * expected to know that `Aetos.diagnostics.build()` exists.
 *
 * A feature nobody can find is a feature that does not exist. That is the same
 * rule the palette was built on (M15) and the same one the shortcut manager
 * enforces (A.23); this milestone applies it to the developer surface.
 *
 * THE HARD RULE: NOT AN OBJECT BROWSER (C.18).
 *
 * "It MUST NOT become a general-purpose arbitrary server-object browser."
 *
 * So the inspector shows what **the client already has** -- its own store, its
 * own registry, its own log. It has no way to ask the server for anything, no
 * query field, no dbref lookup, and no path that turns a developer's curiosity
 * into a request the game did not expect.
 *
 * The reason is not squeamishness about power. An inspector that could fetch
 * arbitrary objects would be a privilege-escalation surface shipped to every
 * player, in a client whose whole security posture is that it asks for nothing
 * the game did not offer. Every widget, every provider and every action in
 * Aetos is reachable only because the game chose to expose it, and an inspector
 * that broke that would undo the guarantee rather than observe it.
 *
 * WHAT IT SHOWS IS THE PLAYER'S OWN CLIENT STATE.
 *
 * The store holds game state the player can already see on screen -- their
 * room, their resources, their inventory. Their *private* data (notes, macros,
 * relationship tags, accessibility preferences) lives in IndexedDB and is not
 * in the store, so it cannot appear here. That is the same "excluded by
 * construction" property the diagnostic report has (E5), and for the same
 * reason: there is no path, so there is nothing to filter.
 */

(function (window, document) {
    "use strict";

    /*
     * Sections, in the order a developer actually needs them.
     *
     * Connection and manifest first because nine problems in ten are "the game
     * did not declare the feature" or "the handshake did not happen", and both
     * are answered in the first two rows. Errors and validation last because
     * they are usually empty, and a panel that leads with an empty section
     * reads as broken.
     */
    var SECTIONS = [
        "connection",
        "manifest",
        "providers",
        "bindings",
        "widgets",
        "state",
        "events",
        "errors",
        "validation"
    ];

    function createInspector(services) {
        var settings = services || {};
        var store = settings.store || null;
        var dialog = settings.dialog || null;
        var announce = settings.announce || function () {};

        function manifest() {
            return (store && store.get("manifest")) || {};
        }

        /* --- Sections ----------------------------------------------------- */

        function connectionSection() {
            var connection = (store && store.get("connection")) || {};
            return [
                ["State", connection.state || "unknown"],
                ["Protocol", String(manifest().protocol || "not received")],
                [
                    "Handshake",
                    manifest().protocol
                        ? "complete"
                        : "no manifest -- the game may not have Aetos installed"
                ]
            ];
        }

        function manifestSection() {
            var payload = manifest();
            var features = payload.features || {};
            var automation = payload.automation || {};

            var enabled = Object.keys(features).filter(function (key) {
                return features[key];
            });
            var forbidden = Object.keys(automation).filter(function (key) {
                return !automation[key];
            });

            return [
                [
                    "Features on",
                    enabled.length
                        ? enabled.join(", ")
                        : "none -- the client shows only what needs no configuration"
                ],
                [
                    "Features off",
                    Object.keys(features).filter(function (key) {
                        return !features[key];
                    }).join(", ") || "none"
                ],
                ["Automation forbidden", forbidden.join(", ") || "none"]
            ];
        }

        /*
         * Providers, only where the game opted in.
         *
         * `AETOS_DIAGNOSTICS` gates this, the same setting the diagnostic
         * report uses (C.17). A provider class name is the game's own internal
         * detail, so the game decides whether the client may see it -- and a
         * developer debugging their own game can turn it on in one line.
         */
        function providersSection() {
            var diagnostics = manifest().diagnostics;
            if (!diagnostics) {
                return [[
                    "Not reported",
                    "Set AETOS_DIAGNOSTICS = True in your game to see which " +
                    "provider class answered for each slot."
                ]];
            }
            if (diagnostics.error) {
                // A provider that cannot describe itself is precisely what an
                // inspector exists to surface.
                return [["Error", String(diagnostics.error)]];
            }
            var providers = diagnostics.providers || {};
            return Object.keys(providers).sort().map(function (slot) {
                return [slot, String(providers[slot].class || "unknown")];
            });
        }

        /*
         * Bindings are the D-track, and it is not built.
         *
         * Said plainly rather than shown as an empty section. An empty section
         * reads as "your game has no bindings"; this reads as "Aetos cannot do
         * that yet", and those send a developer to completely different places.
         */
        function bindingsSection() {
            return [[
                "Not implemented",
                "AETOS_BINDINGS is planned for the D-track. Today a game " +
                "supplies providers, which are listed above."
            ]];
        }

        function widgetsSection() {
            var registry = settings.registry;
            if (!registry) {
                return [["Registry", "not available"]];
            }
            var all = registry.all();
            var available = registry.available(manifest());
            var withheld = all.filter(function (definition) {
                return !available.some(function (offered) {
                    return offered.id === definition.id;
                });
            });

            /*
             * A switched-off widget is the first thing a developer wants to
             * see and the easiest to miss -- its panel says so, but only if
             * you happen to be looking at that panel.
             */
            var layout = settings.layout;
            var broken = layout && layout.disabledWidgets ? layout.disabledWidgets() : [];

            return [
                ["Loaded", String(all.length)],
                [
                    "Switched off after failing",
                    broken.length
                        ? broken.map(function (entry) {
                            return entry.id + " (" + entry.phase + ": " + entry.message + ")";
                        }).join("; ")
                        : "none"
                ],
                ["Offered", available.map(function (d) { return d.id; }).join(", ") || "none"],
                [
                    // The useful line: a widget that never appeared did not
                    // fail, it was withheld because the game does not expose
                    // what it needs. Those look identical from outside.
                    "Withheld",
                    withheld.length
                        ? withheld.map(function (d) {
                            return d.id + " (needs " +
                                (d.requiredCapabilities || []).join(", ") + ")";
                        }).join("; ")
                        : "none"
                ]
            ];
        }

        /*
         * A summary of the store, by shape rather than by dump.
         *
         * Counts and presence, because "resources: 3 items" answers the
         * question a developer actually has, and forty lines of JSON does not.
         * The full payload is one button away for when it does.
         */
        function stateSection() {
            if (!store) {
                return [["Store", "not available"]];
            }
            // `sections` is the array itself, not an accessor.
            return store.sections.map(function (name) {
                var section = store.get(name) || {};
                var detail;
                if (Array.isArray(section.items)) {
                    detail = section.items.length + " item" +
                        (section.items.length === 1 ? "" : "s");
                } else if (section.slots) {
                    detail = Object.keys(section.slots).length + " slots";
                } else {
                    var keys = Object.keys(section);
                    detail = keys.length ? keys.join(", ") : "empty";
                }
                return [name, detail];
            });
        }

        function eventsSection() {
            var log = settings.canonicalLog;
            if (!log) {
                return [["Log", "not available"]];
            }
            var counts = {};
            log.all().forEach(function (event) {
                counts[event.category] = (counts[event.category] || 0) + 1;
            });
            var rows = Object.keys(counts).sort().map(function (category) {
                return [category, String(counts[category])];
            });
            if (!rows.length) {
                rows.push(["No events yet", ""]);
            }
            rows.push(["Total kept", String(log.size()) + " of " + String(log.limit())]);
            if (log.droppedCount()) {
                // Worth surfacing: a developer wondering why an old event is
                // missing from a report has usually hit the cap rather than a
                // bug, and nothing else says so.
                rows.push(["Dropped (over the cap)", String(log.droppedCount())]);
            }
            return rows;
        }

        function errorsSection() {
            var diagnostics = settings.diagnostics;
            if (!diagnostics) {
                return [["Diagnostics", "not available"]];
            }
            var count = diagnostics.errorCount();
            if (!count) {
                return [["No errors recorded", ""]];
            }
            // The messages themselves live in the diagnostic report, which is
            // one button away. Repeating them here would make the panel a wall
            // of stack traces on exactly the games that most need reading.
            return [[
                String(count) + " recorded",
                "Open the diagnostic report to read them."
            ]];
        }

        function validationSection() {
            return [[
                "Not run",
                "Run \"Validate automation\" to check triggers, aliases, timers, " +
                "scripts and display rules."
            ]];
        }

        var BUILDERS = {
            connection: connectionSection,
            manifest: manifestSection,
            providers: providersSection,
            bindings: bindingsSection,
            widgets: widgetsSection,
            state: stateSection,
            events: eventsSection,
            errors: errorsSection,
            validation: validationSection
        };

        var TITLES = {
            connection: "Connection",
            manifest: "Manifest and capabilities",
            providers: "Providers",
            bindings: "Bindings",
            widgets: "Widgets",
            state: "State summary",
            events: "Recent event types",
            errors: "Errors",
            validation: "Validation"
        };

        /*
         * Build the whole report as data.
         *
         * Separated from rendering so it can be tested, read from the console,
         * and -- the reason that matters -- so the panel cannot show something
         * the data does not contain.
         */
        function inspect() {
            return SECTIONS.map(function (name) {
                var rows;
                try {
                    rows = BUILDERS[name]();
                } catch (err) {
                    // One broken section costs that section. An inspector that
                    // fails entirely because the map is malformed is useless at
                    // precisely the moment somebody is inspecting a malformed
                    // map.
                    rows = [["Could not read", String(err && err.message || err)]];
                }
                return { id: name, title: TITLES[name], rows: rows };
            });
        }

        function toText() {
            return inspect().map(function (section) {
                return section.title + "\n" + section.rows.map(function (row) {
                    return "  " + row[0] + (row[1] ? ": " + row[1] : "");
                }).join("\n");
            }).join("\n\n");
        }

        /* --- The panel ---------------------------------------------------- */

        function open() {
            if (!dialog) {
                return null;
            }
            var report = inspect();
            var body = document.createElement("div");

            var explanation = document.createElement("p");
            explanation.className = "aetos-dialog__description";
            explanation.textContent =
                "What this client currently believes. It reads only what Aetos " +
                "already has -- it cannot ask your game for anything.";
            body.appendChild(explanation);

            report.forEach(function (section) {
                var heading = document.createElement("h3");
                heading.className = "aetos-dialog__subheading";
                heading.textContent = section.title;
                body.appendChild(heading);

                var list = document.createElement("ul");
                list.className = "aetos-privacy__list";
                /*
                 * Focusable and labelled, because any of these can grow tall
                 * enough to scroll and a scrolling region outside the tab order
                 * cannot be scrolled by keyboard at all.
                 *
                 * Fourth instance of this defect in the client, and the fourth
                 * caught by axe rather than by reading the code -- it is
                 * invisible to anyone testing with a mouse wheel. Labelled with
                 * the section name so tabbing through nine of them says which
                 * is which.
                 *
                 * No `role` on the <ul>: that would replace its list semantics
                 * and orphan every row (A7 made exactly that mistake).
                 */
                list.setAttribute("tabindex", "0");
                list.setAttribute("aria-label", section.title);
                section.rows.forEach(function (row) {
                    var item = document.createElement("li");
                    item.className = "aetos-privacy__row";

                    var name = document.createElement("span");
                    name.textContent = row[0];
                    item.appendChild(name);

                    if (row[1]) {
                        var value = document.createElement("span");
                        value.className = "aetos-privacy__count";
                        value.textContent = row[1];
                        item.appendChild(value);
                    }
                    list.appendChild(item);
                });
                body.appendChild(list);
            });

            /*
             * The actions that already existed and nobody could find.
             *
             * Each hides itself when its subsystem is absent, rather than
             * offering a button that then explains it cannot work.
             */
            var actions = [];
            if (settings.openDiagnostics) {
                actions.push({
                    label: "Diagnostic report",
                    run: function () { settings.openDiagnostics(false); }
                });
            }
            if (settings.validateAll) {
                actions.push({
                    label: "Validate automation",
                    run: function () { settings.validateAll(); }
                });
            }
            if (settings.capture) {
                actions.push({
                    label: settings.capture.isRecording()
                        ? "Stop capturing"
                        : "Capture this session",
                    run: function () { toggleCapture(); }
                });
                if (settings.capture.records().length) {
                    actions.push({
                        label: "Download capture",
                        run: function () { downloadCapture(); }
                    });
                }
            }
            if (settings.replay) {
                actions.push({
                    label: "Replay a capture",
                    run: function () { loadReplay(); }
                });
            }

            dialog.open({
                title: "Inspector",
                content: body,
                submitLabel: "Close",
                fields: [],
                extraActions: actions,
                onSubmit: function () {}
            });
            return report;
        }

        function toggleCapture() {
            var capture = settings.capture;
            if (!capture) {
                return false;
            }
            if (capture.isRecording()) {
                capture.stop();
                announce(
                    "Capture stopped. " + capture.records().length +
                    " records. Use Download capture to save it.",
                    { category: "system", priority: "important" }
                );
                return false;
            }
            capture.start();
            announce(
                "Capturing. Game text is included, so review it before sharing.",
                { category: "system", priority: "important" }
            );
            return true;
        }

        /*
         * Save a capture to a file.
         *
         * A capture that can only be read from the console is a capture nobody
         * attaches to a bug report -- which was its entire purpose (E1).
         */
        function downloadCapture() {
            var capture = settings.capture;
            if (!capture || !capture.records().length) {
                announce("Nothing captured yet.", {
                    category: "system", priority: "important"
                });
                return false;
            }
            var blob = new window.Blob([capture.toJsonl()], {
                type: "application/x-ndjson"
            });
            var url = window.URL.createObjectURL(blob);
            var link = document.createElement("a");
            link.href = url;
            link.download = "aetos-capture.jsonl";
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);

            announce(
                "Capture saved. It contains the game text from this session, so " +
                "read it before sending it to anybody.",
                { category: "system", priority: "important" }
            );
            return true;
        }

        /*
         * Load a capture and replay it.
         *
         * From a local file the developer chose, never a download. Replay feeds
         * `pipeline.ingest` -- the same seam the websocket uses -- so what is
         * exercised is production code rather than a harness (E1).
         */
        function loadReplay() {
            var replay = settings.replay;
            if (!replay) {
                return false;
            }
            var picker = document.createElement("input");
            picker.type = "file";
            picker.accept = ".jsonl,application/x-ndjson,text/plain";
            picker.addEventListener("change", function () {
                var file = picker.files && picker.files[0];
                if (!file) {
                    return;
                }
                var reader = new window.FileReader();
                reader.onload = function () {
                    var loaded;
                    try {
                        loaded = replay.load(String(reader.result));
                    } catch (err) {
                        announce("Could not read that capture: " + err.message, {
                            category: "system", priority: "important"
                        });
                        return;
                    }
                    announce(
                        "Loaded " + replay.total() + " records. " +
                        "Replaying into this client -- your own session state " +
                        "will be replaced by the capture's.",
                        { category: "system", priority: "important" }
                    );
                    replay.play();
                    return loaded;
                };
                reader.readAsText(file);
            });
            picker.click();
            return true;
        }

        return {
            inspect: inspect,
            toText: toText,
            open: open,
            toggleCapture: toggleCapture,
            downloadCapture: downloadCapture,
            loadReplay: loadReplay,
            SECTIONS: SECTIONS.slice()
        };
    }

    window.AetosInspector = { create: createInspector, SECTIONS: SECTIONS.slice() };

})(window, document);
