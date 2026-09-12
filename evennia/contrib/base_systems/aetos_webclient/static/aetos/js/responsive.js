/*
 * Aetos responsive layout.
 *
 * The client must be usable on a phone, a tablet, an ordinary monitor and a very
 * large one, without the player configuring anything (blueprint section 53).
 *
 * MEASURED, NOT ASSUMED.
 *
 * Breakpoints are driven by a ResizeObserver on the client's own root element,
 * not by `window.innerWidth`. The two are not the same: a browser side panel, a
 * devtools dock, a scrollbar, or an embedded frame all make the element narrower
 * than the window, and a layout that trusts the window in those situations lays
 * out for space it does not have.
 *
 * Observing the element also means the layout is correct inside anything that
 * embeds it, and it reacts to a window resize, a device rotation and a panel
 * opening through exactly one code path.
 *
 * The breakpoint is published as a data attribute on the root, so CSS can key
 * off it directly. That keeps the *decision* in one place while the styling
 * stays in the stylesheet, rather than JavaScript setting pixel values that
 * later fight a media query.
 */

(function (window, document) {
    "use strict";

    /*
     * Widths are in CSS pixels of the client element.
     *
     * The boundaries are where the layout genuinely stops working, found by
     * measuring, not by copying a framework's defaults:
     *
     *   phone   -- one column is the only honest option
     *   tablet  -- two columns fit; the third would squeeze the console
     *   desktop -- three columns fit comfortably
     *   wide    -- extra space goes to the sides, not to an over-long text line
     */
    var BREAKPOINTS = [
        { name: "phone", max: 700 },
        { name: "tablet", max: 1100 },
        { name: "desktop", max: 1800 },
        { name: "wide", max: Infinity }
    ];

    /*
     * The text size those boundaries were measured at.
     *
     * `--aetos-font-size` is `clamp(13px, 0.85vw, 16px)`, so 14px is the middle
     * of the client's own range and the size the numbers above describe. The
     * point of naming it is that the boundaries are really about *how much text
     * fits*, and width alone only answers that while the text stays this size.
     */
    var REFERENCE_FONT_SIZE = 14;

    //: Below this height, vertical space is the scarce resource rather than
    //: width -- a phone in landscape, or a short window on a laptop.
    var SHORT_HEIGHT = 560;

    /*
     * The width the boundaries are compared against: how wide the client is *in
     * its own text*, expressed back in reference pixels.
     *
     * A player who doubles the text size has halved how much fits on a line, and
     * a layout that keeps three columns because the window is still 800px wide
     * gives them three slivers -- which is precisely the failure Gary reported
     * after turning the text up: a column five characters wide with a scrollbar
     * down the side of it.
     *
     * Dividing by the actual text size makes "phone" mean "one column is the only
     * honest option here", which is a statement about the text and the space
     * together rather than about the hardware. Browser zoom is handled by the
     * same arithmetic for free, because zoom scales both terms.
     */
    function effectiveWidth(width, fontSize) {
        if (!fontSize || !isFinite(fontSize) || fontSize <= 0) {
            return width;
        }
        return width * (REFERENCE_FONT_SIZE / fontSize);
    }

    function breakpointFor(width, fontSize) {
        var effective = fontSize === undefined
            ? width
            : effectiveWidth(width, fontSize);
        for (var i = 0; i < BREAKPOINTS.length; i++) {
            if (effective <= BREAKPOINTS[i].max) {
                return BREAKPOINTS[i].name;
            }
        }
        return "wide";
    }

    /*
     * The client's own rendered text size, which is what the accessibility text
     * scale, the browser's minimum font size and browser zoom all end up
     * expressed in. Read rather than computed, for the same reason the width is
     * observed rather than assumed.
     */
    function measuredFontSize(element) {
        if (typeof window.getComputedStyle !== "function") {
            return REFERENCE_FONT_SIZE;
        }
        var size = parseFloat(window.getComputedStyle(element).fontSize);
        return isFinite(size) && size > 0 ? size : REFERENCE_FONT_SIZE;
    }

    function createResponsive(services) {
        var root = services.root;
        var announce = services.announce || function () {};
        var onChange = services.onChange || function () {};

        var current = null;
        var currentShort = null;
        var observer = null;

        function apply(width, height) {
            var fontSize = measuredFontSize(root);
            var next = breakpointFor(width, fontSize);
            // Height gets the same treatment: `SHORT_HEIGHT` is "how many lines
            // fit", and at 180% text a 700px window holds as few lines as a
            // 390px one does at 100%.
            var short = effectiveWidth(height, fontSize) < SHORT_HEIGHT;

            if (next === current && short === currentShort) {
                return false;
            }
            var previous = current;
            current = next;
            currentShort = short;

            root.setAttribute("data-aetos-size", current);
            root.setAttribute("data-aetos-short", short ? "true" : "false");

            // Only announce a real transition, not the initial measurement --
            // a player should not be told the layout on every page load.
            if (previous !== null && previous !== current) {
                announce("Layout switched to " + current + ".");
            }
            onChange(current, { width: width, height: height, short: short });
            return true;
        }

        function measure() {
            var rect = root.getBoundingClientRect();
            apply(rect.width, rect.height);
        }

        function start() {
            if (typeof window.ResizeObserver === "function") {
                observer = new window.ResizeObserver(function (entries) {
                    var entry = entries[0];
                    if (!entry) {
                        return;
                    }
                    // contentRect is the element's own box, which is the number
                    // the layout actually has to work with.
                    apply(entry.contentRect.width, entry.contentRect.height);
                });
                observer.observe(root);
            } else {
                // Older browsers: fall back to resize events. Less precise
                // (it cannot see a side panel opening) but never worse than
                // having no responsiveness at all.
                window.addEventListener("resize", measure);
                window.addEventListener("orientationchange", measure);
            }
            measure();
        }

        function stop() {
            if (observer) {
                observer.disconnect();
                observer = null;
            }
            window.removeEventListener("resize", measure);
            window.removeEventListener("orientationchange", measure);
        }

        return {
            BREAKPOINTS: BREAKPOINTS.map(function (entry) { return entry.name; }),
            start: start,
            stop: stop,
            measure: measure,
            current: function () { return current; },
            isShort: function () { return currentShort === true; },
            breakpointFor: breakpointFor,
            effectiveWidth: effectiveWidth
        };
    }

    window.AetosResponsive = {
        create: createResponsive,
        breakpointFor: breakpointFor,
        effectiveWidth: effectiveWidth,
        BREAKPOINTS: BREAKPOINTS.map(function (entry) { return entry.name; }),
        SHORT_HEIGHT: SHORT_HEIGHT,
        REFERENCE_FONT_SIZE: REFERENCE_FONT_SIZE
    };

})(window, document);
