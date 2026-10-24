/*
 * Aetos built-in widgets.
 *
 * These are ordinary widget definitions using the same public contract a
 * third-party widget uses (blueprint section 57). Nothing here has privileged
 * access: if a built-in widget can be written against this API, so can anyone
 * else's -- which is the only real proof that the widget SDK is usable.
 *
 * Every one of these works on a pristine Evennia game and declares no required
 * capabilities, which is what makes the zero-configuration experience
 * (section 11) possible.
 *
 * Accessibility is part of each definition, not a later pass:
 *   - every actionable entry is a real <button>, so Tab and Enter/Space work
 *     with no custom key handling
 *   - an empty widget hides itself rather than rendering an empty box
 *   - text carries the meaning; colour is decoration
 */

(function (window, document) {
    "use strict";

    /* ------------------------------------------------------------------
     * Shared helpers
     * ------------------------------------------------------------------ */

    // Renders a list of entries as keyboard-operable buttons.
    //
    // `services` carries the context-menu hooks. Every entry gets a menu of the
    // entity's own actions, reachable by right-click, the Context Menu key and
    // Shift+F10 -- the last two being the ones a keyboard user can actually
    // press (blueprint section 51).
    function renderList(element, entries, onActivate, sanitize, services) {
        element.textContent = "";
        if (!entries || !entries.length) {
            return false;
        }
        var list = document.createElement("ul");
        list.className = "aetos-list";
        entries.forEach(function (entry) {
            var item = document.createElement("li");
            var button = document.createElement("button");
            button.type = "button";
            button.className = "aetos-list__button";
            // `display` is HTML with colour markup; `name` is the plain form.
            // Only the plain form is ever used to build a command.
            if (entry.display && sanitize) {
                button.appendChild(sanitize(entry.display));
            } else {
                button.textContent = entry.name || entry.direction || "?";
            }
            if (onActivate) {
                button.addEventListener("click", function () { onActivate(entry); });
            } else {
                button.disabled = true;
            }

            if (services && services.attachMenu && (entry.actions || []).length) {
                services.attachMenu(button, entry);
            }

            item.appendChild(button);
            list.appendChild(item);
        });
        element.appendChild(list);
        return true;
    }

    /*
     * A widget with nothing to show hides its own panel (blueprint section 11).
     *
     * This uses `data-aetos-empty`, NOT the `hidden` attribute. `hidden` belongs
     * to the layout manager, which uses it for the player's own show/hide
     * choice. When both wrote the same attribute the two fought, and whichever
     * ran last won -- so an empty widget reappeared as an empty box because
     * mounting set visibility after the widget had hidden itself.
     *
     * Separating them means "the player hid this" and "this has nothing to show"
     * stay independent facts, which is what they are.
     */
    function setPanelVisible(element, visible) {
        var panel = element.closest ? element.closest("[data-aetos-widget]") : null;
        if (panel) {
            panel.setAttribute("data-aetos-empty", visible ? "false" : "true");
        }
    }

    /* ------------------------------------------------------------------
     * Definitions
     * ------------------------------------------------------------------ */

    function createBuiltins(services) {
        var sanitize = services.sanitize;
        var sendCommand = services.sendCommand;

        return [
            {
                id: "room",
                // Display only. The room description is prose, not controls -- there is
                    // nothing here to operate, so claiming keyboard operability
                    // would be a false positive in the audit.
                accessibility: {
                    landmarkLabel: "Current location",
                    heading: "Current Location",
                    keyboardOperable: false,
                    liveUpdates: true
                },
                displayName: "Current Location",
                description: "Name and description of where you are.",
                builtin: true,
                defaultRegion: "sidebar",
                defaultSize: { height: 160 },
                subscriptions: ["room"],
                mount: function (context) {
                    var name = document.createElement("p");
                    name.className = "aetos-room__name";
                    var desc = document.createElement("p");
                    desc.className = "aetos-room__description";
                    context.element.appendChild(name);
                    context.element.appendChild(desc);
                    context.nameEl = name;
                    context.descEl = desc;
                    setPanelVisible(context.element, false);
                },
                update: function (context, room) {
                    var has = room && (room.name || room.display);
                    setPanelVisible(context.element, !!has);
                    if (!has) {
                        return;
                    }
                    context.nameEl.textContent = "";
                    context.nameEl.appendChild(sanitize(room.display || room.name));
                    context.descEl.textContent = "";
                    context.descEl.appendChild(sanitize(room.description || ""));
                }
            },

            {
                id: "exits",
                // Every exit is a real <button>, so Tab and Enter work with no custom
                    // key handling.
                accessibility: {
                    landmarkLabel: "Exits from this room",
                    heading: "Exits",
                    keyboardOperable: true,
                    liveUpdates: true
                },
                displayName: "Exits",
                description: "Ways out of the current room.",
                builtin: true,
                defaultRegion: "sidebar",
                defaultSize: { height: 90 },
                subscriptions: ["room"],
                mount: function (context) {
                    setPanelVisible(context.element, false);
                },
                update: function (context, room) {
                    var exits = (room && room.exits) || [];
                    var shown = renderList(context.element, exits, function (entry) {
                        // Sends the exit name exactly as typing it would. The
                        // server decides whether the movement succeeds.
                        sendCommand(entry.direction || entry.name);
                    }, sanitize, services);
                    setPanelVisible(context.element, shown);
                }
            },

            {
                id: "people",
                accessibility: {
                    landmarkLabel: "People here",
                    heading: "People Here",
                    keyboardOperable: true,
                    liveUpdates: true
                },
                displayName: "People Here",
                description: "Characters in the room.",
                builtin: true,
                defaultRegion: "sidebar",
                defaultSize: { height: 110 },
                subscriptions: ["entities"],
                mount: function (context) {
                    setPanelVisible(context.element, false);
                },
                update: function (context, entities) {
                    var items = ((entities && entities.items) || []).filter(function (entry) {
                        return entry.kind === "character";
                    });
                    var shown = renderList(context.element, items, function (entry) {
                        sendCommand("look " + entry.name);
                    }, sanitize, services);
                    setPanelVisible(context.element, shown);
                }
            },

            {
                id: "items",
                accessibility: {
                    landmarkLabel: "Items here",
                    heading: "Items Here",
                    keyboardOperable: true,
                    liveUpdates: true
                },
                displayName: "Items Here",
                description: "Objects in the room.",
                builtin: true,
                defaultRegion: "sidebar",
                defaultSize: { height: 110 },
                subscriptions: ["entities"],
                mount: function (context) {
                    setPanelVisible(context.element, false);
                },
                update: function (context, entities) {
                    var items = ((entities && entities.items) || []).filter(function (entry) {
                        return entry.kind !== "character" && entry.kind !== "exit";
                    });
                    var shown = renderList(context.element, items, function (entry) {
                        sendCommand("look " + entry.name);
                    }, sanitize, services);
                    setPanelVisible(context.element, shown);
                }
            }
        ];
    }

    window.AetosBuiltins = { create: createBuiltins };

})(window, document);
