/*
 * Aetos cognitive support.  Addendum A.42, A.43, A.45, A.47, A.48.
 *
 * Reminders and a task list, both entirely the player's own.
 *
 * THE HARD RULE: REMINDERS ARE ONLY EVER CREATED ON REQUEST (A11Y-COG-005).
 *
 * Aetos never invents one. It does not ask "did you remember to talk to
 * everyone?", it does not notice you have not visited a room lately, and it
 * does not build a checklist from your behaviour.
 *
 * A client that generated its own reminders would be doing two objectionable
 * things at once: inferring intent, which A11Y-COG-002 forbids, and nagging --
 * which for a player who reached for a memory aid in the first place is
 * actively counterproductive. Support means holding what you asked it to hold,
 * not deciding what you ought to be doing.
 *
 * TASKS ARE NOT QUESTS. A task here is a note to self. It is not a game
 * objective, Aetos does not know the game has objectives, and nothing in this
 * file talks to the server.
 *
 * QUIET MODE IS ABOUT INTERRUPTION, NOT INFORMATION (A.48). It suppresses
 * unsolicited announcements and leaves the transcript, the history and every
 * direct answer untouched. A player in Quiet Mode who asks a question still
 * gets an answer -- quiet is not deaf, and it is certainly not blind.
 */

(function (window) {
    "use strict";

    var NAMESPACE = "reminders";
    var MAX_ITEMS = 200;
    var MAX_TEXT = 300;

    /*
     * When a reminder should surface.
     *
     * Every one of these is a condition the player stated. There is no
     * "when Aetos thinks you have forgotten".
     */
    var TRIGGERS = ["pinned", "here", "next-session", "after"];

    function normalize(raw) {
        if (!raw || typeof raw !== "object") {
            return null;
        }
        var text = String(raw.text || "").trim();
        if (!text) {
            return null;
        }
        return {
            id: String(raw.id || ("rem-" + text.toLowerCase().slice(0, 40))),
            kind: raw.kind === "task" ? "task" : "reminder",
            text: text.slice(0, MAX_TEXT),
            trigger: TRIGGERS.indexOf(raw.trigger) === -1 ? "pinned" : raw.trigger,
            // Where it applies, for "remind me when I am back here".
            locationId: raw.locationId ? String(raw.locationId) : null,
            locationName: raw.locationName ? String(raw.locationName).slice(0, 80) : null,
            completed: raw.completed === true,
            createdAt: Number(raw.createdAt) || 0
        };
    }

    function createCognitive(services) {
        var settings = services || {};
        var storage = settings.storage || null;
        var announce = settings.announce || function () {};
        var now = settings.now || function () { return Date.now(); };

        var items = [];
        var surfacedThisVisit = {};

        function load() {
            if (!storage) {
                return Promise.resolve([]);
            }
            return storage.all(NAMESPACE).then(function (rows) {
                items = (rows || [])
                    .map(function (row) { return row.value; })
                    .slice(0, MAX_ITEMS)
                    .map(normalize)
                    .filter(Boolean);
                return items.slice();
            }).catch(function () { return []; });
        }

        function save(raw) {
            var item = normalize(raw);
            if (!item) {
                return Promise.reject(new Error("A reminder needs some text."));
            }
            if (!item.createdAt) {
                item.createdAt = now();
            }
            if (!storage) {
                return Promise.reject(new Error("No local storage available."));
            }
            return storage.put(NAMESPACE, item.id, item).then(function () {
                return load().then(function () { return item; });
            });
        }

        function remove(id) {
            if (!storage) {
                return Promise.resolve(false);
            }
            return storage.remove(NAMESPACE, id).then(function () {
                return load().then(function () { return true; });
            });
        }

        function complete(id, done) {
            var found = items.filter(function (item) { return item.id === id; })[0];
            if (!found) {
                return Promise.resolve(false);
            }
            found.completed = done !== false;
            return save(found);
        }

        /* --- Surfacing --------------------------------------------------- */

        function pinned() {
            return items.filter(function (item) {
                return item.trigger === "pinned" && !item.completed;
            });
        }

        function tasks() {
            return items.filter(function (item) { return item.kind === "task"; });
        }

        /*
         * Location reminders, surfaced once per visit.
         *
         * Once, because a reminder that repeats every sync while the player
         * stands in a room stops being a reminder and becomes an obstacle --
         * and the player who most needs the feature is the least able to
         * tolerate that.
         */
        function observeRoom(room) {
            if (!room || !room.id) {
                return [];
            }
            var due = items.filter(function (item) {
                return item.trigger === "here" &&
                    !item.completed &&
                    item.locationId === room.id &&
                    !surfacedThisVisit[item.id];
            });
            due.forEach(function (item) {
                surfacedThisVisit[item.id] = true;
                announce("Reminder: " + item.text, {
                    category: "system",
                    priority: "important"
                });
            });
            // Leaving clears the marks, so returning later surfaces them again.
            Object.keys(surfacedThisVisit).forEach(function (id) {
                var item = items.filter(function (entry) { return entry.id === id; })[0];
                if (item && item.locationId !== room.id) {
                    delete surfacedThisVisit[id];
                }
            });
            return due;
        }

        /*
         * Reminders held for the next session.
         *
         * Surfaced once, on request, rather than fired at connect. Arriving to
         * a queue of announcements is exactly the kind of start that makes
         * somebody close the tab.
         */
        function nextSession() {
            return items.filter(function (item) {
                return item.trigger === "next-session" && !item.completed;
            });
        }

        /*
         * A resume summary.  A11Y-COG-004.
         *
         * Everything here is labelled "last known" until a fresh sync arrives,
         * because presenting cached state as current is how a player acts on a
         * world that has moved on.
         */
        function resumeCard(synced) {
            var store = settings.store;
            var room = (store && store.get("room")) || {};
            var prefix = synced ? "" : "Last known: ";
            var lines = [];

            if (room.name) {
                lines.push(prefix + room.name + ".");
            }
            var waiting = nextSession();
            if (waiting.length) {
                lines.push(waiting.length +
                    (waiting.length === 1 ? " reminder" : " reminders") +
                    " saved for this session.");
            }
            var open = tasks().filter(function (task) { return !task.completed; });
            if (open.length) {
                lines.push(open.length +
                    (open.length === 1 ? " open task." : " open tasks."));
            }
            return { synced: synced === true, lines: lines };
        }

        return {
            load: load,
            save: save,
            remove: remove,
            complete: complete,
            pinned: pinned,
            tasks: tasks,
            nextSession: nextSession,
            observeRoom: observeRoom,
            resumeCard: resumeCard,
            all: function () { return items.slice(); },
            count: function () { return items.length; }
        };
    }

    window.AetosCognitive = {
        create: createCognitive,
        normalize: normalize,
        NAMESPACE: NAMESPACE,
        TRIGGERS: TRIGGERS.slice(),
        MAX_ITEMS: MAX_ITEMS
    };

})(window);
