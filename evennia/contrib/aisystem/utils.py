import string
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from evennia import ScriptDB, ObjectDB, PlayerDB
from evennia.utils import evmore
from evennia.utils.dbserialize import _SaverList, _SaverDict
from evennia.contrib.aisystem.nodes import CompositeNode, Transition

# globals that will store delayed imports
_AI_OBJECT = None
_AI_SCRIPT = None
_AI_PLAYER = None


def recurse(node, func):
    """
    Performing a function on the child nodes of a given node, but does not 
    step into the target tree of a Transition node. For this process to be
    recursive, the method that calls recurse should be the very function
    performed by recurse.
    """
    if isinstance(node, CompositeNode):
        for child in node.children:
            func(child)
    elif node.children:
        func(node.children) 


def recurse_bb(node, func, bb):
    """
    Same as recurse, but performed over a blackboard.
    """
    if isinstance(node, CompositeNode):
        for child in node.children:
            func(child, bb)
    elif node.children:
        func(node.children, bb) 


def recurse_multitree(node, func):
    """
    Same as recurse, but continues recursion through Transition nodes into
    child trees.
    """
    if isinstance(node, CompositeNode):
        for child in node.children:
            func(child)
    elif isinstance(node, Transition):
        func(node.target_tree.nodes[node.target_tree.root])
    elif node.children:
        func(node.children) 


def recursive_clear_watchlists(node):
    """
    Removes the node from all watchlists. Useful when about to delete a node
    and its children.
    """
    watchers = bb['nodes'][node.hash]['watchers']
    for watcher in watchers:
        watcher.aiwizard.watching.remove(node.hash)
        watcher.db.aiwizard = watcher.db.aiwizard # save the aiwizard data
    bb['nodes'][node.hash]['watchers'] = []
    # don't forget to save the bb from its agent after this!
    recurse(node, recursive_clear_watchlists, bb)


def setup(override=False):
    """
    Sets up all AIHandlers and AIWizardHandlers in the game.
    """
    global _AI_OBJECT
    global _AI_SCRIPT
    global _AI_PLAYER
    if not _AI_OBJECT:
        from evennia.contrib.aisystem.typeclasses import (AIObject
            as _AI_OBJECT)
    if not _AI_SCRIPT:
        from evennia.contrib.aisystem.typeclasses import (AIScript
            as _AI_SCRIPT)
    if not _AI_PLAYER:
        from evennia.contrib.aisystem.typeclasses import (AIPlayer
            as _AI_PLAYER)

    aiobjects = [x for x in ObjectDB.objects.all()
        if isinstance(x, _AI_OBJECT)]
    for aiobject in aiobjects:
        aiobject.ai.setup(override=override)

    aiscripts = [x for x in ScriptDB.objects.all() 
        if isinstance(x, _AI_SCRIPT)]
    for aiscript in aiscripts:
        aiscript.ai.setup(override=override)

    aiplayers = [x for x in PlayerDB.objects.all()
        if isinstance(x, _AI_PLAYER)]
    for aiplayer in aiplayers:
        aiplayer.aiwizard.setup(override=override)


# The following functions are only used by the AI system's commands.

def is_aiplayer(caller):
    """
    Returns True if the caller's player is subclassed from AIPlayer,
    else messages the caller and returns False
    """
    global _AI_PLAYER
    if not _AI_PLAYER:
        from evennia.contrib.aisystem.typeclasses import (AIPlayer
            as _AI_PLAYER)

    if not isinstance(caller.player, _AI_PLAYER):
        caller.msg("{0} does not have the ".format(caller.player.name) +
            "AIPlayer typeclass. The command cannot proceed. Please set " +
            "the player's typeclass to AIPlayer in the code, possibly by " +
            "subclassing your game's Player typeclass from AIPlayer.")
        return False
    return True


def is_browsing(player, msg):
    """
    Checks whether the given player is browsing a tree and node.
    If not, sends an error message to that player and returns False.
    """
    if not player.aiwizard.tree:
        player.msg("You are not currently browsing any tree " +
            "and so cannot {0}.".format(msg))
        return False
    if not player.aiwizard.node:
        player.msg("You are not currently browsing any node " +
            "and so cannot {0}.".format(msg))
        return False
    return True


def is_browsing_blackboard(player, msg):
    """
    Checks whether the given player is browsing a blackboard.
    If not, sends an error message to that player and returns False.
    """
    if not player.aiwizard.agent:
        player.msg("You are not currently browsing any blackboard " +
            "and so cannot {0}.".format(msg))
        return False
    return True


def is_node_in_bb(caller, node, bb, msg):
    """
    Checks whether the given node is in the given blackboard's list of nodes
    If not, sends an error message to the given player and returns False
    """
    if not bb['nodes'].has_key(node.hash):
        caller.msg("Node '{0}'(\"{1}\") ".format(node.hash[0:3], node.name) +
            "was not found in the specified blackboard. You cannot " +
            "{0}.".format(msg))
        return False
    return True


def is_agent_set_up(caller, agent, obj_type_name):
    """
    Checks whether the given agent has a blackboard and has been assigned
    a tree. If not, sends an error message to the given caller and returns
    False.
    """
    if not (agent.attributes.has("ai") and agent.db.ai):
        caller.msg("The {0} '{1}' (id {2}) ".format(obj_type_name, agent.name,
            agent.id) + "does not have an AI blackboard. Please set up " +
            "the agent's blackboard by running @aisetup on that agent " +
            "or globally.")
        return False

    if not agent.ai.tree:
        caller.msg("The {0} '{1}' (id {2}) ".format(obj_type_name, agent.name,
            agent.id) + "does not have an associated Behavior Tree. Please " +
            "assign it a tree via the @aiassign command.")
        return False
    return True


def is_agent_correct_type(agent, obj_type_name):
    """
    Checks 
    """


def get_all_agents_with_tree(tree):
    """
    Gets a list of all AIObjects and AIScripts that use the given tree
    """
    global _AI_OBJECT
    global _AI_SCRIPT
    if not _AI_OBJECT:
        from evennia.contrib.aisystem.typeclasses import (AIObject
            as _AI_OBJECT)
    if not _AI_SCRIPT:
        from evennia.contrib.aisystem.typeclasses import (AIScript
            as _AI_SCRIPT)

    objects = [x for x in ObjectDB.objects.all() 
        if isinstance(x, _AI_OBJECT) and x.db.ai 
        and x.db.ai.has_key("tree") and x.db.ai['tree'] == tree]
    scripts = [x for x in ScriptDB.objects.all()
        if isinstance(x, _AI_SCRIPT) and x.db.ai 
        and x.db.ai.has_key("tree") and x.db.ai['tree'] == tree]
    return objects + scripts


def player_from_name(caller, name):
    """
    If there is a single player in the database that has the given id or name, 
    returns that player, else returns None
    """
    if name == 'this':
        # pass the player using the command that calls this function
        player = caller.player

    elif all([x in string.digits for x in name]):
        player = PlayerDB.objects.get_id(name)
        if not player:
            caller.msg("No player with the specified database id of " +
                "{0} has been found. Please check the list ".format(name) +
                "of available players using the @players command.")
            return None
    else:
        # check that a player with the specified name actually exists
        # and that the name does not belong to multiple players
        try:
            player = PlayerDB.objects.get(db_key=name)
        except ObjectDoesNotExist:
            caller.msg("No player with the name {0} has been ".format(name) +
                "found in the database. Please check the list of available " +
                "players using the @ailist command.")
            return None 
        except MultipleObjectsReturned:
            caller.msg("Multiple players with the name {0} ".format(name) +
                "have been found in the database. Please use the " +
                "target player's id instead.") 
            return None

    return player


def tree_from_name(caller, name):
    """
    If there is a single tree in the database that has the given id or name, 
    returns that tree, else returns None

    Caller can be None to accommodate running this function when an AIObject
    or AIScript is loading the tree from a string.
    """
    if name == 'this':
        # check that a tree is currently being browsed
        if caller and caller.player.aiwizard.tree:
            tree = self.caller.player.aiwizard.tree
        else:
            if caller: 
                self.caller.msg("You are not currently browsing any tree, " +
                    "and so you cannot specify a tree via the 'this' " +
                    "keyword. To move the browsing cursor to a given tree, " +
                    "use the @aigo command.")
            return None

    # check whether the name is a database id
    elif all([x in string.digits for x in name]):
        tree = ScriptDB.objects.get_id(name)
        if not tree:
            if caller:
                caller.msg("No tree with the specified database id of " +
                    "{0} has been found. Please check the list ".format(name) +
                    "of available trees using the @ailist command.")
            return None
    else:
        # check that a tree with the specified name actually exists
        # and that the name does not belong to multiple scripts
        try:
            tree = ScriptDB.objects.get(db_key=name)
        except ObjectDoesNotExist:
            if caller:
                caller.msg("No tree with the name {0} has been ".format(name) +
                    "found in the database. Please check the list of " +
                    "available trees using the @ailist command.")
            return None 
        except MultipleObjectsReturned:
            if caller:
                caller.msg("Multiple scripts with the name {0} ".format(name) +
                    "have been found in the database. Please use the target " +
                    "tree's id instead.")
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


def agent_from_name(caller, obj_type, name):
    """
    If there is a single AI object or AI script in the database that has the 
    given name or id, returns that object or script, else returns None
    """
    global _AI_OBJECT
    global _AI_SCRIPT
    if not _AI_OBJECT:
        from evennia.contrib.aisystem.typeclasses import (AIObject
            as _AI_OBJECT)
    if not _AI_SCRIPT:
        from evennia.contrib.aisystem.typeclasses import (AIScript
            as _AI_SCRIPT)

    # check if the name is a database id
    if obj_type == _AI_OBJECT:
        obj_model = ObjectDB
        obj_type_name = "object"
    elif obj_type == _AI_SCRIPT:
        obj_model = ScriptDB
        obj_type_name = "script"
    else:
        raise TypeError("AI agent must be either an AIObject or an AIScript.")


    if all([x in string.digits for x in name]):
        agent = db.objects.get_id(name)
        if agent:
            return agent
        else:
            caller.msg("No blackboard with the id {0} has been ".format(name) +
                "found in the database.")
            return None

    if name == 'this':
        # check that a tree is currently being browsed
        if self.caller.player.aiwizard.agent:
            agent = self.caller.player.aiwizard.agent
        else:
            self.caller.msg("You are not currently browsing any blackboard, " +
                "and so you cannot specify a blackboard via the 'this' " +
                "keyword. To move the browsing cursor to a given " +
                "blackboard, use the @aibb command.")
            return None

    # check if the name belongs to any object of the appropriate type
    # in the database
    try:
        agent = obj_model.objects.get(db_key = name)
    except ObjectDoesNotExist:
        caller.msg("No {0} with the name {1} has been ".format(obj_type_name, 
            name) + "found in the database.")
        return None

    except MultipleObjectsReturned:
        caller.msg("Multiple {0}s with the name ".format(obj_type_name) +
            "{0} have been found in the database. Please use ".format(name) +
            " the target tree's id instead.")
        return None

    return agent


# The indentation used by the various display functions
s_indent = " |G*|n  "


def display_node_in_tree(caller, tree, node):
    """
    Displays information pertaining to a given node in a tree:
    its tree, the name and hash values of its parent and children, as well as
    its attributes
    """
    # get the node's parent
    if node.parent:
        parent = "|w{0}|n '{1}'(\"{2}\")".format(type(node.parent).__name__,
            node.parent.hash[0:3], node.parent.name)
    else:
        parent = "None"
    
    # get the node's children
    if isinstance(node, CompositeNode):
        children = [x.name for x in node.children]
    elif node.children:
        children = "|w{0}|n '{1}'(\"{2}\")".format(
            type(node.children).__name__, node.children.hash[0:3], 
            node.children.name)
    else:
        children = "None"

    # get the node's siblings, if any
    if (node.parent and isinstance(node.parent, CompositeNode) and
        len(node.parent.children) > 1):
        siblings = [x.name for x in node.parent.children
            if x != node]
    else:
        siblings = None

    # get the node's attributes
    attrs = [x for x in dir(node) if x[0] != '_']

    # do not include the node's name amongst its attributes
    attrs.remove('name')

    nonfuncs = {}
    for attr_name in attrs:
        attr = getattr(node, attr_name)
        if not hasattr(attr, '__call__'):
            nonfuncs[attr_name] = attr

    s = "\n|y{0}|n '{1}'(\"{2}\")\n".format(type(node).__name__,
        node.hash[0:3], node.name)
    s += "|x" + "-" * (len(s) - 5) + "|n\n"
    s += "|yTree:|n {0} (id {1})\n".format(tree.name, tree.id)
    s += "|yParent:|n {0}\n".format(parent)
    if isinstance(children, str):
        s += "|yChild:|n {0}\n".format(children)
    else:
        s += "|yChildren:|n\n"
        for child in children:
            s += s_indent + "|w{0}|n '{1}'(\"{2}\")".format(
                type(child).__name__, child.hash[0:3], child.name)
    if siblings:
        s += "|ySiblings:|n\n"
        for sibling in siblings:
            s += s_indent + "|w{0}|n '{1}'(\"{2}\")".format(
                type(sibling).__name__, sibling.hash[0:3], sibling.name)
    s += "|yAttributes:|n\n"
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
    global _AI_OBJECT
    global _AI_SCRIPT
    if not _AI_OBJECT:
        from evennia.contrib.aisystem.typeclasses import (AIObject
            as _AI_OBJECT)
    if not _AI_SCRIPT:
        from evennia.contrib.aisystem.typeclasses import (AIScript
            as _AI_SCRIPT)

    data = bb['nodes'][node.hash]

    # get the node's parent
    if node.parent:
        parent = "|w{0}|n '{1}'(\"{2}\")".format(type(node.parent).__name__,
            node.parent.hash[0:3], node.parent.name) 
    else:
        parent = None

    # get the node's children
    if isinstance(node, CompositeNode):
        children = [x.name for x in node.children]
    elif node.children:
        children = "|w{0}|n '{1}'(\"{2}\")".format(
            type(node.children).__name__, node.children.hash[0:3],
            node.children.name)
    else:
        children = "None"

    # get the node's siblings, if any
    if (node.parent and isinstance(node.parent, CompositeNode) and
        len(node.parent.children) > 1):
        siblings = [x.name for x in node.parent.children
            if x != node]
    else:
        siblings = None
   
    if isinstance(bb['agent'], _AI_OBJECT):
        owner_type = "AI agent"
        owner_name = bb['agent'].name
    elif isinstance(bb['agent'], _AI_SCRIPT):
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
            s += s_indent + "|w{0}|n '{1}'(\"{2}\")".format(
                type(child).__name__, child.hash[0:3], child.name)
    if siblings:
        s += "|gSiblings:|n\n"
        for sibling in siblings:
            s += s_indent + "|w{0}|n '{1}'(\"{2}\")".format(
                type(sibling).__name__, sibling.hash[0:3], sibling.name)
    s += "\n|gData:|n\n"
    for key, val in data.iteritems():
        s += parse_attr(key, val, 1)

    evmore.msg(caller, s)


def display_bb_globals(caller, bb):
    """
    Displays the global parameters of the currently browsed blackboard
    """
    global _AI_OBJECT
    global _AI_SCRIPT
    if not _AI_OBJECT:
        from evennia.contrib.aisystem.typeclasses import (AIObject
            as _AI_OBJECT)
    if not _AI_SCRIPT:
        from evennia.contrib.aisystem.typeclasses import (AIScript
            as _AI_SCRIPT)

    if isinstance(bb['agent'], _AI_OBJECT):
        owner_type = "AI agent"
        owner_name = bb['agent'].name
    elif isinstance(bb['agent'], _AI_SCRIPT):
        owner_type = "AI script"
        owner_name = bb['agent'].name
    else:
        owner_type = type(bb['agent'])
        owner_name = str(bb['agent'])

    s = "Blackboard globals for |g{0}|n {1}:\n".format(owner_type, owner_name)
    for key, val in bb['globals'].iteritems():
        s += parse_attr(key, val, 1)
        
    evmore.msg(caller, s)


def parse_attr(attr_name, attr, indent):
    """
    Parse a given attribute into a string and return it.
    This function is meant to be recursive in the event that the attribute
    is a string or an int.

    Reports lists and SaverLists as 'list', tuples as 'tuple',
    dicts and SaverDicts as 'dict'.
    """
    s = ""
    k_indent = s_indent * indent # current level of indentation
    if (isinstance(attr, list) or isinstance(attr, _SaverList)):
        if attr_name:
            s += k_indent + "|GList|n {0}:\n".format(attr_name)
        else:
            s += k_indent + "|GList|n:\n"
        for val in attr:
            s += parse_attr("", val, indent + 1)
        return s

    elif isinstance(attr, tuple):
        if attr_name:
            s += k_indent + "|GTuple|n {0}:\n".format(attr_name)
        else:
            s += k_indent + "|GTuple|n:\n"
        for val in attr:
            s += parse_attr("", val, indent + 1)
        return s

    elif isinstance(attr, dict) or isinstance(attr, _SaverDict):
        if attr_name:
            s += k_indent + "|GDict|n {0}:\n".format(attr_name)
        else:
            s += k_indent + "|GDict|n:\n"
        for key, val in attr.iteritems():
            s += parse_attr(key, val, indent + 1)
        return s

    else:
        if attr_name:
            return k_indent + "{0}: {1}\n".format(attr_name, attr)
        else:
            return k_indent + str(attr) + "\n"


