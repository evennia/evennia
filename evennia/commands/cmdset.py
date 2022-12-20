"""

A Command Set (CmdSet) holds a set of commands. The Cmdsets can be
merged and combined to create new sets of commands in a
non-destructive way. This makes them very powerful for implementing
custom game states where different commands (or different variations
of commands) are available to the accounts depending on circumstance.

The available merge operations are partly borrowed from mathematical
Set theory.


* Union The two command sets are merged so that as many commands as
    possible of each cmdset ends up in the merged cmdset. Same-name
    commands are merged by priority.  This is the most common default.
    Ex: A1,A3 + B1,B2,B4,B5 = A1,B2,A3,B4,B5
* Intersect - Only commands found in *both* cmdsets (i.e. which have
    same names) end up in the merged cmdset, with the higher-priority
    cmdset replacing the lower one. Ex: A1,A3 + B1,B2,B4,B5 = A1
* Replace -   The commands of this cmdset completely replaces the
    lower-priority cmdset's commands, regardless of if same-name commands
    exist. Ex: A1,A3 + B1,B2,B4,B5 = A1,A3
* Remove -    This removes the relevant commands from the
    lower-priority cmdset completely.  They are not replaced with
    anything, so this in effects uses the high-priority cmdset as a filter
    to affect the low-priority cmdset.  Ex: A1,A3 + B1,B2,B4,B5 = B2,B4,B5

"""
from weakref import WeakKeyDictionary

from django.utils.translation import gettext as _

from evennia.utils.utils import inherits_from, is_iter

__all__ = ("CmdSet",)


class _CmdSetMeta(type):
    """
    This metaclass makes some minor on-the-fly convenience fixes to
    the cmdset class.

    """

    def __init__(cls, *args, **kwargs):
        """
        Fixes some things in the cmdclass

        """
        # by default we key the cmdset the same as the
        # name of its class.
        if not hasattr(cls, "key") or not cls.key:
            cls.key = cls.__name__
        cls.path = "%s.%s" % (cls.__module__, cls.__name__)

        if not isinstance(cls.key_mergetypes, dict):
            cls.key_mergetypes = {}

        super().__init__(*args, **kwargs)


class CmdSet(object, metaclass=_CmdSetMeta):
    """
    This class describes a unique cmdset that understands priorities.
    CmdSets can be merged and made to perform various set operations
    on each other.  CmdSets have priorities that affect which of their
    ingoing commands gets used.

    In the examples, cmdset A always have higher priority than cmdset B.

    key - the name of the cmdset. This can be used on its own for game
    operations

    mergetype (partly from Set theory):

        Union -    The two command sets are merged so that as many
                    commands as possible of each cmdset ends up in the
                    merged cmdset. Same-name commands are merged by
                    priority.  This is the most common default.
                    Ex: A1,A3 + B1,B2,B4,B5 = A1,B2,A3,B4,B5
        Intersect - Only commands found in *both* cmdsets
                    (i.e. which have same names) end up in the merged
                    cmdset, with the higher-priority cmdset replacing the
                    lower one.  Ex: A1,A3 + B1,B2,B4,B5 = A1
        Replace -   The commands of this cmdset completely replaces
                    the lower-priority cmdset's commands, regardless
                    of if same-name commands exist.
                    Ex: A1,A3 + B1,B2,B4,B5 = A1,A3
        Remove -    This removes the relevant commands from the
                    lower-priority cmdset completely.  They are not
                    replaced with anything, so this in effects uses the
                    high-priority cmdset as a filter to affect the
                    low-priority cmdset.
                    Ex: A1,A3 + B1,B2,B4,B5 = B2,B4,B5

                 Note: Commands longer than 2 characters and starting
                       with double underscrores, like '__noinput_command'
                       are considered 'system commands' and are
                       excempt from all merge operations - they are
                       ALWAYS included across mergers and only affected
                       if same-named system commands replace them.

    priority- All cmdsets are always merged in pairs of two so that
              the higher set's mergetype is applied to the
              lower-priority cmdset. Default commands have priority 0,
              high-priority ones like Exits and Channels have 10 and 9.
              Priorities can be negative as well to give default
              commands preference.

    duplicates - determines what happens when two sets of equal
                 priority merge (only). Defaults to None and has the first of them in the
                 merger (i.e. A above) automatically taking
                 precedence. But if `duplicates` is true, the
                 result will be a merger with more than one of each
                 name match.  This will usually lead to the account
                 receiving a multiple-match error higher up the road,
                 but can be good for things like cmdsets on non-account
                 objects in a room, to allow the system to warn that
                 more than one 'ball' in the room has the same 'kick'
                 command defined on it, so it may offer a chance to
                 select which ball to kick ...  Allowing duplicates
                 only makes sense for Union and Intersect, the setting
                 is ignored for the other mergetypes.
                 Note that the `duplicates` flag is *not* propagated in
                 a cmdset merger. So `A + B = C` will result in
                 a cmdset with duplicate commands, but C.duplicates will
                 be `None`. For duplication to apply to a whole cmdset
                 stack merge, _all_ cmdsets in the stack must have
                 `.duplicates=True` set.
                Finally, if a final cmdset has `.duplicates=None` (the normal
                unless created alone with another value), the cmdhandler
                will assume True for object-based cmdsets and False for
                all other. This is usually the most intuitive outcome.

    key_mergetype (dict) - allows the cmdset to define a unique
             mergetype for particular cmdsets.  Format is
             {CmdSetkeystring:mergetype}. Priorities still apply.
             Example: {'Myevilcmdset','Replace'} which would make
             sure for this set to always use 'Replace' on
             Myevilcmdset no matter what overall mergetype this set
             has.

    no_objs  - don't include any commands from nearby objects
                  when searching for suitable commands
    no_exits  - ignore the names of exits when matching against
                        commands
    no_channels   - ignore the name of channels when matching against
                        commands (WARNING- this is dangerous since the
                        account can then not even ask staff for help if
                        something goes wrong)


    """

    key = "Unnamed CmdSet"
    mergetype = "Union"
    priority = 0

    # These flags, if set to None should be interpreted as 'I don't care' and,
    # will allow "pass-through" even of lower-prio cmdsets' explicitly True/False
    # options. If this is set to True/False however, priority matters.
    no_exits = None
    no_objs = None
    no_channels = None
    # The .duplicates setting does not propagate and since duplicates can only happen
    # on same-prio cmdsets, there is no concept of passthrough on `None`.
    # The merger of two cmdsets always return in a cmdset with `duplicates=None`
    # (even if the result may have duplicated commands).
    # If a final cmdset has `duplicates=None` (normal, unless the cmdset is
    # created on its own with the flag set), the cmdhandler will auto-assume it to be
    # True for Object-based cmdsets and stay None/False for all other entities.
    #
    # Example:
    #  A and C has .duplicates=True, B has .duplicates=None (or False)
    #  B + A = BA, where BA will have duplicate cmds, but BA.duplicates = None
    #  BA + C = BAC, where BAC will have more duplication, but BAC.duplicates = None
    #
    # Basically, for the `.duplicate` setting to survive throughout a
    # merge-stack, every cmdset in the stack must have `duplicates` set explicitly.
    duplicates = None

    persistent = False
    key_mergetypes = {}
    errmessage = ""
    # pre-store properties to duplicate straight off
    to_duplicate = (
        "key",
        "cmdsetobj",
        "no_exits",
        "no_objs",
        "no_channels",
        "persistent",
        "mergetype",
        "priority",
        "duplicates",
        "errmessage",
    )

    def __init__(self, cmdsetobj=None, key=None):
        """
        Creates a new CmdSet instance.

        Args:
            cmdsetobj (Session, Account, Object, optional): This is the database object
                to which this particular instance of cmdset is related. It
                is often a character but may also be a regular object, Account
                or Session.
            key (str, optional): The idenfier for this cmdset. This
                helps if wanting to selectively remov cmdsets.

        """

        if key:
            self.key = key
        self.commands = []
        self.system_commands = []
        self.actual_mergetype = self.mergetype
        self.cmdsetobj = cmdsetobj
        # this is set only on merged sets, in cmdhandler.py, in order to
        # track, list and debug mergers correctly.
        self.merged_from = []

        # initialize system
        self.at_cmdset_creation()
        self._contains_cache = WeakKeyDictionary()  # {}

    # Priority-sensitive merge operations for cmdsets

    def _union(self, cmdset_a, cmdset_b):
        """
        Merge two sets using union merger

        Args:
            cmdset_a (Cmdset): Cmdset given higher priority in the case of a tie.
            cmdset_b (Cmdset): Cmdset given lower priority in the case of a tie.

        Returns:
            cmdset_c (Cmdset): The result of A U B operation.

        Notes:
            Union, C = A U B,  means that C gets all elements from both A and B.

        """
        cmdset_c = cmdset_a._duplicate()
        # we make copies, not refs by use of [:]
        cmdset_c.commands = cmdset_a.commands[:]
        if cmdset_a.duplicates and cmdset_a.priority == cmdset_b.priority:
            cmdset_c.commands.extend(cmdset_b.commands)
        else:
            cmdset_c.commands.extend([cmd for cmd in cmdset_b if cmd not in cmdset_a])
        return cmdset_c

    def _intersect(self, cmdset_a, cmdset_b):
        """
        Merge two sets using intersection merger

        Args:
            cmdset_a (Cmdset): Cmdset given higher priority in the case of a tie.
            cmdset_b (Cmdset): Cmdset given lower priority in the case of a tie.

        Returns:
            cmdset_c (Cmdset): The result of A (intersect) B operation.

        Notes:
            Intersection, C = A (intersect) B, means that C only gets the
                parts of A and B that are the same (that is, the commands
                of each set having the same name. Only the one of these
                having the higher prio ends up in C).

        """
        cmdset_c = cmdset_a._duplicate()
        if cmdset_a.duplicates and cmdset_a.priority == cmdset_b.priority:
            for cmd in [cmd for cmd in cmdset_a if cmd in cmdset_b]:
                cmdset_c.add(cmd)
                cmdset_c.add(cmdset_b.get(cmd))
        else:
            cmdset_c.commands = [cmd for cmd in cmdset_a if cmd in cmdset_b]
        return cmdset_c

    def _replace(self, cmdset_a, cmdset_b):
        """
        Replace the contents of one set with another

        Args:
            cmdset_a (Cmdset): Cmdset replacing
            cmdset_b (Cmdset): Cmdset to replace

        Returns:
            cmdset_c (Cmdset): This is indentical to cmdset_a.

        Notes:
            C = A, where B is ignored.

        """
        cmdset_c = cmdset_a._duplicate()
        cmdset_c.commands = cmdset_a.commands[:]
        return cmdset_c

    def _remove(self, cmdset_a, cmdset_b):
        """
        Filter a set by another.

        Args:
            cmdset_a (Cmdset): Cmdset acting as a removal filter.
            cmdset_b (Cmdset): Cmdset to filter

        Returns:
            cmdset_c (Cmdset): B, with all matching commands from A removed.

        Notes:
            C = B - A, where A is used to remove the commands of B.

        """

        cmdset_c = cmdset_a._duplicate()
        cmdset_c.commands = [cmd for cmd in cmdset_b if cmd not in cmdset_a]
        return cmdset_c

    def _instantiate(self, cmd):
        """
        checks so that object is an instantiated command and not, say
        a cmdclass. If it is, instantiate it.  Other types, like
        strings, are passed through.

        Args:
            cmd (any): Entity to analyze.

        Returns:
            result (any): An instantiated Command or the input unmodified.

        """
        if callable(cmd):
            return cmd()
        else:
            return cmd

    def _duplicate(self):
        """
        Returns a new cmdset with the same settings as this one (no
        actual commands are copied over)

        Returns:
            cmdset (Cmdset): A copy of the current cmdset.
        """
        cmdset = CmdSet()
        for key, val in ((key, getattr(self, key)) for key in self.to_duplicate):
            if val != getattr(cmdset, key):
                # only copy if different from default; avoid turning
                # class-vars into instance vars
                setattr(cmdset, key, val)
        cmdset.key_mergetypes = self.key_mergetypes.copy()
        return cmdset

    def __str__(self):
        """
        Show all commands in cmdset when printing it.

        Returns:
            commands (str): Representation of commands in Cmdset.

        """
        perm = "perm" if self.persistent else "non-perm"
        options = ", ".join(
            [
                "{}:{}".format(opt, "T" if getattr(self, opt) else "F")
                for opt in ("no_exits", "no_objs", "no_channels", "duplicates")
                if getattr(self, opt) is not None
            ]
        )
        options = (", " + options) if options else ""
        return (
            f"<CmdSet {self.key}, {self.mergetype}, {perm}, prio {self.priority}{options}>: "
            + ", ".join([str(cmd) for cmd in sorted(self.commands, key=lambda o: o.key)])
        )

    def __iter__(self):
        """
        Allows for things like 'for cmd in cmdset':

        Returns:
            iterable (iter): Commands in Cmdset.

        """
        return iter(self.commands)

    def __contains__(self, othercmd):
        """
        Returns True if this cmdset contains the given command (as
        defined by command name and aliases). This allows for things
        like 'if cmd in cmdset'

        """
        ret = self._contains_cache.get(othercmd)
        if ret is None:
            ret = othercmd in self.commands
            self._contains_cache[othercmd] = ret
        return ret

    def __add__(self, cmdset_a):
        """
        Merge this cmdset (B) with another cmdset (A) using the + operator,

        C = B + A

        Here, we (by convention) say that 'A is merged onto B to form
        C'.  The actual merge operation used in the 'addition' depends
        on which priorities A and B have. The one of the two with the
        highest priority will apply and give its properties to C. In
        the case of a tie, A  takes priority and replaces the
        same-named commands in B unless A has the 'duplicate' variable
        set (which means both sets' commands are kept).
        """

        # It's okay to merge with None
        if not cmdset_a:
            return self

        sys_commands_a = cmdset_a.get_system_cmds()
        sys_commands_b = self.get_system_cmds()

        if self.priority <= cmdset_a.priority:
            # A higher or equal priority to B

            # preserve system __commands
            sys_commands = sys_commands_a + [
                cmd for cmd in sys_commands_b if cmd not in sys_commands_a
            ]

            mergetype = cmdset_a.key_mergetypes.get(self.key, cmdset_a.mergetype)
            if mergetype == "Intersect":
                cmdset_c = self._intersect(cmdset_a, self)
            elif mergetype == "Replace":
                cmdset_c = self._replace(cmdset_a, self)
            elif mergetype == "Remove":
                cmdset_c = self._remove(cmdset_a, self)
            else:  # Union
                cmdset_c = self._union(cmdset_a, self)

            # pass through options whenever they are set, unless the merging or higher-prio
            # set changes the setting (i.e. has a non-None value). We don't pass through
            # the duplicates setting; that is per-merge; the resulting .duplicates value
            # is always None (so merging cmdsets must all have explicit values if wanting
            # to cause duplicates).
            cmdset_c.no_channels = (
                self.no_channels if cmdset_a.no_channels is None else cmdset_a.no_channels
            )
            cmdset_c.no_exits = self.no_exits if cmdset_a.no_exits is None else cmdset_a.no_exits
            cmdset_c.no_objs = self.no_objs if cmdset_a.no_objs is None else cmdset_a.no_objs
            cmdset_c.duplicates = None

        else:
            # B higher priority than A

            # preserver system __commands
            sys_commands = sys_commands_b + [
                cmd for cmd in sys_commands_a if cmd not in sys_commands_b
            ]

            mergetype = self.key_mergetypes.get(cmdset_a.key, self.mergetype)
            if mergetype == "Intersect":
                cmdset_c = self._intersect(self, cmdset_a)
            elif mergetype == "Replace":
                cmdset_c = self._replace(self, cmdset_a)
            elif mergetype == "Remove":
                cmdset_c = self._remove(self, cmdset_a)
            else:  # Union
                cmdset_c = self._union(self, cmdset_a)

            # pass through options whenever they are set, unless the higher-prio
            # set changes the setting (i.e. has a non-None value). We don't pass through
            # the duplicates setting; that is per-merge; the resulting .duplicates value#
            # is always None (so merging cmdsets must all have explicit values if wanting
            # to cause duplicates).
            cmdset_c.no_channels = (
                cmdset_a.no_channels if self.no_channels is None else self.no_channels
            )
            cmdset_c.no_exits = cmdset_a.no_exits if self.no_exits is None else self.no_exits
            cmdset_c.no_objs = cmdset_a.no_objs if self.no_objs is None else self.no_objs
            cmdset_c.duplicates = None

        # we store actual_mergetype since key_mergetypes
        # might be different from the main mergetype.
        # This is used for diagnosis.
        cmdset_c.actual_mergetype = mergetype

        # print "__add__ for %s (prio %i)  called with %s (prio %i)." % (self.key, self.priority,
        # cmdset_a.key, cmdset_a.priority)

        # return the system commands to the cmdset
        cmdset_c.add(sys_commands, allow_duplicates=True)
        return cmdset_c

    def add(self, cmd, allow_duplicates=False):
        """
        Add a new command or commands to this CmdSet, a list of
        commands or a cmdset to this cmdset. Note that this is *not*
        a merge operation (that is handled by the + operator).

        Args:
            cmd (Command, list, Cmdset): This allows for adding one or
                more commands to this Cmdset in one go. If another Cmdset
                is given, all its commands will be added.
            allow_duplicates (bool, optional): If set, will not try to remove
                duplicate cmds in the set. This is needed during the merge process
                to avoid wiping commands coming from cmdsets with duplicate=True.

        Notes:
            If cmd already exists in set, it will replace the old one
            (no priority checking etc happens here). This is very useful
            when overloading default commands).

            If cmd is another cmdset class or -instance, the commands of
            that command set is added to this one, as if they were part of
            the original cmdset definition. No merging or priority checks
            are made, rather later added commands will simply replace
            existing ones to make a unique set.

        """
        if inherits_from(cmd, "evennia.commands.cmdset.CmdSet"):
            # cmd is a command set so merge all commands in that set
            # to this one. We raise a visible error if we created
            # an infinite loop (adding cmdset to itself somehow)
            cmdset = cmd
            try:
                cmdset = self._instantiate(cmdset)
            except RuntimeError:
                err = (
                    "Adding cmdset {cmdset} to {cls} lead to an "
                    "infinite loop. When adding a cmdset to another, "
                    "make sure they are not themself cyclically added to "
                    "the new cmdset somewhere in the chain."
                )
                raise RuntimeError(_(err.format(cmdset=cmdset, cls=self.__class__)))
            cmds = cmdset.commands
        elif is_iter(cmd):
            cmds = [self._instantiate(c) for c in cmd]
        else:
            cmds = [self._instantiate(cmd)]

        commands = self.commands
        system_commands = self.system_commands

        for cmd in cmds:
            # add all commands
            if not hasattr(cmd, "obj") or cmd.obj is None:
                cmd.obj = self.cmdsetobj

            # remove duplicates and add new
            for _dum in range(commands.count(cmd)):
                commands.remove(cmd)
            commands.append(cmd)

            # add system_command to separate list as well,
            # for quick look-up. These have no
            if cmd.key.startswith("__"):
                # remove same-matches and add new
                for _dum in range(system_commands.count(cmd)):
                    system_commands.remove(cmd)
                system_commands.append(cmd)

        if not allow_duplicates:
            # extra run to make sure to avoid doublets
            commands = list(set(commands))
        self.commands = commands

    def remove(self, cmd):
        """
        Remove a command instance from the cmdset.

        Args:
            cmd (Command or str): Either the Command object to remove
                or the key of such a command.

        """
        if isinstance(cmd, str):
            _cmd = next((_cmd for _cmd in self.commands if _cmd.key == cmd), None)
            if _cmd is None:
                if not cmd.startswith("__"):
                    # if a syscommand, keep the original string and instantiate on it
                    return None
            else:
                cmd = _cmd

        cmd = self._instantiate(cmd)
        if cmd.key.startswith("__"):
            try:
                ic = self.system_commands.index(cmd)
                del self.system_commands[ic]
            except ValueError:
                # ignore error
                pass
        else:
            self.commands = [oldcmd for oldcmd in self.commands if oldcmd != cmd]

    def get(self, cmd):
        """
        Get a command from the cmdset. This is mostly useful to
        check if the command is part of this cmdset or not.

        Args:
            cmd (Command or str): Either the Command object or its key.

        Returns:
            cmd (Command): The first matching Command in the set.

        """
        if isinstance(cmd, str):
            _cmd = next((_cmd for _cmd in self.commands if _cmd.key == cmd), None)
            if _cmd is None:
                if not cmd.startswith("__"):
                    # if a syscommand, keep the original string and instantiate on it
                    return None
            else:
                cmd = _cmd

        cmd = self._instantiate(cmd)
        for thiscmd in self.commands:
            if thiscmd == cmd:
                return thiscmd
        return None

    def count(self):
        """
        Number of commands in set.

        Returns:
            N (int): Number of commands in this Cmdset.

        """
        return len(self.commands)

    def get_system_cmds(self):
        """
        Get system commands in cmdset

        Returns:
            sys_cmds (list): The system commands in the set.

        Notes:
            As far as the Cmdset is concerned, system commands are any
            commands with a key starting with double underscore __.
            These are excempt from merge operations.

        """
        return self.system_commands

    def make_unique(self, caller):
        """
        Remove duplicate command-keys (unsafe)

        Args:
            caller (object): Commands on this object will
                get preference in the duplicate removal.

        Notes:
            This is an unsafe command meant to clean out a cmdset of
            doublet commands after it has been created. It is useful
            for commands inheriting cmdsets from the cmdhandler where
            obj-based cmdsets always are added double. Doublets will
            be weeded out with preference to commands defined on
            caller, otherwise just by first-come-first-served.

        """
        unique = {}
        for cmd in self.commands:
            if cmd.key in unique:
                ocmd = unique[cmd.key]
                if (hasattr(cmd, "obj") and cmd.obj == caller) and not (
                    hasattr(ocmd, "obj") and ocmd.obj == caller
                ):
                    unique[cmd.key] = cmd
            else:
                unique[cmd.key] = cmd
        self.commands = list(unique.values())

    def get_all_cmd_keys_and_aliases(self, caller=None):
        """
        Collects keys/aliases from commands

        Args:
            caller (Object, optional): If set, this is used to check access permissions
                on each command. Only commands that pass are returned.

        Returns:
            names (list): A list of all command keys and aliases in this cmdset. If `caller`
                was given, this list will only contain commands to which `caller` passed
                the `call` locktype check.

        """
        names = []
        if caller:
            [names.extend(cmd._keyaliases) for cmd in self.commands if cmd.access(caller)]
        else:
            [names.extend(cmd._keyaliases) for cmd in self.commands]
        return names

    def at_cmdset_creation(self):
        """
        Hook method - this should be overloaded in the inheriting
        class, and should take care of populating the cmdset by use of
        self.add().

        """
        pass
