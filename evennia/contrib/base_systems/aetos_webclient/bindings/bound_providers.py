"""
Providers that read a declaration instead of a game's Python.

These are ordinary providers. They subclass the same bases, return the same
payloads and go through the same normalisers as a hand-written one, which is the
property that matters: **the client cannot tell which route supplied the data.**
A game that outgrows a binding and writes a provider class changes nothing about
what the player sees, and a game that starts with a class and simplifies to a
binding does not have to re-check its widgets.

That is not a coincidence, it is why M16 put every slot through a normaliser. A
second code path into the client would be a second set of bugs, and the first
place they would show is on the accessibility surface -- announcements,
thresholds and labels are computed from the normalised shape.

D1 implemented `resources`, which was its gate. **D2 completes the set**:
`equipment`, `target`, `effects` and `actions`.

WHAT A DECLARATION CAN SAY PER SLOT, and why each shape is the one it is.

`resources` and `equipment` are lists of named things, so a binding names each
one and says where its value lives. `effects` is the same shape asking a
different question: the value answers *is this active*, and an optional
`remaining` says for how long.

`target` is the odd one, because it is a single object rather than a list. The
convention is one reserved key::

    "target": {
        "name":   {"label": "Target", "value": "db.target_name"},
        "health": {"label": "Health", "value": "db.t_hp", "maximum": "db.t_hp_max"},
    }

`name` is the target's identity, and every other entry becomes one of the
target's resources -- which go through the *same* resource normaliser as the
player's own, so a target's health bar and the player's cannot disagree about
thresholds or rounding. No name resolves, no target: "nothing is targeted" is a
real state, and a target with a health bar and no name would be worse than none.

`actions` needs no resolver at all. An action is a label and an ordinary game
command, and the only substitution is `{target}` -- the name of the entity whose
menu was opened. That is a placeholder, not an expression: no operators, no
attribute reads, and exactly one of it.

**Offering an action does not make it legal.** The command travels the ordinary
command path and the server decides, exactly as if the player had typed it. A
binding cannot grant a permission, bypass a lock or skip a cooldown, and a game
that removes a command sees the action stop working without Aetos knowing why.

"""

from evennia.contrib.base_systems.aetos_webclient.bindings.resolver import (
    AetosBindingResolver,
)
from evennia.contrib.base_systems.aetos_webclient.bindings.settings_source import (
    get_bindings,
)
from evennia.contrib.base_systems.aetos_webclient.providers import base


def _declared(slot):
    """
    One slot's declaration, or nothing if the settings are malformed.

    Args:
        slot (str): The provider slot name.

    Returns:
        dict: The slot's entries, in declaration order.

    Notes:
        Every provider here runs inside a websocket handler while a player is
        connecting, so a malformed setting must cost a widget rather than a
        session. The developer is told by the startup check instead, which is
        where they are looking.

        One helper rather than the same try/except in five places: five copies
        of an error path is five chances for one of them to be the version that
        raises.

    """
    try:
        return get_bindings().get(slot, {})
    except Exception:
        return {}


class BoundResourceProvider(base.AetosResourceProvider):
    """
    Resources declared in `AETOS_BINDINGS["resources"]`.

    """

    name = "resources (bindings)"

    def __init__(self, resolver=None):
        """
        Args:
            resolver (AetosBindingResolver, optional): Injected for tests, and so
                that a game with an unusual attribute store can subclass one
                thing rather than this whole provider.

        """
        self.resolver = resolver or AetosBindingResolver()

    def describe(self):
        """
        Identify this provider for the developer inspector.

        Returns:
            dict: The provider's name, class and the keys it serves.

        Notes:
            The keys are included because "resources (bindings)" on its own
            leaves a developer wondering which of their declarations are live.
            Names only -- never the expressions, which say where a game keeps its
            data, and never values.

        """
        described = super().describe()
        try:
            described["bound"] = sorted(get_bindings().get("resources", {}))
        except Exception:
            described["bound"] = []
        return described

    def get_resources(self, character):
        """
        Build the character's resources from the declaration.

        Args:
            character (Object): The character to describe.

        Returns:
            list: Resource dicts, in the shape `resources.normalize_resources`
                expects.

        Notes:
            **A resource whose value will not resolve is omitted, not zeroed.**
            A bar reading 0 says "you are dead"; a missing bar says "this is not
            available", and only one of those is true when a binding points at an
            attribute a character has not got yet.

            The declared order is kept. Python dicts preserve insertion order, so
            the order in settings.py is the order on screen, which is the one
            thing a developer can control here without another field.

        """
        declared = _declared("resources")
        built = []
        for key, entry in declared.items():
            value = self.resolver.resolve_number(character, entry["value"])
            if value is None:
                continue

            resource = {
                "id": key,
                "label": entry.get("label", key),
                "value": value,
            }

            for field in ("maximum", "minimum"):
                if field in entry:
                    bound = self.resolver.resolve_number(character, entry[field])
                    if bound is not None:
                        resource[field] = bound

            # `severity` and `display` are plain text in the declaration and are
            # passed through for the normaliser to accept or drop. Validating
            # them twice would put the list of legal display modes in two files.
            for field in ("display", "severity"):
                if field in entry:
                    resource[field] = entry[field]

            built.append(resource)

        return built


class BoundEquipmentProvider(base.AetosEquipmentProvider):
    """Equipment slots declared in `AETOS_BINDINGS["equipment"]`."""

    name = "equipment (bindings)"

    def __init__(self, resolver=None):
        """
        Args:
            resolver (AetosBindingResolver, optional): Injected for tests.

        """
        self.resolver = resolver or AetosBindingResolver()

    def get_equipment(self, character):
        """
        Build the character's equipment slots from the declaration.

        Args:
            character (Object): The character to describe.

        Returns:
            list: Slot dicts in the shape `normalize_equipment` expects.

        Notes:
            **An empty slot is kept, which is the opposite of the resources
            rule.** "Nothing on your head" is information a player needs, and
            dropping empty slots would make a bare character indistinguishable
            from a game with no equipment at all.

            A resource is different because one that will not resolve is not
            *empty*, it is *absent* -- the game never had that number for this
            character.

            What is stored may be text, a number, or a game object. The resolver
            hands over whatever is there without touching it, and
            `normalize_item` stringifies it exactly as it does for any provider.
            That is not a new exposure; it is the coercion every provider's
            payload has always gone through.

        """
        slots = []

        for key, entry in _declared("equipment").items():
            equipped = self.resolver.resolve(character, entry["value"])
            slot = {"slot": key, "label": entry.get("label", key), "item": None}

            if equipped is not None and equipped != "":
                item = {"id": key, "name": equipped}
                for field in ("kind", "category"):
                    if field in entry:
                        item[field] = entry[field]
                slot["item"] = item

            slots.append(slot)

        return slots


class BoundEffectProvider(base.AetosEffectProvider):
    """Effects declared in `AETOS_BINDINGS["effects"]`."""

    name = "effects (bindings)"

    def __init__(self, resolver=None):
        """
        Args:
            resolver (AetosBindingResolver, optional): Injected for tests.

        """
        self.resolver = resolver or AetosBindingResolver()

    def get_effects(self, character):
        """
        Build the character's active effects from the declaration.

        Args:
            character (Object): The character to describe.

        Returns:
            list: Effect dicts in the shape `normalize_effects` expects.

        Notes:
            The `value` answers *is this active*, so it is read for truthiness
            rather than as a number: `db.poisoned = True` and
            `db.poison_stacks = 3` both mean poisoned, and a game should not have
            to pick one to suit Aetos.

            **Zero is not active.** A countdown that has reached 0 has expired,
            and an effect list that goes on showing it is one a player learns to
            distrust. Python's truthiness is exactly right here, which is worth
            saying out loud because it usually is not.

        """
        built = []

        for key, entry in _declared("effects").items():
            if not self.resolver.resolve(character, entry["value"]):
                continue

            effect = {"id": key, "label": entry.get("label", key)}
            for field in ("kind", "description"):
                if field in entry:
                    effect[field] = entry[field]
            for field in ("remaining", "duration"):
                if field in entry:
                    seconds = self.resolver.resolve_number(character, entry[field])
                    if seconds is not None:
                        effect[field] = seconds

            built.append(effect)

        return built


class BoundTargetProvider(base.AetosTargetProvider):
    """The current target, declared in `AETOS_BINDINGS["target"]`."""

    name = "target (bindings)"

    #: The entry that names the target rather than measuring it.
    #:
    #: Reserved rather than configurable. A `"name_field"` option would be a
    #: setting whose only purpose is to rename another setting.
    NAME_KEY = "name"

    def __init__(self, resolver=None):
        """
        Args:
            resolver (AetosBindingResolver, optional): Injected for tests.

        """
        self.resolver = resolver or AetosBindingResolver()

    def get_target(self, character):
        """
        Build the current target from the declaration.

        Args:
            character (Object): The character whose target this is.

        Returns:
            dict: Target data, or an empty dict when nothing is targeted.

        Notes:
            No `name` entry, or a name that will not resolve, means no target --
            and an empty dict is what "nothing is targeted" looks like everywhere
            else in Aetos, so the widget hides itself with no special case.

            Returning resources without a name would be worse than returning
            nothing: a player would see a health bar belonging to something the
            client could not name.

        """
        declared = _declared("target")
        naming = declared.get(self.NAME_KEY)
        if not naming:
            return {}

        name = self.resolver.resolve(character, naming["value"])
        if name is None or name == "":
            return {}

        target = {"id": self.NAME_KEY, "name": name}
        if "kind" in naming:
            target["kind"] = naming["kind"]

        measures = []
        for key, entry in declared.items():
            if key == self.NAME_KEY:
                continue
            value = self.resolver.resolve_number(character, entry["value"])
            if value is None:
                continue
            measure = {"id": key, "label": entry.get("label", key), "value": value}
            for field in ("maximum", "minimum"):
                if field in entry:
                    bound = self.resolver.resolve_number(character, entry[field])
                    if bound is not None:
                        measure[field] = bound
            measures.append(measure)

        target["resources"] = measures
        return target


class BoundActionProvider(base.AetosActionProvider):
    """Context actions declared in `AETOS_BINDINGS["actions"]`."""

    name = "actions (bindings)"

    #: The only substitution a command template accepts.
    #:
    #: One placeholder, no operators, no attribute reads. A second one would be
    #: the first step towards a template language living in settings.py, and the
    #: D-track's whole argument is that the first step is the one to refuse.
    TARGET_PLACEHOLDER = "{target}"

    def get_actions(self, character, target=None):
        """
        Return the declared actions for a target.

        Args:
            character (Object): The acting character.
            target (Object, optional): The entity acted upon.

        Returns:
            list: Action dicts with `label` and `command`.

        Notes:
            Nothing is offered without a target. These are *context* actions --
            a menu opened on something -- and a declaration cannot know what a
            game's targetless commands are.

            **Offering an action does not make it legal.** The command travels
            the ordinary command path and the server decides, exactly as if the
            player had typed it.

        """
        if character is None or target is None:
            return []

        try:
            name = target.get_display_name(character)
        except Exception:
            # An object mid-deletion, or a typeclass whose display name raises.
            # One menu's worth of loss, not the session's.
            return []

        built = []
        for entry in _declared("actions").values():
            command = entry["command"]
            if self.TARGET_PLACEHOLDER in command:
                command = command.replace(self.TARGET_PLACEHOLDER, str(name))
            action = {"label": entry.get("label", command), "command": command}
            if "kind" in entry:
                action["kind"] = entry["kind"]
            built.append(action)

        return built


#: Slot name mapped to the provider that serves it from bindings.
#:
#: A table rather than a chain of `if slot ==`, so a new slot is one entry and
#: `settings_source.provider_for` can answer "not yet" for a slot by simply not
#: being in it. D1 had one row; D2 has five and changed nothing else.
PROVIDERS = {
    "resources": BoundResourceProvider,
    "equipment": BoundEquipmentProvider,
    "target": BoundTargetProvider,
    "effects": BoundEffectProvider,
    "actions": BoundActionProvider,
}
