"""
Commands for the Evscaperoom. This contains all in-room commands as well as
admin debug-commands to help development.

Gameplay commands

- `look` - custom look
- `focus` - focus on object (to perform actions on it)
- `<action> <obj>` - arbitrary interaction with focused object
- `stand` - stand on the floor, resetting any position
- `emote` - free-form emote
- `say/whisper/shout` - simple communication

Other commands

- `evscaperoom` - starts the evscaperoom top-level menu
- `help` - custom in-room help command
- `options` - set game/accessibility options
- `who` - show who's in the room with you
- `quit` - leave a room, return to menu

Admin/development commands

- `jumpstate` - jump to specific room state
- `flag` - assign a flag to an object
- `createobj` - create a room-object set up for Evscaperoom

"""

import re

from django.conf import settings

from evennia import (
    SESSION_HANDLER,
    CmdSet,
    Command,
    InterruptCommand,
    default_cmds,
    syscmdkeys,
)
from evennia.utils import variable_from_module

from .utils import create_evscaperoom_object

_AT_SEARCH_RESULT = variable_from_module(*settings.SEARCH_AT_RESULT.rsplit(".", 1))

_RE_ARGSPLIT = re.compile(r"\s(with|on|to|in|at)\s", re.I + re.U)
_RE_EMOTE_SPEECH = re.compile(r"(\".*?\")|(\'.*?\')")
_RE_EMOTE_NAME = re.compile(r"(/\w+)")
_RE_EMOTE_PROPER_END = re.compile(r"\.$|\.[\'\"]$|\![\'\"]$|\?[\'\"]$")


# configurable help

if hasattr(settings, "EVSCAPEROOM_HELP_SUMMARY_TEXT"):
    _HELP_SUMMARY_TEXT = settings.EVSCAPEROOM_HELP_SUMMARY_TEXT
else:
    _HELP_SUMMARY_TEXT = """
   |yWhat to do ...|n
    - Your goal is to |wescape|n the room. To do that you need to |wlook|n at
      your surroundings for clues on how to escape. When you find something
      interesting, |wexamine|n it for any actions you could take with it.
   |yHow to explore ...|n
    - |whelp [obj or command]|n           - get usage help (never puzzle-related)
    - |woptions|n                         - set game/accessibility options
    - |wlook/l [obj]|n                    - give things a cursory look.
    - |wexamine/ex/e [obj]|n              - look closer at an object. Use again to
                                        look away.
    - |wstand|n                           - stand up if you were sitting, lying etc.
   |yHow to express yourself ...|n
    - |wwho [all]|n                       - show who's in the room or on server.
    - |wemote/pose/: <something>|n        - free-form emote. Use /me to refer
                                        to yourself and /name to refer to other
                                        things/players. Use quotes "..." to speak.
    - |wsay/; <something>|n               - quick-speak your mind
    - |wwhisper <something>|n             - whisper your mind
    - |wshout <something>|n               - shout your mind
   |yHow to quit like a little baby ...|n
    - |wquit / give up|n                  - admit defeat and give up
"""

_HELP_FALLBACK_TEXT = """
There is no help to be had about |y{this}|n. To look away, use |wexamine|n on
its own or with another object you are interested in.
"""

_QUIT_WARNING = """
|rDo you really want to quit?|n

{warning}

Enter |w'quit'|n again to truly give up.
"""

_QUIT_WARNING_CAN_COME_BACK = """
(Since you are not the last person to leave this room, you |gcan|n get back in here
by joining room '|c{roomname}|n' from the menu. Note however that if you leave
now, any personal achievements you may have gathered so far will be |rlost|n!)
"""

_QUIT_WARNING_LAST_CHAR = """
(You are the |rlast|n player to leave this room ('|c{roomname}|n'). This means that when you
leave, this room will go away and you |rwon't|n be able to come back to it!)
"""


class CmdEvscapeRoom(Command):
    """
    Base command parent for all Evscaperoom commands.

    This operates on the premise of 'focus' - the 'focus'
    is set on the caller, then subsequent commands will
    operate on that focus. If no focus is set,
    the operation will be general or on the room.

    Syntax:

       command [<obj1>|<arg1>] [<prep> <obj2>|<arg2>]

    """

    # always separate the command from any args with a space
    arg_regex = r"(/\w+?(\s|$))|\s|$"
    help_category = "Evscaperoom"

    # these flags allow child classes to determine how strict parsing for obj1/obj2 should be
    # (if they are given at all):
    # True - obj1/obj2 must be found as Objects, otherwise it's an error aborting command
    # False - obj1/obj2 will remain None, instead self.arg1, arg2 will be stored as strings
    # None - if obj1/obj2 are found as Objects, set them, otherwise set arg1/arg2 as strings
    obj1_search = None
    obj2_search = None

    def _search(self, query, required):
        """
        This implements the various search modes

        Args:
            query (str): The search query
            required (bool or None): This defines if query *must* be
                found to match a single local Object or not. If None,
                a non-match means returning the query unchanged. When
                False, immediately return the query. If required is False,
                don't search at all.
        Return:
            match (Object or str): The match or the search string depending
                on the `required` mode.
        Raises:
            InterruptCommand: Aborts the command quietly.
        Notes:
            The _AT_SEARCH_RESULT function will handle all error messaging
            for us.

        """
        if required is False:
            return None, query

        matches = self.caller.search(query, quiet=True)

        if not matches or len(matches) > 1:
            if required:
                if not query:
                    self.caller.msg("You must give an argument.")
                else:
                    _AT_SEARCH_RESULT(matches, self.caller, query=query)
                raise InterruptCommand
            else:
                return None, query
        else:
            return matches[0], None

    def parse(self):
        """
        Parse incoming arguments for use in all child classes.

        """
        caller = self.caller
        self.args = self.args.strip()

        # splits to either ['obj'] or e.g. ['obj', 'on', 'obj']
        parts = [part.strip() for part in _RE_ARGSPLIT.split(" " + self.args, 1)]
        nparts = len(parts)
        self.obj1 = None
        self.arg1 = None
        self.prep = None
        self.obj2 = None
        self.arg2 = None
        if nparts == 1:
            self.obj1, self.arg1 = self._search(parts[0], self.obj1_search)
        elif nparts == 3:
            obj1, self.prep, obj2 = parts
            self.obj1, self.arg1 = self._search(obj1, self.obj1_search)
            self.obj2, self.arg2 = self._search(obj2, self.obj2_search)

        self.room = caller.location
        self.roomstate = self.room.db.state

    @property
    def focus(self):
        return self.caller.attributes.get("focus", category=self.room.db.tagcategory)

    @focus.setter
    def focus(self, obj):
        self.caller.attributes.add("focus", obj, category=self.room.tagcategory)

    @focus.deleter
    def focus(self):
        self.caller.attributes.remove("focus", category=self.room.tagcategory)


class CmdGiveUp(CmdEvscapeRoom):
    """
    Give up

    Usage:
      give up

    Abandons your attempts at escaping and of ever winning the pie-eating contest.

    """

    key = "give up"
    aliases = ("abort", "chicken out", "quit", "q")

    def func(self):
        from .menu import run_evscaperoom_menu

        nchars = len(self.room.get_all_characters())
        if nchars == 1:
            warning = _QUIT_WARNING_LAST_CHAR.format(roomname=self.room.name)
            warning = _QUIT_WARNING.format(warning=warning)
        else:
            warning = _QUIT_WARNING_CAN_COME_BACK.format(roomname=self.room.name)
            warning = _QUIT_WARNING.format(warning=warning)

        ret = yield (warning)
        if ret.upper() == "QUIT":
            self.msg("|R ... Oh. Okay then. Off you go.|n\n")
            yield (1)

            self.room.log(f"QUIT: {self.caller.key} used the quit command")

            # manually call move hooks
            self.room.msg_room(self.caller, f"|r{self.caller.key} gave up and was whisked away!|n")
            self.room.at_object_leave(self.caller, self.caller.home)
            self.caller.move_to(
                self.caller.home, quiet=True, move_hooks=False, move_type="teleport"
            )

            # back to menu
            run_evscaperoom_menu(self.caller)
        else:
            self.msg("|gYou're staying? That's the spirit!|n")


class CmdLook(CmdEvscapeRoom):
    """
    Look at the room, an object or the currently focused object

    Usage:
      look [obj]

    """

    key = "look"
    aliases = ["l", "ls"]
    obj1_search = None
    obj2_search = None

    def func(self):
        caller = self.caller
        target = self.obj1 or self.obj2 or self.focus or self.room
        # the at_look hook will in turn call return_appearance and
        # pass the 'unfocused' kwarg to it
        txt = caller.at_look(target, unfocused=(target and target != self.focus))
        self.room.msg_char(caller, txt, client_type="look")


class CmdWho(CmdEvscapeRoom, default_cmds.CmdWho):
    """
    List other players in the game.

    Usage:
      who
      who all

    Show who is in the room with you, or (with who all), who is online on the
    server as a whole.

    """

    key = "who"

    obj1_search = False
    obj2_search = False

    def func(self):

        caller = self.caller

        if self.args == "all":
            table = self.style_table("|wName", "|wRoom")
            sessions = SESSION_HANDLER.get_sessions()
            for session in sessions:
                puppet = session.get_puppet()
                if puppet:
                    location = puppet.location
                    locname = location.key if location else "(Outside somewhere)"
                    table.add_row(puppet, locname)
                else:
                    account = session.get_account()
                    table.add_row(account.get_display_name(caller), "(OOC)")

            txt = (
                f"|cPlayers active on this server|n:\n{table}\n"
                "(use 'who' to see only those in your room)"
            )

        else:
            chars = [
                f"{obj.get_display_name(caller)} - {obj.db.desc.strip()}"
                for obj in self.room.get_all_characters()
                if obj != caller
            ]
            chars = "\n".join([f"{caller.key} - {caller.db.desc.strip()} (you)"] + chars)
            txt = f"|cPlayers in this room (room-name '{self.room.name}')|n:\n  {chars}"
        caller.msg(txt)


class CmdSpeak(Command):
    """
    Perform an communication action.

    Usage:
      say <text>
      whisper
      shout

    """

    key = "say"
    aliases = [";", "shout", "whisper"]
    arg_regex = r"\w|\s|$"

    def func(self):

        args = self.args.strip()
        caller = self.caller
        action = self.cmdname
        action = "say" if action == ";" else action
        room = self.caller.location

        if not self.args:
            caller.msg(f"What do you want to {action}?")
            return
        if action == "shout":
            args = f"|c{args.upper()}|n"
        elif action == "whisper":
            args = f"|C({args})|n"
        else:
            args = f"|c{args}|n"

        message = f"~You ~{action}: {args}"

        if hasattr(room, "msg_room"):
            room.msg_room(caller, message)
            room.log(f"{action} by {caller.key}: {args}")


class CmdEmote(Command):
    """
    Perform a free-form emote. Use /me to
    include yourself in the emote and /name
    to include other objects or characters.
    Use "..." to enact speech.

    Usage:
        emote <emote>
        :<emote

    Example:
        emote /me smiles at /peter
        emote /me points to /box and /lever.

    """

    key = "emote"
    aliases = [":", "pose"]
    arg_regex = r"\w|\s|$"

    def you_replace(match):
        return match

    def room_replace(match):
        return match

    def func(self):
        emote = self.args.strip()

        if not emote:
            self.caller.msg('Usage: emote /me points to /door, saying "look over there!"')
            return

        speech_clr = "|c"
        obj_clr = "|y"
        self_clr = "|g"
        player_clr = "|b"
        add_period = not _RE_EMOTE_PROPER_END.search(emote)

        emote = _RE_EMOTE_SPEECH.sub(speech_clr + r"\1\2|n", emote)
        room = self.caller.location

        characters = room.get_all_characters()
        logged = False
        for target in characters:
            txt = []
            self_refer = False
            for part in _RE_EMOTE_NAME.split(emote):
                nameobj = None
                if part.startswith("/"):
                    name = part[1:]
                    if name == "me":
                        nameobj = self.caller
                        self_refer = True
                    else:
                        match = self.caller.search(name, quiet=True)
                        if len(match) == 1:
                            nameobj = match[0]
                if nameobj:
                    if target == nameobj:
                        part = f"{self_clr}{nameobj.get_display_name(target)}|n"
                    elif nameobj in characters:
                        part = f"{player_clr}{nameobj.get_display_name(target)}|n"
                    else:
                        part = f"{obj_clr}{nameobj.get_display_name(target)}|n"
                txt.append(part)
            if not self_refer:
                if target == self.caller:
                    txt = [f"{self_clr}{self.caller.get_display_name(target)}|n "] + txt
                else:
                    txt = [f"{player_clr}{self.caller.get_display_name(target)}|n "] + txt
            txt = "".join(txt).strip() + ("." if add_period else "")
            if not logged and hasattr(self.caller.location, "log"):
                self.caller.location.log(f"emote: {txt}")
                logged = True
            target.msg(txt)


class CmdFocus(CmdEvscapeRoom):
    """
    Focus your attention on a target.

    Usage:
      focus <obj>

    Once focusing on an object, use look to get more information about how it
    looks and what actions is available.

    """

    key = "focus"
    aliases = ["examine", "e", "ex", "unfocus"]

    obj1_search = None

    def func(self):
        if self.obj1:
            old_focus = self.focus
            if hasattr(old_focus, "at_unfocus"):
                old_focus.at_unfocus(self.caller)

            if not hasattr(self.obj1, "at_focus"):
                self.caller.msg("Nothing of interest there.")
                return

            if self.focus != self.obj1:
                self.room.msg_room(
                    self.caller, f"~You ~examine *{self.obj1.key}.", skip_caller=True
                )
            self.focus = self.obj1
            self.obj1.at_focus(self.caller)
        elif not self.focus:
            self.caller.msg("What do you want to focus on?")
        else:
            old_focus = self.focus
            del self.focus
            self.caller.msg(f"You no longer focus on |y{old_focus.key}|n.")


class CmdOptions(CmdEvscapeRoom):
    """
    Start option menu

    Usage:
      options

    """

    key = "options"
    aliases = ["option"]

    def func(self):
        from .menu import run_option_menu

        run_option_menu(self.caller, self.session)


class CmdGet(CmdEvscapeRoom):
    """
    Use focus / examine instead.

    """

    key = "get"
    aliases = ["inventory", "i", "inv", "give"]

    def func(self):
        self.caller.msg("Use |wfocus|n or |wexamine|n for handling objects.")


class CmdRerouter(default_cmds.MuxCommand):
    """
    Interact with an object in focus.

    Usage:
       <action> [arg]

    """

    # reroute commands from the default cmdset to the catch-all
    # focus function where needed. This allows us to override
    # individual default commands without replacing the entire
    # cmdset (we want to keep most of them).

    key = "open"
    aliases = ["@dig", "@open"]

    def func(self):
        # reroute to another command
        from evennia.commands import cmdhandler

        cmdhandler.cmdhandler(
            self.session, self.raw_string, cmdobj=CmdFocusInteraction(), cmdobj_key=self.cmdname
        )


class CmdFocusInteraction(CmdEvscapeRoom):
    """
    Interact with an object in focus.

    Usage:
       <action> [arg]

    This is a special catch-all command which will operate on
    the current focus. It will look for a method
        `focused_object.at_focus_<action>(caller, **kwargs)` and call
    it. This allows objects to just add a new hook to make that
    action apply to it. The obj1, prep, obj2, arg1, arg2 are passed
    as keys into the method.

    """

    # all commands not matching something else goes here.
    key = syscmdkeys.CMD_NOMATCH

    obj1_search = None
    obj2_search = None

    def parse(self):
        """
        We assume this type of command is always on the form `command [arg]`

        """
        self.args = self.args.strip()
        parts = self.args.split(None, 1)
        if not self.args:
            self.action, self.args = "", ""
        elif len(parts) == 1:
            self.action = parts[0]
            self.args = ""
        else:
            self.action, self.args = parts
        self.room = self.caller.location

    def func(self):

        focused = self.focus
        action = self.action

        if focused and hasattr(focused, f"at_focus_{action}"):
            # there is a suitable hook to call!
            getattr(focused, f"at_focus_{action}")(self.caller, args=self.args)
        else:
            self.caller.msg("Hm?")


class CmdStand(CmdEvscapeRoom):
    """
    Stand up from whatever position you had.

    """

    key = "stand"

    def func(self):

        # Positionable objects will set this flag on you.
        pos = self.caller.attributes.get("position", category=self.room.tagcategory)

        if pos:
            # we have a position, clean up.
            obj, position = pos
            self.caller.attributes.remove("position", category=self.room.tagcategory)
            del obj.db.positions[self.caller]
            self.room.msg_room(self.caller, "~You ~are back standing on the floor again.")
        else:
            self.caller.msg("You are already standing.")


class CmdHelp(CmdEvscapeRoom, default_cmds.CmdHelp):
    """
    Get help.

    Usage:
      help <topic> or <command>

    """

    key = "help"
    aliases = ["?"]

    def func(self):
        if self.obj1:
            if hasattr(self.obj1, "get_help"):
                helptxt = self.obj1.get_help(self.caller)
                if not helptxt:
                    helptxt = f"There is no help to be had about {self.obj1.get_display_name(self.caller)}."
            else:
                helptxt = (
                    f"|y{self.obj1.get_display_name(self.caller)}|n is "
                    "likely |rnot|n part of any of the Jester's trickery."
                )
        elif self.arg1:
            # fall back to the normal help command
            super().func()
            return
        else:
            helptxt = _HELP_SUMMARY_TEXT
        self.caller.msg(helptxt.rstrip())


# Debug/help command


class CmdCreateObj(CmdEvscapeRoom):
    """
    Create command, only for Admins during debugging.

    Usage:
      createobj name[:typeclass]

    Here, :typeclass is a class in evscaperoom.commands

    """

    key = "createobj"
    aliases = ["cobj"]
    locks = "cmd:perm(Admin)"

    obj1_search = False
    obj2_search = False

    def func(self):
        caller = self.caller
        args = self.args

        if not args:
            caller.msg("Usage: createobj name[:typeclass]")
            return

        typeclass = "EvscaperoomObject"
        if ":" in args:
            name, typeclass = (part.strip() for part in args.rsplit(":", 1))

        if typeclass.startswith("state_"):
            # a state class
            typeclass = "evscaperoom.states." + typeclass
        else:
            name = args.strip()

        obj = create_evscaperoom_object(typeclass=typeclass, key=name, location=self.room)
        caller.msg(f"Created new object {name} ({obj.typeclass_path}).")


class CmdSetFlag(CmdEvscapeRoom):
    """
    Assign a flag to an object. Admin use only

    Usage:
      flag <obj> with <flagname>

    """

    key = "flag"
    aliases = ["setflag"]
    locks = "cmd:perm(Admin)"

    obj1_search = True
    obj2_search = False

    def func(self):

        if not self.arg2:
            self.caller.msg("Usage: flag <obj> with <flagname>")
            return

        if hasattr(self.obj1, "set_flag"):
            if self.obj1.check_flag(self.arg2):
                self.obj1.unset_flag(self.arg2)
                self.caller.msg(f"|rUnset|n flag '{self.arg2}' on {self.obj1}.")
            else:
                self.obj1.set_flag(self.arg2)
                self.caller.msg(f"|gSet|n flag '{self.arg2}' on {self.obj1}.")
        else:
            self.caller.msg(f"Cannot set flag on {self.obj1}.")


class CmdJumpState(CmdEvscapeRoom):
    """
    Jump to a given state.

    Args:
      jumpstate <statename>

    """

    key = "jumpstate"
    locks = "cmd:perm(Admin)"

    obj1_search = False
    obj2_search = False

    def func(self):
        self.caller.msg(f"Trying to move to state {self.args}")
        self.room.next_state(self.args)


# Helper command to start the Evscaperoom menu


class CmdEvscapeRoomStart(Command):
    """
    Go to the Evscaperoom start menu

    """

    key = "evscaperoom"
    help_category = "EvscapeRoom"

    def func(self):
        # need to import here to break circular import
        from .menu import run_evscaperoom_menu

        run_evscaperoom_menu(self.caller)


# command sets


class CmdSetEvScapeRoom(CmdSet):
    priority = 1

    def at_cmdset_creation(self):
        self.add(CmdHelp())
        self.add(CmdLook())
        self.add(CmdGiveUp())
        self.add(CmdFocus())
        self.add(CmdSpeak())
        self.add(CmdEmote())
        self.add(CmdFocusInteraction())
        self.add(CmdStand())
        self.add(CmdWho())
        self.add(CmdOptions())
        # rerouters
        self.add(CmdGet())
        self.add(CmdRerouter())
        # admin commands
        self.add(CmdCreateObj())
        self.add(CmdSetFlag())
        self.add(CmdJumpState())
