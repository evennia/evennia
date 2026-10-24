"""
Normalisation for the four sections that describe the character rather than the
room: inventory, equipment, target and effects.

Providers are game-supplied code, so nothing they return is trusted. Every value
is coerced and bounded here, in one place, so a delta and a full sync can never
disagree about a shape and a buggy provider costs one entry rather than a widget.

**Nothing in this module is a genre concept.** An "effect" is only "something
temporarily true about this character" -- a poison, a stance, a weather exposure,
a debt timer. An equipment "slot" is whatever string the game calls it. Aetos
assigns no meaning to any of them, exactly as it assigns none to a resource.

**A countdown is display, not authority.** An effect's `remaining` is how long the
*server* said was left when the sync was built. The client may count it down for
smoothness, but reaching zero means "the server has not told us yet", never "this
effect is gone" (blueprint section 2.4). Which is also why it is sent as a
duration rather than a wall-clock time: the player's clock may be minutes off the
server's, and an absolute timestamp would be silently wrong for them.

"""

from evennia.contrib.base_systems.aetos_webclient import resources
from evennia.utils.ansi import parse_ansi
from evennia.utils.text2html import parse_html

#: Bounds. Each of these sections is rebuilt on every sync, so an unbounded one
#: would be re-sent continuously rather than once.
MAX_INVENTORY_ITEMS = 200
MAX_EQUIPMENT_SLOTS = 40
MAX_EFFECTS = 40
MAX_TARGET_EFFECTS = 24
MAX_ID_LENGTH = 64
MAX_LABEL_LENGTH = 120
MAX_CATEGORY_LENGTH = 60
MAX_DESCRIPTION_LENGTH = 500

#: Advisory tone for an effect. A client may colour or group by these, but must
#: never rely on them alone: colour is not information a screen reader or a
#: colour-blind player receives (blueprint section 45), so the label always
#: carries the meaning.
EFFECT_KINDS = ("helpful", "harmful", "neutral")
DEFAULT_EFFECT_KIND = "neutral"


def _text(value, limit):
    """
    Coerce a provider value to bounded plain text.

    Args:
        value: Whatever the provider supplied.
        limit (int): Maximum length.

    Returns:
        str: Plain text with Evennia markup stripped, or "" if unusable.

    """
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return parse_ansi(value, strip_ansi=True)[:limit]


def _named(raw, name_key="name"):
    """
    Build the plain/display name pair used everywhere in Aetos.

    A name is needed twice and for opposite reasons: plain, because a button may
    put it into a command and markup would produce something the parser cannot
    read; and as HTML, because the game coloured it for a reason.

    Args:
        raw (dict): The provider entry.
        name_key (str): Which key holds the name.

    Returns:
        tuple: The plain name and its HTML form.

    """
    value = raw.get(name_key)
    if value is None:
        return "", ""
    if not isinstance(value, str):
        value = str(value)
    return parse_ansi(value, strip_ansi=True)[:MAX_LABEL_LENGTH], parse_html(value)


def _positive_int(value, default=None):
    """
    Coerce to a non-negative integer.

    Args:
        value: Whatever the provider supplied.
        default: Returned when the value is unusable.

    Returns:
        int: The coerced value, or `default`.

    """
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return number if number >= 0 else default


def _seconds(value):
    """
    Coerce a duration in seconds.

    Args:
        value: Whatever the provider supplied.

    Returns:
        float: Seconds, or None if absent or unusable.

    """
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number == float("inf") or number == float("-inf"):
        # NaN and infinity would produce a countdown that never resolves.
        return None
    return max(0.0, number)


def normalize_item(raw):
    """
    Validate one carried or equipped item.

    Args:
        raw (dict): The provider's item.

    Returns:
        dict: The item, or None if it is unusable.

    """
    if not isinstance(raw, dict):
        return None

    identifier = _text(raw.get("id"), MAX_ID_LENGTH)
    name, display = _named(raw)
    if not identifier or not name:
        # An item with no id cannot be acted on, and one with no name cannot be
        # shown. Either way there is nothing useful to render.
        return None

    item = {"id": identifier, "name": name, "display": display}

    kind = _text(raw.get("kind"), MAX_CATEGORY_LENGTH)
    if kind:
        item["kind"] = kind

    category = _text(raw.get("category"), MAX_CATEGORY_LENGTH)
    if category:
        item["category"] = category

    quantity = _positive_int(raw.get("quantity"))
    if quantity is not None:
        item["quantity"] = quantity

    return item


def normalize_inventory(raw_items):
    """
    Validate a provider's inventory list.

    Args:
        raw_items: Whatever the provider returned.

    Returns:
        list: Valid items, possibly empty.

    """
    if not isinstance(raw_items, (list, tuple)):
        return []
    items = []
    for raw in raw_items[:MAX_INVENTORY_ITEMS]:
        item = normalize_item(raw)
        if item is not None:
            items.append(item)
    return items


def normalize_equipment(raw_slots):
    """
    Validate a provider's equipment list.

    An empty slot is kept rather than dropped. "Nothing on your head" is
    information a player needs, and silently omitting empty slots would make a
    bare character indistinguishable from a game with no equipment at all.

    Slot order is the provider's, because only the game knows whether its slots
    read head-to-toe, by hand, or by importance.

    Args:
        raw_slots: Whatever the provider returned.

    Returns:
        list: Slot dicts with `slot`, `label`, and `item` (a dict or None).

    """
    if not isinstance(raw_slots, (list, tuple)):
        return []

    slots = []
    seen = set()
    for raw in raw_slots[:MAX_EQUIPMENT_SLOTS]:
        if not isinstance(raw, dict):
            continue
        slot_id = _text(raw.get("slot"), MAX_ID_LENGTH)
        if not slot_id or slot_id in seen:
            # A duplicate slot would render twice and the player could not tell
            # which one was real.
            continue
        seen.add(slot_id)

        label, label_display = _named(raw, "label")
        if not label:
            label = slot_id
            label_display = slot_id

        slots.append(
            {
                "slot": slot_id,
                "label": label,
                "display": label_display,
                "item": normalize_item(raw.get("item")),
            }
        )
    return slots


def normalize_effect(raw):
    """
    Validate one effect.

    Args:
        raw (dict): The provider's effect.

    Returns:
        dict: The effect, or None if it is unusable.

    """
    if not isinstance(raw, dict):
        return None

    identifier = _text(raw.get("id"), MAX_ID_LENGTH)
    label, display = _named(raw, "label")
    if not identifier or not label:
        return None

    kind = _text(raw.get("kind"), MAX_CATEGORY_LENGTH).lower()
    if kind not in EFFECT_KINDS:
        # An unrecognised tone is not worth dropping an effect over -- the label
        # still carries the meaning, which is where it has to live anyway.
        kind = DEFAULT_EFFECT_KIND

    effect = {"id": identifier, "label": label, "display": display, "kind": kind}

    remaining = _seconds(raw.get("remaining"))
    if remaining is not None:
        effect["remaining"] = remaining
    duration = _seconds(raw.get("duration"))
    if duration is not None:
        effect["duration"] = duration

    stacks = _positive_int(raw.get("stacks"))
    if stacks is not None and stacks > 1:
        # A stack count of one is what everything already looks like; sending it
        # would make every widget render a redundant "x1".
        effect["stacks"] = stacks

    description = _text(raw.get("description"), MAX_DESCRIPTION_LENGTH)
    if description:
        effect["description"] = description

    return effect


def normalize_effects(raw_effects, limit=MAX_EFFECTS):
    """
    Validate a provider's effect list.

    Args:
        raw_effects: Whatever the provider returned.
        limit (int): Maximum effects to keep.

    Returns:
        list: Valid effects, possibly empty.

    """
    if not isinstance(raw_effects, (list, tuple)):
        return []
    effects = []
    seen = set()
    for raw in raw_effects[:limit]:
        effect = normalize_effect(raw)
        if effect is None or effect["id"] in seen:
            continue
        seen.add(effect["id"])
        effects.append(effect)
    return effects


def normalize_target(raw):
    """
    Validate the current target.

    A target's resources go through the *same* normaliser as the player's own, so
    a target's health bar and the player's cannot disagree about thresholds,
    rounding or announcement rules. A player who has learned to read one has
    learned to read the other.

    Args:
        raw: Whatever the provider returned.

    Returns:
        dict: Target data, or an empty dict when there is no target.

    """
    if not isinstance(raw, dict) or not raw:
        return {}

    identifier = _text(raw.get("id"), MAX_ID_LENGTH)
    name, display = _named(raw)
    if not identifier or not name:
        return {}

    target = {"id": identifier, "name": name, "display": display}

    kind = _text(raw.get("kind"), MAX_CATEGORY_LENGTH)
    if kind:
        target["kind"] = kind

    target["resources"] = resources.normalize_resources(raw.get("resources"))
    target["effects"] = normalize_effects(raw.get("effects"), limit=MAX_TARGET_EFFECTS)

    relationship = _text(raw.get("relationship"), MAX_CATEGORY_LENGTH)
    if relationship:
        # The *game's* view of the relationship (hostile, allied, neutral). The
        # player's own private tags from M11 live only in their browser and are
        # merged client-side; the two must never be confused, which is why they
        # arrive by entirely different routes.
        target["relationship"] = relationship

    return target
