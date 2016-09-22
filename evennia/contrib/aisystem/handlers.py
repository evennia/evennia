"""
A handler for the AI system. The handler contains a reference to an AI tree, 
a list of nodes that are currently running, a list of nodes that were running
during the previous iteration of the tree, as well as a "blackboard" of
node-specific and global data.

The following names for node-specific blackboard data are reserved, so use
them only for their intended purpose:

weight (float) - the probabilistic weight of a given node. When the node is the
                 direct child of a probabilistic composite node, its weight
                 affects the probability that it will be ticked before the
                 composite node's other child nodes. Note that probabilistic
                 composite nodes treat weight-less nodes as if their weight
                 is 1.

child_weights (dict of floats) - a dict of the weights of all child nodes.
                                 The keys are the child nodes' indices in the
                                 parent node's list of children. When used by
                                 a probabilistic node, this dict allows a
                                 random number to determine which of the nodes
                                 will be selected next.

avail_weights (dict of floats) - a dict of the weights of all child nodes that
                                 are available for ticking. The keys are the
                                 nodes' indices in the parent node's list of
                                 children.

states (list of ints) - a list of the states returned by all children of the
                        node; can include values of None for children that have
                        not yet returned a state. Used by parallel nodes.

primary_child (int) - for parallel nodes, one child of the node whose
                      completion immediately triggers the parallel node's own
                      completion, the parallel node's return status being the
                      same as that of the primary child.

req_successes (int) - used by parallel nodes; represents the number of child
                      nodes that must return success for the parallel node
                      itself to immediately return success.

req_failures (int) - used by parallel nodes; represents the number of child
                     nodes that must return success for the parallel node
                     itself to immediately return success.

default_success (bool) - used by parallel nodes to decide whether to return
                         success when all child nodes have completed but
                         no other condition has been met for returning a status

running (bool) - whether or not the node is currently running or was running
                 during its last tick.

running_child (int) - the currently running child of a MemSequence or 
                      MemSelector node.

ticks (int) - for repeater nodes, this is the number of repeats that have
              already been performed since the repeater started running. For
              limiter nodes, this is the number of repeats left before the
              limiter shuts down. 

watchers (list) - a list of all the players that are currently watching the
                  node

The following names for global blackboard data are reserved, so use them only
for their intended purpose:

resources (dict) - a dictionary with the names of resources as keys and the
                   things using them as values. See the resource allocator
                   node for details about this.

errors (dict) - a dictionary with the hashes of nodes as keys and the error
                strings they returned during the most recent iteration of the
                blackboard as values.
"""

from evennia import ObjectDB, ScriptDB
from evennia.contrib.aisystem.utils import recurse_multitree

_BEHAVIOR_TREE = None #delayed import


class AIHandler(object):
    """
    Stores a dictionary called 'ai' that contains the following fields:
    
    tree (BehaviorTree) - the behavior tree whose structure the AI handler uses

    agent (object etc.) - the agent that the tree operates on; only one of the
                          leaf nodes that come with the AI system (the Command 
                          node) assumes this is an object, so you can safely
                          use any type here if you don't plan on employing that
                          node.

    running_now (list) - a list of the currently running nodes.

    running_pre (list) - a list of the nodes that were running in the previous
                         iteration through the tree

    nodes (dict) - a dictionary of node hashes whose values are dictionaries of
                   the properties of these nodes.

    globals (dict) - a dictionary of properties that are global to the handler

    Together, the nodes and globals dictionary form the AI "blackboard" of the
    object or script to which the handler is attached.
    """
    @property
    def tree(self):
        return self.owner.db.ai['tree']

    @tree.setter
    def tree(self, value):
        self.owner.db.ai['tree'] = value

    @tree.deleter
    def tree(self):
        del self.owner.db.ai['tree']

    @property
    def agent(self):
        return self.owner.db.ai['agent']
    
    @agent.setter
    def agent(self, value):
        self.owner.db.ai['agent'] = value

    @agent.deleter
    def agent(self):
        del self.owner.db.ai['agent']

    @property
    def running_now(self):
        return self.owner.db.ai['running_now']

    @running_now.setter
    def running_now(self, value):
        self.owner.db.ai['running_now'] = value

    @running_now.deleter
    def running_now(self):
        del self.owner.db.ai['running_now']

    @property
    def running_pre(self):
        return self.owner.db.ai['running_pre']

    @running_pre.setter
    def running_pre(self, value):
        self.owner.db.ai['running_pre'] = value

    @running_pre.deleter
    def running_pre(self):
        del self.owner.db.ai['running_pre']

    @property
    def nodes(self):
        return self.owner.db.ai['nodes']

    @nodes.setter
    def nodes(self, value):
        self.owner.db.ai['nodes'] = value

    @nodes.deleter
    def nodes(self):
        del self.owner.db.ai['nodes']

    @property
    def globals(self):
        return self.owner.db.ai['globals']

    @globals.setter
    def globals(self, value):
        self.owner.db.ai['globals'] = value

    @globals.deleter
    def globals(self):
        del self.owner.db.ai['globals']

    def __init__(self, owner):
        """
        sets the handler's owner, i.e. the object or script to which the
        handler is attached
        """
        self.owner = owner

    def tick(self):
        """
        Prepare the behavior tree for the new tick, then go through the tree
        starting from the root node.
        """
        # close all nodes that were running two ticks ago but were not running
        # in the past tick
        for node in self.owner.db.ai['running_pre']:
            if node not in self.owner.db.ai['running_now']:
                node.close(self.owner.db.ai)

        # swap the list of currently running nodes with the list of previously
        # running nodes, clear the list of currently running nodes
        self.owner.db.ai['running_pre'] = self.owner.db.ai['running_now']
        self.owner.db.ai['running_now'] = []

        # tick the root node
        tree = self.owner.db.ai['tree']
        return tree.nodes[tree.root].tick(self.owner.db.ai)

    def setup(self, tree=None, override=False):
        """
        Sets up the attributes associated with the AI handler. If override
        is set to True, replaces all these attributes with the defaults.

        If setup succeeds, it returns "none". Otherwise, it returns an error
        string.
        """
        global _BEHAVIOR_TREE

        if not _BEHAVIOR_TREE:
            from evennia.contrib.aisystem.typeclasses import (BehaviorTree
                as _BEHAVIOR_TREE)

        if isinstance(self.owner, ObjectDB):
            obj_type_name = "object" 
        elif isinstance(self.owner, ScriptDB):
            obj_type_name = "script"
        else:
            raise TypeError("Unknown type for AI agent {0} ".self.owner.name +
                "(id {0}).".format(self.owner.id))

        if not tree:
            if hasattr(self.owner,'aitree') and self.owner.aitree:
                # first use the object's class tree as the desired tree

                # check if the tree is a BehaviorTree
                if isinstance(self.owner.aitree, _BEHAVIOR_TREE):
                    tree = self.owner.aitree

                elif (isinstance(self.owner.aitree, str) or
                    isinstance(self.owner.aitree, unicode)):
                    tree = tree_from_name(None, self.owner.aitree)
                    if not tree:
                        return ("No tree with the name or hash of " +
                            "{0} has been found ".format(self.owner.aitree) +
                            "in the database.")

            elif (self.owner.attributes.has("ai") and
                self.owner.db.ai.has_key('tree')):
                # if no class tree exists, see if the object has already been
                # assigned a tree through some other means, and use that 
                # instead
                tree = self.owner.db.ai['tree']
            else:
                return ("No tree found in either the blackboard or the " +
                    "class of {0} {1} (id {2}). ".format(obj_type_name, 
                    self.owner.name, self.owner.id) + "Please assign the ." +
                    "agent a tree via the @aiassign command before trying " +
                    "to set it up.")

        # confirm that the tree is valid
        try:
            tree.validate_tree()
        except Exception as e:
            return e

        if not self.owner.attributes.has('ai') or override:
            self.owner.db.ai = {}

        if not self.owner.db.ai.has_key('tree') or override:
            self.owner.db.ai['tree'] = tree

        if not self.owner.db.ai.has_key('agent') or override:
            self.owner.db.ai['agent'] = self.owner

        if not self.owner.db.ai.has_key('running_pre') or override:
            self.owner.db.ai['running_pre'] = []

        if not self.owner.db.ai.has_key('running_now') or override:
            self.owner.db.ai['running_now'] = []

        if not self.owner.db.ai.has_key('nodes') or override:
            self.owner.db.ai['nodes'] = {}

        if not self.owner.db.ai.has_key('globals') or override:
            self.owner.db.ai['globals'] = {'resources':{}, 'errors':{}}

        # setup the blackboard's dictionary of nodes
        def recursive_setup_node_dict(node):
            self.owner.db.ai['nodes'][node.hash] = {'running': False,
                'watchers':[]}
            recurse_multitree(node, recursive_setup_node_dict)

        # run on_blackboard_setup for all nodes
        def recursive_setup_node_call(node):
            node.on_blackboard_setup(self.owner.db.ai, override=override)
            recurse_multitree(node, recursive_setup_node_call)

        root = self.owner.db.ai['tree'].nodes[self.owner.db.ai['tree'].root]

        if self.owner.db.ai['nodes'] == {}:
            recursive_setup_node_dict(root)
        recursive_setup_node_call(root)

        return None


class AIWizardHandler(object):
    @property
    def tree(self):
        return self.owner.db.aiwizard['tree']
    
    @tree.setter
    def tree(self, value):
        self.owner.db.aiwizard['tree'] = value

    @tree.deleter
    def tree(self):
        del self.owner.db.aiwizard['tree']

    @property
    def node(self):
        return self.owner.db.aiwizard['node']

    @node.setter
    def node(self, value):
        self.owner.db.aiwizard['node'] = value

    @node.deleter
    def node(self):
        del self.owner.db.aiwizard['node']

    @property
    def agent(self):
        return self.owner.db.aiwizard['agent']

    @agent.setter
    def agent(self, value):
        self.owner.db.aiwizard['agent'] = value

    @agent.deleter
    def agent(self):
        del self.owner.db.aiwizard['agent']

    @property
    def watching(self):
        return self.owner.db.aiwizard['watching']

    @watching.setter
    def watching(self, value):
        self.owner.db.aiwizard['watching'] = value

    @watching.deleter
    def watching(self):
        del self.owner.db.aiwizard['watching']

    def __init__(self, owner):
        """
        sets the handler's owner, i.e. the object or script to which the
        handler is attached
        """
        self.owner = owner

    def setup(self, override=False):
        """
        Sets up the attributes associated with the AI handler. If override
        is set to True, replaces all these attributes with the defaults.   
        """
        if not self.owner.attributes.has('aiwizard') or override:
            self.owner.db.aiwizard = {}

        if not self.owner.db.aiwizard.has_key('tree') or override:
            self.owner.db.aiwizard['tree'] = None

        if not self.owner.db.aiwizard.has_key('node') or override:
            self.owner.db.aiwizard['node'] = ''

        if not self.owner.db.aiwizard.has_key('agent') or override:
            self.owner.db.aiwizard['agent'] = None

        if not self.owner.db.aiwizard.has_key('watching') or override:
            self.owner.db.aiwizard['watching'] = []

