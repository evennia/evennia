"""
Commands for looking over trees, nodes and blackboards in the AI system, as
well as browsing through them.
"""

import re
import string
from evennia import CmdSet, ObjectDB, ScriptDB
from evennia.utils import evmore
from evennia.commands.command import Command
from evennia.contrib.aisystem.typeclasses import (
    BehaviorTree, AIObject, AIScript)
from evennia.contrib.aisystem.nodes import CompositeNode
from evennia.contrib.aisystem.utils import (
    is_aiplayer, is_browsing, is_browsing_blackboard, is_agent_set_up,
    is_node_in_bb, tree_from_name, node_from_name, agent_from_name,
    s_indent, display_node_in_tree, display_node_in_bb, display_bb_globals)

#[WIP] display_node_in_tree for @aigo!!!
#[WIP] cover tree deletion and node removal in the watch / unwatch tests

class AIViewCmdSet(CmdSet):
    """CmdSet for Behavior Tree AI viewing commands."""
    key = "ai_view_cmdset"
    priority = -20

    def at_cmdset_creation(self):
        self.add(CmdList())
        self.add(CmdLook())
        self.add(CmdStatus())
        self.add(CmdWatch())
        self.add(CmdUnwatch())
        self.add(CmdGo())
        self.add(CmdBB())
        self.add(CmdUp())
        self.add(CmdDown())


class CmdList(Command):
    """
    Lists the names of all AI trees in the game, as well as the
    number of nodes each of them contains

    Usage:
        @ailist
        @aili

    See also:
        @aistatus @ailook @aiwatch
    """
    key = "@ailist"
    aliases = ['@aili']
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        s = ""
        trees = [
            x for x in ScriptDB.objects.all() if isinstance(x, BehaviorTree)]

        for tree in trees:
            s += tree.name + " ({0} nodes), ".format(str(len(tree.nodes)))

        if not s:
            s = "No behavior trees were found."
        else:
            s = s[:-2]

        evmore.msg(self.caller, s)


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

    The <tree name> and <node name> |w*must*|n be enclosed in single quotes.

    Usage:
        @ailook
        @ailook '<tree name>' '<node name>'
        @ailook bb
        @ailook bb '<tree name>' '<node name>'
        @ailook globals

    Examples:
        @ailook 'this' 'x1J'
        @ailook '45' 'bash them all'
        @ailook bb 'fighter tree' 'bash them all'

    See also:
        @ailist @aistatus @aiwatch
    """
    key = "@ailook"
    aliases = []
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        if not is_aiplayer(self.caller):
            return False

        names = re.findall(r"(?:\b\w+\b)|(?:'[^']*')", self.args)

        if names and names[0] == "globals":
            # check whether a blackboard is currently being browsed
            msg = (
                "look at any global blackboard data unless you first move " +
                "to a blackboard via the '@aibb command")
            if not is_browsing_blackboard(self.caller.player, msg):
                return False
            display_bb_globals(
                self.caller, self.caller.player.aiwizard.agent.ai.data)
            return True

        if len(names) == 1 and names[0] != "globals" and names[0] != "bb":
            self.caller.msg(
                "You have specified either the name of a tree " +
                "or the name of a node, but not both. Either specify both " +
                "or specify none.")
            return False
        elif len(names) > 1:
            # get the name of the tree and node to be looked at
            if names[0] == "bb":
                tree_name = names[1][1:-1]
                node_name = names[2][1:-1]
            else:
                tree_name = names[0][1:-1]
                node_name = names[1][1:-1]

            tree = tree_from_name(self.caller, tree_name)
            if not tree:
                return False

            node = node_from_name(self.caller, tree, node_name)
            if not node:
                return False

        else:
            # check whether a tree and node are currently being browsed
            msg = (
                "use the @ailook command without arguments unless you " +
                "first move to a node via the @aigo command")
            if not is_browsing(self.caller.player, msg):
                return False
            tree = self.caller.player.aiwizard.tree
            node = tree.nodes[self.caller.player.aiwizard.node]

        if names and names[0] == "bb":
            # check whether a blackboard is being browsed
            msg = (
                "use the @ailook command with the bb argument unless you " +
                "first move to a blackboard via the @aibb command")
            if not is_browsing_blackboard(self.caller.player, msg):
                return False

            bb = self.caller.player.aiwizard.agent.ai.data
            display_node_in_bb(self.caller, tree, node, bb)
            return True

        else:
            display_node_in_tree(self.caller, tree, node)
            return True


class CmdStatus(Command):
    """
    Display the currently browsed tree, node and blackboard, as well as all
    the nodes currently being watched by the player.

    Usage:
        @aistatus
        @aistat

    See also:
        @ailist @ailook @aiwatch
    """
    key = "@aistatus"
    aliases = ['@aistat']
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        if not is_aiplayer(self.caller):
            return False

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

        if wiz.agent:
            s_agent = "{0} (id '{1}')\n".format(wiz.agent.name, wiz.agent.id)
        else:
            s_agent = "None\n"

        s = "|cTree:|n " + s_tree
        s += "|cNode:|n " + s_node
        s += "|cAgent:|n " + s_agent
        if wiz.watching:
            s += "|cWatch list|n:\n"
        else:
            s += "|cWatch list|n: None\n"

        for watched in wiz.watching:
            w_node = watched[0]
            w_obj_type = watched[1]
            w_agent = watched[2]
            w_tree = ScriptDB.get_id(w_node.hash[4:])
            s += (
                s_indent + "{0} '{1}'(\"{2}\") ".format(
                    w_node.hash[0:3], w_node.name) +
                "at tree {0} (id {1}) ".format(
                    w_tree.name, w_tree.id) + "\n")
            s += (
                s_indent * 2 + "in the blackboard of {0} {1} ".format(
                    w_obj_type, w_agent.name) +
                "(id {2})\n".format(w_agent.id))

        evmore.msg(self.caller, s)


def watch_or_unwatch_prep(s_op, caller, names):
    """
    A function present in @aiset and @aidelattr that loads the target tree,
    node and agent.
    """
    n_names = len(names)

    if n_names == 0:
        # The currently browsed tree, node and agent blackboard will be used.
        if s_op == "@aiwatch":
            msg = "add the currently browsed node to your watchlist"
        else:
            msg = "remove the currently browsed node from your watchlist"

        if not is_browsing(caller.player, msg):
            return False

        if not is_browsing_blackboard(caller.player, msg):
            return False

        tree = caller.player.aiwizard.tree
        node = tree.nodes[caller.player.aiwizard.node]
        agent = caller.player.aiwizard.agent

        obj_type_name = "object" if isinstance(agent, AIObject) else "script"

        if not is_agent_set_up(caller, agent, obj_type_name):
            return False

        bb = agent.ai.data
        if not is_node_in_bb(caller, node, bb, msg):
            return False

    elif n_names == 1:
        # The target node in the currently browsed tree, and the target
        # blackboard, will be used
        if s_op == "@aiwatch":
            msg = "add the target node to your watchlist"
        else:
            msg = "remove the target node from your watchlist"

        if not is_browsing(caller.player, msg):
            return False

        if not is_browsing_blackboard(caller.player, msg):
            return False

        tree = caller.player.aiwizard.tree
        node = node_from_name(caller, tree, names[0][1:-1])
        if not node:
            return False

        agent = caller.player.aiwizard.agent
        obj_type_name = "object" if isinstance(agent, AIObject) else "script"

        if not is_agent_set_up(caller, agent, obj_type_name):
            return False

        bb = agent.ai.data
        if not is_node_in_bb(caller, node, bb, msg):
            return False

    elif n_names == 2 and (names[0] == "object" or names[0] == "script"):
        # The currently browsed node and tree, and the target blackboard,
        # will be used
        if s_op == "@aiwatch":
            msg = (
                "add the target node in the currently browsed tree to " +
                "your watchlist")
        else:
            msg = (
                "remove the target node in the currently browsed tree from " +
                "your watchlist")

        if not is_browsing(caller.player, msg):
            return False

        tree = caller.player.aiwizard.tree
        node = tree.nodes[caller.player.aiwizard.node]

        obj_type_name = names[0]
        if obj_type_name == "object":
            obj_type = AIObject
        elif obj_type_name == "script":
            obj_type = AIScript

        agent = agent_from_name(caller, obj_type, names[1][1:-1])
        if not agent:
            return False

        if not is_agent_set_up(caller, agent, obj_type_name):
            return False

        bb = agent.ai.data
        if not is_node_in_bb(caller, node, bb, msg):
            return False

    elif n_names == 2:
        if s_op == "@aiwatch":
            msg = (
                "add the currently browsed instance of the target node to " +
                "your watchlist")
        else:
            msg = (
                "remove the currently browsed instance of the target node " + 
                "from your watchlist")

        if not is_browsing_blackboard(caller.player, msg):
            return False
        agent = caller.player.aiwizard.agent
        obj_type_name = "object" if isinstance(agent, AIObject) else "script"

        if not is_agent_set_up(caller, agent, obj_type_name):
            return False

        tree = tree_from_name(caller, names[0][1:-1])
        if not tree:
            return False

        node = node_from_name(caller, tree, names[1][1:-1])
        if not node:
            return False

        bb = agent.ai.data

        if not is_node_in_bb(caller, node, bb, msg):
            return False

    elif n_names == 4:
        # The target node in the target
        if s_op == "@aiwatch":
            msg = "add the target node to your watchlist"
        else:
            msg = "remove the target node from your watchlist"

        tree = tree_from_name(caller, names[0][1:-1])
        if not tree:
            return False

        node = node_from_name(caller, tree, names[1][1:-1])
        if not node:
            return False

        obj_type_name = names[2]
        if obj_type_name == "object":
            obj_type = AIObject
        elif obj_type_name == "script":
            obj_type = AIScript
        else:
            caller.msg(
                "Invalid third argument for the {0} ".format(s_op) +
                "command. When there are four arguments, the third " +
                "must be either \"object\" or \"script\" (without quotes).")

        agent = agent_from_name(caller, obj_type, names[3][1:-1])

        if not is_agent_set_up(caller, agent, obj_type_name):
            return False

        bb = agent.ai.data
        if not is_node_in_bb(caller, node, bb, msg):
            return False

    else:
        caller.msg(
            "The {0} command cannot take {1} ".format(s_op, n_names) +
            "arguments. Please supply it with 0, 2 or 4 arguments of the " +
            "appropriate type.")
        return False

    return (tree, node, agent, obj_type_name, bb)


class CmdWatch(Command):
    """
    Add a given instance of a node in an AI agent's blackboard to your
    watchlist. As long as a node is on the watchlist, you will be informed
    of the node's return status whenever the node is ticked. This can be
    very useful for debugging.

    If you provide one argument, the hash or name of a node, the instance in
    the currently browsed blackboard of the target node that sits on the
    currently browsed tree will be selected.

    If you provide two arguments, the name or id of a tree and the name or hash
    of a node, the instance in the currently browsed blackboard of the target
    node in the target tree will be used.

    If you provide two arguments, the keyword "object or "script" (without
    quotes) and the name or id of an AIObject or AIScript, the instance of the
    currently browsed node in the blackboard of that object or script will be
    used.

    If you provide four arguments - a tree name or id, a node name or hash,
    the keyword "object" or "script" and finally the name or id of an AIObject
    or AIScript, the instance of the target node in the target blackboard will
    be used, provided that the node is in the target tree.

    Instead of a name or id, you can specify the 'this' keyword (in single
    quotes) to refer to the currently browsed tree or agent.

    The <tree name>, <node name> and <agent name> |w*must*|n be enclosed in
    single quotes.

    Usage:
        @aiwatch
        @aiwatch '<node name>'
        @aiwatch '<tree name>' '<node name>'
        @aiwatch <object|script> '<agent name>'
        @aiwatch '<tree name>' '<node name>' <object|script> '<agent name>'

    Examples:
        @aiwatch
        @aiwatch 'xQg'
        @aiwatch script '1422'
        @aiwatch 'Fighter AI' 'bash them all' object 'orc marauder'

    See also:
        @aistatus @aiunwatch
    """
    key = "@aiwatch"
    aliases = []
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        if not is_aiplayer(self.caller):
            return False

        names = re.findall(r"(?:\b\w+\b)|(?:'[^']*')", self.args)

        retval = watch_or_unwatch_prep("@aiwatch", self.caller, names)
        if not retval:
            return False

        tree, node, agent, obj_type_name, bb = retval

        watching = self.caller.player in bb['nodes'][node.hash]['watchers']

        msg = (
            "{0} '{1}'(\"{2}\") ".format(
                type(node).__name__, node.hash, node.name) +
            "of tree {0} (id {1}) ".format(tree.name, tree.id) +
            "in the blackboard of {0} {1} (id {2}).".format(
                obj_type_name, agent.name, agent.id))

        if watching:
            self.caller.msg("You are already watching " + msg)
        else:
            watch_tuple = (node.hash, agent)
            bb['nodes'][node.hash]['watchers'].append(self.caller.player)
            self.caller.player.aiwizard.watching.append(watch_tuple)
            self.caller.msg("You will now be watching " + msg)

        return True


class CmdUnwatch(Command):
    """
    Remove a given instance of a node in an AI agent's blackboard from your
    watchlist.

    If you provide one argument, the hash or name of a node, the instance in
    the currently browsed blackboard of the target node that sits on the
    currently browsed tree will be selected.

    If you provide two arguments, the name or id of a tree and the name or hash
    of a node, the instance in the currently browsed blackboard of the target
    node in the target tree will be used.

    If you provide two arguments, the keyword "object or "script" (without
    quotes) and the name or id of an AIObject or AIScript, the instance of the
    currently browsed node in the blackboard of that object or script will be
    used.

    If you provide four arguments - a tree name or id, a node name or hash,
    the keyword "object" or "script" and finally the name or id of an AIObject
    or AIScript, the instance of the target node in the target blackboard will
    be used, provided that the node is in the target tree.

    Instead of a name or id, you can specify the 'this' keyword (in single
    quotes) to refer to the currently browsed tree or agent.

    The <tree name>, <node name> and <agent name> |w*must*|n be enclosed in
    single quotes.

    Usage:
        @aiunwatch
        @aiunwatch '<node name>'
        @aiunwatch '<tree name>' '<node name>'
        @aiunwatch <object|script> '<agent name>'
        @aiunwatch '<tree name>' '<node name>' <object|script> '<agent name>'

    Examples:
        @aiunwatch
        @aiunwatch 'xQg'
        @aiunwatch script '1422'
        @aiwatch 'Fighter AI' 'bash them all' object 'orc marauder'

    See also:
        @aistatus @aiwatch
    """
    key = "@aiunwatch"
    aliases = []
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        if not is_aiplayer(self.caller):
            return False

        names = re.findall(r"(?:\b\w+\b)|(?:'[^']*')", self.args)

        retval = watch_or_unwatch_prep("@aiunwatch", self.caller, names)
        if not retval:
            return False

        tree, node, agent, obj_type_name, bb = retval

        watching = self.caller.player in bb['nodes'][node.hash]['watchers']

        msg = (
            "{0} '{1}'(\"{2}\") ".format(
                type(node).__name__, node.hash, node.name) +
            "of tree {0} (id {1}) ".format(tree.name, tree.id) +
            "in the blackboard of {0} {1} (id {2}).".format(
                obj_type_name, agent.name, agent.id))

        if not watching:
            self.caller.msg("You were not even watching " + msg)
        else:
            watch_tuple = (node.hash, agent)
            bb['nodes'][node.hash]['watchers'].remove(self.caller.player)
            self.caller.player.aiwizard.watching.remove(watch_tuple)
            self.caller.msg("You are no longer watching " + msg)

            return True


class CmdGo(Command):
    """
    Set the current AI browsing cursor to a given tree and/or node. You must
    specify the name or database id of the AI tree you intend to go to, placing
    this name or id in single quotes. If you intend to go to the same tree you
    are currently browsing, use the name 'this'. You may also specify the
    three-character hash value or name of a node that you intend to browse,
    placing either of these in single quotes. If no such node is provided,
    your browsing cursor will automatically be placed at root node.

    You can provide the argument "bb" (without quotes) instead of a tree.
    In this case, the browsing cursor will move to the origin tree of the
    currently browsed AI.

    The <tree name> and <node name> |w*must*|n be enclosed in single quotes.

    Usage:
        @aigo '<tree name>'
        @aigo '<tree name>' '<node name>'
        @aigo bb
        @aigo bb '<node name>'

    Examples:
        @aigo 'fighter tree'
        @aigo '315' 'bash them all'
        @aigo 'fighter tree' 'x9F'
        @aigo 'this' 'root'
        @aigo bb 'bash them all'

    See also:
        @aiup @aidown @aibb
    """
    key = "@aigo"
    aliases = []
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        if not is_aiplayer(self.caller):
            return False

        names = re.findall(r"(?:\b\w+\b)|(?:'[^']*')", self.args)

        if len(names) == 0:
            self.caller.msg(
                "You have not provided the name of the tree " +
                "to which you wish to go. Please provide it, ensuring " +
                "it is placed between single quotes (the ' symbol).")
            return False

        # strip the names of their single quotes
        if len(names) > 1:
            node_name = names[1][1:-1]
        else:
            node_name = None

        if names[0] == "bb":
            # get the current blackboard agent's origin tree
            if not is_browsing_blackboard(
                    self.caller.player, " go to the origin tree of the " +
                    "currently browsed blackboard. To go to a blackboard, " +
                    "use the @aibb command"):
                return False

            agent = self.caller.player.aiwizard.agent
            if isinstance(agent, ObjectDB):
                obj_type_name = "object"
            elif isinstance(agent, ScriptDB):
                obj_type_name = "script"
            else:
                raise TypeError(
                    "Unknown type for AI agent {0} ".format(agent.name) +
                    "(id {0}).".format(agent.id))

            if not is_agent_set_up(self.caller, agent, obj_type_name):
                return False
            tree = agent.ai.tree
        else:
            tree = tree_from_name(self.caller, names[0][1:-1])
            if not tree:
                return False

        if self.caller.player.aiwizard.tree == tree:
            already_at_tree = True
        else:
            already_at_tree = False
            self.caller.player.aiwizard.tree = tree

        if node_name == None:
            node = tree.nodes[tree.root]
        else:
            # obtain the node if a valid one was provided.
            node = node_from_name(self.caller, tree, node_name)
            if not node:
                return False

            if self.caller.player.aiwizard.node == node.hash:
                self.caller.msg(
                    "Already browsing tree " +
                    "'{0}', node '{1}'(\"{2}\")".format(
                        tree.name, node.hash[0:3], node.name))
            else:
                self.caller.player.aiwizard.node = node.hash
                self.caller.msg(
                    "Successfully moved to tree " +
                    "'{0}', node '{1}'(\"{2}\")".format(
                        tree.name, node.hash[0:3], node.name))
                display_node_in_tree(self.caller, tree, node)
            return True

        if already_at_tree:
            if self.caller.player.aiwizard.node == node.hash:
                self.caller.msg("Already browsing tree '{0}'.".format(
                    tree.name))
            else:
                self.caller.msg("Already browsing tree '{0}'. ".format(
                    tree.name) + "Moving to root node.")
                self.caller.player.aiwizard.node = node.hash
                display_node_in_tree(self.caller, tree, node)
            return True
        else:
            self.caller.msg("Successfully moved to tree '{0}'.".format(
                tree.name))
            display_node_in_tree(self.caller, tree, node)
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

    See also:
        @aigo @aiup @aidown
    """
    key = "@aibb"
    aliases = []
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        if not is_aiplayer(self.caller):
            return False

        names = re.findall(r"(?:\b\w+\b)|(?:'[^']*')", self.args)

        if len(names) != 2:
            self.caller.msg(
                "Invalid number of arguments for the @aibb command. " +
                "This command may only receive a set of two arguments.")
            return False

        if names[0] == 'object':
            obj_type = AIObject
            obj_type_name = 'object'
        elif names[0] == 'script':
            obj_type = AIScript
            obj_type_name = 'script'
        else:
            self.caller.msg(
                "The first argument you have provided for the " +
                "@aibb command must be 'object' or 'script', without the " +
                "single quotes.")
            return False
        if not names:
            self.caller.msg(
                "Could not find the name or id of the target " +
                "in the arguments list. You must specify the name or id, in " +
                "single quotes, of the object or script whose blackboard " +
                "you wish to browse.")
            return False
        name = names[1][1:-1]

        agent = agent_from_name(self.caller, obj_type, name)
        if not agent:
            return False

        if not is_agent_set_up(self.caller, agent, obj_type_name):
            return False

        if self.caller.player.aiwizard.agent == agent:
            self.caller.msg(
                "Already browsing the blackboard of {0} ".format(
                    obj_type_name) +
                "\"{0}\" (id {1}).".format(agent.name, agent.id))
            return True

        self.caller.player.aiwizard.agent = agent
        self.caller.msg("Switched to the blackboard of {0} ".format(
            obj_type_name) + "\"{0}\" (id {1}).".format(agent.name, agent.id))
        return True


class CmdUp(Command):
    """
    Moves the AI browsing cursor to the currently browsed node's parent.

    Usage:
        @aiup

    See also:
        @aigo @aidown @aibb
    """
    key = "@aiup"
    aliases = []
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        if not is_aiplayer(self.caller):
            return False

        # check that a node is currently being browsed
        if not is_browsing(self.caller.player, "go up from the current node"):
            return False

        tree = self.caller.player.aiwizard.tree
        node = tree.nodes[self.caller.player.aiwizard.node]

        # check that the node being browsed has a parent
        if not node.parent:
            self.caller.msg(
                "The currently browsed node " +
                "'{0}'(\"{1}\") on tree ".format(node.hash[0:3], node.name) +
                "'{0}' (id {1}) ".format(tree.name, tree.id) + "does not " +
                "have a parent. You cannot browse upwards from it.")
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

    See also:
        @aigo @aiup @aibb
    """
    key = "@aidown"
    aliases = []
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        if not is_aiplayer(self.caller):
            return False

        arg = self.args.strip()

        # check that a node is currently being browsed
        if not is_browsing(self.caller.player, "go down from the current node"):
            return False

        tree = self.caller.player.aiwizard.tree
        node = tree.nodes[self.caller.player.aiwizard.node]

        # check that the node being browsed has children
        if not node.children:
            self.caller.msg(
                "Node '{0}'(\"{1}\") ".format(node.hash[0:3], node.name) +
                "of tree {0}(\"{1}\") ".format(tree.id, tree.name) +
                " has no children to which to descend.")
            return False

        if isinstance(node, CompositeNode):
            if len(node.children) != 1 and not arg:
                s = (
                    "Node '{0}'(\"{1}\") ".format(node.hash[0:3], node.name) +
                    "is a composite node. Please specify one " +
                    "of its children in your command:\n")
                for k_child in node.children:
                    s += s_indent + "'{0}'(\"{1}\")\n".format(
                        k_child.hash[0:3], k_child.name)
                evmore.msg(self.caller, s)
                return False

            elif len(node.children) == 1:
                child = node.children[0]

            else:
                if len(arg) > 1 and arg[0] == "'" and arg[-1] == "'":
                    name = arg[1:-1]
                    hashval = name + "_" + node.hash[4:]
                else:
                    name = None

                # check if the name is an index
                if all(
                        [x in string.digits for x in arg[1:]]) and (
                            arg[0] == "-" or arg[0] in string.digits):
                    try:
                        child = node.children[int(arg)]
                    except IndexError:
                        self.caller.msg(
                            "The node '{0}'(\"{1}\") ".format(
                                node.hash[0:3], node.name) +
                            "does not have a child at index {0}. ".format(arg) +
                            "Cannot perform descent.")
                        return False

                # check if the name is a hash
                elif name and hashval in [x.hash for x in node.children]:
                    child = [x for x in node.children if x.hash == hashval][0]

                elif name and name in [x.name for x in node.children]:
                    # get the child from its name
                    children = [
                        x for x in node.children if x.name == name]
                    if len(children) == 1:
                        child = children[0]
                    else:
                        s = (
                            "Multiple children of node '{0}'(\"{1}\") ".format(
                                node.hash[0:3], node.name) +
                            "share the name of {0}. ".format(name) +
                            "Please choose from among these hashes:\n")
                        for k_child in children:
                            s += s_indent + "'{0}'\n".format(k_child.hash[0:3])
                        return False
                else:
                    self.caller.msg(
                        "Node '{0}'(\"{1}\") ".format(
                            node.hash[0:3], node.name) +
                        "has no children with a hash or name of " +
                        "{0}. Cannot perform descent.".format(name))
                    return False
        else:
            child = node.children


        self.caller.player.aiwizard.node = child.hash

        display_node_in_tree(self.caller, tree, child)
        return True
