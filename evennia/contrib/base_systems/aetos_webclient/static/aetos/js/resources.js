/*
 * Aetos resource rendering and threshold announcements.
 *
 * Resources are arbitrary. Nothing here knows what "health" is; a gauge labelled
 * Sanity, Hull or Favour renders through exactly the same code (blueprint
 * section 19).
 *
 * TWO ACCESSIBILITY RULES SHAPE THIS FILE.
 *
 * 1. A gauge is not readable by a screen reader, and a colour change is not
 *    readable by anyone who cannot distinguish the colours. So every resource
 *    renders its value as TEXT alongside the bar, and severity is carried by a
 *    text marker as well as by colour (sections 45, 49).
 *
 * 2. Announcing every change is unusable. A resource that ticks each combat
 *    round would produce continuous speech the player cannot interrupt. So
 *    announcements happen only when a declared threshold is CROSSED, and only
 *    downward -- recovering from 20% to 21% is not news (section 48).
 */

(function (window, document) {
    "use strict";

    /* ------------------------------------------------------------------
     * Threshold tracking
     * ------------------------------------------------------------------ */

    /*
     * Decides when a resource change is worth announcing.
     *
     * A threshold's `at` is read as a fraction when the resource is bounded and
     * `at` lies in 0..1, and as an absolute value otherwise. That lets a game
     * say "below 20%" or "below 5 doses" without a second field to get wrong.
     */
    function createThresholdTracker() {
        var lastValues = {};

        function thresholdValue(resource, threshold) {
            var maximum = resource.maximum;
            var minimum = typeof resource.minimum === "number" ? resource.minimum : 0;
            var isFraction = typeof maximum === "number" &&
                threshold.at >= 0 && threshold.at <= 1;
            if (isFraction) {
                return minimum + ((maximum - minimum) * threshold.at);
            }
            return threshold.at;
        }

        /*
         * Return announcements triggered by this update.
         *
         * Only downward crossings count. If several are crossed at once -- a
         * single large hit -- only the most severe is announced, because
         * reading three messages in a row is worse than reading the one that
         * matters.
         */
        function evaluate(resource) {
            var previous = lastValues[resource.id];
            var current = resource.value;
            lastValues[resource.id] = current;

            if (previous === undefined || previous === current) {
                // First sight of a resource is not a crossing. Announcing on
                // connect would greet every player with their own status.
                return null;
            }
            if (!resource.thresholds || !resource.thresholds.length) {
                return null;
            }

            var crossed = resource.thresholds.filter(function (threshold) {
                var point = thresholdValue(resource, threshold);
                return previous > point && current <= point;
            });
            if (!crossed.length) {
                return null;
            }

            // Thresholds arrive sorted descending, so the last crossed is the
            // lowest and therefore the most serious.
            var worst = crossed[crossed.length - 1];
            return {
                id: resource.id,
                level: worst.level,
                message: worst.label ||
                    (resource.label + " at " + formatValue(resource) + ".")
            };
        }

        function reset() {
            lastValues = {};
        }

        return { evaluate: evaluate, reset: reset };
    }

    /* ------------------------------------------------------------------
     * Formatting
     * ------------------------------------------------------------------ */

    function round(value) {
        return Math.round(value * 10) / 10;
    }

    function formatValue(resource) {
        if (typeof resource.maximum === "number") {
            return round(resource.value) + " of " + round(resource.maximum);
        }
        return String(round(resource.value));
    }

    function percentText(resource) {
        if (typeof resource.maximum !== "number") {
            return null;
        }
        var minimum = typeof resource.minimum === "number" ? resource.minimum : 0;
        var span = resource.maximum - minimum;
        if (span <= 0) {
            return null;
        }
        var pct = ((resource.value - minimum) / span) * 100;
        return Math.max(0, Math.min(100, Math.round(pct)));
    }

    /* ------------------------------------------------------------------
     * Rendering
     * ------------------------------------------------------------------ */

    function severityFor(resource) {
        var pct = percentText(resource);
        if (pct === null || !resource.thresholds || !resource.thresholds.length) {
            return null;
        }
        var minimum = typeof resource.minimum === "number" ? resource.minimum : 0;
        var span = resource.maximum - minimum;
        var worst = null;
        resource.thresholds.forEach(function (threshold) {
            var point = (threshold.at >= 0 && threshold.at <= 1)
                ? minimum + (span * threshold.at)
                : threshold.at;
            if (resource.value <= point) {
                worst = threshold;
            }
        });
        return worst;
    }

    /*
     * A gauge for a resource the game declared but has not yet sent a value
     * for.  M23.
     *
     * Rendered rather than omitted, because an empty panel and a panel whose
     * numbers have not arrived are different situations that look identical.
     * A player reconnecting mid-fight, or on a slow link, otherwise sees a
     * blank space and cannot tell whether this game has a health bar at all.
     *
     * "Waiting" rather than a zero or a spinner: a zero is a *value*, and
     * showing one for a health bar that simply has not loaded is the worst
     * possible wrong answer.
     */
    function renderPending(descriptor) {
        var row = document.createElement("div");
        row.className = "aetos-resource aetos-resource--pending";

        var label = document.createElement("span");
        label.className = "aetos-resource__label";
        label.textContent = descriptor.label || descriptor.id;
        row.appendChild(label);

        var value = document.createElement("span");
        value.className = "aetos-resource__value";
        value.textContent = "waiting";
        row.appendChild(value);

        return row;
    }

    function renderResource(resource) {
        var row = document.createElement("div");
        row.className = "aetos-resource aetos-resource--" + resource.display;
        row.setAttribute("data-aetos-resource", resource.id);

        var severity = severityFor(resource);
        if (severity) {
            row.classList.add("aetos-resource--" + severity.level);
        }

        var label = document.createElement("span");
        label.className = "aetos-resource__label";
        label.textContent = resource.label;

        var value = document.createElement("span");
        value.className = "aetos-resource__value";
        var pct = percentText(resource);
        // The number is always present. A bar alone conveys nothing to a screen
        // reader, and nothing precise to anyone.
        value.textContent = resource.display === "percentage" && pct !== null
            ? pct + "%"
            : formatValue(resource);

        // Severity is stated in words, not only shown as a colour.
        if (severity && severity.level !== "info") {
            var marker = document.createElement("span");
            marker.className = "aetos-resource__severity";
            marker.textContent = " (" + severity.level + ")";
            value.appendChild(marker);
        }

        row.appendChild(label);
        row.appendChild(value);

        if (pct !== null && resource.display !== "number" &&
                resource.display !== "text" && resource.display !== "percentage") {
            var track = document.createElement("div");
            track.className = "aetos-resource__track";
            // A native progress semantic, so assistive technology reports the
            // value without Aetos having to describe the bar.
            track.setAttribute("role", "meter");
            track.setAttribute("aria-valuemin", String(resource.minimum || 0));
            track.setAttribute("aria-valuemax", String(resource.maximum));
            track.setAttribute("aria-valuenow", String(resource.value));
            track.setAttribute("aria-label", resource.label);

            var fill = document.createElement("div");
            fill.className = "aetos-resource__fill";
            fill.style.width = pct + "%";
            track.appendChild(fill);
            row.appendChild(track);
        }

        return row;
    }

    /* ------------------------------------------------------------------
     * Widget definition
     * ------------------------------------------------------------------ */

    function createResourceWidget(services) {
        var announce = services.announce || function () {};
        var tracker = createThresholdTracker();

        return {
            id: "resources",
            // Display only. The numbers are always rendered as text beside the
            // bar, and threshold crossings are announced through the
            // announcement manager rather than a live region here.
            accessibility: {
                landmarkLabel: "Resources",
                heading: "Resources",
                keyboardOperable: false,
                liveUpdates: true
            },
            displayName: "Resources",
            description: "Numeric values your game exposes about your character.",
            builtin: true,
            defaultRegion: "aside",
            defaultSize: { height: 130 },
            // Gated: a game exposing no resources never sees this widget offered.
            requiredCapabilities: ["resources"],
            subscriptions: ["resources"],

            mount: function (context) {
                context.element.setAttribute("data-aetos-resources", "");
                /*
                 * Focusable, because it scrolls. Arrow keys scroll whatever has
                 * focus, so a scrolling region outside the tab order cannot be
                 * scrolled by keyboard at all -- the player can see there is
                 * more and has no way to reach it.
                 *
                 * Fifth and sixth instances of this in the client, both found by
                 * axe rather than by review. It is invisible to anyone testing
                 * with a mouse wheel, which is why it keeps recurring: the
                 * person who writes the panel is never the person it fails.
                 *
                 * `group`, not `region`. The enclosing panel is already a
                 * landmark carrying this widget's name, so a nested `region`
                 * with the same label produces two landmarks called
                 * "Resources" -- which axe reports as `landmark-unique` and a
                 * screen reader reports as the same thing twice. `group` is
                 * not a landmark, so it carries the label without competing.
                 */
                context.element.setAttribute("tabindex", "0");
                context.element.setAttribute("role", "group");
                context.element.setAttribute("aria-label", "Resources");
            },

            update: function (context, data) {
                var items = (data && data.items) || [];
                context.element.textContent = "";

                /*
                 * What the game said it has, from the manifest (M23).
                 *
                 * Used only to fill gaps: anything the provider actually sent
                 * wins, always. A descriptor is a promise about the interface,
                 * not a second source of truth about the numbers.
                 */
                var manifest = (context.store && context.store.get("manifest")) || {};
                var declared = manifest.resources || [];
                var supplied = {};
                items.forEach(function (resource) { supplied[resource.id] = true; });
                var pending = declared.filter(function (descriptor) {
                    return !supplied[descriptor.id];
                });

                var panel = context.element.closest
                    ? context.element.closest("[data-aetos-widget]")
                    : null;
                if (panel) {
                    // Emptiness, not the player's visibility choice. A declared
                    // resource counts as content even before its value lands.
                    panel.setAttribute(
                        "data-aetos-empty",
                        (items.length || pending.length) ? "false" : "true");
                }
                if (!items.length && !pending.length) {
                    return;
                }

                items.forEach(function (resource) {
                    context.element.appendChild(renderResource(resource));

                    var announcement = tracker.evaluate(resource);
                    if (announcement) {
                        announce(announcement.message);
                    }
                });

                /*
                 * Declared-but-absent gauges last, and never announced.
                 *
                 * Announcing "waiting" would be announcing the absence of news,
                 * which is exactly the kind of interruption Quiet Mode exists
                 * to stop -- and it would fire on every reconnect.
                 */
                pending.forEach(function (descriptor) {
                    context.element.appendChild(renderPending(descriptor));
                });
            },

            destroy: function () {
                tracker.reset();
            }
        };
    }

    window.AetosResources = {
        createWidget: createResourceWidget,
        createThresholdTracker: createThresholdTracker,
        renderResource: renderResource,
        formatValue: formatValue,
        percentText: percentText
    };

})(window, document);
