"""
The base Command class.

All commands in Evennia inherit from the 'Command' class in this module.

"""
import inspect
import math
import re

from django.conf import settings
from django.urls import reverse
from django.utils.text import slugify

from evennia.locks.lockhandler import LockHandler
from evennia.utils.ansi import ANSIString
from evennia.utils.evtable import EvTable
from evennia.utils.utils import fill, is_iter, lazy_property, make_iter

CMD_IGNORE_PREFIXES = settings.CMD_IGNORE_PREFIXES


class InterruptCommand(Exception):

    """Cleanly interrupt a command."""

    pass


def _init_command(cls, **kwargs):
    """
    Helper command.
    Makes sure all data are stored as lowercase and
    do checking on all properties that should be in list form.
    Sets up locks to be more forgiving. This is used both by the metaclass
    and (optionally) at instantiation time.

    If kwargs are given, these are set as instance-specific properties
    on the command - but note that the Command instance is *re-used* on a given
    host object, so a kwarg value set on the instance will *remain* on the instance
    for subsequent uses of that Command on that particular object.

    """
    for i in range(len(kwargs)):
        # used for dynamic creation of commands
        key, value = kwargs.popitem()
        setattr(cls, key, value)

    cls.key = cls.key.lower()
    if cls.aliases and not is_iter(cls.aliases):
        try:
            cls.aliases = [str(alias).strip().lower() for alias in cls.aliases.split(",")]
        except Exception:
            cls.aliases = []
    cls.aliases = list(set(alias for alias in cls.aliases if alias and alias != cls.key))

    # optimization - a set is much faster to match against than a list
    cls._matchset = set([cls.key] + cls.aliases)
    # optimization for looping over keys+aliases
    cls._keyaliases = tuple(cls._matchset)

    # by default we don't save the command between runs
    if not hasattr(cls, "save_for_next"):
        cls.save_for_next = False

    # pre-process locks as defined in class definition
    temp = []
    if hasattr(cls, "permissions"):
        cls.locks = cls.permissions
    if not hasattr(cls, "locks"):
        # default if one forgets to define completely
        cls.locks = "cmd:all()"
    if "cmd:" not in cls.locks:
        cls.locks = "cmd:all();" + cls.locks
    for lockstring in cls.locks.split(";"):
        if lockstring and ":" not in lockstring:
            lockstring = "cmd:%s" % lockstring
        temp.append(lockstring)
    cls.lock_storage = ";".join(temp)

    if hasattr(cls, "arg_regex") and isinstance(cls.arg_regex, str):
        cls.arg_regex = re.compile(r"%s" % cls.arg_regex, re.I + re.UNICODE)
    if not hasattr(cls, "auto_help"):
        cls.auto_help = True
    if not hasattr(cls, "is_exit"):
        cls.is_exit = False
    if not hasattr(cls, "help_category"):
        cls.help_category = "general"
    if not hasattr(cls, "retain_instance"):
        cls.retain_instance = False

    # make sure to pick up the parent's docstring if the child class is
    # missing one (important for auto-help)
    if cls.__doc__ is None:
        for parent_class in inspect.getmro(cls):
            if parent_class.__doc__ is not None:
                cls.__doc__ = parent_class.__doc__
                break
    cls.help_category = cls.help_category.lower()

    # pre-prepare a help index entry for quicker lookup
    # strip the @- etc to allow help to be agnostic
    stripped_key = cls.key[1:] if cls.key and cls.key[0] in CMD_IGNORE_PREFIXES else ""
    stripped_aliases = " ".join(
        al[1:] if al and al[0] in CMD_IGNORE_PREFIXES else al for al in cls.aliases
    )
    cls.search_index_entry = {
        "key": cls.key,
        "aliases": " ".join(cls.aliases),
        "no_prefix": f"{stripped_key} {stripped_aliases}",
        "category": cls.help_category,
        "text": cls.__doc__,
        "tags": "",
    }


class CommandMeta(type):
    """
    The metaclass cleans up all properties on the class
    """

    def __init__(cls, *args, **kwargs):
        _init_command(cls, **kwargs)
        super().__init__(*args, **kwargs)


#    The Command class is the basic unit of an Evennia command; when
#    defining new commands, the admin subclass this class and
#    define their own parser method to handle the input. The
#    advantage of this is inheritage; commands that have similar
#    structure can parse the input string the same way, minimizing
#    parsing errors.


class Command(metaclass=CommandMeta):
    """
    ## Base command

    (you may see this if a child command had no help text defined)

    Usage:
      command [args]

    This is the base command class. Inherit from this
    to create new commands.

    The cmdhandler makes the following variables available to the
    command methods (so you can always assume them to be there):

    self.caller - the game object calling the command
    self.cmdstring - the command name used to trigger this command (allows
                     you to know which alias was used, for example)
    self.args - everything supplied to the command following the cmdstring
               (this is usually what is parsed in self.parse())
    self.cmdset - the cmdset from which this command was matched (useful only
                  seldomly, notably for help-type commands, to create dynamic
                  help entries and lists)
    self.obj - the object on which this command is defined. If a default command,
               this is usually the same as caller.
    self.raw_string - the full raw string input, including the command name,
                      any args and no parsing.

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
    auto_help_display_key - (optional) if given, this replaces the string shown
        in the auto-help listing. This is particularly useful for system-commands
        whose actual key is not really meaningful.

    (Note that if auto_help is on, this initial string is also used by the
    system to create the help entry for the command, so it's a good idea to
    format it similar to this one).  This behavior can be changed by
    overriding the method 'get_help' of a command: by default, this
    method returns cmd.__doc__ (that is, this very docstring, or
    the docstring of your command).  You can, however, extend or
    replace this without disabling auto_help.
    """

    # the main way to call this command (e.g. 'look')
    key = "command"
    # alternative ways to call the command (e.g. 'l', 'glance', 'examine')
    aliases = []
    # a list of lock definitions on the form
    #   cmd:[NOT] func(args) [ AND|OR][ NOT] func2(args)
    locks = settings.COMMAND_DEFAULT_LOCKS
    # used by the help system to group commands in lists.
    help_category = settings.COMMAND_DEFAULT_HELP_CATEGORY
    # This allows to turn off auto-help entry creation for individual commands.
    auto_help = True
    # optimization for quickly separating exit-commands from normal commands
    is_exit = False
    # define the command not only by key but by the regex form of its arguments
    arg_regex = settings.COMMAND_DEFAULT_ARG_REGEX
    # whether self.msg sends to all sessions of a related account/object (default
    # is to only send to the session sending the command).
    msg_all_sessions = settings.COMMAND_DEFAULT_MSG_ALL_SESSIONS
    # whether the exact command instance should be retained between command calls.
    # By default it's False; this allows for retaining state and saves some CPU, but
    # can cause cross-talk between users if multiple users access the same command
    # (especially if the command is using yield)
    retain_instance = False

    # auto-set (by Evennia on command instantiation) are:
    #   obj - which object this command is defined on
    #   session - which session is responsible for triggering this command. Only set
    #             if triggered by an account.

    def __init__(self, **kwargs):
        """
        The lockhandler works the same as for objects.
        optional kwargs will be set as properties on the Command at runtime,
        overloading evential same-named class properties.

        """
        if kwargs:
            _init_command(self, **kwargs)
        self._optimize()

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
        except AttributeError:
            # probably got a string
            return cmd in self._matchset

    def __hash__(self):
        """
        Python 3 requires that any class which implements __eq__ must also
        implement __hash__ and that the corresponding hashes for equivalent
        instances are themselves equivalent.

        Technically, the following implementation is only valid for comparison
        against other Commands, as our __eq__ supports comparison against
        str, too.

        """
        return hash("command")

    def __ne__(self, cmd):
        """
        The logical negation of __eq__. Since this is one of the most
        called methods in Evennia (along with __eq__) we do some
        code-duplication here rather than issuing a method-lookup to
        __eq__.
        """
        try:
            return self._matchset.isdisjoint(cmd._matchset)
        except AttributeError:
            return cmd not in self._matchset

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
        matches = [self.key.lower()]
        matches.extend(x.lower() for x in self.aliases)

        self._matchset = set(matches)
        # optimization for looping over keys+aliases
        self._keyaliases = tuple(self._matchset)

        self._noprefix_aliases = {x.lstrip(CMD_IGNORE_PREFIXES): x for x in matches}

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
        Replace aliases with new ones.

        Args:
            new_aliases (str or list): Either a ;-separated string
                or a list of aliases. These aliases will replace the
                existing ones, if any.

        Notes:
            This is necessary to use to make sure the optimization
            caches are properly updated as well.

        """
        if isinstance(new_aliases, str):
            new_aliases = new_aliases.split(";")
        aliases = (str(alias).strip().lower() for alias in make_iter(new_aliases))
        self.aliases = list(set(alias for alias in aliases if alias != self.key))
        self._optimize()

    def match(self, cmdname, include_prefixes=True):
        """
        This is called by the system when searching the available commands,
        in order to determine if this is the one we wanted. cmdname was
        previously extracted from the raw string by the system.

        Args:
            cmdname (str): Always lowercase when reaching this point.

        Kwargs:
            include_prefixes (bool): If false, will compare against the _noprefix
                variants of commandnames.

        Returns:
            result (bool): Match result.

        """
        if include_prefixes:
            for cmd_key in self._keyaliases:
                if cmdname.startswith(cmd_key) and (
                    not self.arg_regex or self.arg_regex.match(cmdname[len(cmd_key) :])
                ):
                    return cmd_key, cmd_key
        else:
            for k, v in self._noprefix_aliases.items():
                if cmdname.startswith(k) and (
                    not self.arg_regex or self.arg_regex.match(cmdname[len(k) :])
                ):
                    return k, v
        return None, None

    def access(self, srcobj, access_type="cmd", default=False):
        """
        This hook is called by the cmdhandler to determine if srcobj
        is allowed to execute this command. It should return a boolean
        value and is not normally something that need to be changed since
        it's using the Evennia permission system directly.

        Args:
            srcobj (Object): Object trying to gain permission
            access_type (str, optional): The lock type to check.
            default (bool, optional): The fallback result if no lock
                of matching `access_type` is found on this Command.

        """
        return self.lockhandler.check(srcobj, access_type, default=default)

    def msg(self, text=None, to_obj=None, from_obj=None, session=None, **kwargs):
        """
        This is a shortcut instead of calling msg() directly on an
        object - it will detect if caller is an Object or an Account and
        also appends self.session automatically if self.msg_all_sessions is False.

        Args:
            text (str, optional): Text string of message to send.
            to_obj (Object, optional): Target object of message. Defaults to self.caller.
            from_obj (Object, optional): Source of message. Defaults to to_obj.
            session (Session, optional): Supply data only to a unique
                session (ignores the value of `self.msg_all_sessions`).

        Keyword Args:
            options (dict): Options to the protocol.
            any (any): All other keywords are interpreted as th
                name of send-instructions.

        """
        from_obj = from_obj or self.caller
        to_obj = to_obj or from_obj
        if not session and not self.msg_all_sessions:
            if to_obj == self.caller:
                session = self.session
            else:
                session = to_obj.sessions.get()
        to_obj.msg(text=text, from_obj=from_obj, session=session, **kwargs)

    def execute_cmd(self, raw_string, session=None, obj=None, **kwargs):
        """
        A shortcut of execute_cmd on the caller. It appends the
        session automatically.

        Args:
            raw_string (str): Execute this string as a command input.
            session (Session, optional): If not given, the current command's Session will be used.
            obj (Object or Account, optional): Object or Account on which to call the execute_cmd.
                If not given, self.caller will be used.

        Keyword Args:
            Other keyword arguments will be added to the found command
            object instace as variables before it executes.  This is
            unused by default Evennia but may be used to set flags and
            change operating paramaters for commands at run-time.

        """
        obj = self.caller if obj is None else obj
        session = self.session if session is None else session
        obj.execute_cmd(raw_string, session=session, **kwargs)

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

    def get_command_info(self):
        """
        This is the default output of func() if no func() overload is done.
        Provided here as a separate method so that it can be called for debugging
        purposes when making commands.

        """
        variables = "\n".join(
            " |w{}|n ({}): {}".format(key, type(val), val) for key, val in self.__dict__.items()
        )
        string = f"""
Command {self} has no defined `func()` - showing on-command variables:
{variables}
        """
        # a simple test command to show the available properties
        string += "-" * 50
        string += "\n|w%s|n - Command variables from evennia:\n" % self.key
        string += "-" * 50
        string += "\nname of cmd (self.key): |w%s|n\n" % self.key
        string += "cmd aliases (self.aliases): |w%s|n\n" % self.aliases
        string += "cmd locks (self.locks): |w%s|n\n" % self.locks
        string += "help category (self.help_category): |w%s|n\n" % self.help_category.capitalize()
        string += "object calling (self.caller): |w%s|n\n" % self.caller
        string += "object storing cmdset (self.obj): |w%s|n\n" % self.obj
        string += "command string given (self.cmdstring): |w%s|n\n" % self.cmdstring
        # show cmdset.key instead of cmdset to shorten output
        string += fill(
            "current cmdset (self.cmdset): |w%s|n\n"
            % (self.cmdset.key if self.cmdset.key else self.cmdset.__class__)
        )

        self.caller.msg(string)

    def func(self):
        """
        This is the actual executing part of the command.  It is
        called directly after self.parse(). See the docstring of this
        module for which object properties are available (beyond those
        set in self.parse())

        """
        self.get_command_info()

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
        if hasattr(self, "obj") and self.obj and self.obj != caller:
            return " (%s)" % self.obj.get_display_name(caller).strip()
        return ""

    def get_help(self, caller, cmdset):
        """
        Return the help message for this command and this caller.

        By default, return self.__doc__ (the docstring just under
        the class definition).  You can override this behavior,
        though, and even customize it depending on the caller, or other
        commands the caller can use.

        Args:
            caller (Object or Account): the caller asking for help on the command.
            cmdset (CmdSet): the command set (if you need additional commands).

        Returns:
            docstring (str): the help text to provide the caller for this command.

        """
        return self.__doc__

    def web_get_detail_url(self):
        """
        Returns the URI path for a View that allows users to view details for
        this object.

        ex. Oscar (Character) = '/characters/oscar/1/'

        For this to work, the developer must have defined a named view somewhere
        in urls.py that follows the format 'modelname-action', so in this case
        a named view of 'character-detail' would be referenced by this method.

        ex.
        ::
            url(r'characters/(?P<slug>[\w\d\-]+)/(?P<pk>[0-9]+)/$',
                CharDetailView.as_view(), name='character-detail')

        If no View has been created and defined in urls.py, returns an
        HTML anchor.

        This method is naive and simply returns a path. Securing access to
        the actual view and limiting who can view this object is the developer's
        responsibility.

        Returns:
            path (str): URI path to object detail page, if defined.

        """
        try:
            return reverse(
                "help-entry-detail",
                kwargs={"category": slugify(self.help_category), "topic": slugify(self.key)},
            )
        except Exception as e:
            return "#"

    def web_get_admin_url(self):
        """
        Returns the URI path for the Django Admin page for this object.

        ex. Account#1 = '/admin/accounts/accountdb/1/change/'

        Returns:
            path (str): URI path to Django Admin page for object.

        """
        return False

    def client_width(self):
        """
        Get the client screenwidth for the session using this command.

        Returns:
            client width (int): The width (in characters) of the client window.

        """
        if self.session:
            return self.session.protocol_flags.get(
                "SCREENWIDTH", {0: settings.CLIENT_DEFAULT_WIDTH}
            )[0]
        return settings.CLIENT_DEFAULT_WIDTH

    def styled_table(self, *args, **kwargs):
        """
        Create an EvTable styled by on user preferences.

        Args:
            *args (str): Column headers. If not colored explicitly, these will get colors
                from user options.
        Keyword Args:
            any (str, int or dict): EvTable options, including, optionally a `table` dict
                detailing the contents of the table.
        Returns:
            table (EvTable): An initialized evtable entity, either complete (if using `table` kwarg)
                or incomplete and ready for use with `.add_row` or `.add_collumn`.

        """
        border_color = self.account.options.get("border_color")
        column_color = self.account.options.get("column_names_color")

        colornames = ["|%s%s|n" % (column_color, col) for col in args]

        h_line_char = kwargs.pop("header_line_char", "~")
        header_line_char = ANSIString(f"|{border_color}{h_line_char}|n")
        c_char = kwargs.pop("corner_char", "+")
        corner_char = ANSIString(f"|{border_color}{c_char}|n")

        b_left_char = kwargs.pop("border_left_char", "||")
        border_left_char = ANSIString(f"|{border_color}{b_left_char}|n")

        b_right_char = kwargs.pop("border_right_char", "||")
        border_right_char = ANSIString(f"|{border_color}{b_right_char}|n")

        b_bottom_char = kwargs.pop("border_bottom_char", "-")
        border_bottom_char = ANSIString(f"|{border_color}{b_bottom_char}|n")

        b_top_char = kwargs.pop("border_top_char", "-")
        border_top_char = ANSIString(f"|{border_color}{b_top_char}|n")

        table = EvTable(
            *colornames,
            header_line_char=header_line_char,
            corner_char=corner_char,
            border_left_char=border_left_char,
            border_right_char=border_right_char,
            border_top_char=border_top_char,
            border_bottom_char=border_bottom_char,
            **kwargs,
        )
        return table

    def _render_decoration(
        self,
        header_text=None,
        fill_character=None,
        edge_character=None,
        mode="header",
        color_header=True,
        width=None,
    ):
        """
        Helper for formatting a string into a pretty display, for a header, separator or footer.

        Keyword Args:
            header_text (str): Text to include in header.
            fill_character (str): This single character will be used to fill the width of the
                display.
            edge_character (str): This character caps the edges of the display.
            mode(str): One of 'header', 'separator' or 'footer'.
            color_header (bool): If the header should be colorized based on user options.
            width (int): If not given, the client's width will be used if available.

        Returns:
            string (str): The decorated and formatted text.

        """

        colors = dict()
        colors["border"] = self.account.options.get("border_color")
        colors["headertext"] = self.account.options.get("%s_text_color" % mode)
        colors["headerstar"] = self.account.options.get("%s_star_color" % mode)

        width = width or self.client_width()
        if edge_character:
            width -= 2

        if header_text:
            if color_header:
                header_text = ANSIString(header_text).clean()
                header_text = ANSIString("|n|%s%s|n" % (colors["headertext"], header_text))
            if mode == "header":
                begin_center = ANSIString(
                    "|n|%s<|%s* |n" % (colors["border"], colors["headerstar"])
                )
                end_center = ANSIString("|n |%s*|%s>|n" % (colors["headerstar"], colors["border"]))
                center_string = ANSIString(begin_center + header_text + end_center)
            else:
                center_string = ANSIString("|n |%s%s |n" % (colors["headertext"], header_text))
        else:
            center_string = ""

        fill_character = self.account.options.get("%s_fill" % mode)

        remain_fill = width - len(center_string)
        if remain_fill % 2 == 0:
            right_width = remain_fill / 2
            left_width = remain_fill / 2
        else:
            right_width = math.floor(remain_fill / 2)
            left_width = math.ceil(remain_fill / 2)

        right_fill = ANSIString("|n|%s%s|n" % (colors["border"], fill_character * int(right_width)))
        left_fill = ANSIString("|n|%s%s|n" % (colors["border"], fill_character * int(left_width)))

        if edge_character:
            edge_fill = ANSIString("|n|%s%s|n" % (colors["border"], edge_character))
            main_string = ANSIString(center_string)
            final_send = (
                ANSIString(edge_fill) + left_fill + main_string + right_fill + ANSIString(edge_fill)
            )
        else:
            final_send = left_fill + ANSIString(center_string) + right_fill
        return final_send

    def styled_header(self, *args, **kwargs):
        """
        Create a pretty header.
        """

        if "mode" not in kwargs:
            kwargs["mode"] = "header"
        return self._render_decoration(*args, **kwargs)

    def styled_separator(self, *args, **kwargs):
        """
        Create a separator.

        """
        if "mode" not in kwargs:
            kwargs["mode"] = "separator"
        return self._render_decoration(*args, **kwargs)

    def styled_footer(self, *args, **kwargs):
        """
        Create a pretty footer.

        """
        if "mode" not in kwargs:
            kwargs["mode"] = "footer"
        return self._render_decoration(*args, **kwargs)
