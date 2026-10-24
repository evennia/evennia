/*
 * Aetos notes.
 *
 * A player's own notebook: what they worked out, who to avoid, where the locked
 * door was. Attachable to a person, a room, an item, or nothing in particular.
 *
 * LOCAL, LIKE EVERYTHING ELSE A PLAYER OWNS.
 *
 * Notes are stored in the browser and never sent to the game server (blueprint
 * sections 2.3 and 25). A note about another player is private in the strongest
 * sense available: the server has no copy, so it cannot be read by staff,
 * subpoenaed from the game, or leaked by a database dump.
 *
 * Map notes and POIs (section 26) are notes with a room subject and a `poi`
 * flag, rather than a parallel system -- the same search, the same storage, the
 * same privacy guarantee, one implementation to keep correct.
 */

(function (window, document) {
    "use strict";

    var MAX_SUBJECT_LENGTH = 200;
    var MAX_BODY_LENGTH = 20000;
    var MAX_TAGS = 20;
    var MAX_TAG_LENGTH = 40;

    //: What a note can be attached to. "free" is a note about nothing in
    //: particular, which is a legitimate and common case.
    var SUBJECT_KINDS = ["character", "object", "room", "free"];

    function makeId(subject, kind) {
        // Deterministic id from subject and kind, so re-noting the same person
        // edits the existing note instead of accumulating duplicates the player
        // then has to reconcile.
        return String(kind || "free") + ":" + String(subject || "").trim().toLowerCase();
    }

    function createNotes(storage, options) {
        var opts = options || {};
        // Time is injected rather than read here, so tests are deterministic and
        // the module has no hidden dependency on the clock.
        var now = opts.now || function () { return new Date().toISOString(); };

        function normalize(note) {
            var tags = (note.tags || [])
                .map(function (tag) { return String(tag).trim().slice(0, MAX_TAG_LENGTH); })
                .filter(Boolean)
                .slice(0, MAX_TAGS);
            return {
                id: note.id,
                subject: String(note.subject || "").slice(0, MAX_SUBJECT_LENGTH),
                kind: SUBJECT_KINDS.indexOf(note.kind) === -1 ? "free" : note.kind,
                body: String(note.body || "").slice(0, MAX_BODY_LENGTH),
                tags: tags,
                pinned: note.pinned === true,
                poi: note.poi === true,
                icon: note.icon || null,
                created: note.created || now(),
                updated: now()
            };
        }

        /*
         * Save a note, MERGING with any existing note for the same subject.
         *
         * Merge rather than replace, deliberately. A caller that omits `tags`
         * means "leave the tags alone", not "delete them" -- and silently
         * discarding a player's own tags because a field was not passed is
         * exactly the kind of quiet data loss that personal data must not
         * suffer.
         *
         * Clearing is still possible: pass an explicit empty value.
         */
        function save(note) {
            if (!storage) {
                return window.Promise.resolve(null);
            }
            var id = note.id || makeId(note.subject, note.kind);
            return storage.get("notes", id).then(function (existing) {
                var merged = Object.assign({}, existing || {}, {});
                Object.keys(note).forEach(function (field) {
                    if (note[field] !== undefined) {
                        merged[field] = note[field];
                    }
                });
                merged.id = id;
                var record = normalize(merged);
                return storage.put("notes", id, record).then(function () { return record; });
            });
        }

        function get(id) {
            return storage ? storage.get("notes", id) : window.Promise.resolve(null);
        }

        function forSubject(subject, kind) {
            return get(makeId(subject, kind));
        }

        function remove(id) {
            return storage ? storage.remove("notes", id) : window.Promise.resolve(false);
        }

        function all() {
            if (!storage) {
                return window.Promise.resolve([]);
            }
            return storage.all("notes").then(function (rows) {
                return rows.map(function (row) { return row.value; });
            });
        }

        /*
         * Search notes.
         *
         * Matches subject, body and tags together, because a player looking for
         * "harbour" does not remember whether they wrote it in the title, the
         * text, or as a tag.
         */
        function search(query, filters) {
            var needle = String(query || "").trim().toLowerCase();
            var options = filters || {};
            return all().then(function (notes) {
                var matched = notes.filter(function (note) {
                    if (options.kind && note.kind !== options.kind) {
                        return false;
                    }
                    if (options.poi && !note.poi) {
                        return false;
                    }
                    if (options.tag) {
                        var wanted = options.tag.toLowerCase();
                        var hasTag = (note.tags || []).some(function (tag) {
                            return tag.toLowerCase() === wanted;
                        });
                        if (!hasTag) {
                            return false;
                        }
                    }
                    if (!needle) {
                        return true;
                    }
                    var haystack = [
                        note.subject,
                        note.body,
                        (note.tags || []).join(" ")
                    ].join(" ").toLowerCase();
                    return haystack.indexOf(needle) !== -1;
                });

                // Pinned first, then most recently updated. A player pins the
                // thing they keep coming back to; burying it under newer notes
                // would defeat the point of pinning.
                matched.sort(function (a, b) {
                    if (a.pinned !== b.pinned) {
                        return a.pinned ? -1 : 1;
                    }
                    return String(b.updated).localeCompare(String(a.updated));
                });
                return matched;
            });
        }

        function tags() {
            return all().then(function (notes) {
                var seen = {};
                notes.forEach(function (note) {
                    (note.tags || []).forEach(function (tag) { seen[tag] = true; });
                });
                return Object.keys(seen).sort();
            });
        }

        return {
            SUBJECT_KINDS: SUBJECT_KINDS.slice(),
            makeId: makeId,
            save: save,
            get: get,
            forSubject: forSubject,
            remove: remove,
            all: all,
            search: search,
            tags: tags
        };
    }

    /* ------------------------------------------------------------------
     * Notes widget
     * ------------------------------------------------------------------ */

    function createNotesWidget(services) {
        var notes = services.notes;
        var announce = services.announce || function () {};

        function renderNote(note, onEdit, onDelete) {
            var item = document.createElement("li");
            item.className = "aetos-note";

            var heading = document.createElement("h3");
            heading.className = "aetos-note__subject";
            heading.textContent = (note.pinned ? "★ " : "") + note.subject;
            item.appendChild(heading);

            if (note.tags && note.tags.length) {
                var tagLine = document.createElement("p");
                tagLine.className = "aetos-note__tags";
                tagLine.textContent = note.tags.join(", ");
                item.appendChild(tagLine);
            }

            var body = document.createElement("p");
            body.className = "aetos-note__body";
            // A note is the player's own text. It is never markup, so it is
            // inserted as text -- no sanitiser needed because nothing is parsed.
            body.textContent = note.body;
            item.appendChild(body);

            var controls = document.createElement("div");
            controls.className = "aetos-note__controls";

            var editButton = document.createElement("button");
            editButton.type = "button";
            editButton.className = "aetos-list__button";
            editButton.textContent = "Edit";
            editButton.addEventListener("click", function () { onEdit(note); });
            controls.appendChild(editButton);

            var deleteButton = document.createElement("button");
            deleteButton.type = "button";
            deleteButton.className = "aetos-list__button";
            deleteButton.textContent = "Delete";
            deleteButton.addEventListener("click", function () { onDelete(note); });
            controls.appendChild(deleteButton);

            item.appendChild(controls);
            return item;
        }

        return {
            id: "notes",
            // Not live: notes change only when the player edits them, so nothing
            // here updates behind their back.
            accessibility: {
                landmarkLabel: "Your private notes",
                heading: "Notes",
                keyboardOperable: true,
                liveUpdates: false
            },
            displayName: "Notes",
            description: "Your own private notebook, stored in this browser.",
            builtin: true,
            defaultRegion: "aside",
            defaultSize: { height: 260 },
            subscriptions: [],

            mount: function (context) {
                var search = document.createElement("input");
                search.type = "search";
                search.className = "aetos-input aetos-notes__search";
                search.placeholder = "Search notes";
                // A bare search box is announced only as "edit"; the label says
                // what it searches.
                search.setAttribute("aria-label", "Search notes");

                var list = document.createElement("ul");
                list.className = "aetos-notes__list";

                var empty = document.createElement("p");
                empty.className = "aetos-notes__empty";
                empty.textContent = "No notes yet. Add one from any person, item or room.";

                context.element.appendChild(search);
                context.element.appendChild(empty);
                context.element.appendChild(list);

                context.searchEl = search;
                context.listEl = list;
                context.emptyEl = empty;

                function refresh() {
                    notes.search(search.value).then(function (found) {
                        list.textContent = "";
                        empty.hidden = found.length > 0;
                        found.forEach(function (note) {
                            list.appendChild(renderNote(note, function (target) {
                                services.editNote(target);
                            }, function (target) {
                                notes.remove(target.id).then(function () {
                                    announce("Note on " + target.subject + " deleted.");
                                    refresh();
                                });
                            }));
                        });
                    });
                }

                context.refresh = refresh;
                search.addEventListener("input", refresh);
                services.registerRefresh(refresh);
                refresh();
            }
        };
    }

    window.AetosNotes = {
        create: createNotes,
        createWidget: createNotesWidget,
        makeId: makeId,
        SUBJECT_KINDS: SUBJECT_KINDS.slice()
    };

})(window, document);
