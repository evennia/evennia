/*
 * Aetos widget registry.
 *
 * A widget declares what it is and what it needs; the registry decides whether
 * the current game can support it. That is the mechanism behind progressive
 * enhancement: a widget requiring a capability the game does not expose is never
 * offered, so a pristine game gets a clean palette rather than dead entries.
 *
 * Widget definition (blueprint section 57):
 *
 *   {
 *     id:                   "room",              // unique, stable
 *     displayName:          "Current Location",
 *     requiredCapabilities: ["entities"],        // manifest features
 *     defaultSize:          {width: 260, height: 160},
 *     singleton:            true,                // at most one instance
 *     subscriptions:        ["room"],            // store sections
 *     accessibility:        {...}             // REQUIRED -- see below
 *     mount(context)        -> element
 *     update(context, data) // called on subscribed section change
 *     destroy(context)      // release listeners/timers
 *   }
 *
 * THE ACCESSIBILITY CONTRACT (Addendum A.28) IS NOT OPTIONAL.
 *
 *   accessibility: {
 *     landmarkLabel:  "Inventory",          // names the panel's region
 *     heading:        "Inventory",          // the visible <h2>
 *     description:    "Items you carry",    // for the widget palette
 *     keyboardOperable: true,               // false = display only
 *     liveUpdates:    false,                // does it change on its own?
 *     graphicalOnly:  false,                // canvas/SVG with no text form?
 *     textAlternative: null                 // required if graphicalOnly
 *   }
 *
 * Registration THROWS without it. That is deliberate and it is the whole point
 * of A1: a widget author who has not thought about how their widget is read
 * cannot ship it by accident, and "we'll do accessibility later" is not
 * expressible in the API.
 *
 * The metadata is not decoration. The layout adapter uses `landmarkLabel` and
 * `heading` to build the panel, so a widget that declares them badly is visibly
 * wrong to its author rather than silently wrong for somebody else.
 *
 * `graphicalOnly` without a `textAlternative` is refused outright. A canvas with
 * no text form is not a widget with an accessibility gap -- it is a widget half
 * the audience cannot use at all (A.29 applied generally).
 *
 * The registry never touches the DOM and never knows about layout. It is a
 * catalogue plus a capability filter, which is what lets the layout engine be
 * replaced without touching a single widget.
 */

(function (window) {
    "use strict";

    /*
     * The widget contract's version.  C.20.
     *
     * Bumped only when a change would break a widget written against the
     * previous one -- a new required field, a changed lifecycle call, a
     * different context shape. Adding an *optional* field does not bump it.
     *
     * A widget may declare which version it was written against. That is not
     * bureaucracy: a game-bundled widget outlives the Aetos release it was
     * written for, and the failure it would otherwise produce is a mount error
     * in somebody else's game months later, with nothing pointing at the
     * cause. Declaring the version turns that into a sentence naming both
     * numbers.
     */
    var SDK_VERSION = 1;

    function validateDefinition(definition) {
        var problems = [];
        if (!definition || typeof definition !== "object") {
            return ["definition must be an object"];
        }
        if (typeof definition.id !== "string" || !definition.id) {
            problems.push("id must be a non-empty string");
        }
        if (definition.sdkVersion !== undefined) {
            if (typeof definition.sdkVersion !== "number") {
                problems.push("sdkVersion must be a number");
            } else if (definition.sdkVersion > SDK_VERSION) {
                problems.push(
                    "sdkVersion " + definition.sdkVersion + " is newer than this " +
                    "client supports (" + SDK_VERSION + ") -- update Aetos"
                );
            } else if (definition.sdkVersion < SDK_VERSION) {
                problems.push(
                    "sdkVersion " + definition.sdkVersion + " is older than this " +
                    "client's contract (" + SDK_VERSION + ") -- see docs/widget-sdk.md"
                );
            }
        }
        if (typeof definition.displayName !== "string" || !definition.displayName) {
            problems.push("displayName must be a non-empty string");
        }
        if (typeof definition.mount !== "function") {
            problems.push("mount must be a function");
        }
        if (definition.requiredCapabilities !== undefined
                && !Array.isArray(definition.requiredCapabilities)) {
            problems.push("requiredCapabilities must be an array when given");
        }
        if (definition.subscriptions !== undefined && !Array.isArray(definition.subscriptions)) {
            problems.push("subscriptions must be an array when given");
        }
        problems.push.apply(problems, validateAccessibility(definition));
        return problems;
    }

    /*
     * The accessibility contract.  Addendum A.28.
     *
     * Required, and required to be *answered* rather than merely present: every
     * question here is one whose wrong answer produces a widget that works
     * perfectly for its author and not at all for somebody else.
     */
    function validateAccessibility(definition) {
        var problems = [];
        var meta = definition.accessibility;

        if (!meta || typeof meta !== "object") {
            return [
                "accessibility metadata is required (Addendum A.28). Declare " +
                "landmarkLabel, heading, keyboardOperable and liveUpdates."
            ];
        }

        if (typeof meta.landmarkLabel !== "string" || !meta.landmarkLabel) {
            // An unlabelled region is an anonymous entry in a screen reader's
            // landmark list, which is worse than no landmark: it is one more
            // thing to step through that says nothing.
            problems.push("accessibility.landmarkLabel must be a non-empty string");
        }
        if (typeof meta.heading !== "string" || !meta.heading) {
            problems.push("accessibility.heading must be a non-empty string");
        }
        if (typeof meta.keyboardOperable !== "boolean") {
            // Deliberately not defaulted. "Can this be used without a mouse?"
            // has no safe default answer -- assuming true hides the widgets
            // that cannot, and assuming false slanders the ones that can.
            problems.push(
                "accessibility.keyboardOperable must be true or false, stated " +
                "explicitly -- there is no safe default for it"
            );
        }
        if (typeof meta.liveUpdates !== "boolean") {
            problems.push("accessibility.liveUpdates must be true or false");
        }
        if (meta.graphicalOnly === true && !meta.textAlternative) {
            problems.push(
                "accessibility.graphicalOnly requires a textAlternative: a " +
                "graphical widget with no text form is unusable, not merely " +
                "imperfect"
            );
        }
        return problems;
    }

    function normalize(definition) {
        return {
            id: definition.id,
            displayName: definition.displayName,
            description: definition.description || "",
            requiredCapabilities: (definition.requiredCapabilities || []).slice(),
            // The region a widget asks for. Dropping this here silently sent
            // every widget to the fallback region, so a definition declaring
            // `bottom` or `aside` was ignored and the default layout became one
            // long scrolling column.
            defaultRegion: definition.defaultRegion || null,
            defaultSize: definition.defaultSize || { width: 280, height: 200 },
            singleton: definition.singleton !== false,
            subscriptions: (definition.subscriptions || []).slice(),
            mount: definition.mount,
            update: definition.update || null,
            destroy: definition.destroy || null,
            // Marks widgets shipped with Aetos, so a third-party widget can
            // never quietly replace a built-in one (blueprint section 57).
            builtin: definition.builtin === true,
            accessibility: {
                landmarkLabel: definition.accessibility.landmarkLabel,
                heading: definition.accessibility.heading,
                description: definition.accessibility.description || "",
                keyboardOperable: definition.accessibility.keyboardOperable,
                liveUpdates: definition.accessibility.liveUpdates,
                graphicalOnly: definition.accessibility.graphicalOnly === true,
                textAlternative: definition.accessibility.textAlternative || null
            }
        };
    }

    function createRegistry() {
        var definitions = {};

        /*
         * Register a widget.
         *
         * Registration is additive and validated. A third-party widget may not
         * overwrite a built-in: allowing that would let a custom widget silently
         * replace the console or the command input, which the blueprint requires
         * to remain intact.
         */
        function register(definition) {
            var problems = validateDefinition(definition);
            if (problems.length) {
                throw new Error(
                    "Aetos widget registration failed: " + problems.join("; "));
            }
            var existing = definitions[definition.id];
            if (existing && existing.builtin && definition.builtin !== true) {
                throw new Error(
                    "Aetos widget \"" + definition.id +
                    "\" is built in and cannot be replaced.");
            }
            definitions[definition.id] = normalize(definition);
            return definitions[definition.id];
        }

        function get(id) {
            return definitions[id] || null;
        }

        function all() {
            return Object.keys(definitions).map(function (id) {
                return definitions[id];
            });
        }

        /*
         * Whether the game supports a widget.
         *
         * A widget with no required capabilities always qualifies -- that is what
         * makes the zero-configuration widgets (console, input, room) work on a
         * pristine game.
         */
        function isSupported(definition, manifest) {
            if (!definition) {
                return false;
            }
            if (!definition.requiredCapabilities.length) {
                return true;
            }
            var features = (manifest && manifest.features) || {};
            return definition.requiredCapabilities.every(function (capability) {
                return features[capability] === true;
            });
        }

        /*
         * The palette: widgets this game can actually support.
         *
         * Blueprint section 51 -- no unsupported controls clutter the screen.
         */
        function available(manifest) {
            return all().filter(function (definition) {
                return isSupported(definition, manifest);
            });
        }

        function unavailable(manifest) {
            return all().filter(function (definition) {
                return !isSupported(definition, manifest);
            });
        }

        return {
            register: register,
            get: get,
            all: all,
            available: available,
            unavailable: unavailable,
            isSupported: isSupported
        };
    }

    window.AetosWidgets = {
        SDK_VERSION: SDK_VERSION, createRegistry: createRegistry };

})(window);
