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

from evennia.contrib.aisystem.typeclasses import AIObject, AIScript
from evennia.contrib.aisystem.utils import (is_aiplayer, is_browsing, 
    is_browsing_blackboard, is_node_in_bb, tree_from_name, node_from_name, 
    agent_from_name)


class AIBuildCmdSet(CmdSet):
    """CmdSet for Behavior Tree AI building commands."""
    key = "ai_build_cmdset"
    priority = -20

    def at_cmdset_creation(self):
        self.add(CmdSetAttr())
        self.add(CmdDelAttr())

        #self.add(CmdAdd())
        #self.add(CmdCopy()) #in
        #self.add(CmdMove()) #in
        #self.add(CmdSwap())
        #self.add(CmdShift())
        #self.add(CmdRemove())


def set_or_del_prep(s_op, caller, names):
    """
    A function present in @aiset and @aidelattr that loads the target tree,
    node, agent and associated properties from the names provided in the
    command's arguments list.
    """

    # setting variables that will later be returned but may not be assigned
    # any value by this function
    agent = None
    bb = None
    obj_arg = None

    msg_tree = ("assign a new value to an attribute of the currently " +
        "browsed node")
    msg_bb = ("assign a new value to an attribute on the currently " +
        "browsed blackboard")

    if len(names) == 1:
        # working on the currently browsed node
        if not is_browsing(caller.player, msg_tree):
            return False
        
        tree = caller.player.aiwizard.tree
        node = tree.nodes[caller.player.aiwizard.node]

    elif len(names) == 2:
        # working on the currently browsed node's instance in the currently
        # browsed blackboard
        if not is_browsing(caller.player, msg_tree):
            return False

        tree = caller.player.aiwizard.tree
        node = tree.nodes[caller.player.aiwizard.node]

        obj_arg = names[0]
        if not obj_arg == "bb" and not obj_arg == "globals":
            caller.msg("When providing a single argument to the @aiset " +
                "command besides the attribute's name and its value, " +
                "only the arguments \"bb\" and \"globals\" (without quotes " +
                "are acceptable. You have provided the argument " +
                "\"{0}\"".format(obj_arg))
            return False

        if not is_browsing_blackboard(caller.player, msg_bb):
            return False

        agent = caller.player.aiwizard.agent
        # agent currently being browsed should already be set up
        bb = agent.db.ai
        obj_arg = "object" if isinstance(agent, AIObject) else "script"

        if not is_node_in_bb(caller.player, node, bb, msg_bb):
            return False

    elif len(names) == 3:
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

            bb = agent.db.ai

            if not is_browsing(caller.player, msg_tree):
                return False

            tree = caller.player.aiwizard.tree
            node = tree.nodes[caller.player.aiwizard.node]

            if not is_node_in_bb(caller.player, node, bb, 
                msg_bb):
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

    elif len(names) == 5:
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
            caller.msg("The @aiset command has received four " +
                "arguments besides the attribute's name and its value, " +
                "and so the third argument should be 'object' or " +
                "'script'. Instead, it is {0}.".format(obj_arg))
            return False

        tree = tree_from_name(caller, tree_name)
        if not tree:
            return False

        node = node_from_name(caller, node, node_name)
        if not node:
            return False

        agent = agent_from_name(caller, obj_arg, agent_name)
        if not agent:    
            return False
        
        bb = agent.db.ai

        if not is_node_in_bb(caller.player, node, bb, msg_bb):
            return False

    else:
        # incorrect number of arguments
        caller.msg("Incorrect number of arguments to the @aiset " +
            "command. Please enter either 0, 1, 2 or 4 arguments " +
            "followed by the name of the attribute you wish to change, " +
            "the = sign and the value you wish to assign the attribute.")
        return False

    return (tree, node, agent, bb, obj_arg)


def recursive_traverse_indices(obj, indices):
    if indices:
        index = indices[0]
        obj_type = type(obj)         
        if (obj_type == list or obj_type == _SaverList
            or obj_type == tuple):
            index = int(index)
        else: # assuming object is a dict or _SaverDict
            index = index[1:-1] # strip quotes

        return recursive_traverse_indices(obj[index], indices[1:])
    else:
        return obj


def get_container(caller, attr, p_attr):
    try:
        container = recursive_traverse_indices(attr, p_attr[1:-1])
    except IndexError:
        caller.msg("One of the indices you specified in " +
            "the attribute's chain of indices is not present in " + 
            "its container. Cannot perform the operation.")
        return None
    except TypeError:
        caller.msg("An item of a type that does not support " +
            "indexing has been encountered in the attribute's " +
            "chain of indexed items. Cannot perform the operation.")
        return None            

    if type(container) == tuple:
        caller.msg("The penultimate item in the attribute's " +
            "chain of indexed items is a tuple. Cannot peroform " +
            "the operation as tuples are immutable.")
        return None
    return container


class CmdSetAttr(Command):
    """
    Sets an attribute of the specified node to a specified value. The number of
    arguments you provide, besides the attribute name and its new value, will 
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

    If you provide four arguments - the name or hash of a tree, followed by the
    name or id of a node that resides on that tree, followed by the word
    "object" or "script" (without the quotes), followed by the name or id
    of an AI object or script - the instance of that node on that AI object or
    script will be selected.
    The change will affect that node instance specifically.

    If the tree and/or agent name is set to 'this', the currently browsed tree 
    and/or blackboard will be selected.

    The attribute name does not have to be an attribute itself, but can also be
    an entry in a dictionary, list or tuple attribute. For instance, if the
    attribute you wish to modify is called 'targets', and it is a list, you can
    modify the fourth entry in the list by setting the attribute name to 
    'targets[3]'. For nestled containers, you can chain indices, e.g. 
    'targets[3]['threat level'][15]'.

    The value you assign to an attribute can be a string, an int, a float, or a
    list, dict or tuple thereof, but you cannot assign arbitrary objects, 
    classes or functions this way.

    The names, ids or hashes of agents, trees or nodes |w*must*|n be provided
    in single quotes(the ' symbol).

    Finally, be careful about how you use this command. Some of the built-in
    attributes of various nodes and node instances are not meant to be tampered
    with. Modifying them may lead to errors.

    Usage:
        @aiset <attribute>=<value>
        @aiset <object|script> <agent name> <attribute>=<value>
        @aiset bb <attribute>=<value>
        @aiset globals <attribute>=<value>
        @aiset <tree name> <node name> <attribute>=<value>
        @aiset <tree name> <node name>  <agent name> <attribute>=<value>
        @aisetattr <any of the above sets of arguments>    

    Examples:
        @aiset name="check for hostiles"
        @aiset object 'tentacle monster' weight=15.0
        @aiset script 'this' weight=15.0
        @aisetattr bb ticks=2
        @aiset globals emotions['fear']=5.0
        @aiset 'this' 'attack' weapons['blunt'][1]=['mace', 'club', 'hammer']
        @aisetattr 'Fighter AI' 'Lji' '29415' msg[5]="Surrender or die!"

    See also:
        @aidelattr @ailook @aiassign
    """
    key = "@aiset"
    aliases = ['@aisetattr']
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
            self.caller.msg("No value for the attribute provided. Please " +
                "ensure that there is an equals sign after the attribute " +
                "name and a value following that.")
            return False
        rhe = rhe[0].strip()
        try:
            val = literal_eval(rhe)
        except ValueError:
            self.caller.msg("The value you have specified for the argument " +
                "is invalid. Cannot assign it to the attribute.")

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

        # The last entry in names should be the attribute name, possibly 
        # followed by a set of indices.        
        s_attr = names[-1]

        # parse this entry
        p_attr = re.findall(r"(?<=\[)[^\[\]]+(?=\])|\b\w+", s_attr)   
        p_attr = [x.strip() for x in p_attr]
        attr_name = p_attr[0]
        has_indices = len(p_attr) > 1

        # check whether a new attribute will be created or an old one will be
        # modified
        if affects_globals and not bb["globals"].has_key(attr_name):
            if has_indices:
                self.caller.msg("The global dictionary in the blackboard of " +
                    "{0} '{1}' (id {2}) ".format(obj_arg, agent.name, 
                    agent.id) + "does not have attribute {0}. ".format(
                    attr_name) + "Cannot assign value to the attribute's " +
                    "item.")
                return False
            msg_change = "|wcreated|n"    

        elif affects_globals:
            msg_change = "|wmodified|n"

        elif bb and not bb['nodes'][node.hash].has_key(attr_name):
            if has_indices:
                self.caller.msg("Instance of node '{0}'(\"{1}\") ".format(
                    node.hash[0:3], node.name) + "in the blackboard of " +
                    "{0} '{1}' (id {2}) ".format(obj_arg, agent.name, 
                    agent.id) + "does not have attribute {0}. ".format(
                    attr_name) + "Cannot assign value to the attribute's " +
                    "item.")
                return False
            msg_change = "|wcreated|n"

        elif not bb and not hasattr(node, attr_name):
            if has_indices:
                self.caller.msg("Node '{0}'(\"{1}\") ".format(node.hash[0:3],
                    node.name) + "does not have attribute " +
                    "{0}. Cannot assign value ".format(attr_name) +
                    "to the attribute's item.")
                return False
            msg_change = "|wcreated|n"

        else:
            msg_change = "|wmodified|n"


        if has_indices:
            if affects_globals:
                attr = bb['globals']
            elif bb:
                attr = bb['nodes'][node.hash]
            else:
                attr = getattr(node, attr_name)

            # Extract the penultimate container
            # in the chain of containers designated by these indices.
            if len(p_attr) > 2:
                container = get_container(self.caller, attr, p_attr)
                if container == None:
                    return False
            else:
                container = attr

            try:
                obj_type = type(container)
                if (obj_type == list or obj_type == _SaverList 
                    or obj_type == tuple):
                    index = int(p_attr[-1])
                else: # assuming object is a dict or _SaverDict
                    index = p_attr[-1][1:-1] #strip quotes
                container[index] = val
            except IndexError:
                self.caller.msg("The last index you specified for the " +
                    "attribute is invalid.")
        elif affects_globals:
            bb['globals'][attr_name] = val
        elif bb:
            bb['nodes'][node.hash][attr_name] = val
        else:
            setattr(node, attr_name, val)
        
        if affects_globals: 
            # save the node's blackboard
            agent.db.ai = bb
            
            self.caller.msg("Successfully {0} the ".format(msg_change) +
                "global attribute {0} in the blackboard of ".format(
                attr_name) + "{0} '{1}' (id {2}). ".format(obj_arg,
                agent.name, agent.id) + "value is now {0}.".format(rhe))

        elif bb:
            # save the node's blackboard
            agent.db.ai = bb

            self.caller.msg("Successfully {0} the ".format(msg_change) +
                "attribute {0} in the blackboard of ".format(attr_name) +
                "{0} '{1}' (id {2}), at ".format(obj_arg, agent.name, 
                agent.id) + "node '{0}'(\"{1}\") of tree ".format(
                node.hash[0:3], node.name) + "{0} (id {1}). The " +
                "attribute's ".format(tree.name, tree.id) +
                "value is now {0}.".format(rhe))
        else:
            # save the node's tree
            tree.db.nodes = tree.db.nodes

            self.caller.msg("Successfully {0} the ".format(msg_change) +
                "attribute {0} at node '{1}'".format(attr_name, 
                node.hash[0:3]) + "(\"{0}\") of tree {1} ".format(node.name, 
                tree.name) + "(id {0}). The attribute's value is now ".format(
                tree.id) + rhe)

        return True


#re.findall(r"(?:\b[^='\[\]]+(?:\[[^\[\]]+\])*)|(?:'[^']+')","bb 'a test' 'b' 'c' val[1][' test ']")

#re.findall(r"(?:\b[^='\[\]]+\b(?:\[[^\[\]]+\])*)|(?:'[^']+')","bb  'a test'   'b 15 x'   'c'  val[1][ 'test t' ]")

#(difference is one \b)

class CmdDelAttr(Command):
    """
    Deletes an attribute of the specified node. The number of arguments you 
    provide, besides the attribute name, will determine what node to affect.

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

    If you provide four arguments - the name or hash of a tree, followed by the
    name or id of a node that resides on that tree, followed by the word
    "object" or "script" (without the quotes), followed by the name or id
    of an AI object or script - the instance of that node on that AI object or
    script will be selected.
    The change will affect that node instance specifically.

    If the tree and/or agent name is set to 'this', the currently browsed tree 
    and/or blackboard will be selected.

    The attribute name does not have to be an attribute itself, but can also be
    an entry in a dictionary, list or tuple attribute. For instance, if the
    attribute you wish to modify is called 'targets', and it is a list, you can
    delete the fourth entry in the list by setting the attribute name to 
    'targets[3]'. For nestled containers, you can chain indices, e.g. 
    'targets[3]['threat level'][15]'.

    The names, ids or hashes of agents, trees or nodes |w*must*|n be provided
    in single quotes(the ' symbol).

    Finally, be extremely careful about how you use this command. The built-in
    attributes of various nodes and node instances are not meant to be deleted.

    Usage:
        @aidelattr <attribute>
        @aidelattr <object|script> <agent name> <attribute>
        @aidelattr bb <attribute>
        @aidelattr globals <attribute>
        @aidelattr <tree name> <node name> <attribute>
        @aidelattr <tree name> <node name>  <agent name> <attribute>
    
    Examples:
        @aidelattr name
        @aidelattr object 'tentacle monster' weight
        @aidelattr script 'marauder army strategy' weight
        @aidelattr bb ticks=2
        @aiset globals emotions['rage']
        @aidelattr 'this' 'bash them all' weapons
        @aidelattr 'Fighter AI' 'Lji' '29415' groups[1]

    See also:
        @aiset @ailook @aiassign
    """
    key = "@aidelattr"
    aliases = []
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
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

        retval = set_or_del_prep("@aidelattr", self.caller, names)
        if not retval:
            return False
        tree, node, agent, bb, obj_arg = retval

        # The last entry in names should be the attribute name, possibly 
        # followed by a set of indices.        
        s_attr = names[-1]

        # parse this entry
        p_attr = re.findall(r"(?<=\[)[^\[\]]+(?=\])|\b\w+", s_attr)   
        p_attr = [x.strip() for x in p_attr]
        attr_name = p_attr[0]
        has_indices = len(p_attr) > 1

        if has_indices:
            msg_act = "item of "
        else:
            msg_act = ""

        # check that the attribute exists
        if affects_globals and not bb["globals"].has_key(attr_name):
            self.caller.msg("The global dictionary in the blackboard of " +
                "{0} '{1}' (id {2}) ".format(obj_arg, agent.name, 
                agent.id) + "does not have attribute {0}. ".format(
                attr_name) + "Cannot assign value to the attribute's " +
                "item.")
            return False

        if bb and not bb['nodes'][node.hash].has_key(attr_name):
            self.caller.msg("Instance of node '{0}'(\"{1}\") ".format(
                node.hash[0:3], node.name) + "in the blackboard of " +
                "{0} '{1}' (id {2}) ".format(obj_arg, agent.name, 
                agent.id) + "does not have attribute {0}. ".format(
                attr_name) + "Cannot proceed with deletion.")
            return False

        elif not bb and not hasattr(node, attr_name):
            self.caller.msg("Node '{0}'(\"{1}\") ".format(node.hash[0:3],
                node.name) + "does not have attribute " +
                "{0}. Cannot proceed with deletion. ".format(attr_name))
            return False

        if has_indices:
            if affects_globals:
                attr = bb['globals']
            elif bb:
                attr = bb['nodes'][node.hash]
            else:
                attr = getattr(node, attr_name)

            # Extract the penultimate container
            # in the chain of containers designated by these indices.
            if len(p_attr) > 2:
                container = get_container(self.caller, attr, p_attr)
                if container == None:
                    return False
            else:
                container = attr

            try:
                obj_type = type(container)
                if (obj_type == list or obj_type == _SaverList 
                    or obj_type == tuple):
                    index = int(p_attr[-1])
                else: # assuming object is a dict or _SaverDict
                    index = p_attr[-1][1:-1] #strip quotes

                del container[index]
            except IndexError:
                self.caller.msg("The last index you specified for the " +
                    "attribute is invalid.")
        elif affects_globals:
            del bb['globals'][attr_name]
        elif bb:
            del bb['nodes'][node.hash][attr_name]
        else:
            delattr(node, attr_name)

        if affects_globals: 
            # save the node's blackboard
            agent.db.ai = bb
            
            self.caller.msg("Successfully deleted the {0}".format(msg_act) +
                "global attribute {0} in the blackboard of ".format(
                attr_name) + "{0} '{1}' (id {2}). ".format(obj_arg,
                agent.name, agent.id) + "value is now {0}.".format(rhe))       
        elif bb:
            # save the node's blackboard
            agent.db.ai = bb

            self.caller.msg("Successfully |wdeleted|n the " +
                "{0} attribute {1} in the ".format(msg_act, attr_name) +
                "blackboard of {0} '{1}' (id {2}), at ".format(obj_arg, 
                agent.name, agent.id) + "node '{0}'(\"{1}\") ".format(
                node.hash[0:3], node.name) + "of tree {0} (id {1}).".format(
                tree.name, tree.id))
        else:
            # save the node's tree
            tree.db.nodes = tree.db.nodes

            self.caller.msg("Successfully |wdeleted|n the {0} ".format(
                msg_act) + "attribute {0} at node '{1}' ".format(attr_name, 
                node.hash[0:3]) + "(\"{0}\") of tree {1} ".format(node.name, 
                tree.name) + "(id {0}).".format(tree.id))

        return True


