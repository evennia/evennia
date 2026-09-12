/*
 * Aetos local relationships.
 *
 * A player's own opinion of the people they meet: Friend, Neutral, Enemy, plus
 * any tags they invent -- Guildmate, Trader, Avoid, Suspect.
 *
 * THIS DATA NEVER LEAVES THE BROWSER.
 *
 * Blueprint section 2.3 forbids storing a player's relationships on the game
 * server, and section 24 is explicit that these tags do not modify server-side
 * PvP or social systems. Marking someone an Enemy is a private note to yourself,
 * not a declaration the game or the other player can see.
 *
 * That has a consequence worth stating plainly: nothing here is ever sent, and
 * no code path exists to send it. A relationship tag is not a command, so it
 * cannot leak through the command dispatcher either.
 *
 * KEYED BY NAME, NOT BY ID.
 *
 * A player thinks "Aric", not "#42". Database ids are also not stable across the
 * things a player cares about -- a character can be recreated, and an id means
 * nothing on a different game. Names are what a player recognises, so names are
 * the key.
 */

(function (window) {
    "use strict";

    //: The three categories every player gets without inventing anything.
    var CATEGORIES = ["friend", "neutral", "enemy"];

    var CATEGORY_LABELS = {
        friend: "Friend",
        neutral: "Neutral",
        enemy: "Enemy"
    };

    var MAX_TAG_LENGTH = 40;
    var MAX_TAGS = 20;

    function normalizeKey(name) {
        return String(name || "").trim().toLowerCase();
    }

    function createRelationships(storage) {

        function get(name) {
            var key = normalizeKey(name);
            if (!key || !storage) {
                return window.Promise.resolve(null);
            }
            return storage.get("relationships", key);
        }

        function save(name, record) {
            var key = normalizeKey(name);
            if (!key || !storage) {
                return window.Promise.resolve(false);
            }
            return storage.put("relationships", key, record).then(function () {
                return true;
            });
        }

        /*
         * Set someone's category.
         *
         * Setting "neutral" with no tags removes the record entirely rather than
         * storing a row that says nothing. A player who un-tags someone should
         * not leave a trace behind -- this is their private data and "I have no
         * opinion" is the absence of a record, not a record of absence.
         */
        function setCategory(name, category) {
            if (CATEGORIES.indexOf(category) === -1) {
                return window.Promise.reject(new Error("Unknown category: " + category));
            }
            return get(name).then(function (existing) {
                var record = existing || { name: String(name), tags: [] };
                record.category = category;
                record.name = record.name || String(name);
                if (category === "neutral" && !(record.tags || []).length) {
                    return storage.remove("relationships", normalizeKey(name))
                        .then(function () { return null; });
                }
                return save(name, record).then(function () { return record; });
            });
        }

        function addTag(name, tag) {
            var clean = String(tag || "").trim().slice(0, MAX_TAG_LENGTH);
            if (!clean) {
                return window.Promise.resolve(null);
            }
            return get(name).then(function (existing) {
                var record = existing || { name: String(name), category: "neutral", tags: [] };
                record.tags = record.tags || [];
                // Case-insensitive comparison, so "Trader" and "trader" are one
                // tag rather than two the player has to keep straight.
                var seen = record.tags.some(function (entry) {
                    return entry.toLowerCase() === clean.toLowerCase();
                });
                if (!seen && record.tags.length < MAX_TAGS) {
                    record.tags.push(clean);
                }
                return save(name, record).then(function () { return record; });
            });
        }

        function removeTag(name, tag) {
            return get(name).then(function (existing) {
                if (!existing) {
                    return null;
                }
                existing.tags = (existing.tags || []).filter(function (entry) {
                    return entry.toLowerCase() !== String(tag).toLowerCase();
                });
                if (existing.category === "neutral" && !existing.tags.length) {
                    return storage.remove("relationships", normalizeKey(name))
                        .then(function () { return null; });
                }
                return save(name, existing).then(function () { return existing; });
            });
        }

        function clear(name) {
            var key = normalizeKey(name);
            if (!key || !storage) {
                return window.Promise.resolve(false);
            }
            return storage.remove("relationships", key);
        }

        function all() {
            if (!storage) {
                return window.Promise.resolve([]);
            }
            return storage.all("relationships").then(function (rows) {
                return rows.map(function (row) { return row.value; });
            });
        }

        /*
         * Decorate a list of entities with the player's own relationship data.
         *
         * Returns a copy: the store holds authoritative server state, and mixing
         * local opinion into it would make the two indistinguishable later.
         */
        function decorate(entities) {
            if (!storage || !entities || !entities.length) {
                return window.Promise.resolve(entities || []);
            }
            return window.Promise.all(entities.map(function (entity) {
                return get(entity.name).then(function (record) {
                    if (!record) {
                        return entity;
                    }
                    return Object.assign({}, entity, {
                        relationship: record.category || "neutral",
                        tags: record.tags || []
                    });
                });
            }));
        }

        return {
            CATEGORIES: CATEGORIES.slice(),
            CATEGORY_LABELS: CATEGORY_LABELS,
            get: get,
            setCategory: setCategory,
            addTag: addTag,
            removeTag: removeTag,
            clear: clear,
            all: all,
            decorate: decorate,
            normalizeKey: normalizeKey
        };
    }

    window.AetosRelationships = {
        create: createRelationships,
        CATEGORIES: CATEGORIES.slice(),
        CATEGORY_LABELS: CATEGORY_LABELS
    };

})(window);
