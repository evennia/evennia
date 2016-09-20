"""
Commands for the aisystem. They allow for navigating, studying and
modifying behavior trees.
"""
import re
import string
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from evennia import CmdSet, ScriptDB, create_script
from evennia.utils import evmore
from evennia.utils.dbserialize import _SaverList, _SaverDict
from evennia.commands.command import Command
from evennia.contrib.aisystem.typeclasses import (BehaviorTree, 
    AIObject, AIScript, AIPlayer)
from evennia.contrib.aisystem.nodes import CompositeNode


class AICmdSet(CmdSet):
    """CmdSet for action-related commands."""
    key = "ai_cmdset"
    priority = -20

    def at_cmdset_creation(self):
        self.add(CmdList())
        self.add(CmdNewTree())
        self.add(CmdRenameTree())
        self.add(CmdDelTree())
        self.add(CmdAssign())
        self.add(CmdGo())
        self.add(CmdBB())
        self.add(CmdStatus())
        self.add(CmdUp())
        self.add(CmdDown())
        self.add(CmdLook())
        self.add(CmdSetAttr())
        #self.add(CmdWatch())
        #self.add(CmdAdd())
        #self.add(CmdMove())
        #self.add(CmdAddIn())
        #self.add(CmdMoveIn())
        #self.add(CmdSwap())
        #self.add(CmdShift())
        #self.add(CmdRemove())


def check_is_aiplayer(caller):
    """
    Returns True if the caller's player is subclassed from AIPlayer,
    else messages the caller and returns False
    """
    if isinstance(caller.player, AIPlayer):
        return True
    else:
        caller.msg("{0} does not have the ".format(caller.player.name) +
            "AIPlayer typeclass. The command cannot proceed. Please set " +
            "the player's typeclass to AIPlayer in the code, possibly by " +
            "subclassing your game's Player typeclass from AIPlayer.")
        return False



def check_is_browsing(player, msg):
    if not player.aiwizard.tree:
        player.msg("You are not currently browsing any tree " +
            "and so cannot {0}.").format(msg)
        return False
    if not player.aiwizard.node:
        player.msg("You are not currently browsing any node " +
            "and so cannot {0}.").format(msg)
        return False
    return True


def check_is_browsing_blackboard(caller, msg):
    if not player.aiwizard.blackboard:
        player.msg("You are not currently browsing any blackboard " +
            "and so cannot {0}.").format(msg)
        return False


def tree_from_name(caller, name):
    """
    If there is a single tree in the database that has the given id or name, 
    returns that tree, else returns None

    msg can be a string set to either 'source', 'target' or '' if a
    message is intended to be sent. Setting msg to None prohibits sending
    a success message to the caller.
    """
    if name == 'this':
        # check that a tree is currently being browsed
        if self.caller.player.aiwizard.tree:
            tree = self.caller.player.aiwizard.tree
        else:
            self.caller.msg("You are not currently browsing any tree, " +
                "and so you cannot specify a tree via the 'this' " +
                "keyword. To move the browsing cursor to a given tree, " +
                "use the @aigo command.")
            return None

    # check whether the name is a database id
    elif all([x in string.digits for x in name]):
        tree = ScriptDB.objects.get_id(name)
        if not tree:
            self.caller.msg("No tree with the specified database id of " +
                "{0} has been found. Please check the list of available " +
                "trees using the @ailist command.")
            return None
    else:
        # check that a tree with the specified name actually exists
        # and that the name does not belong to multiple scripts
        try:
            tree = ScriptDB.objects.get(db_key=name)
        except ObjectDoesNotExist:
            caller.msg("No tree with the name {0} has been ".format(name) +
                "found in the database. Please check the list of available " +
                "trees using the @ailist command.")
            return None 
        except MultipleObjectsReturned:
            caller.msg("Multiple scripts with the name {0} have ".format(name) +
                "been found in the database. Please use the target tree's id " +
                "instead.") 
            return None

    return tree


def node_from_name(caller, tree, name):
    """
    If there is a single node in the tree's nodes registry that has the given 
    hash or name, returns that node, else returns None
    """
    nodes = [x for x in tree.nodes.values() if x.name == name]

    # first check if the name is a hash in the tree's registry 
    hashval = name + "_" + str(tree.id)
    if hashval in tree.nodes.keys():
        node = tree.nodes[hashval]
        return node

    elif len(nodes) == 1:
        # a node was found with the given name
        node = nodes[0]
        return node

    elif len(nodes) == 0:
        # no node was found with the given hash or name
        caller.msg("No node was found with either the name or hash of " +
            "{0}.".format(name))
        return None

    else:
        # multiple nodes were found with the given name.
        s = ("Multiple nodes were found with the name {0}, ".format(name) +
            "with the hashes:\n")
        for node in nodes:
            s += node.hash[0:3] + "\n"
        s += ("Please re-input your command, specifying one of these hashes " +
            "instead of the desired node's name. To inspect these nodes, " +
            "use the @ailook command, or browse them using the @aigo command.")
        evmore.msg(self.caller, s)
        return None


def bb_from_name(caller, obj_type, name):
    """
    Attempts to acquire the AI blackboard of an object whose type and whose 
    database key or id have been provided.
    """
    # check if the name is a database id
    if obj_type == AIObject:
        db = ObjectDB
        obj_type_name = "object"
    else:
        db = ScriptDB
        obj_type_name = "script"

    if all([x in string.digits for x in name]):
        obj = db.objects.get_id(name)
        if obj:
            return obj.db.ai
        else:
            caller.msg("No blackboard with the id {0} has been ".format(name) +
                "found in the database.")
            return None

    # check if the name belongs to any object of the appropriate type
    # in the database    
    try: 
        obj = scriptDB.get(db_key = name)
    except ObjectDoesNotExist:
        caller.msg("No blackboard with the name {0} has been ".format(name) +
            "found in the database.")
        return None

    except MultipleObjectsReturned:
        caller.msg("Multiple {0}s with the name ".format(obj_type_name) +
            "{0} have been found in the database. Please use ".format(name) +
            " the target tree's id instead.")
        return None

    return obj.db.ai


# The indentation used by the various display functions
s_indent = "    "


def display_node_in_tree(caller, tree, node):
    """
    Displays information pertaining to a given node in a tree:
    its tree, the name and hash values of its parent and children, as well as
    its attributes
    """
    # get the node's parent
    if node.parent:
        parent = "'{0}'(\"{1}\")".format(node.parent.hash[0:3],
            node.parent.name)
    else:
        parent = "None"
    
    # get the node's children
    if isinstance(node, CompositeNode):
        children = [x.name for x in node.children]
    elif node.children:
        children = "'{0}'(\"{1}\")".format(node.children.hash[0:3],
            node.children.name)
    else:
        children = "None"

    # get the node's attributes
    attrs = [x for x in dir(node) if x[0] != '_']

    # do not include the node's name amongst its attributes
    attrs.remove('name')

    nonfuncs = {}
    for attr_name in attrs:
        attr = getattr(node, attr_name)
        if not hasattr(attr, '__call__'):
            nonfuncs[attr_name] = attr

    s = "|yNode|n '{0}'(\"{1}\")\n".format(node.hash[0:3], node.name)
    s += "-" * (len(s) - 5) + "\n" #accounting for the formatting characters
    s += "|yTree:|n {0} (id {1})\n".format(tree.name, tree.id)
    s += "|yParent:|n {0}\n".format(parent)
    if isinstance(children, str):
        s += "|yChild:|n {0}\n".format(children)
    else:
        s += "|yChildren:|n\n"
        for child in children:
            s += s_indent + "'{0}'(\"{1}\")".format(child.hash[0:3], 
                child.name)
            
    s += "\n|yAttributes:|n\n"
    for attr_name, attr in nonfuncs.iteritems():
        if attr_name not in ['tree', 'hash', 'children', 'parent']:
            s += parse_attr(attr_name, attr, 1)

    evmore.msg(caller, s)


def display_node_in_bb(caller, tree, node, bb):
    """
    Displays information pertaining to a given instance of a node in a
    blackboard: the node's tree, the owner of the blackboard itself,
    the name and hash values of the node's parent and children, as well
    as the node instance's current attributes
    """
    data = bb['nodes'][node.hash]

    # get the node's parent
    if node.parent:
        parent = "'{0}'(\"{1}\")".format(node.parent.hash[0:3], 
            node.parent.name) 
    else:
        parent = None

    # get the node's children
    if isinstance(node, CompositeNode):
        children = [x.name for x in node.children]
    elif node.children:
        children = "'{0}'(\"{1}\")".format(node.parent.hash[0:3],
            node.children.name)
    else:
        children = "None"
    
    if isinstance(bb['agent'], AIObject):
        owner_type = "AI agent"
        owner_name = bb['agent'].name
    elif isinstance(bb['agent'], AIScript):
        owner_type = "AI script"
        owner_name = bb['agent'].name
    else:
        owner_type = type(bb['agent'])
        owner_name = str(bb['agent'])

    s = "|gNode instance|n of '{0}'(\"{1}\")\n".format(node.hash[0:3], 
        node.name)
    s += "-" * len(s)
    s += "|gTree:|n {0} (id {1})\n".format(tree.name, tree.id)
    s += "|g{0}:|n {1}\n".format(owner_type, owner_name)
    s += "|gParent:|n {0}\n".format(parent)
    if isinstance(children, str):
        s += "|gChild:|n {0}\n".format(children)
    else:
        s += "|gChildren:|n\n"
        for child in children:
            s += s_indent + "'{0}'(\"{1}\")".format(child.hash[0:3], 
                child.name)

    s += "\n|gData:|n\n"
    for key, val in data:
        s += parse_attr(key, val, 1)

    evmore.msg(caller, s)


def display_bb_globals(caller, bb):
    """
    Displays the global parameters of the currently browsed blackboard
    """
    if isinstance(bb['agent'], AIObject):
        owner_type = "AI agent"
        owner_name = bb['agent'].name
    elif isinstance(bb['agent'], AIScript):
        owner_type = "AI script"
        owner_name = bb['agent'].name
    else:
        owner_type = type(bb['agent'])
        owner_name = str(bb['agent'])

    s = "Blackboard globals for |g{0}|n {1}:".format(owner_type, owner_name)
    for key, val in bb['globals'].iteritems():
        s += parse_attr(key, val, 1)
        
    evmore.msg(caller, s)


def parse_attr(attr_name, attr, indent):
    """
    Parse a given attribute into a string and return it.
    This function is meant to be recursive in the event that the attribute
    is a string or an int.

    Reports lists and SaverLists as 'list', sets and tuples as 'tuple',
    dicts and SaverDicts as 'dict'.
    """
    s = ""
    k_indent = s_indent * indent # current level of indentation
    if (isinstance(attr, list) or isinstance(attr, _SaverList)):
        if attr_name:
            s += k_indent + "List {0}:\n".format(attr_name)
        else:
            s += k_indent + "List:"
        s += k_indent + "[\n"
        for val in attr:
            s += parse_attr("", val, indent + 1)
        s += k_indent + "]\n"
        return s

    elif isinstance(attr, set) or isinstance(attr, tuple):
        if attr_name:
            s += k_indent + "Tuple {0}:\n".format(attr_name)
        else:
            s += k_indent + "Tuple:"
        s += k_indent + "(\n"
        for val in attr:
            s += parse_attr("", val, indent + 1)
        s += k_indent + ")\n"
        return s

    elif isinstance(attr, dict) or isinstance(attr, _SaverDict):
        if attr_name:
            s += k_indent + "Dict {0}:\n".format(attr_name)
        else:
            s += k_indent + "Dict:"
        s += k_indent + "{\n"
        for key, val in attr.iteritems():
            s += parse_attr(key, val, indent + 1)
        s += k_indent + "}\n"
        return s

    else:
        if attr_name:
            return k_indent + "{0}: {1}\n".format(attr_name, attr)
        else:
            return k_indent + str(attr) + "\n"


class CmdList(Command):
    """
    Lists the names of all AI trees in the game, as well as the
    number of nodes each of them contains

    Usage:
        @ailist
        @aili
    """
    key = "@ailist"
    aliases = ['@aili']
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"

    def func(self):
        s = ""
        trees = [x for x in ScriptDB.objects.all() 
            if isinstance(x, BehaviorTree)]

        for tree in trees:
            s += tree.name + " ({0} nodes)".format(str(len(tree.nodes)))

        if not s:
            s = "No behavior trees were found."
        
        evmore.msg(self.caller, s)


class CmdNewTree(Command):
    """
    Generates a new tree with the given name. The name must not contain
    single quotes (the ' symbol).

    Usage:
        @ainewtree <tree name>
    """
    key = "@ainewtree"
    aliases = []
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        # check that a name has been provided
        name = self.args.strip()
        if not name:
            self.caller.msg("Please provide a name for the new tree.")
            return False

        if "'" in name:
            self.caller.msg("Please provide a name that does not contain " +
                "single quotes.")
            return False

        # check that the tree's name does not have the format of a database id
        if all([x in string.digits for x in name]):
            self.caller.msg("The name you provided is made entirely of " +
                "digits. You must supply a name that contains other types " +
                "of characters as well.")
            return False

        # check that a tree with the same name does not already exist
        tree_exists = True if [x for x in ScriptDB.objects.all() 
            if x.name == name] else False
        if tree_exists:
            self.caller.msg("A script with the name {0} has ".format(args) +
                "already been found. Cannot create a new tree with the " +
                "same name.")
            return False

        # create the new tree
        tree = create_script(BehaviorTree, key=name)
        self.caller.msg("Tree \"{0}\" with database id  ".format(name) +
            "{0} created.".format(tree.id))
        return True


class CmdRenameTree(Command):
    """
    Renames a given tree. To identify the tree, its original name or its
    database id can be specified. If the original name specified for the
    tree is 'this', the tree to be renamed is considered to be the currently
    browsed tree.

    Usage:
        @airenametree '<original tree name>' '<new tree name>'

    Example:
        @airenametree 'fighter AI' 'warrior AI'
        @airenametree '216' 'warrior AI'
        @airenametree 'this' 'warrior AI'

    The <tree name> and <new tree name> |w*must*|n be enclosed in single quotes.
    """
    key = "@airenametree"
    aliases = []
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        # check that the original name and the new name have been provided
        names = re.findall(r"'[^']*'", self.args)
        if len(names) == 0:
            self.caller.msg("You have provided no names. You must provide " +
                "the original name of the tree as well as its new name, " +
                "both enclosed in single quotes (the ' symbol).")
            return False
        elif len(names) == 1:
            self.caller.msg("You have provided only one name. You must " +
                "provide the original name of the tree as well as its new " +
                "name, both enclosed in single quotes (the ' symbol).")
            return False
            
        # strip the names of their single quotes
        old_name = names[0][1:len(names[0]) - 1]
        new_name = names[1][1:len(names[1]) - 1]

        tree = tree_from_name(self.caller, old_name)
        if not tree:
            return False

        # give the tree the new name.
        tree.key = new_name
        self.caller.msg("Tree '{0}' successfully renamed ".format(old_name) +
            "to '{0}'.".format(new_name))
        return True


class CmdDelTree(Command):
    """
    Delete a given tree completely, removing it from the database. You may
    specify the tree via its name, its database id or the keyword 'this'. If
    the specified tree name is 'this', the currently browsed tree will be
    deleted.

    Usage:
        @aideltree <tree name>

    Examples:
        @aideltree fighter AI
        @aideltree 47
        @aideltree this

    The <tree name> must |rnot|n be enclosed in single quotes.
    """
    key = "@aideltree"
    aliases = []
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        name = self.args.strip()
        if not name:
            self.caller.msg("Please specify the name of the tree to be " +
                "deleted.")
            return False

        if "'" in name:
            self.caller.msg("Please specify a name that does not contain " +
                "single quotes.")
            return False

        tree = tree_from_name(self.caller, name)
        if not tree:
            return False

        if self.caller.player.aiwizard.tree == tree:
            self.caller.player.aiwizard.node = ''
            # aiwizard.tree gets set to None automatically after deletion,
            # no need to set it here

        #[WIP] Take the tree's nodes out of every watch list


        self.caller.msg("Tree '{0}'(\"{1}\") deleted.".format(tree.id,
            tree.name))
        tree.delete()
        return True


class CmdAssign(Command):
    """
    Assign a given tree to a given AIAgent or AIScript. You can use the 'this'
    keyword as the tree's name to refer to the currently browsed tree.
    If specifying an id rather than a name for the tree, object or script, the
    id number should not be preceded with the hash symbol '#' (e.g. use '12' 
    instead of '#12') 

    Usage:
        @aiassign <tree name> <object|script> <id or name of object/script>

    Examples:
        @aiassign 'fighter AI' object '13'
        @aiassign '82' object 'big orc masher'
        @aiassign 'strategy AI' script 'the orcs'
        @aiassign 'this' script '235'

    """
    key = "@aiassign"
    aliases = []
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        pass


class CmdGo(Command):
    """
    Set the current AI browsing cursor to a given tree and/or node. You must 
    specify the name or database id of the AI tree you intend to go to, placing
    this name or id in single quotes. If you intend to go to the same tree you
    are currently browsing, use the name 'this'. You may also specify the
    three-character hash value or name of a node that you intend to browse, 
    placing either of these in single quotes. If no such node is provided,
    your browsing cursor will automatically be placed at root node.

    Usage:
        @aigo '<tree>' '<node>'

    Examples:
        @aigo 'fighter AI'
        @aigo '315' 'bash them all'
        @aigo 'fighter AI' 'x9F'
        @aigo 'this' 'root'
    """
    key = "@aigo"
    aliases = []
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"
    
    def func(self):
        if not check_is_aiplayer(self.caller):
            return False

        names = re.findall(r"'[^']*'", self.args)

        if len(names) == 0:
            self.caller.msg("You have not provided the name of the tree " +
                "to which you wish to go. Please provide it, ensuring " +
                "it is placed between single quotes (the ' symbol).")
            return False

        # strip the names of their single quotes
        tree_name = names[0][1:len(names[0]) - 1]
        if len(names) > 1:
            node_name = names[1][1:len(names[1]) - 1]
        else:
            node_name = None

        tree = tree_from_name(self.caller, tree_name)
        if not tree:
            return False

        if self.caller.player.aiwizard.tree == tree:
            already_at_tree = True
        else:
            self.caller.player.aiwizard.tree = tree
            already_at_tree = False

        if node_name != None:            
            # obtain the node if a valid one was provided.
            node = node_from_name(self.caller, tree, node_name)

            if node:
                if self.caller.player.aiwizard.node == node.hash:
                    self.caller.msg("Already browsing tree " +
                        "'{0}', node '{1}'(\"{2}\")".format(tree.name,
                        node.hash[0:3], node.name))
                else:
                    self.caller.player.aiwizard.node = node.hash
                    self.caller.msg("Successfully moved to tree " +
                        "'{0}', node '{1}'(\"{2}\")".format(tree.name, 
                        node.hash[0:3], node.name))
                return True
        else:
            node = tree.root

        if already_at_tree:
            if self.caller.player.aiwizard.node == node.hash:
                self.caller.msg("Already browsing tree '{0}'.".format(
                    tree.name))
            else:
                self.caller.msg("Already browsing tree '{0}'. ".format(
                    tree.name) + "Moving to root node.")
                self.caller.player.aiwizard.node = node.hash
            return True
        else:
            self.caller.msg("Successfully moved to tree '{0}'.".format(
                tree.name))
            self.caller.player.aiwizard.node = node.hash
            return True


class CmdBB(Command):
    """
    Moves the browsing cursor to the blackboard of a specified target object
    or script. The browsing cursor can be located at a given tree and node at 
    the same time as it is located at a given blackboard.

    The target's name can be an id or a name. It |w*must*|n be enclosed in
    single quotes (the ' symbol).

    Usage:
        @aibb <object|script> '<target name>'

    Examples:
        @aibb object 'George'
        @aibb object '63'
        @aibb script 'hivemind of the dark ones'
        @aibb script '584'
    """
    key = "@aibb"
    aliases = []
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"
   
    def func(self):
        args = self.args.strip()
        names = re.findall(r"'[^']*'", self.args)

        if 'object' in args:
            obj_type = AIObject
            obj_type_name = 'object'
        elif 'script' in args:
            obj_type = AIScript
        else:
            self.caller.msg("Could not find the keyword 'object' or 'script' " +
                "among the arguments of the @aibb command. You must " +
                "specify one of these keywords, without the single quotes.") 
            return False
        if not names:
            self.caller.msg("Could not find the name or id of the target " +  
                "in the arguments list. You must specify the name or id, in " +
                "single quotes, of the object or script whose blackboard " +
                "you wish to browse.")
            return False
        name = names[0][1:len(names[0]) - 1]        

        bb = bb_from_name(self.caller, obj_type, name)
        if not bb:
            return False

        if self.caller.player.aiwizard.blackboard == bb:
            self.caller.msg("Already browsing the blackboard of {0} ".format(
                obj_type_name) + "\"{0}\" (id {1}).".format(bb['agent'].name,
                bb['agent'].id))
            return True

        self.caller.player.aiwizard.blackboard = bb
        self.caller.msg("Switched to the blackboard of {0} ".format(
            obj_type_name) + "\"{0}\" (id {1}).".format(bb['agent'].name,
                bb['agent'].id))
        return True


class CmdStatus(Command):
    """
    Display the currently browsed tree, node and blackboard, as well as all
    the nodes currently being watched by the player.

    Usage:
        @aistatus
    """
    key = "@aistatus"
    aliases = []
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        wiz = self.caller.player.aiwizard
        if wiz.tree:
            s_tree = "'{0}' (id '{1}')\n".format(wiz.tree.name, wiz.tree.id)
        else:
            s_tree = "None\n"

        if wiz.node:
            node_name = wiz.tree.nodes[wiz.node]
            s_node = "'{0}'(\"{1}\")\n".format(wiz.node[0:3], node_name)
        else:
            s_node = "None\n"

        if wiz.blackboard:
            s_agent = "{0} (id '{1}')\n".format(wiz.blackboard['agent'].name,
                wiz.blackboard['agent'].id)
        else:
            s_agent = "None\n"

        s = "|wTree:|n " + s_tree
        s += "|wNode:|n " + s_node
        s += "|wAgent:|n " + s_agent
        if wiz.watching:
            s += "|wWatch list|n:\n"
        else:
            s += "|wWatch list|n: None"

        for watched in wiz.watching:
            watched_tree = ScriptDB.get_id(watched.tree)
            s += s_indent + "'{0}'(\"{1}\") ".format(watched.hash[0:3],
                watched.name) + "in tree {0} (id {1})".format(watched_tree.name,
                watched_tree.id)

        evmore.msg(self.caller, s)


class CmdUp(Command):
    """
    Moves the AI browsing cursor to the currently browsed node's parent.

    Usage:
        @aiup
    """
    key = "@aiup"
    aliases = []
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        # check that a node is currently being browsed
        check_is_browsing(self.caller.player, "go up from the current node")

        tree = self.caller.player.aiwizard.tree
        node = self.caller.player.aiwizard.node

        # check that the node being browsed has a parent
        if not node.parent:
            self.caller.msg("The currently browsed node " +
                "'{0}'(\"{1}\") on tree ".format(node.hash[0:3], node.name) +
                "'{0}'".format(tree.name) + "does not have a parent." +
                "You cannot browse upwards from it.")        
            return False

        self.caller.player.aiwizard.node = node.parent.hash
        
        display_node_in_tree(self.caller, tree, node.parent)
        return True

class CmdDown(Command):        
    """
    Moves the AI browsing cursor to the specified child of the currently 
    browsed node. If the node has only one child, you do not need to input
    an argument.

    If you specify a name or hash rather than a number as the argument, you 
    must put this name between single quotes (the ' symbol). If, however,
    you specify a number as the argument, it must not be put between single
    quotes.

    Usage:
        @aidown <number, hash or name of child>

    Examples:
        @aidown 1
        @aidown 'xQ4'
        @aidown 'bash them all'
    """
    key = "@aidown"
    aliases = []
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        child_name = self.args.strip()

        # check that a node is currently being browsed
        check_is_browsing(self.caller.player, "go down from the current node")

        tree = self.caller.player.aiwizard.tree
        node = self.caller.player.aiwizard.node

        # check that the node being browsed has children
        if not node.children:
            self.caller.msg("Node '{0}'(\"{1}\") ".format(node.hash[0:3],
                node.name) + "of tree {0}(\"{1}\") ".format(tree.id, 
                tree.name) + " has no children to which to descend.")

        if isinstance(node, CompositeNode):
            if len(node.children) != 1 and not child_name:
                s = ("Node '{0}'(\"{1}\") ".format(node.hash[0:3],
                    node.name) + "is a composite node. Please specify one " +
                    "of its children in your command:\n")
                for k_child in node.children:
                    s += s_indent + "'{0}'(\"{1}\")\n".format(
                        k_child.hash[0:3], k_child.name)
                evmore.msg(self.caller, s)
                return False

            elif len(node.children) == 1:
                child = node.children[0]

            else:
                hashval = child_name + "_" + node.tree

                # check if the name is an index
                if all([x in string.digits for x in child_name[1:]]) and (
                    child_name[0] == "-" or child_name[0] in string.digits):
                    try:
                        child = node.children[int(child_name)]
                    except IndexError:
                        self.caller.msg("The node '{0}'(\"{1}\") ".format(
                            node.hash[0:3], node.name) + "does not have " +
                            "a child at index {0}. ".format(child_name) +
                            "Cannot perform descent.")
                    return False

                # check if the name is a hash
                elif hashval in [x.hash for x in node.children]:
                    child = [x for x in node.children if x.hash == hashval][0]

                elif child_name in [x.name for x in node.children]:
                    # get the child from its name
                    children = [x for x in node.children 
                        if x.name == child_name]
                    if len(children) == 1:
                        child = children[0]
                    else:
                        s = ("Multiple children of node '{0}'(\"{1}\") ".format(
                            node.hash[0:3], node.name) + "share the name of " +
                            "{0}. Please choose from ".format(child_name) +
                            "among these hashes:\n")
                        for k_child in children:
                            s += s_indent + "'{0}'\n".format(k_child.hash[0:3])
                        return False                            
                else:
                    self.caller.msg("Node '{0}'(\"{1}\")".format(
                        node.hash[0:3], node.name) + " has no children " +
                        "with a hash or name of {0}.".format(child_name) +
                        "Cannot perform descent.")
                    return False
        else:
            child = node.children

        self.caller.player.aiwizard.node = child.hash
        
        display_node_in_tree(self.caller, tree, node.parent)
        return True


class CmdLook(Command):
    """
    Displays the name and hash value, the tree, parent, children (if any) and
    attributes of either the currently browsed node or a specified node in
    this tree or a given tree. You may specify the name of the tree and node
    to be looked at by putting the id or name of the tree, as well as the id or
    name of the node, in single quotes (the ' symbol). If the tree name 'this'
    is provided, the node is considered to be in the current tree. If no node
    or tree name is specified, the currently browsed node is displayed. 

    If the bb argument is specified, the node instance's blackboard data and 
    associated AI agent are displayed instead of the node's attributes.

    If the globals argument is specified, the global blackboard data of the
    currently browsed blackboard will be displayed.

    Usage:
        @ailook
        @ailook '<tree name>' '<node name>'
        @ailook bb
        @ailook bb '<tree name>' '<node name>'
        @ailook globals

    Examples:
        @ailook 'this' 'x1J'
        @ailook '45' 'bash them all'
        @ailook bb 'fighter AI' 'bash them all'

    The <tree name> and <node name> |w*must*|n be enclosed in single quotes.
    """
    key = "@ailook"
    aliases = []
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        args = [x for x in self.args.split(" ") if x]
        names = re.findall(r"'[^']*'", self.args)

        if args == "globals":
            # check whether a blackboard is currently being browsed
            msg = ("look at any global blackboard data unless you first move " +
                "to a blackboard via the '@aigo <agent|script> " +
                "<agent/script name>' command.")
            if not check_is_browsing_blackboard(self.caller.player, msg):
                return False
            display_bb_globals(self.caller, 
                self.caller.player.aiwizard.blackboard)
            return True

        if len(names) == 1:
            self.caller.msg("You have specified either the name of a tree " +
                "or the name of a node, but not both. Either specify both or " +
                "specify none.")
            return False
        elif names:
            # get the name of the tree and node to be looked at
            tree_name = names[0][1:len(names[0]) - 1]
            node_name = names[1][1:len(names[1]) - 1]

            tree = tree_from_name(self.caller, tree_name)
            if not tree:
                return False

            node = node_from_name(self.caller, tree, node_name)
            if not node:
                return False

        else:
            # check whether a tree and node are currently being browsed
            msg = ("use the @ailook command without arguments unless you " +
                "first move to a node via the @aigo command.")
            if not check_is_browsing(self.caller.player, msg):
                return False
            tree = self.caller.player.aiwizard.tree
            node = tree.nodes[self.caller.player.aiwizard.node]

        if "bb" in args:
            # check whether a blackboard is being browsed
            msg = ("use the @ailook command with the bb argument unless you " +
                "first move to a blackboard via the '@aigo <agent|script> " +
                "<agent/script name>' command.")
            if not check_is_browsing_blackboard(self.caller.player, msg):
                return False
            bb = self.caller.player.aiwizard.blackboard
            display_node_in_bb(self.caller, tree, node, bb)
            return True
        else:
            display_node_in_tree(self.caller, tree, node)
            return True


class CmdSetAttr(Command):
    pass






