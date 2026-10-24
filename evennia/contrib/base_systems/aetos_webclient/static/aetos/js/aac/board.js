/*
 * Aetos picture communication board and sentence strip.
 * Addendum A.64, A.65, A.66, A.67, A.68.
 *
 * NOT REVIEWED AAC SUPPORT. See the header of `concepts.js` and A.94.
 *
 * A board of concepts; pressing one appends it to a sentence strip; the strip
 * is previewed as text and then sent as an ordinary game command.
 *
 * KEYBOARD OPERABLE IS NOT A FEATURE HERE, IT IS THE REQUIREMENT (A.66).
 *
 * Add, remove, move left, move right, clear, preview and send are all buttons.
 * Drag-and-drop is not implemented at all -- A.66 permits it as an addition but
 * forbids requiring it, and the population most likely to use a communication
 * board includes people for whom dragging is difficult or impossible. Building
 * the pointer version first is how a keyboard path ends up as an afterthought
 * that nobody tests.
 *
 * THE PREVIEW IS NOT A CONFIRMATION DIALOG (A.67).
 *
 * It exists because a wrong concept-to-text mapping would otherwise speak for
 * the player, in public, under their name, without them seeing what was said.
 * That is the specific harm this whole subsystem exists to prevent, so the
 * preview shows the exact text, and offers Send, Edit text, and Cancel. Edit
 * text matters as much as the other two: the player is the authority on what
 * they meant, and the board is a keyboard, not a translator.
 *
 * IT SENDS ORDINARY COMMANDS (A.68, blueprint 2.4).
 *
 * `say I want help` goes through the same seam as anything typed. The server
 * needs no AAC subsystem, is not told the player uses one, and applies every
 * lock, cooldown and rule exactly as usual. A board that bypassed a mute would
 * be a board that got somebody into trouble.
 */

(function (window, document) {
    "use strict";

    //: How many concepts a strip may hold. Long enough for a real sentence,
    //: short enough that clearing it is not a chore.
    var MAX_STRIP = 12;

    function createBoard(services) {
        var settings = services || {};
        var symbols = settings.symbols || null;
        var preferences = settings.preferences || null;
        var announce = settings.announce || function () {};
        var sendCommand = settings.sendCommand || function () { return false; };
        var dialog = settings.dialog || null;

        var strip = [];
        var activeCategory = "common";
        var stripEl = null;
        var gridEl = null;

        function showText() {
            if (!preferences || typeof preferences.value !== "function") {
                return true;
            }
            return preferences.value("aac.showTextWithSymbols", true) !== false;
        }

        /* --- The strip ---------------------------------------------------- */

        function add(conceptId) {
            var concept = window.AetosConcepts.find(conceptId);
            if (!concept || strip.length >= MAX_STRIP) {
                return null;
            }
            strip.push(concept);
            renderStrip();
            // Announced as the word, not as "button pressed": what matters is
            // what the sentence now says.
            announce(concept.label + ". " + currentText(), { category: "system" });
            return concept;
        }

        function removeAt(index) {
            if (index < 0 || index >= strip.length) {
                return false;
            }
            var removed = strip.splice(index, 1)[0];
            renderStrip();
            announce("Removed " + removed.label + ". " + (currentText() || "Empty."),
                { category: "system" });
            return true;
        }

        /*
         * Move a concept along the strip.
         *
         * Word order is meaning. "You give me" and "me give you" are different
         * sentences, and a player who put a word in the wrong place needs to
         * fix it without rebuilding the whole thing from scratch.
         */
        function move(index, offset) {
            var target = index + offset;
            if (index < 0 || index >= strip.length || target < 0 || target >= strip.length) {
                return false;
            }
            var moved = strip[index];
            strip[index] = strip[target];
            strip[target] = moved;
            renderStrip();
            announce(currentText(), { category: "system" });
            return true;
        }

        function clear() {
            strip = [];
            renderStrip();
            announce("Cleared.", { category: "system" });
            return true;
        }

        function currentText() {
            return window.AetosConcepts.toText(strip);
        }

        /* --- Sending ------------------------------------------------------ */

        /*
         * The command a sentence becomes.
         *
         * A single concept carrying its own template is sent as that command --
         * "North" means go north, not say the word "north". Everything else is
         * speech, through whatever command the player has chosen.
         *
         * Both are ordinary commands. Neither is special-cased anywhere in the
         * client or the server.
         */
        function buildCommand() {
            if (strip.length === 1 && strip[0].commandTemplate) {
                return strip[0].commandTemplate;
            }
            var verb = (preferences && preferences.value("aac.sayCommand", "say")) || "say";
            return verb + " " + currentText();
        }

        /*
         * Preview, then send.  A.67.
         *
         * Never sends directly. The whole point is that the player sees the
         * exact text before anybody else does.
         */
        function preview() {
            if (!strip.length) {
                announce("Nothing to send.", { category: "system", priority: "important" });
                return null;
            }
            var command = buildCommand();

            if (!dialog) {
                // No dialog available: send nothing rather than send unseen.
                announce("Cannot preview: " + command, {
                    category: "system", priority: "important"
                });
                return null;
            }

            var body = document.createElement("div");

            var heading = document.createElement("p");
            heading.className = "aetos-dialog__description";
            heading.textContent = "This will be sent to the game exactly as written:";
            body.appendChild(heading);

            var shown = document.createElement("p");
            shown.className = "aetos-aac__preview";
            shown.textContent = command;
            body.appendChild(shown);

            dialog.open({
                title: "Send this?",
                content: body,
                submitLabel: "Send",
                fields: [],
                extraActions: [
                    {
                        // The player is the authority on what they meant. A
                        // board is a keyboard, not a translator.
                        label: "Edit text",
                        run: function () { editText(command); }
                    }
                ],
                onSubmit: function () {
                    send(command);
                }
            });
            return command;
        }

        function editText(command) {
            if (!dialog) {
                return null;
            }
            dialog.open({
                title: "Edit before sending",
                description: "Change anything you like. It is sent exactly as it reads.",
                fields: [{ name: "command", label: "Command to send", value: command }],
                onSubmit: function (values) {
                    send(values.command);
                }
            });
            return command;
        }

        function send(command) {
            var text = String(command || "").trim();
            if (!text) {
                return false;
            }
            var sent = sendCommand(text);
            if (sent) {
                clear();
            } else {
                // Honestly reported. A board that cleared itself on a failed
                // send would have thrown away a sentence somebody spent a
                // minute building.
                announce("Could not send. Your sentence is still here.", {
                    category: "system", priority: "important"
                });
            }
            return sent;
        }

        /* --- Rendering ---------------------------------------------------- */

        function conceptButton(concept) {
            var button = document.createElement("button");
            button.type = "button";
            button.className = "aetos-aac__key";
            button.setAttribute("data-aetos-concept", concept.id);

            var symbol = symbols ? symbols.getSymbol(concept) : null;
            if (symbol) {
                var image = document.createElement("img");
                image.src = symbol.src;
                /*
                 * Empty alt when the label is shown beside it.
                 *
                 * Otherwise a screen reader announces the word twice -- once
                 * from the image and once from the text -- which on a board of
                 * sixty keys is sixty duplications to listen through.
                 */
                image.alt = showText() ? "" : symbol.alt;
                image.className = "aetos-aac__symbol";
                button.appendChild(image);
            }

            if (showText() || !symbol) {
                var label = document.createElement("span");
                label.className = "aetos-aac__label";
                label.textContent = concept.label;
                button.appendChild(label);
            }

            /*
             * `adapt-symbol` only where a verified concept id exists.  A.61.
             *
             * Every bundled concept has `waiAdaptConcept: null`, so this
             * currently emits nothing at all. It is here so that a pack or a
             * game supplying verified ids gets the attribute for free, and so
             * that nobody later adds invented ids to make the attribute appear.
             */
            if (concept.waiAdaptConcept) {
                button.setAttribute("adapt-symbol", concept.waiAdaptConcept);
            }

            button.addEventListener("click", function () { add(concept.id); });
            return button;
        }

        function renderStrip() {
            if (!stripEl) {
                return;
            }
            stripEl.textContent = "";

            if (!strip.length) {
                var empty = document.createElement("li");
                empty.className = "aetos-aac__strip-empty";
                empty.textContent = "Your sentence will appear here.";
                stripEl.appendChild(empty);
                return;
            }

            strip.forEach(function (concept, index) {
                var item = document.createElement("li");
                item.className = "aetos-aac__strip-item";

                var word = document.createElement("span");
                word.className = "aetos-aac__strip-word";
                word.textContent = concept.label;
                item.appendChild(word);

                /*
                 * One control per operation, each naming the word it acts on.
                 *
                 * "Left" repeated five times down a strip is indistinguishable
                 * when tabbed through, and this is the surface where getting
                 * the wrong one means saying something you did not mean.
                 */
                [
                    { label: "<", action: "Move left", run: function () { move(index, -1); } },
                    { label: ">", action: "Move right", run: function () { move(index, 1); } },
                    { label: "x", action: "Remove", run: function () { removeAt(index); } }
                ].forEach(function (control) {
                    var button = document.createElement("button");
                    button.type = "button";
                    button.className = "aetos-aac__strip-button";
                    button.textContent = control.label;
                    button.setAttribute("aria-label", control.action + ": " + concept.label);
                    button.addEventListener("click", control.run);
                    item.appendChild(button);
                });

                stripEl.appendChild(item);
            });
        }

        function renderGrid() {
            if (!gridEl) {
                return;
            }
            gridEl.textContent = "";
            window.AetosConcepts.byCategory(activeCategory).forEach(function (concept) {
                gridEl.appendChild(conceptButton(concept));
            });
        }

        function selectCategory(id) {
            activeCategory = id;
            renderGrid();
            return id;
        }

        return {
            id: "aac",
            accessibility: {
                landmarkLabel: "Picture communication",
                heading: "Talk",
                description:
                    "Build a sentence from words and pictures, see it, then send it.",
                keyboardOperable: true,
                // Nothing here changes on its own; it changes when the player
                // presses something.
                liveUpdates: false,
                graphicalOnly: false,
                textAlternative: null
            },
            displayName: "Talk",
            description: "A picture and word board for composing what you want to say.",
            builtin: true,
            defaultRegion: "bottom",
            defaultSize: { height: 300 },
            subscriptions: [],

            mount: function (context) {
                context.element.textContent = "";

                /* The strip comes first in the DOM, above the board.

                   Reading order matters more than visual order here: the
                   sentence being built is the thing a player needs to check,
                   and putting sixty keys before it means tabbing past all of
                   them to reach what you just said. */
                var stripSection = document.createElement("div");
                stripSection.className = "aetos-aac__strip-section";

                var stripLabel = document.createElement("h3");
                stripLabel.className = "aetos-dialog__subheading";
                stripLabel.textContent = "Your sentence";
                stripSection.appendChild(stripLabel);

                stripEl = document.createElement("ul");
                stripEl.className = "aetos-aac__strip";
                stripEl.setAttribute("aria-label", "Your sentence");
                stripSection.appendChild(stripEl);

                var actions = document.createElement("div");
                actions.className = "aetos-aac__actions";
                [
                    { label: "Preview and send", run: preview },
                    { label: "Clear", run: clear }
                ].forEach(function (action) {
                    var button = document.createElement("button");
                    button.type = "button";
                    button.className = "aetos-list__button";
                    button.textContent = action.label;
                    button.addEventListener("click", action.run);
                    actions.appendChild(button);
                });
                stripSection.appendChild(actions);
                context.element.appendChild(stripSection);

                var tabs = document.createElement("div");
                tabs.className = "aetos-aac__categories";
                tabs.setAttribute("role", "group");
                tabs.setAttribute("aria-label", "Word categories");
                window.AetosConcepts.CATEGORIES.forEach(function (category) {
                    var button = document.createElement("button");
                    button.type = "button";
                    button.className = "aetos-list__button";
                    button.textContent = category.label;
                    button.setAttribute(
                        "aria-pressed", category.id === activeCategory ? "true" : "false"
                    );
                    button.addEventListener("click", function () {
                        selectCategory(category.id);
                        Array.prototype.forEach.call(tabs.children, function (other) {
                            other.setAttribute(
                                "aria-pressed",
                                other === button ? "true" : "false"
                            );
                        });
                    });
                    tabs.appendChild(button);
                });
                context.element.appendChild(tabs);

                gridEl = document.createElement("div");
                gridEl.className = "aetos-aac__grid";
                /*
                 * `role="group"` before the label, not decoration.
                 *
                 * `aria-label` on a plain <div> has no role to attach to, so
                 * it is prohibited -- and, worse, silently ignored: the grid
                 * was simply unlabelled, and the only sign was axe reporting
                 * `aria-prohibited-attr` as *incomplete* rather than as a
                 * violation. A group is right here because these are buttons
                 * in a container; the same role on a <ul> would orphan its
                 * list items, which is a mistake this client has already made
                 * twice.
                 */
                gridEl.setAttribute("role", "group");
                gridEl.setAttribute("aria-label", "Words");
                context.element.appendChild(gridEl);

                renderStrip();
                renderGrid();
                return context.element;
            },

            destroy: function () {
                stripEl = null;
                gridEl = null;
            },

            // Exposed for the shell and for tests.
            add: add,
            removeAt: removeAt,
            move: move,
            clear: clear,
            preview: preview,
            send: send,
            buildCommand: buildCommand,
            currentText: currentText,
            selectCategory: selectCategory,
            sentence: function () { return strip.slice(); }
        };
    }

    window.AetosBoard = {
        createWidget: createBoard,
        MAX_STRIP: MAX_STRIP
    };

})(window, document);
