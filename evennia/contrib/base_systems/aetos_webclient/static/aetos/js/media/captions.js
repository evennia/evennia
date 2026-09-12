/*
 * Aetos captions and media controls.  Addendum A.58, A.79, A.84.
 *
 * The text half of every sound, and the controls that govern all of them.
 *
 * WHY THIS IS A WIDGET AND NOT A TOAST. A caption that appears for three
 * seconds and disappears is a caption for people who happened to be looking.
 * Somebody reading with a braille display, or who looked away, or who reads
 * slowly, gets nothing from it. So captions accumulate in a scrollable list
 * that stays -- the same treatment the transcript gets, for the same reason.
 *
 * IMAGES LIVE HERE TOO. An image with a description is shown with its
 * description as `alt`; an image without one is shown with `alt=""` and
 * reported, because a decorative-by-omission image is better than a screen
 * reader reading out a filename.
 *
 * THE CONTROLS ARE THE POINT (A11Y-MEDIA-002). Mute all, a master volume, one
 * slider per category, and stop-all. Every one of them a real `<input>` or
 * `<button>` with a real label, because a custom slider that a screen reader
 * cannot operate is a volume control that does not exist for the person most
 * likely to need it.
 */

(function (window, document) {
    "use strict";

    //: Captions kept. Bounded like every other growing list in the client.
    var MAX_CAPTIONS = 200;

    //: Category sliders, with the labels a player actually reads. "effect" is
    //: shown as "Sound effects" because the bare word means nothing on its own.
    var SLIDERS = [
        { key: "master", label: "Overall volume" },
        { key: "music", label: "Music" },
        { key: "ambience", label: "Ambience" },
        { key: "effect", label: "Sound effects" },
        { key: "ui", label: "Interface sounds" },
        { key: "voice", label: "Voice" }
    ];

    function createWidget(services) {
        var settings = services || {};
        var audio = settings.audio || null;
        var preferences = settings.preferences || null;

        var captions = [];
        var listEl = null;
        var imageEl = null;

        function preference(key, fallback) {
            if (!preferences || typeof preferences.value !== "function") {
                return fallback;
            }
            var found = preferences.value("audio." + key, fallback);
            return found === undefined ? fallback : found;
        }

        /*
         * Record one caption.
         *
         * Called by the audio engine for every non-decorative item, whether or
         * not the sound played. The list is the authoritative record of what
         * the game emitted; the speakers are best-effort.
         */
        function record(text, item) {
            captions.push({
                text: String(text || ""),
                category: (item && item.category) || "media",
                uncaptioned: !!(item && item.uncaptioned)
            });
            if (captions.length > MAX_CAPTIONS) {
                captions.shift();
            }
            renderCaptions();
            return captions.length;
        }

        function renderCaptions() {
            if (!listEl) {
                return;
            }
            listEl.textContent = "";
            captions.slice(-40).forEach(function (entry) {
                var row = document.createElement("li");
                row.className = "aetos-caption";

                var kind = document.createElement("span");
                kind.className = "aetos-caption__category";
                kind.textContent = entry.category;
                row.appendChild(kind);

                var text = document.createElement("span");
                text.className = "aetos-caption__text";
                text.textContent = entry.text;
                row.appendChild(text);

                listEl.appendChild(row);
            });
            // Newest at the bottom, matching the console, so a player reading
            // both is not switching direction between them.
            listEl.scrollTop = listEl.scrollHeight;
        }

        /*
         * Show one image, with its description.
         *
         * One at a time and never automatically dismissed: an image that
         * disappears on a timer cannot be examined, and A.84 requires
         * auto-updating content to be under the player's control.
         */
        function showImage(item) {
            if (!imageEl) {
                return false;
            }
            imageEl.textContent = "";
            if (!item) {
                return false;
            }
            var picture = document.createElement("img");
            picture.src = item.url;
            /*
             * A described image gets its description. An undescribed one is
             * marked decorative rather than left for a screen reader to read
             * the filename out of -- "seven underscore dungeon underscore
             * two dot png" is worse than silence.
             */
            picture.alt = item.description || item.caption || "";
            picture.className = "aetos-media__image";
            imageEl.appendChild(picture);

            var close = document.createElement("button");
            close.type = "button";
            close.className = "aetos-list__button";
            close.textContent = "Hide image";
            close.addEventListener("click", function () { showImage(null); });
            imageEl.appendChild(close);
            return true;
        }

        /* --- Controls ----------------------------------------------------- */

        function buildControls(container) {
            var controls = document.createElement("div");
            controls.className = "aetos-media__controls";

            var mute = document.createElement("button");
            mute.type = "button";
            mute.className = "aetos-list__button";
            mute.textContent = "Mute all sound";
            // Pressed state rather than a changing label alone, so the current
            // state is available without reading the button twice.
            mute.setAttribute("aria-pressed", preference("muted", false) ? "true" : "false");
            mute.addEventListener("click", function () {
                var next = !preference("muted", false);
                if (preferences) {
                    preferences.update({ audio: { muted: next } });
                }
                mute.setAttribute("aria-pressed", next ? "true" : "false");
                if (audio) {
                    audio.applyVolumes();
                }
            });
            controls.appendChild(mute);

            var stop = document.createElement("button");
            stop.type = "button";
            stop.className = "aetos-list__button";
            stop.textContent = "Stop all sound";
            stop.addEventListener("click", function () {
                if (audio) {
                    audio.stopAll();
                }
            });
            controls.appendChild(stop);

            SLIDERS.forEach(function (slider) {
                var row = document.createElement("div");
                row.className = "aetos-media__slider";

                var id = "aetos-volume-" + slider.key;
                var label = document.createElement("label");
                label.setAttribute("for", id);
                label.textContent = slider.label;
                row.appendChild(label);

                /*
                 * A native range input.
                 *
                 * Not a styled div. Screen readers, switch devices and
                 * keyboard users all already know how to operate this one, and
                 * a custom slider that any of them cannot use is a volume
                 * control that does not exist for the person most likely to
                 * need it.
                 */
                var input = document.createElement("input");
                input.type = "range";
                input.id = id;
                input.min = "0";
                input.max = "100";
                input.step = "5";
                input.value = String(Math.round(
                    preference(slider.key, slider.key === "master" ? 0.7 : 1) * 100
                ));
                input.addEventListener("input", function () {
                    var value = Number(input.value) / 100;
                    if (preferences) {
                        var patch = {};
                        patch[slider.key] = value;
                        preferences.update({ audio: patch });
                    }
                    if (audio) {
                        audio.applyVolumes();
                    }
                });
                row.appendChild(input);
                controls.appendChild(row);
            });

            container.appendChild(controls);
        }

        return {
            id: "media",
            accessibility: {
                landmarkLabel: "Sound and captions",
                heading: "Sound",
                description:
                    "Volume controls, and the text of everything the game has played.",
                keyboardOperable: true,
                /*
                 * It updates as media arrives, but it never announces from
                 * here. The announcement manager already speaks each caption,
                 * and a second live region for media would compete with the
                 * transcript for speech -- the client has exactly two, on
                 * purpose.
                 */
                liveUpdates: true,
                graphicalOnly: false,
                textAlternative: null
            },
            displayName: "Sound",
            description: "Captions and volume, for every sound the game plays.",
            builtin: true,
            /*
             * Only for games that expose media.
             *
             * Progressive enhancement, the same as every other section: a game
             * with no sound has nothing to caption and nothing to turn down,
             * so it gets no panel rather than an empty one with six dead
             * sliders.
             *
             * The announcer still speaks a caption when there is no widget to
             * record it in, so a game that calls `push_media()` without
             * declaring the feature loses the durable list but not the text.
             * The information reaches the player either way.
             */
            requiredCapabilities: ["media"],
            defaultRegion: "aside",
            defaultSize: { height: 260 },
            /*
             * Subscribed to `media` for the sake of the widget palette's
             * capability filter, but playback is driven by the shell's own
             * media handler rather than from `update`. Ambient media and
             * one-off media arrive through the same message and mean different
             * things; the store cannot tell them apart, and the engine can.
             */
            subscriptions: ["media"],

            mount: function (context) {
                context.element.textContent = "";
                // Explicitly off. Captions are spoken by the announcer; this
                // panel is the durable record you come to on purpose.
                context.element.setAttribute("aria-live", "off");

                buildControls(context.element);

                imageEl = document.createElement("div");
                imageEl.className = "aetos-media__image-holder";
                context.element.appendChild(imageEl);

                listEl = document.createElement("ul");
                listEl.className = "aetos-media__captions";
                /*
                 * Focusable, because it scrolls. Arrow keys scroll whatever
                 * has focus, so a scrolling region outside the tab order
                 * cannot be scrolled by keyboard at all. Fourth instance in
                 * this client, and the first written in from the start rather
                 * than found by axe afterwards.
                 */
                listEl.setAttribute("tabindex", "0");
                /*
                 * No `role="region"` here.
                 *
                 * A role on a <ul> replaces its list semantics, which orphans
                 * every <li> inside it -- axe reports it as `listitem`, and a
                 * screen reader stops announcing "list, 12 items". A0 made
                 * exactly this mistake once already, while *fixing* a
                 * scrollable region, and it is worth the comment because the
                 * wrong version looks more accessible than the right one.
                 *
                 * `tabindex` and a label are all a scrolling region needs.
                 */
                listEl.setAttribute("aria-label", "Captions");
                context.element.appendChild(listEl);

                renderCaptions();
                return context.element;
            },

            destroy: function () {
                listEl = null;
                imageEl = null;
            },

            /*
             * The engine arrives after the widget, because the engine writes
             * captions into the widget and the widget's controls drive the
             * engine.
             *
             * A setter, not an assignment onto this object: the closures above
             * captured `audio` at creation, so `widget.audio = engine` would
             * set a property nothing reads and leave every control inert while
             * looking entirely correct. Fifth instance of that trap in this
             * client and the first anticipated rather than discovered.
             */
            setAudio: function (engine) { audio = engine; return true; },
            record: record,
            showImage: showImage,
            captions: function () { return captions.slice(); }
        };
    }

    window.AetosCaptions = {
        createWidget: createWidget,
        MAX_CAPTIONS: MAX_CAPTIONS,
        SLIDERS: SLIDERS.slice()
    };

})(window, document);
