/*
 * Aetos reads the game aloud.  A15.
 *
 * WHY THIS EXISTS. Gary turned on the option called "How much is announced",
 * played, and heard nothing:
 *
 *     *"ok I have the reading turned on but it doesnt read out loud"*
 *
 * The client was behaving exactly as designed, and the design was wrong. Aetos
 * wrote announcements into an ARIA live region and left the speaking to a screen
 * reader -- correct for somebody running NVDA, and silence for everybody else.
 * The setting's own wording ("what is spoken aloud") promised speech the client
 * never produced.
 *
 * The population that wants text read to them is much larger than the
 * population running a screen reader: people with dyslexia, people with low
 * vision who have never set up assistive technology, people whose eyes are tired
 * at the end of a long session, people who want to listen while doing something
 * else. Telling all of them to install NVDA is not an accessibility answer.
 *
 * WHAT IT IS. A *renderer* of the announcer's output. It is handed messages the
 * announcer has already decided should be heard, and it knows nothing about
 * categories, quiet mode, review mode or flood control -- see the `write`
 * function in announcer.js for why the hook is where it is. Duplicating any of
 * that policy here would guarantee the two eventually disagreed about what a
 * player asked for.
 *
 * WHAT IT IS NOT. It is not a screen reader and does not pretend to be one. It
 * reads what the client decided to announce; it cannot describe the interface,
 * navigate by heading, or read a control's state. Somebody who needs those needs
 * a real screen reader, and this must not get in their way -- hence off by
 * default and a warning in its own description.
 *
 * NO DEPENDENCY. `window.speechSynthesis` is part of the platform in every
 * browser at the published floor. Nothing is downloaded, nothing is sent
 * anywhere, and no audio leaves the machine. The voices are the ones the
 * operating system already has.
 */

(function (window) {
    "use strict";

    /*
     * Speech is off unless somebody asks for it.
     *
     * A client that starts talking on first load is alarming, and for a screen
     * reader user it would be actively harmful: two voices reading the same
     * text over each other. Aetos cannot detect a screen reader and must never
     * try -- that is fingerprinting, and A.72 forbids it -- so the only honest
     * default is silence plus a clearly named control.
     */
    function createSpeech(services) {
        var preferences = services.preferences || null;
        var synth = services.synth
            || (typeof window.speechSynthesis !== "undefined" ? window.speechSynthesis : null);
        var Utterance = services.Utterance
            || (typeof window.SpeechSynthesisUtterance !== "undefined"
                ? window.SpeechSynthesisUtterance
                : null);

        //: Set once the browser has let us speak. See `unlock`.
        var permitted = false;
        var wanted = false;

        function available() {
            return !!(synth && Utterance);
        }

        function preferenceValue(path, fallback) {
            if (!preferences || typeof preferences.value !== "function") {
                return fallback;
            }
            var value = preferences.value(path);
            return value === undefined ? fallback : value;
        }

        function enabled() {
            return available() && preferenceValue("speech.enabled", false) === true;
        }

        /**
         * The voice the player chose, if it is still installed.
         *
         * @returns {SpeechSynthesisVoice|null} A voice, or null for the default.
         */
        function chosenVoice() {
            var name = preferenceValue("speech.voice", null);
            if (!name || !synth.getVoices) {
                return null;
            }
            var voices = synth.getVoices() || [];
            for (var index = 0; index < voices.length; index += 1) {
                if (voices[index].name === name) {
                    return voices[index];
                }
            }
            /*
             * The named voice is gone -- a different machine, or the language
             * pack was removed. Fall back to the browser's default rather than
             * refusing to speak: silence is the failure this module exists to
             * fix, and it would be a strange way to report a missing voice.
             */
            return null;
        }

        /*
         * Browsers require a user gesture before audio.
         *
         * Speaking before one produces no sound and, in some browsers, leaves
         * the synthesiser in a state where the *next* utterance is dropped too.
         * So the first gesture of the session arms it, and until then requests
         * are discarded rather than queued -- a queue would empty itself in one
         * burst the moment somebody clicked, reading out everything that had
         * happened since the page loaded.
         */
        function unlock() {
            permitted = true;
        }

        /**
         * Say something, if speech is on.
         *
         * @param {string} message The text to speak.
         * @param {object} options `urgent` cancels whatever is being said.
         * @returns {boolean} Whether anything was spoken.
         */
        function speak(message, options) {
            if (!enabled() || !permitted || !message) {
                return false;
            }
            var settings = options || {};

            /*
             * Urgent messages interrupt; everything else queues behind what is
             * already being said.
             *
             * This mirrors the two live regions exactly, and for the same
             * reason: a channel that interrupts constantly stops being an
             * interruption, and the one message that genuinely needed to cut in
             * is the one nobody hears.
             */
            if (settings.urgent && synth.cancel) {
                synth.cancel();
            }

            var utterance = new Utterance(String(message));
            var voice = chosenVoice();
            if (voice) {
                utterance.voice = voice;
            }
            utterance.rate = clamp(preferenceValue("speech.rate", 1), 0.5, 2.5);
            utterance.volume = clamp(preferenceValue("speech.volume", 1), 0, 1);
            try {
                synth.speak(utterance);
            } catch (err) {
                // Degrade, never raise: this runs in a websocket-driven client
                // and a throwing renderer must not take the announcer with it.
                return false;
            }
            return true;
        }

        function clamp(value, low, high) {
            var number = parseFloat(value);
            if (!isFinite(number)) {
                return low;
            }
            return Math.min(high, Math.max(low, number));
        }

        /*
         * Stop talking, now.
         *
         * The single most important control in this module. Somebody who has
         * just been read a two-hundred-word room description needs a way to cut
         * it off that does not involve finding a setting, and speech that cannot
         * be stopped is worse than no speech.
         */
        function stop() {
            if (available() && synth.cancel) {
                synth.cancel();
            }
            return true;
        }

        /**
         * The voices this machine has, for the picker.
         *
         * @returns {Array} Objects with `name` and `lang`.
         */
        function voices() {
            if (!available() || !synth.getVoices) {
                return [];
            }
            return (synth.getVoices() || []).map(function (voice) {
                return { name: voice.name, lang: voice.lang };
            });
        }

        /*
         * Stop speaking the moment speech is turned off.
         *
         * Without this, switching it off leaves the current utterance running
         * to the end -- which reads as the control not working, and is the
         * first thing somebody does when they want the talking to stop.
         */
        function watchPreferences() {
            if (!preferences || typeof preferences.subscribe !== "function") {
                return;
            }
            wanted = enabled();
            preferences.subscribe(function () {
                var now = enabled();
                if (wanted && !now) {
                    stop();
                }
                wanted = now;
            });
        }

        watchPreferences();

        return {
            speak: speak,
            stop: stop,
            voices: voices,
            unlock: unlock,
            isAvailable: available,
            isEnabled: enabled,
            isPermitted: function () { return permitted; }
        };
    }

    window.AetosSpeech = { create: createSpeech };

})(window);
