"""
General Character commands usually available to all characters
"""

import re

from django.conf import settings

from evennia.objects.objects import DefaultObject
from evennia.typeclasses.attributes import NickTemplateInvalid
from evennia.utils import utils

COMMAND_DEFAULT_CLASS = utils.class_from_module(settings.COMMAND_DEFAULT_CLASS)

# limit symbol import for API
__all__ = (
    "CmdHome",
    "CmdLook",
    "CmdNick",
    "CmdInventory",
    "CmdSetDesc",
    "CmdGet",
    "CmdDrop",
    "CmdGive",
    "CmdSay",
    "CmdWhisper",
    "CmdPose",
    "CmdAccess",
)


class CmdHome(COMMAND_DEFAULT_CLASS):
    """
    move to your character's home location

    Usage:
      home

    Teleports you to your home location.
    """

    key = "home"
    locks = "cmd:perm(home) or perm(Builder)"
    arg_regex = r"$"

    def func(self):
        """Implement the command"""
        caller = self.caller
        home = caller.home
        if not home:
            caller.msg("You have no home!")
        elif home == caller.location:
            caller.msg("You are already home!")
        else:
            caller.msg("There's no place like home ...")
            caller.move_to(home, move_type="teleport")


class CmdLook(COMMAND_DEFAULT_CLASS):
    """
    look at location or object

    Usage:
      look
      look <obj>
      look *<account>

    Observes your location or objects in your vicinity.
    """

    key = "look"
    aliases = ["l", "ls"]
    locks = "cmd:all()"
    arg_regex = r"\s|$"

    def func(self):
        """
        Handle the looking.
        """
        caller = self.caller
        if not self.args:
            target = caller.location
            if not target:
                caller.msg("You have no location to look at!")
                return
        else:
            target = caller.search(self.args)
            if not target:
                return
        desc = caller.at_look(target)
        # add the type=look to the outputfunc to make it
        # easy to separate this output in client.
        self.msg(text=(desc, {"type": "look"}), options=None)


class CmdNick(COMMAND_DEFAULT_CLASS):
    """
    define a personal alias/nick by defining a string to
    match and replace it with another on the fly

    Usage:
      nick[/switches] <string> [= [replacement_string]]
      nick[/switches] <template> = <replacement_template>
      nick/delete <string> or number
      nicks

    Switches:
      inputline - replace on the inputline (default)
      object    - replace on object-lookup
      account   - replace on account-lookup
      list      - show all defined aliases (also "nicks" works)
      delete    - remove nick by index in /list
      clearall  - clear all nicks

    Examples:
      nick hi = say Hello, I'm Sarah!
      nick/object tom = the tall man
      nick build $1 $2 = create/drop $1;$2
      nick tell $1 $2=page $1=$2
      nick tm?$1=page tallman=$1
      nick tm\\\\=$1=page tallman=$1

    A 'nick' is a personal string replacement. Use $1, $2, ... to catch arguments.
    Put the last $-marker without an ending space to catch all remaining text. You
    can also use unix-glob matching for the left-hand side <string>:

        * - matches everything
        ? - matches 0 or 1 single characters
        [abcd] - matches these chars in any order
        [!abcd] - matches everything not among these chars
        \\\\= - escape literal '=' you want in your <string>

    Note that no objects are actually renamed or changed by this command - your nicks
    are only available to you. If you want to permanently add keywords to an object
    for everyone to use, you need build privileges and the alias command.

    """

    key = "nick"
    switch_options = ("inputline", "object", "account", "list", "delete", "clearall")
    aliases = ["nickname", "nicks"]
    locks = "cmd:all()"

    def parse(self):
        """
        Support escaping of = with \\=
        """
        super().parse()
        args = (self.lhs or "") + (" = %s" % self.rhs if self.rhs else "")
        parts = re.split(r"(?<!\\)=", args, 1)
        self.rhs = None
        if len(parts) < 2:
            self.lhs = parts[0].strip()
        else:
            self.lhs, self.rhs = [part.strip() for part in parts]
        self.lhs = self.lhs.replace("\\=", "=")

    def func(self):
        """Create the nickname"""

        def _cy(string):
            "add color to the special markers"
            return re.sub(r"(\$[0-9]+|\*|\?|\[.+?\])", r"|Y\1|n", string)

        caller = self.caller
        switches = self.switches
        nicktypes = [switch for switch in switches if switch in ("object", "account", "inputline")]
        specified_nicktype = bool(nicktypes)
        nicktypes = nicktypes if specified_nicktype else ["inputline"]

        nicklist = (
            utils.make_iter(caller.nicks.get(category="inputline", return_obj=True) or [])
            + utils.make_iter(caller.nicks.get(category="object", return_obj=True) or [])
            + utils.make_iter(caller.nicks.get(category="account", return_obj=True) or [])
        )

        if "list" in switches or self.cmdstring in ("nicks",):
            if not nicklist:
                string = "|wNo nicks defined.|n"
            else:
                table = self.styled_table("#", "Type", "Nick match", "Replacement")
                for inum, nickobj in enumerate(nicklist):
                    _, _, nickvalue, replacement = nickobj.value
                    table.add_row(
                        str(inum + 1), nickobj.db_category, _cy(nickvalue), _cy(replacement)
                    )
                string = "|wDefined Nicks:|n\n%s" % table
            caller.msg(string)
            return

        if "clearall" in switches:
            caller.nicks.clear()
            if caller.account:
                caller.account.nicks.clear()
            caller.msg("Cleared all nicks.")
            return

        if "delete" in switches or "del" in switches:
            if not self.args or not self.lhs:
                caller.msg("usage nick/delete <nick> or <#num> ('nicks' for list)")
                return
            # see if a number was given
            arg = self.args.lstrip("#")
            oldnicks = []
            if arg.isdigit():
                # we are given a index in nicklist
                delindex = int(arg)
                if 0 < delindex <= len(nicklist):
                    oldnicks.append(nicklist[delindex - 1])
                else:
                    caller.msg("Not a valid nick index. See 'nicks' for a list.")
                    return
            else:
                if not specified_nicktype:
                    nicktypes = ("object", "account", "inputline")
                for nicktype in nicktypes:
                    oldnicks.append(caller.nicks.get(arg, category=nicktype, return_obj=True))

            oldnicks = [oldnick for oldnick in oldnicks if oldnick]
            if oldnicks:
                for oldnick in oldnicks:
                    nicktype = oldnick.category
                    nicktypestr = "%s-nick" % nicktype.capitalize()
                    _, _, old_nickstring, old_replstring = oldnick.value
                    caller.nicks.remove(old_nickstring, category=nicktype)
                    caller.msg(
                        f"{nicktypestr} removed: '|w{old_nickstring}|n' -> |w{old_replstring}|n."
                    )
            else:
                caller.msg("No matching nicks to remove.")
            return

        if not self.rhs and self.lhs:
            # check what a nick is set to
            strings = []
            if not specified_nicktype:
                nicktypes = ("object", "account", "inputline")
            for nicktype in nicktypes:
                nicks = [
                    nick
                    for nick in utils.make_iter(
                        caller.nicks.get(category=nicktype, return_obj=True)
                    )
                    if nick
                ]
                for nick in nicks:
                    _, _, nick, repl = nick.value
                    if nick.startswith(self.lhs):
                        strings.append(f"{nicktype.capitalize()}-nick: '{nick}' -> '{repl}'")
            if strings:
                caller.msg("\n".join(strings))
            else:
                caller.msg(f"No nicks found matching '{self.lhs}'")
            return

        if not self.rhs and self.lhs:
            # check what a nick is set to
            strings = []
            if not specified_nicktype:
                nicktypes = ("object", "account", "inputline")
            for nicktype in nicktypes:
                if nicktype == "account":
                    obj = account
                else:
                    obj = caller
                nicks = utils.make_iter(obj.nicks.get(category=nicktype, return_obj=True))
                for nick in nicks:
                    _, _, nick, repl = nick.value
                    if nick.startswith(self.lhs):
                        strings.append(f"{nicktype.capitalize()}-nick: '{nick}' -> '{repl}'")
            if strings:
                caller.msg("\n".join(strings))
            else:
                caller.msg(f"No nicks found matching '{self.lhs}'")
            return

        if not self.rhs and self.lhs:
            # check what a nick is set to
            strings = []
            if not specified_nicktype:
                nicktypes = ("object", "account", "inputline")
            for nicktype in nicktypes:
                if nicktype == "account":
                    obj = account
                else:
                    obj = caller
                nicks = utils.make_iter(obj.nicks.get(category=nicktype, return_obj=True))
                for nick in nicks:
                    _, _, nick, repl = nick.value
                    if nick.startswith(self.lhs):
                        strings.append(f"{nicktype.capitalize()}-nick: '{nick}' -> '{repl}'")
            if strings:
                caller.msg("\n".join(strings))
            else:
                caller.msg(f"No nicks found matching '{self.lhs}'")
            return

        if not self.args or not self.lhs:
            caller.msg("Usage: nick[/switches] nickname = [realname]")
            return

        # setting new nicks

        nickstring = self.lhs
        replstring = self.rhs

        if replstring == nickstring:
            caller.msg("No point in setting nick same as the string to replace...")
            return

        # check so we have a suitable nick type
        errstring = ""
        string = ""
        for nicktype in nicktypes:
            nicktypestr = f"{nicktype.capitalize()}-nick"
            old_nickstring = None
            old_replstring = None

            oldnick = caller.nicks.get(key=nickstring, category=nicktype, return_obj=True)
            if oldnick:
                _, _, old_nickstring, old_replstring = oldnick.value
            if replstring:
                # creating new nick
                errstring = ""
                if oldnick:
                    if replstring == old_replstring:
                        string += f"\nIdentical {nicktypestr.lower()} already set."
                    else:
                        string += (
                            f"\n{nicktypestr} '|w{old_nickstring}|n' updated to map to"
                            f" '|w{replstring}|n'."
                        )
                else:
                    string += f"\n{nicktypestr} '|w{nickstring}|n' mapped to '|w{replstring}|n'."
                try:
                    caller.nicks.add(nickstring, replstring, category=nicktype)
                except NickTemplateInvalid:
                    caller.msg(
                        "You must use the same $-markers both in the nick and in the replacement."
                    )
                    return
            elif old_nickstring and old_replstring:
                # just looking at the nick
                string += f"\n{nicktypestr} '|w{old_nickstring}|n' maps to '|w{old_replstring}|n'."
                errstring = ""
        string = errstring if errstring else string
        caller.msg(_cy(string))


class CmdInventory(COMMAND_DEFAULT_CLASS):
    """
    view inventory

    Usage:
      inventory
      inv

    Shows your inventory.
    """

    key = "inventory"
    aliases = ["inv", "i"]
    locks = "cmd:all()"
    arg_regex = r"$"

    def func(self):
        """check inventory"""
        items = self.caller.contents
        if not items:
            string = "You are not carrying anything."
        else:
            from evennia.utils.ansi import raw as raw_ansi

            table = self.styled_table(border="header")
            for key, desc, _ in utils.group_objects_by_key_and_desc(items, caller=self.caller):
                table.add_row(
                    f"|C{key}|n",
                    "{}|n".format(utils.crop(raw_ansi(desc or ""), width=50) or ""),
                )
            string = f"|wYou are carrying:\n{table}"
        self.msg(text=(string, {"type": "inventory"}))


class NumberedTargetCommand(COMMAND_DEFAULT_CLASS):
    """
    A class that parses out an optional number component from the input string. This
    class is intended to be inherited from to provide additional functionality, rather
    than used on its own.
    """

    def parse(self):
        """
        Parser that extracts a `.number` property from the beginning of the input string.

        For example, if the input string is "3 apples", this parser will set `self.number = 3` and
        `self.args = "apples"`. If the input string is "apples", this parser will set
        `self.number = 0` and `self.args = "apples"`.

        """
        super().parse()
        self.number = 0
        if getattr(self, "lhs", None):
            # handle self.lhs but don't require it
            count, *args = self.lhs.split(maxsplit=1)
            # we only use the first word as a count if it's a number and
            # there is more text afterwards
            if args and count.isdecimal():
                self.number = int(count)
                self.lhs = args[0]
        if self.args:
            # check for numbering
            count, *args = self.args.split(maxsplit=1)
            # we only use the first word as a count if it's a number and
            # there is more text afterwards
            if args and count.isdecimal():
                self.args = args[0]
                # we only re-assign self.number if it wasn't already taken from self.lhs
                if not self.number:
                    self.number = int(count)


class CmdGet(NumberedTargetCommand):
    """
    pick up something

    Usage:
      get <obj>

    Picks up an object from your location and puts it in your inventory.
    """

    key = "get"
    aliases = "grab"
    locks = "cmd:all()"
    arg_regex = r"\s|$"

    def func(self):
        """implements the command."""

        caller = self.caller

        if not self.args:
            self.msg("Get what?")
            return
        objs = caller.search(self.args, location=caller.location, stacked=self.number)
        if not objs:
            return
        # the 'stacked' search sometimes returns a list, sometimes not, so we make it always a list
        # NOTE: this behavior may be a bug, see issue #3432
        objs = utils.make_iter(objs)

        if len(objs) == 1 and caller == objs[0]:
            self.msg("You can't get yourself.")
            return

        # if we aren't allowed to get any of the objects, cancel the get
        for obj in objs:
            # check the locks
            if not obj.access(caller, "get"):
                if obj.db.get_err_msg:
                    self.msg(obj.db.get_err_msg)
                else:
                    self.msg("You can't get that.")
                return
            # calling at_pre_get hook method
            if not obj.at_pre_get(caller):
                return

        moved = []
        # attempt to move all of the objects
        for obj in objs:
            if obj.move_to(caller, quiet=True, move_type="get"):
                moved.append(obj)
                # calling at_get hook method
                obj.at_get(caller)

        if not moved:
            # none of the objects were successfully moved
            self.msg("That can't be picked up.")
        else:
            obj_name = moved[0].get_numbered_name(len(moved), caller, return_string=True)
            caller.location.msg_contents(f"$You() $conj(pick) up {obj_name}.", from_obj=caller)


class CmdDrop(NumberedTargetCommand):
    """
    drop something

    Usage:
      drop <obj>

    Lets you drop an object from your inventory into the
    location you are currently in.
    """

    key = "drop"
    locks = "cmd:all()"
    arg_regex = r"\s|$"

    def func(self):
        """Implement command"""

        caller = self.caller
        if not self.args:
            caller.msg("Drop what?")
            return

        # Because the DROP command by definition looks for items
        # in inventory, call the search function using location = caller
        objs = caller.search(
            self.args,
            location=caller,
            nofound_string=f"You aren't carrying {self.args}.",
            multimatch_string=f"You carry more than one {self.args}:",
            stacked=self.number,
        )
        if not objs:
            return
        # the 'stacked' search sometimes returns a list, sometimes not, so we make it always a list
        # NOTE: this behavior may be a bug, see issue #3432
        objs = utils.make_iter(objs)

        # if any objects fail the drop permission check, cancel the drop
        for obj in objs:
            # Call the object's at_pre_drop() method.
            if not obj.at_pre_drop(caller):
                return

        # do the actual dropping
        moved = []
        for obj in objs:
            if obj.move_to(caller.location, quiet=True, move_type="drop"):
                moved.append(obj)
                # Call the object's at_drop() method.
                obj.at_drop(caller)

        if not moved:
            # none of the objects were successfully moved
            self.msg("That can't be dropped.")
        else:
            obj_name = moved[0].get_numbered_name(len(moved), caller, return_string=True)
            caller.location.msg_contents(f"$You() $conj(drop) {obj_name}.", from_obj=caller)


class CmdGive(NumberedTargetCommand):
    """
    give away something to someone

    Usage:
      give <inventory obj> <to||=> <target>

    Gives an item from your inventory to another person,
    placing it in their inventory.
    """

    key = "give"
    rhs_split = ("=", " to ")  # Prefer = delimiter, but allow " to " usage.
    locks = "cmd:all()"
    arg_regex = r"\s|$"

    def func(self):
        """Implement give"""

        caller = self.caller
        if not self.args or not self.rhs:
            caller.msg("Usage: give <inventory object> = <target>")
            return
        # find the thing(s) to give away
        to_give = caller.search(
            self.lhs,
            location=caller,
            nofound_string=f"You aren't carrying {self.lhs}.",
            multimatch_string=f"You carry more than one {self.lhs}:",
            stacked=self.number,
        )
        if not to_give:
            return
        # find the target to give to
        target = caller.search(self.rhs)
        if not target:
            return

        # the 'stacked' search sometimes returns a list, sometimes not, so we make it always a list
        # NOTE: this behavior may be a bug, see issue #3432
        to_give = utils.make_iter(to_give)

        singular, plural = to_give[0].get_numbered_name(len(to_give), caller)
        if target == caller:
            caller.msg(f"You keep {plural if len(to_give) > 1 else singular} to yourself.")
            return

        # if any of the objects aren't allowed to be given, cancel the give
        for obj in to_give:
            # calling at_pre_give hook method
            if not obj.at_pre_give(caller, target):
                return

        # do the actual moving
        moved = []
        for obj in to_give:
            if obj.move_to(target, quiet=True, move_type="give"):
                moved.append(obj)
                # Call the object's at_give() method.
                obj.at_give(caller, target)

        if not moved:
            caller.msg(f"You could not give that to {target.get_display_name(caller)}.")
        else:
            obj_name = to_give[0].get_numbered_name(len(moved), caller, return_string=True)
            caller.msg(f"You give {obj_name} to {target.get_display_name(caller)}.")
            target.msg(f"{caller.get_display_name(target)} gives you {obj_name}.")


class CmdSetDesc(COMMAND_DEFAULT_CLASS):
    """
    describe yourself

    Usage:
      setdesc <description>

    Add a description to yourself. This
    will be visible to people when they
    look at you.
    """

    key = "setdesc"
    locks = "cmd:all()"
    arg_regex = r"\s|$"

    def func(self):
        """add the description"""

        if not self.args:
            self.msg("You must add a description.")
            return

        self.caller.db.desc = self.args.strip()
        self.msg("You set your description.")


class CmdSay(COMMAND_DEFAULT_CLASS):
    """
    speak as your character

    Usage:
      say <message>

    Talk to those in your current location.
    """

    key = "say"
    aliases = ['"', "'"]
    locks = "cmd:all()"

    # don't require a space after `say/'/"`
    arg_regex = None

    def func(self):
        """Run the say command"""

        caller = self.caller

        if not self.args:
            caller.msg("Say what?")
            return

        speech = self.args

        # Calling the at_pre_say hook on the character
        speech = caller.at_pre_say(speech)

        # If speech is empty, stop here
        if not speech:
            return

        # Call the at_post_say hook on the character
        caller.at_say(speech, msg_self=True)


class CmdWhisper(COMMAND_DEFAULT_CLASS):
    """
    Speak privately as your character to another

    Usage:
      whisper <character> = <message>
      whisper <char1>, <char2> = <message>

    Talk privately to one or more characters in your current location, without
    others in the room being informed.
    """

    key = "whisper"
    locks = "cmd:all()"

    def func(self):
        """Run the whisper command"""

        caller = self.caller

        if not self.lhs or not self.rhs:
            caller.msg("Usage: whisper <character> = <message>")
            return

        receivers = [recv.strip() for recv in self.lhs.split(",")]

        receivers = [caller.search(receiver) for receiver in set(receivers)]
        receivers = [recv for recv in receivers if recv]

        speech = self.rhs
        # If the speech is empty, abort the command
        if not speech or not receivers:
            return

        # Call a hook to change the speech before whispering
        speech = caller.at_pre_say(speech, whisper=True, receivers=receivers)

        # no need for self-message if we are whispering to ourselves (for some reason)
        msg_self = None if caller in receivers else True
        caller.at_say(speech, msg_self=msg_self, receivers=receivers, whisper=True)


class CmdPose(COMMAND_DEFAULT_CLASS):
    """
    strike a pose

    Usage:
      pose <pose text>
      pose's <pose text>

    Example:
      pose is standing by the wall, smiling.
       -> others will see:
      Tom is standing by the wall, smiling.

    Describe an action being taken. The pose text will
    automatically begin with your name.
    """

    key = "pose"
    aliases = [":", "emote"]
    locks = "cmd:all()"
    arg_regex = ""

    # we want to be able to pose without whitespace between
    # the command/alias and the pose (e.g. :pose)
    arg_regex = None

    def parse(self):
        """
        Custom parse the cases where the emote
        starts with some special letter, such
        as 's, at which we don't want to separate
        the caller's name and the emote with a
        space.
        """
        args = self.args
        if args and not args[0] in ["'", ",", ":"]:
            args = " %s" % args.strip()
        self.args = args

    def func(self):
        """Hook function"""
        if not self.args:
            msg = "What do you want to do?"
            self.msg(msg)
        else:
            msg = f"{self.caller.name}{self.args}"
            self.caller.location.msg_contents(text=(msg, {"type": "pose"}), from_obj=self.caller)


class CmdAccess(COMMAND_DEFAULT_CLASS):
    """
    show your current game access

    Usage:
      access

    This command shows you the permission hierarchy and
    which permission groups you are a member of.
    """

    key = "access"
    aliases = ["groups", "hierarchy"]
    locks = "cmd:all()"
    arg_regex = r"$"

    def func(self):
        """Load the permission groups"""

        caller = self.caller
        hierarchy_full = settings.PERMISSION_HIERARCHY
        string = "\n|wPermission Hierarchy|n (climbing):\n %s" % ", ".join(hierarchy_full)

        if caller.account and caller.account.is_superuser:
            cperms = "<Superuser>"
            pperms = "<Superuser>"
        else:
            cperms = ", ".join(caller.permissions.all())
            if caller.account:
                pperms = ", ".join(caller.account.permissions.all())
            else:
                pperms = "<No account>"

        string += "\n|wYour access|n:"
        string += f"\nCharacter |c{caller.key}|n: {cperms}"
        if utils.inherits_from(caller, DefaultObject) and caller.account:
            string += f"\nAccount |c{caller.account.key}|n: {pperms}"
        caller.msg(string)
