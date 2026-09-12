/*
 * Aetos profile export and import.
 *
 * A profile is a portable copy of a player's local Aetos data: layouts, macros,
 * notes, relationships, themes, map annotations. Export lets a player move
 * between browsers or keep a backup; import restores it.
 *
 * THIS IS THE MOST DANGEROUS INPUT AETOS ACCEPTS. An exported profile is a file
 * a player may have received from someone else, and it lands directly in the
 * store that drives macros, aliases and triggers -- things that send commands.
 * Blueprint section 62 lists "malicious imported profile" first in the threat
 * model, and it is treated that way here:
 *
 *   - the envelope is validated before anything is read
 *   - unknown namespaces are dropped, never trusted
 *   - every value is size- and depth-bounded
 *   - strings are length-capped
 *   - functions, prototypes and non-JSON values cannot survive
 *   - import is transactional per namespace and reports what it refused
 *
 * Import NEVER executes anything. It writes data. Whether a macro may later run
 * is governed by the server's automation policy in the manifest.
 */

(function (window) {
    "use strict";

    var FORMAT = "aetos-profile";
    var FORMAT_VERSION = 1;

    // Bounds. A profile is a hand-portable file; anything beyond these is either
    // corrupt or hostile, and both deserve rejection rather than best effort.
    var MAX_ENTRIES_PER_NAMESPACE = 2000;
    var MAX_KEY_LENGTH = 200;
    var MAX_STRING_LENGTH = 20000;
    var MAX_DEPTH = 12;
    var MAX_ARRAY_LENGTH = 5000;
    var MAX_OBJECT_KEYS = 500;

    function ProfileError(message) {
        var err = new Error(message);
        err.name = "AetosProfileError";
        return err;
    }

    /*
     * Rebuild a value from scratch, keeping only plain JSON.
     *
     * Rebuilding rather than validating-in-place is deliberate: it guarantees the
     * result shares no object identity, prototype or accessor with the input, so
     * a crafted `__proto__`, a getter with side effects, or a self-referential
     * structure cannot survive into the store.
     */
    function sanitizeValue(value, depth, report) {
        if (depth > MAX_DEPTH) {
            report.truncated += 1;
            return null;
        }

        if (value === null) {
            return null;
        }

        var type = typeof value;

        if (type === "string") {
            if (value.length > MAX_STRING_LENGTH) {
                report.truncated += 1;
                return value.slice(0, MAX_STRING_LENGTH);
            }
            return value;
        }

        if (type === "number") {
            // NaN and Infinity are not representable in JSON and usually signal
            // a corrupt file.
            return isFinite(value) ? value : null;
        }

        if (type === "boolean") {
            return value;
        }

        // Functions, symbols and undefined are dropped outright. A profile is
        // data; anything executable has no business in it.
        if (type !== "object") {
            report.rejected += 1;
            return null;
        }

        if (Array.isArray(value)) {
            var arr = [];
            var limit = Math.min(value.length, MAX_ARRAY_LENGTH);
            if (value.length > MAX_ARRAY_LENGTH) {
                report.truncated += 1;
            }
            for (var i = 0; i < limit; i++) {
                arr.push(sanitizeValue(value[i], depth + 1, report));
            }
            return arr;
        }

        var out = {};
        var keys = Object.keys(value);
        if (keys.length > MAX_OBJECT_KEYS) {
            report.truncated += 1;
            keys = keys.slice(0, MAX_OBJECT_KEYS);
        }
        for (var k = 0; k < keys.length; k++) {
            var key = keys[k];
            // Prototype-pollution guards. Object.keys does not return inherited
            // properties, but an explicit own "__proto__" key is possible in
            // parsed JSON and must never be written back.
            if (key === "__proto__" || key === "constructor" || key === "prototype") {
                report.rejected += 1;
                continue;
            }
            if (key.length > MAX_KEY_LENGTH) {
                report.rejected += 1;
                continue;
            }
            out[key] = sanitizeValue(value[key], depth + 1, report);
        }
        return out;
    }

    function newReport() {
        return { imported: 0, rejected: 0, truncated: 0, unknownNamespaces: [] };
    }

    /*
     * Validate the envelope before reading any content.
     *
     * A file that is not an Aetos profile must be refused with a clear message
     * rather than silently importing nothing, which would look like data loss.
     */
    function validateEnvelope(data) {
        if (!data || typeof data !== "object" || Array.isArray(data)) {
            throw ProfileError("Not an Aetos profile: expected a JSON object.");
        }
        if (data.format !== FORMAT) {
            throw ProfileError(
                "Not an Aetos profile: expected format \"" + FORMAT + "\", got " +
                JSON.stringify(data.format) + ".");
        }
        if (typeof data.version !== "number" || !isFinite(data.version)) {
            throw ProfileError("Profile has no usable version number.");
        }
        if (data.version > FORMAT_VERSION) {
            throw ProfileError(
                "Profile was written by a newer version of Aetos (format version " +
                data.version + "; this client understands " + FORMAT_VERSION +
                "). Update Aetos, or export again from the older client.");
        }
        if (!data.data || typeof data.data !== "object" || Array.isArray(data.data)) {
            throw ProfileError("Profile contains no data section.");
        }
        return data;
    }

    function createProfileManager(storage) {

        /*
         * Export selected namespaces.
         *
         * `timestamp` is passed in rather than read from the clock here so the
         * caller owns it and the function stays deterministic for testing.
         */
        function exportProfile(namespaces, meta) {
            var selected = (namespaces && namespaces.length)
                ? namespaces.filter(function (ns) {
                    return storage.namespaces.indexOf(ns) !== -1;
                })
                : storage.namespaces.slice();

            return window.Promise.all(selected.map(function (ns) {
                return storage.all(ns).then(function (rows) {
                    var section = {};
                    rows.forEach(function (row) { section[row.key] = row.value; });
                    return { namespace: ns, section: section };
                });
            })).then(function (sections) {
                var data = {};
                sections.forEach(function (entry) { data[entry.namespace] = entry.section; });
                return {
                    format: FORMAT,
                    version: FORMAT_VERSION,
                    exported: (meta && meta.timestamp) || null,
                    game: (meta && meta.game) || null,
                    data: data
                };
            });
        }

        /*
         * Import a profile.
         *
         * Returns a report rather than throwing on partial problems: a profile
         * with one bad entry should still restore the rest, and the player
         * should be told exactly what was refused.
         */
        function importProfile(rawData, options) {
            var opts = options || {};
            var parsed;

            if (typeof rawData === "string") {
                try {
                    parsed = window.JSON.parse(rawData);
                } catch (err) {
                    return window.Promise.reject(
                        ProfileError("Profile is not valid JSON: " + err.message));
                }
            } else {
                parsed = rawData;
            }

            var profile;
            try {
                profile = validateEnvelope(parsed);
            } catch (err) {
                return window.Promise.reject(err);
            }

            var report = newReport();
            var wanted = opts.namespaces && opts.namespaces.length ? opts.namespaces : null;
            var writes = [];

            Object.keys(profile.data).forEach(function (ns) {
                if (storage.namespaces.indexOf(ns) === -1) {
                    // Unknown namespace: could be from a newer Aetos, could be
                    // crafted. Either way it is never written.
                    report.unknownNamespaces.push(ns);
                    return;
                }
                if (wanted && wanted.indexOf(ns) === -1) {
                    return;
                }

                var section = profile.data[ns];
                if (!section || typeof section !== "object" || Array.isArray(section)) {
                    report.rejected += 1;
                    return;
                }

                var keys = Object.keys(section);
                if (keys.length > MAX_ENTRIES_PER_NAMESPACE) {
                    report.truncated += 1;
                    keys = keys.slice(0, MAX_ENTRIES_PER_NAMESPACE);
                }

                keys.forEach(function (key) {
                    if (typeof key !== "string" || !key || key.length > MAX_KEY_LENGTH) {
                        report.rejected += 1;
                        return;
                    }
                    var clean = sanitizeValue(section[key], 0, report);
                    report.imported += 1;
                    // Collect a DESCRIPTOR, not a started write. Calling
                    // storage.put() here would begin the write immediately, so
                    // in replace mode it would race the clear below and the
                    // freshly imported data could be wiped by it.
                    writes.push({ namespace: ns, key: key, value: clean });
                });
            });

            var prelude = opts.replace
                ? window.Promise.all((wanted || storage.namespaces).map(function (ns) {
                    return storage.clear(ns);
                }))
                : window.Promise.resolve(true);

            return prelude
                .then(function () {
                    // Only now that any clear has completed do the writes start.
                    return window.Promise.all(writes.map(function (write) {
                        return storage.put(write.namespace, write.key, write.value);
                    }));
                })
                .then(function () { return report; });
        }

        function toJson(profile) {
            return window.JSON.stringify(profile, null, 2);
        }

        return {
            FORMAT: FORMAT,
            FORMAT_VERSION: FORMAT_VERSION,
            exportProfile: exportProfile,
            importProfile: importProfile,
            toJson: toJson
        };
    }

    window.AetosProfile = {
        create: createProfileManager,
        FORMAT: FORMAT,
        FORMAT_VERSION: FORMAT_VERSION,
        // Exposed for the browser QA suite.
        _sanitizeValue: function (value) {
            var report = newReport();
            return { value: sanitizeValue(value, 0, report), report: report };
        },
        _validateEnvelope: validateEnvelope
    };

})(window);
