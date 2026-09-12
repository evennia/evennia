/*
 * Aetos Review Mode.  Addendum A.17, A.18, A11Y-REV-001.
 *
 * Reading back through what happened, without the present tense shouting over
 * you while you do it.
 *
 * THE PROBLEM IT SOLVES. A player wants to re-read the tell that arrived during
 * a fight. They scroll back. New output keeps arriving, the console keeps
 * announcing, and on a braille display the review cursor is dragged forward
 * every time -- so they lose their place, repeatedly, while trying to read one
 * sentence. The game does not stop for them, and neither did the client.
 *
 * Review Mode stops the client. Low-priority announcements pause, the reading
 * position holds still, and events keep arriving into the canonical log where
 * they will be waiting.
 *
 * LEAVING DOES NOT REPLAY (A.17). This is the rule that makes it usable. Reading
 * seventeen held announcements in a row is worse than the interruption they were
 * held to avoid, so exiting produces a *count*:
 *
 *     "17 events occurred while reviewing. 2 tells, 11 combat events, 4 other."
 *
 * Then the player decides. That is the whole design: the client reports, the
 * player chooses, and nothing is thrown away in either direction.
 *
 * WHAT KEEPS SPEAKING. Critical and important messages still get through --
 * review is not a mute. Somebody reading their combat log should still be told
 * the connection dropped, because everything they are reading just became
 * potentially stale.
 *
 * NAVIGATION IS BY CATEGORY (A.18). "Previous tell" is the operation a player
 * actually wants, and it only exists because the game told Aetos which events
 * were tells -- Aetos never infers that by reading the words.
 */

(function (window) {
    "use strict";

    /*
     * Channels a player can step through.
     *
     * Deliberately short. A list of thirteen categories is a menu; these four
     * are the ones somebody reaches for mid-session.
     */
    var CHANNELS = ["tell", "chat", "combat", "system"];

    /*
     * The text of an event as a person reads or hears it.
     *
     * `originalText` carries the server's markup. Announcing it meant a screen
     * reader in Review Mode read out "span class equals color hyphen zero zero
     * two" before every coloured line, and searching it matched tag names
     * rather than words.
     */
    function readable(event) {
        if (!event) {
            return "";
        }
        return (event.plainText === undefined ? event.originalText : event.plainText) || "";
    }

    function createReview(services) {
        var settings = services || {};
        var log = settings.canonicalLog || null;
        var announcer = settings.announcer || null;
        var announce = settings.announce || function () {};

        var active = false;
        // Where the player is reading. Held across incoming events -- the whole
        // point is that new arrivals do not move it.
        var position = null;
        var enteredAtSequence = 0;

        function events() {
            return log ? log.all() : [];
        }

        /* --- Entering and leaving ---------------------------------------- */

        function enter() {
            if (active) {
                return false;
            }
            active = true;

            var all = events();
            enteredAtSequence = all.length ? all[all.length - 1].sequence : 0;
            // Start at the most recent event, which is where the player was
            // looking when they decided to stop and read.
            position = all.length ? all.length - 1 : null;

            if (announcer && announcer.beginReview) {
                announcer.beginReview();
            }
            announce("Review mode. " + all.length + " events. Escape to resume.", {
                category: "system",
                priority: "important"
            });
            return true;
        }

        /*
         * Leave, and summarise rather than replay.
         *
         * The summary counts what arrived *while reviewing*, taken from the
         * canonical log rather than from the announcement queue -- so it counts
         * what happened, not what would have been spoken. A player who has
         * muted combat still wants to know a fight occurred.
         */
        function exit() {
            if (!active) {
                return null;
            }
            active = false;
            position = null;

            var missed = events().filter(function (event) {
                return event.sequence > enteredAtSequence;
            });

            if (announcer && announcer.endReview) {
                announcer.endReview();
            }

            if (!missed.length) {
                announce("Resumed. Nothing happened while reviewing.", {
                    category: "system",
                    priority: "important"
                });
                return { total: 0, byCategory: {} };
            }

            var byCategory = {};
            missed.forEach(function (event) {
                byCategory[event.category] = (byCategory[event.category] || 0) + 1;
            });

            var parts = Object.keys(byCategory).map(function (category) {
                var count = byCategory[category];
                return count + " " + category + (count === 1 ? " event" : " events");
            });

            announce(
                "Resumed. " + missed.length +
                (missed.length === 1 ? " event" : " events") +
                " occurred while reviewing: " + parts.join(", ") + ".",
                { category: "system", priority: "important" }
            );

            return { total: missed.length, byCategory: byCategory, events: missed };
        }

        function toggle() {
            return active ? exit() : enter();
        }

        /* --- Navigation --------------------------------------------------- */

        /*
         * Read out the event at the current position.
         *
         * Announced as `important` so it is heard even in Review Mode, which is
         * suppressing everything else. The player asked for this one.
         */
        function speakCurrent() {
            var all = events();
            if (position === null || !all[position]) {
                announce("No events.", { category: "system", priority: "important" });
                return null;
            }
            var event = all[position];
            announce(
                (position + 1) + " of " + all.length + ". " +
                event.category + ". " + readable(event),
                { category: "system", priority: "important" }
            );
            return event;
        }

        function move(direction, category) {
            var all = events();
            if (!all.length) {
                return null;
            }
            if (position === null) {
                position = all.length - 1;
            }

            var index = position + direction;
            while (index >= 0 && index < all.length) {
                if (!category || all[index].category === category) {
                    position = index;
                    return speakCurrent();
                }
                index += direction;
            }

            // Said rather than silently doing nothing. A key that appears not
            // to work is worse than one that explains itself.
            announce(
                category
                    ? "No " + (direction < 0 ? "earlier" : "later") + " " + category + " events."
                    : (direction < 0 ? "Start of history." : "End of history."),
                { category: "system", priority: "important" }
            );
            return null;
        }

        function previous(category) { return move(-1, category); }
        function next(category) { return move(1, category); }

        function latest() {
            var all = events();
            position = all.length ? all.length - 1 : null;
            return speakCurrent();
        }

        /*
         * Search the canonical text.
         *
         * Canonical, not displayed. A player searching for something they saw
         * must find it even if a display rule has since hidden it -- which is
         * exactly the case where searching matters most.
         */
        function search(query) {
            var needle = String(query || "").trim().toLowerCase();
            if (!needle) {
                return [];
            }
            return events().filter(function (event) {
                return readable(event).toLowerCase().indexOf(needle) !== -1;
            });
        }

        function jumpTo(id) {
            var all = events();
            for (var i = 0; i < all.length; i++) {
                if (all[i].id === id) {
                    position = i;
                    return speakCurrent();
                }
            }
            return null;
        }

        return {
            enter: enter,
            exit: exit,
            toggle: toggle,
            previous: previous,
            next: next,
            latest: latest,
            search: search,
            jumpTo: jumpTo,
            speakCurrent: speakCurrent,
            isActive: function () { return active; },
            position: function () { return position; },
            missedCount: function () {
                return events().filter(function (event) {
                    return event.sequence > enteredAtSequence;
                }).length;
            }
        };
    }

    window.AetosReview = {
        create: createReview,
        CHANNELS: CHANNELS.slice()
    };

})(window);
