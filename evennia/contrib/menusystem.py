"""
Evennia menu system.

Contribution - Griatch 2011

This module offers the ability for admins to let their game be fully
or partly menu-driven. Menu choices can be numbered or use arbitrary
keys. There are also some formatting options, such a putting options
in one or more columns.

The menu system consists of a MenuTree object populated by MenuNode
objects. Nodes are linked together with automatically created commands
so the player may select and traverse the menu. Each node can display
text and show options, but also execute a callback to act on the
system and the calling object when they are selected.

There is also a simple Yes/No function as well as a one-level choice
function supplied. This will create a one-off Yes/No question or a
one-level choice. These helpers will execute a given callback
depending on which choice was made.

To start a menu, define the nodes of the menu and then add the
following to a command `func` you can call:

```python

menu = MenuTree(self.caller, nodes=(...))
menu.start()

```

This will switch you into menu-mode. See `contrib/menu_login.py` for an
example of usage.


For a simple demonstration, add `CmdMenuTest` from this module to the default cmdset.

"""
from types import MethodType
from evennia import syscmdkeys

from evennia import Command, CmdSet, utils
from evennia import default_cmds, logger

# imported only to make it available during execution of code blocks
import evennia

CMD_NOMATCH = syscmdkeys.CMD_NOMATCH
CMD_NOINPUT = syscmdkeys.CMD_NOINPUT


#
# Commands used by the Menu system
#

class CmdMenuNode(Command):
    """
    Parent for menu selection commands.
    """
    key = "selection"
    aliases = []
    locks = "cmd:all()"
    help_category = "Menu"

    menutree = None
    callback = None

    def func(self):
        "Execute a selection"

        if self.callback:
            try:
                self.callback()
            except Exception, e:
                self.caller.msg("%s\n{rThere was an error with this selection.{n" % e)
        else:
            self.caller.msg("{rThis option is not available.{n")


class CmdMenuLook(default_cmds.CmdLook):
    """
    ooc look

    Usage:
      look

    This is a Menu version of the look command. It will normally show
    the options available, otherwise works like the normal look
    command.
    """
    key = "look"
    aliases = ["l", "ls"]
    locks = "cmd:all()"
    help_cateogory = "General"

    def func(self):
        "implement the menu look command"
        if self.caller.db._menu_data:
            # if we have menu data, try to use that.
            lookstring = self.caller.db._menu_data.get("look", None)
            if lookstring:
                self.caller.msg(lookstring)
                return
        # otherwise we use normal look
        super(CmdMenuLook, self).func()


class CmdMenuHelp(default_cmds.CmdHelp):
    """
    help

    Usage:
      help

    Get help specific to the menu, if available. If not,
    works like the normal help command.
    """
    key = "help"
    aliases = "h"
    locks = "cmd:all()"
    help_category = "Menu"

    def func(self):
        "implement the menu help command"
        if self.caller.db._menu_data:
            # if we have menu data, try to use that.
            lookstring = self.caller.db._menu_data.get("help", None)
            if lookstring:
                self.caller.msg(lookstring)
                return
        # otherwise we use normal help
        super(CmdMenuHelp, self).func()


class MenuCmdSet(CmdSet):
    """
    Cmdset for the menu. Will replace all other commands.
    This always has a few basic commands available.

    Note that you must always supply a way to exit the
    cmdset manually!
    """
    key = "menucmdset"
    priority = 1
    mergetype = "Replace"
    # secure the menu against local cmdsets (but leave channels)
    no_objs = True
    no_exits = True
    no_channels = False

    def at_cmdset_creation(self):
        "populate cmdset"
        pass


#
# Menu Node system
#

class MenuTree(object):
    """
    The menu tree object holds the full menu structure consisting of
    MenuNodes. Each node is identified by a unique key.  The tree
    allows for traversal of nodes as well as entering and exiting the
    tree as needed. For safety, being in a menu will not survive a
    server reboot.

    A menutree has two special node keys given by 'startnode' and
    'endnode' arguments. The startnode is where the user will start
    upon first entering the menu.  The endnode need not actually
    exist, the moment it is linked to and that link is used, the menu
    will be exited and cleanups run. The default keys for these are
    'START' and 'END' respectively.

    """
    def __init__(self, caller, nodes=None,
                 startnode="START", endnode="END", exec_end="look"):
        """
        We specify startnode/endnode so that the system knows where to
        enter and where to exit the menu tree. If nodes is given, it
        should be a list of valid node objects to add to the tree.

        caller (Object): The caller triggering the menu
        nodes (tuple, optional): A tuple of `MenuNode` objects. This need
            not be in any particular order.
        startnode (str, optional): The key of the first `MenuNode` to jump
            to when starting the menu. Defaults to "START".
        endnode (str, optional): The key of the end node. When
            instructed to go to this node (by any means), the menu
            will be gracefully exited. Defaults to "END".
        exec_end (str, optional): If not `None`, this command name will be executed
            directly after the menu system has been exited. It is
            normally useful for making sure the user realizes their UI
            mode has changed.

        """
        self.tree = {}
        self.startnode = startnode
        self.endnode = endnode
        self.exec_end = exec_end
        self.caller = caller
        if nodes and utils.is_iter(nodes):
            for node in nodes:
                self.add(node)

    def start(self):
        """
        Initialize the menu and go to the starting node.

        """
        self.goto(self.startnode)

    def add(self, menunode):
        """
        Add a menu node object to the tree. Each node itself keeps
        track of which nodes it is connected to.

        Args:
            menunode (MenuNode): The node to add.
        """
        self.tree[menunode.key] = menunode

    def goto(self, key):
        """
        Go to a key in the tree. This sets up the cmdsets on the
        caller so that they match the choices in that node.

        Args:
            key (str): The node-key to go to.

        """
        if key == self.endnode:
            # if we was given the END node key, we clean up immediately.
            self.caller.cmdset.delete("menucmdset")
            del self.caller.db._menu_data
            if self.exec_end is not None:
                self.caller.execute_cmd(self.exec_end)
            return
        # not exiting, look for a valid node
        node = self.tree.get(key, None)
        # make caller available on node
        node.caller = self.caller
        if node:
            # call on-node callback
            if node.callback:
                try:
                    node.callback()
                except Exception:
                    logger.log_trace()
                    self.caller.msg("{rNode callback could not be executed for node %s. Continuing anyway.{n" % key)
            # initialize - this creates new cmdset
            node.init(self)
            # clean old menu cmdset and replace with the new one
            self.caller.cmdset.delete("menucmdset")
            self.caller.cmdset.add(node.cmdset)
            # set the menu flag data for the default commands
            self.caller.db._menu_data = {"help": node.helptext,
                                         "look": str(node.text)}
            # display the node
            self.caller.msg(node.text)
        else:
            self.caller.msg("{rMenu node '%s' does not exist - maybe it's not created yet..{n" % key)


class MenuNode(object):
    """
    This represents a node in a menu tree. The node will display its
    textual content and offer menu links to other nodes (the relevant
    commands are created automatically)

    """
    def __init__(self, key, text="", links=None, linktexts=None,
                 keywords=None, cols=1, helptext=None,
                 selectcmds=None, callback=None, nodefaultcmds=False, separator=""):
        """
        Initialize the node.

        Args:
            key (str): The unique identifier of this node.
            text (str, optional): The text that will be displayed at
                top when viewing this node.
        Kwargs:
            links (list): A liist of keys for unique menunodes this is connected to.
                The actual keys will not printed - keywords will be
                used (or a number)
            linktexts (list)- A list of texts to describe the links. Must
                match order of `links` list if defined. Entries can be
                None to not generate any extra text for a particular
                link.
            keywords (list): A list of unique keys for choosing links. Must
                match links list. If not given, index numbers will be
                used.  Also individual list entries can be None and
                will be replaed by indices. If CMD_NOMATCH or
                CMD_NOENTRY, no text will be generated to indicate the
                option exists.
            cols (int): How many columns to use for displaying options.
            helptext (str): If defined, this is shown when using the help command
                instead of the normal help index.
            selectcmds (list): A list of custom cmdclasses for
                handling each option.  Must match links list, but some
                entries may be set to None to use default menu cmds.
                The given command's key will be used for the menu list
                entry unless it's CMD_NOMATCH or CMD_NOENTRY, in which
                case no text will be generated. These commands have
                access to self.menutree and so can be used to select
                nodes.
            callback (function): Function callback. This will be
                called as callback(currentnode) just before this node is
                loaded (i.e. as soon as possible as it's been selected
                from another node).  currentnode.caller is available.
            nodefaultcmds (bool): If `True`, don't offer the default
                help and look commands in the node
            separator (str): This string will be put on the line
                between menu nodes.

        """
        self.key = key
        self.cmdset = None
        self.links = links
        self.linktexts = linktexts
        self.keywords = keywords
        self.cols = cols
        self.selectcmds = selectcmds
        self.callback = MethodType(callback, self, MenuNode) if callback else None
        self.nodefaultcmds = nodefaultcmds
        self.separator = separator
        Nlinks = len(self.links)

        # validate the input
        if not self.links:
            self.links = []
        if not self.linktexts or (len(self.linktexts) != Nlinks):
            self.linktexts = [None for i in range(Nlinks)]
        if not self.keywords or (len(self.keywords) != Nlinks):
            self.keywords = [None for i in range(Nlinks)]
        if not selectcmds or (len(self.selectcmds) != Nlinks):
            self.selectcmds = [None for i in range(Nlinks)]

        # Format default text for the menu-help command
        if not helptext:
            helptext = "Select one of the valid options ("
            for i in range(Nlinks):
                if self.keywords[i]:
                    if self.keywords[i] not in (CMD_NOMATCH, CMD_NOINPUT):
                        helptext += "%s, " % self.keywords[i]
                else:
                    helptext += "%s, " % (i + 1)
            helptext = helptext.rstrip(", ") + ")"
        self.helptext = helptext

        # Format text display
        string = ""
        if text:
            string += "%s\n" % text

        # format the choices into as many columns as specified
        choices = []
        for ilink, link in enumerate(self.links):
            choice = ""
            if self.keywords[ilink]:
                if self.keywords[ilink] not in (CMD_NOMATCH, CMD_NOINPUT):
                    choice += "{g{lc%s{lt%s{le{n" % (self.keywords[ilink], self.keywords[ilink])
            else:
                choice += "{g {lc%i{lt%i{le{n" % ((ilink + 1), (ilink + 1))
            if self.linktexts[ilink]:
                choice += " - %s" % self.linktexts[ilink]
            choices.append(choice)
        cols = [[] for i in range(min(len(choices), cols))]
        while True:
            for i in range(len(cols)):
                if not choices:
                    cols[i].append("")
                else:
                    cols[i].append(choices.pop(0))
            if not choices:
                break
        ftable = utils.format_table(cols)
        for row in ftable:
            string += "\n" + "".join(row)
        # store text
        self.text = self.separator + "\n" + string.rstrip()

    def init(self, menutree):
        """
        Called by menu tree. Initializes the commands needed by
        the menutree structure.
        """
        # Create the relevant cmdset
        self.cmdset = MenuCmdSet()
        if not self.nodefaultcmds:
            # add default menu commands
            self.cmdset.add(CmdMenuLook())
            self.cmdset.add(CmdMenuHelp())

        for i, link in enumerate(self.links):
            if self.selectcmds[i]:
                cmd = self.selectcmds[i]()
            else:
                # this is the operable command, it moves us to the next node.
                cmd = CmdMenuNode()
                cmd.key = str(i + 1)
                cmd.link = link
                def _callback(self):
                    self.menutree.goto(self.link)
                cmd.callback = MethodType(_callback, cmd, CmdMenuNode)
            # also custom commands get access to the menutree.
            cmd.menutree = menutree
            if self.keywords[i] and cmd.key not in (CMD_NOMATCH, CMD_NOINPUT):
                cmd.aliases = [self.keywords[i]]
            self.cmdset.add(cmd)

    def __str__(self):
        "Returns the string representation."
        return self.text


#
# A simple yes/no question. Call this from a command to give object
# a cmdset where they may say yes or no to a question. Does not
# make use the node system since there is only one level of choice.
#

def prompt_yesno(caller, question="", yesfunc=None, nofunc=None, default="N"):
    """
    This sets up a simple yes/no questionnaire. Question will be
    asked, followed by a Y/[N] prompt where the [x] signifies the
    default selection. Note that this isn't actually making use of the
    menu node system, but does use the MenuCmdSet.

    Args:
        caller (Object): The object triggering the prompt.
        question (str, optional): The Yes/No question asked.
        yesfunc (function, optional): Callback for a Yes answer.
        nofunc (functionm optional): Callback for a No answer.
        default (str, optional): Default used if caller just hits
            return. Either `"Y"` or `"N"`

    """

    # creating and defining commands
    cmdyes = CmdMenuNode(key="yes", aliases=["y"])
    if yesfunc:
        cmdyes.yesfunc = yesfunc
        def _yesfunc(self):
            self.caller.cmdset.delete('menucmdset')
            del self.caller.db._menu_data
            self.yesfunc(self)
        cmdyes.callback = MethodType(_yesfunc, cmdyes, CmdMenuNode)

    cmdno = CmdMenuNode(key="no", aliases=["n"])
    if nofunc:
        cmdno.nofunc = nofunc
        def _nofunc(self):
            self.caller.cmdset.delete('menucmdset')
            del self.caller.db._menu_data
            self.nofunc(self) if self.nofunc else None
        cmdno.callback = MethodType(_nofunc, cmdno, CmdMenuNode)

    errorcmd = CmdMenuNode(key=CMD_NOMATCH)
    def _errorcmd(self):
        self.caller.msg("Please choose either Yes or No.")
    errorcmd.callback = MethodType(_errorcmd, errorcmd, CmdMenuNode)

    defaultcmd = CmdMenuNode(key=CMD_NOINPUT)
    def _defaultcmd(self):
        self.caller.execute_cmd('%s' % default)
    defaultcmd.callback = MethodType(_defaultcmd, defaultcmd, CmdMenuNode)

    # creating cmdset (this will already have look/help commands)
    yesnocmdset = MenuCmdSet()
    yesnocmdset.add(cmdyes)
    yesnocmdset.add(cmdno)
    yesnocmdset.add(errorcmd)
    yesnocmdset.add(defaultcmd)
    yesnocmdset.add(CmdMenuLook())
    yesnocmdset.add(CmdMenuHelp())

    # assinging menu data flags to caller.
    caller.db._menu_data = {"help": "Please select Yes or No.",
                            "look": "Please select Yes or No."}
    # assign cmdset and ask question
    caller.cmdset.add(yesnocmdset)
    if default == "Y":
        prompt = "{lcY{lt[Y]{le/{lcN{ltN{le"
    else:
        prompt = "{lcY{ltY{le/{lcN{lt[N]{le"
    prompt = "%s %s: " % (question, prompt)
    caller.msg(prompt)


#
# A simple choice question. Call this from a command to give object
# a cmdset where they need to make a choice. Does not
# make use the node system since there is only one level of choice.
#

def prompt_choice(caller, question="", prompts=None, choicefunc=None, force_choose=False):
    """
    This sets up a simple choice questionnaire. Question will be
    asked, followed by a series of prompts. Note that this isn't
    making use of the menu node system but uses the MenuCmdSet.

    Args:
        caller (object): The object calling and being offered the choice
        question (str, optional): Text describing the offered choice
        prompts (list, optional): List of strings defining the available choises.
        choicefunc (function, optional): A function called as
            `choicefunc(self)` when a choice is made. Inside this function,
            `self.caller` is available and `self.prompt_index` is the index
            (starting with 0) matching the chosen prompt in the `prompts` list.
        force_choose - force user to make a choice

    Examples:

        ```python
            def mychoice(self):
                self.caller.msg("Index of choice is %s." % self.prompt_index)

            prompt_choice(caller, "Make a choice:", prompts=["A","B","C"], choicefunc=mychoice)
        ```

        When triggering the above from a command or @py prompt you get the following options:

        >>> Make a choice:
            [1] A
            [2] B
            [3] C
        <<< 2
        >>> Index of choice is 1.

    """

    # creating and defining commands
    count = 0
    choices = ""
    commands = []

    for choice in utils.make_iter(prompts):
        # create the available choice-commands
        count += 1
        choices += "\n{lc%d{lt[%d]{le %s" % (count, count, choice)

        cmdfunc = CmdMenuNode(key="%d" % count)
        cmdfunc.prompt_index = count-1
        if choicefunc:
            cmdfunc.choicefunc = choicefunc
            def _choicefunc(self):
                self.caller.cmdset.delete('menucmdset')
                del self.caller.db._menu_data
                self.choicefunc(self)
            # set a new method "callback" on cmdfunc
            cmdfunc.callback = MethodType(_choicefunc, cmdfunc, CmdMenuNode)

        commands.append(cmdfunc)

    if not force_choose:
        choices += "\n{lc{lt[No choice]{le"

    prompt = question + choices + "\nPlease choose one."

    # create the error-reporting command
    errorcmd = CmdMenuNode(key=CMD_NOMATCH)
    if force_choose:
        def _errorcmd(self):
            self.caller.msg("You can only choose given choices.")
    else:
        if choicefunc:
            errorcmd.choicefunc = choicefunc
            def _errorcmd(self):
                self.caller.msg("No choice.")
                self.caller.cmdset.delete('menucmdset')
                del self.caller.db._menu_data
                self.choicefunc(self)
    errorcmd.callback = MethodType(_errorcmd, errorcmd, CmdMenuNode)

    # create the fallback command
    defaultcmd = CmdMenuNode(key=CMD_NOINPUT)
    if force_choose:
        def _defaultcmd(self):
            caller.msg(prompt)
    else:
        if choicefunc:
            defaultcmd.choicefunc = choicefunc
            def _defaultcmd(self):
                self.caller.msg("No choice.")
                self.caller.cmdset.delete('menucmdset')
                del self.caller.db._menu_data
                self.choicefunc(self)
    defaultcmd.callback = MethodType(_defaultcmd, defaultcmd, CmdMenuNode)

    # creating cmdset (this will already have look/help commands)
    choicecmdset = MenuCmdSet()
    for cmdfunc in commands:
        choicecmdset.add(cmdfunc)
    choicecmdset.add(errorcmd)
    choicecmdset.add(defaultcmd)
    choicecmdset.add(CmdMenuLook())
    choicecmdset.add(CmdMenuHelp())

    # assigning menu data flags to caller.
    caller.db._menu_data = {"help": "Please select.",
                            "look": prompt}

    # assign cmdset and ask question
    caller.cmdset.add(choicecmdset)
    caller.msg(prompt)


#
# Menu command test
#

class CmdMenuTest(Command):
    """
    testing menu module

    Usage:
      menu
      menu yesno

    This will test the menu system. The normal operation will produce
    a small menu tree you can move around in. The 'yesno' option will
    instead show a one-time yes/no question.

    """

    key = "menu"
    locks = "cmd:all()"
    help_category = "Menu"

    def func(self):
        "Testing the menu system"

        if self.args.strip() == "yesno":
            "Testing the yesno question"
            prompt_yesno(self.caller, question="Please answer yes or no - Are you the master of this mud or not?",
                         yesfunc=lambda self: self.caller.msg('{gGood for you!{n'),
                         nofunc=lambda self: self.caller.msg('{GNow you are just being modest ...{n'),
                         default="N")
        else:
            # testing the full menu-tree system

            node0 = MenuNode("START", text="Start node. Select one of the links below. Here the links are ordered in one column.",
                             links=["node1", "node2", "END"], linktexts=["Goto first node", "Goto second node", "Quit"])
            node1 = MenuNode("node1", text="First node. This node shows letters instead of numbers for the choices.",
                             links=["END", "START"], linktexts=["Quit", "Back to start"], keywords=["q","b"])
            node2 = MenuNode("node2", text="Second node. This node lists choices in two columns.",
                             links=["node3", "START"], linktexts=["Set an attribute", "Back to start"], cols=2)
            node3 = MenuNode("node3", text="Attribute 'menutest' set on you. You can examine it (only works if you are allowed to use the examine command) or remove it. You can also quit and examine it manually.",
                             links=["node4", "node5", "node2", "END"], linktexts=["Remove attribute", "Examine attribute",
                                                                                  "Back to second node", "Quit menu"], cols=2,
                             callback=lambda self: self.caller.attributes.add("menutest",'Testing!'))
            node4 = MenuNode("node4", text="Attribute 'menutest' removed again.",
                             links=["node2"], linktexts=["Back to second node."], cols=2,
                             callback=lambda self: self.caller.attributes.remove("menutest"))
            node5 = MenuNode("node5", links=["node4", "node2"], linktexts=["Remove attribute", "Back to second node."], cols=2,
                    callback=lambda self: self.caller.msg('%s/%s = %s' % (self.caller.key, 'menutest', self.caller.db.menutest)))

            menu = MenuTree(self.caller, nodes=(node0, node1, node2, node3, node4, node5))
            menu.start()
