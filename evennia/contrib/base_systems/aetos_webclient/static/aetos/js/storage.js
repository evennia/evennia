/*
 * Aetos local storage.
 *
 * Everything personal a player accumulates -- layouts, notes, relationship tags,
 * macros, aliases, triggers, themes, map annotations -- lives here, in their
 * browser, under their control. None of it is sent to the game server
 * (blueprint sections 2.3 and 13).
 *
 * Three properties matter:
 *
 *   - SCOPED BY GAME. Stock Evennia already writes unscoped localStorage keys
 *     (`evenniaGoldenLayoutSavedState`), which two games on one origin would
 *     share. Aetos scopes its database per game so your notes about a player on
 *     one MUD never surface on another.
 *
 *   - NEVER CLOBBERS STOCK EVENNIA. Aetos uses IndexedDB, which is a separate
 *     store from localStorage entirely, and prefixes the few localStorage keys it
 *     does use. "Clear all Aetos data" must never delete a player's stock
 *     webclient layout.
 *
 *   - DEGRADES. A browser with IndexedDB blocked (private mode, strict settings)
 *     falls back to an in-memory store. The client keeps working for the session;
 *     it simply cannot remember anything afterwards, and says so.
 */

(function (window) {
    "use strict";

    /*
     * Schema version.
     *
     * **Bump this whenever a namespace is added.** IndexedDB only creates
     * object stores during an upgrade, so a new namespace on an unchanged
     * version means every existing player gets a database with no store for it
     * -- and the failure is a thrown transaction the first time anything writes
     * there, on their machine and not on a fresh one. E2 hit exactly that when
     * `display_rules` was added.
     *
     * The upgrade handler creates only missing stores, so bumping is safe and
     * loses nothing.
     *
     * 1 -> 2: added `display_rules` (E2).
     * 2 -> 3: added `reminders` (A5).
     */
    var DB_VERSION = 3;

    // Namespaces from blueprint section 13. Fixed here so that export, import,
    // the privacy panel and the clear operations can never drift apart.
    var NAMESPACES = [
        "layouts",
        "workspaces",
        "macros",
        "aliases",
        "triggers",
        "scripts",
        "variables",
        "relationships",
        "notes",
        "map_notes",
        "map_pois",
        "display_rules",
        "reminders",
        "themes",
        "keybindings",
        "preferences",
        "automation_profiles"
    ];

    // Prefix for the few tiny values that must be readable before the database
    // opens (boot preferences only). Namespaced so Aetos can never collide with
    // or clear Evennia's own localStorage keys.
    var LOCAL_PREFIX = "aetos:";

    /*
     * Build the per-game scope key.
     *
     * IndexedDB is already origin-scoped by the browser, so the origin is
     * belt-and-braces; the game name is what actually separates two games served
     * from the same origin.
     */
    function scopeKeyFor(gameName) {
        var origin = (window.location && window.location.origin) || "unknown-origin";
        var game = gameName || "unknown-game";
        return origin + "|" + game;
    }

    /* ------------------------------------------------------------------
     * In-memory fallback
     * ------------------------------------------------------------------ */
    function MemoryBackend() {
        var data = {};
        NAMESPACES.forEach(function (ns) { data[ns] = {}; });

        function resolved(value) {
            return window.Promise.resolve(value);
        }

        return {
            persistent: false,
            get: function (ns, key) { return resolved(data[ns] ? data[ns][key] : undefined); },
            put: function (ns, key, value) {
                if (!data[ns]) { data[ns] = {}; }
                data[ns][key] = value;
                return resolved(true);
            },
            remove: function (ns, key) {
                if (data[ns]) { delete data[ns][key]; }
                return resolved(true);
            },
            all: function (ns) {
                var out = [];
                Object.keys(data[ns] || {}).forEach(function (key) {
                    out.push({ key: key, value: data[ns][key] });
                });
                return resolved(out);
            },
            clear: function (ns) { data[ns] = {}; return resolved(true); }
        };
    }

    /* ------------------------------------------------------------------
     * IndexedDB backend
     * ------------------------------------------------------------------ */
    function IndexedDbBackend(db) {
        /*
         * Stand aside when another tab needs to upgrade the schema.
         *
         * IndexedDB will not run an upgrade while any connection is still open
         * on the old version. Without this handler, a player with Aetos open in
         * two tabs who reloads one of them after a version that added a
         * namespace gets a new tab whose open never completes -- so *every*
         * local read hangs: no notes, no macros, no aliases, no error, no
         * message. It looks exactly like the client having lost their data.
         *
         * Found the hard way while adding the `reminders` namespace in A5. The
         * `blocked` fallback below is not enough on its own: it rescues the
         * tab doing the upgrading, while the tab holding the old connection is
         * what has to yield.
         */
        db.onversionchange = function () {
            db.close();
        };

        function tx(ns, mode) {
            return db.transaction([ns], mode).objectStore(ns);
        }

        function wrap(request) {
            return new window.Promise(function (resolve, reject) {
                request.onsuccess = function () { resolve(request.result); };
                request.onerror = function () { reject(request.error); };
            });
        }

        return {
            persistent: true,
            get: function (ns, key) {
                return wrap(tx(ns, "readonly").get(key)).then(function (row) {
                    return row ? row.value : undefined;
                });
            },
            put: function (ns, key, value) {
                return wrap(tx(ns, "readwrite").put({ key: key, value: value })).then(function () {
                    return true;
                });
            },
            remove: function (ns, key) {
                return wrap(tx(ns, "readwrite").delete(key)).then(function () { return true; });
            },
            all: function (ns) {
                return wrap(tx(ns, "readonly").getAll()).then(function (rows) {
                    return (rows || []).map(function (row) {
                        return { key: row.key, value: row.value };
                    });
                });
            },
            clear: function (ns) {
                return wrap(tx(ns, "readwrite").clear()).then(function () { return true; });
            }
        };
    }

    function openDatabase(scopeKey) {
        return new window.Promise(function (resolve) {
            if (!window.indexedDB) {
                resolve(MemoryBackend());
                return;
            }
            var request;
            try {
                request = window.indexedDB.open("aetos::" + scopeKey, DB_VERSION);
            } catch (err) {
                resolve(MemoryBackend());
                return;
            }

            request.onupgradeneeded = function (event) {
                var db = event.target.result;
                NAMESPACES.forEach(function (ns) {
                    if (!db.objectStoreNames.contains(ns)) {
                        db.createObjectStore(ns, { keyPath: "key" });
                    }
                });
            };
            request.onsuccess = function () {
                resolve(IndexedDbBackend(request.result));
            };
            // Private browsing and hardened settings can refuse or block the
            // open. Fall back rather than leaving the client broken.
            request.onerror = function () { resolve(MemoryBackend()); };
            /*
             * Blocked means another tab still holds the old schema open.
             *
             * The memory fallback keeps this tab working, but it is working
             * *without persistence* -- so it is flagged rather than swallowed.
             * A player who writes a note into a client that quietly forgot how
             * to save it has been failed twice: once by losing the note, and
             * once by not being told.
             */
            request.onblocked = function () {
                var backend = MemoryBackend();
                backend.blocked = true;
                resolve(backend);
            };
        });
    }

    /* ------------------------------------------------------------------
     * Public API
     * ------------------------------------------------------------------ */
    function createStorage(options) {
        var opts = options || {};
        var scopeKey = scopeKeyFor(opts.gameName);
        var backendPromise = openDatabase(scopeKey);

        function isKnown(ns) {
            return NAMESPACES.indexOf(ns) !== -1;
        }

        function withBackend(fn) {
            return backendPromise.then(fn);
        }

        function guard(ns) {
            if (!isKnown(ns)) {
                return window.Promise.reject(new Error("Aetos storage: unknown namespace " + ns));
            }
            return null;
        }

        function get(ns, key) {
            return guard(ns) || withBackend(function (b) { return b.get(ns, key); });
        }

        function put(ns, key, value) {
            return guard(ns) || withBackend(function (b) { return b.put(ns, key, value); });
        }

        function remove(ns, key) {
            return guard(ns) || withBackend(function (b) { return b.remove(ns, key); });
        }

        function all(ns) {
            return guard(ns) || withBackend(function (b) { return b.all(ns); });
        }

        function clear(ns) {
            return guard(ns) || withBackend(function (b) { return b.clear(ns); });
        }

        /*
         * Counts per namespace, for the privacy panel (blueprint section 63).
         * A player should be able to see exactly what is being kept about them.
         */
        function counts() {
            return withBackend(function (b) {
                return window.Promise.all(NAMESPACES.map(function (ns) {
                    return b.all(ns).then(function (rows) {
                        return { namespace: ns, count: rows.length };
                    });
                })).then(function (entries) {
                    var out = {};
                    entries.forEach(function (entry) { out[entry.namespace] = entry.count; });
                    return out;
                });
            });
        }

        /*
         * Clear every Aetos namespace.
         *
         * Deliberately scoped to Aetos's own database and its prefixed
         * localStorage keys. Stock Evennia's `evenniaGoldenLayoutSavedState` is
         * NOT touched -- deleting a player's stock webclient layout because they
         * asked to clear Aetos data would be a destructive bug.
         */
        function clearAll() {
            return withBackend(function (b) {
                return window.Promise.all(NAMESPACES.map(function (ns) {
                    return b.clear(ns);
                })).then(function () {
                    try {
                        Object.keys(window.localStorage)
                            .filter(function (key) { return key.indexOf(LOCAL_PREFIX) === 0; })
                            .forEach(function (key) { window.localStorage.removeItem(key); });
                    } catch (err) {
                        // localStorage can be unavailable; the database clear
                        // above is the part that matters.
                    }
                    return true;
                });
            });
        }

        function isPersistent() {
            return withBackend(function (b) { return b.persistent; });
        }

        /*
         * Distinguishes "another tab is holding the old schema open" from
         * "this browser refuses to store anything".
         *
         * Both end up on the memory backend, but they have completely
         * different fixes: one is "close the other tab and reload", the other
         * is "you are in private browsing". Telling a player the wrong one
         * sends them looking in the wrong place.
         */
        function isBlocked() {
            return withBackend(function (b) { return b.blocked === true; });
        }

        /* --- Boot preferences ----------------------------------------- */

        // Only for values needed before the database opens. Everything else
        // belongs in a namespace.
        function getBootPreference(key, fallback) {
            try {
                var raw = window.localStorage.getItem(LOCAL_PREFIX + key);
                return raw === null ? fallback : JSON.parse(raw);
            } catch (err) {
                return fallback;
            }
        }

        function setBootPreference(key, value) {
            try {
                window.localStorage.setItem(LOCAL_PREFIX + key, JSON.stringify(value));
                return true;
            } catch (err) {
                return false;
            }
        }

        return {
            namespaces: NAMESPACES.slice(),
            scopeKey: scopeKey,
            get: get,
            put: put,
            remove: remove,
            all: all,
            clear: clear,
            counts: counts,
            clearAll: clearAll,
            isPersistent: isPersistent,
            isBlocked: isBlocked,
            getBootPreference: getBootPreference,
            setBootPreference: setBootPreference
        };
    }

    window.AetosStorage = {
        create: createStorage,
        NAMESPACES: NAMESPACES.slice(),
        LOCAL_PREFIX: LOCAL_PREFIX,
        scopeKeyFor: scopeKeyFor
    };

})(window);
