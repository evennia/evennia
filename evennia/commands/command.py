"""
The base Command class.

All commands in Evennia inherit from the 'Command' class in this module.

"""
from builtins import range

import re
from evennia.locks.lockhandler import LockHandler
from evennia.utils.utils import is_iter, fill, lazy_property
from future.utils import with_metaclass


def _init_command(mcs, **kwargs):
    """
    Helper command.
    Makes sure all data are stored as lowercase and
    do checking on all properties that should be in list form.
    Sets up locks to be more forgiving. This is used both by the metaclass
    and (optionally) at instantiation time.

    If kwargs are given, these are set as instance-specific properties
    on the command.
    """
    for i in range(len(kwargs)):
        # used for dynamic creation of commands
        key, value = kwargs.popitem()
        setattr(mcs, key, value)

    mcs.key = mcs.key.lower()
    if mcs.aliases and not is_iter(mcs.aliases):
        try:
            mcs.aliases = [str(alias).strip().lower()
                          for alias in mcs.aliases.split(',')]
        except Exception:
            mcs.aliases = []
    mcs.aliases = list(set(alias for alias in mcs.aliases
                           if alias and alias != mcs.key))

    # optimization - a set is much faster to match against than a list
    mcs._matchset = set([mcs.key] + mcs.aliases)
    # optimization for looping over keys+aliases
    mcs._keyaliases = tuple(mcs._matchset)

    # by default we don't save the command between runs
    if not hasattr(mcs, "save_for_next"):
        mcs.save_for_next = False

    # pre-process locks as defined in class definition
    temp = []
    if hasattr(mcs, 'permissions'):
        mcs.locks = mcs.permissions
    if not hasattr(mcs, 'locks'):
        # default if one forgets to define completely
        mcs.locks = "cmd:all()"
    if not "cmd:" in mcs.locks:
        mcs.locks = "cmd:all();" + mcs.locks
    for lockstring in mcs.locks.split(';'):
        if lockstring and not ':' in lockstring:
            lockstring = "cmd:%s" % lockstring
        temp.append(lockstring)
    mcs.lock_storage = ";".join(temp)

    if hasattr(mcs, 'arg_regex') and isinstance(mcs.arg_regex, basestring):
        mcs.arg_regex = re.compile(r"%s" % mcs.arg_regex, re.I + re.UNICODE)
    if not hasattr(mcs, "auto_help"):
        mcs.auto_help = True
    if not hasattr(mcs, 'is_exit'):
        mcs.is_exit = False
    if not hasattr(mcs, "help_category"):
        mcs.help_category = "general"
    mcs.help_category = mcs.help_category.lower()


class CommandMeta(type):
    """
    The metaclass cleans up all properties on the class
    """
    def __init__(mcs, *args, **kwargs):
        _init_command(mcs, **kwargs)
        super(CommandMeta, mcs).__init__(*args, **kwargs)

#    The Command class is the basic unit of an Evennia command; when
#    defining new commands, the admin subclass this class and
#    define their own parser method to handle the input. The
#    advantage of this is inheritage; commands that have similar
#    structure can parse the input string the same way, minimizing
#    parsing errors.


class Command(with_metaclass(CommandMeta, object)):
    """
    Base command

    Usage:
      command [args]

    This is the base command class. Inherit from this
    to create new commands.

    The cmdhandler makes the following variables available to the
    command methods (so you can always assume them to be there):
    self.caller - the game object calling the command
    self.cmdstring - the command name used to trigger this command (allows
                     you to know which alias was used, for example)
    cmd.args - everything supplied to the command following the cmdstring
               (this is usually what is parsed in self.parse())
    cmd.cmdset - the cmdset from which this command was matched (useful only
                seldomly, notably for help-type commands, to create dynamic
                help entries and lists)
    cmd.obj - the object on which this command is defined. If a default command,
                 this is usually the same as caller.
    cmd.rawstring - the full raw string input, including any args and no parsing.

    The following class properties can/should be defined on your child class:

    key - identifier for command (e.g. "look")
    aliases - (optional) list of aliases (e.g. ["l", "loo"])
    locks - lock string (default is "cmd:all()")
    help_category - how to organize this help entry in help system
                    (default is "General")
    auto_help - defaults to True. Allows for turning off auto-help generation
    arg_regex - (optional) raw string regex defining how the argument part of
                the command should look in order to match for this command
                (e.g. must it be a space between cmdname and arg?)

    (Note that if auto_help is on, this initial string is also used by the
    system to create the help entry for the command, so it's a good idea to
    format it similar to this one)
    """

    # the main way to call this command (e.g. 'look')
    key = "command"
    # alternative ways to call the command (e.g. 'l', 'glance', 'examine')
    aliases = []
    # a list of lock definitions on the form
    #   cmd:[NOT] func(args) [ AND|OR][ NOT] func2(args)
    locks = ""
    # used by the help system to group commands in lists.
    help_category = "general"
    # This allows to turn off auto-help entry creation for individual commands.
    auto_help = True
    # optimization for quickly separating exit-commands from normal commands
    is_exit = False
    # define the command not only by key but by the regex form of its arguments
    arg_regex = None

    # auto-set (by Evennia on command instantiation) are:
    #   obj - which object this command is defined on
    #   session - which session is responsible for triggering this command. Only set
    #             if triggered by a player.

    def __init__(self, **kwargs):
        """
        The lockhandler works the same as for objects.
        optional kwargs will be set as properties on the Command at runtime,
        overloading evential same-named class properties.

        """
        if kwargs:
            _init_command(self, **kwargs)

    @lazy_property
    def lockhandler(self):
        return LockHandler(self)

    def __str__(self):
        """
        Print the command key
        """
        return self.key

    def __eq__(self, cmd):
        """
        Compare two command instances to each other by matching their
        key and aliases.

        Args:
            cmd (Command or str): Allows for equating both Command
                objects and their keys.

        Returns:
            equal (bool): If the commands are equal or not.

        """
        try:
            # first assume input is a command (the most common case)
            return self._matchset.intersection(cmd._matchset)
            #return cmd.key in self._matchset
        except AttributeError:
            # probably got a string
            return cmd in self._matchset

    def __ne__(self, cmd):
        """
        The logical negation of __eq__. Since this is one of the most
        called methods in Evennia (along with __eq__) we do some
        code-duplication here rather than issuing a method-lookup to
        __eq__.
        """
        try:
            return self._matchset.isdisjoint(cmd._matchset)
            #return not cmd.key in self._matcheset
        except AttributeError:
            return not cmd in self._matchset

    def __contains__(self, query):
        """
        This implements searches like 'if query in cmd'. It's a fuzzy
        matching used by the help system, returning True if query can
        be found as a substring of the commands key or its aliases.

        Args:
            query (str): query to match against. Should be lower case.

        Returns:
            result (bool): Fuzzy matching result.

        """
        return any(query in keyalias for keyalias in self._keyaliases)

    def _optimize(self):
        """
        Optimize the key and aliases for lookups.
        """
        # optimization - a set is much faster to match against than a list
        self._matchset = set([self.key] + self.aliases)
        # optimization for looping over keys+aliases
        self._keyaliases = tuple(self._matchset)

    def set_key(self, new_key):
        """
        Update key.

        Args:
            new_key (str): The new key.

        Notes:
            This is necessary to use to make sure the optimization
            caches are properly updated as well.

        """
        self.key = new_key.lower()
        self._optimize()

    def set_aliases(self, new_aliases):
        """
        Update aliases.

        Args:
            new_aliases (list):

        Notes:
            This is necessary to use to make sure the optimization
            caches are properly updated as well.

        """
        if not is_iter(new_aliases):
            try:
                self.aliases = [str(alias).strip().lower()
                                for alias in self.aliases.split(',')]
            except Exception:
                self.aliases = []
        self.aliases = list(set(alias for alias in self.aliases
                            if alias and alias != self.key))
        self._optimize()


    def match(self, cmdname):
        """
        This is called by the system when searching the available commands,
        in order to determine if this is the one we wanted. cmdname was
        previously extracted from the raw string by the system.

        Args:
            cmdname (str): Always lowercase when reaching this point.

        Returns:
            result (bool): Match result.

        """
        return cmdname in self._matchset

    def access(self, srcobj, access_type="cmd", default=False):
        """
        This hook is called by the cmdhandler to determine if srcobj
        is allowed to execute this command. It should return a boolean
        value and is not normally something that need to be changed since
        it's using the Evennia permission system directly.

        Args:
            srcobj (Object): Object trying to gain permission
            access_type (str, optional): The lock type to check.
            default (bool, optional): The fallbacl result if no lock
                of matching `access_type` is found on this Command.

        """
        return self.lockhandler.check(srcobj, access_type, default=default)

    def msg(self, msg="", to_obj=None, from_obj=None,
            session=None, **kwargs):
        """
        This is a shortcut instad of calling msg() directly on an
        object - it will detect if caller is an Object or a Player and
        also appends self.session automatically.

        Args:
            msg (str, optional): Text string of message to send.
            to_obj (Object, optional): Target object of message. Defaults to self.caller.
            from_obj (Object, optional): Source of message. Defaults to to_obj.
            session (Session, optional): Supply data only to a unique
                session.

        Kwargs:
            kwargs (any): These are all passed on to the message mechanism. Common
                keywords are `oob` and `raw`.

        """
        from_obj = from_obj or self.caller
        to_obj = to_obj or from_obj
        if not session:
            if to_obj == self.caller:
                session = self.session
            else:
                session = to_obj.sessions.get()
        to_obj.msg(msg, from_obj=from_obj, session=session, **kwargs)

    # Common Command hooks

    def at_pre_cmd(self):
        """
        This hook is called before self.parse() on all commands.  If
        this hook returns anything but False/None, the command
        sequence is aborted.

        """
        pass

    def at_post_cmd(self):
        """
        This hook is called after the command has finished executing
        (after self.func()).

        """
        pass

    def parse(self):
        """
        Once the cmdhandler has identified this as the command we
        want, this function is run. If many of your commands have a
        similar syntax (for example 'cmd arg1 = arg2') you should
        simply define this once and just let other commands of the
        same form inherit from this. See the docstring of this module
        for which object properties are available to use (notably
        self.args).

        """
        pass

    def func(self):
        """
        This is the actual executing part of the command.  It is
        called directly after self.parse(). See the docstring of this
        module for which object properties are available (beyond those
        set in self.parse())

        """
        # a simple test command to show the available properties
        string = "-" * 50
        string += "\n{w%s{n - Command variables from evennia:\n" % self.key
        string += "-" * 50
        string += "\nname of cmd (self.key): {w%s{n\n" % self.key
        string += "cmd aliases (self.aliases): {w%s{n\n" % self.aliases
        string += "cmd locks (self.locks): {w%s{n\n" % self.locks
        string += "help category (self.help_category): {w%s{n\n" % self.help_category.capitalize()
        string += "object calling (self.caller): {w%s{n\n" % self.caller
        string += "object storing cmdset (self.obj): {w%s{n\n" % self.obj
        string += "command string given (self.cmdstring): {w%s{n\n" % self.cmdstring
        # show cmdset.key instead of cmdset to shorten output
        string += fill("current cmdset (self.cmdset): {w%s{n\n" % (self.cmdset.key if self.cmdset.key else self.cmdset.__class__))

        self.caller.msg(string)

    def get_extra_info(self, caller, **kwargs):
        """
        Display some extra information that may help distinguish this
        command from others, for instance, in a disambiguity prompt.

        If this command is a potential match in an ambiguous
        situation, one distinguishing feature may be its attachment to
        a nearby object, so we include this if available.

        Args:
            caller (TypedObject): The caller who typed an ambiguous
            term handed to the search function.

        Returns:
            A string with identifying information to disambiguate the
            object, conventionally with a preceding space.

        """
        if hasattr(self, 'obj') and self.obj != caller:
            return " (%s)" % self.obj.get_display_name(caller).strip()
        return ""
