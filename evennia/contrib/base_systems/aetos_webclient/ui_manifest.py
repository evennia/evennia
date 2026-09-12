"""
The server-described UI manifest.  Milestone M23.

A game describes its interface declaratively::

    AETOS_UI = {
        "resources": [
            {"id": "health", "label": "Health", "order": 1,
             "thresholds": [{"at": 0.25, "label": "badly hurt",
                             "level": "critical"}]},
            {"id": "stamina", "label": "Stamina", "order": 2},
        ],
        "panels": {
            "resources": {"title": "Vitals"},
        },
    }

WHAT THIS IS, AND WHAT IT DELIBERATELY IS NOT
---------------------------------------------

This is **description**, not **data**. It says a resource called `health` exists,
what to call it, where it sits in the list and when it is worth announcing. It
says nothing about where the number comes from.

That line matters because the other side of it is the D-track (`AETOS_BINDINGS`),
which is about *sourcing* values from a game's own model. Keeping the two apart
means a game can describe its interface today, without Discovery, and adopt
bindings later without rewriting any of it.

WHY DESCRIPTION ALONE IS WORTH HAVING
-------------------------------------

Two things a provider cannot do:

**A gauge can exist before its first value.** Without this, a resource widget is
empty until the first sync arrives -- so a player on a slow connection, or one
who reconnects mid-fight, sees a blank panel and cannot tell whether the game has
no health bar or has not spoken yet. Declaring it means the panel renders
immediately, labelled, with its value pending.

**Order is stable.** Provider output arrives as a list, and a game assembling
that list from a dict gets whatever order the dict yields. A health bar that
moves between second and fourth place between syncs is not a cosmetic problem
for somebody navigating by position or by screen reader.

WHAT IT CANNOT DO
-----------------

It cannot create a widget, run a command, override a lock, or change what the
game sends. Everything here is presentation metadata that the client applies to
data the game supplies through the ordinary channels -- so a malformed or hostile
`AETOS_UI` produces a badly labelled interface, never a privileged one.

Unknown keys are an error rather than being ignored, for the same reason
`AETOS_FEATURES` rejects them: a typo in a settings key is otherwise silent, and
a developer believing they had renamed a gauge would simply never see it change.

"""

from django.conf import settings

from evennia.contrib.base_systems.aetos_webclient import resources

#: Sections a game may describe. An allowlist, so a typo is caught rather than
#: silently doing nothing.
UI_SECTIONS = ("resources", "panels")

#: The keys a threshold declaration may carry.
#:
#: Checked here and not in `resources.py`, and the asymmetry is deliberate: a
#: *provider* is game code producing values at runtime, contained by `safe_call`
#: and expected to be imperfect. A *setting* is a developer typing a literal,
#: where a wrong key is a mistake they want told about.
#:
#: Found by declaring `state_text` and `announce` -- A.77's field names, which
#: belong to a resource rather than a threshold. They were accepted silently and
#: produced a threshold with an empty label at the default level: one that would
#: never announce anything useful, with nothing to say why.
THRESHOLD_KEYS = ("at", "label", "level")

#: Panels whose presentation a game may adjust. Naming them explicitly keeps
#: this from becoming a general-purpose style sheet -- a game may rename a
#: panel, not restyle the client.
PANEL_KEYS = (
    "resources",
    "inventory",
    "equipment",
    "effects",
    "target",
    "map",
    "entities",
    "media",
)

MAX_DESCRIBED_RESOURCES = 64
MAX_TITLE_LENGTH = 60


class AetosUIError(ValueError):
    """Raised when a game's `AETOS_UI` setting is malformed."""


def _describe_resource(raw, index):
    """
    Validate one declared resource descriptor.

    Reuses the resource normaliser for thresholds so a declared threshold and a
    provider-supplied one cannot mean different things -- two validators for one
    concept is how a client ends up announcing at 25% in one place and 0.25 in
    another.

    Args:
        raw (dict): The declaration from settings.
        index (int): Position in the list, for error messages.

    Returns:
        dict: A validated descriptor.

    Raises:
        AetosUIError: If the declaration is malformed.

    """
    if not isinstance(raw, dict):
        raise AetosUIError(
            "AETOS_UI['resources'][%d] must be a dict, got %r" % (index, type(raw).__name__)
        )

    identifier = raw.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise AetosUIError("AETOS_UI['resources'][%d] needs a non-empty 'id'" % index)

    descriptor = {
        "id": identifier.strip()[: resources.MAX_ID_LENGTH],
        # Falls back to the id rather than to a blank: an unlabelled gauge is
        # announced as "edit, blank" or worse, and the id is at least a word.
        "label": str(raw.get("label") or identifier).strip()[: resources.MAX_LABEL_LENGTH],
        # Declared order wins over arrival order. Missing means "after the
        # declared ones", not "first".
        "order": int(raw["order"]) if isinstance(raw.get("order"), int) else None,
    }

    units = raw.get("units")
    if isinstance(units, str) and units.strip():
        descriptor["units"] = units.strip()[: resources.MAX_UNITS_LENGTH]

    thresholds = []
    raw_thresholds = raw.get("thresholds")
    if raw_thresholds is not None and not isinstance(raw_thresholds, (list, tuple)):
        raise AetosUIError("AETOS_UI['resources'][%d]['thresholds'] must be a list" % index)
    for position, entry in enumerate(
        (raw_thresholds or [])[: resources.MAX_THRESHOLDS_PER_RESOURCE]
    ):
        if not isinstance(entry, dict):
            raise AetosUIError(
                "AETOS_UI['resources'][%d]['thresholds'][%d] must be a dict" % (index, position)
            )
        unknown = set(entry) - set(THRESHOLD_KEYS)
        if unknown:
            raise AetosUIError(
                "AETOS_UI['resources'][%d]['thresholds'][%d] has unknown key(s) %s. "
                "Valid keys: %s" % (index, position, sorted(unknown), sorted(THRESHOLD_KEYS))
            )
        threshold = resources.normalize_threshold(entry)
        if threshold is None:
            raise AetosUIError(
                "AETOS_UI['resources'][%d]['thresholds'][%d] needs a numeric 'at'"
                % (index, position)
            )
        if not threshold["label"]:
            # A threshold with no label announces nothing a player can act on,
            # which makes it indistinguishable from having no threshold at all.
            raise AetosUIError(
                "AETOS_UI['resources'][%d]['thresholds'][%d] needs a 'label' -- it is "
                "what a player is told when the threshold is crossed" % (index, position)
            )
        thresholds.append(threshold)
    if thresholds:
        descriptor["thresholds"] = thresholds

    return descriptor


def _describe_panels(raw):
    """
    Validate declared panel presentation.

    Args:
        raw (dict): The `panels` section from settings.

    Returns:
        dict: Validated panel descriptors.

    Raises:
        AetosUIError: If a panel is unknown or malformed.

    """
    if not isinstance(raw, dict):
        raise AetosUIError("AETOS_UI['panels'] must be a dict, got %r" % type(raw).__name__)

    unknown = set(raw) - set(PANEL_KEYS)
    if unknown:
        raise AetosUIError(
            "AETOS_UI['panels'] contains unknown panel(s) %s. Valid panels: %s"
            % (sorted(unknown), sorted(PANEL_KEYS))
        )

    described = {}
    for key, value in raw.items():
        if not isinstance(value, dict):
            raise AetosUIError("AETOS_UI['panels'][%r] must be a dict" % key)
        title = value.get("title")
        if title is not None:
            if not isinstance(title, str) or not title.strip():
                raise AetosUIError(
                    "AETOS_UI['panels'][%r]['title'] must be a non-empty string" % key
                )
            # A title is the panel's accessible name as well as its heading, so
            # it is the one field worth refusing rather than silently dropping.
            described[key] = {"title": title.strip()[:MAX_TITLE_LENGTH]}
    return described


def get_ui_description():
    """
    Read and validate the game's `AETOS_UI` setting.

    Returns:
        dict: `{"resources": [...], "panels": {...}}`, both possibly empty.

    Raises:
        AetosUIError: If the setting is malformed.

    """
    configured = getattr(settings, "AETOS_UI", None)
    if configured is None:
        return {"resources": [], "panels": {}}

    if not isinstance(configured, dict):
        raise AetosUIError("AETOS_UI must be a dict, got %r" % type(configured).__name__)

    unknown = set(configured) - set(UI_SECTIONS)
    if unknown:
        raise AetosUIError(
            "AETOS_UI contains unknown section(s) %s. Valid sections: %s"
            % (sorted(unknown), sorted(UI_SECTIONS))
        )

    described_resources = []
    raw_resources = configured.get("resources", [])
    if not isinstance(raw_resources, (list, tuple)):
        raise AetosUIError(
            "AETOS_UI['resources'] must be a list, got %r" % type(raw_resources).__name__
        )

    seen = set()
    for index, raw in enumerate(raw_resources[:MAX_DESCRIBED_RESOURCES]):
        descriptor = _describe_resource(raw, index)
        if descriptor["id"] in seen:
            raise AetosUIError("AETOS_UI['resources'] declares %r twice" % descriptor["id"])
        seen.add(descriptor["id"])
        described_resources.append(descriptor)

    return {
        "resources": described_resources,
        "panels": _describe_panels(configured.get("panels", {})),
    }


def order_resources(items, described):
    """
    Apply a declared order to a provider's resource list.

    Declared resources come first, in their declared order; anything the game
    sends but did not declare follows in arrival order.

    Undeclared resources are **kept**, not dropped. A game that adds a resource
    to its provider and forgets the declaration should see it appear at the
    bottom, not vanish -- the second failure is much harder to diagnose and the
    first is self-correcting.

    Args:
        items (list): Normalised resources from the provider.
        described (list): Declared descriptors, in declaration order.

    Returns:
        list: The same resources, reordered.

    """
    if not described:
        return items

    position = {}
    for index, descriptor in enumerate(described):
        explicit = descriptor.get("order")
        position[descriptor["id"]] = explicit if explicit is not None else index

    # Undeclared resources sort after every declared one, keeping their relative
    # order via the enumerate index.
    after = len(described) + max((position.values() or [0]), default=0) + 1

    return sorted(
        items,
        key=lambda item: (position.get(item.get("id"), after), items.index(item)),
    )
