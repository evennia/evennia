/*
 * Aetos accessibility mode and its options.  A9, then A10.
 *
 * One visible control that switches between the standard interface and the
 * accessible one, and the picker that belongs to the second.
 *
 * WHY IT EXISTS. The preferences it shows are not new -- every one has worked
 * since the A-track built it, and every one is in Settings. The problem was that
 * they sat across five groups of a panel reached from the command palette, and
 * **almost nobody would ever find them**. Granularity was right and it created a
 * discovery problem.
 *
 * WHAT THE TOGGLE DOES. A9 shipped it as a disclosure: the panel hid and every
 * setting stayed applied. Gary asked for the sharper version -- two modes, "so
 * we dont have to try to be everything to everybody" -- and that is A10.
 * Standard mode stops the governed accommodations applying. Accessible mode
 * resumes them.
 *
 * IT MASKS; IT NEVER ERASES. Switching to standard leaves every stored value
 * untouched, so switching back restores the interface somebody built rather than
 * a fresh one. That is what makes the switch safe to try, and it is the whole
 * difference between a mode and a reset.
 *
 * WHAT IS NOT GOVERNED BY IT. Keyboard operation, focus management, landmarks,
 * accessible names, the announcer, colour never carrying meaning alone. Those
 * are unconditional in both modes and are listed in the panel as such --
 * somebody deciding whether to switch deserves to know what was never off.
 *
 * Three of the panel's own options are not governed either, because their
 * defaults are the *less* accessible value: reverting gestures, mute or
 * orientation help would impose an accommodation's opposite on the person who
 * asked for it. See `revertsInStandardMode` in preferences.js.
 */

(function (window, document) {
    "use strict";

    var PANEL_ID = "aetos-accessibility-panel";

    /*
     * Human-readable choices for the enumerated preferences.
     *
     * Written out rather than derived from the stored values, because
     * "reduced-stimulation" is a key and "Calmer" is a word. A picker whose
     * options read like configuration is a picker that fails the people it is
     * for.
     */
    var CHOICES = {
        "visual.contrast": [
            ["standard", "Standard"],
            ["high", "High contrast"]
        ],
        "visual.motion": [
            ["system", "Follow my system setting"],
            ["reduced", "Reduce motion"],
            ["full", "Full motion"]
        ],
        "visual.stimulation": [
            ["standard", "Standard"],
            ["reduced", "Reduced"],
            ["minimal", "Minimal"]
        ],
        "screenReader.announcementMode": [
            ["selective", "Only what I chose"],
            ["all", "Everything"],
            ["minimal", "As little as possible"]
        ],
        "visual.typeface": [
            ["proportional", "Normal lettering"],
            ["monospace", "Fixed-width lettering"]
        ]
    };

    function createAccessibilityPanel(services) {
        var preferences = services.preferences;
        var announce = services.announce || function () {};
        var focusManager = services.focusManager || null;
        var schema = window.AetosAccessibilityPreferences || {};
        var host = null;
        var toggleButton = null;
        var optionsButton = null;
        var summaryHost = null;

        /*
         * Whether the options are on screen.
         *
         * Deliberately NOT a stored preference. The mode is a lasting choice
         * about which interface you are in; having the settings open is a thing
         * you are doing this minute. Persisting it would mean the panel came
         * back every session for somebody who opened it once.
         */
        var optionsShown = false;

        function isAccessible() {
            return preferences.value("shell.mode") === "accessible";
        }

        function isOpen() {
            return optionsShown;
        }

        /*
         * Which screen the panel is showing.  A13.
         *
         *   "hub"     every setting as a tile, with its current value on it
         *   "detail"  one setting, with its choices large enough to read
         *
         * Not a stored preference, for the same reason `optionsShown` is not:
         * where you are inside a panel is a thing you are doing this minute, and
         * coming back next session to the middle of a settings screen you left
         * open once would be baffling.
         *
         * Closing the panel resets it to the hub, so reopening never drops
         * somebody into a detail view they have no memory of opening.
         */
        var view = "hub";
        var detailPath = null;

        /**
         * The governed entry for a path, if this mode offers it.
         *
         * @param {string} path A dotted preference path.
         * @returns {object|null} The entry, or null.
         */
        function entryAt(path) {
            var found = null;
            entriesForMode().forEach(function (entry) {
                if (entry.path === path) {
                    found = entry;
                }
            });
            return found;
        }

        /*
         * Open one setting.
         *
         * Focus moves to the heading of the new screen rather than staying on a
         * tile that no longer exists. This is the one place in the client where
         * focus moves without the player pressing a key that means "go there" --
         * and it is exactly the case WCAG allows it: the activation *was* the
         * request to go there, and leaving focus on a removed element drops it
         * to the document.
         */
        function openDetail(path) {
            var entry = entryAt(path);
            if (!entry) {
                return null;
            }
            view = "detail";
            detailPath = path;
            render();
            focusFirstHeading();
            announce(entry.label + ". " + entry.detail);
            return path;
        }

        /*
         * Back to the tiles.
         *
         * Gary, on A12's chooser: *"theres no way to get back once you pick
         * one."* He was right, and it was true of the chooser and would have
         * been true of every detail screen this view adds. A screen somebody can
         * enter and not leave is the worst thing an accessibility panel can be,
         * because the person stuck in it is the person least able to guess at a
         * way out.
         */
        function backToHub() {
            view = "hub";
            detailPath = null;
            render();
            focusFirstHeading();
            announce("All settings.");
            return "hub";
        }

        /*
         * Ask the starting-point question again.
         *
         * The other half of Gary's "no way to get back": having taken a starting
         * point, there was no route to the screen of tiles he liked. Clearing
         * `shell.preset` puts it back, and it changes nothing else -- every
         * setting the preset applied stays exactly as it is until a new one is
         * chosen.
         */
        function reopenChooser() {
            preferences.update({ shell: { preset: null } });
            view = "hub";
            detailPath = null;
            render();
            focusFirstHeading();
            announce("Starting points. Nothing has been changed.");
            return true;
        }

        /**
         * Put focus on the first heading of whatever was just rendered.
         *
         * @returns {boolean} Whether anything was focused.
         */
        function focusFirstHeading() {
            if (!host) {
                return false;
            }
            var target = host.querySelector("h2, .aetos-a11y-detail__back");
            if (!target) {
                return false;
            }
            // Headings are not focusable by default, and making one permanently
            // focusable would add a stop to everybody's tab order. -1 lets it
            // receive focus programmatically without joining that order.
            if (!target.hasAttribute("tabindex")) {
                target.setAttribute("tabindex", "-1");
            }
            target.focus();
            return true;
        }

        /*
         * Whether the starting-point question is still owed.  A12.
         *
         * Only in accessible mode: standard mode is the client as it comes, and
         * putting an accessibility question in front of somebody who has not
         * asked for one is the presumption A10 was right to avoid.
         *
         * `null` is "never asked". Every other value -- including "custom" --
         * is an answer, which is why choosing to set things up by hand has to
         * be a preset rather than a way of dismissing the chooser.
         */
        function needsChooser() {
            return isAccessible() && preferences.value("shell.preset") === null;
        }

        /*
         * The options this mode can actually apply.
         *
         * Standard mode is not empty -- text size, sound, gestures and
         * orientation help all apply there, because none of them is reverted by
         * the switch. Showing the full list in standard mode would offer
         * controls that do nothing; hiding the panel entirely would take text
         * size away from the people most likely to need it.
         */
        function entriesForMode() {
            var all = schema.GOVERNED || [];
            if (isAccessible()) {
                return all;
            }
            return all.filter(function (entry) {
                return !entry.revertsInStandardMode;
            });
        }

        /*
         * Write one preference.
         *
         * Paths are `group.key`, which is the shape `update` takes. Split here
         * rather than teaching the panel about the schema's structure.
         */
        /*
         * True while this panel is the one writing.  A13.
         *
         * THE SLIDER WAS UNDRAGGABLE. Every `input` event wrote a preference,
         * every write notified subscribers, and this panel's subscriber calls
         * `render()`, which begins `host.textContent = ""`. So dragging the
         * text-size slider destroyed the very element being dragged, on the
         * first pixel of movement: the browser had nothing left to send pointer
         * events to, the drag ended, and the next increment needed a fresh
         * click.
         *
         * Gary: *"I try to slide it smoothly back and forth but the slider
         * redraws every time... one click, wait, one click, wait."*
         *
         * A panel does not need to redraw itself to show a change it just made
         * -- the control already shows it. The subscription exists for changes
         * from *elsewhere*: Settings, the command palette, a keyboard shortcut.
         * So the flag suppresses only self-inflicted repaints.
         *
         * `update()` notifies synchronously, so the flag is down again before
         * this function returns and cannot be left stuck by an exception in a
         * subscriber -- `notify()` already catches those individually.
         */
        var applyingOwnChange = false;

        function set(path, value) {
            var parts = path.split(".");
            var patch = {};
            patch[parts[0]] = {};
            patch[parts[0]][parts[1]] = value;
            applyingOwnChange = true;
            try {
                return preferences.update(patch);
            } finally {
                applyingOwnChange = false;
            }
        }

        /*
         * The text-size control.  A13 rewrote it; A0 chose the element.
         *
         * A native range input, not a custom slider: it arrives already operable
         * by keyboard, already announced with its value, and already understood
         * by every assistive technology the player might use. A hand-built one
         * starts at none of that.
         *
         * It no longer builds its own label and explanation. In the detail view
         * the `<legend>` is the name and the paragraph under it is the
         * explanation, so a control that carried its own would say everything
         * twice.
         *
         * The buttons either side are not decoration. A slider is the hardest
         * gesture this interface asks for and the least forgiving for a tremor,
         * and this is the one setting somebody may need to change *before* they
         * can comfortably see anything -- so there is a way to change it that
         * needs no dragging at all, and each press is a whole step rather than a
         * pixel.
         */
        function rangeControl(entry, id) {
            var bounds = (schema.RANGES && schema.RANGES[entry.path]) || [0.75, 2.5];
            var step = 0.25;

            var wrapper = document.createElement("div");
            wrapper.className = "aetos-a11y-detail__range";

            var input = document.createElement("input");
            input.type = "range";
            input.className = "aetos-a11y-panel__range";
            input.id = id;
            input.min = String(bounds[0]);
            input.max = String(bounds[1]);
            input.step = "0.05";
            input.value = String(preferences.value(entry.path));

            var output = document.createElement("output");
            output.className = "aetos-a11y-detail__reading";
            output.setAttribute("for", id);

            function show() {
                output.textContent = Math.round(parseFloat(input.value) * 100) + "%";
            }
            show();

            /*
             * `input`, so the client changes as the slider moves.
             *
             * Since A13 this no longer destroys the control it is dragged by:
             * `set()` suppresses this panel's own repaint. Before that, every
             * pixel of movement rebuilt the panel and the drag ended on the
             * first one.
             */
            input.addEventListener("input", function () {
                show();
                set(entry.path, parseFloat(input.value));
                renderSummary();
            });

            function nudge(direction) {
                var next = parseFloat(input.value) + direction * step;
                next = Math.min(bounds[1], Math.max(bounds[0], next));
                next = Math.round(next * 100) / 100;
                input.value = String(next);
                show();
                set(entry.path, next);
                renderSummary();
                announce(entry.label + " " + Math.round(next * 100) + " percent.");
            }

            function stepper(text, label, direction) {
                var button = document.createElement("button");
                button.type = "button";
                button.className = "aetos-a11y-detail__step";
                button.textContent = text;
                button.setAttribute("aria-label", label);
                button.addEventListener("click", function () { nudge(direction); });
                return button;
            }

            wrapper.appendChild(stepper("\u2212", "Smaller text", -1));
            wrapper.appendChild(input);
            wrapper.appendChild(stepper("+", "Larger text", 1));
            wrapper.appendChild(output);
            return wrapper;
        }

        /*
         * What is actually on, without opening anything.  A13.
         *
         * Gary: *"once options are selected I dont see them on the main
         * screen."*
         *
         * That is a real gap and it matters more than it sounds. Accessible mode
         * masks rather than erases, settings survive a switch, and a preset can
         * change five things at once -- so "what is in force right now" is a
         * genuine question with a non-obvious answer, and the only way to answer
         * it was to open the panel and read four groups.
         *
         * A single line, only when there is something to say. Each item is a
         * button that opens that setting, so the strip is also the shortest
         * route to changing one's mind about it.
         *
         * SHOWN IN BOTH MODES, and this is the part worth getting right: in
         * standard mode it lists only what is still applying, because that is
         * precisely the confusing case. Somebody who switched to standard and
         * kept their text size deserves to see that their text size is still
         * theirs and their contrast is not.
         */
        function activeSettings() {
            var active = [];
            entriesForMode().forEach(function (entry) {
                var current = preferences.value(entry.path);
                var fallback = defaultFor(entry.path);
                if (current === fallback) {
                    return;
                }
                // In standard mode a governed setting is stored but not
                // applied, so listing it would claim something untrue.
                if (!isAccessible() && entry.revertsInStandardMode) {
                    return;
                }
                active.push(entry);
            });
            return active;
        }

        /**
         * A preference's shipped default.
         *
         * @param {string} path A dotted preference path.
         * @returns {*} The default value, or undefined.
         */
        function defaultFor(path) {
            var parts = path.split(".");
            var defaults = schema.DEFAULTS || {};
            return defaults[parts[0]] ? defaults[parts[0]][parts[1]] : undefined;
        }

        function renderSummary() {
            if (!summaryHost) {
                return;
            }
            summaryHost.textContent = "";

            var active = activeSettings();
            /*
             * Nothing to say, so nothing on screen. A permanent strip reading
             * "no accommodations" would be a line of the client's own furniture
             * spent telling people about the absence of a thing.
             *
             * A17 adds the second condition: hidden while the options are open.
             * The panel lists every one of these settings and its value a few
             * pixels below, so leaving the strip up duplicates the whole thing
             * -- twice the reading for somebody going through it with a screen
             * reader, and a row of the panel's own space spent repeating what
             * the panel says. It exists to answer "what is on" *without*
             * opening anything.
             */
            summaryHost.hidden = !active.length || isOpen();
            if (summaryHost.hidden) {
                return;
            }

            var lead = document.createElement("span");
            lead.className = "aetos-a11y-summary__lead";
            lead.textContent = "In use:";
            summaryHost.appendChild(lead);

            var list = document.createElement("ul");
            list.className = "aetos-a11y-summary__list";

            active.forEach(function (entry) {
                var item = document.createElement("li");
                var button = document.createElement("button");
                button.type = "button";
                button.className = "aetos-a11y-summary__item";
                /*
                 * "Contrast: High contrast", not "Contrast High contrast".
                 * Without the separator the two halves run together into
                 * something that reads like a stutter.
                 */
                button.textContent = entry.label + ": " + valueText(entry);
                /*
                 * No `aria-label`.  A17.
                 *
                 * It used to read "Change Contrast, currently High contrast",
                 * which is more words for the same information and, being an
                 * attribute rather than a text node, was not translated. The
                 * visible text already names the setting and its value, and the
                 * element is a button -- which is exactly the affordance a
                 * sighted person infers from the way it is drawn. Telling a
                 * screen reader user something extra here would break parity
                 * rather than add to it.
                 */
                button.addEventListener("click", function () {
                    if (!isOpen()) {
                        optionsShown = true;
                    }
                    openDetail(entry.path);
                });
                item.appendChild(button);
                list.appendChild(item);
            });

            summaryHost.appendChild(list);
        }

        /*
         * The hub: one tile per setting, showing what it is set to.  A13.
         *
         * Gary, on A12's flat panel of grouped controls:
         *
         *     *"I liked the tiles and then opening a box for that specific
         *     setting so if you are visually impaired, its easy to see choices
         *     and drill down into those choices."*
         *
         * He is describing progressive disclosure, and he is right that the
         * flat version is the wrong shape for the person it is for. A12 fixed
         * the *density* of the old panel -- eleven controls became four groups
         * of four -- but every control was still on screen at once, and each one
         * was still a `<select>` or a checkbox: small, sitting next to its own
         * explanation, and requiring you to read the whole board to find the one
         * you wanted.
         *
         * A tile is a different proposition. It says two things -- what this
         * setting is, and what it is currently set to -- in text large enough to
         * read, and it is one target rather than a control plus a label plus a
         * sentence. **Showing the current value on the tile is the half that
         * matters**: it turns the hub into an answer to "what is on right now",
         * which was the other thing Gary could not find.
         *
         * Each group keeps its heading, so the structure a screen reader gets is
         * the same one the eye gets.
         */
        function buildHub(container) {
            var available = entriesForMode();
            var byPath = {};
            available.forEach(function (entry) {
                byPath[entry.path] = entry;
            });

            var placed = {};

            function addGroup(label, entries) {
                if (!entries.length) {
                    return;
                }
                var group = document.createElement("section");
                group.className = "aetos-a11y-panel__group";

                var heading = document.createElement("h3");
                heading.className = "aetos-a11y-panel__group-heading";
                heading.id = "aetos-a11y-group-"
                    + label.toLowerCase().replace(/[^a-z0-9]+/g, "-");
                heading.textContent = label;
                group.setAttribute("aria-labelledby", heading.id);
                group.appendChild(heading);

                var list = document.createElement("ul");
                list.className = "aetos-a11y-panel__tiles";
                entries.forEach(function (entry) {
                    list.appendChild(tileFor(entry));
                });
                group.appendChild(list);
                container.appendChild(group);
            }

            (schema.SECTIONS || []).forEach(function (section) {
                var entries = [];
                section.paths.forEach(function (path) {
                    if (byPath[path]) {
                        entries.push(byPath[path]);
                        placed[path] = true;
                    }
                });
                addGroup(section.label, entries);
            });

            // Anything the sections forgot. A test asserts this is empty; it
            // renders anyway so that adding a preference and not listing it
            // costs a heading rather than the setting itself.
            addGroup(
                "More",
                available.filter(function (entry) {
                    return !placed[entry.path];
                })
            );
        }

        /**
         * One tile: the setting's name, and what it is set to.
         *
         * @param {object} entry A governed preference.
         * @returns {HTMLElement} A list item containing the button.
         */
        function tileFor(entry) {
            var item = document.createElement("li");

            var button = document.createElement("button");
            button.type = "button";
            button.className = "aetos-a11y-tile";

            var slug = entry.path.replace(/\./g, "-");

            var name = document.createElement("span");
            name.className = "aetos-a11y-tile__name";
            name.id = "aetos-a11y-tile-name-" + slug;
            name.textContent = entry.label;

            var value = document.createElement("span");
            value.className = "aetos-a11y-tile__value";
            value.id = "aetos-a11y-tile-value-" + slug;
            value.textContent = valueText(entry);

            /*
             * The accessible name is composed from the visible text.  A17.
             *
             * It carries both halves, because a button reading only "Text size"
             * tells a screen reader user nothing about the state, and the state
             * is half the reason the tile exists.
             *
             * `aria-labelledby` pointing at the two spans rather than an
             * `aria-label` string, for two reasons Heydon Pickering makes and
             * this project had ignored:
             *
             *   - **`aria-label` is not translated.** Machine translation
             *     services work on text nodes and skip the attribute, so a
             *     player reading the client in another language would get an
             *     English accessible name on every tile. `aria-labelledby`
             *     points at real text, which does get translated.
             *   - **Parity.** An `aria-label` can drift from what is on screen;
             *     two ids cannot. That matters most for voice control, where
             *     somebody says what they *see* to activate a control.
             */
            button.setAttribute("aria-labelledby", name.id + " " + value.id);

            button.appendChild(name);
            button.appendChild(value);
            button.addEventListener("click", function () {
                openDetail(entry.path);
            });

            item.appendChild(button);
            return item;
        }

        /**
         * What a setting is currently set to, in words.
         *
         * @param {object} entry A governed preference.
         * @returns {string} Human-readable current value.
         */
        function valueText(entry) {
            var current = preferences.value(entry.path);
            if (entry.kind === "range") {
                return Math.round(parseFloat(current) * 100) + "%";
            }
            if (entry.kind === "boolean") {
                return current ? "On" : "Off";
            }
            var choices = CHOICES[entry.path] || [];
            for (var i = 0; i < choices.length; i++) {
                if (choices[i][0] === current) {
                    return choices[i][1];
                }
            }
            return String(current);
        }

        /*
         * One setting, on its own, with room.  A13.
         *
         * WHY RADIOS RATHER THAN A `<select>`. A dropdown shows one option at a
         * time in small text and hides the rest behind an interaction. For
         * somebody who came here *because* reading small text is hard, that is
         * the wrong control: the whole point of drilling in is to see the
         * choices. Native `<input type="radio">` in a `<fieldset>` gives a real
         * radio group -- arrow-key operable, announced as "2 of 4", understood
         * by every assistive technology -- and can be drawn as large as we like.
         *
         * The same treatment for booleans. "On" and "Off" as two visible choices
         * reads better than a checkbox whose state has to be inferred from a
         * tick, and it makes every setting in the panel behave the same way.
         *
         * Still native controls, which is A0's rule and the reason the earlier
         * `<select>` was chosen over anything hand-built. A radio is not a step
         * away from that; it is the same rule with a different native element.
         *
         * THERE IS NO PREVIEW PANE, deliberately. Every one of these applies
         * immediately to the whole client, so the preview *is* the client. A
         * sample of text beside the real thing would be a second, smaller, less
         * honest version of the change.
         */
        function buildDetail(container, entry) {
            /*
             * The way back comes first.
             *
             * First in the DOM, so it is the first thing Tab reaches and the
             * first thing a screen reader meets inside the panel. Gary found
             * that the chooser had no way back at all, and a screen you can
             * enter but not leave is the defect this view could most easily
             * repeat.
             */
            var back = document.createElement("button");
            back.type = "button";
            back.className = "aetos-a11y-detail__back";
            back.textContent = "\u2190 All settings";
            back.addEventListener("click", function () { backToHub(); });
            container.appendChild(back);

            var fieldset = document.createElement("fieldset");
            fieldset.className = "aetos-a11y-detail";

            var legend = document.createElement("legend");
            legend.className = "aetos-a11y-detail__legend";
            legend.textContent = entry.label;
            fieldset.appendChild(legend);

            var note = document.createElement("p");
            note.className = "aetos-a11y-detail__note";
            note.id = "aetos-a11y-detail-note";
            note.textContent = entry.detail;
            fieldset.appendChild(note);
            fieldset.setAttribute("aria-describedby", note.id);

            if (entry.kind === "range") {
                fieldset.appendChild(rangeControl(entry, "aetos-a11y-detail-range"));
            } else {
                fieldset.appendChild(choiceList(entry));
            }

            container.appendChild(fieldset);
        }

        /**
         * The choices for one setting, as a native radio group.
         *
         * @param {object} entry A governed preference.
         * @returns {HTMLElement} The list of choices.
         */
        function choiceList(entry) {
            var list = document.createElement("div");
            list.className = "aetos-a11y-detail__choices";

            var choices = entry.kind === "boolean"
                ? [[true, "On"], [false, "Off"]]
                : (CHOICES[entry.path] || []);
            var current = preferences.value(entry.path);
            var group = "aetos-a11y-choice-" + entry.path.replace(/\./g, "-");
            var cards = [];

            /*
             * Mark the chosen card.
             *
             * From JavaScript rather than with CSS `:has()`, which needs Chrome
             * 105 and Firefox 121 against a published floor of Chrome 87 and
             * Firefox 75. The radio itself carries the state natively either
             * way; this is the border weight around it.
             */
            function markChosen() {
                cards.forEach(function (card) {
                    var on = card.input.checked;
                    card.label.className = on
                        ? "aetos-a11y-choice aetos-a11y-choice--chosen"
                        : "aetos-a11y-choice";
                });
            }

            choices.forEach(function (choice, index) {
                var id = group + "-" + index;

                var label = document.createElement("label");
                label.className = "aetos-a11y-choice";
                label.setAttribute("for", id);

                var input = document.createElement("input");
                input.type = "radio";
                input.name = group;
                input.id = id;
                input.className = "aetos-a11y-choice__input";
                input.checked = choice[0] === current;
                input.addEventListener("change", function () {
                    if (!input.checked) {
                        return;
                    }
                    set(entry.path, choice[0]);
                    markChosen();
                    /*
                     * Repaint the summary strip, not this list.
                     * Rebuilding the radios while one of them has focus would
                     * drop focus to the document -- the same class of defect as
                     * the slider destroying itself mid-drag.
                     */
                    renderSummary();
                    announce(entry.label + ": " + choice[1] + ".");
                });

                var text = document.createElement("span");
                text.className = "aetos-a11y-choice__label";
                text.textContent = choice[1];

                label.appendChild(input);
                label.appendChild(text);
                list.appendChild(label);
                cards.push({ label: label, input: input });
            });

            markChosen();
            return list;
        }

        /*
         * The starting point chooser.  A12.
         *
         * Shown instead of the options when somebody has turned accessible mode
         * on and has never been asked. One question, five answers, in the words
         * a person would use about their own situation -- against the eleven
         * technical decisions this panel used to open with.
         *
         * Buttons rather than radios: choosing one *does* something
         * immediately, and a radio group implies a pending Apply. The list is a
         * `list` so the number of choices is announced up front, which is the
         * thing that tells somebody how long this will take.
         */
        function buildChooser(container) {
            var heading = document.createElement("h2");
            heading.className = "aetos-a11y-panel__heading";
            heading.textContent = "What would help most?";

            var intro = document.createElement("p");
            intro.className = "aetos-a11y-panel__detail";
            intro.textContent =
                "Pick the closest one and the client changes straight away. "
                + "You can change any of it afterwards, and nothing here is "
                + "permanent.";

            container.appendChild(heading);
            container.appendChild(intro);

            var list = document.createElement("ul");
            list.className = "aetos-a11y-panel__choices";

            (schema.PRESETS || []).forEach(function (preset) {
                var item = document.createElement("li");

                var button = document.createElement("button");
                button.type = "button";
                button.className = "aetos-a11y-panel__choice";
                button.setAttribute(
                    "aria-describedby", "aetos-a11y-preset-" + preset.name
                );

                var name = document.createElement("span");
                name.className = "aetos-a11y-panel__choice-label";
                name.textContent = preset.label;

                var detail = document.createElement("span");
                detail.className = "aetos-a11y-panel__choice-detail";
                detail.id = "aetos-a11y-preset-" + preset.name;
                detail.textContent = preset.detail;

                button.appendChild(name);
                button.appendChild(detail);
                button.addEventListener("click", function () {
                    choose(preset.name);
                });

                item.appendChild(button);
                list.appendChild(item);
            });

            container.appendChild(list);
        }

        /*
         * Take a starting point, and say what happened.
         *
         * The announcement names the way back in the same breath as the change.
         * Somebody who has just altered the contrast and type size of their
         * whole client on one keypress needs to hear that it is undoable before
         * they need to hear anything else.
         */
        function choose(name) {
            var preset = null;
            (schema.PRESETS || []).forEach(function (candidate) {
                if (candidate.name === name) {
                    preset = candidate;
                }
            });
            if (!preset) {
                return null;
            }
            preferences.applyPreset(name);
            render();
            if (focusManager && focusManager.focusFirst) {
                focusManager.focusFirst(host);
            }
            announce(
                preset.name === "custom"
                    ? "Every setting is listed below. Nothing has been changed."
                    : preset.label + " applied. Every setting is listed below "
                        + "and any of them can be changed."
            );
            return preset.name;
        }

        function buildUnconditional(container) {
            var heading = document.createElement("h3");
            heading.className = "aetos-a11y-panel__heading";
            heading.textContent = "Always on";

            var note = document.createElement("p");
            note.className = "aetos-a11y-panel__detail";
            note.textContent =
                "These are not options. They are how the client is built, and "
                + "they are the same whether this panel is open or closed.";

            var list = document.createElement("ul");
            list.className = "aetos-a11y-panel__always";
            (schema.UNCONDITIONAL || []).forEach(function (line) {
                var item = document.createElement("li");
                item.textContent = line;
                list.appendChild(item);
            });

            container.appendChild(heading);
            container.appendChild(note);
            container.appendChild(list);
        }

        function render() {
            if (!host) {
                return;
            }
            host.textContent = "";
            host.hidden = !isOpen();
            if (optionsButton) {
                // Shown in both modes: standard mode still has text size.
                optionsButton.hidden = false;
                optionsButton.setAttribute("aria-expanded", isOpen() ? "true" : "false");
            }
            if (toggleButton) {
                /*
                 * `aria-checked` on a `switch`, not `aria-pressed` on a button
                 * and not `aria-expanded` on a disclosure.
                 *
                 * It is a two-state control: a switch announces "on" and "off",
                 * which is what this is. `aria-pressed` would say "pressed",
                 * which describes the act rather than the state, and
                 * `aria-expanded` would claim it merely reveals a panel -- while
                 * it is in fact changing the contrast and type size of the whole
                 * client.
                 */
                /*
                 * `isAccessible()`, not `isOpen()`.
                 *
                 * They were the same function until the options were split out
                 * of the mode, and this line kept the old one -- so the switch
                 * would have reported whether the settings panel was open
                 * rather than which mode you were in. It reads correctly only
                 * when both happen to agree, which is exactly how a defect like
                 * this survives a quick look.
                 */
                toggleButton.setAttribute("aria-checked", isAccessible() ? "true" : "false");
                toggleButton.setAttribute(
                    "title",
                    isAccessible()
                        ? "Accessible mode is on. Ctrl+Shift+A switches back."
                        : "Switch to accessible mode. Ctrl+Shift+A."
                );
            }
            // The strip is not part of the panel and does not hide with it --
            // that is the whole point of it.
            renderSummary();

            if (!isOpen()) {
                return;
            }

            /*
             * Never asked, and in accessible mode: ask.  A12.
             *
             * This is the whole answer to "you flip the switch and nothing
             * happens". It happens once -- taking any starting point, including
             * "let me choose each setting myself", records an answer and this
             * never appears again. A13 added a route back to it, so "once" is
             * now "until you ask for it again" rather than "ever".
             */
            if (needsChooser()) {
                buildChooser(host);
                return;
            }

            /*
             * One setting, on its own.  A13.
             *
             * Guarded on the entry still existing: switching to standard mode
             * while a detail screen is open for a setting standard mode does not
             * offer would otherwise render an empty box with a back button.
             */
            if (view === "detail") {
                var open = entryAt(detailPath);
                if (open) {
                    buildDetail(host, open);
                    return;
                }
                view = "hub";
                detailPath = null;
            }

            var heading = document.createElement("h2");
            heading.className = "aetos-a11y-panel__heading";
            heading.textContent = isAccessible()
                ? "Accessible mode options"
                : "Display options";

            var intro = document.createElement("p");
            intro.className = "aetos-a11y-panel__detail";
            intro.textContent = isAccessible()
                ? "Pick any one to change it. Each is separate -- there is no "
                    + "bundle to accept or refuse. Switching back to standard mode "
                    + "stops them applying and keeps every choice, so you can look "
                    + "and come back."
                : "These apply in standard mode too. Turning on accessible mode "
                    + "adds contrast, motion, announcement and layout options to "
                    + "this list.";

            host.appendChild(heading);
            host.appendChild(intro);

            // The groups lay out side by side; the tiles inside each one stack.
            // A12 -- the flat version put every control in a single grid, which
            // came out five columns wide with no headings.
            var groups = document.createElement("div");
            groups.className = "aetos-a11y-panel__groups";
            buildHub(groups);
            host.appendChild(groups);

            /*
             * The way back to the starting points.  A13.
             *
             * Only in accessible mode, because that is the only mode the
             * question is ever asked in. Phrased as what it does rather than as
             * a reset: it shows the tiles again and changes nothing until
             * something is picked.
             */
            if (isAccessible()) {
                var again = document.createElement("button");
                again.type = "button";
                again.className = "aetos-a11y-panel__restart";
                again.textContent = "Show the starting points again";
                again.addEventListener("click", function () { reopenChooser(); });
                host.appendChild(again);
            }

            buildUnconditional(host);
            markScrollable();
        }

        /*
         * A scrollable panel is focusable; a panel that fits is not.  A17.
         *
         * At a large text size eleven settings do not fit on one screen, and
         * that is correct -- it is what reflow means. What was missing is that
         * the overflow was neither operable nor announced: a sighted mouse user
         * saw three groups of four with nothing to say a fourth existed, and
         * nobody could scroll the region directly.
         *
         * `tabindex="0"` on a scroll container buys native arrow-key, Page Up
         * and Page Down scrolling with no key handler at all, and because the
         * panel is already a `role="region"` with a label, focusing it
         * announces "Accessibility options, region" -- so the stop explains
         * itself.
         *
         * Only while it actually overflows, which is Heydon Pickering's rule
         * from Data Tables: a tab stop that does nothing is a WCAG 2.4.3 Focus
         * Order failure in his reading, and an irritation in anybody's. Tabbing
         * to a container you cannot scroll is exactly that.
         */
        function markScrollable() {
            if (!host) {
                return;
            }
            // Reading `scrollHeight` forces layout, so this is accurate
            // immediately after the render that built the content.
            var overflowing = host.scrollHeight > host.clientHeight + 1;
            if (overflowing) {
                host.setAttribute("tabindex", "0");
            } else {
                host.removeAttribute("tabindex");
            }
            return overflowing;
        }

        /*
         * Switch between the standard interface and the accessible one.
         *
         * The stored settings are never touched -- see `effective()` in
         * preferences.js. Standard mode stops the governed accommodations
         * applying; accessible mode resumes exactly what was there before.
         *
         * THE WAY BACK. This is the hazard in a real mode switch and the reason
         * A9 shipped the softer version first: somebody turns it off to look,
         * the type shrinks and the contrast drops, and they cannot find the
         * control again. Three things answer that, and all three matter:
         *
         *   1. `Ctrl+Shift+A` works in both modes and is stated out loud at the
         *      moment it becomes relevant, rather than in documentation nobody
         *      is reading at that moment.
         *   2. The toggle itself is never governed by the mode. It keeps its
         *      place, its label and its size in both.
         *   3. Nothing is erased, so the way back is one keystroke rather than
         *      a rebuild.
         */
        function setMode(wanted) {
            /*
             * `setMode("standard")` used to turn accessible mode ON.
             *
             * The argument was coerced with `!!wanted`, so any non-empty string
             * was true -- and the two strings anybody would reach for are the
             * names of the two modes. A function called `setMode` that accepts
             * `"standard"` and does the opposite is the exact shape of defect
             * this project keeps finding, except in an API rather than in a
             * control.
             *
             * No player could hit it: every call site inside the client passes
             * nothing and toggles. It was found by the A8 readiness probe, which
             * is an outside caller, falling into it on its first run -- which is
             * what an outside caller would do.
             *
             * Now the mode names work, booleans still work, no argument still
             * toggles, and anything else is refused rather than guessed at.
             * Refused with `null` rather than an exception, because this runs in
             * a websocket-driven client where "degrade, never raise" is the
             * rule -- and `null` rather than `false`, because a successful
             * switch to standard mode already returns `false` and the two must
             * not look the same.
             */
            var next;
            if (wanted === undefined) {
                next = !isAccessible();
            } else if (wanted === "accessible" || wanted === "standard") {
                next = wanted === "accessible";
            } else if (typeof wanted === "boolean") {
                next = wanted;
            } else {
                return null;
            }
            var lost = preferences.activeAccommodations
                ? preferences.activeAccommodations()
                : [];
            set("shell.mode", next ? "accessible" : "standard");

            /*
             * Ask the question, once, at the only moment it makes sense.  A12.
             *
             * This is a deliberate narrowing of the rule stated below, and it
             * is worth being plain about that. The objection there was that
             * opening the settings made the switch read as "show me a panel of
             * options" rather than as a mode control, and that objection was
             * right about a panel of eleven technical choices.
             *
             * One question with five plain-language answers is not that panel.
             * And the alternative, measured, is worse than the thing the rule
             * was protecting against: turning on accessible mode with no preset
             * and no options open changes **nothing at all** on screen, because
             * every governed preference already sits at its standard value. A
             * switch that visibly does nothing teaches people it is cosmetic.
             *
             * It happens once. Any answer, including "let me choose each
             * setting myself", is recorded, and from then on the switch behaves
             * exactly as the rule below describes.
             */
            if (next && needsChooser()) {
                optionsShown = true;
            }
            render();

            if (next) {
                announce(needsChooser()
                    ? "Accessible mode. One question below about what would "
                        + "help most."
                    : lost.length
                        ? "Accessible mode. " + lost.join(", ") + " back on."
                        : "Accessible mode. The Options button beside the switch "
                            + "chooses what it applies.");
            } else {
                /*
                 * Say what stopped and how to undo it, in that order. Somebody
                 * who has just lost their contrast needs the second half more
                 * than the first, and hears the sentence to the end.
                 */
                announce(lost.length
                    ? "Standard mode. " + lost.join(", ") + " no longer applied, "
                        + "and nothing was erased. Press Control Shift A to bring "
                        + "them back."
                    : "Standard mode. Press Control Shift A to return.",
                    { priority: "important" });
            }

            /*
             * Switching the mode does not open the settings.
             *
             * It used to, and that made the switch read as "show me a panel of
             * options" rather than as a mode control -- which is exactly how it
             * was described back to me. Turning a mode on and configuring it are
             * two things, and the switch does the first.
             */
            return next;
        }

        /*
         * Change the text size by a step, or reset it.
         *
         * Works in both modes, because `visual.scale` is not reverted by the
         * switch. Clamped to the schema's own range so a repeated keystroke
         * cannot walk it somewhere unreadable, and announced with the resulting
         * percentage rather than "larger" -- somebody adjusting this cannot
         * necessarily see the result.
         *
         * Args:
         *     delta (number|null): The step, or null to reset to the default.
         */
        function adjustTextSize(delta) {
            var bounds = (schema.RANGES && schema.RANGES["visual.scale"]) || [0.75, 2.5];
            var next = 1;
            if (delta !== null && delta !== undefined) {
                next = (parseFloat(preferences.value("visual.scale")) || 1) + delta;
                next = Math.min(bounds[1], Math.max(bounds[0], next));
                next = Math.round(next * 100) / 100;
            }
            set("visual.scale", next);
            render();
            announce("Text size " + Math.round(next * 100) + " percent.");
            return next;
        }

        /*
         * Show or hide the options.
         *
         * Only meaningful in accessible mode, and the button that calls it is
         * hidden in standard mode. Guarded anyway, because the palette command
         * can reach it from anywhere.
         */
        function toggleOptions() {
            // Does NOT switch the mode. Standard mode has options of its own,
            // and quietly changing somebody's interface because they asked to
            // see the settings would be the same conflation the switch itself
            // just had removed.
            optionsShown = !optionsShown;
            // Closing returns to the tiles, so reopening never drops somebody
            // into a detail screen they have no memory of leaving open.
            if (!optionsShown) {
                view = "hub";
                detailPath = null;
            }
            render();
            if (optionsShown) {
                announce("Accessibility options shown.");
                if (focusManager && focusManager.focusFirst) {
                    focusManager.focusFirst(host);
                }
            } else {
                announce("Accessibility options hidden. Nothing was changed.");
            }
            return optionsShown;
        }

        function attach(container, button) {
            /*
             * The summary strip sits ABOVE the panel and outside it.  A13.
             *
             * Outside, because it has to survive the panel being closed -- the
             * whole complaint was that with the panel shut there was no sign of
             * what had been chosen. Above, because it is a statement about the
             * client rather than part of the settings screen, and it should read
             * as a continuation of the status bar it sits under.
             */
            summaryHost = document.createElement("div");
            summaryHost.id = "aetos-accessibility-summary";
            summaryHost.className = "aetos-a11y-summary";
            summaryHost.hidden = true;
            /*
             * A named region, like the panel below it.
             *
             * Not decoration: `#aetos-accessibility-host` sits between the
             * header and `<main>` and is inside no landmark, so a bare `<div>`
             * here put its buttons outside every landmark on the page. axe's
             * `region` rule caught it -- and caught it only at 250% text,
             * because that is the one view in the sweep where a setting is away
             * from its default and the strip is therefore on screen at all.
             *
             * The strip appears only when it has something to say, so this adds
             * a landmark that comes and goes. That is the right trade: a
             * landmark with no content would be worse, and "what is in use" is a
             * genuine destination.
             *
             * Not a live region. It changes as a *result* of something the
             * player just did and was already told about, and announcing it
             * again would say everything twice -- one of the three failures
             * `checks/announce.js` exists to catch.
             */
            summaryHost.setAttribute("role", "region");
            summaryHost.setAttribute("aria-label", "Accessibility settings in use");
            container.appendChild(summaryHost);

            host = document.createElement("section");
            host.id = PANEL_ID;
            host.className = "aetos-a11y-panel";
            // A landmark, because it is a destination somebody navigates to
            // rather than a dialog that interrupts them.
            host.setAttribute("role", "region");
            host.setAttribute("aria-label", "Accessibility options");
            container.appendChild(host);

            toggleButton = button || null;
            if (toggleButton) {
                toggleButton.addEventListener("click", function () { setMode(); });
            }

            optionsButton = document.getElementById("aetos-accessibility-options");
            if (optionsButton) {
                optionsButton.setAttribute("aria-controls", PANEL_ID);
                optionsButton.addEventListener("click", function () { toggleOptions(); });
            }

            // Re-render when anything else changes a preference this panel
            // shows -- Settings and the palette can change the same values, and
            // a picker showing stale state is worse than no picker.
            // Only for changes from elsewhere -- Settings, the palette, a
            // shortcut. Repainting in response to this panel's own writes is
            // what made the slider undraggable; see `applyingOwnChange`.
            preferences.subscribe(function () {
                if (!applyingOwnChange) {
                    render();
                }
            });
            render();
            return host;
        }

        return {
            attach: attach,
            // `toggle` switches the MODE, which is what the shortcut and the
            // switch both mean by it.
            toggle: setMode,
            setMode: setMode,
            toggleOptions: toggleOptions,
            openDetail: openDetail,
            backToHub: backToHub,
            reopenChooser: reopenChooser,
            activeSettings: activeSettings,
            adjustTextSize: adjustTextSize,
            isAccessible: isAccessible,
            isOpen: isOpen,
            needsChooser: needsChooser,
            choose: choose,
            render: render
        };
    }

    window.AetosAccessibilityPanel = {
        create: createAccessibilityPanel,
        PANEL_ID: PANEL_ID,
        CHOICES: CHOICES
    };

})(window, document);
