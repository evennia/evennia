/*
 * Aetos Current State View.  Addendum A.9, A11Y-STATE-001.
 *
 * Answers one question: **what is true right now?**
 *
 * WHY THIS EXISTS AT ALL. The transcript answers "what happened", and it
 * answers it in the worst possible order for someone who arrived late: newest
 * last, mixed with everything else, at whatever length the game felt like. A
 * player who looked away for two minutes, or whose screen reader was
 * interrupted, or who lost their place on a braille display, should not have to
 * reconstruct the present by reading the past.
 *
 * So this is a *snapshot*, assembled from the same authoritative store the
 * visual widgets read. It is not a summary of the console, and it never parses
 * rendered text to work out what is going on -- A.4 forbids that, and it would
 * be reconstructing information Aetos already has.
 *
 * IT DOES NOT ANNOUNCE (A11Y-STATE-002). This is the rule that makes it usable.
 * A snapshot that spoke every time the room changed would duplicate every
 * announcement the announcement manager already makes, and a player would hear
 * everything twice. It is somewhere you *go*, not something that talks.
 *
 * WHY IT IS ONE WIDGET AND NOT A CONCATENATION OF THE OTHERS. Because the
 * others are arranged for glancing and this is arranged for reading: heading,
 * then list, in a fixed order, every time. A screen-reader user navigating by
 * heading gets the same shape on every game, which is the whole point -- the
 * player learns the structure once.
 */

(function (window, document) {
    "use strict";

    /*
     * Section order. Fixed, and deliberately not configurable.
     *
     * Predictability is the feature (A.49). A player who learns that exits are
     * the third heading should find them there on every game and after every
     * update, so the order runs: where am I, what can I do about it, who else
     * is here, what is true of me.
     */
    var SECTIONS = [
        "location",
        "exits",
        "people",
        "objects",
        "character",
        "effects",
        "target",
        "queue"
    ];

    //: An empty section is omitted rather than rendered as "Players: none".
    //: Fifteen headings, twelve of which say "nothing", is a worse snapshot
    //: than four headings that all carry information.
    //:
    //: The exception is `exits`, below.
    function heading(level, text) {
        var element = document.createElement("h" + level);
        element.className = "aetos-state__heading";
        element.textContent = text;
        return element;
    }

    function paragraph(text, className) {
        var element = document.createElement("p");
        element.className = className || "aetos-state__line";
        element.textContent = text;
        return element;
    }

    function list(entries, className) {
        var element = document.createElement("ul");
        element.className = className || "aetos-state__list";
        entries.forEach(function (entry) {
            var item = document.createElement("li");
            item.textContent = entry;
            element.appendChild(item);
        });
        return element;
    }

    /*
     * A resource as one readable line.  A11Y-BRL-002.
     *
     * Compact by default: "Health 82/100, healthy" rather than "Health, 82 out
     * of 100, healthy". On a 40-cell braille display the difference is whether
     * two resources fit on one line or one resource takes two, and a player
     * panning back and forth across padding is a player being slowed down by
     * their own status bar.
     *
     * `state_text` is the game's own word for the value (A.77) and is worth
     * more than the numbers to anyone who has not memorised the scale.
     */
    function resourceLine(resource, compact) {
        var name = resource.label || resource.id;
        var value = resource.value;
        var text;

        if (typeof resource.maximum === "number") {
            text = compact
                ? name + " " + value + "/" + resource.maximum
                : name + ", " + value + " of " + resource.maximum;
        } else {
            text = compact ? name + " " + value : name + ", " + value;
        }
        if (resource.units) {
            text += " " + resource.units;
        }
        if (resource.state_text) {
            text += compact ? " " + resource.state_text : ", " + resource.state_text;
        }
        return text;
    }

    /*
     * "1 item" rather than "1 items".
     *
     * Trivial to get wrong and grating to read, and worse to hear: a screen
     * reader gives a mis-pluralised count the same weight as any other word,
     * so it lands as a stumble in the middle of a status line the player is
     * trying to read quickly.
     */
    function plural(count, noun) {
        return count + " " + noun + (count === 1 ? "" : "s");
    }

    /*
     * A remaining duration, rounded.  A11Y-BRL-005.
     *
     * "4.973, 4.941, 4.902" is not a countdown, it is a denial of service
     * against the accessibility tree. Whole seconds below a minute, whole
     * minutes above it -- nobody needs a buff timer to three decimal places,
     * and the precision costs a braille reader an entire line of churn every
     * frame.
     */
    function remainingText(seconds) {
        if (seconds === null || seconds === undefined) {
            return "";
        }
        var whole = Math.max(0, Math.floor(seconds));
        if (whole >= 60) {
            return Math.floor(whole / 60) + "m";
        }
        return whole + "s";
    }

    function createStateWidget(services) {
        var preferences = services.preferences || null;

        function compactStatus() {
            if (!preferences || typeof preferences.value !== "function") {
                return true;
            }
            return preferences.value("braille.compactStatus") !== false;
        }

        /*
         * Build the snapshot.
         *
         * Reads the store directly rather than being handed one section,
         * because the whole point is a view across sections that the ordinary
         * widgets deliberately keep separate.
         */
        function render(container, store) {
            container.textContent = "";
            var compact = compactStatus();
            var wrote = false;

            function section(title, build) {
                var fragment = document.createDocumentFragment();
                var produced = build(fragment);
                if (!produced) {
                    return;
                }
                container.appendChild(heading(3, title));
                container.appendChild(fragment);
                wrote = true;
            }

            var room = store.get("room") || {};
            var entities = (store.get("entities") || {}).items || [];
            var resources = (store.get("resources") || {}).items || [];
            var effects = (store.get("effects") || {}).items || [];
            var inventory = (store.get("inventory") || {}).items || [];
            var equipment = (store.get("equipment") || {}).slots || [];
            var target = store.get("target") || {};

            /* --- Where am I ------------------------------------------- */

            section("Location", function (fragment) {
                if (!room.name) {
                    return false;
                }
                fragment.appendChild(paragraph(room.name, "aetos-state__location"));
                return true;
            });

            /*
             * Exits are the one section shown even when empty.
             *
             * "No visible exits" is a fact a player urgently needs, and
             * omitting the heading makes it indistinguishable from a game that
             * does not report exits at all. The distinction between "nowhere to
             * go" and "I do not know" matters most at exactly the moment
             * someone is trying to leave.
             */
            section("Exits", function (fragment) {
                var exits = (room.exits || []).map(function (exit) {
                    var name = exit.direction || exit.name;
                    return exit.destination_name ? name + " to " + exit.destination_name : name;
                });
                if (!exits.length) {
                    fragment.appendChild(paragraph("No visible exits."));
                    return true;
                }
                fragment.appendChild(list(exits));
                return true;
            });

            /* --- Who and what is here ---------------------------------- */

            section("People here", function (fragment) {
                var people = entities.filter(function (entry) {
                    return entry.kind === "character";
                });
                if (!people.length) {
                    return false;
                }
                fragment.appendChild(list(people.map(function (entry) {
                    // The game's own view of the relationship, where it has
                    // one (A.80). The player's private tags are merged
                    // separately and are never confused with it.
                    return entry.relationship
                        ? entry.name + " (" + entry.relationship + ")"
                        : entry.name;
                })));
                return true;
            });

            section("Objects here", function (fragment) {
                var objects = entities.filter(function (entry) {
                    return entry.kind !== "character" && entry.kind !== "exit";
                });
                if (!objects.length) {
                    return false;
                }
                fragment.appendChild(list(objects.map(function (entry) {
                    return entry.name;
                })));
                return true;
            });

            /* --- What is true of me ------------------------------------ */

            section("Your character", function (fragment) {
                var lines = resources.map(function (resource) {
                    return resourceLine(resource, compact);
                });
                var equipped = equipment.filter(function (slot) { return slot.item; });
                if (equipped.length) {
                    lines.push(plural(equipped.length, "item") + " equipped");
                }
                if (inventory.length) {
                    lines.push(plural(inventory.length, "item") + " carried");
                }
                if (!lines.length) {
                    return false;
                }
                fragment.appendChild(list(lines));
                return true;
            });

            section("Effects", function (fragment) {
                if (!effects.length) {
                    return false;
                }
                fragment.appendChild(list(effects.map(function (effect) {
                    var text = effect.label;
                    if (effect.stacks) {
                        text += " x" + effect.stacks;
                    }
                    if (effect.kind && effect.kind !== "neutral") {
                        text += " (" + effect.kind + ")";
                    }
                    var left = remainingText(effect.remaining);
                    if (left) {
                        text += ", " + left;
                    }
                    return text;
                })));
                return true;
            });

            section("Target", function (fragment) {
                if (!target || !target.name) {
                    return false;
                }
                var text = target.name;
                if (target.relationship) {
                    text += " (" + target.relationship + ")";
                }
                fragment.appendChild(paragraph(text));
                if ((target.resources || []).length) {
                    fragment.appendChild(list(target.resources.map(function (resource) {
                        return resourceLine(resource, compact);
                    })));
                }
                return true;
            });

            /* --- What am I in the middle of ---------------------------- */

            /*
             * Whatever the queue is part-way through -- a route, a macro, a
             * script. "What am I in the middle of" is the question a player
             * returning after an interruption asks second, right after "where
             * am I", and the console answers it only by inference.
             */
            section("In progress", function (fragment) {
                var queue = services.queueState && services.queueState();
                if (!queue || !queue.running) {
                    return false;
                }
                var text = (queue.label || "Queued commands") + ": " +
                    queue.remaining + " of " + queue.total + " remaining";
                if (queue.paused) {
                    text += ", paused";
                }
                fragment.appendChild(paragraph(text));
                return true;
            });

            if (!wrote) {
                container.appendChild(paragraph(
                    "Nothing to report yet. This fills in once the game sends state."
                ));
            }
        }

        return {
            id: "state",
            accessibility: {
                landmarkLabel: "Current state",
                heading: "Current State",
                description: "Everything true right now, in one place.",
                // Read, not operated. Nothing here is a control: acting on
                // anything listed is done from the widget that owns it, so
                // this stays a place to find out rather than a second way to
                // do the same things slightly differently.
                keyboardOperable: false,
                // It updates as state arrives, but it does NOT announce
                // (A11Y-STATE-002) -- the announcement manager already speaks
                // for these events, and a snapshot that spoke too would say
                // everything twice.
                liveUpdates: true
            },
            displayName: "Current State",
            description: "A snapshot of everything true right now, without scrolling back.",
            builtin: true,
            defaultRegion: "sidebar",
            defaultSize: { height: 320 },
            // Ungated: every section degrades to absent, so this is useful on a
            // pristine game (room, exits, people, objects) and grows as a game
            // exposes more.
            subscriptions: [
                "room", "entities", "resources", "effects",
                "target", "inventory", "equipment"
            ],

            mount: function (context) {
                context.element.setAttribute("data-aetos-state-view", "");
                /*
                 * Focusable, because it scrolls. Arrow keys scroll whatever has
                 * focus, so a scrolling region outside the tab order cannot be
                 * scrolled by keyboard at all -- the player can see there is
                 * more and has no way to reach it.
                 *
                 * Fifth and sixth instances of this in the client, both found by
                 * axe rather than by review. It is invisible to anyone testing
                 * with a mouse wheel, which is why it keeps recurring: the
                 * person who writes the panel is never the person it fails.
                 *
                 * `group`, not `region`. The enclosing panel is already a
                 * landmark carrying this widget's name, so a nested `region`
                 * with the same label produces two landmarks called
                 * "Resources" -- which axe reports as `landmark-unique` and a
                 * screen reader reports as the same thing twice. `group` is
                 * not a landmark, so it carries the label without competing.
                 */
                context.element.setAttribute("tabindex", "0");
                context.element.setAttribute("role", "group");
                context.element.setAttribute("aria-label", "Current state");
                // Explicitly off. `role="region"` carries no implicit live
                // behaviour, but stating it documents the decision where the
                // next person will look for it.
                context.element.setAttribute("aria-live", "off");
                render(context.element, context.store);
            },

            update: function (context) {
                // Ignores which section changed and rebuilds the snapshot,
                // because a snapshot of one section is not a snapshot.
                render(context.element, context.store);
            }
        };
    }

    window.AetosStateView = {
        createWidget: createStateWidget,
        resourceLine: resourceLine,
        plural: plural,
        remainingText: remainingText,
        SECTIONS: SECTIONS
    };

})(window, document);
