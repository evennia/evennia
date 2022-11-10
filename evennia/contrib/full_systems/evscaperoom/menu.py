"""
Start menu

This is started from the `evscaperoom` command.

Here player user can set their own description as well as select to create a
new room (to start from scratch) or join an existing room (with other players).

"""
from evennia import EvMenu
from evennia.utils import create, justify, list_to_string, logger
from evennia.utils.evmenu import list_node

from .room import EvscapeRoom
from .utils import create_fantasy_word

# ------------------------------------------------------------
# Main menu
# ------------------------------------------------------------

_START_TEXT = """
|mEv|rScape|mRoom|n

|x- an escape-room experience using Evennia|n

You are |c{name}|n - {desc}|n.

Make a selection below.
"""

_CREATE_ROOM_TEXT = """
This will create a |ynew, empty room|n to challenge you.

Other players can be thrown in there at any time.

Remember that if you give up and are the last person to leave, that particular
room will be gone!

|yDo you want to create (and automatically join) a new room?|n")
"""

_JOIN_EXISTING_ROOM_TEXT = """
This will have you join an existing room ({roomname}).

This is {percent}% complete and has {nplayers} player(s) in it already:

 {players}

|yDo you want to join this room?|n
"""


def _move_to_room(caller, raw_string, **kwargs):
    """
    Helper to move a user to a room

    """
    room = kwargs["room"]
    room.msg_char(caller, f"Entering room |c'{room.name}'|n ...")
    room.msg_room(caller, f"~You |c~were just tricked in here too!|n")
    # we do a manual move since we don't want all hooks to fire.
    old_location = caller.location
    caller.location = room
    room.at_object_receive(caller, old_location)
    return "node_quit", {"quiet": True}


def _create_new_room(caller, raw_string, **kwargs):

    # create a random name, retrying until we find
    # a unique one
    key = create_fantasy_word(length=5, capitalize=True)
    while EvscapeRoom.objects.filter(db_key=key):
        key = create_fantasy_word(length=5, capitalize=True)
    room = create.create_object(EvscapeRoom, key=key)
    # we must do this once manually for the new room
    room.statehandler.init_state()
    _move_to_room(caller, "", room=room)

    nrooms = EvscapeRoom.objects.all().count()
    logger.log_info(
        f"Evscaperoom: {caller.key} created room '{key}' (#{room.id}). Now {nrooms} room(s) active."
    )

    room.log(f"JOIN: {caller.key} created and joined room")
    return "node_quit", {"quiet": True}


def _get_all_rooms(caller):
    """
    Get a list of all available rooms and store the mapping
    between option and room so we get to it later.

    """
    room_option_descs = []
    room_map = {}
    for room in EvscapeRoom.objects.all():
        if not room.pk or room.db.deleting:
            continue
        stats = room.db.stats or {"progress": 0}
        progress = int(stats["progress"])
        nplayers = len(room.get_all_characters())
        desc = (
            f"Join room |c'{room.get_display_name(caller)}'|n "
            f"(complete: {progress}%, players: {nplayers})"
        )
        room_map[desc] = room
        room_option_descs.append(desc)
    caller.ndb._menutree.room_map = room_map
    return room_option_descs


def _select_room(caller, menuchoice, **kwargs):
    """
    Get a room from the selection using the mapping we created earlier.
    """
    room = caller.ndb._menutree.room_map[menuchoice]
    return "node_join_room", {"room": room}


@list_node(_get_all_rooms, _select_room)
def node_start(caller, raw_string, **kwargs):
    text = _START_TEXT.strip()
    text = text.format(name=caller.key, desc=caller.db.desc)

    # build a list of available rooms
    options = (
        {
            "key": (
                "|y[s]et your description|n",
                "set your description",
                "set",
                "desc",
                "description",
                "s",
            ),
            "goto": "node_set_desc",
        },
        {
            "key": ("|y[c]reate/join a new room|n", "create a new room", "create", "c"),
            "goto": "node_create_room",
        },
        {"key": ("|r[q]uit the challenge", "quit", "q"), "goto": "node_quit"},
    )

    return text, options


def node_set_desc(caller, raw_string, **kwargs):

    current_desc = kwargs.get("desc", caller.db.desc)

    text = (
        "Your current description is\n\n " f'   "{current_desc}"' "\n\nEnter your new description!"
    )

    def _temp_description(caller, raw_string, **kwargs):
        desc = raw_string.strip()
        if 5 < len(desc) < 40:
            return None, {"desc": raw_string.strip()}
        else:
            caller.msg("|rYour description must be 5-40 characters long.|n")
            return None

    def _set_description(caller, raw_string, **kwargs):
        caller.db.desc = kwargs.get("desc")
        caller.msg("You set your description!")
        return "node_start"

    options = (
        {"key": "_default", "goto": _temp_description},
        {"key": ("|g[a]ccept", "a"), "goto": (_set_description, {"desc": current_desc})},
        {"key": ("|r[c]ancel", "c"), "goto": "node_start"},
    )
    return text, options


def node_create_room(caller, raw_string, **kwargs):

    text = _CREATE_ROOM_TEXT

    options = (
        {"key": ("|g[c]reate new room and start game|n", "c"), "goto": _create_new_room},
        {"key": ("|r[a]bort and go back|n", "a"), "goto": "node_start"},
    )

    return text, options


def node_join_room(caller, raw_string, **kwargs):

    room = kwargs["room"]
    stats = room.db.stats or {"progress": 0}

    players = [char.key for char in room.get_all_characters()]
    text = _JOIN_EXISTING_ROOM_TEXT.format(
        roomname=room.get_display_name(caller),
        percent=int(stats["progress"]),
        nplayers=len(players),
        players=list_to_string(players),
    )

    options = (
        {"key": ("|g[a]ccept|n (default)", "a"), "goto": (_move_to_room, kwargs)},
        {"key": ("|r[c]ancel|n", "c"), "goto": "node_start"},
        {"key": "_default", "goto": (_move_to_room, kwargs)},
    )

    return text, options


def node_quit(caller, raw_string, **kwargs):
    quiet = kwargs.get("quiet")
    text = ""
    if not quiet:
        text = "Goodbye for now!\n"
        # we check an Attribute on the caller to see if we should
        # leave the game entirely when leaving
        if caller.db.evscaperoom_standalone:
            from evennia import default_cmds
            from evennia.commands import cmdhandler

            cmdhandler.cmdhandler(
                caller.ndb._menutree._session, "", cmdobj=default_cmds.CmdQuit(), cmdobj_key="@quit"
            )

    return text, None  # empty options exit the menu


class EvscaperoomMenu(EvMenu):
    """
    Custom menu with a different formatting of options.

    """

    node_border_char = "~"

    def nodetext_formatter(self, text):
        return justify(text.strip("\n").rstrip(), align="c", indent=1)

    def options_formatter(self, optionlist):
        main_options = []
        room_choices = []
        for key, desc in optionlist:
            if key.isdigit():
                room_choices.append((key, desc))
            else:
                main_options.append(key)
        main_options = " | ".join(main_options)
        room_choices = super().options_formatter(room_choices)
        return "{}{}{}".format(main_options, "\n\n" if room_choices else "", room_choices)


# access function
def run_evscaperoom_menu(caller):
    """
    Run room selection menu

    """
    menutree = {
        "node_start": node_start,
        "node_quit": node_quit,
        "node_set_desc": node_set_desc,
        "node_create_room": node_create_room,
        "node_join_room": node_join_room,
    }

    EvscaperoomMenu(caller, menutree, startnode="node_start", cmd_on_exit=None, auto_quit=True)


# ------------------------------------------------------------
# In-game Options menu
# ------------------------------------------------------------


def _set_thing_style(caller, raw_string, **kwargs):
    room = caller.location
    options = caller.attributes.get("options", category=room.tagcategory, default={})
    options["things_style"] = kwargs.get("value", 2)
    caller.attributes.add("options", options, category=room.tagcategory)
    return None, kwargs  # rerun node


def _toggle_screen_reader(caller, raw_string, **kwargs):

    session = kwargs["session"]
    # flip old setting
    session.protocol_flags["SCREENREADER"] = not session.protocol_flags.get("SCREENREADER", False)
    # sync setting with portal
    session.sessionhandler.session_portal_sync(session)
    return None, kwargs  # rerun node


def node_options(caller, raw_string, **kwargs):
    text = "|cOption menu|n\n('|wq|nuit' to return)"
    room = caller.location

    options = caller.attributes.get("options", category=room.tagcategory, default={})
    things_style = options.get("things_style", 2)

    session = kwargs["session"]  # we give this as startnode_input when starting menu
    screenreader = session.protocol_flags.get("SCREENREADER", False)

    options = (
        {
            "desc": "{}No item markings (hard mode)".format(
                "|g(*)|n " if things_style == 0 else "( ) "
            ),
            "goto": (_set_thing_style, {"value": 0, "session": session}),
        },
        {
            "desc": "{}Items marked as |yitem|n (with color)".format(
                "|g(*)|n " if things_style == 1 else "( ) "
            ),
            "goto": (_set_thing_style, {"value": 1, "session": session}),
        },
        {
            "desc": "{}Items are marked as |y[item]|n (screenreader friendly)".format(
                "|g(*)|n " if things_style == 2 else "( ) "
            ),
            "goto": (_set_thing_style, {"value": 2, "session": session}),
        },
        {
            "desc": "{}Screenreader mode".format("(*) " if screenreader else "( ) "),
            "goto": (_toggle_screen_reader, kwargs),
        },
    )
    return text, options


class OptionsMenu(EvMenu):
    """
    Custom display of Option menu
    """

    def node_formatter(self, nodetext, optionstext):
        return f"{nodetext}\n\n{optionstext}"


# access function
def run_option_menu(caller, session):
    """
    Run option menu in-game
    """
    menutree = {"node_start": node_options}

    OptionsMenu(
        caller,
        menutree,
        startnode="node_start",
        cmd_on_exit="look",
        auto_quit=True,
        startnode_input=("", {"session": session}),
    )
