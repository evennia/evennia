/*
 * WCAG contrast ratios in the browser.  Addendum A.55, A11Y-VIS-003.
 *
 * The same calculation as `contrast.py`, which checks Aetos's own themes at
 * test time. Two implementations of one published formula, pinned to the same
 * fixtures by a test, because the check has to happen in two places: shipped
 * themes are validated before release, and a player's own theme is validated as
 * they build it.
 *
 * WHY VALIDATION IS PART OF SAVING
 *
 * A palette chosen by eye passes for the person who chose it. That is not a
 * criticism of anybody's judgement -- it is what having particular eyes means.
 * The author of an illegible theme is, necessarily, somebody who could read it.
 *
 * So the editor computes the ratios as the colours change and says which pairs
 * fail and why. It does **not** refuse the save. A player who wants a theme
 * Aetos considers unwise is entitled to have it; what they are not entitled to
 * is not being told. A tool that silently blocked would be overruling somebody
 * about their own eyes, and a tool that silently accepted would be failing the
 * next person who uses their exported theme.
 */

(function (window) {
    "use strict";

    var AA_NORMAL_TEXT = 4.5;
    var AA_NON_TEXT = 3.0;

    /*
     * The pairs every theme has to satisfy, and what each one is for.
     *
     * Named rather than derived. "Every token against every other token" would
     * produce dozens of combinations that never appear together on screen, and
     * a validator reporting failures nobody can see is one people learn to
     * ignore.
     */
    var REQUIRED_PAIRS = [
        ["--aetos-text", "--aetos-bg", AA_NORMAL_TEXT, "body text on the background"],
        ["--aetos-text", "--aetos-panel", AA_NORMAL_TEXT, "body text on a panel"],
        // Where contrast themes usually fail: the muted colour is chosen to
        // recede, and then recedes past legibility.
        ["--aetos-text-muted", "--aetos-bg", AA_NORMAL_TEXT, "secondary text on the background"],
        ["--aetos-text-muted", "--aetos-panel", AA_NORMAL_TEXT, "secondary text on a panel"],
        ["--aetos-accent", "--aetos-panel", AA_NON_TEXT, "accents and headings on a panel"],
        ["--aetos-success", "--aetos-panel", AA_NON_TEXT, "the success colour on a panel"],
        ["--aetos-warning", "--aetos-panel", AA_NON_TEXT, "the warning colour on a panel"],
        ["--aetos-danger", "--aetos-panel", AA_NON_TEXT, "the danger colour on a panel"],
        // Borders carry structure: they are what separates one region from
        // another for somebody who cannot rely on a subtle background shift.
        ["--aetos-border", "--aetos-bg", AA_NON_TEXT, "panel borders against the background"],
        ["--aetos-focus", "--aetos-bg", AA_NON_TEXT, "the focus ring on the background"],
        ["--aetos-focus", "--aetos-panel", AA_NON_TEXT, "the focus ring on a panel"]
    ];

    /*
     * Parse a hex colour.
     *
     * Hex only. A theme token is a colour literal, not an expression:
     * supporting `rgb()`, `hsl()` and `color-mix()` would mean reimplementing a
     * CSS colour parser in order to reject one of them, and every format that
     * cannot be checked is a format a failing theme can hide in.
     */
    function parseColor(value) {
        if (typeof value !== "string") {
            return null;
        }
        var text = value.trim().toLowerCase();
        var match = /^#([0-9a-f]{3}|[0-9a-f]{6})$/.exec(text);
        if (!match) {
            return null;
        }
        var digits = match[1];
        if (digits.length === 3) {
            digits = digits[0] + digits[0] + digits[1] + digits[1] + digits[2] + digits[2];
        }
        return [
            parseInt(digits.slice(0, 2), 16),
            parseInt(digits.slice(2, 4), 16),
            parseInt(digits.slice(4, 6), 16)
        ];
    }

    function relativeLuminance(rgb) {
        var channels = rgb.map(function (value) {
            var proportion = value / 255;
            return proportion <= 0.03928
                ? proportion / 12.92
                : Math.pow((proportion + 0.055) / 1.055, 2.4);
        });
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
    }

    function contrastRatio(foreground, background) {
        var first = parseColor(foreground);
        var second = parseColor(background);
        if (!first || !second) {
            return null;
        }
        var lighter = relativeLuminance(first);
        var darker = relativeLuminance(second);
        if (lighter < darker) {
            var swap = lighter;
            lighter = darker;
            darker = swap;
        }
        return (lighter + 0.05) / (darker + 0.05);
    }

    /*
     * Check a theme.
     *
     * A missing token is skipped rather than failed: a partial theme inherits
     * the rest, and reporting an inherited pair as this theme's failure would
     * send an author looking in the wrong place.
     */
    function validate(tokens) {
        var values = tokens || {};
        var failures = [];
        var checked = 0;

        REQUIRED_PAIRS.forEach(function (pair) {
            var foreground = pair[0];
            var background = pair[1];
            if (!values[foreground] || !values[background]) {
                return;
            }
            var ratio = contrastRatio(values[foreground], values[background]);
            if (ratio === null) {
                return;
            }
            checked += 1;
            if (ratio < pair[2]) {
                failures.push({
                    foreground: foreground,
                    background: background,
                    ratio: Math.round(ratio * 100) / 100,
                    required: pair[2],
                    reason: pair[3]
                });
            }
        });

        return { failures: failures, checked: checked, passes: failures.length === 0 };
    }

    /*
     * Turn failures into sentences somebody can act on.
     *
     * A ratio alone tells an author they are wrong without telling them what to
     * change. Naming the pair and what it is *for* is the difference between a
     * warning that gets fixed and one that gets dismissed.
     */
    function describe(failures) {
        return (failures || []).map(function (failure) {
            return failure.foreground + " is " + failure.ratio.toFixed(2) + ":1 against " +
                failure.background + " -- " + failure.reason + " needs at least " +
                failure.required.toFixed(1) + ":1.";
        });
    }

    window.AetosContrast = {
        parseColor: parseColor,
        relativeLuminance: relativeLuminance,
        ratio: contrastRatio,
        validate: validate,
        describe: describe,
        REQUIRED_PAIRS: REQUIRED_PAIRS,
        AA_NORMAL_TEXT: AA_NORMAL_TEXT,
        AA_NON_TEXT: AA_NON_TEXT
    };

})(window);
