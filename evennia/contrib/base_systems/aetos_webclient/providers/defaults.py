"""
Default Aetos providers.

These use nothing but ordinary Evennia concepts -- locations, contents, exits and
destinations -- so they work on a pristine game with zero custom code. They
deliberately provide only what every Evennia game has:

* entities: what is in the room
* inventory: what the character is carrying
* map: the local room/exit graph

There is no default resource or action provider that invents data. A game with no
resource system exposes no resources, and Aetos simply shows no resource widgets.
Inventing a "health" default would be exactly the genre assumption this project
forbids.

Visibility is enforced through Evennia's own `filter_visible`, which honours the
`view` and `search` locks. Aetos must never surface an object a character cannot
see; a client that leaks hidden objects is an information-disclosure bug, not a
cosmetic one.

"""

from django.conf import settings

from evennia.contrib.base_systems.aetos_webclient.providers.base import (
    AetosActionProvider,
    AetosEntityProvider,
    AetosInventoryProvider,
    AetosMapProvider,
)

#: Entity kinds the default provider distinguishes. These are structural, not
#: genre concepts: anything with a destination is an exit, anything that can be
#: puppeted is a character, everything else is an object.
KIND_EXIT = "exit"
KIND_CHARACTER = "character"
KIND_OBJECT = "object"

#: How far the default mapper walks from the current room.
DEFAULT_MAP_DEPTH = 2

#: Hard ceiling on rooms in one map payload, so a densely connected world cannot
#: produce an unbounded message.
MAX_MAP_ROOMS = 250

#: Hard ceiling on carried items in one payload. A builder can hand a character a
#: bag of ten thousand coins; the client should not have to render them.
MAX_INVENTORY_ITEMS = 200


def _visible_contents(location, looker):
    """
    Return the contents of a location that the looker may see.

    Args:
        location (Object): The location to inspect.
        looker (Object): The observing character.

    Returns:
        list: Visible objects, excluding the looker.

    """
    if not location:
        return []
    contents = location.contents
    filter_visible = getattr(location, "filter_visible", None)
    if callable(filter_visible):
        return filter_visible(contents, looker)
    # Extremely old or heavily customised typeclasses may lack the helper. Fall
    # back to the same lock checks rather than returning everything.
    return [
        obj
        for obj in contents
        if obj != looker
        and obj.access(looker, "view")
        and obj.access(looker, "search", default=True)
    ]


def _classify(obj):
    """
    Classify an object structurally.

    The character test uses the game's *own* `BASE_CHARACTER_TYPECLASS` setting
    rather than any hardcoded class, so a game with a custom character typeclass
    is classified correctly and Aetos assumes nothing about the game's design.

    Args:
        obj (Object): The object to classify.

    Returns:
        str: One of the KIND_* constants.

    """
    if getattr(obj, "destination", None):
        return KIND_EXIT

    # `has_account` is Evennia's own test for a currently puppeted object.
    if getattr(obj, "has_account", False):
        return KIND_CHARACTER

    # An unpuppeted character typeclass still models a person (an NPC), which is
    # structurally distinct from an item even though nothing is driving it.
    #
    # Do NOT test for puppet-related hooks here: `at_pre_puppet` is defined on
    # DefaultObject, so every object in the game has it, and using it classified
    # ordinary items as characters.
    is_typeclass = getattr(obj, "is_typeclass", None)
    if callable(is_typeclass):
        try:
            if is_typeclass(settings.BASE_CHARACTER_TYPECLASS, exact=False):
                return KIND_CHARACTER
        except Exception:
            # A game may configure an unimportable typeclass path. That is its
            # problem to fix, not a reason to break the entity list.
            pass

    return KIND_OBJECT


class DefaultEntityProvider(AetosEntityProvider):
    """Describes room contents using only stock Evennia visibility rules."""

    def get_room_entities(self, character):
        """
        Return the entities visible to a character in their location.

        Args:
            character (Object): The observing character.

        Returns:
            list: Entity dicts with `id`, `name`, `kind`, and `direction` for
                exits.

        """
        location = getattr(character, "location", None)
        entities = []
        for obj in _visible_contents(location, character):
            kind = _classify(obj)
            entity = {
                "id": str(obj.id),
                "name": obj.get_display_name(character),
                "kind": kind,
            }
            if kind == KIND_EXIT:
                entity["direction"] = obj.key
                entity["destination"] = str(obj.destination.id) if obj.destination else None
            entities.append(entity)
        return entities


class DefaultMapProvider(AetosMapProvider):
    """
    Builds a local room graph by walking visible exits.

    This is mapping level 0-1 from the blueprint: no coordinates, no zone
    metadata, no game cooperation required. It walks outward from the character's
    room through exits the character can actually see, which means hidden exits
    stay hidden.

    """

    #: How many rooms out to walk.
    depth = DEFAULT_MAP_DEPTH

    def get_map(self, character):
        """
        Return the local room graph around a character.

        Args:
            character (Object): The character to map around.

        Returns:
            dict: `rooms`, `exits`, and `current` (the current room id, or None).

        """
        origin = getattr(character, "location", None)
        if not origin:
            return {"rooms": [], "exits": [], "current": None}

        rooms = {}
        links = []
        seen_links = set()

        # Breadth-first so that a shallow depth yields the nearest rooms rather
        # than one long corridor.
        frontier = [(origin, 0)]
        visited = {origin.id}

        while frontier and len(rooms) < MAX_MAP_ROOMS:
            room, distance = frontier.pop(0)
            rooms[room.id] = {
                "id": str(room.id),
                "name": room.get_display_name(character),
                "distance": distance,
            }
            if distance >= self.depth:
                continue

            for exit_obj in self._visible_exits(room, character):
                destination = exit_obj.destination
                if not destination:
                    continue
                link_key = (room.id, destination.id, exit_obj.key)
                if link_key in seen_links:
                    continue
                seen_links.add(link_key)
                links.append(
                    {
                        "from": str(room.id),
                        "to": str(destination.id),
                        "direction": exit_obj.key,
                    }
                )
                if destination.id not in visited:
                    visited.add(destination.id)
                    frontier.append((destination, distance + 1))

        # A link may point at a room the walk never expanded (depth limit or room
        # cap). Drop those so the client never references a room it was not sent.
        known = set(rooms)
        links = [link for link in links if int(link["to"]) in known]

        return {
            "rooms": list(rooms.values()),
            "exits": links,
            "current": str(origin.id),
        }

    def _visible_exits(self, room, character):
        """
        Return exits from a room that the character may see.

        Args:
            room (Object): The room to inspect.
            character (Object): The observing character.

        Returns:
            list: Visible exit objects.

        """
        return [
            obj for obj in _visible_contents(room, character) if getattr(obj, "destination", None)
        ]


class DefaultActionProvider(AetosActionProvider):
    """
    Offers the few actions every stock Evennia game already has.

    Blueprint section 11 promises "basic context actions" with zero custom game
    code, which means the defaults must be commands that genuinely exist in a
    fresh install rather than genre guesses.

    Only Evennia's own default-cmdset commands are used: `look`, and `get`/`drop`
    for ordinary objects. Nothing here assumes combat, magic, trade or any other
    system.

    Offering an action does not make it legal. The command travels the ordinary
    command path and the server decides, exactly as if the player had typed it --
    so a game that has removed `get`, or locked a particular object, behaves
    correctly without Aetos knowing anything about it.

    A game wanting richer menus supplies its own action provider; this one is
    replaced wholesale rather than extended, so it can never fight the game.

    """

    def get_actions(self, character, target=None):
        """
        Return actions for a target.

        Args:
            character (Object): The acting character.
            target (Object, optional): The entity acted upon.

        Returns:
            list: Action dicts with `label` and `command`.

        """
        if target is None or character is None:
            return []

        name = target.get_display_name(character)
        kind = _classify(target)

        if kind == KIND_EXIT:
            # An exit's useful action is to use it, which is its own name.
            return [
                {"label": "Go %s" % target.key, "command": target.key},
                {"label": "Look", "command": "look %s" % target.key},
            ]

        actions = [{"label": "Look", "command": "look %s" % name}]

        if kind == KIND_OBJECT:
            # `get` and `drop` are default-cmdset commands. Which one is useful
            # depends on where the object is, so only the applicable one is
            # offered rather than both.
            if target.location == character:
                actions.append({"label": "Drop", "command": "drop %s" % name})
            else:
                actions.append({"label": "Get", "command": "get %s" % name})

        return actions


class DefaultInventoryProvider(AetosInventoryProvider):
    """
    Lists what a character carries, using stock Evennia contents.

    This is the one slot of M16's four that can have a real default. Every
    Evennia object has `contents`, and `inventory` is a default-cmdset command --
    so a pristine game gets a working inventory widget with no code at all.

    Equipment, target and effects get no default, because Evennia models none of
    them and inventing slots or a target would be exactly the genre assumption
    this project forbids.

    Visibility still applies. A carried object a character cannot see -- a game
    may hide a cursed item until it is identified -- stays hidden here too.
    Aetos must never be the thing that reveals it.

    """

    def get_inventory(self, character):
        """
        Return the character's carried items.

        Args:
            character (Object): The character to describe.

        Returns:
            list: Item dicts with `id`, `name` and `kind`.

        """
        if not character:
            return []

        items = []
        for obj in _visible_contents(character, character)[:MAX_INVENTORY_ITEMS]:
            # An exit inside a character is a builder error rather than a real
            # concept, but classifying structurally costs nothing and means the
            # client never has to guess.
            items.append(
                {
                    "id": str(obj.id),
                    "name": obj.get_display_name(character),
                    "kind": _classify(obj),
                }
            )
        return items
