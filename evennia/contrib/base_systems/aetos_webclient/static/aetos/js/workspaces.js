/*
 * Aetos workspaces and Edit Layout mode.
 *
 * A workspace is a named layout the player owns: General, Combat, Roleplay,
 * whatever they choose. Workspaces live in the player's browser and are never
 * sent to the game server (blueprint sections 2.3, 18).
 *
 * EDIT LAYOUT IS KEYBOARD-FIRST.
 *
 * Blueprint revision 2 requires a keyboard equivalent for every drag operation
 * (section 16) and no widget is finished until it is usable without a mouse
 * (section 72). Rather than build dragging and add shortcuts afterwards, this
 * module exposes discrete commands -- select, move, resize, hide -- and drives
 * them from both the keyboard and the on-screen controls. The two paths share
 * one implementation, so they cannot diverge.
 *
 * Every action is announced through the shared announcer, because a player who
 * cannot see the panel move has no other way to know it did.
 */

(function (window, document) {
    "use strict";

    var DEFAULT_WORKSPACE = "General";

    function createWorkspaceManager(services) {
        var layout = services.layout;
        var registry = services.registry;
        var storage = services.storage;
        var store = services.store;
        var announce = services.announce || function () {};

        var editing = false;
        var selectedId = null;
        var currentWorkspace = DEFAULT_WORKSPACE;

        /* --- Workspace persistence ------------------------------------- */

        function saveWorkspace(name) {
            var target = name || currentWorkspace;
            if (!storage) {
                return window.Promise.resolve(false);
            }
            return storage.put("workspaces", target, {
                name: target,
                layout: layout.serialize()
            }).then(function () {
                announce("Workspace " + target + " saved.");
                return true;
            });
        }

        function listWorkspaces() {
            if (!storage) {
                return window.Promise.resolve([]);
            }
            return storage.all("workspaces").then(function (rows) {
                return rows.map(function (row) { return row.value; });
            });
        }

        /*
         * Switch to a workspace.
         *
         * A stored workspace is local data that may predate a change in the
         * game's manifest or in Aetos, so the layout manager re-checks every
         * entry on restore rather than trusting it. Widgets that no longer exist
         * or are no longer supported are skipped and counted.
         */
        function switchTo(name) {
            if (!storage) {
                return window.Promise.resolve(false);
            }
            return storage.get("workspaces", name).then(function (record) {
                if (!record || !record.layout) {
                    announce("Workspace " + name + " not found.");
                    return false;
                }
                layout.instances().forEach(function (instance) {
                    layout.remove(instance.id);
                });
                var result = layout.restore(record.layout);
                currentWorkspace = name;
                selectedId = null;
                announce(
                    "Workspace " + name + ". " + result.restored + " widgets restored" +
                    (result.skipped ? ", " + result.skipped + " unavailable." : "."));
                return true;
            });
        }

        function deleteWorkspace(name) {
            if (!storage || name === currentWorkspace) {
                return window.Promise.resolve(false);
            }
            return storage.remove("workspaces", name).then(function () {
                announce("Workspace " + name + " deleted.");
                return true;
            });
        }

        /* --- Selection -------------------------------------------------- */

        function widgetIds() {
            return layout.instances().map(function (instance) { return instance.id; });
        }

        function select(widgetId) {
            var ids = widgetIds();
            if (ids.indexOf(widgetId) === -1) {
                return false;
            }
            selectedId = widgetId;
            markSelection();
            layout.focusWidget(widgetId);
            var definition = registry.get(widgetId);
            announce((definition ? definition.displayName : widgetId) + " selected.");
            return true;
        }

        // Cycle selection, which is how a keyboard user reaches every panel.
        function selectNext(step) {
            var ids = widgetIds();
            if (!ids.length) {
                return false;
            }
            var index = ids.indexOf(selectedId);
            var next = index === -1 ? 0 : (index + step + ids.length) % ids.length;
            return select(ids[next]);
        }

        function markSelection() {
            layout.instances().forEach(function (instance) {
                var panel = document.querySelector('[data-aetos-widget="' + instance.id + '"]');
                if (!panel) {
                    return;
                }
                var isSelected = instance.id === selectedId;
                panel.classList.toggle("aetos-widget--selected", isSelected);
                // Selection is exposed to assistive technology, not just styled.
                panel.setAttribute("aria-current", isSelected ? "true" : "false");
            });
        }

        /* --- Edit mode --------------------------------------------------- */

        function setEditing(value) {
            editing = !!value;
            var root = document.getElementById("aetos-root");
            if (root) {
                root.classList.toggle("aetos-editing", editing);
                root.setAttribute("data-aetos-editing", editing ? "true" : "false");
            }
            var palette = document.getElementById("aetos-palette");
            if (palette) {
                palette.hidden = !editing;
            }
            if (editing) {
                renderPalette();
                announce(
                    "Edit layout mode on. Bracket keys select a widget, arrow keys " +
                    "move it, plus and minus resize, H hides, R resets. The Widgets " +
                    "palette lists everything available. Escape finishes.");
                if (!selectedId) {
                    selectNext(1);
                }
            } else {
                selectedId = null;
                markSelection();
                announce("Edit layout mode off.");
                saveWorkspace();
            }
            return editing;
        }

        function toggleEditing() {
            return setEditing(!editing);
        }

        /* --- Layout operations (shared by keyboard and pointer) ---------- */

        function move(direction) {
            if (!selectedId) {
                return false;
            }
            var moved = layout.moveWidget(selectedId, direction);
            var definition = registry.get(selectedId);
            var label = definition ? definition.displayName : selectedId;
            announce(moved
                ? label + " moved " + direction + "."
                : label + " cannot move " + direction + " any further.");
            return moved;
        }

        function resize(delta) {
            if (!selectedId) {
                return false;
            }
            var resized = layout.resizeWidget(selectedId, delta);
            var definition = registry.get(selectedId);
            announce((definition ? definition.displayName : selectedId) +
                (delta > 0 ? " larger." : " smaller."));
            return resized;
        }

        function hideSelected() {
            if (!selectedId) {
                return false;
            }
            var definition = registry.get(selectedId);
            layout.setVisible(selectedId, false);
            renderPalette();
            announce((definition ? definition.displayName : selectedId) +
                " hidden. Restore it from the Widgets palette below.");
            return true;
        }

        /* --- Widget palette ---------------------------------------------
         *
         * Hiding a widget must be reversible. Without a palette the only route
         * back would be a full layout reset, which discards everything else the
         * player arranged -- so the palette is part of the hide operation, not
         * a nicety.
         *
         * It lists every widget this game supports and marks which are shown.
         * Widgets the game cannot support are listed separately with the reason,
         * rather than silently absent, so a developer can see why a widget they
         * expected is missing.
         */
        function renderPalette() {
            var container = document.getElementById("aetos-palette-list");
            if (!container) {
                return;
            }
            container.textContent = "";

            var manifest = store ? store.get("manifest") : {};
            var mounted = {};
            layout.instances().forEach(function (instance) {
                mounted[instance.id] = instance;
            });

            registry.available(manifest).forEach(function (definition) {
                var instance = mounted[definition.id];
                var shown = !!instance && instance.visible !== false;
                var item = document.createElement("li");
                var button = document.createElement("button");
                button.type = "button";
                button.className = "aetos-list__button";
                button.textContent = definition.displayName;
                // State is carried by aria-pressed and by a text marker, never
                // by colour alone.
                button.setAttribute("aria-pressed", shown ? "true" : "false");
                button.title = (shown ? "Hide " : "Show ") + definition.displayName;
                button.addEventListener("click", function () {
                    if (shown) {
                        layout.setVisible(definition.id, false);
                        announce(definition.displayName + " hidden.");
                    } else if (instance) {
                        layout.setVisible(definition.id, true);
                        announce(definition.displayName + " shown.");
                    } else {
                        addWidget(definition.id);
                    }
                    renderPalette();
                });
                item.appendChild(button);
                container.appendChild(item);
            });

            registry.unavailable(manifest).forEach(function (definition) {
                var item = document.createElement("li");
                var note = document.createElement("span");
                note.className = "aetos-palette__unavailable";
                note.textContent = definition.displayName + " (needs: " +
                    definition.requiredCapabilities.join(", ") + ")";
                item.appendChild(note);
                container.appendChild(item);
            });
        }

        function addWidget(widgetId) {
            var instance = layout.add(widgetId);
            var definition = registry.get(widgetId);
            var label = definition ? definition.displayName : widgetId;
            if (!instance) {
                // Almost always because the game does not expose the capability
                // the widget needs -- worth saying, rather than failing silently.
                announce(label + " is not available for this game.");
                return false;
            }
            layout.setVisible(widgetId, true);
            announce(label + " added.");
            return true;
        }

        function resetLayout() {
            layout.instances().forEach(function (instance) {
                layout.remove(instance.id);
            });
            registry.available(store ? store.get("manifest") : {}).forEach(function (definition) {
                layout.add(definition.id);
            });
            selectedId = null;
            renderPalette();
            announce("Layout reset to defaults.");
            return true;
        }

        /*
         * The simplified workspace.  Addendum A.51.
         *
         * Six panels: the game, who is here, the map, your character, the
         * communication board, and help.
         *
         * **This is not an inferior client.** A.51 is explicit about that, and
         * it matters: it is the same capabilities with fewer things on screen
         * at once. Every feature is still reachable from the palette, nothing
         * is disabled, and switching back restores exactly what was there.
         *
         * A client that offered a "simple mode" which quietly removed
         * functionality would be making a decision about what somebody is
         * capable of, on the basis of them having asked for a calmer screen.
         * Those are not the same request, and conflating them is the specific
         * condescension this requirement exists to prevent.
         *
         * Distinct from Focus Mode (A.47), which hides everything but the game
         * text. Focus Mode is a temporary quieting; this is a layout somebody
         * might use permanently.
         */
        /*
         * A.51 names six: Game, People, Map, My Character, Talk, Help.
         *
         * Two of them are not panels and never were. The console *is* the game
         * and lives in `main` regardless of layout -- a player must never be
         * able to end up with no output. Help is an overlay on F1 with a button
         * that stays in one place whatever the workspace (A.50), which is the
         * stronger guarantee: somebody who is lost should not have to find help
         * somewhere new.
         *
         * So the four that are panels are listed, and the other two are
         * present by construction rather than by being added here.
         */
        var SIMPLIFIED_WIDGETS = ["people", "map", "state", "aac"];

        function applySimplifiedLayout() {
            layout.instances().forEach(function (instance) {
                layout.remove(instance.id);
            });

            var manifest = store ? store.get("manifest") : {};
            var offered = registry.available(manifest).map(function (definition) {
                return definition.id;
            });

            /*
             * Only what this game actually has.
             *
             * A simplified layout that added a map panel to a game with no map
             * would be six panels of which one is permanently empty -- which is
             * worse than five, and precisely the confusion the layout is meant
             * to remove.
             */
            var placed = SIMPLIFIED_WIDGETS.filter(function (id) {
                return offered.indexOf(id) !== -1;
            });
            placed.forEach(function (id) { layout.add(id); });

            selectedId = null;
            renderPalette();
            announce(
                "Simplified layout: " + placed.length +
                (placed.length === 1 ? " panel." : " panels.") +
                " Everything else is still in the command palette.",
                { category: "system", priority: "important" }
            );
            return placed;
        }

        /* --- Keyboard bindings ------------------------------------------- */

        /*
         * Bindings are only active in edit mode, so ordinary play is never
         * intercepted -- a player typing "n" to go north must not move a panel.
         * Nothing here fires while focus is in the command input.
         */
        function handleKey(event) {
            var target = event.target;
            var inInput = target && (target.tagName === "TEXTAREA" || target.tagName === "INPUT");

            // Ctrl+Shift+L is also registered with AetosShortcutManager so it
            // can be rebound (A.23). This local handler stays as a fallback:
            // edit mode must not become unreachable because one module failed
            // to load. The manager calls toggleEditing() directly, so a rebound
            // key and this default both end up in the same place.
            if (event.ctrlKey && event.shiftKey && event.key.toLowerCase() === "l") {
                event.preventDefault();
                toggleEditing();
                return;
            }
            if (!editing || inInput) {
                return;
            }

            var handled = true;
            switch (event.key) {
            case "Escape":      setEditing(false); break;
            case "]":           selectNext(1); break;
            case "[":           selectNext(-1); break;
            case "ArrowUp":     move("up"); break;
            case "ArrowDown":   move("down"); break;
            case "ArrowLeft":   move("sidebar"); break;
            case "ArrowRight":  move("aside"); break;
            case "+":
            case "=":           resize(1); break;
            case "-":
            case "_":           resize(-1); break;
            case "h":
            case "H":           hideSelected(); break;
            case "r":
            case "R":           resetLayout(); break;
            default:            handled = false;
            }
            if (handled) {
                event.preventDefault();
            }
        }

        function bindKeys(element) {
            (element || document).addEventListener("keydown", handleKey);
        }

        return {
            DEFAULT_WORKSPACE: DEFAULT_WORKSPACE,
            isEditing: function () { return editing; },
            selectedWidget: function () { return selectedId; },
            currentWorkspace: function () { return currentWorkspace; },
            setEditing: setEditing,
            toggleEditing: toggleEditing,
            select: select,
            selectNext: selectNext,
            move: move,
            resize: resize,
            hideSelected: hideSelected,
            addWidget: addWidget,
            resetLayout: resetLayout,
            applySimplifiedLayout: applySimplifiedLayout,
            SIMPLIFIED_WIDGETS: SIMPLIFIED_WIDGETS.slice(),
            saveWorkspace: saveWorkspace,
            listWorkspaces: listWorkspaces,
            switchTo: switchTo,
            deleteWorkspace: deleteWorkspace,
            bindKeys: bindKeys,
            handleKey: handleKey,
            renderPalette: renderPalette
        };
    }

    window.AetosWorkspaces = { create: createWorkspaceManager };

})(window, document);
