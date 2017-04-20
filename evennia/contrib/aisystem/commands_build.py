"""
Commands for building behavior trees by adding, removing, copying, moving,
swapping and shifting the positions of nodes.
"""
import re
from ast import literal_eval
from evennia import CmdSet
from evennia.utils import evmore
from evennia.utils.dbserialize import _SaverList
from evennia.commands.command import Command
from evennia.contrib.aisystem.nodes import RootNode, CompositeNode, LeafNode
from evennia.contrib.aisystem.typeclasses import AIObject, AIScript
from evennia.contrib.aisystem.utils import (
    is_aiplayer, is_browsing, is_browsing_blackboard, is_node_in_bb,
    tree_from_name, node_from_name, agent_from_name, is_agent_set_up,
    get_all_agents_with_tree, recursive_clear_watchlists)


class AIBuildCmdSet(CmdSet):
    """CmdSet for Behavior Tree AI building commands."""
    key = "ai_build_cmdset"
    priority = -20

    def at_cmdset_creation(self):
        self.add(CmdSetProp())
        self.add(CmdDelProp())
        self.add(CmdAdd())
        self.add(CmdCopy())
        self.add(CmdMove())
        self.add(CmdSwap())
        self.add(CmdShift())
        self.add(CmdRemove())


def set_or_del_prep(s_op, caller, names):
    """
    A function present in @aiset and @aidelprop that loads the target tree,
    node, agent and associated properties from the names provided in the
    command's arguments list.
    """

    # setting variables that will later be returned but may not be assigned
    # any value by this function
    agent = None
    bb = None
    obj_arg = None

    msg_tree = (
        "assign a new value to a property of the currently browsed node")
    msg_bb = (
        "assign a new value to a property on the currently browsed " +
        "blackboard")
    n_names = len(names)

    if n_names == 1:
        # working on the currently browsed node
        if not is_browsing(caller.player, msg_tree):
            return False

        tree = caller.player.aiwizard.tree
        node = tree.nodes[caller.player.aiwizard.node]

    elif n_names == 2:
        # working on the currently browsed node's instance in the currently
        # browsed blackboard
        obj_arg = names[0]

        if obj_arg == "bb":
            if not is_browsing(caller.player, msg_tree):
                return False

            tree = caller.player.aiwizard.tree
            node = tree.nodes[caller.player.aiwizard.node]

        else:
            tree = None
            node = ""

        if not obj_arg == "bb" and not obj_arg == "globals":
            caller.msg(
                "When providing a single argument to the {0} ".format(s_op) +
                "command besides the property's name and its value, " +
                "only the arguments \"bb\" and \"globals\" (without quotes) " +
                "are acceptable. You have provided the argument " +
                "\"{0}\"".format(obj_arg))
            return False

        if not is_browsing_blackboard(caller.player, msg_bb):
            return False

        agent = caller.player.aiwizard.agent
        # agent currently being browsed should already be set up
        bb = agent.ai.data
        obj_arg = "object" if isinstance(agent, AIObject) else "script"

        if (obj_arg == "bb" and 
                not is_node_in_bb(caller.player, node, bb, msg_bb)):
            return False

    elif n_names == 3:
        obj_arg = names[0].strip()

        if obj_arg == 'object':
            obj_type = AIObject
        elif obj_arg == 'script':
            obj_type = AIScript
        else:
            obj_type = None

        if obj_type:
            # working on the target agent's blackboard instance of the
            # currently browsed node
            agent_name = names[1].strip()[1:-1]
            agent = agent_from_name(caller, obj_type, agent_name)
            if not agent:
                return False

            bb = agent.ai.data

            if not is_browsing(caller.player, msg_tree):
                return False

            tree = caller.player.aiwizard.tree
            node = tree.nodes[caller.player.aiwizard.node]

            if not is_node_in_bb(
                    caller.player, node, bb, msg_bb):
                return False

        else:
            # working on the target node in the target tree
            tree_name = names[0].strip()[1:-1]
            node_name = names[1].strip()[1:-1]

            tree = tree_from_name(caller, tree_name)
            if not tree:
                return False

            node = node_from_name(caller, tree, node_name)
            if not node:
                return False

    elif n_names == 4:
        if names[0] != "globals":
            self.caller.msg(
                "When providing three arguments to the {0} ".format(s_op) +
                "command besides the property's name and its value, " +
                "only the argument \"globals\" (without quotes) " +
                "is acceptable. You have provided the argument " +
                "\"{0}\"".format(obj_arg))

        tree = None
        node = ""
        obj_arg = names[1].strip()
        agent_name = names[2].strip()[1:-1]

        if obj_arg == 'object':
            obj_type = AIObject
        elif obj_arg == 'script':
            obj_type = AIScript
        else:
            caller.msg(
                "The {0} command has received three ".format(s_op) +
                "arguments besides the property's name and its value, " +
                "and so the second argument should be 'object' or " +
                "'script'. Instead, it is {0}.".format(obj_arg))
            return False
          
        agent = agent_from_name(caller, obj_type, agent_name)
        if not agent:
            return False

        if not is_agent_set_up(caller, agent, obj_arg):
            return False

        bb = agent.ai.data

    elif n_names == 5:
        # working on the target agent's blackboard instance of the target
        # node in the target tree
        tree_name = names[0].strip()[1:-1]
        node_name = names[1].strip()[1:-1]
        obj_arg = names[2].strip()
        agent_name = names[3].strip()[1:-1]

        if obj_arg == 'object':
            obj_type = AIObject
        elif obj_arg == 'script':
            obj_type = AIScript
        else:
            caller.msg(
                "The {0} command has received four ".format(s_op) +
                "arguments besides the property's name and its value, " +
                "and so the third argument should be 'object' or " +
                "'script'. Instead, it is {0}.".format(obj_arg))
            return False

        tree = tree_from_name(caller, tree_name)
        if not tree:
            return False

        node = node_from_name(caller, tree, node_name)
        if not node:
            return False

        agent = agent_from_name(caller, obj_type, agent_name)
        if not agent:
            return False

        if not is_agent_set_up(caller, agent, obj_arg):
            return False

        bb = agent.ai.data

        if not is_node_in_bb(caller.player, node, bb, msg_bb):
            return False

    else:
        # incorrect number of arguments
        caller.msg(
            "Incorrect number of arguments to the {0} ".format(s_op) +
            "command. Please enter between 0 and 4 arguments " +
            "followed by the name of the property you wish to change, " +
            "the = sign and the value you wish to assign the property.")
        return False

    return (tree, node, agent, bb, obj_arg)


def recursive_traverse_indices(obj, indices):
    """
    Goes through all indices in the provided chain of indices of a left-hand
    argument, e.g. obj[5]['test1'][12][-1]['test2']
    """
    if indices:
        index = indices[0]
        obj_type = type(obj)
        if (obj_type == list or obj_type == _SaverList or
                obj_type == tuple):
            index = int(index)
        else: # assuming object is a dict or _SaverDict
            index = index[1:-1] # strip quotes

        return recursive_traverse_indices(obj[index], indices[1:])
    else:
        return obj


def get_container(caller, prop, p_prop):
    """
    Wrapper around the recursive_traverse_indices function, meant to
    provide the same error messages for the @aisetprop and @aidelprop commands.
    """
    try:
        container = recursive_traverse_indices(prop, p_prop[1:-1])
    except IndexError:
        caller.msg(
            "One of the indices you specified in " +
            "the property's chain of indices is not present in " +
            "its container. Cannot perform the operation.")
        return None
    except TypeError:
        caller.msg(
            "An item of a type that does not support " +
            "indexing has been encountered in the property's " +
            "chain of indexed items. Cannot perform the operation.")
        return None

    if type(container) == tuple:
        caller.msg(
            "The penultimate item in the property's " +
            "chain of indexed items is a tuple. Cannot peroform " +
            "the operation as tuples are immutable.")
        return None
    return container


class CmdSetProp(Command):
    """
    Sets a property of the specified node to a specified value. The number of
    arguments you provide, besides the property's name and its new value, will
    determine what node to browse and how to modify it.

    If you provide no extra arguments, the currently browsed node will be
    selected. The change will affect the node itself, not one of its instances.

    If you provide only one argument - "bb" or "globals" (without the quotes)
     - the currently browsed node or the currently browsed blackboard will be
    selected. If "bb" is provided, the change will affect the node instance
    associated with the currently browsed blackboard. If "globals" is provided,
    the change will affect the global data of the currently browsed blackboard.

    If you provide two arguments - the name or hash of a tree followed by the
    name or id of a node that resides on that tree - that node will be
    selected. The change will affect the node itself, not one of its instances.

    If you provide two arguments - the word "object" or "script" (without the
    quotes) followed by the name or id of an AI object or script - the instance
    of the currently browsed node on that AI object or script will be selected.

    If you provide three arguments - the word "globals" followed by the word
    "object" or "script" (without the quotes) followed by the name or id of an
    AI object or script - the global blackboard data of that AI object or script
    will be selected.

    If you provide four arguments - the name or hash of a tree, followed by the
    name or id of a node that resides on that tree, followed by the word
    "object" or "script" (without the quotes), followed by the name or id
    of an AI object or script - the instance of that node on that AI object or
    script will be selected.
    The change will affect that node instance specifically.

    If the tree and/or agent name is set to 'this', the currently browsed tree
    and/or blackboard will be selected.

    The property name does not have to be a property itself, but can also be
    an entry in a dictionary, list or tuple property. For instance, if the
    property you wish to modify is called 'targets', and it is a list, you can
    modify the fourth entry in the list by setting the property name to
    'targets[3]'. For nestled containers, you can chain indices, e.g.
    'targets[3]['threat level'][15]'.

    The value you assign to a property can be a string, an int, a float, or a
    list, dict or tuple thereof, but you cannot assign arbitrary objects,
    classes or functions this way.

    The names, ids or hashes of agents, trees or nodes |w*must*|n be enclosed
    in single quotes(the ' symbol).

    Finally, be careful about how you use this command. Some of the built-in
    properties of various nodes and node instances are not meant to be tampered
    with. Modifying them may lead to errors.

    Usage:
        @aiset <property>=<value>
        @aiset <object|script> '<agent name>' <property>=<value>
        @aiset bb <property>=<value>
        @aiset globals <property>=<value>
        @aiset globals <object|script> '<agent name>' <property>=<value>
        @aiset '<tree name>' '<node name>' <property>=<value>
        @aiset '<tree name>' '<node name>' '<agent name>' <property>=<value>
        @aisetprop <any of the above sets of arguments>

    Examples:
        @aiset name="check for hostiles"
        @aiset object 'tentacle monster' check=False
        @aiset script 'this' weight=15.0
        @aisetprop bb ticks=2
        @aiset globals emotions['fear']=5.0
        @aiset globals object 'tentacle monster' emotions['rage']=2.0
        @aiset 'this' 'attack' weapons['blunt'][1]=['mace', 'club', 'hammer']
        @aisetprop 'Fighter AI' 'Lji' '29415' msg[5]="Surrender or die!"

    See also:
        @aidelprop @ailook @aiassigntree
    """
    key = "@aisetprop"
    aliases = ['@aiset']
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        if not is_aiplayer(self.caller):
            return False

        args = self.args.strip()
        # extract the right-hand expression from the string
        rhe = re.findall(r"(?<==).*$", args)
        if not rhe:
            self.caller.msg(
                "No value for the property provided. Please " +
                "ensure that there is an equals sign after the property " +
                "name and a value following that.")
            return False
        rhe = rhe[0].strip()
        try:
            val = literal_eval(rhe)
        except ValueError:
            self.caller.msg(
                "The value you have specified for the argument " +
                "is invalid. Cannot assign it to the property.")
            return False

        # extract a string that lacks the right-hand expression and equals sign
        args_nonrhe = args.replace(rhe, "")[0:-1]

        # get either a word (like bb), followed by any number of list or
        # dictionary indices, or a name in single quotes
        exp = r"(?:\b[^='\s\[\]]+\b(?:\[[^\[\]]+\])*)|(?:'[^']+')"

        names = re.findall(exp, args_nonrhe)

        # ensure that the arguments "globals" and "bb" are read appropriately
        # if flanked by spaces
        names[0] = names[0].strip()
        affects_globals = names[0] == "globals"

        retval = set_or_del_prep("@aiset", self.caller, names)
        if not retval:
            return False
        tree, node, agent, bb, obj_arg = retval

        # The last entry in names should be the property name, possibly
        # followed by a set of indices.
        s_prop = names[-1]

        # parse this entry
        p_prop = re.findall(r"(?<=\[)[^\[\]]+(?=\])|\b\w+", s_prop)
        p_prop = [x.strip() for x in p_prop]
        prop_name = p_prop[0]
        has_indices = len(p_prop) > 1

        # check whether a new property will be created or an old one will be
        # modified
        if affects_globals and not bb["globals"].has_key(prop_name):
            if has_indices:
                self.caller.msg(
                    "The global dictionary in the blackboard of " +
                    "{0} '{1}' (id {2}) ".format(
                        obj_arg, agent.name, agent.id) +
                    "does not have property {0}. ".format(prop_name) +
                    "Cannot assign value to the property's item.")
                return False
            msg_change = "|wcreated|n"

        elif affects_globals:
            msg_change = "|wmodified|n"

        elif bb and not bb['nodes'][node.hash].has_key(prop_name):
            if has_indices:
                self.caller.msg(
                    "Instance of node '{0}'(\"{1}\") ".format(
                        node.hash[0:3], node.name) +
                    "in the blackboard of " + "{0} '{1}' (id {2}) ".format(
                        obj_arg, agent.name, agent.id) +
                    "does not have property {0}. ".format(prop_name) +
                    "Cannot assign value to the property's item.")
                return False
            msg_change = "|wcreated|n"

        elif not bb and not hasattr(node, prop_name):
            if has_indices:
                self.caller.msg(
                    "Node '{0}'(\"{1}\") ".format(node.hash[0:3], node.name) +
                    "does not have property {0}. ".format(prop_name) +
                    "Cannot assign value to the property's item.")
                return False
            msg_change = "|wcreated|n"

        else:
            msg_change = "|wmodified|n"


        if has_indices:
            if affects_globals:
                prop = bb['globals']
            elif bb:
                prop = bb['nodes'][node.hash]
            else:
                prop = getattr(node, prop_name)

            # Extract the penultimate container
            # in the chain of containers designated by these indices.
            if len(p_prop) > 2:
                container = get_container(self.caller, prop, p_prop)
                if container == None:
                    return False
            else:
                container = prop

            try:
                obj_type = type(container)
                if (obj_type == list or obj_type == _SaverList
                        or obj_type == tuple):
                    index = int(p_prop[-1])
                else: # assuming object is a dict or _SaverDict
                    index = p_prop[-1][1:-1] #strip quotes
                container[index] = val
            except IndexError:
                self.caller.msg(
                    "The last index you specified for the property " +
                    "is invalid.")
                return False
        elif affects_globals:
            bb['globals'][prop_name] = val
        elif bb:
            bb['nodes'][node.hash][prop_name] = val
        else:
            setattr(node, prop_name, val)

        if affects_globals:
            # save the node's blackboard
            agent.ai.data = bb

            self.caller.msg(
                "Successfully {0} the ".format(msg_change) +
                "global property {0} in the ".format(prop_name) +
                "blackboard of {0} '{1}' (id {2}). ".format(
                    obj_arg, agent.name, agent.id) +
                "value is now {0}.".format(rhe))

        elif bb:
            # save the node's blackboard
            agent.ai.data = bb

            self.caller.msg(
                "Successfully {0} the ".format(msg_change) +
                "property {0} in the blackboard of ".format(prop_name) +
                "{0} '{1}' (id {2}), at ".format(
                    obj_arg, agent.name, agent.id) +
                "node '{0}'(\"{1}\") of tree ".format(
                    node.hash[0:3], node.name) +
                "{0} (id {1}). The property's ".format(tree.name, tree.id) +
                "value is now {0}.".format(rhe))
        else:
            # save the node's tree
            tree.db.nodes = tree.db.nodes

            self.caller.msg(
                "Successfully {0} the ".format(msg_change) +
                "property {0} at node '{1}'".format(
                    prop_name, node.hash[0:3]) +
                "(\"{0}\") of tree {1} ".format(node.name, tree.name) +
                "(id {0}). The property's value is now ".format(tree.id) + rhe)

        return True


class CmdDelProp(Command):
    """
    Deletes a property of the specified node. The number of arguments you
    provide, besides the property's name, will determine what node to affect.

    If you provide no extra arguments, the currently browsed node will be
    selected. The change will affect the node itself, not one of its instances.

    If you provide only one argument - "bb" or "globals" (without the quotes)
     - the currently browsed node or the currently browsed blackboard will be
    selected. If "bb" is provided, the change will affect the node instance
    associated with the currently browsed blackboard. If "globals" is provided,
    the change will affect the global data of the currently browsed blackboard.

    If you provide two arguments - the name or hash of a tree followed by the
    name or id of a node that resides on that tree - that node will be
    selected. The change will affect the node itself, not one of its instances.

    If you provide two arguments - the word "object" or "script" (without the
    quotes) followed by the name or id of an AI object or script - the instance
    of the currently browsed node on that AI object or script will be selected.

    If you provide three arguments - the word "globals" followed by the word
    "object" or "script" (without the quotes) followed by the name or id of an
    AI object or script - the global blackboard data of that AI object or script
    will be selected.

    If you provide four arguments - the name or hash of a tree, followed by the
    name or id of a node that resides on that tree, followed by the word
    "object" or "script" (without the quotes), followed by the name or id
    of an AI object or script - the instance of that node on that AI object or
    script will be selected.
    The change will affect that node instance specifically.

    If the tree and/or agent name is set to 'this', the currently browsed tree
    and/or blackboard will be selected.

    The property name does not have to be a property itself, but can also be
    an entry in a dictionary, list or tuple property. For instance, if the
    property you wish to modify is called 'targets', and it is a list, you can
    delete the fourth entry in the list by setting the property name to
    'targets[3]'. For nestled containers, you can chain indices, e.g.
    'targets[3]['threat level'][15]'.

    The names, ids or hashes of agents, trees or nodes |w*must*|n be enclosed
    in single quotes(the ' symbol).

    Finally, be extremely careful about how you use this command. The built-in
    properties of various nodes and node instances are not meant to be deleted.

    Usage:
        @aidelprop <property>
        @aidelprop <object|script> '<agent name>' <property>
        @aidelprop bb <property>
        @aidelprop globals <property>
        @aidelprop globals <object|script> '<agent name>' <property>=<value>
        @aidelprop '<tree name>' '<node name>' <property>
        @aidelprop '<tree name>' '<node name>' '<agent name>' <property>

    Examples:
        @aidelprop name
        @aidelprop object 'tentacle monster' weight
        @aidelprop script 'marauder army strategy' weight
        @aidelprop bb ticks=2
        @aidelprop globals emotions['fear']
        @aidelprop globals object 'tentacle monster' emotions['rage']=2.0
        @aidelprop 'this' 'bash them all' weapons
        @aidelprop 'Fighter AI' 'Lji' '29415' groups[1]

    See also:
        @aiset @ailook @aiassigntree
    """
    key = "@aidelprop"
    aliases = []
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        if not is_aiplayer(self.caller):
            return False

        # extract a string that lacks the right-hand expression and equals sign
        args = self.args.strip()

        # get either a word (like bb), followed by any number of list or
        # dictionary indices, or a name in single quotes
        exp = r"(?:\b[^='\s\[\]]+\b(?:\[[^\[\]]+\])*)|(?:'[^']+')"

        names = re.findall(exp, args)

        # ensure that the arguments "globals" and "bb" are read appropriately
        # if flanked by spaces
        names[0] = names[0].strip()
        affects_globals = names[0] == "globals"

        retval = set_or_del_prep("@aidelprop", self.caller, names)
        if not retval:
            return False
        tree, node, agent, bb, obj_arg = retval

        # The last entry in names should be the property name, possibly
        # followed by a set of indices.
        s_prop = names[-1]

        # parse this entry
        p_prop = re.findall(r"(?<=\[)[^\[\]]+(?=\])|\b\w+", s_prop)
        p_prop = [x.strip() for x in p_prop]
        prop_name = p_prop[0]
        has_indices = len(p_prop) > 1

        if has_indices:
            msg_act = "item of "
        else:
            msg_act = ""

        # check that the property exists
        if affects_globals and not bb["globals"].has_key(prop_name):
            self.caller.msg(
                "The global dictionary in the blackboard of " +
                "{0} '{1}' (id {2}) ".format(obj_arg, agent.name, agent.id) +
                "does not have property {0}. ".format(prop_name) +
                "Cannot assign value to the property's item.")
            return False

        if (bb and not affects_globals and
                not bb['nodes'][node.hash].has_key(prop_name)):
            self.caller.msg(
                "Instance of node '{0}'(\"{1}\") ".format(
                    node.hash[0:3], node.name) +
                "in the blackboard of {0} '{1}' (id {2}) ".format(
                    obj_arg, agent.name, agent.id) +
                "does not have property {0}. ".format(prop_name) +
                "Cannot proceed with deletion.")
            return False

        elif not bb and not hasattr(node, prop_name):
            self.caller.msg(
                "Node '{0}'(\"{1}\") ".format(node.hash[0:3], node.name) +
                "does not have property {0}. Cannot ".format(prop_name) +
                "proceed with deletion.")
            return False

        if has_indices:
            if affects_globals:
                prop = bb['globals']
            elif bb:
                prop = bb['nodes'][node.hash]
            else:
                prop = getattr(node, prop_name)

            # Extract the penultimate container
            # in the chain of containers designated by these indices.
            if len(p_prop) > 2:
                container = get_container(self.caller, prop, p_prop)
                if container == None:
                    return False
            else:
                container = prop

            try:
                obj_type = type(container)
                if (obj_type == list or obj_type == _SaverList
                        or obj_type == tuple):
                    index = int(p_prop[-1])
                else: # assuming object is a dict or _SaverDict
                    index = p_prop[-1][1:-1] #strip quotes

                del container[index]
            except IndexError:
                self.caller.msg(
                    "The last index you specified for the " +
                    "property is invalid.")
                return False
        elif affects_globals:
            del bb['globals'][prop_name]
        elif bb:
            del bb['nodes'][node.hash][prop_name]
        else:
            delattr(node, prop_name)

        if affects_globals:
            # save the node's blackboard
            agent.ai.data = bb

            self.caller.msg(
                "Successfully |wdeleted|n the {0}".format(msg_act) +
                "global property {0} in the ".format(prop_name) +
                "blackboard of {0} '{1}' (id {2}). ".format(
                    obj_arg, agent.name, agent.id))
        elif bb:
            # save the node's blackboard
            agent.ai.data = bb

            self.caller.msg(
                "Successfully |wdeleted|n the {0}".format(msg_act) +
                "property {0} in the ".format(prop_name) +
                "blackboard of {0} '{1}' (id {2}), at ".format(
                    obj_arg, agent.name, agent.id) +
                "node '{0}'(\"{1}\") ".format(node.hash[0:3], node.name) +
                "of tree {0} (id {1}).".format(tree.name, tree.id))
        else:
            # save the node's tree
            tree.db.nodes = tree.db.nodes

            self.caller.msg(
                "Successfully |wdeleted|n the {0} ".format(msg_act) +
                "property {0} at node '{1}'(\"{2}\") ".format(
                    prop_name, node.hash[0:3], node.name) +
                "of tree {0} (id {1}).".format(tree.name, tree.id))

        return True


class CmdAdd(Command):
    """
    Appends a new node of the specified type to the target node.

    When no target node or target tree is specified, the currently browsed
    node is targeted. When no target tree is specified, the target node in
    the currently browsed tree is targeted.

    When adding a node to a composite node, if the "in" argument is not
    specified, you can specify a position as an optional argument, denoting
    where in the composite node's list of children to attach the new node. The
    position can be any positive or negative integer. If no position argument
    is specified, the node will be placed at the end of the list of children.
    Specifying a position when the target node is not a composite node has no
    effect.

    The keyword "this" (without quotes) may be used instead of a tree name or
    id to refer to the currently browsed tree.

    The new node's name must not contain any single quotes, but must be
    enclosed by single quotes.

    Usage:
        @aiadd <node type> '<a-node>' [<position>] [in]
        @aiadd '<t-node>' <node type> '<a-node>' [<position>] [in]
        @aiadd '<t-tree>' '<t-node>' <node type> '<a-name>' [<position>] [in]
        @aiaddnode <any of the above sets of arguments>

    Where <a-node> is the name of the added node,
          <t-tree> is the name or id of the target tree,
          <t-node> is the name or hash of the target node,
      and [<position>], an optional argument, is a positive or negative integer

    The names, ids or hashes of trees and nodes |w*must*|n be enclosed in
    single quotes(the ' symbol).

    Examples:
        @aiadd MemSequence 'flee'
        @aiadd Parallel 'run and shoot' 3 in
        @aiadd '5mY' Repeater 'keep firing' in
        @aiadd 'rush the enemy' Inverter 'invert' -1
        @aiadd '15' 'g1k' Succeeder 'always'
        @aiadd 'fighter tree' 'bash them all' MemSequence 'goto next enemy' 0

    See also:
        @aicopynode @aimovenode @aiswapnode @aishiftnode @airemovenode
    """

    key = "@aiaddnode"
    aliases = ['@aiadd']
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        if not is_aiplayer(self.caller):
            return False

        names = re.findall(r"(?:-?\b\w+\b)|(?:'[^']*')", self.args)

        msg_invalid_n_args = (
            "Invalid number of arguments for the " +
            "@aiaddnode command. Can only accept between 2 and 6 " +
            "arguments, including the optional position and \"in\"" +
            "arguments.")

        if len(names) < 2:
            self.caller.msg(msg_invalid_n_args)
            return False

        if names[-1] == "in":
            is_in = True
            names = names[:-1]
        else:
            is_in = False

        try:
            position = int(names[-1])
            names = names[:-1]
        except ValueError:
            position = None

        # doing this again in case the node name and type string are missing
        if len(names) < 2:
            self.caller.msg(msg_invalid_n_args)
            return False

        new_node_typestr = names[-2]
        new_node_name = names[-1][1:-1]

        # Check that the type of the node exists
        if new_node_typestr in self.player.ainodes.keys():
            new_node_type = self.player.ainodes[new_node_typestr]
        else:
            self.caller.msg(
                "The desired node type could not be found in " +
                "the dictionary of all AI nodes. To add it to the " +
                "dictionary, follow the instructions in the aisystem's " +
                "README.md file.")
            return False

        if new_node_type == RootNode:
            self.caller.msg(
                "You have attempted to add a root node. " +
                "Root nodes cannot be added, moved or copied.")
            return False

        msg = "append the new node"
        n_names = len(names)

        if n_names == 2:
            # The currently browsed tree and node will be used
            if not is_browsing(self.caller.player, msg):
                return False

            tree = self.caller.player.aiwizard.tree
            node = tree.nodes[self.caller.player.aiwizard.node]

        elif n_names == 3:
            # The currently browsed tree and the target node will be used
            if not is_browsing(self.caller.player, msg):
                return False

            tree = self.caller.player.aiwizard.tree
            node = node_from_name(self.caller, tree, names[0][1:-1])
            if not node:
                return False

        elif n_names == 4:
            # The target tree and node will be used

            tree = tree_from_name(self.caller, names[0][1:-1])
            if not tree:
                return False

            node = node_from_name(self.caller, tree, names[1][1:-1])
            if not node:
                return False
        else:
            self.caller.msg(msg_invalid_n_args)
            return False

        if is_in:
            parent = node.parent
            if not parent:
                self.caller.msg(
                    "{0} '{1}'(\"{2}\") ".format(
                        type(node).__name__, node.hash[0:3], node.name) +
                    "has no parent. Cannot insert the new node above it.")
                return False

            if isinstance(parent, CompositeNode):
                position = parent.children.index(node)
                parent.children.remove(node)
            else:
                parent.children = None

            try:
                new_node = new_node_type(
                    new_node_name, tree, parent, position=position)
            except Exception as e:
                self.caller.msg(e)
                return False

            node.parent = new_node
            if isinstance(new_node, CompositeNode):
                new_node.children.append(node)
            else:
                new_node.children = node

            msg_act1 = "inserted"
            msg_act2 = "over"
        else:
            try:
                new_node = new_node_type(
                    new_node_name, tree, node, position=position)
            except Exception as e:
                self.caller.msg(e)
                return False

            msg_act1 = "added"
            msg_act2 = "to"

        if position == None:
            msg_position = ""
        else:
            msg_position = "position {0} under ".format(position)

        self.caller.msg(
            "Successfully {0} {1} '{2}'(\"{3}\") ".format(
                msg_act1, type(new_node).__name__, new_node.hash[0:3],
                new_node.name) +
            "{0} {1}{2} '{3}'(\"{4}\") ".format(
                msg_act2, msg_position, type(node).__name__, node.hash[0:3],
                node.name) +
            "in tree {0} (id {1}).".format(tree.name, tree.id))

        return True


def copy_move_swap_prep(s_op, caller, names, msg):
    """
    A function present in the @aicopynode, @aimovenode and @aiswapnode that
    loads the target tree, node, agent and associated properties from the names
    provided in the command's arguments list.
    """
    n_names = len(names)

    if n_names == 0:
        caller.msg(
            "Invalid number of arguments. You must provide at least the name " +
            "or hash of the target node.")
        return False

    elif n_names == 1:
        # The currently browsed tree is both the target tree and the source
        # tree. The currently browsed node is the source node.

        if not is_browsing(caller.player, msg):
            return False

        s_tree = None
        t_tree = caller.player.aiwizard.tree
        s_node = t_tree.nodes[caller.player.aiwizard.node]
        t_node = node_from_name(caller, t_tree, names[0][1:-1])
        if not t_node:
            return False

    elif n_names == 2:
        # The currently browsed tree is the source tree. The currently browsed
        # node is the source node. Both the target tree and the target node
        # are specified in the names list.
        if not is_browsing(caller.player, msg):
            return False

        s_tree = caller.player.aiwizard.tree
        s_node = s_tree.nodes[caller.player.aiwizard.node]
        t_tree = tree_from_name(caller, names[0][1:-1])
        if not t_tree:
            return False

        t_node = node_from_name(caller, t_tree, names[1][1:-1])
        if not t_node:
            return False

    elif n_names == 3:
        # The currently browsed tree is the source tree. The source node,
        # target node and target tree are all specified in the names list.
        if not is_browsing(caller.player, msg):
            return False

        s_tree = caller.player.aiwizard.tree
        s_node = node_from_name(caller, s_tree, names[0][1:-1])
        if not s_node:
            return False

        t_tree = tree_from_name(caller, names[1][1:-1])
        if not t_tree:
            return False

        t_node = node_from_name(caller, t_tree, names[2][1:-1])
        if not t_node:
            return False

    elif n_names == 4:
        # All trees and nodes are specified in the names list.
        s_tree = tree_from_name(caller, names[0][1:-1])
        if not s_tree:
            return False

        s_node = node_from_name(caller, s_tree, names[1][1:-1])
        if not s_node:
            return False

        t_tree = tree_from_name(caller, names[2][1:-1])
        if not t_tree:
            return False

        t_node = node_from_name(caller, t_tree, names[3][1:-1])
        if not t_node:
            return False

    else:
        caller.msg(
            "Invalid number of arguments for the {0} command. ".format(s_op) +
            "You may only specify up to 4 arguments besides the optional ones.")
        return False

    if s_tree == t_tree:
        s_tree = None

    return (s_tree, s_node, t_tree, t_node)


class CmdCopy(Command):
    """
    Copies the source node in the source tree to the target node in the target
    tree. If the "in" argument (without quotes) is specified, the copy of the
    source node is interposed between the target node and its parent. Otherwise,
    it is appended to the target node as its child.

    If no source node or tree is specified, the currently browsed node or tree
    will be used as the source node or tree. If no target tree is specified,
    the currently browsed tree will be used as the target tree.

    When adding a node to a composite node, you can specify a position as an
    optional argument, denoting where in the composite node's list of children
    to attach the new node. The position can be any positive or negative
    integer. If no position argument is specified, the node will be placed at
    the end of the list of children. Specifying a position when the target node
    is not a composite node has no effect.

    The keyword "this" (without quotes) may be used instead of a tree name or
    id to refer to the currently browsed tree.

    Usage:
        @aicopy '<t-node>' [<position>] [in]
        @aicopy '<t-tree>' '<t-node>' [<position>] [in]
        @aicopy '<s-node>' '<t-tree>' '<t-node>' [<position>] [in]
        @aicopy '<s-tree>' '<s-node>' '<t-tree>' '<t-node>' [<position>] [in]
        @aicopynode <any of the above sets of arguments>

    Where <s-tree> is the name or id of the source tree,
          <s-node> is the name or hash of the source node,
          <t-tree> is the name or id of the target tree,
          <t-node> is the name or hash of the target node,
          [<position>], an optional argument, is a positive or negative integer
          [in] is the optional argument "in" (without quotes)

    The names, ids or hashes of trees and nodes |w*must*|n be enclosed in
    single quotes(the ' symbol).

    Examples:
        @aicopy '7hW' in
        @aicopy 'fighter tree' 'bash them all' 5
        @aicopy 'eat lunch' 'commoner AI' 'business hours'
        @aicopy 'warrior tree' 'retreat' 'this' 'k8v' -2 in

    See also:
        @aiaddnode @aimovenode @aiswapnode @aishiftnode @airemovenode
    """

    key = "@aicopynode"
    aliases = ['@aicopy']
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        if not is_aiplayer(self.caller):
            return False

        names = re.findall(r"(?:-?\b\w+\b)|(?:'[^']*')", self.args)

        if names and names[-1] == "in":
            is_in = True
            names = names[:-1]
        else:
            is_in = False

        try:
            position = int(names[-1])
            names = names[:-1]
        except ValueError:
            position = None
        except IndexError:
            pass

        msg_prep = "copy the currently browsed node to the target node"
        retval = copy_move_swap_prep(
            "@aicopynode", self.caller, names, msg_prep)
        if not retval:
            return False

        s_tree, s_node, t_tree, t_node = retval

        if s_tree:
            msg_s_tree = "from tree {0} (id {1}) ".format(
                s_tree.name, s_tree.id)
        else:
            msg_s_tree = ""

        if is_in:
            errstr = t_tree.interpose(
                s_node, t_node, position=position, copying=True,
                source_tree=s_tree)
            msg_act = (
                "interposed a copy of {0} '{1}'(\"{2}\") {3}".format(
                    type(s_node).__name__, s_node.hash[0:3], s_node.name,
                    msg_s_tree) +
                "between")
        else:
            errstr = t_tree.add(
                s_node, t_node, position=position, copying=True,
                source_tree=s_tree)
            msg_act = (
                "copied {0} '{1}'(\"{2}\") {3}to".format(
                    type(s_node).__name__, s_node.hash[0:3], s_node.name,
                    msg_s_tree))

        if errstr:
            self.caller.msg(errstr)
            return False
        else:
            self.caller.msg(
                "Successfully {0} {1}'{2}'(\"{3}\") ".format(
                    msg_act, type(t_node).__name__, t_node.hash[0:3],
                    t_node.name) +
                "in tree {0} (id {1}).".format(t_tree.name, t_tree.id))
            return True


class CmdMove(Command):
    """
    Moves the source node in the source tree to the target node in the target
    tree. If the "in" argument (without quotes) is specified, the source node
    is interposed between the target node and its parent. Otherwise, it is
    appended to the target node as its child.

    If no source node or tree is specified, the currently browsed node or tree
    will be used as the source node or tree. If no target tree is specified,
    the currently browsed tree will be used as the target tree.

    When adding a node to a composite node, you can specify a position as an
    optional argument, denoting where in the composite node's list of children
    to attach the new node. The position can be any positive or negative
    integer. If no position argument is specified, the node will be placed at
    the end of the list of children. Specifying a position when the target node
    is not a composite node has no effect.

    The keyword "this" (without quotes) may be used instead of a tree name or
    id to refer to the currently browsed tree.

    Usage:
        @aimove '<t-node>' [<position>] [in]
        @aimove '<t-tree>' '<t-node>' [<position>] [in]
        @aimove '<s-node>' '<t-tree>' '<t-node>' [<position>] [in]
        @aimove '<s-tree>' '<s-node>' '<t-tree>' '<t-node>' [<position>] [in]
        @aimovenode <any of the above sets of arguments>

    Where <s-tree> is the name or id of the source tree,
          <s-node> is the name or hash of the source node,
          <t-tree> is the name or id of the target tree,
          <t-node> is the name or hash of the target node,
          [<position>], an optional argument, is a positive or negative integer
          [in] is the optional argument "in" (without quotes)

    The names, ids or hashes of trees and nodes |w*must*|n be enclosed in
    single quotes(the ' symbol).

    Examples:
        @aimove '7hW' in
        @aimove 'fighter tree' 'bash them all' 5
        @aimove 'eat lunch' 'commoner AI' 'business hours'
        @aimove 'warrior tree' 'retreat' 'this' 'k8v' -2 in

    See also:
        @aiaddnode @aicopynode @aiswapnode @aishiftnode @airemovenode
    """

    key = "@aimovenode"
    aliases = ['@aimove']
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        if not is_aiplayer(self.caller):
            return False

        names = re.findall(r"(?:-?\b\w+\b)|(?:'[^']*')", self.args)

        if names and names[-1] == "in":
            is_in = True
            names = names[:-1]
        else:
            is_in = False

        try:
            position = int(names[-1])
            names = names[:-1]
        except ValueError:
            position = None
        except IndexError:
            pass

        msg_prep = "move the currently browsed node to the target node"
        retval = copy_move_swap_prep(
            "@aimovenode", self.caller, names, msg_prep)
        if not retval:
            return False

        s_tree, s_node, t_tree, t_node = retval

        if s_tree:
            msg_s_tree = "from tree {0} (id {1}) ".format(
                s_tree.name, s_tree.id)
        else:
            msg_s_tree = ""

        if is_in:
            errstr = t_tree.interpose(
                s_node, t_node, position=position, copying=False,
                source_tree=s_tree)
            msg_act = (
                "interposed {0} '{1}'(\"{2}\") {3}".format(
                    type(s_node).__name__, s_node.hash[0:3], s_node.name,
                    msg_s_tree) +
                "between")
        else:
            errstr = t_tree.add(
                s_node, t_node, position=position, copying=False,
                source_tree=s_tree)
            msg_act = (
                "moved {0} '{1}'(\"{2}\") {3}to".format(
                    type(s_node).__name__, s_node.hash[0:3], s_node.name,
                    msg_s_tree))

        if errstr:
            self.caller.msg(errstr)
            return False
        else:
            self.caller.msg(
                "Successfully {0} {1}'{2}'(\"{3}\") ".format(
                    msg_act, type(t_node).__name__, t_node.hash[0:3],
                    t_node.name) +
                "in tree {0} (id {1}).".format(t_tree.name, t_tree.id))
            return True


class CmdSwap(Command):
    """
    Swaps the locations of the source node and the target node, even if the two
    nodes are in different trees.

    If no source node or tree is specified, the currently browsed node or tree
    will be used as the source node or tree. If no target tree is specified,
    the currently browsed tree will be used as the target tree.

    The keyword "this" (without quotes) may be used instead of a tree name or
    id to refer to the currently browsed tree.

    Usage:
        @aiswap '<t-node>'
        @aiswap '<t-tree>' '<t-node>'
        @aiswap '<s-node>' '<t-tree>' '<t-node>'
        @aiswap '<s-tree>' '<s-node>' '<t-tree>' '<t-node>'
        @aiswapnode <any of the above sets of arguments>

    Where <s-tree> is the name or id of the source tree,
          <s-node> is the name or hash of the source node,
          <t-tree> is the name or id of the target tree,
          <t-node> is the name or hash of the target node,

    The names, ids or hashes of trees and nodes |w*must*|n be enclosed in
    single quotes(the ' symbol).

    Examples:
        @aiswap '7hW' in
        @aiswap 'fighter tree' 'bash them all' 5
        @aiswap 'eat lunch' 'commoner AI' 'business hours'
        @aiswap 'warrior tree' 'retreat' 'this' 'k8v' -2 in

    See also:
        @aiaddnode @aicopynode @aimovenode @aishiftnode @airemovenode
    """

    key = "@aiswapnode"
    aliases = ['@aiswap']
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        if not is_aiplayer(self.caller):
            return False

        names = re.findall(r"(?:-?\b\w+\b)|(?:'[^']*')", self.args)

        try:
            position = int(names[-1])
            names = names[:-1]
        except ValueError:
            position = None
        except IndexError:
            pass

        msg_prep = "swap the currently browsed node with the target node"
        retval = copy_move_swap_prep(
            "@aiswapnode", self.caller, names, msg_prep)
        if not retval:
            return False

        s_tree, s_node, t_tree, t_node = retval

        if s_tree:
            msg_s_tree = "from tree {0} (id {1}) ".format(
                s_tree.name, s_tree.id)
        else:
            msg_s_tree = ""

        errstr = t_tree.swap(s_node, t_node, source_tree=s_tree)
        if errstr:
            self.caller.msg(errstr)
            return False
        else:
            self.caller.msg(
                "Successfully swapped {0} '{1}'(\"{2}\") ".format(
                    type(s_node).__name__, s_node.hash[0:3], s_node.name) +
                "{0}with {1} '{2}'(\"{3}\") ".format(
                    msg_s_tree, type(t_node).__name__, t_node.hash[0:3],
                    t_node.name) +
                "in tree {0} (id {1}).".format(t_tree.name, t_tree.id))
            return True


class CmdShift(Command):
    """
    Shifts the target node to the specified position in its parent's list of
    children. Only applicable for children of composite nodes.

    If no node and / or tree is specified, the currently browsed node and / or
    tree will be used.

    The position argument may be any positive or negative integer. If no
    position argument is specified, this command moves the node to the
    end of its parent's list of children.

    The keyword "this" (without quotes) may be used instead of a tree name or
    id to refer to the currently browsed tree.

    Usage:
        @aishift [<position>]
        @aishift '<node>' [<position>]
        @aishift '<tree>' '<node>' [<position>]

    Examples:
        @aishift 2
        @aishift 'iv4'
        @aishift 'this' 'attack' -1

    Where <tree> is the name or id of the source tree,
          <node> is the name or hash of the source node,
      and [<position>], an optional argument, is a positive or negative integer

    The names, ids or hashes of trees and nodes |w*must*|n be enclosed in
    single quotes(the ' symbol).

    See also:
        @aiaddnode @aicopynode @aimovenode @aiswapnode @airemovenode
    """
    key = "@aishiftnode"
    aliases = ['@aishift']
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        if not is_aiplayer(self.caller):
            return False

        names = re.findall(r"(?:-?\b\w+\b)|(?:'[^']*')", self.args)

        try:
            position = int(names[-1])
            names = names[:-1]
        except ValueError:
            position = None
        except IndexError:
            position = None

        n_names = len(names)
        msg = "shift the currently browsed node"

        if n_names == 0:
            # use the currently browsed tree and node
            if not is_browsing(self.caller.player, msg):
                return False

            tree = self.player.aiwizard.tree
            node = tree.nodes[self.player.aiwizard.node]

        elif n_names == 1:
            # use the currently browsed tree and the target node
            if not is_browsing(self.caller.player, msg):
                return False

            tree = self.caller.player.aiwizard.tree
            node = node_from_name(self.caller, tree, names[0][1:-1])
            if not node:
                return False

        elif n_names == 2:
            # use the target tree and node
            tree = tree_from_name(self.caller, names[0][1:-1])
            if not tree:
                return False

            node = node_from_name(self.caller, tree, names[1][1:-1])
            if not node:
                return False

        else:
            self.caller.msg(
                "Invalid number of arguments for the " +
                "@aishiftnode command. You may only specify up to 2 " +
                "arguments apart from the optional position index.")
            return False

        errstr = tree.shift(node, position=position)

        if errstr:
            self.caller.msg(errstr)
            return False
        else:
            if position == None:
                msg_pos = "the final position"
            else:
                msg_pos = "position {0}".format(position)
            parent = node.parent

            self.caller.msg(
                "Successfully shifted {0} '{1}'(\"{2}\") ".format(
                    type(node).__name__, node.hash[0:3], node.name) +
                "to {0} in the children list of {1} '{2}'(\"{3}\").".format(
                    msg_pos, type(parent).__name__, parent.hash[0:3],
                    parent.name))
            return False


class CmdRemove(Command):
    """
    Removes the target node, along with all its child nodes, from its tree.

    If no node and / or tree is specified, the currently browsed node and / or
    tree will be used.

    The keyword "this" (without quotes) may be used instead of a tree name or
    id to refer to the currently browsed tree.

    Usage:
        @airemove
        @airemove '<node>'
        @airemove '<tree>' '<node>'

    Examples:
        @airemove
        @airemove 'iv4'
        @airemove 'this' 'attack'

    Where <tree> is the name or id of the source tree,
      and <node> is the name or hash of the source node.

    The names, ids or hashes of trees and nodes |w*must*|n be enclosed in
    single quotes(the ' symbol).

    See also:
        @aiaddnode @aicopynode @aimovenode @aiswapnode @aishiftnode
    """
    key = "@airemovenode"
    aliases = ['@airemove']
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        if not is_aiplayer(self.caller):
            return False

        names = re.findall(r"(?:-?\b\w+\b)|(?:'[^']*')", self.args)

        n_names = len(names)
        msg = "shift the currently browsed node"

        if n_names == 0:
            # use the currently browsed tree and node
            if not is_browsing(self.player, msg):
                return False

            tree = self.caller.player.aiwizard.tree
            node = tree.nodes[self.caller.player.aiwizard.node]

        elif n_names == 1:
            # use the currently browsed tree and the target node
            if not is_browsing(self.player, msg):
                return False

            tree = self.caller.player.aiwizard.tree
            node = node_from_name(self.caller, tree, names[0][1:-1])
            if not node:
                return False

        elif n_names == 2:
            # use the target tree and the target node
            tree = tree_from_name(self.caller, names[0][1:-1])
            if not tree:
                return False

            node = node_from_name(self.caller, tree, names[1][1:-1])
            if not node:
                return False

        else:
            self.caller.msg(
                "Invalid number of arguments for the " +
                "@airemovenode command. You may only specify up to 2 " +
                "arguments.")
            return False

        if not isinstance(node, RootNode):
            # Trying to remove a root node will be caught as an error and will
            # cause the command to fail, don't remove the watchlists if that
            # happens
            agents = get_all_agents_with_tree(tree)
            for agent in agents:
                recursive_clear_watchlists(node, agent.ai.data)
                agent.ai.data = agent.ai.data

        parent = node.parent
        errstr = tree.remove(node)
        if errstr:
            self.caller.msg(errstr)
            return False

        # Move the browsing cursor to the node's parent if necessary
        if self.caller.player.aiwizard.node == node.hash:
            self.caller.player.aiwizard.node = parent.hash
            msg_parent = (
                " Browsing cursor moved to the node's parent, " +
                "{0} '{1}'(\"{2}\").".format(
                    type(parent).__name__, parent.hash, parent.name))
        else:
            msg_parent = ""

        self.caller.msg(
            "Successfully removed {0} '{1}'(\"{2}\") ".format(
                type(node).__name__, node.hash[0:3], node.name) +
            "from tree {0} (id {1}).{2}".format(
                tree.name, tree.id, msg_parent))

        return True
