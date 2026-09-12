/*
 * Aetos audio.  Addendum A.58, A.79, A.84.  Milestone M18.
 *
 * Sound the player controls, and that never carries information alone.
 *
 * THE GATE: A11Y-MEDIA-001. No gameplay-essential information may exist only
 * in audio.
 *
 * Aetos cannot enforce that inside a sound file -- it cannot listen to one and
 * describe it, and inventing a caption would be confidently wrong to precisely
 * the player who cannot check it. What it *can* do is make sure every
 * non-decorative sound is also **text**: captioned in the transcript and
 * announced to a screen reader. A player with the volume at zero, or no
 * speakers, or no hearing, receives everything a player with headphones does.
 *
 * So this module plays sound as a *secondary* channel. The caption is the
 * primary one, and it is emitted whether or not anything is audible -- including
 * when playback fails, when the file 404s, and when the category is muted.
 * Tying the text to successful playback would mean the players who most need
 * the text are the ones least likely to get it.
 *
 * DECORATIVE MEDIA IS THE EXCEPTION (A11Y-MEDIA-003). `decorative: true` is the
 * game asserting that this sound carries nothing -- a wind loop, a UI click --
 * and such sounds are played silently, with no caption and no announcement.
 * It is an assertion, not a validation: a game that marks its combat cues
 * decorative has lied to its own players and no client can catch that.
 *
 * NOTHING PLAYS UNTIL THE PLAYER HAS INTERACTED. Browsers refuse autoplay, and
 * rightly. Aetos does not fight it, does not nag, and above all does not fail
 * silently: sound that could not start is reported once, in text, with what to
 * do about it.
 *
 * EVERY CATEGORY HAS A SLIDER (A11Y-MEDIA-002). A sound the player cannot turn
 * down is a sound they cannot escape, so a media descriptor whose category has
 * no control is rejected on the server rather than played uncontrollably.
 */

(function (window, document) {
    "use strict";

    /*
     * Categories, in the order their controls appear.
     *
     * Fixed rather than free text: each one is a volume slider, and a category
     * the player has no slider for is a sound they cannot turn down.
     */
    var CATEGORIES = ["music", "ambience", "effect", "ui", "voice"];

    //: Simultaneous sounds. Beyond this, a burst is dropped rather than
    //: layered -- forty overlapping effects are not louder information, they
    //: are noise, and on a screen reader they are forty interruptions.
    var MAX_CONCURRENT = 8;

    //: How long a one-off sound may run before it is considered finished and
    //: its slot released, in case a browser never fires `ended`.
    var MAX_ONESHOT_MS = 30000;

    function createAudio(services) {
        var settings = services || {};
        var announce = settings.announce || function () {};
        var caption = settings.caption || function () {};
        var preferences = settings.preferences || null;

        //: Currently playing ambient media, keyed by id, so a sync that
        //: repeats a descriptor does not restart the track.
        var ambient = {};
        var oneshots = [];
        var blockedReported = false;
        var unsupportedReported = false;

        function preference(path, fallback) {
            if (!preferences || typeof preferences.value !== "function") {
                return fallback;
            }
            var found = preferences.value(path, fallback);
            return found === undefined ? fallback : found;
        }

        /*
         * The volume a sound should actually play at.
         *
         * Three multipliers: the game's own suggestion for this item, the
         * player's slider for its category, and the master. The player's
         * settings can always reach zero, so a game cannot insist on being
         * heard.
         */
        function effectiveVolume(item) {
            if (preference("audio.muted", false)) {
                return 0;
            }
            var master = Number(preference("audio.master", 0.7));
            var category = Number(preference("audio." + item.category, 1));
            var own = typeof item.volume === "number" ? item.volume : 1;
            var level = master * category * own;
            if (!isFinite(level)) {
                return 0;
            }
            return Math.min(Math.max(level, 0), 1);
        }

        /*
         * Emit the text half of a piece of media.
         *
         * Called for every non-decorative item, **before** any attempt to play
         * it and regardless of whether that attempt succeeds. The caption is
         * the information; the sound is an accompaniment.
         */
        function describe(item) {
            if (item.decorative) {
                return null;
            }
            var text = item.caption || item.description;
            if (!text) {
                /*
                 * No caption, and not marked decorative.
                 *
                 * The game has published audio some of its players cannot
                 * receive. Aetos says so rather than papering over it: a
                 * developer who never hears about this will never fix it, and
                 * a player who is missing something deserves to know that they
                 * are, rather than being left to wonder.
                 */
                text = "Uncaptioned " + item.category + " audio.";
            }
            caption(text, item);
            announce(text, {
                category: "media",
                // Advisory. The player's own preferences decide what is
                // actually spoken (A.76) -- media does not get to shout.
                priority: item.category === "voice" ? "important" : "normal"
            });
            return text;
        }

        function canPlay() {
            if (typeof window.Audio !== "function") {
                if (!unsupportedReported) {
                    unsupportedReported = true;
                    caption("This browser cannot play audio. Captions will still appear.", {});
                }
                return false;
            }
            return true;
        }

        /*
         * Report, once, that the browser refused to start audio.
         *
         * Once, because a blocked autoplay policy blocks *every* sound, and a
         * message per sound would be its own kind of noise. In text, because a
         * player who cannot hear the sounds is exactly the person who needs to
         * know why the ones they were told about are not arriving.
         */
        function reportBlocked() {
            if (blockedReported) {
                return;
            }
            blockedReported = true;
            caption(
                "Sound is waiting for you to interact with the page -- your browser " +
                "blocks audio until then. Click or press a key and it will start. " +
                "Captions appear either way.",
                {}
            );
        }

        function element(item) {
            var audio = new window.Audio(item.url);
            audio.volume = effectiveVolume(item);
            audio.loop = item.loop === true;
            audio.preload = "auto";
            return audio;
        }

        function start(audio, item) {
            var attempt;
            try {
                attempt = audio.play();
            } catch (err) {
                reportBlocked();
                return false;
            }
            if (attempt && typeof attempt.catch === "function") {
                attempt.catch(function () {
                    // Autoplay refusal and a failed load look the same here.
                    // Both mean the player is not hearing this, and both are
                    // already covered by the caption.
                    reportBlocked();
                });
            }
            return true;
        }

        /* --- One-off media ------------------------------------------------ */

        /*
         * Play something that happened.
         *
         * The caption is emitted first, and unconditionally. Everything after
         * it is best-effort.
         */
        function play(item) {
            if (!item || !item.url) {
                return null;
            }
            describe(item);

            if (!canPlay() || effectiveVolume(item) === 0) {
                return null;
            }
            if (oneshots.length >= MAX_CONCURRENT) {
                // Dropped rather than layered. The caption already went out,
                // so nothing is lost but the sound.
                return null;
            }

            var audio = element(item);
            var entry = { audio: audio, item: item };
            oneshots.push(entry);

            function release() {
                var index = oneshots.indexOf(entry);
                if (index !== -1) {
                    oneshots.splice(index, 1);
                }
            }
            audio.addEventListener("ended", release);
            audio.addEventListener("error", release);
            window.setTimeout(release, MAX_ONESHOT_MS);

            start(audio, item);
            return entry;
        }

        /* --- Ambient media ------------------------------------------------ */

        /*
         * Reconcile what is playing with what should be.
         *
         * A diff, not a restart. The server sends ambient media as *state*, so
         * a sync arriving every few seconds must not restart the music -- which
         * would be both unpleasant and, for anyone relying on a sound to know
         * where they are, actively confusing.
         */
        function sync(section) {
            var items = (section && section.items) || [];
            var wanted = {};

            items.forEach(function (item) {
                if (!item || !item.url) {
                    return;
                }
                wanted[item.id] = item;
                if (ambient[item.id]) {
                    // Already playing: adjust volume only, in case the player
                    // moved a slider.
                    ambient[item.id].audio.volume = effectiveVolume(item);
                    return;
                }
                describe(item);
                if (!canPlay() || effectiveVolume(item) === 0) {
                    // Recorded as playing at zero, so it is not re-announced
                    // on every subsequent sync and so raising the slider later
                    // is what starts it.
                    ambient[item.id] = { audio: element(item), item: item, started: false };
                    return;
                }
                var audio = element(item);
                ambient[item.id] = { audio: audio, item: item, started: true };
                start(audio, item);
            });

            Object.keys(ambient).forEach(function (id) {
                if (!wanted[id]) {
                    stopOne(id);
                }
            });

            return Object.keys(ambient).length;
        }

        function stopOne(id) {
            var entry = ambient[id];
            if (!entry) {
                return false;
            }
            try {
                entry.audio.pause();
                entry.audio.currentTime = 0;
            } catch (err) {
                // A element that never loaded cannot be paused. Nothing to do.
            }
            delete ambient[id];
            return true;
        }

        /*
         * Stop everything, now.  A11Y-MEDIA-002, A.84.
         *
         * The control somebody reaches for when sound has become unbearable,
         * so it is immediate and total, and it does not need the player to
         * find the right slider first.
         */
        function stopAll() {
            Object.keys(ambient).forEach(stopOne);
            oneshots.slice().forEach(function (entry) {
                try {
                    entry.audio.pause();
                } catch (err) {
                    // Already gone.
                }
            });
            oneshots.length = 0;
            announce("All sound stopped.", { category: "system", priority: "important" });
            return true;
        }

        /*
         * Re-apply the player's volumes to what is already playing.
         *
         * Without this a slider would only affect the *next* sound, which for
         * ambient music means it appears not to work at all.
         */
        function applyVolumes() {
            Object.keys(ambient).forEach(function (id) {
                var entry = ambient[id];
                var level = effectiveVolume(entry.item);
                entry.audio.volume = level;
                if (level > 0 && !entry.started && canPlay()) {
                    entry.started = true;
                    start(entry.audio, entry.item);
                } else if (level === 0 && entry.started) {
                    try {
                        entry.audio.pause();
                    } catch (err) {
                        // Nothing to pause.
                    }
                    entry.started = false;
                }
            });
            oneshots.forEach(function (entry) {
                entry.audio.volume = effectiveVolume(entry.item);
            });
            return true;
        }

        return {
            play: play,
            sync: sync,
            stopAll: stopAll,
            applyVolumes: applyVolumes,
            effectiveVolume: effectiveVolume,
            playing: function () { return Object.keys(ambient).slice(); },
            oneshotCount: function () { return oneshots.length; }
        };
    }

    window.AetosAudio = {
        create: createAudio,
        CATEGORIES: CATEGORIES.slice(),
        MAX_CONCURRENT: MAX_CONCURRENT
    };

})(window, document);
