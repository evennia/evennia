"""
Aetos state assembly.

Turns the active providers into the payloads the client renders. This is the only
place that knows how a full sync is composed, so a delta and a sync can never
disagree about the shape of a section.

**How state reaches the client.** Aetos must work on a game with zero custom code,
and a pristine Evennia game has no hooks calling into Aetos. So the default flow is
client-requested: the browser asks for a sync after connecting and after each
command it sends. That needs no cooperation from the game at all.

A game that wants true push can call `push_sync(session)` from its own typeclass
hooks (`at_post_move`, and so on). That is an opt-in improvement, never a
requirement -- requiring it would break the zero-configuration promise.

Nothing here executes a command or bypasses a lock. Every value is read through a
provider, and the default providers honour Evennia's own visibility rules.

"""

from evennia.contrib.base_systems.aetos_webclient import (
    character_state,
    map_layout,
    media,
    protocol,
    providers,
    resources,
    ui_manifest,
)
from evennia.contrib.base_systems.aetos_webclient.providers import base
from evennia.utils.ansi import parse_ansi
from evennia.utils.text2html import parse_html

#: Cap on the characters of a room description sent in one payload. A builder can
#: put an arbitrarily long description on a room; the client should not have to
#: cope with a megabyte of it.
MAX_DESCRIPTION_LENGTH = 8000

#: Bounds on a provider's action list, so a buggy provider cannot produce an
#: unbounded menu or a command longer than any game would accept.
MAX_ACTIONS_PER_ENTITY = 24
MAX_ACTION_LABEL_LENGTH = 80
MAX_ACTION_COMMAND_LENGTH = 400
MAX_ACTION_DESCRIPTION_LENGTH = 200


def _plain(text):
    """
    Strip Evennia colour markup, leaving plain text.

    Used for any value the client may put into a command. An exit button sends
    the exit's name, so that name must be exactly what a player would type --
    markup or HTML in it would produce a command the server cannot parse.

    Args:
        text (str): Text possibly containing Evennia markup.

    Returns:
        str: The text with markup removed.

    """
    if not text:
        return ""
    return parse_ansi(str(text), strip_ansi=True)


def _html(text):
    """
    Render Evennia colour markup as HTML.

    Only the `text` outputfunc is converted by the Portal, so anything Aetos
    sends in its own messages arrives as raw markup unless converted here. The
    output passes through the client's allowlist sanitiser before display.

    Args:
        text (str): Text possibly containing Evennia markup.

    Returns:
        str: HTML with Evennia's own colour classes.

    """
    if not text:
        return ""
    return parse_html(str(text))


def _decorate(entry):
    """
    Add a display form to a provider-supplied entry.

    Providers return names as ordinary game text, which may carry colour markup.
    Normalising here rather than in each provider means a game's custom provider
    gets correct rendering for free, and cannot accidentally emit markup into a
    command.

    Args:
        entry (dict): An entry with a `name` key.

    Returns:
        dict: The entry with `name` plain and `display` added as HTML.

    """
    if not isinstance(entry, dict) or "name" not in entry:
        return entry
    decorated = dict(entry)
    raw = entry.get("name") or ""
    decorated["name"] = _plain(raw)
    decorated["display"] = _html(raw)
    return decorated


def _attach_actions(entities, character, action_provider, container=None):
    """
    Attach each entity's contextual actions to the entity itself.

    Actions travel with the entity rather than in a parallel list, so a client
    can never render a menu against the wrong target -- a mismatch that would be
    invisible until a player attacked the wrong thing.

    The provider is asked once per entity and resolved against the live object,
    because an action list is only meaningful for a specific target.

    Args:
        entities (list): Entity dicts from a provider.
        character (Object): The observing character.
        action_provider (AetosActionProvider): The active provider.
        container (Object, optional): Where to resolve the ids. Defaults to the
            character's location; carried items resolve against the character.

    Returns:
        list: Entities with an `actions` list added.

    """
    if not character or not entities:
        return entities

    if container is None:
        container = getattr(character, "location", None)
    if not container:
        return entities

    # One lookup pass, so a room with many objects does not become N searches.
    by_id = {str(obj.id): obj for obj in container.contents}

    decorated = []
    for entity in entities:
        target = by_id.get(entity.get("id"))
        actions = []
        if target is not None:
            actions = base.safe_call(action_provider, "get_actions", [], character, target=target)
            actions = _normalize_actions(actions)
        decorated.append(dict(entity, actions=actions))
    return decorated


def _attach_carried_actions(items, character, action_provider):
    """
    Attach contextual actions to carried items.

    Separate from the room pass only because carried objects resolve against the
    character rather than the location -- the same provider answers, so an item
    in a pack offers the same actions it would on the ground, minus the ones the
    game decides do not apply there.

    Args:
        items (list): Normalised inventory items.
        character (Object): The carrying character.
        action_provider (AetosActionProvider): The active provider.

    Returns:
        list: Items with an `actions` list added.

    """
    return _attach_actions(items, character, action_provider, container=character)


def _normalize_actions(raw_actions):
    """
    Validate a provider's action list.

    An action is a label plus an ordinary command. Both must be plain strings:
    anything else is a provider bug, and a malformed action reaching the client
    would render a button that sends nonsense.

    Args:
        raw_actions: Whatever the provider returned.

    Returns:
        list: Validated actions, possibly empty.

    """
    if not isinstance(raw_actions, (list, tuple)):
        return []

    actions = []
    for entry in raw_actions[:MAX_ACTIONS_PER_ENTITY]:
        if not isinstance(entry, dict):
            continue
        label = entry.get("label")
        command = entry.get("command")
        if not isinstance(label, str) or not label:
            continue
        if not isinstance(command, str) or not command:
            continue
        action = {
            # The label is display text and may carry colour markup; the
            # command is sent verbatim and must not.
            "label": _plain(label)[:MAX_ACTION_LABEL_LENGTH],
            "display": _html(label),
            "command": command[:MAX_ACTION_COMMAND_LENGTH],
        }

        # An explanation, for where the label alone is ambiguous.  Addendum
        # A.78. "Trade" is clear enough in a menu titled "Captain Renn"; read
        # aloud out of context it is not, and a description gives a screen
        # reader something to say beyond the verb.
        description = entry.get("description")
        if isinstance(description, str) and description:
            action["description"] = _plain(description)[:MAX_ACTION_DESCRIPTION_LENGTH]

        # Whether the game currently considers the action possible. Advisory
        # only: this shapes presentation, and the server still rules on the
        # command exactly as it would if it had been typed.
        if entry.get("disabled") is True:
            action["disabled"] = True
        if isinstance(entry.get("reason"), str) and entry["reason"]:
            action["reason"] = _plain(entry["reason"])[:MAX_ACTION_DESCRIPTION_LENGTH]

        actions.append(action)
    return actions


def _describe_character(character):
    """
    Describe the character itself.

    Args:
        character (Object): The character, or None if unpuppeted.

    Returns:
        dict: Character data, empty if there is no character.

    """
    if not character:
        return {}
    raw_name = character.get_display_name(character)
    return {
        "id": str(character.id),
        "name": _plain(raw_name),
        "display": _html(raw_name),
    }


def _describe_room(character):
    """
    Describe the character's current location.

    Uses only stock Evennia concepts -- key and the `desc` attribute -- so it
    works on a pristine game.

    Args:
        character (Object): The observing character.

    Returns:
        dict: Room data, empty if the character has no location.

    """
    location = getattr(character, "location", None) if character else None
    if not location:
        return {}

    description = location.db.desc or ""
    if not isinstance(description, str):
        description = str(description)

    raw_name = location.get_display_name(character)
    return {
        "id": str(location.id),
        # Plain for anything command-shaped, HTML for display.
        "name": _plain(raw_name),
        "display": _html(raw_name),
        "description": _html(description[:MAX_DESCRIPTION_LENGTH]),
    }


def build_sync(character, active_providers=None):
    """
    Build a complete `aetos_sync` payload.

    Args:
        character (Object): The character to describe, or None if unpuppeted.
        active_providers (dict, optional): Pre-resolved providers. Resolved from
            settings if omitted.

    Returns:
        dict: A payload keyed by store section.

    """
    resolved = active_providers if active_providers is not None else providers.get_providers()
    if active_providers is not None:
        # A caller supplying providers may not know about a slot added since
        # they wrote the call -- a test fixture, or a game calling build_sync
        # from its own hook. Filling the gaps from the defaults means a new
        # slot degrades to "this game exposes none of that", which is what a
        # game that has said nothing about it means anyway. The alternative is
        # a KeyError that takes down the entire sync over one absent section.
        missing = {
            slot: default()
            for slot, default in providers.DEFAULT_PROVIDERS.items()
            if slot not in resolved
        }
        if missing:
            resolved = dict(resolved, **missing)

    entities = base.safe_call(resolved["entities"], "get_room_entities", [], character)
    entities = _attach_actions(entities, character, resolved["actions"])
    # Providers are game-supplied code, so their output is validated rather than
    # trusted. A malformed resource is dropped individually; one bad entry must
    # not cost the player every other one.
    raw_resources = base.safe_call(resolved["resources"], "get_resources", [], character)
    resource_list = resources.normalize_resources(raw_resources)
    # Declared order wins over arrival order (M23). A gauge that moves between
    # second and fourth place between syncs is not a cosmetic problem for
    # somebody navigating by position or by screen reader.
    try:
        resource_list = ui_manifest.order_resources(
            resource_list, ui_manifest.get_ui_description()["resources"]
        )
    except ui_manifest.AetosUIError:
        # A malformed AETOS_UI is reported loudly at handshake, where a
        # developer will see it. Here it must not cost the player their
        # resources as well.
        pass
    actions = base.safe_call(resolved["actions"], "get_actions", [], character)
    map_data = base.safe_call(
        resolved["map"], "get_map", {"rooms": [], "exits": [], "current": None}, character
    )

    # The four character-facing sections. Each is normalised rather than trusted,
    # for the same reason resources are: a provider is game code, and one bad
    # entry must cost that entry alone.
    inventory = character_state.normalize_inventory(
        base.safe_call(resolved["inventory"], "get_inventory", [], character)
    )
    inventory = _attach_carried_actions(inventory, character, resolved["actions"])
    equipment = character_state.normalize_equipment(
        base.safe_call(resolved["equipment"], "get_equipment", [], character)
    )
    effects = character_state.normalize_effects(
        base.safe_call(resolved["effects"], "get_effects", [], character)
    )
    target = character_state.normalize_target(
        base.safe_call(resolved["target"], "get_target", {}, character)
    )
    # Ambient media. State rather than events: the client compares this with
    # what is already playing and starts or stops only the difference, so a
    # sync arriving every few seconds does not restart the music.
    media_data = media.normalize_media(
        base.safe_call(resolved["media"], "get_media", [], character)
    )

    # Exits are entities too, but the client wants them as a first-class list for
    # the exit widget and the compass. Splitting here keeps that logic out of
    # every widget.
    entities = [_decorate(entity) for entity in entities]
    exits = [entity for entity in entities if entity.get("kind") == "exit"]
    occupants = [entity for entity in entities if entity.get("kind") != "exit"]

    # Map room names are game text too, and the map widget renders them.
    if isinstance(map_data, dict) and isinstance(map_data.get("rooms"), list):
        map_data = dict(map_data, rooms=[_decorate(room) for room in map_data["rooms"]])

        # Coordinates and the non-visual description are generated from the same
        # graph, so the picture and its spoken equivalent can never disagree
        # (blueprint sections 21 and 47). A provider supplying its own
        # positions keeps them.
        if "positions" not in map_data:
            layout = map_layout.assign_coordinates(
                map_data["rooms"], map_data.get("exits") or [], origin=map_data.get("current")
            )
            map_data = dict(map_data, **layout)
        map_data = dict(map_data, surroundings=map_layout.describe_surroundings(map_data))

    return {
        "character": _describe_character(character),
        "room": dict(_describe_room(character), exits=exits),
        "entities": {"items": occupants},
        "resources": {"items": resource_list},
        "actions": {"items": actions},
        "map": map_data,
        "inventory": {"items": inventory},
        "equipment": {"slots": equipment},
        "effects": {"items": effects},
        "target": target,
        "media": media_data,
        # No default source yet. Present and empty so the client can rely on
        # the shape at protocol v1.
        "mode": {},
    }


def push_sync(session, character=None):
    """
    Send a full authoritative sync to a session.

    Games may call this from their own hooks for real-time updates. It is safe to
    call at any time; a session with no puppet simply receives empty sections.

    Args:
        session (Session): The session to update.
        character (Object, optional): The character to describe. Defaults to the
            session's current puppet.

    """
    puppet = character if character is not None else getattr(session, "puppet", None)
    session.msg(**{protocol.MSG_SYNC: ((), build_sync(puppet))})


def push_media(
    session,
    url,
    category,
    caption=None,
    description=None,
    decorative=False,
    loop=False,
    volume=1.0,
    media_id=None,
):
    """
    Play or show one piece of media, once.

    For a door slamming or a spell landing -- something that happens rather than
    something that is true. Ambient media belongs in the media provider, where
    the client can tell "still playing" from "started again".

    The descriptor goes through the same validation as provider media, so a
    caption obligation cannot be dodged by using the convenience helper, and an
    unsafe URL is refused on both paths.

    Args:
        session (Session): The session to play it on.
        url (str): Where the media lives. `http`, `https` or relative.
        category (str): One of `media.MEDIA_CATEGORIES`.
        caption (str, optional): What a player who cannot hear it is told.
            Required unless `decorative` is True.
        description (str, optional): A longer description.
        decorative (bool): True when the media carries no information.
        loop (bool): Whether it repeats.
        volume (float): 0.0 to 1.0, scaled by the player's own volume.
        media_id (str, optional): A stable identifier.

    Returns:
        bool: True if it was sent, False if the descriptor was rejected.

    """
    item = media.normalize_media_item(
        {
            "id": media_id,
            "url": url,
            "category": category,
            "caption": caption,
            "description": description,
            "decorative": decorative,
            "loop": loop,
            "volume": volume,
        }
    )
    if item is None:
        return False
    session.msg(**{protocol.MSG_MEDIA: ((), {"play": [item]})})
    return True


#: Categories a game may declare on an event (Addendum A.11). Structural rather
#: than genre-specific: "combat" describes where a message came from in the
#: client's routing, not what kind of game this is.
EVENT_CATEGORIES = (
    "room",
    "movement",
    "tell",
    "chat",
    "combat",
    "system",
    "resource",
    "effect",
    "inventory",
    "target",
    "command",
    "media",
    "other",
)

#: Importance a game may advise. Advisory only -- the player's own announcement
#: preferences always decide what is actually spoken (A.76).
EVENT_IMPORTANCE = ("critical", "important", "normal", "background", "silent")

MAX_EVENT_TEXT_LENGTH = 4000


def push_event(session, text, category="other", importance=None, data=None):
    """
    Send one categorised event to a session.

    Optional. A game that never calls this still works: its output arrives as
    ordinary text in the "other" category, which supports search and review by
    time but not review by channel.

    The point of calling it is that Aetos will not guess. It cannot tell a tell
    from a shout by reading the words, and a client that tried would be wrong on
    every game that phrases things its own way.

    Args:
        session (Session): The session to notify.
        text (str): The message, as the player should read it.
        category (str): One of `EVENT_CATEGORIES`. Unknown values become
            "other" rather than being rejected -- a typo should cost the
            categorisation, not the message.
        importance (str, optional): One of `EVENT_IMPORTANCE`. Advisory: the
            player's own preferences still decide what is announced.
        data (dict, optional): Structured payload accompanying the text.

    """
    if category not in EVENT_CATEGORIES:
        category = "other"

    payload = {
        "category": category,
        "text": _html(str(text)[:MAX_EVENT_TEXT_LENGTH]),
        # The plain form travels too, because automation matches on what the
        # player reads rather than on the markup they never see.
        "plain": _plain(str(text)[:MAX_EVENT_TEXT_LENGTH]),
    }
    if importance in EVENT_IMPORTANCE:
        payload["importance_hint"] = importance
    if isinstance(data, dict):
        payload["data"] = data

    session.msg(**{protocol.MSG_EVENT: ((), payload)})
