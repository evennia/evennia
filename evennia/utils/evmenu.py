"""
EvMenu

This implements a full menu system for Evennia.

To start the menu, just import the EvMenu class from this module.
Example usage:

```python

    from evennia.utils.evmenu import EvMenu

    EvMenu(caller, menu_module_path,
         startnode="node1",
         cmdset_mergetype="Replace", cmdset_priority=1,
         auto_quit=True, cmd_on_exit="look", persistent=True)
```

Where `caller` is the Object to use the menu on - it will get a new
cmdset while using the Menu. The menu_module_path is the python path
to a python module containing function definitions.  By adjusting the
keyword options of the Menu() initialization call you can start the
menu at different places in the menu definition file, adjust if the
menu command should overload the normal commands or not, etc.

The `persistent` keyword will make the menu survive a server reboot.
It is `False` by default. Note that if using persistent mode, every
node and callback in the menu must be possible to be *pickled*, this
excludes e.g. callables that are class methods or functions defined
dynamically or as part of another function. In non-persistent mode
no such restrictions exist.

The menu is defined in a module (this can be the same module as the
command definition too) with function definitions:

```python

    def node1(caller):
        # (this is the start node if called like above)
        # code
        return text, options

    def node_with_other_name(caller, input_string):
        # code
        return text, options
```

Where caller is the object using the menu and input_string is the
command entered by the user on the *previous* node (the command
entered to get to this node). The node function code will only be
executed once per node-visit and the system will accept nodes with
both one or two arguments interchangeably.

The menu tree itself is available on the caller as
`caller.ndb._menutree`. This makes it a convenient place to store
temporary state variables between nodes, since this NAttribute is
deleted when the menu is exited.

The return values must be given in the above order, but each can be
returned as None as well. If the options are returned as None, the
menu is immediately exited and the default "look" command is called.

    text (str, tuple or None): Text shown at this node. If a tuple, the
        second element in the tuple is a help text to display at this
        node when the user enters the menu help command there.
    options (tuple, dict or None): (
        {'key': name,   # can also be a list of aliases. A special key is
                        # "_default", which marks this option as the default
                        # fallback when no other option matches the user input.
         'desc': description, # optional description
         'goto': nodekey,  # node to go to when chosen. This can also be a callable with
                           # caller and/or raw_string args. It must return a string
                           # with the key pointing to the node to go to.
         'exec': nodekey}, # node or callback to trigger as callback when chosen. This
                           # will execute *before* going to the next node. Both node
                           # and the explicit callback will be called as normal nodes
                           # (with caller and/or raw_string args). If the callable/node
                           # returns a single string (only), this will replace the current
                           # goto location string in-place (if a goto callback, it will never fire).
                           # Note that relying to much on letting exec assign the goto
                           # location can make it hard to debug your menu logic.
        {...}, ...)

If key is not given, the option will automatically be identified by
its number 1..N.

Example:

```python

    # in menu_module.py

    def node1(caller):
        text = ("This is a node text",
                "This is help text for this node")
        options = ({"key": "testing",
                    "desc": "Select this to go to node 2",
                    "goto": "node2",
                    "exec": "callback1"},
                   {"desc": "Go to node 3.",
                    "goto": "node3"})
        return text, options

    def callback1(caller):
        # this is called when choosing the "testing" option in node1
        # (before going to node2). If it returned a string, say 'node3',
        # then the next node would be node3 instead of node2 as specified
        # by the normal 'goto' option key above.
        caller.msg("Callback called!")

    def node2(caller):
        text = '''
            This is node 2. It only allows you to go back
            to the original node1. This extra indent will
            be stripped. We don't include a help text.
            '''
        options = {"goto": "node1"}
        return text, options

    def node3(caller):
        text = "This ends the menu since there are no options."
        return text, None

```

When starting this menu with  `Menu(caller, "path.to.menu_module")`,
the first node will look something like this:

    This is a node text
    ______________________________________

    testing: Select this to go to node 2
    2: Go to node 3

Where you can both enter "testing" and "1" to select the first option.
If the client supports MXP, they may also mouse-click on "testing" to
do the same. When making this selection, a function "callback1" in the
same Using `help` will show the help text, otherwise a list of
available commands while in menu mode.

The menu tree is exited either by using the in-menu quit command or by
reaching a node without any options.


For a menu demo, import CmdTestMenu from this module and add it to
your default cmdset. Run it with this module, like `testmenu
evennia.utils.evmenu`.

"""
from __future__ import print_function
from builtins import object, range

from textwrap import dedent
from inspect import isfunction, getargspec
from django.conf import settings
from evennia import Command, CmdSet
from evennia.utils import logger
from evennia.utils.evtable import EvTable
from evennia.utils.ansi import strip_ansi
from evennia.utils.utils import mod_import, make_iter, pad, m_len
from evennia.commands import cmdhandler

# read from protocol NAWS later?
_MAX_TEXT_WIDTH = settings.CLIENT_DEFAULT_WIDTH

# we use cmdhandler instead of evennia.syscmdkeys to
# avoid some cases of loading before evennia init'd
_CMD_NOMATCH = cmdhandler.CMD_NOMATCH
_CMD_NOINPUT = cmdhandler.CMD_NOINPUT

# Return messages

# i18n
from django.utils.translation import ugettext as _
_ERR_NOT_IMPLEMENTED = _("Menu node '{nodename}' is not implemented. Make another choice.")
_ERR_GENERAL = _("Error in menu node '{nodename}'.")
_ERR_NO_OPTION_DESC = _("No description.")
_HELP_FULL = _("Commands: <menu option>, help, quit")
_HELP_NO_QUIT = _("Commands: <menu option>, help")
_HELP_NO_OPTIONS = _("Commands: help, quit")
_HELP_NO_OPTIONS_NO_QUIT = _("Commands: help")
_HELP_NO_OPTION_MATCH = _("Choose an option or try 'help'.")

_ERROR_PERSISTENT_SAVING = """
{error}

|rThe menu state could not be saved for persistent mode. Switching
to non-persistent mode (which means the menu session won't survive
an eventual server reload).|n
"""

_TRACE_PERSISTENT_SAVING = "EvMenu persistent-mode error. Commonly, this is because one or " \
                           "more of the EvEditor callbacks could not be pickled, for example " \
                           "because it's a class method or is defined inside another function."


class EvMenuError(RuntimeError):
    """
    Error raised by menu when facing internal errors.

    """
    pass

# -------------------------------------------------------------
#
# Menu command and command set
#
# -------------------------------------------------------------


class CmdEvMenuNode(Command):
    """
    Menu options.
    """
    key = _CMD_NOINPUT
    aliases = [_CMD_NOMATCH]
    locks = "cmd:all()"
    help_category = "Menu"

    def func(self):
        """
        Implement all menu commands.
        """
        def _restore(caller):
            # check if there is a saved menu available.
            # this will re-start a completely new evmenu call.
            saved_options = caller.attributes.get("_menutree_saved")
            if saved_options:
                startnode_tuple = caller.attributes.get("_menutree_saved_startnode")
                try:
                    startnode, startnode_input = startnode_tuple
                except ValueError:  # old form of startnode store
                    startnode, startnode_input = startnode_tuple, ""
                if startnode:
                    saved_options[1]["startnode"] = startnode
                    saved_options[1]["startnode_input"] = startnode_input
                # this will create a completely new menu call
                EvMenu(caller, *saved_options[0], **saved_options[1])
                return True
            return None

        caller = self.caller
        # we store Session on the menu since this can be hard to
        # get in multisession environemtns if caller is a Player.
        menu = caller.ndb._menutree
        if not menu:
            if _restore(caller):
                return
            orig_caller = caller
            caller = caller.player if hasattr(caller, "player") else None
            menu = caller.ndb._menutree if caller else None
            if not menu:
                if caller and _restore(caller):
                    return
                caller = self.session
                menu = caller.ndb._menutree
                if not menu:
                    # can't restore from a session
                    err = "Menu object not found as %s.ndb._menutree!" % orig_caller
                    orig_caller.msg(err) # don't give the session as a kwarg here, direct to original
                    raise EvMenuError(err)
        # we must do this after the caller with the menui has been correctly identified since it
        # can be either Player, Object or Session (in the latter case this info will be superfluous).
        caller.ndb._menutree._session = self.session
        # we have a menu, use it.
        menu._input_parser(menu, self.raw_string, caller)


class EvMenuCmdSet(CmdSet):
    """
    The Menu cmdset replaces the current cmdset.

    """
    key = "menu_cmdset"
    priority = 1
    mergetype = "Replace"
    no_objs = True
    no_exits = True
    no_channels = False

    def at_cmdset_creation(self):
        """
        Called when creating the set.
        """
        self.add(CmdEvMenuNode())


# These are default node formatters
def dedent_strip_nodetext_formatter(nodetext, has_options, caller=None):
    """
    Simple dedent formatter that also strips text
    """
    return dedent(nodetext).strip()


def dedent_nodetext_formatter(nodetext, has_options, caller=None):
    """
    Just dedent text.
    """
    return dedent(nodetext)


def evtable_options_formatter(optionlist, caller=None):
    """
    Formats the option list display.
    """
    if not optionlist:
        return ""

    # column separation distance
    colsep = 4

    nlist = len(optionlist)

    # get the widest option line in the table.
    table_width_max = -1
    table = []
    for key, desc in optionlist:
        if not (key or desc):
            continue
        table_width_max = max(table_width_max,
                              max(m_len(p) for p in key.split("\n")) +
                              max(m_len(p) for p in desc.split("\n")) + colsep)
        raw_key = strip_ansi(key)
        if raw_key != key:
            # already decorations in key definition
            table.append(" |lc%s|lt%s|le: %s" % (raw_key, key, desc))
        else:
            # add a default white color to key
            table.append(" |lc%s|lt|w%s|n|le: %s" % (raw_key, raw_key, desc))

    ncols = (_MAX_TEXT_WIDTH // table_width_max) + 1  # number of ncols

    # get the amount of rows needed (start with 4 rows)
    nrows = 4
    while nrows * ncols < nlist:
        nrows += 1
    ncols = nlist // nrows  # number of full columns
    nlastcol = nlist % nrows  # number of elements in last column

    # get the final column count
    ncols = ncols + 1 if nlastcol > 0 else ncols
    if ncols > 1:
        # only extend if longer than one column
        table.extend([" " for _ in range(nrows - nlastcol)])

    # build the actual table grid
    table = [table[icol * nrows: (icol * nrows) + nrows] for icol in range(0, ncols)]

    # adjust the width of each column
    for icol in range(len(table)):
        col_width = max(max(m_len(p) for p in part.split("\n")) for part in table[icol]) + colsep
        table[icol] = [pad(part, width=col_width + colsep, align="l") for part in table[icol]]

    # format the table into columns
    return unicode(EvTable(table=table, border="none"))


def underline_node_formatter(nodetext, optionstext, caller=None):
    """
    Draws a node with underlines '_____' around it.
    """
    nodetext_width_max = max(m_len(line) for line in nodetext.split("\n"))
    options_width_max = max(m_len(line) for line in optionstext.split("\n"))
    total_width = max(options_width_max, nodetext_width_max)
    separator1 = "_" * total_width + "\n\n" if nodetext_width_max else ""
    separator2 = "\n" + "_" * total_width + "\n\n" if total_width else ""
    return separator1 + "|n" + nodetext + "|n" + separator2 + "|n" + optionstext


def null_node_formatter(nodetext, optionstext, caller=None):
    """
    A minimalistic node formatter, no lines or frames.
    """
    return nodetext + "\n\n" + optionstext


def evtable_parse_input(menuobject, raw_string, caller):
    """
    Processes the user's node inputs.

    Args:
        menuobject (EvMenu): The EvMenu instance
        raw_string (str): The incoming raw_string from the menu
            command.
        caller (Object, Player or Session): The entity using
            the menu.
    """
    cmd = raw_string.strip().lower()

    if cmd in menuobject.options:
        # this will take precedence over the default commands
        # below
        goto, callback = menuobject.options[cmd]
        menuobject.callback_goto(callback, goto, raw_string)
    elif menuobject.auto_look and cmd in ("look", "l"):
        menuobject.display_nodetext()
    elif menuobject.auto_help and cmd in ("help", "h"):
        menuobject.display_helptext()
    elif menuobject.auto_quit and cmd in ("quit", "q", "exit"):
        menuobject.close_menu()
    elif menuobject.default:
        goto, callback = menuobject.default
        menuobject.callback_goto(callback, goto, raw_string)
    else:
        caller.msg(_HELP_NO_OPTION_MATCH, session=menuobject._session)

    if not (menuobject.options or menuobject.default):
        # no options - we are at the end of the menu.
        menuobject.close_menu()

# -------------------------------------------------------------
#
# Menu main class
#
# -------------------------------------------------------------


class EvMenu(object):
    """
    This object represents an operational menu. It is initialized from
    a menufile.py instruction.

    """
    def __init__(self, caller, menudata, startnode="start",
                 cmdset_mergetype="Replace", cmdset_priority=1,
                 auto_quit=True, auto_look=True, auto_help=True,
                 cmd_on_exit="look",
                 nodetext_formatter=dedent_strip_nodetext_formatter,
                 options_formatter=evtable_options_formatter,
                 node_formatter=underline_node_formatter,
                 input_parser=evtable_parse_input,
                 persistent=False, startnode_input="", session=None,
                 **kwargs):
        """
        Initialize the menu tree and start the caller onto the first node.

        Args:
            caller (Object, Player or Session): The user of the menu.
            menudata (str, module or dict): The full or relative path to the module
                holding the menu tree data. All global functions in this module
                whose name doesn't start with '_ ' will be parsed as menu nodes.
                Also the module itself is accepted as input. Finally, a dictionary
                menu tree can be given directly. This must then be a mapping
                `{"nodekey":callable,...}` where `callable` must be called as
                and return the data expected of a menu node. This allows for
                dynamic menu creation.
            startnode (str, optional): The starting node name in the menufile.
            cmdset_mergetype (str, optional): 'Replace' (default) means the menu
                commands will be exclusive - no other normal commands will
                be usable while the user is in the menu. 'Union' means the
                menu commands will be integrated with the existing commands
                (it will merge with `merge_priority`), if so, make sure that
                the menu's command names don't collide with existing commands
                in an unexpected way. Also the CMD_NOMATCH and CMD_NOINPUT will
                be overloaded by the menu cmdset. Other cmdser mergetypes
                has little purpose for the menu.
            cmdset_priority (int, optional): The merge priority for the
                menu command set. The default (1) is usually enough for most
                types of menus.
            auto_quit (bool, optional): Allow user to use "q", "quit" or
                "exit" to leave the menu at any point. Recommended during
                development!
            auto_look (bool, optional): Automatically make "looK" or "l" to
                re-show the last node. Turning this off means you have to handle
                re-showing nodes yourself, but may be useful if you need to
                use "l" for some other purpose.
            auto_help (bool, optional): Automatically make "help" or "h" show
                the current help entry for the node. If turned off, eventual
                help must be handled manually, but it may be useful if you
                need 'h' for some other purpose, for example.
            cmd_on_exit (callable, str or None, optional): When exiting the menu
                (either by reaching a node with no options or by using the
                in-built quit command (activated with `allow_quit`), this
                callback function or command string will be executed.
                The callback function takes two parameters, the caller then the
                EvMenu object. This is called after cleanup is complete.
                Set to None to not call any command.
            nodetext_formatter (callable, optional): This callable should be on
                the form `function(nodetext, has_options, caller=None)`, where `nodetext` is the
                node text string and `has_options` a boolean specifying if there
                are options associated with this node. It must return a formatted
                string. `caller` is optionally a reference to the user of the menu.
                `caller` is optionally a reference to the user of the menu.
            options_formatter (callable, optional): This callable should be on
                the form `function(optionlist, caller=None)`, where ` optionlist is a list
                of option dictionaries, like
                [{"key":..., "desc",..., "goto": ..., "exec",...}, ...]
                Each dictionary describes each possible option. Note that this
                will also be called if there are no options, and so should be
                able to handle an empty list. This should
                be formatted into an options list and returned as a string,
                including the required separator to use between the node text
                and the options. If not given the default EvMenu style will be used.
                `caller` is optionally a reference to the user of the menu.
            node_formatter (callable, optional): This callable should be on the
                form `func(nodetext, optionstext, caller=None)` where the arguments are strings
                representing the node text and options respectively (possibly prepared
                by `nodetext_formatter`/`options_formatter` or by the default styles).
                It should return a string representing the final look of the node. This
                can e.g. be used to create line separators that take into account the
                dynamic width of the parts. `caller` is optionally a reference to the
                user of the menu.
            input_parser (callable, optional): This callable is responsible for parsing the
                options dict from a node and has the form `func(menuobject, raw_string, caller)`,
                where menuobject is the active `EvMenu` instance, `input_string` is the
                incoming text from the caller and `caller` is the user of the menu.
                It should use the helper method of the menuobject to goto new nodes, show
                help texts etc. See the default `evtable_parse_input` function for help
                with parsing.
            persistent (bool, optional): Make the Menu persistent (i.e. it will
                survive a reload. This will make the Menu cmdset persistent. Use
                with caution - if your menu is buggy you may end up in a state
                you can't get out of! Also note that persistent mode requires
                that all formatters, menu nodes and callables are possible to
                *pickle*. When the server is reloaded, the latest node shown will be completely
                re-run with the same input arguments - so be careful if you are counting
                up some persistent counter or similar - the counter may be run twice if
                reload happens on the node that does that.
            startnode_input (str, optional): Send an input text to `startnode` as if
                a user input text from a fictional previous node. When the server reloads,
                the latest visited node will be re-run using this kwarg.
            session (Session, optional): This is useful when calling EvMenu from a player
                in multisession mode > 2. Note that this session only really relevant
                for the very first display of the first node - after that, EvMenu itself
                will keep the session updated from the command input. So a persistent
                menu will *not* be using this same session anymore after a reload.

        Kwargs:
            any (any): All kwargs will become initialization variables on `caller.ndb._menutree`,
                to be available at run.

        Raises:
            EvMenuError: If the start/end node is not found in menu tree.

        Notes:
            While running, the menu is stored on the caller as `caller.ndb._menutree`. Also
            the current Session (from the Command, so this is still valid in multisession
            environments) is available through `caller.ndb._menutree._session`. The `_menutree`
            property is a good one for storing intermediary data on between nodes since it
            will be automatically deleted when the menu closes.

            In persistent mode, all nodes, formatters and callbacks in the menu must be
            possible to be *pickled*, this excludes e.g. callables that are class methods
            or functions defined dynamically or as part of another function. In
            non-persistent mode no such restrictions exist.

        """
        self._startnode = startnode
        self._menutree = self._parse_menudata(menudata)

        self._nodetext_formatter = nodetext_formatter
        self._options_formatter = options_formatter
        self._node_formatter = node_formatter
        self._input_parser = input_parser
        self._persistent = persistent

        if startnode not in self._menutree:
            raise EvMenuError("Start node '%s' not in menu tree!" % startnode)

        # public variables made available to the command

        self.caller = caller
        self.auto_quit = auto_quit
        self.auto_look = auto_look
        self.auto_help = auto_help
        self._session = session
        if isinstance(cmd_on_exit, str):
            # At this point menu._session will have been replaced by the
            # menu command to the actual session calling.
            self.cmd_on_exit = lambda caller, menu: caller.execute_cmd(cmd_on_exit, session=menu._session)
        elif callable(cmd_on_exit):
            self.cmd_on_exit = cmd_on_exit
        else:
            self.cmd_on_exit = None
        self.default = None
        self.nodetext = None
        self.helptext = None
        self.options = None

        # assign kwargs as initialization vars on ourselves.
        if set(("_startnode", "_menutree", "_nodetext_formatter", "_options_formatter",
                "node_formatter", "_input_parser", "_peristent", "cmd_on_exit", "default",
                "nodetext", "helptext", "options")).intersection(set(kwargs.keys())):
            raise RuntimeError("One or more of the EvMenu `**kwargs` is reserved by EvMenu for internal use.")
        for key, val in kwargs.iteritems():
            setattr(self, key, val)

        # store ourself on the object
        self.caller.ndb._menutree = self

        if persistent:
            # save the menu to the database
            try:
                caller.attributes.add("_menutree_saved",
                                      ((menudata, ),
                                       {"startnode": startnode,
                                        "cmdset_mergetype": cmdset_mergetype,
                                        "cmdset_priority": cmdset_priority,
                                        "auto_quit": auto_quit, "auto_look": auto_look, "auto_help": auto_help,
                                        "cmd_on_exit": cmd_on_exit,
                                        "nodetext_formatter": nodetext_formatter,
                                        "options_formatter": options_formatter,
                                        "node_formatter": node_formatter, "input_parser": input_parser,
                                        "persistent": persistent, }))
                caller.attributes.add("_menutree_saved_startnode", (startnode, startnode_input))
            except Exception as err:
                caller.msg(_ERROR_PERSISTENT_SAVING.format(error=err), session=self._session)
                logger.log_trace(_TRACE_PERSISTENT_SAVING)
                persistent = False

        # set up the menu command on the caller
        menu_cmdset = EvMenuCmdSet()
        menu_cmdset.mergetype = str(cmdset_mergetype).lower().capitalize() or "Replace"
        menu_cmdset.priority = int(cmdset_priority)
        self.caller.cmdset.add(menu_cmdset, permanent=persistent)

        # start the menu
        self.goto(self._startnode, startnode_input)

    def _parse_menudata(self, menudata):
        """
        Parse a menufile for node functions and store in dictionary
        map. Alternatively, accept a pre-made mapping dictionary of
        node functions.

        Args:
            menudata (str, module or dict): The python.path to the menufile,
                or the python module itself. If a dict, this should be a
                mapping nodename:callable, where the callable must match
                the criteria for a menu node.

        Returns:
            menutree (dict): A {nodekey: func}

        """
        if isinstance(menudata, dict):
            # This is assumed to be a pre-loaded menu tree.
            return menudata
        else:
            # a python path of a module
            module = mod_import(menudata)
            return dict((key, func) for key, func in module.__dict__.items()
                        if isfunction(func) and not key.startswith("_"))

    def _format_node(self, nodetext, optionlist):
        """
        Format the node text + option section

        Args:
            nodetext (str): The node text
            optionlist (list): List of (key, desc) pairs.

        Returns:
            string (str): The options section, including
                all needed spaces.

        Notes:
            This will adjust the columns of the options, first to use
            a maxiumum of 4 rows (expanding in columns), then gradually
            growing to make use of the screen space.

        """

        # handle the node text
        nodetext = self._nodetext_formatter(nodetext, len(optionlist), self.caller)

        # handle the options
        optionstext = self._options_formatter(optionlist, self.caller)

        # format the entire node
        return self._node_formatter(nodetext, optionstext, self.caller)

    def _execute_node(self, nodename, raw_string):
        """
        Execute a node.

        Args:
            nodename (str): Name of node.
            raw_string (str): The raw default string entered on the
                previous node (only used if the node accepts it as an
                argument)

        Returns:
            nodetext, options (tuple): The node text (a string or a
                tuple and the options tuple, if any.

        """
        try:
            node = self._menutree[nodename]
        except KeyError:
            self.caller.msg(_ERR_NOT_IMPLEMENTED.format(nodename=nodename), session=self._session)
            raise EvMenuError
        try:
            # the node should return data as (text, options)
            if len(getargspec(node).args) > 1:
                # a node accepting raw_string
                nodetext, options = node(self.caller, raw_string)
            else:
                # a normal node, only accepting caller
                nodetext, options = node(self.caller)
        except KeyError:
            self.caller.msg(_ERR_NOT_IMPLEMENTED.format(nodename=nodename), session=self._session)
            raise EvMenuError
        except Exception:
            self.caller.msg(_ERR_GENERAL.format(nodename=nodename), session=self._session)
            raise
        return nodetext, options

    def display_nodetext(self):
        self.caller.msg(self.nodetext, session=self._session)

    def display_helptext(self):
        self.caller.msg(self.helptext, session=self._session)

    def callback_goto(self, callback, goto, raw_string):
        """
        Call callback and goto in sequence.

        Args:
            callback (callable or str): Callback to run before goto. If
                the callback returns a string, this is used to replace
                the `goto` string before going to the next node.
            goto (str): The target node to go to next (unless replaced
                by `callable`)..
            raw_string (str): The original user input.

        """
        if callback:
            # replace goto only if callback returns
            goto = self.callback(callback, raw_string) or goto
        if goto:
            self.goto(goto, raw_string)

    def callback(self, nodename, raw_string):
        """
        Run a function or node as a callback (with the 'exec' option key).

        Args:
            nodename (callable or str): A callable to run as
                `callable(caller, raw_string)`, or the Name of an existing
                node to run as a callable. This may or may not return
                a string.
            raw_string (str): The raw default string entered on the
                previous node (only used if the node accepts it as an
                argument)
        Returns:
            new_goto (str or None): A replacement goto location string or
                None (no replacement).
        Notes:
            Relying on exec callbacks to set the goto location is
            very powerful but will easily lead to spaghetti structure and
            hard-to-trace paths through the menu logic. So be careful with
            relying on this.

        """
        if callable(nodename):
            # this is a direct callable - execute it directly
            try:
                if len(getargspec(nodename).args) > 1:
                    # callable accepting raw_string
                    ret = nodename(self.caller, raw_string)
                else:
                    # normal callable, only the caller as arg
                    ret = nodename(self.caller)
            except Exception:
                self.caller.msg(_ERR_GENERAL.format(nodename=nodename), self._session)
                raise
        else:
            # nodename is a string; lookup as node
            try:
                # execute the node
                ret = self._execute_node(nodename, raw_string)
            except EvMenuError:
                return
        if isinstance(ret, basestring):
            # only return a value if a string (a goto target), ignore all other returns
            return ret
        return None

    def goto(self, nodename, raw_string):
        """
        Run a node by name

        Args:
            nodename (str or callable): Name of node or a callable
                to be called as `function(caller, raw_string)` or `function(caller)`
                to return the actual goto string.
            raw_string (str): The raw default string entered on the
                previous node (only used if the node accepts it as an
                argument)

        """
        if callable(nodename):
            try:
                if len(getargspec(nodename).args) > 1:
                    # callable accepting raw_string
                    nodename = nodename(self.caller, raw_string)
                else:
                    nodename = nodename(self.caller)
            except Exception:
                self.caller.msg(_ERR_GENERAL.format(nodename=nodename), self._session)
                raise
        try:
            # execute the node, make use of the returns.
            nodetext, options = self._execute_node(nodename, raw_string)
        except EvMenuError:
            return

        if self._persistent:
            self.caller.attributes.add("_menutree_saved_startnode", (nodename, raw_string))

        # validation of the node return values
        helptext = ""
        if hasattr(nodetext, "__iter__"):
            if len(nodetext) > 1:
                nodetext, helptext = nodetext[:2]
            else:
                nodetext = nodetext[0]
        nodetext = "" if nodetext is None else str(nodetext)
        options = [options] if isinstance(options, dict) else options

        # this will be displayed in the given order
        display_options = []
        # this is used for lookup
        self.options = {}
        self.default = None
        if options:
            for inum, dic in enumerate(options):
                # fix up the option dicts
                keys = make_iter(dic.get("key"))
                if "_default" in keys:
                    keys = [key for key in keys if key != "_default"]
                    desc = dic.get("desc", dic.get("text", _ERR_NO_OPTION_DESC).strip())
                    goto, execute = dic.get("goto", None), dic.get("exec", None)
                    self.default = (goto, execute)
                else:
                    keys = list(make_iter(dic.get("key", str(inum+1).strip())))
                    desc = dic.get("desc", dic.get("text", _ERR_NO_OPTION_DESC).strip())
                    goto, execute = dic.get("goto", None), dic.get("exec", None)
                if keys:
                    display_options.append((keys[0], desc))
                    for key in keys:
                        if goto or execute:
                            self.options[strip_ansi(key).strip().lower()] = (goto, execute)

        self.nodetext = self._format_node(nodetext, display_options)

        # handle the helptext
        if helptext:
            self.helptext = helptext
        elif options:
            self.helptext = _HELP_FULL if self.auto_quit else _HELP_NO_QUIT
        else:
            self.helptext = _HELP_NO_OPTIONS if self.auto_quit else _HELP_NO_OPTIONS_NO_QUIT

        self.display_nodetext()
        if not options:
            self.close_menu()

    def close_menu(self):
        """
        Shutdown menu; occurs when reaching the end node or using the quit command.
        """
        self.caller.cmdset.remove(EvMenuCmdSet)
        del self.caller.ndb._menutree
        if self._persistent:
            self.caller.attributes.remove("_menutree_saved")
            self.caller.attributes.remove("_menutree_saved_startnode")
        if self.cmd_on_exit is not None:
            self.cmd_on_exit(self.caller, self)


# -------------------------------------------------------------------------------------------------
#
# Simple input shortcuts
#
# -------------------------------------------------------------------------------------------------

class CmdGetInput(Command):
    """
    Enter your data and press return.
    """
    key = _CMD_NOMATCH
    aliases = _CMD_NOINPUT

    def func(self):
        """This is called when user enters anything."""
        caller = self.caller
        try:
            getinput = caller.ndb._getinput
            if not getinput and hasattr(caller, "player"):
                getinput = caller.player.ndb._getinput
                caller = caller.player
            callback = getinput._callback

            caller.ndb._getinput._session = self.session
            prompt = caller.ndb._getinput._prompt
            args = caller.ndb._getinput._args
            kwargs = caller.ndb._getinput._kwargs
            result = self.raw_string.strip()  # we strip the ending line break caused by sending

            ok = not callback(caller, prompt, result, *args, **kwargs)
            if ok:
                # only clear the state if the callback does not return
                # anything
                del caller.ndb._getinput
                caller.cmdset.remove(InputCmdSet)
        except Exception:
            # make sure to clean up cmdset if something goes wrong
            caller.msg("|rError in get_input. Choice not confirmed (report to admin)|n")
            logger.log_trace("Error in get_input")
            caller.cmdset.remove(InputCmdSet)


class InputCmdSet(CmdSet):
    """
    This stores the input command
    """
    key = "input_cmdset"
    priority = 1
    mergetype = "Replace"
    no_objs = True
    no_exits = True
    no_channels = False

    def at_cmdset_creation(self):
        """called once at creation"""
        self.add(CmdGetInput())


class _Prompt(object):
    """Dummy holder"""
    pass


def get_input(caller, prompt, callback, session=None, *args, **kwargs):
    """
    This is a helper function for easily request input from
    the caller.

    Args:
        caller (Player or Object): The entity being asked
            the question. This should usually be an object
            controlled by a user.
        prompt (str): This text will be shown to the user,
            in order to let them know their input is needed.
        callback (callable): A function that will be called
            when the user enters a reply. It must take three
            arguments: the `caller`, the `prompt` text and the
            `result` of the input given by the user. If the
            callback doesn't return anything or return False,
            the input prompt will be cleaned up and exited. If
            returning True, the prompt will remain and continue to
            accept input.
        session (Session, optional): This allows to specify the
            session to send the prompt to. It's usually only
            needed if `caller` is a Player in multisession modes
            greater than 2. The session is then updated by the
            command and is available (for example in callbacks)
            through `caller.ndb.getinput._session`.
        *args, **kwargs (optional): Extra arguments will be
            passed to the fall back function as a list 'args'
            and all keyword arguments as a dictionary 'kwargs'.
            To utilise *args and **kwargs, a value for the
            session argument must be provided (None by default)
            and the callback function must take *args and
            **kwargs as arguments.

    Raises:
        RuntimeError: If the given callback is not callable.

    Notes:
        The result value sent to the callback is raw and not
        processed in any way. This means that you will get
        the ending line return character from most types of
        client inputs. So make sure to strip that before
        doing a comparison.

        When the prompt is running, a temporary object
        `caller.ndb._getinput` is stored; this will be removed
        when the prompt finishes.
        If you need the specific Session of the caller (which
        may not be easy to get if caller is a player in higher
        multisession modes), then it is available in the
        callback through `caller.ndb._getinput._session`.

        Chaining get_input functions will result in the caller
        stacking ever more instances of InputCmdSets. Whilst
        they will all be cleared on concluding the get_input
        chain, EvMenu should be considered for anything beyond
        a single question.

    """
    if not callable(callback):
        raise RuntimeError("get_input: input callback is not callable.")
    caller.ndb._getinput = _Prompt()
    caller.ndb._getinput._callback = callback
    caller.ndb._getinput._prompt = prompt
    caller.ndb._getinput._session = session
    caller.ndb._getinput._args = args
    caller.ndb._getinput._kwargs = kwargs
    caller.cmdset.add(InputCmdSet)
    caller.msg(prompt, session=session)


# -------------------------------------------------------------
#
# test menu strucure and testing command
#
# -------------------------------------------------------------

def test_start_node(caller):
    menu = caller.ndb._menutree
    text = """
    This is an example menu.

    If you enter anything except the valid options, your input will be
    recorded and you will be brought to a menu entry showing your
    input.

    Select options or use 'quit' to exit the menu.

    The menu was initialized with two variables: %s and %s.
    """ % (menu.testval, menu.testval2)

    options = ({"key": ("|yS|net", "s"),
                "desc": "Set an attribute on yourself.",
                "exec": lambda caller: caller.attributes.add("menuattrtest", "Test value"),
                "goto": "test_set_node"},
               {"key": ("|yL|nook", "l"),
                "desc": "Look and see a custom message.",
                "goto": "test_look_node"},
               {"key": ("|yV|niew", "v"),
                "desc": "View your own name",
                "goto": "test_view_node"},
               {"key": ("|yQ|nuit", "quit", "q", "Q"),
                "desc": "Quit this menu example.",
                "goto": "test_end_node"},
               {"key": "_default",
                "goto": "test_displayinput_node"})
    return text, options


def test_look_node(caller):
    text = ""
    options = {"key": ("|yL|nook", "l"),
               "desc": "Go back to the previous menu.",
               "goto": "test_start_node"}
    return text, options


def test_set_node(caller):
    text = ("""
    The attribute 'menuattrtest' was set to

            |w%s|n

    (check it with examine after quitting the menu).

    This node's has only one option, and one of its key aliases is the
    string "_default", meaning it will catch any input, in this case
    to return to the main menu.  So you can e.g. press <return> to go
    back now.
    """ % caller.db.menuattrtest,  # optional help text for this node
            """
    This is the help entry for this node. It is created by returning
    the node text as a tuple - the second string in that tuple will be
    used as the help text.
    """)

    options = {"key": ("back (default)", "_default"),
               "desc": "back to main",
               "goto": "test_start_node"}
    return text, options


def test_view_node(caller):
    text = """
    Your name is |g%s|n!

    click |lclook|lthere|le to trigger a look command under MXP.
    This node's option has no explicit key (nor the "_default" key
    set), and so gets assigned a number automatically. You can infact
    -always- use numbers (1...N) to refer to listed options also if you
    don't see a string option key (try it!).
    """ % caller.key
    options = {"desc": "back to main",
               "goto": "test_start_node"}
    return text, options


def test_displayinput_node(caller, raw_string):
    text = """
    You entered the text:

        "|w%s|n"

    ... which could now be handled or stored here in some way if this
    was not just an example.

    This node has an option with a single alias "_default", which
    makes it hidden from view. It catches all input (except the
    in-menu help/quit commands) and will, in this case, bring you back
    to the start node.
    """ % raw_string
    options = {"key": "_default",
               "goto": "test_start_node"}
    return text, options


def test_end_node(caller):
    text = """
    This is the end of the menu and since it has no options the menu
    will exit here, followed by a call of the "look" command.
    """
    return text, None


class CmdTestMenu(Command):
    """
    Test menu

    Usage:
      testmenu <menumodule>

    Starts a demo menu from a menu node definition module.

    """
    key = "testmenu"

    def func(self):

        if not self.args:
            self.caller.msg("Usage: testmenu menumodule")
            return
        # start menu
        EvMenu(self.caller, self.args.strip(), startnode="test_start_node", persistent=True,
               cmdset_mergetype="Replace", testval="val", testval2="val2")
