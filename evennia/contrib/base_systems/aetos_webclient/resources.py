"""
Aetos generic resources.

A resource is any numeric thing a game tracks about a character. Aetos assigns no
meaning to any of them: health, sanity, hull integrity, fuel, favour, hunger and
blood are all the same shape and render through the same widget. Nothing in Aetos
may special-case a resource name (blueprint section 19).

Resource shape::

    {
        "id":       "sanity",         # required, stable identifier
        "label":    "Sanity",         # required, human-readable
        "value":    71,               # required, number
        "maximum":  100,              # optional; omit for an unbounded counter
        "minimum":  0,                # optional, defaults to 0
        "display":  "gauge",          # optional presentation hint
        "thresholds": [               # optional, see below
            {"at": 0.5, "label": "Sanity slipping"},
            {"at": 0.2, "label": "Sanity critical", "level": "critical"},
        ],
    }

**Thresholds exist from the start, not as a later accessibility addition.**

A screen reader announcing every change to a resource that ticks each combat
round is unusable -- the player cannot get a word in. Blueprint section 48
requires announcements at meaningful crossings instead, and revision 2 makes that
part of the resource schema rather than something bolted on at review time. A
resource that declares no thresholds is simply never announced.

This module validates what a game's provider returns. Providers are game-supplied
code and a malformed resource must degrade to "not shown" rather than breaking the
client.

"""

from evennia.utils.ansi import parse_ansi

#: Presentation hints. A client may honour or ignore these; they are a
#: suggestion from the game, never a requirement.
DISPLAY_MODES = (
    "gauge",
    "vertical",
    "radial",
    "number",
    "percentage",
    "icon",
    "text",
)

DEFAULT_DISPLAY = "gauge"

#: Severity levels a threshold may declare. These describe importance, not
#: colour: a client must convey them by text as well (blueprint section 45).
THRESHOLD_LEVELS = ("info", "warning", "critical")

DEFAULT_THRESHOLD_LEVEL = "warning"

#: Bounds. A resource list is built per sync, so an unbounded one would be sent
#: repeatedly.
MAX_RESOURCES = 64
MAX_THRESHOLDS_PER_RESOURCE = 8
MAX_LABEL_LENGTH = 120
MAX_ID_LENGTH = 64

#: A unit is a word or two -- "litres", "rounds", "gp". Anything longer is a
#: label that has been put in the wrong field.
MAX_UNITS_LENGTH = 24


def _coerce_number(value):
    """
    Convert a value to a finite number, or None.

    Args:
        value: Anything a provider returned.

    Returns:
        float or int or None: The number, or None if it is not usable.

    """
    if isinstance(value, bool):
        # bool is an int subclass; a boolean resource value is a provider bug,
        # and silently rendering True as 1 would hide it.
        return None
    if not isinstance(value, (int, float)):
        return None
    if value != value or value in (float("inf"), float("-inf")):  # NaN / inf
        return None
    return value


def normalize_threshold(raw):
    """
    Validate one threshold.

    Args:
        raw (dict): Threshold as supplied by a provider.

    Returns:
        dict or None: The normalised threshold, or None if unusable.

    """
    if not isinstance(raw, dict):
        return None

    at = _coerce_number(raw.get("at"))
    if at is None:
        return None

    label = raw.get("label")
    if label is not None and not isinstance(label, str):
        return None

    level = raw.get("level", DEFAULT_THRESHOLD_LEVEL)
    if level not in THRESHOLD_LEVELS:
        level = DEFAULT_THRESHOLD_LEVEL

    return {
        "at": at,
        "label": (label or "")[:MAX_LABEL_LENGTH],
        "level": level,
    }


def normalize_resource(raw):
    """
    Validate and normalise one resource from a provider.

    Args:
        raw (dict): Resource as supplied by a provider.

    Returns:
        dict or None: The normalised resource, or None if it cannot be shown.

    """
    if not isinstance(raw, dict):
        return None

    identifier = raw.get("id")
    if not isinstance(identifier, str) or not identifier:
        return None

    value = _coerce_number(raw.get("value"))
    if value is None:
        return None

    maximum = _coerce_number(raw.get("maximum"))
    minimum = _coerce_number(raw.get("minimum"))
    if minimum is None:
        minimum = 0

    # A maximum below the minimum is a provider bug. Dropping the maximum leaves
    # a usable unbounded counter rather than a gauge that renders nonsensically.
    if maximum is not None and maximum < minimum:
        maximum = None

    label = raw.get("label")
    if not isinstance(label, str) or not label:
        label = identifier

    display = raw.get("display", DEFAULT_DISPLAY)
    if display not in DISPLAY_MODES:
        display = DEFAULT_DISPLAY

    thresholds = []
    raw_thresholds = raw.get("thresholds")
    if isinstance(raw_thresholds, (list, tuple)):
        for entry in raw_thresholds[:MAX_THRESHOLDS_PER_RESOURCE]:
            normalized = normalize_threshold(entry)
            if normalized:
                thresholds.append(normalized)
        # Descending, so a client crossing several at once can report the most
        # severe rather than the first it happens to check.
        thresholds.sort(key=lambda item: item["at"], reverse=True)

    resource = {
        "id": identifier[:MAX_ID_LENGTH],
        "label": label[:MAX_LABEL_LENGTH],
        "value": value,
        "minimum": minimum,
        "display": display,
        "thresholds": thresholds,
    }
    if maximum is not None:
        resource["maximum"] = maximum

    # A word for the value, supplied by the game.  Addendum A.77.
    #
    # "healthy", "bloodied", "critical" -- a game knows what its own numbers
    # mean and Aetos never will. A player reading "82 of 100" has to know the
    # scale to interpret it; a player reading "82 of 100, healthy" does not.
    #
    # It is also the field that makes a resource legible where a bar cannot go
    # at all: braille, a compact status line, or a spoken summary.
    state_text = raw.get("state_text")
    if isinstance(state_text, str) and state_text:
        resource["state_text"] = parse_ansi(state_text, strip_ansi=True)[:MAX_LABEL_LENGTH]

    # Units, so a client can say "40 litres" rather than "40" and a screen
    # reader does not have to leave the player guessing what was counted.
    units = raw.get("units")
    if isinstance(units, str) and units:
        resource["units"] = parse_ansi(units, strip_ansi=True)[:MAX_UNITS_LENGTH]

    return resource


def normalize_resources(raw_resources):
    """
    Validate a provider's full resource list.

    Malformed entries are dropped individually: one bad resource must not cost
    the player every other one.

    Args:
        raw_resources: Whatever the provider returned.

    Returns:
        list: Normalised resources, possibly empty.

    """
    if not isinstance(raw_resources, (list, tuple)):
        return []

    seen = set()
    normalized = []
    for entry in raw_resources:
        resource = normalize_resource(entry)
        if not resource:
            continue
        # A duplicate id would make two widgets fight over the same slot.
        if resource["id"] in seen:
            continue
        seen.add(resource["id"])
        normalized.append(resource)
        if len(normalized) >= MAX_RESOURCES:
            break
    return normalized


def fraction(resource):
    """
    Return a resource's fill fraction, if it has one.

    Args:
        resource (dict): A normalised resource.

    Returns:
        float or None: Value between 0 and 1, or None when unbounded.

    """
    maximum = resource.get("maximum")
    if maximum is None:
        return None
    minimum = resource.get("minimum", 0)
    span = maximum - minimum
    if span <= 0:
        return None
    position = (resource.get("value", minimum) - minimum) / float(span)
    return max(0.0, min(1.0, position))
