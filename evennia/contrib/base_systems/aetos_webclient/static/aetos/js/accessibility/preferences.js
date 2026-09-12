/*
 * Aetos accessibility preferences.  Addendum A.70, A.71, A.72.
 *
 * THERE IS A MODE, AND IT DOES NOT REACH THE BASELINE (A10).
 *
 * `shell.mode` chooses between the standard interface and the accessible one.
 * It governs the *optional* layer only -- contrast, type size, motion,
 * stimulation, verbosity, quiet and focus modes, the word board.
 *
 * Semantic HTML, keyboard operation, focus management, landmarks, accessible
 * names and the announcer are unconditional, are not represented in this file
 * at all, and cannot be turned off by a player or a game developer
 * (A11Y-BASE-001). A mode switch that could reach them would not be a mode
 * switch; it would be a way to break the client.
 *
 * This file said "there is no accessibility mode here" until A10, and for the
 * baseline that is still exactly true. What changed is that the optional layer
 * now has one, because trying to be everything to everybody at once produced an
 * interface that was nobody's first choice.
 *
 * What lives here is the part that genuinely varies between people: how much
 * the client should say out loud, how much it should move, and how much it
 * should help with orientation. Choosing a screen-reader profile adjusts
 * verbosity. It does not "turn accessibility on" (A.71).
 *
 * TWO STORES, ON PURPOSE.
 *
 * The canonical copy lives in the `preferences` namespace, so it is exported,
 * imported and counted by the privacy panel like everything else the player
 * owns (A.75).
 *
 * A mirror lives in the boot channel, because several of these settings decide
 * how the client should look *before* the database has opened. Reading them
 * late would mean a player who asked for no motion sees motion first, which is
 * precisely the harm the setting exists to prevent.
 *
 * The mirror is a cache and the namespace is the truth. They are reconciled on
 * boot in that direction.
 *
 * NEVER LEAVES THE BROWSER (A.72, A.73, A.74). Nothing here is sent to the game
 * server, and Aetos does not attempt to detect a screen reader, a braille
 * display or AAC use. That detection would be fingerprinting, and a player must
 * never have to disclose a disability to a MUD operator in order to play.
 */

(function (window) {
    "use strict";

    //: Storage key. One document, because these settings are read together.
    var DOC_ID = "accessibility";
    var BOOT_KEY = "accessibility";

    //: Schema version, so a future migration can tell old documents apart.
    var VERSION = 1;

    /*
     * Defaults.
     *
     * Chosen so that a player who changes nothing gets a client that is quiet
     * rather than chatty. An interface that announces everything is as
     * unusable as one that announces nothing, and the failure mode of
     * over-announcing is worse: it trains people to ignore the channel that
     * carries the urgent messages.
     */
    var DEFAULTS = {
        version: VERSION,

        /*
         * Which interface the player is in.  A10.
         *
         * `"standard"` is the client as it is for somebody who never asks for
         * anything: default contrast, default type, no accessibility panel.
         * `"accessible"` applies the accommodations they have chosen and offers
         * the panel to change them.
         *
         * A9 shipped this as a *disclosure* -- the panel hid and every setting
         * stayed applied. Gary asked for the sharper version: two modes, "so we
         * dont have to try to be everything to everybody". This is that.
         *
         * **The mode masks; it never erases.** Switching to standard stops the
         * governed accommodations applying and leaves every stored value
         * exactly as it was, so switching back restores the interface somebody
         * spent time building rather than handing them a fresh one. Erasing
         * would make the toggle a thing you cannot afford to try.
         */
        shell: {
            mode: "standard",

            /*
             * Which starting point the player took, if any.  A12.
             *
             * `null` means they have never been asked. That is the state the
             * chooser exists for, and it is the whole reason this key is not
             * simply "custom" by default: "not yet asked" and "asked, and chose
             * to set it up themselves" are different, and only the first one
             * should put a question in front of somebody.
             *
             * A preset is a **bulk write of ordinary preferences**, not a mode
             * and not a layer. Once applied it is indistinguishable from having
             * set those values by hand, which is what keeps `effective()` --
             * the masking rule, the delicate part of A10 -- completely
             * untouched by any of this. The name is kept only so the panel can
             * show which one was taken.
             */
            preset: null
        },

        screenReader: {
            // "selective" honours the per-category flags below. "all" and
            // "minimal" are shortcuts that ignore them.
            announcementMode: "selective",
            announceRoom: true,
            announceTells: true,
            announceChat: true,
            // Off by default: combat is the highest-volume category in most
            // games and the one most likely to make speech useless.
            announceCombat: false,
            // Thresholds only -- "health 61", "health 60", "health 59" is not
            // information, it is noise with a number in it.
            announceResources: "thresholds",
            reviewModeBehavior: "pause-normal"
        },

        /*
         * Aetos reading aloud, by itself.  A15.
         *
         * Distinct from everything in `screenReader` above, which describes what
         * is handed to *your* assistive technology. This is the client's own
         * voice, for the much larger group of people who want text read to them
         * and do not run a screen reader.
         *
         * Off by default, and it must stay that way. A client that starts
         * talking on load is alarming, and for somebody running a screen reader
         * it would be two voices over each other. Aetos cannot detect a screen
         * reader and must never try (A.72), so the only honest default is
         * silence plus a clearly named control.
         */
        speech: {
            enabled: false,
            rate: 1.0,
            volume: 1.0,
            // The voice's name, or null for whatever the browser picks. A name
            // rather than an index: voice lists differ between machines and an
            // index would silently select a different voice on another one.
            voice: null
        },

        braille: {
            // "HP 82/100" rather than "Health, 82 out of 100" (A11Y-BRL-002).
            compactStatus: true,
            preserveReviewPosition: true
        },

        keyboard: {
            // A11Y-KEY-002. Off by default and, when a player does opt in,
            // still never bound to a bare character by Aetos itself.
            singleKeyShortcuts: false,
            conflictWarnings: true
        },

        /*
         * Pointer and motor access.  A.57.
         *
         * Its own group rather than tacked onto `keyboard`, because a swipe is
         * not a keystroke and the distinction matters to whoever reads this
         * next.
         *
         * Every gesture duplicates a palette command, so switching them off
         * costs nothing but the shortcut -- which is exactly why it is safe to
         * offer, and why the default can be on.
         */
        pointer: {
            gestures: true
        },

        cognitive: {
            reorientEnabled: true,
            orientationChecklist: "manual",
            quietMode: false,
            // A.47. Visual quieting, separate from quietMode's announcement
            // quieting: wanting a calmer screen and wanting fewer
            // interruptions are different needs, and somebody may want either
            // without the other.
            focusMode: false,
            // A11Y-COG-007. A game event rearranging the workspace under
            // someone is disorienting for everyone and disabling for some.
            automaticWorkspaceSwitching: "never"
        },

        /*
         * Sound.  A11Y-MEDIA-002.
         *
         * One control per category, because a sound a player cannot turn down
         * is a sound they cannot escape. The master starts below full: a
         * client that arrives loud is a client somebody closes before they
         * find the slider.
         */
        audio: {
            muted: false,
            master: 0.7,
            music: 1.0,
            ambience: 1.0,
            effect: 1.0,
            ui: 1.0,
            voice: 1.0
        },

        visual: {
            scale: 1.0,
            contrast: "standard",
            // "system" defers to prefers-reduced-motion. An explicit choice
            // overrides it, in both directions -- a player may want motion the
            // operating system is suppressing.
            motion: "system",
            stimulation: "standard",

            /*
             * The face the *shell* is set in.  A12.
             *
             * Game output is always monospace and is not affected: the server
             * aligned it by counting characters. This is about the client's own
             * prose -- labels, explanations, the accessibility panel's own 242
             * words, all of which were monospaced until A12 because the whole
             * client was.
             *
             * A preference rather than a decision because the evidence splits.
             * Vision Australia and APA Style say avoid monospace for long
             * passages; Rello and Baeza-Yates measured dyslexic readers and
             * found monospace *improved* reading performance. Defaulting to
             * proportional follows the larger body of low-vision guidance;
             * `monospace` is here so that following it does not quietly cost
             * the other group.
             */
            typeface: "proportional"
        },

        aac: {
            enabled: false,
            symbolPack: null,
            // A.64. Symbol *and* text by default: a symbol nobody recognises
            // with no word under it is unusable, while the reverse is merely
            // plain. A symbol-focused presentation is a choice, not a default.
            showTextWithSymbols: true,
            // The command a composed sentence is sent with. A player on a game
            // that uses something other than `say` -- or who wants their board
            // to whisper rather than speak aloud -- changes it here, and it is
            // an ordinary command either way (A.68).
            sayCommand: "say"
        }
    };

    //: Allowed values. Anything outside these falls back to the default rather
    //: than being stored, so a hand-edited import cannot produce a client in a
    //: state no code path expects.
    /*
     * Numeric preferences, and the range each is clamped to.
     *
     * A table rather than a branch per key. `visual.scale` used to be the only
     * number here and had its own special case; adding the volumes exposed
     * what that shape cost -- a number with no branch fell through to the
     * string check and was silently discarded, so every volume slider appeared
     * to work while nothing it set survived a reload. A player would have
     * concluded the client was broken, and they would have been right.
     */
    /*
     * What the accessibility panel offers.  A9.
     *
     * This table is the deliverable of A9 as much as the panel is: it draws the
     * line between the accommodations a player chooses and the ones that are
     * simply how the client is built.
     *
     * Everything here is **optional and opinionated** -- a matter of need and
     * taste, which a player might reasonably not want. Nothing here is load
     * bearing for basic operation.
     *
     * `kind` says how to render it; `label` is what a player reads; `detail`
     * says what changes, in terms of what they will see rather than what the
     * code does.
     *
     * `revertsInStandardMode` is the one that needs care. A10 makes standard
     * mode stop applying the accommodations, and something may only be reverted
     * safely if its **default is the standard experience** -- so that reverting
     * removes an accommodation rather than imposing one.
     *
     * Four here are marked `false`. `visual.scale` is the odd one and the most
     * important: being able to set the size of text is not an accommodation
     * somebody opts into, it is a basic property of a text interface, so it is
     * offered in *both* modes and survives the switch. The other three fail the
     * test above:
     *
     *   `pointer.gestures` defaults to ON, so somebody with a tremor turns them
     *   OFF. Reverting would switch gestures back on for the person who most
     *   needed them off.
     *
     *   `audio.muted` defaults to OFF, so muting is the accommodation.
     *   Reverting would start playing sound at somebody.
     *
     *   `cognitive.reorientEnabled` defaults to ON. Reverting adds a feature
     *   rather than removing one, which is not what a mode switch is for.
     *
     * They stay in the panel, because they belong there, and they survive the
     * mode switch untouched. Getting this backwards would make standard mode
     * actively hostile to three of the people it is meant to leave alone.
     */
    var GOVERNED = [
        {
            path: "visual.contrast",
            revertsInStandardMode: true,
            kind: "enum",
            label: "Contrast",
            detail: "Higher contrast strengthens every border and text colour."
        },
        {
            path: "visual.scale",
            /*
             * NOT reverted, and offered in both modes.
             *
             * Gary: "one of the worst things is having to read tiny text with no
             * way to just adjust the text size. having to zoom the browser is
             * janky" -- and "that option should be in both modes".
             *
             * He is right, and the first version had this wrong. Being able to
             * set the size of text is not an accommodation you opt into; it is
             * a basic property of a text interface, and taking it away because
             * somebody chose the standard client would be taking away the thing
             * they most likely needed. Browser zoom is the fallback everybody
             * already has and it reflows the whole page rather than the client.
             */
            revertsInStandardMode: false,
            kind: "range",
            label: "Text size",
            detail: "Scales the whole interface, not only the text. Available in "
                + "both modes, and kept when you switch."
        },
        {
            path: "visual.motion",
            revertsInStandardMode: true,
            kind: "enum",
            label: "Motion",
            detail: "Your choice wins over the system setting, in both directions."
        },
        {
            path: "visual.stimulation",
            revertsInStandardMode: true,
            kind: "enum",
            label: "Visual detail",
            detail: "Removes decoration that carries no information."
        },
        {
            path: "screenReader.announcementMode",
            revertsInStandardMode: true,
            kind: "enum",
            label: "How much is announced",
            /*
             * A14b: this used to say "What is spoken aloud or sent to a braille
             * display", which reads as a promise that Aetos speaks. It does not.
             * It writes to a live region and a screen reader voices it, so with
             * no screen reader running the setting appears to do nothing at all
             * -- and the person most likely to be confused by that is somebody
             * setting up assistive technology for the first time.
             */
            detail: "Passed to your screen reader or braille display, which "
                + "reads it. Aetos does not speak by itself."
        },
        {
            path: "cognitive.quietMode",
            revertsInStandardMode: true,
            kind: "boolean",
            label: "Quiet mode",
            detail: "Fewer interruptions. Nothing is lost -- it is still in the log."
        },
        {
            path: "cognitive.focusMode",
            revertsInStandardMode: true,
            kind: "boolean",
            label: "Focus mode",
            detail: "A calmer screen. Separate from quiet mode, because wanting "
                + "less on screen and wanting fewer interruptions are different needs."
        },
        {
            path: "cognitive.reorientEnabled",
            revertsInStandardMode: false,
            kind: "boolean",
            label: "Orientation help",
            detail: "Where you are, how you got here, and how to go back."
        },
        {
            path: "aac.enabled",
            revertsInStandardMode: true,
            kind: "boolean",
            label: "Picture and word board",
            detail: "Compose commands from symbols and words instead of typing."
        },
        {
            path: "pointer.gestures",
            revertsInStandardMode: false,
            kind: "boolean",
            label: "Touch gestures",
            detail: "Every gesture also has a keyboard command, so turning these "
                + "off costs only the shortcut."
        },
        {
            path: "audio.muted",
            revertsInStandardMode: false,
            kind: "boolean",
            label: "Mute all sound",
            detail: "Captions stay on screen regardless."
        },
        {
            path: "speech.enabled",
            /*
             * Not reverted by standard mode.
             *
             * Somebody who has asked the client to read to them has not asked
             * for that to stop when they look at the standard interface, and
             * silently muting it would be the same class of defect as quiet
             * mode silencing the game.
             */
            revertsInStandardMode: false,
            kind: "boolean",
            label: "Read the game aloud",
            detail: "Aetos reads new game text using your computer's own "
                + "voice. Leave this off if you already use a screen reader, "
                + "or you will hear everything twice."
        },
        {
            path: "speech.rate",
            revertsInStandardMode: false,
            kind: "range",
            label: "Reading speed",
            detail: "How fast the game is read aloud. Only applies when "
                + "reading aloud is on."
        },
        {
            path: "visual.typeface",
            /*
             * Offered in both modes, for the same reason text size is: the
             * shape of the letters is a basic property of a text interface
             * rather than an accommodation somebody opts into.
             */
            revertsInStandardMode: false,
            kind: "enum",
            label: "Lettering",
            detail: "Game text always keeps its fixed-width lettering so maps "
                + "and tables line up. This is about the client's own words."
        }
    ];

    /*
     * How the options are grouped on screen.  A12.
     *
     * The panel used to render all eleven in one flat grid -- measured at five
     * columns, 242 words and 53% of a 1080px screen, with the reading order
     * zig-zagging across the full width. W3C's COGA guidance asks for no more
     * than about seven options in any one section; this is four sections of
     * four or fewer.
     *
     * Declared here rather than as a `section` key on each entry so that the
     * grouping is legible in one place -- the question "is any section too
     * long" should be answerable by looking, not by counting matching keys down
     * a hundred-line list.
     *
     * An entry missing from every section still renders, under "More", so
     * adding a preference and forgetting this list degrades to the old
     * behaviour for one control rather than hiding it. A test enforces that the
     * list is empty.
     */
    var SECTIONS = [
        {
            label: "Seeing",
            paths: [
                "visual.scale",
                "visual.typeface",
                "visual.contrast",
                "visual.stimulation"
            ]
        },
        {
            label: "Movement and sound",
            paths: ["visual.motion", "audio.muted"]
        },
        {
            label: "Calm and focus",
            paths: [
                "cognitive.quietMode",
                "cognitive.focusMode",
                "cognitive.reorientEnabled"
            ]
        },
        {
            label: "Speech and other ways in",
            paths: [
                "speech.enabled",
                "speech.rate",
                "screenReader.announcementMode",
                "aac.enabled",
                "pointer.gestures"
            ]
        }
    ];

    /*
     * What is NOT here, and must never be.
     *
     * A0 built this schema with no master switch (A.70) and the reasoning holds
     * for exactly this list. These are not features to be enabled; they are
     * what makes the client usable at all, and they are unconditional.
     *
     * A client that is only operable by keyboard when a box is ticked is not an
     * accessible client with a toggle. It is an inaccessible client with an
     * apology.
     *
     * Stated as data so the panel can *show* it -- somebody deciding whether to
     * turn accessibility "on" deserves to know what was never off.
     */
    var UNCONDITIONAL = [
        "Every function is operable from the keyboard.",
        "Focus is always visible and never moves on its own.",
        "Landmarks, headings and accessible names on every control.",
        "One announcement channel, so nothing competes to speak.",
        "Colour never carries meaning on its own.",
        "Target sizes that do not require fine pointing."
    ];

    var SCALE_MIN = 0.75;
    var SCALE_MAX = 2.5;

    var RANGES = {
        "speech.rate": [0.5, 2.5],
        "speech.volume": [0, 1],
        // The scale bounds by reference, not by repetition: an earlier draft
        // of this table wrote 2.0 here and silently narrowed a range that had
        // been 2.5 since A0.
        "visual.scale": [SCALE_MIN, SCALE_MAX],
        "audio.master": [0, 1],
        "audio.music": [0, 1],
        "audio.ambience": [0, 1],
        "audio.effect": [0, 1],
        "audio.ui": [0, 1],
        "audio.voice": [0, 1]
    };

    var ENUMS = {
        "shell.mode": ["standard", "accessible"],
        "shell.preset": [
            null, "low-vision", "calm", "screen-reader", "motor", "custom"
        ],
        "visual.typeface": ["proportional", "monospace"],
        "speech.enabled": [true, false],
        "screenReader.announcementMode": ["selective", "all", "minimal"],
        "screenReader.announceResources": ["never", "thresholds", "always"],
        "screenReader.reviewModeBehavior": ["pause-normal", "pause-all", "pause-none"],
        "cognitive.orientationChecklist": [
            "disabled", "manual", "idle", "unfamiliar", "always"
        ],
        "cognitive.automaticWorkspaceSwitching": ["never", "ask", "always"],
        "visual.contrast": ["standard", "high"],
        "visual.motion": ["system", "full", "reduced"],
        "visual.stimulation": ["rich", "standard", "reduced", "minimal"]
    };

    //: Bounds on the one numeric setting, so a bad value cannot render the
    //: interface unreadably small or large.

    /*
     * Starting points.  A12.
     *
     * WHY THESE EXIST. Measured at A12, `accessible` mode and `standard` mode
     * rendered **byte-identically**: same faces, same sizes, same everything.
     * That is not a bug -- the mode masks preferences, and every governed
     * preference defaults to its standard value, so by default there is nothing
     * to mask. But it means the sequence for somebody who needs help was: find
     * the switch, flip it, watch nothing happen, press Options, read 242 words
     * across five columns, and make eleven decisions in a vocabulary nobody
     * taught them -- and only then get an accessible client.
     *
     * Every step of that was correct in isolation. The sum put the entire
     * configuration burden on the person least able to spend it, in the name of
     * not presuming. W3C's COGA guidance asks for no more than about seven
     * options in a section; we had eleven, before anything had been made easier.
     *
     * So: one question with five answers, asked once, instead of eleven
     * questions asked immediately.
     *
     * WHAT A PRESET IS NOT. It is not a mode, a layer, or a lock. Applying one
     * writes ordinary preferences, exactly as if they had been set by hand; the
     * panel still shows every one of them and any can be changed afterwards.
     * Nothing here reads a preset back, so there is no state to get out of sync
     * and `effective()` never learns that presets exist.
     *
     * The names are what a person would call their own situation, not what a
     * specification calls it. Somebody who cannot read small text knows that
     * about themselves; they do not necessarily know the phrase "reduced
     * stimulation".
     */
    var PRESETS = [
        {
            name: "low-vision",
            label: "Hard to see small text",
            detail: "Larger type, stronger borders, and less decoration "
                + "competing with the words.",
            values: {
                visual: { scale: 1.5, contrast: "high", stimulation: "reduced" }
            }
        },
        {
            name: "calm",
            label: "Too much going on",
            detail: "A quieter screen with fewer interruptions and no "
                + "movement. Nothing is lost -- it is all still in the log.",
            values: {
                visual: { motion: "reduced", stimulation: "minimal" },
                cognitive: { quietMode: true, focusMode: true }
            }
        },
        {
            name: "screen-reader",
            label: "I use a screen reader or braille display",
            detail: "Announces what you chose rather than everything, and "
                + "keeps orientation help on so you can always ask where you "
                + "are.",
            values: {
                screenReader: { announcementMode: "selective" },
                cognitive: { reorientEnabled: true },
                visual: { stimulation: "reduced" }
            }
        },
        {
            name: "motor",
            label: "Hard to click small things",
            detail: "Bigger targets and text, and every gesture also has a "
                + "keyboard command.",
            values: {
                visual: { scale: 1.25 },
                pointer: { gestures: true }
            }
        },
        {
            /*
             * Not an empty preset -- an answer.
             *
             * Recording "custom" is what stops the chooser asking again. A
             * player who has decided to set things up themselves has answered
             * the question, and being asked it every session would be the
             * interruption this whole change exists to remove.
             */
            name: "custom",
            label: "Let me choose each setting myself",
            detail: "Opens the full list. Nothing is changed until you change "
                + "it.",
            values: {}
        }
    ];

    /*
     * Every preference any preset has an opinion about.  A14b.
     *
     * Derived from the table rather than listed beside it, so adding a value to
     * a preset cannot forget to add it here -- which would bring back exactly
     * the leftover-setting bug this exists to prevent.
     */
    var PRESET_KEYS = (function () {
        var keys = [];
        PRESETS.forEach(function (preset) {
            Object.keys(preset.values).forEach(function (group) {
                Object.keys(preset.values[group]).forEach(function (key) {
                    var path = group + "." + key;
                    if (keys.indexOf(path) === -1) {
                        keys.push(path);
                    }
                });
            });
        });
        return keys;
    }());

    function presetNamed(name) {
        for (var i = 0; i < PRESETS.length; i++) {
            if (PRESETS[i].name === name) {
                return PRESETS[i];
            }
        }
        return null;
    }

    function clone(value) {
        return JSON.parse(JSON.stringify(value));
    }

    /*
     * Merge a stored document over the defaults.
     *
     * Deliberately not a deep-merge library. Unknown keys are dropped and
     * out-of-range values fall back, so the object handed to the rest of the
     * client always has exactly the shape the code expects -- there is no
     * "maybe this key exists" anywhere downstream.
     */
    function normalize(raw) {
        var result = clone(DEFAULTS);
        if (!raw || typeof raw !== "object") {
            return result;
        }

        Object.keys(DEFAULTS).forEach(function (group) {
            if (group === "version") {
                return;
            }
            var stored = raw[group];
            if (!stored || typeof stored !== "object") {
                return;
            }
            Object.keys(DEFAULTS[group]).forEach(function (key) {
                if (!Object.prototype.hasOwnProperty.call(stored, key)) {
                    return;
                }
                var value = stored[key];
                var path = group + "." + key;

                if (ENUMS[path]) {
                    if (ENUMS[path].indexOf(value) !== -1) {
                        result[group][key] = value;
                    }
                    return;
                }
                if (RANGES[path]) {
                    var number = parseFloat(value);
                    if (isFinite(number)) {
                        result[group][key] = Math.min(
                            RANGES[path][1], Math.max(RANGES[path][0], number)
                        );
                    }
                    return;
                }
                if (typeof DEFAULTS[group][key] === "boolean") {
                    if (typeof value === "boolean") {
                        result[group][key] = value;
                    }
                    return;
                }
                // symbolPack: a string or null, nothing else.
                if (value === null || typeof value === "string") {
                    result[group][key] = value;
                }
            });
        });

        return result;
    }

    function createPreferences(services) {
        var storage = services && services.storage;
        var listeners = [];

        // Seeded from the boot mirror so the very first paint is already
        // correct, then reconciled from the database when it opens.
        var current = normalize(
            storage && storage.getBootPreference
                ? storage.getBootPreference(BOOT_KEY, null)
                : null
        );

        function notify() {
            listeners.forEach(function (listener) {
                try {
                    listener(effective());
                } catch (err) {
                    // One bad subscriber must not stop the others from
                    // applying a preference the player explicitly asked for.
                    if (window.console) {
                        window.console.error("Aetos: accessibility subscriber failed", err);
                    }
                }
            });
        }

        function get() {
            return clone(current);
        }

        /*
         * What is actually in force, as opposed to what the player has chosen.
         *
         * In accessible mode the two are the same. In standard mode the
         * governed accommodations read as their defaults -- **without the
         * stored values being touched**, so switching back restores the
         * interface somebody built rather than a fresh one.
         *
         * Subscribers get this rather than `get()`, so every consumer honours
         * the mode without having to know a mode exists. `get()` and `value()`
         * still answer "what did the player choose", which is what the editors
         * need in order to show it.
         *
         * A consumer that subscribed and then wrote back what it received would
         * persist the mask and lose the choice. Nothing does; it is worth
         * knowing that nothing may.
         */
        function effective() {
            var view = clone(current);
            if (view.shell && view.shell.mode === "accessible") {
                return view;
            }
            GOVERNED.forEach(function (entry) {
                if (!entry.revertsInStandardMode) {
                    return;
                }
                var parts = entry.path.split(".");
                if (view[parts[0]] && DEFAULTS[parts[0]]) {
                    view[parts[0]][parts[1]] = DEFAULTS[parts[0]][parts[1]];
                }
            });
            return view;
        }

        /*
         * Whether anything the mode governs is actually set away from default.
         *
         * Used to decide what to say when somebody switches modes: "nothing you
         * chose was in use anyway" and "your five settings have stopped
         * applying" deserve different sentences.
         */
        function activeAccommodations() {
            var names = [];
            GOVERNED.forEach(function (entry) {
                if (!entry.revertsInStandardMode) {
                    return;
                }
                var parts = entry.path.split(".");
                var chosen = current[parts[0]] && current[parts[0]][parts[1]];
                var fallback = DEFAULTS[parts[0]] && DEFAULTS[parts[0]][parts[1]];
                if (chosen !== fallback) {
                    names.push(entry.label);
                }
            });
            return names;
        }

        /*
         * Read one setting by dotted path.
         *
         * Callers ask questions like `pref("visual.motion")` rather than
         * reaching into the object, so a later reshuffle of the schema does not
         * mean editing every widget.
         */
        function value(path) {
            var parts = String(path).split(".");
            var node = current;
            for (var i = 0; i < parts.length; i++) {
                if (!node || typeof node !== "object") {
                    return undefined;
                }
                node = node[parts[i]];
            }
            return node;
        }

        function persist() {
            if (!storage) {
                return Promise.resolve(current);
            }
            // Mirror first. If the database write fails -- quota, private
            // browsing -- the player's choice still applies on the next load,
            // which matters more than the record being complete.
            if (storage.setBootPreference) {
                storage.setBootPreference(BOOT_KEY, current);
            }
            return storage
                .put("preferences", { id: DOC_ID, accessibility: current })
                .then(function () { return current; })
                .catch(function () { return current; });
        }

        /*
         * Apply a partial update.
         *
         * Partial by group, so a caller changing one setting cannot silently
         * reset the others -- the same merge-not-replace rule the notes store
         * learned the hard way in M11.
         */
        function update(patch) {
            var merged = clone(current);
            Object.keys(patch || {}).forEach(function (group) {
                if (!merged[group] || typeof patch[group] !== "object") {
                    return;
                }
                Object.keys(patch[group]).forEach(function (key) {
                    merged[group][key] = patch[group][key];
                });
            });
            current = normalize(merged);
            notify();
            return persist();
        }

        function reset() {
            current = clone(DEFAULTS);
            notify();
            return persist();
        }

        /*
         * Reconcile with the database once it is available.
         *
         * The namespace is the truth and the boot mirror is a cache, so a
         * stored document wins. If none exists, the mirror is written back so a
         * profile imported on another machine survives.
         */
        function load() {
            if (!storage) {
                notify();
                return Promise.resolve(get());
            }
            return storage
                .get("preferences", DOC_ID)
                .then(function (stored) {
                    if (stored && stored.accessibility) {
                        current = normalize(stored.accessibility);
                    }
                    notify();
                    return persist().then(get);
                })
                .catch(function () {
                    notify();
                    return get();
                });
        }

        function subscribe(listener) {
            if (typeof listener !== "function") {
                return function () {};
            }
            listeners.push(listener);
            // Prime immediately. A subscriber that only hears about *changes*
            // never applies the current value, which is the bug the state store
            // hit in M6.
            //
            // `effective()`, matching `notify()`. Priming with `get()` would
            // hand every subscriber the unmasked settings once at boot and the
            // masked ones from then on -- so a client started in standard mode
            // would apply the accommodations for exactly as long as it took
            // somebody to change something.
            try {
                listener(effective());
            } catch (err) {
                if (window.console) {
                    window.console.error("Aetos: accessibility subscriber failed", err);
                }
            }
            return function unsubscribe() {
                var index = listeners.indexOf(listener);
                if (index !== -1) {
                    listeners.splice(index, 1);
                }
            };
        }

        /*
         * Take a starting point.  A12.
         *
         * One `update`, so subscribers see one change and the panel repaints
         * once rather than eleven times. The preset name is recorded in the
         * same write, which is what makes "have they been asked yet" a fact
         * rather than a guess.
         *
         * An unknown name is refused rather than silently ignored: the only way
         * to get one is a bug or a hand-edited profile, and quietly recording a
         * preset that applied nothing would leave somebody looking at an
         * unchanged client wondering what they had just chosen.
         */
        function applyPreset(name) {
            var preset = presetNamed(name);
            if (!preset) {
                return Promise.resolve(get());
            }

            /*
             * A starting point puts you at a known place.  A14b.
             *
             * Presets used to be purely additive: they wrote their own values
             * and left everything else alone. Which means picking "Too much
             * going on" and then "I use a screen reader" left `quietMode` on
             * from the first -- and quiet mode silenced every line of game
             * output, so the second preset produced a client that said nothing
             * at all. Nobody chose that combination and nothing on screen
             * explained it.
             *
             * So every key any preset touches is written on every apply: to the
             * chosen preset's value, or back to its default. Switching starting
             * points now means what it says, rather than accumulating the
             * sediment of the ones before it.
             *
             * Only the keys presets touch. A preference somebody set by hand
             * and no preset has an opinion about is theirs, and clearing it
             * would make picking a starting point a destructive act.
             */
            var patch = {};
            PRESET_KEYS.forEach(function (path) {
                var parts = path.split(".");
                patch[parts[0]] = patch[parts[0]] || {};
                patch[parts[0]][parts[1]] = DEFAULTS[parts[0]][parts[1]];
            });
            Object.keys(preset.values).forEach(function (group) {
                patch[group] = patch[group] || {};
                Object.keys(preset.values[group]).forEach(function (key) {
                    patch[group][key] = preset.values[group][key];
                });
            });

            patch.shell = patch.shell || {};
            patch.shell.preset = preset.name;
            return update(patch);
        }

        return {
            get: get,
            effective: effective,
            activeAccommodations: activeAccommodations,
            value: value,
            update: update,
            applyPreset: applyPreset,
            reset: reset,
            load: load,
            subscribe: subscribe
        };
    }

    /*
     * Every numeric default must appear in RANGES.
     *
     * Checked at load rather than asserted in a test alone, because the
     * failure it prevents is silent: a number with no range is dropped by
     * `normalize`, and the only symptom is a setting that will not stick.
     * Better to be loud in the console of whoever added it.
     */
    Object.keys(DEFAULTS).forEach(function (group) {
        if (group === "version" || typeof DEFAULTS[group] !== "object") {
            return;
        }
        Object.keys(DEFAULTS[group]).forEach(function (key) {
            if (typeof DEFAULTS[group][key] !== "number") {
                return;
            }
            if (!RANGES[group + "." + key] && window.console) {
                window.console.warn(
                    "Aetos: numeric preference " + group + "." + key +
                    " has no entry in RANGES and will not persist."
                );
            }
        });
    });

    window.AetosAccessibilityPreferences = {
        create: createPreferences,
        DEFAULTS: DEFAULTS,
        ENUMS: ENUMS,
        RANGES: RANGES,
        GOVERNED: GOVERNED,
        SECTIONS: SECTIONS,
        PRESETS: PRESETS,
        PRESET_KEYS: PRESET_KEYS,
        presetNamed: presetNamed,
        UNCONDITIONAL: UNCONDITIONAL,
        VERSION: VERSION,
        DOC_ID: DOC_ID,
        normalize: normalize
    };

})(window);
