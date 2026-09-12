/*
 * Aetos character widgets: inventory, equipment, target and effects.
 *
 * These describe the player rather than the room. They are ordinary widget
 * definitions using the same public contract a third-party widget uses.
 *
 * GATING (blueprint section 11). Inventory is NOT capability-gated, because
 * `contents` is a stock Evennia concept and the default provider works on a
 * pristine game. Equipment, target and effects ARE gated, because Evennia models
 * none of them -- an empty paper doll on a game with no equipment is worse than
 * no widget, since it implies a system that does not exist.
 *
 * COUNTDOWNS ARE DISPLAY, NEVER AUTHORITY (section 2.4). The client ticks an
 * effect's remaining time down for smoothness, but reaching zero means "the
 * server has not told us yet", not "this effect is over". A client that removed
 * an effect on its own clock would show a player as unpoisoned while the server
 * still had them poisoned, which is a lie at exactly the moment it matters.
 *
 * ANNOUNCEMENTS ARE FOR EVENTS, NOT TICKS. Gaining or losing an effect is
 * announced; the second-by-second countdown is not. A live region that updated
 * every second would make the client unusable with a screen reader -- so the
 * countdown text updates in place with `aria-live` off, and the player reads it
 * when they choose to.
 */

(function (window, document) {
    "use strict";

    //: How often the effect countdown redraws. One second is what a player
    //: expects from a timer; anything faster is invisible and costs battery.
    var TICK_MS = 1000;

    function panelOf(element) {
        return element.closest ? element.closest("[data-aetos-widget]") : null;
    }

    /*
     * Emptiness, expressed with `data-aetos-empty` rather than `hidden`.
     *
     * `hidden` belongs to the layout manager, which uses it for the player's own
     * show/hide choice. When both wrote the same attribute they fought and
     * whichever ran last won.
     */
    function setEmpty(element, empty) {
        var panel = panelOf(element);
        if (panel) {
            panel.setAttribute("data-aetos-empty", empty ? "true" : "false");
        }
    }

    /*
     * Format a remaining duration for reading, not for precision.
     *
     * "2m 30s" rather than "150s": a player judging whether a buff will outlast
     * a fight is comparing against minutes, and a raw second count makes them do
     * the arithmetic.
     */
    function formatRemaining(seconds) {
        if (seconds === null || seconds === undefined) {
            return "";
        }
        var whole = Math.max(0, Math.floor(seconds));
        if (whole >= 3600) {
            var hours = Math.floor(whole / 3600);
            return hours + "h " + Math.floor((whole % 3600) / 60) + "m";
        }
        if (whole >= 60) {
            return Math.floor(whole / 60) + "m " + (whole % 60) + "s";
        }
        return whole + "s";
    }

    /* ------------------------------------------------------------------
     * Inventory
     * ------------------------------------------------------------------ */

    function createInventoryWidget(services) {
        var sanitize = services.sanitize;
        var sendCommand = services.sendCommand;

        return {
            id: "inventory",
            accessibility: {
                landmarkLabel: "Your inventory",
                heading: "Inventory",
                keyboardOperable: true,
                liveUpdates: true
            },
            displayName: "Inventory",
            description: "What you are carrying.",
            builtin: true,
            defaultRegion: "aside",
            defaultSize: { height: 200 },
            // Deliberately ungated. The default provider reads `contents`, which
            // every Evennia game has, so this works with no game code at all.
            subscriptions: ["inventory"],

            mount: function (context) {
                context.element.setAttribute("data-aetos-inventory", "");
                setEmpty(context.element, true);
            },

            update: function (context, data) {
                var items = (data && data.items) || [];
                context.element.textContent = "";
                setEmpty(context.element, !items.length);
                if (!items.length) {
                    return;
                }

                var list = document.createElement("ul");
                list.className = "aetos-list";

                items.forEach(function (item) {
                    var row = document.createElement("li");
                    var button = document.createElement("button");
                    button.type = "button";
                    button.className = "aetos-list__button";

                    var name = document.createElement("span");
                    if (item.display && sanitize) {
                        name.appendChild(sanitize(item.display));
                    } else {
                        name.textContent = item.name;
                    }
                    button.appendChild(name);

                    if (item.quantity !== undefined && item.quantity !== 1) {
                        // Written as a word, not only as a superscript badge:
                        // "x3" read aloud is ambiguous, "3" after the name is
                        // not, and the visual form costs nothing either way.
                        var quantity = document.createElement("span");
                        quantity.className = "aetos-list__count";
                        quantity.textContent = " ×" + item.quantity;
                        button.appendChild(quantity);
                    }

                    // The name is the plain form precisely so it can go into a
                    // command. `look <item>` is a default-cmdset command, so
                    // this works on a pristine game; the server still decides.
                    button.addEventListener("click", function () {
                        sendCommand("look " + item.name);
                    });

                    if (services.attachMenu && (item.actions || []).length) {
                        services.attachMenu(button, item);
                    }

                    row.appendChild(button);
                    list.appendChild(row);
                });

                context.element.appendChild(list);
            }
        };
    }

    /* ------------------------------------------------------------------
     * Equipment
     * ------------------------------------------------------------------ */

    function createEquipmentWidget(services) {
        var sanitize = services.sanitize;
        var sendCommand = services.sendCommand;

        return {
            id: "equipment",
            // Empty slots are stated in words, so the panel reads correctly when
            // nothing is equipped rather than reading as blank.
            accessibility: {
                landmarkLabel: "Equipped items",
                heading: "Equipment",
                keyboardOperable: true,
                liveUpdates: true
            },
            displayName: "Equipment",
            description: "What you have equipped, by slot.",
            builtin: true,
            defaultRegion: "aside",
            defaultSize: { height: 200 },
            // Gated: Evennia has no equipment, so a game that has not said it
            // has slots never sees this offered.
            requiredCapabilities: ["equipment"],
            subscriptions: ["equipment"],

            mount: function (context) {
                context.element.setAttribute("data-aetos-equipment", "");
                setEmpty(context.element, true);
            },

            update: function (context, data) {
                var slots = (data && data.slots) || [];
                context.element.textContent = "";
                setEmpty(context.element, !slots.length);
                if (!slots.length) {
                    return;
                }

                // A description list, because that is what this is: each slot
                // names a thing and gives its current value. Assistive
                // technology can then navigate slot by slot.
                var list = document.createElement("dl");
                list.className = "aetos-equipment";

                slots.forEach(function (slot) {
                    var term = document.createElement("dt");
                    term.className = "aetos-equipment__slot";
                    if (slot.display && sanitize) {
                        term.appendChild(sanitize(slot.display));
                    } else {
                        term.textContent = slot.label;
                    }

                    var value = document.createElement("dd");
                    value.className = "aetos-equipment__item";

                    if (slot.item) {
                        var button = document.createElement("button");
                        button.type = "button";
                        button.className = "aetos-list__button";
                        if (slot.item.display && sanitize) {
                            button.appendChild(sanitize(slot.item.display));
                        } else {
                            button.textContent = slot.item.name;
                        }
                        button.addEventListener("click", function () {
                            sendCommand("look " + slot.item.name);
                        });
                        if (services.attachMenu && (slot.item.actions || []).length) {
                            services.attachMenu(button, slot.item);
                        }
                        value.appendChild(button);
                    } else {
                        // An empty slot is stated, not left blank. "Nothing on
                        // your head" is information; a blank cell is a puzzle,
                        // and reads as nothing at all to a screen reader.
                        value.textContent = "empty";
                        value.setAttribute("data-aetos-empty-slot", "true");
                    }

                    list.appendChild(term);
                    list.appendChild(value);
                });

                context.element.appendChild(list);
            }
        };
    }

    /* ------------------------------------------------------------------
     * Effects
     * ------------------------------------------------------------------ */

    /*
     * Tracks which effects are present so gains and losses can be announced.
     *
     * Diffing by id rather than by list length: an effect ending at the same
     * moment another begins leaves the count unchanged, and that is exactly the
     * moment a player most needs to be told.
     */
    function createEffectTracker() {
        var known = {};
        var primed = false;

        function update(effects) {
            var messages = [];
            var seen = {};

            effects.forEach(function (effect) {
                seen[effect.id] = effect;
                if (primed && !known[effect.id]) {
                    messages.push(effect.label + " gained.");
                } else if (primed && known[effect.id] &&
                           effect.stacks && effect.stacks !== known[effect.id].stacks) {
                    messages.push(effect.label + ", " + effect.stacks + " stacks.");
                }
            });

            Object.keys(known).forEach(function (id) {
                if (!seen[id]) {
                    messages.push(known[id].label + " ended.");
                }
            });

            known = seen;
            // The first sync is the state on arrival, not a set of events. A
            // player reconnecting mid-fight should not hear their whole
            // condition list read out as if it had all just happened.
            var result = primed ? messages : [];
            primed = true;
            return result;
        }

        function reset() {
            known = {};
            primed = false;
        }

        return { update: update, reset: reset };
    }

    function renderEffect(effect, sanitize, now) {
        var row = document.createElement("li");
        row.className = "aetos-effect aetos-effect--" + effect.kind;
        row.setAttribute("data-aetos-effect", effect.id);

        var label = document.createElement("span");
        label.className = "aetos-effect__label";
        if (effect.display && sanitize) {
            label.appendChild(sanitize(effect.display));
        } else {
            label.textContent = effect.label;
        }
        row.appendChild(label);

        // Tone is stated in words as well as carried by the class. A red border
        // tells a colour-blind player nothing and a screen reader less.
        if (effect.kind !== "neutral") {
            var tone = document.createElement("span");
            tone.className = "aetos-effect__kind";
            tone.textContent = " (" + effect.kind + ")";
            label.appendChild(tone);
        }

        if (effect.stacks) {
            var stacks = document.createElement("span");
            stacks.className = "aetos-effect__stacks";
            stacks.textContent = " ×" + effect.stacks;
            row.appendChild(stacks);
        }

        if (effect.remaining !== undefined) {
            var time = document.createElement("span");
            time.className = "aetos-effect__remaining";
            // Explicitly not a live region. This text changes every second, and
            // announcing each change would flood a screen reader with the one
            // piece of information the player can ask for whenever they want.
            time.setAttribute("aria-live", "off");
            row.appendChild(time);

            // The absolute moment this was true, so the tick does not
            // accumulate drift by repeatedly subtracting from itself.
            row.__aetosExpiry = now + effect.remaining * 1000;
            row.__aetosTimeEl = time;
        }

        if (effect.description) {
            var description = document.createElement("span");
            description.className = "aetos-effect__description";
            description.textContent = effect.description;
            row.appendChild(description);
        }

        return row;
    }

    function createEffectsWidget(services) {
        var sanitize = services.sanitize;
        var announce = services.announce || function () {};
        var now = services.now || function () { return Date.now(); };
        var tracker = createEffectTracker();

        function tick(context) {
            (context.rows || []).forEach(function (row) {
                if (!row.__aetosTimeEl) {
                    return;
                }
                var left = (row.__aetosExpiry - now()) / 1000;
                if (left > 0) {
                    row.__aetosTimeEl.textContent = " " + formatRemaining(left);
                    row.removeAttribute("data-aetos-expiring");
                } else {
                    // Zero does NOT mean gone. The server decides when an effect
                    // ends; all the client knows is that its own estimate ran
                    // out. Saying so is honest and leaves the row in place until
                    // the next sync confirms.
                    row.__aetosTimeEl.textContent = " expiring";
                    row.setAttribute("data-aetos-expiring", "true");
                }
            });
        }

        return {
            id: "effects",
            // Display only, and deliberately so: an effect is something happening
            // TO the character, not a control. Countdowns update every second
            // and are explicitly not announced.
            accessibility: {
                landmarkLabel: "Active effects",
                heading: "Effects",
                keyboardOperable: false,
                liveUpdates: true
            },
            displayName: "Effects",
            description: "Temporary conditions currently on your character.",
            builtin: true,
            defaultRegion: "aside",
            defaultSize: { height: 160 },
            requiredCapabilities: ["effects"],
            subscriptions: ["effects"],

            mount: function (context) {
                context.element.setAttribute("data-aetos-effects", "");
                context.rows = [];
                setEmpty(context.element, true);
                context.timer = window.setInterval(function () { tick(context); }, TICK_MS);
            },

            update: function (context, data) {
                var items = (data && data.items) || [];
                context.element.textContent = "";
                context.rows = [];
                setEmpty(context.element, !items.length);

                var stamp = now();
                if (items.length) {
                    var list = document.createElement("ul");
                    list.className = "aetos-effects";
                    items.forEach(function (effect) {
                        var row = renderEffect(effect, sanitize, stamp);
                        context.rows.push(row);
                        list.appendChild(row);
                    });
                    context.element.appendChild(list);
                    tick(context);
                }

                tracker.update(items).forEach(function (message) {
                    announce(message);
                });
            },

            destroy: function (context) {
                if (context && context.timer) {
                    window.clearInterval(context.timer);
                    context.timer = null;
                }
                tracker.reset();
            }
        };
    }

    /* ------------------------------------------------------------------
     * Target
     * ------------------------------------------------------------------ */

    function createTargetWidget(services) {
        var sanitize = services.sanitize;
        var sendCommand = services.sendCommand;
        var announce = services.announce || function () {};
        var renderResource = services.renderResource;
        var lastId = null;

        return {
            id: "target",
            accessibility: {
                landmarkLabel: "Current target",
                heading: "Target",
                keyboardOperable: true,
                liveUpdates: true
            },
            displayName: "Target",
            description: "The thing your game currently has you focused on.",
            builtin: true,
            defaultRegion: "aside",
            defaultSize: { height: 180 },
            requiredCapabilities: ["target"],
            subscriptions: ["target"],

            mount: function (context) {
                context.element.setAttribute("data-aetos-target", "");
                // A change of target is worth hearing without having to look.
                context.element.setAttribute("role", "region");
                context.element.setAttribute("aria-label", "Current target");
                setEmpty(context.element, true);
            },

            update: function (context, target) {
                var has = target && target.id && target.name;
                context.element.textContent = "";
                setEmpty(context.element, !has);

                if (!has) {
                    if (lastId !== null) {
                        announce("Target cleared.");
                        lastId = null;
                    }
                    return;
                }

                if (target.id !== lastId) {
                    announce("Target: " + target.name + ".");
                    lastId = target.id;
                }

                var heading = document.createElement("p");
                heading.className = "aetos-target__name";
                if (target.display && sanitize) {
                    heading.appendChild(sanitize(target.display));
                } else {
                    heading.textContent = target.name;
                }

                if (target.relationship) {
                    // The GAME's view of the relationship, not the player's own
                    // private tag from their notes. Keeping them visually and
                    // structurally distinct matters: one is authoritative and
                    // the other is a personal reminder nobody else can see.
                    var relation = document.createElement("span");
                    relation.className = "aetos-target__relationship";
                    relation.textContent = " (" + target.relationship + ")";
                    heading.appendChild(relation);
                }

                var button = document.createElement("button");
                button.type = "button";
                button.className = "aetos-list__button";
                button.appendChild(heading);
                button.addEventListener("click", function () {
                    sendCommand("look " + target.name);
                });
                if (services.attachMenu) {
                    services.attachMenu(button, target);
                }
                context.element.appendChild(button);

                // The SAME renderer as the player's own resources, so a target's
                // health bar and the player's cannot disagree about thresholds
                // or rounding. Learning to read one teaches the other.
                if (renderResource) {
                    (target.resources || []).forEach(function (resource) {
                        context.element.appendChild(renderResource(resource));
                    });
                }

                if ((target.effects || []).length) {
                    var list = document.createElement("ul");
                    list.className = "aetos-effects aetos-effects--target";
                    var stamp = services.now ? services.now() : Date.now();
                    target.effects.forEach(function (effect) {
                        list.appendChild(renderEffect(effect, sanitize, stamp));
                    });
                    context.element.appendChild(list);
                }
            },

            destroy: function () {
                lastId = null;
            }
        };
    }

    function createWidgets(services) {
        return [
            createInventoryWidget(services),
            createEquipmentWidget(services),
            createEffectsWidget(services),
            createTargetWidget(services)
        ];
    }

    window.AetosCharacter = {
        create: createWidgets,
        createEffectTracker: createEffectTracker,
        formatRemaining: formatRemaining,
        renderEffect: renderEffect
    };

})(window, document);
