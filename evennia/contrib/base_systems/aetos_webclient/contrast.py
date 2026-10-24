"""
WCAG contrast ratios, and the pairs a theme has to get right.

Addendum A.55, `A11Y-VIS-003`: themes MUST meet contrast requirements, theme
validation MUST be part of theme acceptance, and a theme that fails MUST produce
a warning.

WHY THIS IS A TEST AND NOT ONLY A RUNTIME CHECK
-----------------------------------------------

A palette chosen by eye passes for the person who chose it. That is not a
criticism of anyone's judgement -- it is what having particular eyes means. The
designer of a low-contrast theme is, by construction, someone who could read it.

So Aetos's own themes are checked by a test that reads them out of the
stylesheet and computes the ratios. A high-contrast theme that fails contrast is
the exact failure `A11Y-VIS-003` exists to prevent, and it is not hypothetical:
it is the most common way accessibility themes go wrong, because the muted
colour is chosen to recede and then recedes past legibility.

User themes are checked at save time by the client, with the same thresholds.

WHAT THE RATIOS MEAN
--------------------

The formula is WCAG 2.x: relative luminance of each colour, then
`(lighter + 0.05) / (darker + 0.05)`. It is a published, fixed calculation --
this module implements it rather than inventing anything.

`4.5:1` is the AA threshold for normal text; `3:1` for large text and for
non-text elements that carry meaning, such as a border that separates two
regions or the fill of a progress bar. Aetos holds itself to AA, not AAA:
committing to 7:1 would rule out most legible palettes and push games towards
ignoring the system entirely, which helps nobody.

"""

import re

#: WCAG 2.2 AA thresholds.
AA_NORMAL_TEXT = 4.5
AA_LARGE_TEXT = 3.0
AA_NON_TEXT = 3.0


def parse_color(value):
    """
    Parse a CSS hex colour into RGB components.

    Only hex is accepted. A theme token is a colour literal, not an expression:
    supporting `rgb()`, `hsl()`, `color-mix()` and named colours would mean
    reimplementing a CSS colour parser in order to reject one of them, and every
    format that cannot be checked is a format a failing theme can hide in.

    Args:
        value (str): A CSS colour, `#rgb` or `#rrggbb`.

    Returns:
        tuple or None: `(r, g, b)` as 0-255 ints, or None if unparseable.

    """
    if not isinstance(value, str):
        return None
    text = value.strip().lower()
    match = re.fullmatch(r"#([0-9a-f]{3}|[0-9a-f]{6})", text)
    if not match:
        return None
    digits = match.group(1)
    if len(digits) == 3:
        digits = "".join(digit * 2 for digit in digits)
    return tuple(int(digits[index : index + 2], 16) for index in (0, 2, 4))


def relative_luminance(rgb):
    """
    Compute WCAG relative luminance.

    Args:
        rgb (tuple): `(r, g, b)` as 0-255 ints.

    Returns:
        float: Luminance between 0.0 and 1.0.

    """
    channels = []
    for value in rgb:
        proportion = value / 255.0
        if proportion <= 0.03928:
            channels.append(proportion / 12.92)
        else:
            channels.append(((proportion + 0.055) / 1.055) ** 2.4)
    red, green, blue = channels
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(foreground, background):
    """
    Compute the WCAG contrast ratio between two colours.

    Args:
        foreground (str): A hex colour.
        background (str): A hex colour.

    Returns:
        float or None: The ratio, 1.0 to 21.0, or None if either colour is
            unparseable.

    """
    first = parse_color(foreground)
    second = parse_color(background)
    if first is None or second is None:
        return None
    lighter = relative_luminance(first)
    darker = relative_luminance(second)
    if lighter < darker:
        lighter, darker = darker, lighter
    return (lighter + 0.05) / (darker + 0.05)


#: The pairs every theme must satisfy, and why each one matters.
#:
#: Named rather than derived, because "every token against every other token"
#: would produce dozens of pairs that never appear together on screen -- and a
#: validator that reports failures nobody can see is a validator people learn to
#: ignore.
REQUIRED_PAIRS = (
    ("--aetos-text", "--aetos-bg", AA_NORMAL_TEXT, "body text on the background"),
    ("--aetos-text", "--aetos-panel", AA_NORMAL_TEXT, "body text on a panel"),
    # The muted colour is where contrast themes usually fail: it is chosen to
    # recede, and then recedes past legibility.
    ("--aetos-text-muted", "--aetos-bg", AA_NORMAL_TEXT, "secondary text on the background"),
    ("--aetos-text-muted", "--aetos-panel", AA_NORMAL_TEXT, "secondary text on a panel"),
    ("--aetos-accent", "--aetos-panel", AA_NON_TEXT, "accents and headings on a panel"),
    ("--aetos-success", "--aetos-panel", AA_NON_TEXT, "the success colour on a panel"),
    ("--aetos-warning", "--aetos-panel", AA_NON_TEXT, "the warning colour on a panel"),
    ("--aetos-danger", "--aetos-panel", AA_NON_TEXT, "the danger colour on a panel"),
    # Borders carry structure: they are what separates one region from another
    # for somebody who cannot rely on a subtle background difference.
    ("--aetos-border", "--aetos-bg", AA_NON_TEXT, "panel borders against the background"),
    ("--aetos-focus", "--aetos-bg", AA_NON_TEXT, "the focus ring on the background"),
    ("--aetos-focus", "--aetos-panel", AA_NON_TEXT, "the focus ring on a panel"),
)


def validate_theme(tokens):
    """
    Check a theme's colours against every required pair.

    Args:
        tokens (dict): Token name mapped to a hex colour. Missing tokens are
            skipped rather than failed -- a partial theme inherits the rest,
            and reporting an inherited pair as this theme's failure would send
            an author looking in the wrong place.

    Returns:
        dict: `{"failures": [...], "checked": int, "unparseable": [...]}`.
            Each failure carries the pair, its ratio, the threshold and the
            plain-language reason.

    """
    failures = []
    unparseable = []
    checked = 0

    for foreground, background, threshold, reason in REQUIRED_PAIRS:
        if foreground not in tokens or background not in tokens:
            continue
        ratio = contrast_ratio(tokens[foreground], tokens[background])
        if ratio is None:
            unparseable.append((foreground, background))
            continue
        checked += 1
        if ratio < threshold:
            failures.append(
                {
                    "foreground": foreground,
                    "background": background,
                    "ratio": round(ratio, 2),
                    "required": threshold,
                    "reason": reason,
                }
            )

    return {"failures": failures, "checked": checked, "unparseable": unparseable}


def describe_failures(failures):
    """
    Turn failures into sentences an author can act on.

    A ratio on its own tells somebody they are wrong without telling them what
    to change. Naming the pair and what it is *for* is the difference between a
    warning that gets fixed and one that gets dismissed.

    Args:
        failures (list): Failures from `validate_theme`.

    Returns:
        list: One sentence per failure.

    """
    return [
        "%s is %.2f:1 against %s -- %s needs at least %.1f:1."
        % (
            failure["foreground"],
            failure["ratio"],
            failure["background"],
            failure["reason"],
            failure["required"],
        )
        for failure in failures
    ]


def extract_theme_tokens(css, selector):
    """
    Read a theme's tokens out of a stylesheet block.

    Used to check Aetos's own shipped themes, which live in CSS rather than in
    a Python table. Reading them from the stylesheet means the test checks what
    actually ships, rather than a copy that can drift from it.

    Args:
        css (str): Stylesheet source.
        selector (str): The selector introducing the block, e.g. `:root`.

    Returns:
        dict: Token name mapped to its declared value.

    """
    marker = selector + " {"
    if marker not in css:
        return {}
    start = css.index(marker) + len(marker)
    block = css[start : css.index("}", start)]
    return {
        name: value.strip()
        for name, value in re.findall(r"(--aetos-[a-z-]+)\s*:\s*([^;]+);", block)
    }
