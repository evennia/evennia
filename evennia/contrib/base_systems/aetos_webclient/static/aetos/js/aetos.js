/*
 * Aetos Web Client -- shell bootstrap.
 *
 * Aetos never touches Evennia's transport. `evennia.js` is loaded unmodified by
 * the stock `webclient/base.html`, and Aetos drives it through its documented
 * public API only: Evennia.init(), Evennia.connect(), Evennia.msg() and the
 * emitter contract.
 *
 * Layering (blueprint section 7): widgets subscribe to state and never touch the
 * websocket, and outbound commands funnel through a single dispatcher. This file
 * establishes those seams while the shell is still small, so that later widgets
 * have somewhere correct to attach.
 */

(function (window, document) {
    "use strict";

    /* ------------------------------------------------------------------
     * Protocol constants
     *
     * These mirror `protocol.py`. They are duplicated rather than fetched
     * because they are needed to send the very first message, before any server
     * data has arrived. The Python tests assert the two stay in step.
     * ------------------------------------------------------------------ */
    var AETOS_PROTOCOL_VERSION = 1;

    var AETOS_MSG = {
        HELLO: "aetos_hello",
        MANIFEST: "aetos_manifest",
        SYNC: "aetos_sync",
        // A categorised game event (A.76). Optional for a game to send.
        EVENT: "aetos_event",
        REQUEST_SYNC: "aetos_request_sync",
        ERROR: "aetos_error"
    };

    // Delta message -> the store section it replaces.
    var AETOS_DELTA_SECTIONS = {
        aetos_state: "character",
        aetos_resources: "resources",
        aetos_room: "room",
        aetos_entities: "entities",
        aetos_map: "map",
        aetos_actions: "actions",
        aetos_effects: "effects",
        aetos_target: "target",
        aetos_media: "media",
        aetos_mode: "mode"
    };

    var AETOS_CAPABILITIES = [
        "manifest",
        "resources",
        "map",
        "actions",
        "media",
        "entities",
        "effects",
        "target",
        "mode"
    ];

    /* ------------------------------------------------------------------
     * AetosEmitter
     *
     * Evennia's DefaultEmitter keeps a single listener per event name --
     * `listeners[cmdname] = listener` overwrites any previous registration. That
     * suits the stock client, where one plugin owns each event, but Aetos needs
     * many widgets observing the same event independently.
     *
     * Evennia.init() accepts a replacement emitter, so Aetos supplies one with
     * the same emit/on/off surface plus multi-subscriber fan-out. This is an
     * additive use of a documented extension point, not a patch.
     * ------------------------------------------------------------------ */
    function AetosEmitter() {
        var listeners = {};

        function on(cmdname, listener) {
            if (typeof listener !== "function") {
                return function () {};
            }
            if (!listeners[cmdname]) {
                listeners[cmdname] = [];
            }
            listeners[cmdname].push(listener);
            return function unsubscribe() {
                off(cmdname, listener);
            };
        }

        function off(cmdname, listener) {
            if (!listeners[cmdname]) {
                return;
            }
            if (!listener) {
                delete listeners[cmdname];
                return;
            }
            listeners[cmdname] = listeners[cmdname].filter(function (entry) {
                return entry !== listener;
            });
        }

        // One misbehaving widget must never stop the others from receiving an
        // event, so each handler is isolated.
        function dispatch(handlers, callArgs, cmdname) {
            handlers.slice().forEach(function (handler) {
                try {
                    handler.apply(null, callArgs);
                } catch (err) {
                    window.console.error("Aetos: listener for " + cmdname + " threw", err);
                }
            });
        }

        function emit(cmdname, args, kwargs) {
            var handlers = listeners[cmdname];
            if (handlers && handlers.length) {
                dispatch(handlers, [args, kwargs], cmdname);
                return;
            }
            var fallback = listeners["default"];
            if (fallback && fallback.length) {
                dispatch(fallback, [cmdname, args, kwargs], cmdname);
            }
        }

        return { emit: emit, on: on, off: off };
    }

    /* ------------------------------------------------------------------
     * Command dispatcher
     *
     * Every outbound command passes through here (blueprint section 7). Aetos is
     * never authoritative: this sends exactly the "text" payload a player typing
     * the command by hand would send, so locks, cooldowns and permissions apply
     * identically.
     * ------------------------------------------------------------------ */
    function CommandDispatcher(evennia, services) {
        var settings = services || {};
        /*
         * Send one command, or say honestly that it did not go.
         *
         * Until M24 this called `evennia.msg` unconditionally and returned
         * `true` regardless. Evennia's transport does not buffer: a
         * `websocket.send` on a closed socket throws or is dropped, and
         * nothing is delivered on reconnect. So a command typed during a
         * disconnect was **reported as sent**, recorded in the capture as
         * sent, and recorded by the orientation trail as sent -- while
         * having done nothing at all.
         *
         * **Aetos deliberately does not queue it for later.** A player who
         * typed "attack the dragon" during a thirty-second dropout may be
         * somewhere else entirely by the time the socket returns, and
         * replaying it would execute a decision they made about a situation
         * that no longer exists. Saying it did not send leaves the choice
         * with them, which is the only place it belongs.
         */
        function send(commandText) {
            var text = (commandText || "").trim();
            if (!text) {
                return false;
            }
            if (typeof settings.isConnected === "function" && !settings.isConnected()) {
                return false;
            }
            try {
                evennia.msg("text", [text], {});
            } catch (err) {
                // A socket that closed between the check and the call. Rare,
                // and still not something to report as success.
                return false;
            }
            return true;
        }
        return { send: send };
    }

    /* ------------------------------------------------------------------
     * Sanitiser
     *
     * Evennia renders server-side ANSI/xterm colour into HTML before it reaches
     * the client, so the "text" payload legitimately contains markup. It cannot
     * simply be inserted as text (colour codes would show as literal tags), and
     * it must not be inserted via innerHTML either -- game content can carry
     * anything a builder or another player was able to type.
     *
     * So Aetos parses the payload in an inert document and rebuilds it from an
     * allowlist. Unknown elements are replaced by their text content rather than
     * dropped, so nothing a game says is ever silently lost. Blueprint section 55.
     * ------------------------------------------------------------------ */
    var ALLOWED_TAGS = {
        BR: [],
        SPAN: ["class"],
        DIV: ["class"],
        P: ["class"],
        B: [],
        STRONG: [],
        I: [],
        EM: [],
        U: [],
        CODE: [],
        PRE: [],
        H1: [], H2: [], H3: [], H4: [], H5: [], H6: [],
        UL: [], OL: [], LI: [],
        TABLE: [], THEAD: [], TBODY: [], TR: [], TD: [], TH: []
    };

    // Class names Evennia emits are simple tokens (e.g. "color-012"). Anything
    // else is discarded rather than trusted.
    var SAFE_CLASS = /^[A-Za-z0-9_ -]{0,200}$/;

    /*
     * How deep the rebuild will follow nesting before flattening the rest.
     *
     * M26. The rebuild is recursive, and the input is markup a builder or
     * another player was able to produce. Browsers cap their own parser's
     * nesting depth, so this is a second bound rather than the only one -- but
     * the cap differs between engines, and a stack overflow here throws inside
     * the output path, which is where the *game's own text* is being drawn.
     * Losing a line to a crash is a worse outcome than flattening one.
     *
     * 64 is far past any real formatting. Content below it is not discarded:
     * the deeper nodes are flattened to their text, which is the same thing
     * that already happens to any tag not on the allowlist.
     */
    var MAX_NESTING = 64;

    function sanitizeInto(sourceNode, targetNode, doc, depth) {
        var level = depth || 0;
        if (level > MAX_NESTING) {
            targetNode.appendChild(doc.createTextNode(sourceNode.textContent || ""));
            return;
        }
        var children = sourceNode.childNodes;
        for (var i = 0; i < children.length; i++) {
            var node = children[i];

            if (node.nodeType === 3) {
                targetNode.appendChild(doc.createTextNode(node.nodeValue));
                continue;
            }
            if (node.nodeType !== 1) {
                // Comments, processing instructions and anything else: ignored.
                continue;
            }

            // script/style carry executable or layout-breaking payloads and
            // their text content is not meaningful game output.
            if (node.tagName === "SCRIPT" || node.tagName === "STYLE") {
                continue;
            }

            var allowedAttrs = ALLOWED_TAGS[node.tagName];
            if (!allowedAttrs) {
                // Not allowed, but its text still belongs to the player.
                sanitizeInto(node, targetNode, doc, level + 1);
                continue;
            }

            var clean = doc.createElement(node.tagName.toLowerCase());
            allowedAttrs.forEach(function (attrName) {
                var value = node.getAttribute(attrName);
                if (attrName === "class" && value && SAFE_CLASS.test(value)) {
                    clean.setAttribute("class", value);
                }
            });
            sanitizeInto(node, clean, doc, level + 1);
            targetNode.appendChild(clean);
        }
    }

    function sanitizeHtml(markup) {
        // DOMParser builds an inert document: no scripts run, no resources load.
        var parsed = new window.DOMParser().parseFromString(
            "<body>" + String(markup) + "</body>",
            "text/html"
        );
        var fragment = document.createDocumentFragment();
        sanitizeInto(parsed.body, fragment, document, 0);
        return fragment;
    }

    /* ------------------------------------------------------------------
     * Console widget
     * ------------------------------------------------------------------ */
    function ConsoleWidget(rootElement, options) {
        var maxLines = (options && options.maxLines) || 5000;

        /*
         * Lines wait here until the next frame.
         *
         * M25. Until then every append read `scrollHeight`, added a node, and
         * wrote `scrollTop` -- three operations that, interleaved, force the
         * browser to lay out the whole scrollback once per line. Measured
         * against a full 5000-line console that cost **68ms per line**: a
         * 200-line burst -- one `help`, one long room, one busy combat round --
         * froze the client for thirteen seconds.
         *
         * The bound was doing the damage. `maxLines` exists so a long session
         * stays responsive, and `scrollTop = scrollHeight` over a list held at
         * its maximum is the most expensive possible version of that write.
         * The cap kept memory flat and made latency quadratic.
         *
         * Batching turns it into one layout per frame regardless of how many
         * lines arrive in it, which is the rate the player can actually read at
         * anyway.
         */
        var MAX_PENDING = 500;
        var pending = [];
        var flushQueued = false;

        function isScrolledToBottom() {
            var slack = 4;
            return rootElement.scrollHeight - rootElement.scrollTop -
                rootElement.clientHeight <= slack;
        }

        function schedule() {
            if (flushQueued) {
                return;
            }
            flushQueued = true;
            if (typeof window.requestAnimationFrame === "function") {
                window.requestAnimationFrame(flush);
            }
            /*
             * And a timer as well, not instead.
             *
             * A backgrounded tab does not run animation frames. Without this
             * the lines would sit in `pending` -- not lost, since the canonical
             * log has them, but absent from a console somebody may be reading
             * in another window with a screen reader. `flush` is idempotent, so
             * whichever arrives first does the work and the other returns.
             */
            window.setTimeout(flush, 100);
        }

        function flush() {
            flushQueued = false;
            if (!pending.length) {
                return;
            }
            // The one geometry read of the batch, taken before anything is
            // added -- so it answers "was the player at the bottom", which is
            // the question, rather than "is the console taller now", which is
            // not.
            var atBottom = isScrolledToBottom();
            var fragment = document.createDocumentFragment();
            for (var i = 0; i < pending.length; i++) {
                fragment.appendChild(pending[i]);
            }
            pending.length = 0;
            rootElement.appendChild(fragment);
            trim();
            if (atBottom) {
                rootElement.scrollTop = rootElement.scrollHeight;
            }
        }

        // Bounded scrollback (blueprint section 54): unbounded output is a
        // reliable way to make a long session unresponsive.
        function trim() {
            var overflow = rootElement.childElementCount - maxLines;
            for (var i = 0; i < overflow; i++) {
                rootElement.removeChild(rootElement.firstElementChild);
            }
        }

        /*
         * Append a line, optionally with presentation metadata.
         *
         * `presentation` carries what the display rules decided (E2). It never
         * carries what happened -- that is the canonical event, which the
         * console never sees and could not alter if it did.
         */
        function append(content, className, presentation) {
            var display = presentation || {};

            // Filtered out of this view. NOT deleted: the event is in the
            // canonical log, the history widget, Review Mode search and any
            // developer capture. The console simply does not draw it.
            if (display.hiddenInView) {
                return null;
            }

            var line = document.createElement("div");
            line.className = "aetos-console__line" + (className ? " " + className : "");

            if (display.collapsed) {
                line.classList.add("aetos-console__line--collapsed");
            }

            if (display.spans && display.spans.length) {
                // Highlights are rendered over the PLAIN text, because span
                // offsets were computed against plain text and applying them
                // to markup would slice through tags. The colour comes from a
                // theme token and the meaning from the label -- a highlight
                // that only changed colour would say nothing to a screen
                // reader or a colour-blind player.
                line.appendChild(renderHighlighted(
                    display.displayText, display.spans));
            } else if (display.substituted && display.displayText !== undefined) {
                /*
                 * A rule rewrote the words, so what is drawn is the rewrite --
                 * as plain text, because the offsets and the replacement were
                 * both computed against plain text.
                 *
                 * Gated on `substituted` rather than on `displayText !==
                 * content`. That comparison was true for every line containing
                 * any markup at all once `displayText` became the plain
                 * rendering, which is how the client came to draw all of its
                 * output without colour.
                 */
                line.textContent = display.displayText;
            } else {
                // Server content is rebuilt from an allowlist. innerHTML is
                // never used anywhere in Aetos.
                line.appendChild(sanitizeHtml(content));
            }

            pending.push(line);
            /*
             * A burst larger than a frame's worth flushes on its own rather
             * than growing without limit. It is also the only path that runs
             * when animation frames are unavailable altogether.
             */
            if (pending.length >= MAX_PENDING) {
                flush();
            } else {
                schedule();
            }
            return line;
        }

        /*
         * Build a line with highlighted ranges.
         *
         * Each highlighted range is a <mark> carrying an accessible name, so
         * assistive technology announces *why* it is marked rather than the
         * player being told nothing at all -- which is what a bare colour
         * change amounts to.
         */
        function renderHighlighted(plain, spans) {
            var fragment = document.createDocumentFragment();
            var cursor = 0;

            spans.forEach(function (span) {
                if (span.start > cursor) {
                    fragment.appendChild(
                        document.createTextNode(plain.slice(cursor, span.start)));
                }
                var mark = document.createElement("mark");
                mark.className = "aetos-console__mark aetos-console__mark--" + span.style;

                /*
                 * The label is visually hidden TEXT, not an aria-label.
                 *
                 * `<mark>` carries no implicit role, and `aria-label` on a
                 * roleless element is not reliably supported -- axe flags it as
                 * indeterminate, which is a fair description of what a screen
                 * reader will do with it. Real text in the DOM is announced by
                 * everything, everywhere, with no ARIA involved.
                 *
                 * So a highlight reads as "Enemy: goblin" rather than as a
                 * colour the player may not be able to see.
                 */
                if (span.label) {
                    var name = document.createElement("span");
                    name.className = "aetos-visually-hidden";
                    name.textContent = span.label + ": ";
                    mark.appendChild(name);
                }
                mark.appendChild(
                    document.createTextNode(plain.slice(span.start, span.end)));
                fragment.appendChild(mark);
                cursor = span.end;
            });

            if (cursor < plain.length) {
                fragment.appendChild(document.createTextNode(plain.slice(cursor)));
            }
            return fragment;
        }

        /*
         * `flush` is exported because a caller that needs the console to be
         * current *now* -- a test, a capture, anything that reads the DOM --
         * must be able to ask, rather than guessing at a frame boundary.
         */
        return { append: append, flush: flush };
    }

    /* ------------------------------------------------------------------
     * Announcer
     *
     * The single channel through which Aetos deliberately speaks to assistive
     * technology. The output console is NOT a live region: announcing every line
     * of game text would be unusable during combat spam or a long room listing.
     * Resource threshold announcements and command feedback come through here
     * instead, sparingly. Blueprint sections 48 and 100.
     *
     * Aetos never speaks over a screen reader by synthesising audio; this is
     * semantic output that the user's own assistive technology renders.
     * ------------------------------------------------------------------ */
    function Announcer(regionElement) {
        var lastMessage = null;

        function announce(message) {
            if (!regionElement || !message) {
                return;
            }
            // Re-setting identical text does not always re-trigger an
            // announcement, so nudge it when the message repeats.
            if (message === lastMessage) {
                regionElement.textContent = "";
            }
            lastMessage = message;
            regionElement.textContent = message;
        }

        return { announce: announce };
    }

    /* ------------------------------------------------------------------
     * Connection indicator
     * ------------------------------------------------------------------ */
    function ConnectionIndicator(container, label) {
        var STATES = {
            pending: "Connecting",
            open: "Connected",
            closed: "Disconnected"
        };

        var current = null;

        function set(state) {
            if (!container || !label || state === current) {
                return;
            }
            current = state;
            container.className = "aetos-connection aetos-connection--" + state;
            // Status is conveyed as text, not colour alone (blueprint section 45).
            // The element is role="status", so the change is announced once --
            // which is why repeat states are filtered out above.
            label.textContent = STATES[state] || state;
        }

        return { set: set };
    }

    /* ------------------------------------------------------------------
     * Boot
     * ------------------------------------------------------------------ */
    function boot() {
        var evennia = window.Evennia;
        if (!evennia) {
            window.console.error("Aetos: evennia.js not loaded; cannot start.");
            return;
        }

        var consoleEl = document.getElementById("aetos-console");
        var inputEl = document.getElementById("aetos-input");
        var sendEl = document.getElementById("aetos-send");
        var indicator = ConnectionIndicator(
            document.getElementById("aetos-connection"),
            document.getElementById("aetos-connection-label")
        );

        var consoleWidget = ConsoleWidget(consoleEl, {});
        // The announcer is created below, once storage exists: the
        // accessibility subsystem needs it for preferences and keybindings.
        var emitter = AetosEmitter();
        var store = window.AetosStore ? window.AetosStore.create() : null;

        // Local player data, scoped per game so two MUDs on one origin never
        // share notes or relationship tags (blueprint section 13).
        var gameName = (document.title || "").trim() || "evennia";
        var storage = window.AetosStorage
            ? window.AetosStorage.create({ gameName: gameName })
            : null;
        var profile = (storage && window.AetosProfile)
            ? window.AetosProfile.create(storage)
            : null;

        /*
         * The accessibility subsystem.  Addendum A.4.
         *
         * Owns the only two live regions in the client (A11Y-ANN-001), the
         * focus stack, the shortcut table and the player's accessibility
         * preferences.
         *
         * Created here rather than at the top of boot() because it needs
         * `storage`: preferences and keybindings are the player's data like any
         * other, so they live in the same per-game store and are exported,
         * counted and cleared with everything else (A.75). Nothing above this
         * line announces.
         */
        var accessibility = window.AetosAccessibility
            ? window.AetosAccessibility.create({
                root: document.documentElement,
                storage: storage,
                politeRegion: document.getElementById("aetos-announcer"),
                urgentRegion: document.getElementById("aetos-announcer-urgent"),
                // Where focus goes when the element that opened a dialog no
                // longer exists -- a note deleted from its own editor, say.
                focusFallback: function () {
                    return document.getElementById("aetos-input");
                }
            })
            : null;

        /*
         * Compatibility shim.
         *
         * Existing call sites pass a bare string and keep working. New ones may
         * pass a category and priority, which is what lets the manager honour a
         * player who has asked not to hear about combat.
         *
         * Kept as a shim rather than a rename so that A0 does not touch a
         * hundred call sites at once; they gain categories as each milestone
         * revisits its own widget.
         */
        var announcer = {
            announce: function (message, options) {
                return accessibility ? accessibility.announce(message, options) : null;
            }
        };

        // Local player data. None of this is ever sent to the game server
        // (blueprint section 2.3): there is no code path from here to the
        // command dispatcher.
        var relationships = (storage && window.AetosRelationships)
            ? window.AetosRelationships.create(storage)
            : null;
        var notes = (storage && window.AetosNotes)
            ? window.AetosNotes.create(storage)
            : null;
        var notesRefreshers = [];
        var historyRefreshers = [];

        evennia.init({ emitter: emitter });

        /*
         * The dispatcher asks the store whether we are connected.
         *
         * Read live rather than captured, because the answer changes and a
         * boolean taken at boot would be permanently "connecting".
         */
        var dispatcher = CommandDispatcher(evennia, {
            isConnected: function () {
                var connection = store ? store.get("connection") : null;
                // Absent state means the client has not learned otherwise yet.
                // Refusing on "unknown" would block the very first command of
                // a session, before any connection event has arrived.
                return !connection || connection.state !== "closed";
            }
        });

        /*
         * The inbound pipeline.  Addendum C.7, PIPE-001.
         *
         * Everything arriving from the server goes through here, in one order:
         *
         *     validate -> normalize -> state -> log -> automation
         *              -> presentation -> announce
         *
         * The ordering that matters is that **automation observes canonical
         * state and canonical text before presentation runs**. Before E0 the
         * console rendered first and triggers second, which worked only because
         * nothing yet transformed the text on its way to the console. The
         * moment E2 adds display filters, that order would mean a filtered line
         * never reaching the trigger that was watching for it -- an automation
         * silently breaking because of an unrelated display setting.
         */
        var canonicalLog = window.AetosCanonicalLog
            ? window.AetosCanonicalLog.create()
            : null;

        /*
         * Developer capture and replay.  E1.
         *
         * Idle until a developer starts it. Nothing is recorded by default:
         * a client that quietly accumulated a session log would be storing
         * game text nobody asked it to keep.
         */
        var capture = window.AetosCapture
            ? window.AetosCapture.create({
                protocolVersion: AETOS_PROTOCOL_VERSION,
                clientVersion: 1,
                manifest: function () { return store ? store.get("manifest") : null; }
            })
            : null;

        var pipeline = window.AetosPipeline
            ? window.AetosPipeline.create({
                store: store,
                canonicalLog: canonicalLog,
                /*
                 * Derive the plain-text rendering once, here.
                 *
                 * Everything that *matches* text needs it -- display rules,
                 * triggers, history search -- and deriving it separately in each
                 * of them is how they came to disagree, with the rules matching
                 * markup that the triggers had already learned to strip.
                 *
                 * Guarded on there being any markup at all, because the great
                 * majority of lines have none and parsing every one of them
                 * would put a DOM round trip back on the hot path M25 just took
                 * off it.
                 */
                normalize: function (validated) {
                    var text = validated.text || "";
                    var plain = text;
                    if (text.indexOf("<") !== -1) {
                        var holder = document.createElement("div");
                        holder.appendChild(sanitizeHtml(text));
                        /*
                         * A `<br>` contributes no text, so `textContent` alone
                         * welds the words on either side of it together:
                         * "need<br>help" reads "needhelp", and a room
                         * description becomes one run-on paragraph. Gary spotted
                         * it in a screenshot of the login banner.
                         *
                         * Replaced with a newline rather than a space, because
                         * the break carried structure -- the history panel and
                         * a braille display both want the line to end there.
                         */
                        Array.prototype.forEach.call(
                            holder.querySelectorAll("br"),
                            function (element) {
                                element.parentNode.replaceChild(
                                    document.createTextNode("\n"), element);
                            }
                        );
                        plain = holder.textContent;
                    }
                    return {
                        category: validated.category || "other",
                        originalText: text,
                        plainText: plain,
                        structuredData: validated.payload || null
                    };
                },
                applyState: function (payload) {
                    if (store) {
                        store.applySync(payload);
                    }
                },
                onError: function (failure) {
                    window.console.error(
                        "Aetos: " + failure.stage + " stage failed on " +
                        failure.eventId, failure.error);
                    // Recorded for the diagnostic report. The event id is kept
                    // and the payload is not -- the payload may contain game
                    // text, which a report has no business carrying.
                    if (diagnostics) {
                        diagnostics.record(
                            "pipeline:" + failure.stage, failure.error);
                    }
                }
            })
            : null;

        /*
         * Review Mode.  A.17, A.18.
         *
         * Reads the canonical log rather than the console, so a player can
         * review a line that a display rule has since hidden -- which is
         * exactly the case where reviewing matters.
         */
        var review = (canonicalLog && window.AetosReview)
            ? window.AetosReview.create({
                canonicalLog: canonicalLog,
                announcer: accessibility ? accessibility.announcer : null,
                announce: function (message, options) {
                    announcer.announce(message, options);
                }
            })
            : null;

        /*
         * Orientation and cognitive support.  A5.
         *
         * Created here because both need the store, the announcer and the
         * queue, and none of them needs a widget to exist. Orientation is
         * driven by authoritative room changes rather than typed movement
         * (A11Y-COG-003): a player who walked into a wall has not moved, and a
         * trail built from intentions would lead somewhere they have never
         * been.
         */
        var cognitive = (storage && window.AetosCognitive)
            ? window.AetosCognitive.create({
                storage: storage,
                store: store,
                announce: function (message, options) {
                    announcer.announce(message, options);
                }
            })
            : null;

        var orientation = window.AetosOrientation
            ? window.AetosOrientation.create({
                store: store,
                announce: function (message, options) {
                    announcer.announce(message, options);
                },
                // The queue already reports this; a second accessor could
                // disagree with it.
                queueState: function () {
                    return commandQueue ? commandQueue.state() : null;
                },
                queueRoute: function (steps) { return walkRoute(steps); },
                pinnedReminders: cognitive
                    ? function () { return cognitive.pinned(); }
                    : null
            })
            : null;

        if (cognitive) {
            cognitive.load();
        }

        /*
         * Progressive web app shell.  M20.
         *
         * Optional twice over: the game must have added Aetos's URLs for the
         * worker to exist, and the browser must support one. Both absences are
         * silent, because a player loses nothing they would notice -- the
         * client works identically and simply reloads from the network.
         */
        var pwa = window.AetosPwa
            ? window.AetosPwa.create({
                announce: function (message, options) {
                    announcer.announce(message, options);
                }
            })
            : null;

        if (pwa) {
            pwa.start();
        }

        /*
         * Touch gestures.  M20, A.57.
         *
         * Every one is a shortcut for a palette command, never the only way to
         * do something. A gesture cannot be discovered, listed, rebound or
         * announced, so a feature reachable only by swipe does not exist for
         * anyone using a screen reader, a switch device, or a desktop.
         */
        var gestures = window.AetosGestures
            ? window.AetosGestures.create({
                /*
                 * No palette here, deliberately. Whether a command exists is
                 * checked at registration in the shell, where the palette
                 * already is; passing it in as well would be a second route to
                 * the same fact, and the wiring tripwire caught exactly that.
                 */
                preferences: accessibility ? accessibility.preferences : null,
                announce: function (message, options) {
                    announcer.announce(message, options);
                }
            })
            : null;

        /*
         * Picture communication.  A7.
         *
         * An AAC *architecture*, not reviewed AAC support -- A.94 requires a
         * practitioner to review the concept organisation, the symbol
         * assumptions and the cognitive load before anybody claims the latter,
         * and that has not happened. See the header of `aac/concepts.js`.
         *
         * Aetos ships no symbol artwork (A.63), so the provider starts empty
         * and every control falls back to its text label until a player
         * installs a pack they are licensed to use.
         */
        var aacBoard = null;

        var symbolProvider = window.AetosSymbolProvider
            ? window.AetosSymbolProvider.create({
                preferences: accessibility ? accessibility.preferences : null
            })
            : null;

        /*
         * Themes.  M19.
         *
         * Created and applied before the widgets exist, because a theme that
         * arrives after the first paint is a flash of the wrong colours on
         * every load -- and for somebody using a dark theme because light
         * hurts, that is not a cosmetic problem.
         *
         * The accessibility layer applies its presets afterwards and wins, so
         * choosing a theme can never quietly undo an accommodation.
         */
        var themes = window.AetosThemes
            ? window.AetosThemes.create({
                storage: storage,
                announce: function (message, options) {
                    announcer.announce(message, options);
                }
            })
            : null;

        if (themes) {
            themes.load();
        }

        /*
         * Sound, and the text that must accompany it.  M18.
         *
         * The captions widget is created before the audio engine because the
         * engine writes into it. That ordering is the whole design in one
         * line: the text is not a by-product of playing a sound, it is the
         * primary channel, and it is emitted whether or not anything is
         * audible (A11Y-MEDIA-001).
         */
        var captionsWidget = window.AetosCaptions
            ? window.AetosCaptions.createWidget({
                preferences: accessibility ? accessibility.preferences : null,
                // Filled in below: the widget needs the engine for its
                // controls, and the engine needs the widget for its captions.
                audio: null
            })
            : null;

        var audio = window.AetosAudio
            ? window.AetosAudio.create({
                preferences: accessibility ? accessibility.preferences : null,
                announce: function (message, options) {
                    announcer.announce(message, options);
                },
                caption: function (text, item) {
                    if (captionsWidget) {
                        captionsWidget.record(text, item);
                    }
                }
            })
            : null;

        if (captionsWidget && audio) {
            // Through the setter, not by assigning a property: the widget's
            // controls close over their own `audio` variable, and setting a
            // field on the returned object would leave every one of them
            // inert while looking entirely correct.
            captionsWidget.setAudio(audio);
        }

        /*
         * Focus Mode.  A.47.
         *
         * Visual quieting: the client drops to its essentials and the rest is
         * hidden. Distinct from Quiet Mode, which is about *announcements* --
         * the two are separate because wanting a calmer screen and wanting
         * fewer interruptions are different needs, and somebody may want either
         * without the other.
         *
         * Nothing in the game can turn this on or off. A11Y-COG-007 makes that
         * explicit for workspace switching, and the same reasoning applies
         * here: a layout that rearranges itself under somebody is disorienting
         * for everyone and disabling for some.
         */
        function setFocusMode(on) {
            if (accessibility && accessibility.preferences) {
                // The preference is the single source of truth; the
                // accessibility layer reflects it onto the root, so the mode
                // survives a reload without the shell restoring anything.
                accessibility.preferences.update({
                    cognitive: { focusMode: on !== false }
                });
            }
            announcer.announce(
                on !== false
                    ? "Focus mode on. Extra panels are hidden."
                    : "Focus mode off.",
                { category: "system", priority: "important" }
            );
            return on !== false;
        }

        function focusModeIsOn() {
            return !!(accessibility && accessibility.preferences &&
                accessibility.preferences.value("cognitive.focusMode", false));
        }

        /*
         * Reorient: speak the summary and show it.
         *
         * One function rather than two call sites, because the keyboard
         * shortcut and the palette entry must do the same thing. An earlier
         * draft had the shortcut speak only, which meant a sighted player who
         * pressed it saw nothing happen at all.
         */
        function reorientNow() {
            if (!orientation) {
                return null;
            }
            var summary = orientation.speakReorientation();
            if (settings && settings.openOrientation) {
                settings.openOrientation();
            }
            return summary;
        }

        /*
         * Replay feeds records through `pipeline.ingest` -- the same seam the
         * websocket uses. There is deliberately no second path: a harness that
         * exercises different code from production tests the harness.
         */
        /*
         * Display rules.  E2.
         *
         * Presentation only. They produce metadata describing how a line should
         * look; they cannot touch the record, the store, or what a trigger saw.
         */
        var displayRules = (storage && window.AetosPresentationRules)
            ? window.AetosPresentationRules.create({ storage: storage })
            : null;
        if (displayRules) {
            displayRules.load();
        }

        var replay = (pipeline && window.AetosReplay)
            ? window.AetosReplay.create({ pipeline: pipeline })
            : null;

        if (pipeline) {
            /*
             * Automation first.
             *
             * Text triggers see the PLAIN text, never the markup: matching
             * against HTML would make a player's pattern depend on colour codes
             * they never see. They also see the *canonical* text rather than
             * whatever the console ended up displaying.
             */
            pipeline.observe("automation", function (event) {
                if (!triggers || !triggerCache.length) {
                    return;
                }
                if (event.category === "text" || event.originalText) {
                    // Derived at normalize now, so the triggers and the display
                    // rules are looking at the same string by construction
                    // rather than by two implementations agreeing.
                    triggers.onText(event.plainText || "", triggerCache);
                }
                if (event.structuredData) {
                    // Structured triggers are edge-triggered against state that
                    // has already been applied, two stages earlier.
                    triggers.onState(triggerCache);
                }
            });

            /*
             * The history widget redraws from the canonical log. Driven from
             * the pipeline rather than from a store subscription, because it
             * shows *events* and the store holds *state* -- correlated, but
             * not the same thing.
             *
             * Coalesced to once per frame (M25). A redraw filters the entire
             * canonical log -- up to 5000 events, each with a substring test
             * when a search is active -- and rebuilds a page of DOM. Doing that
             * per event made the cost of one line proportional to the length of
             * the session, so a burst late in an evening cost far more than the
             * same burst at the start. Once per frame is the rate the screen
             * updates at regardless.
             *
             * Not skipped when the widget is hidden, though that would save
             * more. The layout has no "became visible" signal to redraw on, and
             * a widget that quietly stops updating and has no way to be told to
             * start again is a worse bug than the one being fixed.
             */
            var historyRefreshQueued = false;

            function refreshHistory() {
                historyRefreshQueued = false;
                historyRefreshers.forEach(function (refresh) { refresh(); });
            }

            pipeline.observe("presentation", function () {
                if (historyRefreshQueued || !historyRefreshers.length) {
                    return;
                }
                historyRefreshQueued = true;
                if (typeof window.requestAnimationFrame === "function") {
                    window.requestAnimationFrame(refreshHistory);
                }
                // A backgrounded tab runs no animation frames; same reasoning
                // as the console. `refreshHistory` is safe to run twice.
                window.setTimeout(refreshHistory, 100);
            });

            // Presentation second, and handed a copy -- so nothing it does can
            // reach the record or the automation that already ran (PIPE-002).
            pipeline.observe("presentation", function (event) {
                if (!event.originalText) {
                    return;
                }
                /*
                 * Display rules run here and nowhere else.
                 *
                 * By this point the canonical log has already recorded the
                 * event and the automation stage has already seen it, so a
                 * filter cannot prevent a trigger firing and cannot erase
                 * anything. That ordering is E0's guarantee; this is the code
                 * that depends on it.
                 */
                var presentation = displayRules
                    ? displayRules.present(
                        event,
                        automationGroups ? automationGroups.activeMap() : null)
                    : null;
                consoleWidget.append(event.originalText, null, presentation);
            });

            /*
             * Game output reaches the announcer.  A14.
             *
             * THIS WAS MISSING, and it is the most serious defect this project
             * has shipped. Gary: *"when I turn screen reader on and then go back
             * to the game and type look nothing is read to me."*
             *
             * Everything needed for it existed. The pipeline has had an
             * `announce` stage since E0 and `events/pipeline.js` even carries a
             * comment about the console being "still announced if the player's
             * announcement settings" allow. The announcer has categories,
             * per-category preferences, priorities, flood control and review
             * mode. `screenReader.announceRoom` has defaulted to `true` since
             * A0. The two live regions are in the template.
             *
             * Nothing connected them. The only observer of the `announce` stage
             * was the capture recorder, so **no game text was ever announced**,
             * and the console is deliberately `aria-live="off"` -- so a screen
             * reader user got silence. Measured: emit a line of game text, and
             * the polite region still held the previous message.
             *
             * The console's `aria-live="off"` is right and stays. `role="log"`
             * carries an implicit polite region that would speak every line
             * including combat spam, with no categories, no thresholds and no
             * flood control. The announcer exists to make those decisions; it
             * was simply never given anything to decide about.
             *
             * No filtering here, deliberately. Category, priority, per-category
             * preferences, quiet mode, review mode and burst aggregation are all
             * the announcer's job, and a second opinion in this file is how two
             * places come to disagree about what a player asked for.
             */
            pipeline.observe("announce", function (event) {
                if (!announcer) {
                    return;
                }
                /*
                 * The plain text, never the markup -- a screen reader must not
                 * read span tags aloud. Falls back to the original only when
                 * normalize produced nothing, which is the same string for an
                 * event that carried no markup in the first place.
                 */
                var spoken = event.plainText || event.text || "";
                if (!spoken || !String(spoken).trim()) {
                    return;
                }
                announcer.announce(String(spoken), {
                    category: event.category || "other",
                    priority: event.priority || null
                });
            });

            /*
             * Capture observes the announce stage.  E1.
             *
             * Last, so a capture records what the client actually decided --
             * after state, after the log, after automation. Recording at the
             * transport instead would capture what arrived rather than what the
             * client made of it, and the bugs worth reproducing live in the
             * second thing.
             *
             * Registered after the announcer for the same reason: what the
             * client decided includes whether it spoke.
             */
            if (capture) {
                pipeline.observe("announce", function (event) {
                    capture.recordInbound(event);
                });
            }
        }

        emitter.on("text", function (args) {
            var payload = (args && args.length) ? args[0] : "";
            if (pipeline) {
                pipeline.ingest({ kind: "text", text: payload, category: "other" });
            } else {
                // No pipeline module: the console still works. Losing the
                // ordering guarantee is bad; losing the game output is worse.
                consoleWidget.append(payload);
            }
        });

        function updateConnection(state) {
            indicator.set(state);
            /*
             * The only category routed to the urgent region (A.15).
             *
             * A dropped connection is not merely news: everything else the
             * client is showing became potentially stale the moment it
             * happened, so a player needs to know before they act on it. That
             * is the bar for interrupting, and gameplay does not meet it.
             */
            if (capture) {
                capture.recordConnection(state);
            }
            if (state === "closed") {
                announcer.announce("Connection lost.", {
                    category: "connection", priority: "critical"
                });
            } else if (state === "open") {
                announcer.announce("Connected.", {
                    category: "connection", priority: "important"
                });
            }
            if (store) {
                store.merge("connection", { state: state });
            }

            /*
             * Mark everything on screen as no longer authoritative.  M24.
             *
             * The moment the connection drops, every panel is showing the world
             * as it was -- and looks exactly as it did when it was current.
             * A player glancing at their health bar during a dropout reads a
             * number presented as fact.
             *
             * An attribute rather than a rewrite of every widget: the panels
             * already render correctly, they are simply out of date, and
             * restating that once in the frame is both cheaper and more honest
             * than making sixteen widgets each invent their own way to say it.
             */
            var root = document.getElementById("aetos-root");
            if (root) {
                root.setAttribute(
                    "data-aetos-stale", state === "closed" ? "true" : "false"
                );
            }
            var notice = document.getElementById("aetos-stale-notice");
            if (notice) {
                // `hidden` rather than CSS, so it leaves the accessibility tree
                // entirely when connected -- a description that is always
                // present but sometimes false is worse than none.
                notice.hidden = state !== "closed";
            }
        }

        emitter.on("connection_open", function () {
            updateConnection("open");
            // The handshake is re-sent on every open, not only the first. After a
            // reconnect the server has no memory of this client's capabilities,
            // and the reply is a fresh authoritative sync (blueprint section 60).
            sendHello();
        });

        emitter.on("connection_close", function () {
            updateConnection("closed");
            // Allow the next connection to handshake afresh.
            helloSent = false;
            // The next connection has to ask again, and be watched again.
            manifestReceived = false;
            handshakeAttempts = 0;
            clearHandshakeWatch();
        });

        /* --- Aetos protocol ------------------------------------------- */

        // One hello per connection. Both the open event and the settle check
        // below can reach this, and the flag is cleared on close so that a
        // reconnect handshakes again.
        var helloSent = false;

        /*
         * Whether the server has ever answered the handshake on this
         * connection, and the timer watching for the case where it does not.
         *
         * M31. Found by installing into a clean game and opening the client
         * while the server was still starting: the websocket connects to the
         * **Portal**, which is up seconds before the Server behind it. The
         * Portal accepts the socket, creates no session, and the client sits
         * there reporting "Connected" with an empty console -- indefinitely,
         * because nothing ever tells it otherwise. A raw websocket opened a
         * minute later received the greeting immediately, which is what proved
         * where the silence was.
         *
         * Aetos cannot see this from the socket; `Evennia.isConnected()` is
         * true and honest, because the socket really is open. It *can* see it
         * from its own protocol: it sends a hello and expects a manifest.
         * Silence there means connected to a Portal with nothing behind it.
         *
         * This is the M24 family again -- the client presenting something as
         * true that it had no way to know was still true -- and the answer is
         * the same one: say so.
         */
        var HANDSHAKE_TIMEOUT_MS = 8000;
        var HANDSHAKE_ATTEMPTS = 4;
        var manifestReceived = false;
        var handshakeTimer = null;
        var handshakeAttempts = 0;

        function clearHandshakeWatch() {
            if (handshakeTimer !== null) {
                window.clearTimeout(handshakeTimer);
                handshakeTimer = null;
            }
        }

        /*
         * Re-send the handshake, or give up and say so.
         *
         * Retrying is safe here in a way that retrying a *command* is not
         * (see M24): a hello asks a question and changes nothing, so a second
         * one cannot execute a decision the player has since moved past. It
         * also makes the client heal itself the moment the server finishes
         * starting, which is the common case by far.
         *
         * Bounded rather than forever. A client quietly retrying for an hour
         * looks exactly like a client that is working.
         */
        function watchHandshake() {
            clearHandshakeWatch();
            handshakeTimer = window.setTimeout(function () {
                handshakeTimer = null;
                if (manifestReceived) {
                    return;
                }
                if (handshakeAttempts < HANDSHAKE_ATTEMPTS) {
                    if (handshakeAttempts === 0) {
                        announcer.announce(
                            "Connected, but the game has not answered yet. It may still "
                            + "be starting.",
                            { category: "connection", priority: "important" }
                        );
                    }
                    handshakeAttempts += 1;
                    helloSent = false;
                    sendHello();
                    return;
                }
                announcer.announce(
                    "Connected, but the game is not answering. Reloading the page may "
                    + "help.",
                    { category: "connection", priority: "critical" }
                );
            }, HANDSHAKE_TIMEOUT_MS);
        }

        function sendHello() {
            if (helloSent) {
                return;
            }
            helloSent = true;
            evennia.msg(AETOS_MSG.HELLO, [], {
                protocol: AETOS_PROTOCOL_VERSION,
                client: "aetos",
                capabilities: AETOS_CAPABILITIES.slice()
            });
            watchHandshake();
        }

        emitter.on(AETOS_MSG.MANIFEST, function (args, kwargs) {
            // The question the handshake watch was waiting on has an answer.
            manifestReceived = true;
            handshakeAttempts = 0;
            clearHandshakeWatch();
            if (store) {
                store.set("manifest", kwargs || {});
            }
            // The manifest tells us the server is listening; ask for state so the
            // first paint is populated rather than empty.
            requestSync();
            // Widgets are gated on manifest capabilities, so they mount only now.
            mountWidgets();
            reloadTriggers();
        });

        emitter.on(AETOS_MSG.ERROR, function (args, kwargs) {
            var detail = kwargs || {};
            window.console.error(
                "Aetos: server reported an error during " + (detail.stage || "?") +
                ": " + (detail.message || "unknown"));
        });

        /*
         * A categorised game event.  A.76, M17.
         *
         * Optional: a game that never sends one still works, and its output
         * arrives as ordinary text in the "other" category. What a category
         * buys is review by channel -- "previous tell" is only possible
         * because the game said which events were tells. Aetos will not work
         * that out by reading the words, on any game.
         */
        emitter.on(AETOS_MSG.EVENT, function (args, kwargs) {
            var detail = kwargs || {};
            if (!pipeline) {
                if (detail.text) {
                    consoleWidget.append(detail.text);
                }
                return;
            }
            pipeline.ingest({
                kind: "event",
                category: detail.category || "other",
                text: detail.text || "",
                plain: detail.plain || "",
                priority: detail.importance_hint || null,
                payload: detail.data || null
            });
        });

        emitter.on(AETOS_MSG.SYNC, function (args, kwargs) {
            if (pipeline) {
                // The pipeline applies state at stage 3 and notifies automation
                // at stage 5, so the ordering guarantee holds for structured
                // events exactly as it does for text.
                pipeline.ingest({
                    kind: "sync",
                    category: "room",
                    payload: kwargs || {}
                });
                observeLocation();
                return;
            }
            // Fallback, same order: state before automation.
            if (store) {
                store.applySync(kwargs || {});
            }
            observeLocation();
            if (triggers && triggerCache.length) {
                triggers.onState(triggerCache);
            }
        });

        // Delta messages map one-to-one onto store sections.
        Object.keys(AETOS_DELTA_SECTIONS).forEach(function (message) {
            var section = AETOS_DELTA_SECTIONS[message];
            emitter.on(message, function (args, kwargs) {
                if (store) {
                    store.set(section, kwargs || {});
                }
            });
        });

        /*
         * Media arrives two ways, and they are not the same thing.
         *
         * `{items: [...]}` is *state*: what should be playing while the player
         * is here. The engine diffs it, so a sync every few seconds does not
         * restart the music.
         *
         * `{play: [...]}` is an *event*: something happened once. It is never
         * diffed, because a door slamming twice is two sounds.
         *
         * Registered after the generic handler so the store still receives
         * ambient state -- other widgets read it -- while playback is handled
         * here.
         */
        emitter.on("aetos_media", function (args, kwargs) {
            if (!audio) {
                return;
            }
            var payload = kwargs || {};
            if (payload.play) {
                payload.play.forEach(function (item) {
                    if (item && item.category === "image") {
                        if (captionsWidget) {
                            captionsWidget.showImage(item);
                        }
                    } else {
                        audio.play(item);
                    }
                });
                return;
            }
            audio.sync(payload);
        });

        // Anything Aetos does not yet model is logged rather than dropped
        // silently, so a game is never mysteriously unable to reach the client.
        emitter.on("default", function (cmdname, args) {
            if (evennia.debug) {
                window.console.debug("Aetos: unhandled event " + cmdname, args);
            }
        });

        /* --- Command queue, routes and macros ---------------------------
         *
         * Blueprint section 28 requires every chained sequence to go through one
         * queue. Click-to-walk previously had its own walker; it now shares this
         * one, so the safety properties -- order, caps, stop-on-failure, pause on
         * disconnect -- are implemented once rather than re-derived per feature.
         */

        var commandQueue = window.AetosQueue ? window.AetosQueue.create({
            send: function (text) { return sendCommand(text); },
            isConnected: function () { return evennia.isConnected(); },
            announce: function (message) { announcer.announce(message); }
        }) : null;

        /*
         * Walking a route verifies each step structurally: did the room id
         * change? That needs no cooperation from the game and no parsing of
         * failure messages in any particular language.
         */
        function walkRoute(steps) {
            if (!commandQueue || !store) {
                return false;
            }
            return commandQueue.run(steps, {
                label: "Route",
                completionMessage: "Arrived.",
                verify: {
                    snapshot: function () {
                        return (store.get("room") || {}).id;
                    },
                    check: function (before, command) {
                        var after = (store.get("room") || {}).id;
                        if (after === before) {
                            return {
                                ok: false,
                                reason: "Route stopped: could not go " + command + "."
                            };
                        }
                        return { ok: true };
                    }
                }
            });
        }

        function cancelRoute() {
            return commandQueue ? commandQueue.cancel() : false;
        }

        /*
         * Macros run only when the game permits them. The manifest carries the
         * game's automation policy, and the client honours it rather than
         * quietly ignoring it (blueprint section 32).
         */
        function macrosAllowed() {
            var manifest = store ? store.get("manifest") : {};
            var automation = (manifest && manifest.automation) || {};
            // Absent policy means the server has not spoken yet. Defaulting to
            // allowed matches the documented default and avoids a hotbar that
            // flickers away while the handshake completes.
            return automation.macros !== false;
        }

        var macros = (storage && window.AetosMacros && commandQueue)
            ? window.AetosMacros.create({
                storage: storage,
                queue: commandQueue,
                announce: function (message) { announcer.announce(message); },
                isAllowed: macrosAllowed,
                confirm: function (options) {
                    if (!window.AetosDialog) {
                        options.onConfirm();
                        return;
                    }
                    window.AetosDialog.open({
                        title: options.title,
                        description: options.description,
                        submitLabel: "Run",
                        fields: [],
                        onSubmit: function () { options.onConfirm(); }
                    });
                }
            })
            : null;

        var macroRefreshers = [];

        /*
         * Aliases and triggers.
         *
         * Both are the player's own data and both are gated by the game's
         * automation policy, read from the manifest rather than assumed
         * (blueprint section 32).
         */
        function automationAllowed(name) {
            var manifest = store ? store.get("manifest") : {};
            var automation = (manifest && manifest.automation) || {};
            // Absent policy means the handshake has not completed yet; the
            // documented defaults apply until it does.
            return automation[name] !== false;
        }

        /*
         * Automation groups.  E3, C.15.
         *
         * Created before the engines that consult it, because each of them
         * takes it as a service -- `effective = rule.enabled AND
         * group.enabled` lives in one place rather than being reimplemented
         * five times.
         */
        var automationGroups = (storage && window.AetosAutomationGroups)
            ? window.AetosAutomationGroups.create({
                storage: storage,
                announce: function (message, options) {
                    announcer.announce(message, options);
                }
            })
            : null;
        if (automationGroups) {
            automationGroups.load();
        }

        var aliases = (storage && window.AetosAliases)
            ? window.AetosAliases.create({
                storage: storage,
                groups: automationGroups,
                isAllowed: function () { return automationAllowed("aliases"); },
                announce: function (message) { announcer.announce(message); }
            })
            : null;

        var triggers = (storage && window.AetosTriggers && commandQueue)
            ? window.AetosTriggers.create({
                storage: storage,
                groups: automationGroups,
                queue: commandQueue,
                store: store,
                isAllowed: function () { return automationAllowed("triggers"); },
                announce: function (message) { announcer.announce(message); }
            })
            : null;

        var timers = (storage && window.AetosTimers && commandQueue)
            ? window.AetosTimers.create({
                storage: storage,
                queue: commandQueue,
                announce: function (message) { announcer.announce(message); },
                // Timers act without the player at the keyboard, so they are
                // off unless the game opts in.
                isAllowed: function () { return automationAllowed("timers"); }
            })
            : null;

        /*
         * The scripting API.
         *
         * This object IS the sandbox boundary. A script can call these
         * functions and nothing else -- there is no property access in the
         * language and no way to name a host object, so anything absent from
         * here is unreachable rather than merely discouraged.
         *
         * Note what is deliberately missing: no file access, no network, no
         * DOM, no timers, no way to define a function. Blueprint section 33.
         */
        var scriptApi = {
            send: function (text) {
                // Scripts send ordinary commands through the same queue as
                // everything else, so the same caps and stop-on-failure apply.
                if (commandQueue) {
                    commandQueue.run([String(text)], { announceStart: false,
                                                       announceCompletion: false });
                }
                return true;
            },
            echo: function (text) {
                // The player's own console only. Never sent to the game.
                consoleWidget.append(String(text));
                return true;
            },
            resource: function (id) {
                var items = (store ? store.get("resources").items : []) || [];
                var found = items.filter(function (entry) { return entry.id === id; })[0];
                if (!found) {
                    return false;
                }
                if (typeof found.maximum === "number" && found.maximum > 0) {
                    var minimum = typeof found.minimum === "number" ? found.minimum : 0;
                    return (found.value - minimum) / (found.maximum - minimum);
                }
                return found.value;
            },
            room: function () {
                return (store ? store.get("room").name : "") || "";
            },
            target: function () {
                return (store ? store.get("target").name : "") || "";
            },
            get: function (key) {
                return scriptVariables[String(key)];
            },
            set: function (key, value) {
                scriptVariables[String(key)] = value;
                return value;
            }
        };

        var scriptVariables = {};

        var scripting = (storage && window.AetosScripting)
            ? window.AetosScripting.create({
                storage: storage,
                api: scriptApi,
                isAllowed: function () { return automationAllowed("scripting"); },
                announce: function (message) { announcer.announce(message); }
            })
            : null;

        /*
         * The unified validator.  E4.
         *
         * Created after every engine it consults: it takes them by value,
         * so an earlier position would have captured six hoisted
         * `undefined`s and reported "0 items checked" forever, silently.
         *
         * One place that answers "is this going to work" for every kind of
         * automation, so a player is not told two different things about the
         * same regular expression in two different dialogs.
         */
        /*
         * Diagnostic reports.  E5.
         *
         * Assembled from a fixed list of sources, none of which is the local
         * data store -- so there is no path by which a note, a macro or an
         * accessibility preference reaches a report. Excluded by construction
         * rather than by filtering.
         */
        var diagnostics = window.AetosDiagnostics
            ? window.AetosDiagnostics.create({
                store: store,
                canonicalLog: canonicalLog,
                // Accessors, not arrays: the registry does not exist yet, and
                // an array captured now would still be empty at report time.
                widgets: function () {
                    return registry
                        ? registry.all().map(function (d) { return d.id; })
                        : [];
                },
                modules: function () {
                    return Object.keys(window).filter(function (key) {
                        return key.indexOf("Aetos") === 0;
                    });
                }
            })
            : null;

        var validator = window.AetosValidator
            ? window.AetosValidator.create({
                triggers: triggers,
                aliases: aliases,
                timers: timers,
                scripting: scripting,
                displayRules: displayRules,
                macros: macros
            })
            : null;

        // Loaded once and refreshed on change, so evaluating a trigger against
        // a line of output is not an async storage read per line.
        var triggerCache = [];

        function reloadTriggers() {
            if (!triggers) {
                return window.Promise.resolve([]);
            }
            return triggers.all().then(function (list) {
                triggerCache = list;
                return list;
            });
        }


        function refreshHotbars() {
            macroRefreshers.forEach(function (refresh) {
                try {
                    refresh();
                } catch (err) {
                    // A widget may have been unmounted since it registered.
                }
            });
        }

        function editMacro(existing) {
            if (!macros || !window.AetosDialog) {
                return;
            }
            var macro = existing || { label: "", commands: [] };
            window.AetosDialog.open({
                title: existing ? "Edit macro" : "New macro",
                description:
                    "Up to " + window.AetosMacros.MAX_COMMANDS +
                    " commands, one per line. Each is sent exactly as if you " +
                    "typed it, so the game decides whether it works.",
                fields: [
                    { name: "label", label: "Button label", value: macro.label },
                    {
                        name: "commands",
                        label: "Commands (one per line)",
                        type: "textarea",
                        value: (macro.commands || []).join("\n")
                    },
                    {
                        name: "confirm",
                        label: "Ask before running",
                        type: "checkbox",
                        value: macro.confirm
                    }
                ],
                onSubmit: function (values) {
                    var commands = String(values.commands || "")
                        .split("\n")
                        .map(function (line) { return line.trim(); })
                        .filter(Boolean);
                    if (commands.length > window.AetosMacros.MAX_COMMANDS) {
                        announcer.announce(
                            "A macro holds at most " + window.AetosMacros.MAX_COMMANDS +
                            " commands. The extra ones were not saved.");
                    }
                    macros.save({
                        id: macro.id,
                        label: values.label || "Macro",
                        commands: commands,
                        confirm: values.confirm,
                        order: macro.order
                    }).then(function (saved) {
                        announcer.announce("Macro " + saved.label + " saved.");
                        refreshHotbars();
                    }).catch(function (err) {
                        announcer.announce(err.message);
                    });
                }
            });
        }

        /* --- Widget registry, layout and workspaces --------------------
         *
         * The surroundings widgets are ordinary registry definitions, mounted by
         * the layout manager. They have no privileged access -- a third-party
         * widget uses exactly the same contract, which is the only real proof
         * that the widget API is usable.
         */

        var registry = null;
        var layout = null;
        var workspaces = null;

        if (window.AetosWidgets && window.AetosLayout && window.AetosBuiltins) {
            registry = window.AetosWidgets.createRegistry();

            // Context menus for every listed entity. Bound to right-click, the
            // Context Menu key and Shift+F10 alike -- the latter two being the
            // ones a keyboard user can reach.
            //
            // Shared by every widget that lists entities, so an item in the room
            // and the same item in your pack offer the same menu.
            var attachMenu = window.AetosMenu ? function (element, entry) {
                window.AetosMenu.attach(element, function () {
                    return {
                        trigger: element,
                        label: entry.name || entry.direction || "entity",
                        // Game actions first, then the player's own. The two are
                        // separated in the menu because they differ in kind: one
                        // sends a command, the other edits data that never
                        // leaves this browser.
                        actions: (entry.actions || []).concat(localActionsFor(entry)),
                        sanitize: sanitizeHtml,
                        announce: function (m) { announcer.announce(m); },
                        onCommand: function (command) { sendCommand(command); }
                    };
                });
            } : null;

            window.AetosBuiltins.create({
                sanitize: sanitizeHtml,
                sendCommand: function (text) { return sendCommand(text); },
                attachMenu: attachMenu
            }).forEach(function (definition) {
                registry.register(definition);
            });

            // Inventory, equipment, target and effects. Only inventory is
            // ungated: `contents` is a stock Evennia concept, so it works on a
            // pristine game, while the other three describe systems Evennia
            // does not have.
            if (window.AetosCharacter) {
                window.AetosCharacter.create({
                    sanitize: sanitizeHtml,
                    sendCommand: function (text) { return sendCommand(text); },
                    attachMenu: attachMenu,
                    announce: function (message) { announcer.announce(message); },
                    // The player's own resource renderer, reused for a target so
                    // the two can never disagree about how a bar reads.
                    renderResource: window.AetosResources
                        ? window.AetosResources.renderResource
                        : null
                }).forEach(function (definition) {
                    registry.register(definition);
                });
            }

            // The resource widget announces threshold crossings, so it needs the
            // announcer. It is capability-gated, so a game exposing no resources
            // never sees it offered.
            if (window.AetosResources) {
                registry.register(window.AetosResources.createWidget({
                    announce: function (message) { announcer.announce(message); }
                }));
            }

            if (window.AetosMacros && macros) {
                registry.register(window.AetosMacros.createWidget({
                    macros: macros,
                    editMacro: editMacro,
                    isAllowed: macrosAllowed,
                    registerRefresh: function (fn) { macroRefreshers.push(fn); }
                }));
            }

            if (window.AetosNotes && notes) {
                registry.register(window.AetosNotes.createWidget({
                    notes: notes,
                    announce: function (m) { announcer.announce(m); },
                    editNote: function (note) { editNote(note, note.subject, note.kind); },
                    registerRefresh: function (fn) { notesRefreshers.push(fn); }
                }));
            }

            /*
             * The Current State View.  A.9.
             *
             * Registered after the widgets it summarises, so that if one of
             * them failed to load the snapshot simply has less to say rather
             * than erroring -- every section degrades to absent.
             */
            if (window.AetosHistory && canonicalLog) {
                registry.register(window.AetosHistory.createWidget({
                    canonicalLog: canonicalLog,
                    review: review,
                    registerRefresh: function (fn) { historyRefreshers.push(fn); }
                }));
            }

            if (captionsWidget) {
                registry.register(captionsWidget);
            }

            if (window.AetosBoard) {
                aacBoard = window.AetosBoard.createWidget({
                    symbols: symbolProvider,
                    preferences: accessibility ? accessibility.preferences : null,
                    dialog: window.AetosDialog,
                    announce: function (message, options) {
                        announcer.announce(message, options);
                    },
                    // The single outbound seam. A board that reached the
                    // transport directly would be one that bypassed a mute,
                    // a cooldown or a lock -- and got somebody into trouble
                    // for a sentence the game had already refused.
                    sendCommand: function (text) { return sendCommand(text); }
                });
                registry.register(aacBoard);

            }

            if (window.AetosStateView) {
                registry.register(window.AetosStateView.createWidget({
                    preferences: accessibility ? accessibility.preferences : null,
                    // The queue already reports this; there is no need for a
                    // second accessor that could disagree with it.
                    queueState: function () {
                        return commandQueue ? commandQueue.state() : null;
                    }
                }));
            }

            if (window.AetosMap) {
                registry.register(window.AetosMap.createWidget({
                    sendCommand: function (text) { return sendCommand(text); },
                    announce: function (message, options) {
                        announcer.announce(message, options);
                    },
                    queueRoute: function (steps) { return walkRoute(steps); },
                    // The player's own points of interest, which are notes with
                    // a room subject (M11). Browser-local, and the map is the
                    // only place they are useful -- so the map lists them
                    // beside the game's own rooms, clearly labelled as the
                    // player's rather than the game's.
                    listPois: notes
                        ? function () { return notes.search("", { poi: true }); }
                        : null
                }));
            }

            // The console lives in the template because it is the irreducible
            // core of the client -- a player must never be able to end up with
            // no output. It is relocated into the "main" region so the layout
            // adapter can order it relative to the widget panels; without this
            // the regions append after it and every sidebar lands on the right.
            var workspaceEl = document.getElementById("aetos-workspace");
            var consoleSection = document.getElementById("aetos-console-widget");

            layout = window.AetosLayout.createManager({
                registry: registry,
                store: store,
                storage: storage,
                adapter: window.AetosLayout.VanillaDockAdapter(workspaceEl),
                announce: function (message, options) {
                    announcer.announce(message, options);
                },
                /*
                 * A widget failure reaches the diagnostic report, so a bug
                 * report says which widget broke and where. Without this the
                 * only record is a console line the reporter has usually
                 * already scrolled past.
                 */
                onWidgetFailure: diagnostics
                    ? function (widgetId, phase, err) {
                        diagnostics.record("widget:" + widgetId + ":" + phase, err);
                    }
                    : null
            });

            /*
             * The word board follows its own preference.  A10.
             *
             * `aac.enabled` existed from A7 and **was read by nothing** -- the
             * checkbox offering it changed a stored value and no behaviour,
             * which is the "control that appears to work and changes nothing"
             * defect this project keeps finding. Caught by looking at the
             * screen: the board was still there in standard mode, where the
             * mode says it should not be.
             *
             * Registered HERE rather than beside the widget, because `layout`
             * does not exist yet at that point. `var` hoisting would have made
             * the guard false at priming time and the subscription would simply
             * never have been made -- the M21 shape, where a defensive check
             * turns a loud failure into a silent nothing.
             *
             * Driven from the *effective* preferences, so standard mode hides
             * it and accessible mode brings it back.
             */
            if (aacBoard && accessibility && accessibility.preferences) {
                accessibility.preferences.subscribe(function (current) {
                    applyBoardVisibility(current);
                });
            }

            var mainRegion = workspaceEl.querySelector('[data-aetos-region="main"]');
            if (mainRegion && consoleSection) {
                mainRegion.appendChild(consoleSection);
            }

            if (window.AetosWorkspaces) {
                workspaces = window.AetosWorkspaces.create({
                    layout: layout,
                    registry: registry,
                    storage: storage,
                    store: store,
                    announce: function (message) { announcer.announce(message); }
                });
                workspaces.bindKeys(document);
            }
        }

        /*
         * Widgets are added once the manifest has arrived, not at boot.
         *
         * Capability gating reads `manifest.features`, so adding widgets before
         * the handshake completes would evaluate every gate against an empty
         * manifest and silently drop capability-dependent widgets for the whole
         * session.
         */
        var widgetsMounted = false;

        function mountWidgets() {
            if (widgetsMounted || !layout || !registry || !workspaces) {
                return;
            }
            widgetsMounted = true;
            var saved = storage ? storage.get("workspaces", workspaces.DEFAULT_WORKSPACE) : null;
            window.Promise.resolve(saved).then(function (record) {
                if (record && record.layout) {
                    var result = layout.restore(record.layout);
                    if (result.restored) {
                        return;
                    }
                }
                // No usable saved layout: mount everything this game supports.
                registry.available(store ? store.get("manifest") : {}).forEach(function (def) {
                    layout.add(def.id);
                });
            }).then(function () {
                // Now that the widgets exist, the preference can reach them.
                applyBoardVisibility(null);
            });
        }

        /*
         * Apply `aac.enabled` to the word board's widget.
         *
         * Called from the preference subscription *and* once after the widgets
         * are mounted, because the subscription primes before any widget
         * exists: `layout.setVisible` on an unmounted widget returns false and
         * does nothing, so at boot the board kept whatever the saved layout
         * said. Measured -- the board was on screen in standard mode with the
         * preference off.
         *
         * Args:
         *     current (object): The effective preferences.
         */
        function applyBoardVisibility(current) {
            if (!aacBoard || !layout) {
                return;
            }
            var effective = current
                || (accessibility && accessibility.preferences
                    ? accessibility.preferences.effective()
                    : null);
            layout.setVisible(
                aacBoard.id,
                !!(effective && effective.aac && effective.aac.enabled)
            );
        }

        /* --- Command submission --------------------------------------- */

        var syncTimer = null;

        // A pristine Evennia game has no hooks calling into Aetos, so the client
        // asks for fresh state after acting. Debounced so a burst of commands
        // costs one request, not one per command.
        function requestSync() {
            if (syncTimer !== null) {
                window.clearTimeout(syncTimer);
            }
            syncTimer = window.setTimeout(function () {
                syncTimer = null;
                if (evennia.isConnected()) {
                    evennia.msg(AETOS_MSG.REQUEST_SYNC, [], {});
                }
            }, 200);
        }

        /*
         * Tell orientation and cognitive support where the player now is.
         *
         * Called after the store has been updated, never from the raw payload:
         * the store is what everything else reads, so a breadcrumb taken from
         * anywhere else could describe a room the rest of the client does not
         * believe in.
         *
         * Both modules ignore a repeat of the same room id, so calling this on
         * every sync is harmless.
         */
        function observeLocation() {
            var room = store ? store.get("room") : null;
            if (!room) {
                return;
            }
            if (orientation) {
                orientation.observeRoom(room);
            }
            if (cognitive) {
                cognitive.observeRoom(room);
            }
        }

        // The single outbound seam. Widgets, and later voice and macros, all go
        // through here rather than talking to the transport themselves.
        function sendCommand(text) {
            if (!dispatcher.send(text)) {
                /*
                 * Said once, at `important`, and not queued.
                 *
                 * A player who typed something and got no response would
                 * otherwise assume the game ignored them -- and on a slow
                 * dropout would keep typing, building up commands they believe
                 * are in flight.
                 */
                announcer.announce(
                    "Not connected. That was not sent.",
                    { category: "connection", priority: "important" }
                );
                return false;
            }
            // Recorded here rather than at each call site, because this is the
            // single point every command source converges on (C.11) -- keyboard,
            // button, macro, route, script, voice and AAC alike. A capture that
            // missed one of them would be a capture that could not reproduce the
            // session.
            //
            // Reached only when the command actually went, so a capture never
            // records something that was refused, and the orientation trail
            // never claims you sent something you did not.
            if (capture) {
                capture.recordOutbound(text);
            }
            if (orientation) {
                orientation.observeCommand(text);
            }
            requestSync();
            return true;
        }

        /* --- Local actions ---------------------------------------------
         *
         * Relationship tags and notes. These carry a `run` function rather than
         * a `command`, so the menu executes them locally and they never reach
         * the command dispatcher -- a structural guarantee rather than a promise
         * that nobody wired it up wrongly.
         */

        function refreshNoteWidgets() {
            notesRefreshers.forEach(function (refresh) {
                try {
                    refresh();
                } catch (err) {
                    // A widget may have been unmounted since it registered.
                }
            });
        }

        function editNote(existing, subject, kind) {
            if (!notes || !window.AetosDialog) {
                return;
            }
            var note = existing || { subject: subject, kind: kind, body: "", tags: [] };
            window.AetosDialog.open({
                title: existing ? "Edit note" : "Note on " + (subject || "something"),
                description: "Stored in this browser only. Never sent to the game.",
                fields: [
                    { name: "body", label: "Note", type: "textarea", value: note.body || "" },
                    {
                        name: "tags",
                        label: "Tags (comma separated)",
                        value: (note.tags || []).join(", ")
                    },
                    { name: "pinned", label: "Pin to top", type: "checkbox", value: note.pinned }
                ],
                onSubmit: function (values) {
                    notes.save({
                        id: note.id,
                        subject: note.subject || subject,
                        kind: note.kind || kind,
                        body: values.body,
                        tags: String(values.tags || "").split(",").map(function (tag) {
                            return tag.trim();
                        }).filter(Boolean),
                        pinned: values.pinned,
                        poi: note.poi,
                        created: note.created
                    }).then(function (saved) {
                        announcer.announce("Note on " + saved.subject + " saved.");
                        refreshNoteWidgets();
                    });
                }
            });
        }

        function localActionsFor(entry) {
            if (!relationships && !notes) {
                return [];
            }
            var name = entry.name || entry.direction;
            if (!name) {
                return [];
            }
            var kind = "object";
            if (entry.kind === "character") {
                kind = "character";
            } else if (entry.kind === "exit") {
                kind = "room";
            }
            var actions = [];

            // Relationship tags apply to people, not to items or exits.
            if (relationships && entry.kind === "character") {
                window.AetosRelationships.CATEGORIES.forEach(function (category) {
                    actions.push({
                        group: "local",
                        label: window.AetosRelationships.CATEGORY_LABELS[category],
                        run: function () {
                            relationships.setCategory(name, category).then(function () {
                                announcer.announce(
                                    name + " marked " +
                                    window.AetosRelationships.CATEGORY_LABELS[category] +
                                    ". This is private to you.");
                                requestSync();
                            });
                        }
                    });
                });
            }

            if (notes) {
                actions.push({
                    group: "local",
                    label: "Add note",
                    run: function () {
                        notes.forSubject(name, kind).then(function (existing) {
                            editNote(existing, name, kind);
                        });
                    }
                });
            }
            return actions;
        }

        function submit() {
            var raw = inputEl.value;
            if (!String(raw || "").trim()) {
                inputEl.focus();
                return;
            }
            inputEl.value = "";
            inputEl.focus();

            /*
             * Aliases expand only what the player TYPES.
             *
             * Deliberately not applied to commands from macros, menus, the map
             * or triggers. Expanding those would make an alias change silently
             * alter what a saved macro does, and would compound with the alias
             * recursion limit in ways nobody could reason about.
             */
            if (aliases) {
                aliases.expandInput(raw).then(function (expanded) {
                    sendCommand(expanded);
                });
            } else {
                sendCommand(raw);
            }
        }

        // The Edit Layout button and the keyboard drive one implementation, so
        // the two paths cannot diverge (blueprint section 16).
        var editButton = document.getElementById("aetos-edit-layout");
        if (editButton && workspaces) {
            editButton.addEventListener("click", function () {
                var editing = workspaces.toggleEditing();
                editButton.setAttribute("aria-pressed", editing ? "true" : "false");
            });
        } else if (editButton) {
            // Layout modules unavailable: hide the control rather than offering
            // a button that does nothing.
            editButton.hidden = true;
        }

        sendEl.addEventListener("click", submit);
        inputEl.addEventListener("keydown", function (event) {
            if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                submit();
            }
        });

        // Reflect the real socket state once it settles, in case the open event
        // fired before Aetos subscribed to it.
        window.setTimeout(function () {
            if (evennia.isConnected()) {
                updateConnection("open");
                sendHello();
            } else {
                updateConnection("closed");
            }
        }, 500);

        /* --- Settings and command palette -------------------------------
         *
         * The palette is the discoverability surface (blueprint section 36). A
         * keyboard shortcut nobody can find is not a feature, so every client
         * action registers here with a description -- including the ones that
         * also have a shortcut, so the shortcut becomes learnable.
         */

        var settings = (storage && window.AetosSettings && window.AetosDialog)
            ? window.AetosSettings.create({
                storage: storage,
                profile: profile,
                dialog: window.AetosDialog,
                aliases: aliases,
                triggers: triggers,
                timers: timers,
                scripting: scripting,
                groups: automationGroups,
                displayRules: displayRules,
                validator: validator,
                diagnostics: diagnostics,
                cognitive: cognitive,
                orientation: orientation,
                themes: themes,
                symbols: symbolProvider,
                pwa: pwa,
                reloadTriggers: reloadTriggers,
                gameName: gameName,
                announce: function (message) { announcer.announce(message); }
            })
            : null;

        /*
         * In-client help.
         *
         * Topics are gated on the same automation policy as the editors, so a
         * game that forbids scripting has no scripting topic -- documenting a
         * feature the player cannot use sends them looking for a button that is
         * not there.
         */
        var help = window.AetosHelp
            ? window.AetosHelp.create({
                isAllowed: automationAllowed,
                announce: function (message) { announcer.announce(message); }
            })
            : null;


        /*
         * Universal search needs a synchronous view of the player's notes.
         *
         * Notes live in IndexedDB and palette search runs on every keystroke,
         * so the shell keeps a snapshot and refreshes it whenever the palette
         * opens. Nothing else reads this: it exists only so that search can
         * answer immediately.
         */
        var noteSnapshot = [];

        function refreshNoteSnapshot() {
            if (!notes) {
                return;
            }
            notes.all().then(function (all) {
                noteSnapshot = all || [];
            }).catch(function () {
                // Search finds fewer things rather than failing.
            });
        }

        /*
         * Developer inspector.  M21, C.18.
         *
         * Created after `settings` because it reaches three actions that
         * already lived there -- the diagnostic report, the validator and
         * capture. It adds no capability of its own; what it adds is a place to
         * find them, which is the difference between a feature existing and a
         * feature existing for anybody but its author.
         */
        var inspector = window.AetosInspector
            ? window.AetosInspector.create({
                store: store,
                /*
                 * Passed directly, because by the time this runs the registry
                 * is already built -- it is populated several hundred lines
                 * above.
                 *
                 * The first version handed it over later through a setter, on
                 * the assumption that the inspector was created first. It was
                 * not, and `var` hoisting made the mistake silent: `inspector`
                 * existed and was `undefined`, so `if (inspector && ...)`
                 * skipped the call without a word and the panel reported
                 * "Registry: not available" forever.
                 *
                 * Worth naming what went wrong there, because the guard was
                 * mine and it was defensive: it turned a loud crash into a
                 * quiet wrong answer. A guard against a condition that should
                 * be impossible hides the bug that makes it possible.
                 */
                registry: registry,
                layout: layout,
                canonicalLog: canonicalLog,
                diagnostics: diagnostics,
                capture: capture,
                replay: replay,
                dialog: window.AetosDialog,
                announce: function (message, options) {
                    announcer.announce(message, options);
                },
                openDiagnostics: settings
                    ? function (includeOutput) {
                        return settings.openDiagnostics(includeOutput);
                    }
                    : null,
                validateAll: settings
                    ? function () { return settings.validateAll(); }
                    : null
            })
            : null;

        var palette = window.AetosPalette
            ? window.AetosPalette.create({
                announce: function (message) { announcer.announce(message); },
                onOpen: refreshNoteSnapshot
            })
            : null;

            /*
         * The accessibility panel.  A9.
         *
         * The options it shows are not new -- they are the A-track's, and all
         * of them are in Settings. What is new is that somebody can find them
         * without knowing they exist, which was the one thing granularity cost.
         */
        var accessibilityPanel = window.AetosAccessibilityPanel && accessibility
            ? window.AetosAccessibilityPanel.create({
                preferences: accessibility.preferences,
                announce: function (message, options) {
                    // Forwarded, not fixed at "normal": switching to standard
                    // mode announces at `important`, and swallowing that would
                    // mean the one message somebody needs to hear -- how to get
                    // back -- arrives in the quietest category there is.
                    accessibility.announce(message, options || { priority: "normal" });
                },
                focusManager: window.AetosFocusManager || null
            })
            : null;
        if (accessibilityPanel) {
            var a11yHost = document.getElementById("aetos-accessibility-host");
            var a11yToggle = document.getElementById("aetos-accessibility-toggle");
            if (a11yHost) {
                accessibilityPanel.attach(a11yHost, a11yToggle);
            }
        } else {
            var orphanToggle = document.getElementById("aetos-accessibility-toggle");
            if (orphanToggle) {
                // A control that does nothing is worse than an absent one.
                orphanToggle.hidden = true;
            }
        }

        if (palette) {
            // No self-binding: Ctrl+K is registered with the shortcut manager
            // below, so a player can see it, rebind it or turn it off (A.23).

            function addCommand(id, label, group, description, run, when, shortcut) {
                palette.register({
                    id: id, label: label, group: group, description: description,
                    run: run, when: when, shortcut: shortcut
                });
            }

            /* Accessibility */
            if (accessibilityPanel) {
                /*
                 * Two commands, because they are two things. The mode is the
                 * one with the shortcut, because it is the one somebody needs
                 * when they can no longer read the screen.
                 */
                addCommand("accessibility.mode", "Accessible mode on or off", "Accessibility",
                    "Switch between the standard interface and the accessible one. "
                        + "Nothing you chose is erased either way.",
                    function () { accessibilityPanel.setMode(); }, null, "Ctrl+Shift+A");
                addCommand("accessibility.options", "Display and accessibility options",
                    "Accessibility",
                    "Text size and sound in either mode; contrast, motion and "
                        + "announcements as well in accessible mode.",
                    function () { accessibilityPanel.toggleOptions(); });

                /*
                 * Text size directly, without opening anything.
                 *
                 * Gary: "having to zoom the browser is janky". Somebody who
                 * cannot read the screen should not have to read a settings
                 * panel first, so the two commands that fix it are searchable on
                 * their own -- and the palette itself scales with them.
                 */
                addCommand("text.larger", "Larger text", "Accessibility",
                    "Increase the size of everything in the client.",
                    function () { accessibilityPanel.adjustTextSize(0.15); });
                addCommand("text.smaller", "Smaller text", "Accessibility",
                    "Decrease the size of everything in the client.",
                    function () { accessibilityPanel.adjustTextSize(-0.15); });
                addCommand("text.reset", "Reset text size", "Accessibility",
                    "Back to the default size.",
                    function () { accessibilityPanel.adjustTextSize(null); });
            }

            /* Layout */
            if (workspaces) {
                addCommand("layout.edit", "Edit layout", "Layout",
                    "Move, resize, hide and restore widgets using the keyboard.",
                    function () { workspaces.toggleEditing(); }, null, "Ctrl+Shift+L");
                addCommand("layout.reset", "Reset layout", "Layout",
                    "Put every available widget back in its default place.",
                    function () { workspaces.resetLayout(); });
                addCommand("workspace.save", "Save workspace", "Layout",
                    "Store the current arrangement under its name.",
                    function () { workspaces.saveWorkspace(); });
            }

            /* Automation. Each entry hides itself when the game forbids it, so
               the palette never offers something that would then refuse. */
            if (macros) {
                addCommand("macro.new", "New macro", "Automation",
                    "A button that sends up to five commands.",
                    function () { editMacro(null); },
                    function () { return automationAllowed("macros"); });
            }
            if (settings && aliases) {
                addCommand("alias.new", "New alias", "Automation",
                    "Shorthand for something you type often.",
                    function () { settings.editAlias(null); },
                    function () { return automationAllowed("aliases"); });
            }
            if (settings && triggers) {
                addCommand("trigger.new", "New trigger", "Automation",
                    "Run commands when the game says something.",
                    function () { settings.editTrigger(null); },
                    function () { return automationAllowed("triggers"); });
            }
            if (settings && timers) {
                addCommand("timer.new", "New timer", "Automation",
                    "Run commands on a schedule.",
                    function () { settings.editTimer(null); },
                    function () { return automationAllowed("timers"); });
            }
            if (settings && scripting) {
                addCommand("script.new", "New script", "Automation",
                    "Write an Aetos Script.",
                    function () { settings.editScript(null); },
                    function () { return automationAllowed("scripting"); });
            }

            if (settings && diagnostics) {
                addCommand("diagnostics.report", "Diagnostic report", "Help",
                    "Describe this client for a bug report. Shows you everything " +
                    "before you share it.",
                    function () { settings.openDiagnostics(false); });
            }

            if (settings && validator) {
                addCommand("automation.validate", "Validate automation", "Automation",
                    "Check every trigger, alias, timer, script and rule you have.",
                    function () { settings.validateAll(); });
            }

            /* Automation groups and display rules */
            if (settings && automationGroups) {
                addCommand("groups.open", "Automation groups", "Automation",
                    "Switch related automation on and off together.",
                    function () { settings.openGroups(); });
                addCommand("group.new", "New automation group", "Automation",
                    "Create a group -- Combat, Crafting, whatever you need.",
                    function () { settings.editGroup(null); });
            }
            if (settings && displayRules) {
                addCommand("displayrule.new", "New display rule", "Automation",
                    "Highlight, replace, hide or collapse output. Never deletes it.",
                    function () { settings.editDisplayRule(null); });
            }

            /* Notes and local data */
            if (notes) {
                addCommand("note.new", "New note", "Notes",
                    "A private note, stored in this browser only.",
                    function () { editNote(null, "", "free"); });
            }
            if (settings) {
                addCommand("privacy.open", "Privacy and local data", "Privacy",
                    "See everything Aetos stores about you, export it, or delete it.",
                    function () { settings.openPrivacy(); });
                addCommand("profile.export", "Export profile", "Privacy",
                    "Download your layouts, macros, notes and settings as a file.",
                    function () { settings.exportProfile(); });
                addCommand("profile.import", "Import profile", "Privacy",
                    "Restore from an exported Aetos profile.",
                    function () { settings.importProfile(); });
            }

            /* Help. Registered first in its own group so it is the thing a
               lost player finds, and so the F1 shortcut becomes learnable. */
            if (help) {
                addCommand("help.open", "Help", "Help",
                    "Documentation for everything this client does, with examples.",
                    function () { help.open(null); }, null, "F1");
                help.topics().forEach(function (topic) {
                    addCommand("help." + topic.id, "Help: " + topic.title, "Help",
                        topic.summary,
                        function () { help.open(topic.id); });
                });
            }

            /* Review */
            if (review) {
                addCommand("review.toggle", "Review mode", "Review",
                    "Pause announcements and read back through what happened.",
                    function () { review.toggle(); }, null, "Ctrl+Shift+R");
                addCommand("review.prev.tell", "Previous tell", "Review",
                    "Jump back to the last thing someone said to you.",
                    function () { review.previous("tell"); });
                addCommand("review.next.tell", "Next tell", "Review",
                    "Jump forward to the next thing someone said to you.",
                    function () { review.next("tell"); });
                addCommand("review.latest", "Latest event", "Review",
                    "Jump to the most recent thing that happened.",
                    function () { review.latest(); });
            }

            /* Orientation.  A5.

               Grouped separately from Review because they answer different
               questions: Review is "what happened", orientation is "where am I
               now". Somebody who has lost their place usually wants the second
               and would have to read the whole of the first to get it. */
            if (orientation) {
                addCommand("orientation.reorient", "Where am I", "Orientation",
                    "Read back your location, exits, who is here and what you " +
                    "last did. Facts only -- Aetos never guesses what you were " +
                    "trying to do.",
                    function () { reorientNow(); }, null, "Ctrl+Shift+W");
                addCommand("orientation.trail", "How I got here", "Orientation",
                    "The rooms you have walked through this session.",
                    function () {
                        var trail = orientation.trail();
                        announcer.announce(
                            trail.length
                                ? trail.map(function (step) { return step.name; }).join(", ")
                                : "No movement recorded yet.",
                            { category: "system", priority: "important" }
                        );
                    });
                addCommand("orientation.walkback", "Walk back", "Orientation",
                    "Retrace your steps using ordinary movement commands. Stops " +
                    "wherever the game stops you.",
                    function () { orientation.walkBack(); });
            }
            if (cognitive && settings) {
                addCommand("reminder.new", "New reminder", "Orientation",
                    "A note to yourself, kept in this browser.",
                    function () {
                        settings.editReminder(store ? store.get("room") : null);
                    });
                addCommand("reminder.list", "Reminders and tasks", "Orientation",
                    "Everything you have asked to be reminded about.",
                    function () { settings.openReminders(); });
                addCommand("session.resume", "What did I miss", "Orientation",
                    "A short summary of where you left off.",
                    function () {
                        var card = cognitive.resumeCard(
                            !!(store && store.get("room") && store.get("room").name)
                        );
                        announcer.announce(
                            card.lines.length
                                ? card.lines.join(" ")
                                : "Nothing saved from last time.",
                            { category: "system", priority: "important" }
                        );
                    });
            }

            /* Comfort.  A.47, A.48.

               Both are toggles the player owns. Neither is ever changed by the
               game, and neither hides anything from the transcript -- they
               change what interrupts you and what is on screen, not what
               happened. */
            addCommand("focus.toggle", "Focus mode", "Comfort",
                "Hide everything except the game text and your input.",
                function () { setFocusMode(!focusModeIsOn()); });
            if (accessibility && accessibility.preferences) {
                addCommand("quiet.toggle", "Quiet mode", "Comfort",
                    "Stop routine announcements. Anything important still " +
                    "gets through, and nothing is removed from the transcript.",
                    function () {
                        var preferences = accessibility.preferences;
                        var now = preferences.value("cognitive.quietMode", false);
                        preferences.update({ cognitive: { quietMode: !now } });
                        announcer.announce(
                            now ? "Quiet mode off." : "Quiet mode on.",
                            { category: "system", priority: "important" }
                        );
                    });
            }

            if (audio) {
                addCommand("audio.stop", "Stop all sound", "Comfort",
                    "Silence everything immediately.",
                    function () { audio.stopAll(); });
                addCommand("audio.mute", "Mute all sound", "Comfort",
                    "Keep captions, drop the audio.",
                    function () {
                        var preferences = accessibility && accessibility.preferences;
                        if (!preferences) {
                            return;
                        }
                        var now = preferences.value("audio.muted", false);
                        preferences.update({ audio: { muted: !now } });
                        audio.applyVolumes();
                        announcer.announce(
                            now ? "Sound unmuted." : "Sound muted. Captions continue.",
                            { category: "system", priority: "important" }
                        );
                    });
            }

            if (workspaces) {
                addCommand("layout.simplified", "Simplified layout", "Layout",
                    "Four panels instead of a dozen. Nothing is removed -- " +
                    "everything is still here in the palette.",
                    function () { workspaces.applySimplifiedLayout(); });
            }

            if (symbolProvider && settings) {
                addCommand("aac.packs", "Symbol packs", "Comfort",
                    "Install pictures for the word board, and see which words " +
                    "a pack does not cover.",
                    function () { settings.openSymbolPacks(); });
            }

            if (aacBoard) {
                addCommand("aac.clear", "Clear my sentence", "Comfort",
                    "Empty the picture communication strip.",
                    function () { aacBoard.clear(); });
                addCommand("aac.send", "Preview and send my sentence", "Comfort",
                    "See exactly what will be sent, then send or edit it.",
                    function () { aacBoard.preview(); });
            }

            if (themes && settings) {
                addCommand("theme.choose", "Themes", "Comfort",
                    "Change colours. Your accessibility settings still win.",
                    function () { settings.openThemes(); });
                addCommand("theme.new", "New theme", "Comfort",
                    "Build your own palette, checked against WCAG contrast.",
                    function () { settings.editTheme(null); });
            }

            /*
             * Opening the palette, as a palette command.
             *
             * Circular-looking and genuinely needed. Ctrl+K has named
             * `palette.toggle` as the command it accelerates since A0, and no
             * such command existed -- so the shortcut pointed at nothing and
             * the rule "every shortcut names its palette command" was satisfied
             * in spelling only. M20's gesture guard found it, because that one
             * checks the command *resolves* rather than that a string is
             * present.
             *
             * It earns its place beyond tidiness: on a touch device there is no
             * Ctrl+K, so the up-swipe needs a real command to duplicate.
             */
            if (palette) {
                addCommand("palette.toggle", "Close the command palette", "Session",
                    "Also opens it, from a swipe or a shortcut.",
                    function () { palette.toggle(); });
            }

            if (inspector) {
                addCommand("developer.inspect", "Inspector", "Help",
                    "What this client believes: manifest, providers, widgets, " +
                    "state and recent events. Reads only what Aetos already has.",
                    function () { inspector.open(); });
            }

            if (capture) {
                addCommand("developer.capture", "Capture this session", "Help",
                    "Record everything for a bug report. Includes game text, " +
                    "so read it before sharing.",
                    function () { inspector.toggleCapture(); },
                    function () { return !!inspector; });
                addCommand("developer.capture.save", "Download capture", "Help",
                    "Save the recorded session to a file.",
                    function () { inspector.downloadCapture(); },
                    function () { return !!inspector && capture.records().length > 0; });
            }
            if (replay && inspector) {
                addCommand("developer.replay", "Replay a capture", "Help",
                    "Load a captured session and play it back through this " +
                    "client. Replaces your current state.",
                    function () { inspector.loadReplay(); });
            }

            if (pwa) {
                addCommand("app.install", "Install Aetos", "Session",
                    "Add this client to your device, so it opens like an app.",
                    function () { pwa.install(); },
                    function () { return pwa.canInstall(); });
                addCommand("app.update", "Apply the waiting update", "Session",
                    "Reload to use the new version. Nothing changes until you do.",
                    function () { pwa.applyUpdate(); },
                    function () { return pwa.updateAvailable(); });
            }

            /* Session */
            if (commandQueue) {
                addCommand("queue.cancel", "Stop queued commands", "Session",
                    "Cancel a running macro, route or script.",
                    function () { commandQueue.cancel(); },
                    function () { return commandQueue.isRunning(); });
            }
            addCommand("console.focus", "Focus the command input", "Session",
                "Put the cursor back in the game input.",
                function () { inputEl.focus(); });
        }

        /*
         * Universal search sources.  A11Y-COG-006.
         *
         * Registered after the commands so that a query searches both at once.
         * The point is that a player who half-remembers something does not
         * have to work out *which panel* it is in before they can look for it
         * -- reconstructing that is exactly the recall this replaces.
         */
        if (palette) {
            if (notes) {
                palette.registerSource(function (query) {
                    var needle = String(query).toLowerCase();
                    return noteSnapshot.filter(function (note) {
                        return (note.title || "").toLowerCase().indexOf(needle) !== -1 ||
                            (note.body || "").toLowerCase().indexOf(needle) !== -1;
                    }).slice(0, 8).map(function (note) {
                        return {
                            id: "note:" + note.id,
                            label: note.title || note.subjectName || "Note",
                            group: "Your notes",
                            description: (note.body || "").slice(0, 80),
                            run: function () { editNote(note); }
                        };
                    });
                });
            }

            if (cognitive) {
                palette.registerSource(function (query) {
                    var needle = String(query).toLowerCase();
                    return cognitive.all().filter(function (item) {
                        return item.text.toLowerCase().indexOf(needle) !== -1;
                    }).slice(0, 8).map(function (item) {
                        return {
                            id: "reminder:" + item.id,
                            label: item.text,
                            group: item.kind === "task" ? "Your tasks" : "Your reminders",
                            description: item.completed ? "Done" : item.trigger,
                            run: function () {
                                if (settings) { settings.openReminders(); }
                            }
                        };
                    });
                });
            }

            if (canonicalLog && review) {
                palette.registerSource(function (query) {
                    var needle = String(query).toLowerCase();
                    return canonicalLog.all().filter(function (event) {
                        return (event.originalText || "").toLowerCase()
                            .indexOf(needle) !== -1;
                    }).slice(-8).reverse().map(function (event) {
                        return {
                            id: "event:" + event.id,
                            label: (event.originalText || "").slice(0, 90),
                            group: "What happened",
                            description: event.category || "",
                            // Jumps in Review Mode rather than scrolling the
                            // console, so the line is reachable even when a
                            // display rule has since hidden it (E2).
                            run: function () { review.jumpTo(event.id); }
                        };
                    });
                });
            }
        }

        /*
         * The gestures themselves.
         *
         * Deliberately few. A phone-sized screen has room for a handful of
         * learnable movements, and a client with twelve of them has none --
         * they stop being shortcuts and become a language to memorise.
         *
         * Registered only where the command they duplicate exists, so a game
         * that forbids something never has a gesture for it.
         */
        if (gestures && palette) {
            function addGesture(direction, label, command, run, when) {
                if (!palette.commands().some(function (c) { return c.id === command; })) {
                    return false;
                }
                gestures.register({
                    direction: direction,
                    label: label,
                    paletteCommand: command,
                    run: run,
                    when: when
                });
                return true;
            }

            addGesture("up", "Command palette", "palette.toggle",
                function () { palette.toggle(); });

            if (review) {
                addGesture("right", "Review mode", "review.toggle",
                    function () { review.toggle(); });
            }
            if (orientation) {
                addGesture("left", "Where am I", "orientation.reorient",
                    function () { reorientNow(); });
            }
            if (commandQueue) {
                // Down for stop: the one gesture somebody reaches for in a
                // hurry, and the direction a hand falls naturally.
                addGesture("down", "Stop queued commands", "queue.cancel",
                    function () { commandQueue.cancel(); },
                    function () { return commandQueue.isRunning(); });
            }

            gestures.listen(document);
        }

        /*
         * Global shortcuts.  Addendum A.22, A.23.
         *
         * Every one of these names the palette command it accelerates. That is
         * enforced, not conventional: `register` throws without it, because a
         * feature reachable only by keystroke is a feature that does not exist
         * for anyone who does not already know the keystroke.
         *
         * None is a bare character. The manager refuses those outright --
         * NVDA and JAWS use single letters to move between headings, buttons
         * and lists, and taking one is taking away navigation, invisibly.
         */
        if (accessibility && accessibility.shortcuts) {
            var shortcuts = accessibility.shortcuts;

            if (palette) {
                shortcuts.register({
                    id: "palette.toggle",
                    label: "Command palette",
                    description: "Search everything this client can do.",
                    defaultBinding: "Ctrl+K",
                    paletteCommand: "palette.toggle",
                    run: function () { palette.toggle(); }
                });
            }
            if (help) {
                shortcuts.register({
                    id: "help.toggle",
                    label: "Help",
                    description: "Documentation for every feature, with examples.",
                    defaultBinding: "F1",
                    paletteCommand: "help.open",
                    run: function () { help.toggle(); }
                });
            }

            if (accessibilityPanel) {
                shortcuts.register({
                    id: "accessibility.mode",
                    label: "Accessible mode",
                    description: "Switch between the standard interface and the accessible one.",
                    // Ctrl+Shift+A. Not a bare character: single letters are
                    // what NVDA and JAWS use for structural navigation, and
                    // taking one would break reading the client to reach a
                    // panel about reading the client.
                    defaultBinding: "Ctrl+Shift+A",
                    paletteCommand: "accessibility.mode",
                    run: function () { accessibilityPanel.setMode(); }
                });
            }
            if (review) {
                shortcuts.register({
                    id: "review.toggle",
                    label: "Review mode",
                    description: "Pause announcements and read back through history.",
                    // Ctrl+Shift+R: not a bare character, and not Ctrl+R, which
                    // reloads the page and would lose the session being
                    // reviewed.
                    defaultBinding: "Ctrl+Shift+R",
                    paletteCommand: "review.toggle",
                    run: function () { review.toggle(); }
                });
            }

            if (orientation) {
                shortcuts.register({
                    id: "orientation.reorient",
                    label: "Where am I",
                    // Ctrl+Shift+W: W for "where", and not Ctrl+W, which closes
                    // the tab -- an accelerator for the lost that ended the
                    // session would be a cruel joke.
                    description: "Read back where you are and what you last did.",
                    defaultBinding: "Ctrl+Shift+W",
                    paletteCommand: "orientation.reorient",
                    run: function () { reorientNow(); }
                });
            }

            if (workspaces) {
                shortcuts.register({
                    id: "layout.edit",
                    label: "Edit layout",
                    description: "Move, resize, hide and restore widgets.",
                    defaultBinding: "Ctrl+Shift+L",
                    paletteCommand: "layout.edit",
                    run: function () { workspaces.toggleEditing(); }
                });
            }
        }

        // A.50: help stays in the same place regardless of workspace. Someone
        // who is lost should not have to find it somewhere new.
        var helpButton = document.getElementById("aetos-open-help");
        if (helpButton && help) {
            helpButton.addEventListener("click", function () { help.open(null); });
        } else if (helpButton) {
            helpButton.hidden = true;
        }

        /*
         * Settings.
         *
         * Aetos has no single settings screen -- it has seven panels (privacy,
         * themes, automation groups, reminders, symbol packs, diagnostics, and
         * the editors), each its own palette command. Until now none of them had
         * a button, so all of it was reachable only by knowing to press Ctrl+K
         * and what to search for.
         *
         * This opens the palette with the search already filled in, rather than
         * building a second list of destinations that would then have to be
         * styled, keyboard-enabled and kept in step with the first. Hidden if
         * there is no palette, because a button that does nothing is worse than
         * an absent one.
         */
        var settingsDashboard = window.AetosSettingsDashboard
            ? window.AetosSettingsDashboard.create({
                dialog: window.AetosDialog,
                settings: settings,
                inspector: inspector,
                accessibilityPanel: accessibilityPanel,
                manifest: function () { return store ? store.get("manifest") : null; },
                automationAllowed: automationAllowed,
                announce: function (message) {
                    announcer.announce(message, { priority: "normal" });
                }
            })
            : null;

        var settingsButton = document.getElementById("aetos-open-settings");
        if (settingsButton && settingsDashboard) {
            settingsButton.addEventListener("click", function () {
                settingsDashboard.open();
            });
        } else if (settingsButton && palette) {
            // No dashboard module: the palette still finds every destination by
            // name, which is where they all lived before this existed.
            settingsButton.addEventListener("click", function () {
                palette.open("settings");
            });
        } else if (settingsButton) {
            settingsButton.hidden = true;
        }

        /*
         * Bring the subsystem up.
         *
         * Last, because it loads the player's stored preferences and bindings,
         * and those must be applied over a client that is already fully
         * assembled -- a preference applied to half a client is a preference
         * silently ignored by the other half.
         */
        if (accessibility) {
            accessibility.start();
        }


        window.Aetos = {
            version: 1,
            protocol: AETOS_PROTOCOL_VERSION,
            emitter: emitter,
            dispatcher: dispatcher,
            store: store,
            consoleWidget: consoleWidget,
            accessibilityPanel: accessibilityPanel,
            settingsDashboard: settingsDashboard,
            announcer: announcer,
            storage: storage,
            profile: profile,
            registry: registry,
            layout: layout,
            workspaces: workspaces,
            queue: commandQueue,
            aliases: aliases,
            triggers: triggers,
            timers: timers,
            scripting: scripting,
            scriptApi: scriptApi,
            settings: settings,
            palette: palette,
            help: help,
            accessibility: accessibility,
            pipeline: pipeline,
            canonicalLog: canonicalLog,
            capture: capture,
            replay: replay,
            review: review,
            displayRules: displayRules,
            automationGroups: automationGroups,
            validator: validator,
            diagnostics: diagnostics,
            orientation: orientation,
            cognitive: cognitive,
            audio: audio,
            captions: captionsWidget,
            themes: themes,
            symbols: symbolProvider,
            aac: aacBoard,
            pwa: pwa,
            gestures: gestures,
            inspector: inspector,
            reloadTriggers: reloadTriggers,
            macros: macros,
            editMacro: editMacro,
            relationships: relationships,
            notes: notes,
            editNote: editNote,
            walkRoute: function (steps) { return walkRoute(steps); },
            cancelRoute: function () { return cancelRoute(); },
            // The public way to send a command. Unlike dispatcher.send() this
            // also refreshes state afterwards, which is what a caller almost
            // always wants -- acting without refreshing leaves the widgets
            // showing the world as it was before the command.
            sendCommand: function (text) { return sendCommand(text); }
        };

        /*
         * Responsive layout.
         *
         * Started last, once every widget exists, so the first measurement
         * reflects the real layout rather than an empty shell.
         */
        var responsive = window.AetosResponsive
            ? window.AetosResponsive.create({
                root: document.getElementById("aetos-root"),
                announce: function (message) { announcer.announce(message); }
            })
            : null;
        if (responsive) {
            responsive.start();
            window.Aetos.responsive = responsive;
        }

        window.console.log("Aetos Web Client shell initialized.");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }

})(window, document);
