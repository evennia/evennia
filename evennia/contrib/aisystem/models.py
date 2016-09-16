"""
Database models for behavior trees and behavior blackboards

A behavior tree model stores all the node types and their relationships
within the tree in db_root. Accessing db_root is equivalent to accessing
the root node. db_root does not contain any data pertaining to a given
instance of the tree, so that the same tree can be used by multiple agents,
each agent storing the tree-related data in its own blackboard.

A behavior blackboard model is associated with a single agent and stores
all information related to the state of that agent's behavior tree. This
information includes which nodes are currently running, which nodes were
running during the previous tick, as well as all global and node-specific
user-specified data.

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

"""


from __future__ import unicode_literals

import copy
from django.db import models
from evennia.utils.idmapper.models import SharedMemoryModel
from evennia.contrib.aisystem.nodes import (Node, RootNode, CompositeNode, 
    LeafNode)


class BehaviorTreeDB(SharedMemoryModel):
    """
    The BehaviorTree provides the following properties:

     - key - main name
     - name - alias for 'key'
     - db_date_created - time stamp of object creation
     - root - TextField that stores the entirety of the tree. It is called
        root because referencing it from within the game actually references
        the root node.
     - db_nodes - a dictionary of all the tree's node objects, using the hash
        values of the nodes as keys. Used internally for creating, moving and
        deleting nodes as well as for populating the 'nodes' dictionary of each
        blackboard associated with the tree.
    """
    db_key = models.CharField('key', max_length=80, db_index=True)
    db_date_created = models.DateTimeField('date created', editable=False,
        auto_now_add=True, db_index=False)
    db_root = models.TextField('root', null=True, blank=True)
    db_nodes = models.TextField('node dict', default='', null=True,
        blank=True)

    class Meta(object):
        verbose_name = 'behavior tree'
        app_label = 'aisystem'

    def __unicode__(self):
        return u"%s(behavior tree #%s)" % (self.name, self.id)

    @property
    def name(self):
        """
        Alternative name for db_key
        """
        return self.db_key

    @name.setter
    def name(self, value):
        self.db_key = value

    def setup(self):
        """
        Called when the tree is created. Gives the tree a root node.
        """
        self.db_nodes = {}
        self.db_root = RootNode("Root node", self, None)

    def rename(self, node, name):
        """
        Changes a node's name.
        """
        node.name = name

    def recursive_add_hash(self, node):
        """
        Add the node and its subtree to this tree, setting the hashes
        for all of the subtree's nodes
        """
        if not self.db_nodes.has_key(node.hash):
            self.db_nodes[node.hash] = node
        elif (self.db_nodes.has_key(node.hash) and 
            self.db_nodes[node.hash] != node):
            node.hash = node.rehash(self)
            self.db_nodes[node.hash] = node

        if isinstance(node, CompositeNode):
            for child in node.children:
                self.recursive_add_hash(child)
        elif node.children:
            self.recursive_add_hash(node.children)

    def recursive_remove_hash(self, node):
        """
        Remove the node and its subtree from this tree
        """
        if (self.db_nodes.has_key(node.hash) and
            self.db_nodes[node.hash] == node):
            self.db_nodes.pop(node.hash)

        if isinstance(node, CompositeNode):
            for child in node.children:
                self.recursive_remove_hash(child)
        elif node.children:
            self.recursive_remove_hash(node.children)                
   

    def check_node_in_tree(self, node, source_tree=None, msg="operation"):
        """
        Checks whether the node is in the source tree, or in this tree
        if source_tree=None.

        Returns an error string on failure, returns None on success.
        """
        if not source_tree and not (self.db_nodes.has_key(node.hash) and 
            self.db_nodes[node.hash] == node):
            return ("the node '{0}'(\"{1}\") ".format(node.hash, node.name) + 
                "is not in the target tree, yet no source tree " +
                "was provided. The node {0} cannot proceed.".format(msg))
        elif source_tree and not (source_tree.db_nodes.has_key(node.hash) and
            source_tree.db_nodes[node.hash] == node):
            return ("the node '{0}'(\"{1}\") ".format(node.hash, node.name) + 
                "could not be found in its purported source tree. " +
                "The node {0} cannot proceed.".format(msg))
        return None 

    def add(self, node, target, position=None, copying=True, 
            source_tree=None):
        """
        Attempts to add a node to the tree, attaching it to the parent node
        if it either has no children of its own or is a composite node.
        If the node already has a parent, and copying is false, the node will
        be removed from that parent's list of children.
        The hash values of the node and its children will be recomputed as
        necessary when being copied or added in from another tree.

        Arguments:

        node - the node to be added
        (node)

        target - the node that will become the added node's new parent
        (node)

        position - if the target node is a composite node, the position that
        (int)      the added node will have in the target node's list of
                   children
        
        copying - whether the node and its subtree is being copied. If true,
        (bool)    an entirely new node and subtree will be grafted onto the
                  target. If false, the node and its subtree will be removed
                  from the node's original parent and tree before being added
                  to the target.
                  Note that, when copying is True, on_remove_node(node) will
                  point to the old node object, not the new one. The two
                  objects are identical apart from their memory address,
                  but you should probably not make modifications to the old
                  node object in this method. on_add_node(node) points to the
                  new node object, so it's fine to make modifications here.

        source_tree - the tree to which the node originally belongs. If set to
        (tree)        None, the node is assumed to belong to the target tree.
                      No operations on any tree's db_nodes property will occur
                      when the source tree is set to None or the target tree.

        Returns an error string on failure, returns None on success.
        """
        if not isinstance(node, Node):
            return ("{0} is a {1}, not a node; ".format(node, type(node)) +
                "expected a node.")
        if not isinstance(target, Node):
            return ("target {0} is a {1}, not a ".format(node, type(node)) +
                "node; expected a node.")

        if isinstance(node, RootNode):
            return ("node '{0}(\"{1}\") is a ".format(node.hash, node.name) +
                "root node. It may not be added as the child of any node.")

        # check that the node is in the source tree, if one exists
        if source_tree:
            errstr = self.check_node_in_tree(node, source_tree=source_tree, 
                msg="addition")
            if errstr:
                return errstr

        # prevent modifying the source or target tree if they are the same
        if source_tree == self:
            source_tree = None

        old_node = node
        if copying:
            node = copy.deepcopy(node)

        parent = node.parent
        if not target:
            target = self.db_root

        if isinstance(target, CompositeNode):
            # if target is a composite node, add the node to the target
            if position != None:
                target.children.insert(position, node)
            else:    
                target.children.append(node)
        elif isinstance(target, LeafNode):
            # prohibit adding to a leaf node
            return ("target node '{0}'(\"{1}\") ".format(target.hash, 
                target.name) + "is a leaf node, cannot add node " +
                "'{0}'(\"{1}\") to it as leaf ".format(node.hash, node.name) +
                "nodes are prohibited from having child nodes.")
        elif not target.children:
            # if target is not a leaf node and has no children, add the node
            # to the target
            target.children = node
        else:
            # prohibit adding to a non-composite target node that has a child
            return ("target node '{0}'(\"{1}\") is a ".format(target.hash,
                target.name) + " non-composite node with a child, cannot " +
                "add another node to it.")
 
        node.parent = target
        target.on_add_child(node)

        # remove the target from its parent
        if parent and not copying:
            if isinstance(parent, CompositeNode):
                parent.children.remove(old_node)
            else:
                parent.children = None
            parent.on_remove_child(old_node)
            
            # remove the target from its source tree, if different from the
            # target tree
            if source_tree:
                source_tree.recursive_remove_hash(old_node)

        # if the node is being copied, or added in from another tree,
        # recompute its hashes
        if source_tree or copying:
            self.recursive_add_hash(node)

        return None # No error occurred

    def shift(self, node, position=None):
        """
        Attempts to shift the node to a new position in its parent's list of
        children. If the parent is not a composite node, the attempt fails.

        See the add() method for a description of the arguments.
        """
        if not isinstance(node, Node):
            return ("{0} is a {1}, not a node; ".format(node, type(node)) +
                "expected a node.")

        if isinstance(node, RootNode):
            return ("node '{0}(\"{1}\") is a ".format(node.hash, node.name) +
                "root node. It may not be shifted as it has no parent.")

        if isinstance(node.parent, CompositeNode):
            index = node.parent.children.index(node)
            node.parent.children[index] = None
            if position != None:
                node.parent.children.insert(position, node)
            else:
                node.parent.children.append(node)
            node.parent.children.remove(None)
        else:
            return ("Parent node '{0}'(\"{1}\") ".format(node.parent.hash, 
                node.parent.name) + "is not a composite node, cannot shift " + 
                "node '{0}'(\"{1}\").".format(node.hash, node.name))

    def swap(self, node, target, source_tree=None):
        """
        Swaps the parents of two different nodes.
        If the nodes are on separate trees, their hashes and the hashes of
        all their children will be rewritten.

        See the add() method for a description of the arguments.
        """
        if not isinstance(node, Node):
            return ("{0} is a {1}, not a node; ".format(node, type(node)) +
                "expected a node.")
        if not isinstance(target, Node):
            return ("target {0} is a {1}, not a ".format(node, type(node)) +
                "node; expected a node.")

        # check that the node is in the source tree or the target tree
        errstr = self.check_node_in_tree(node, source_tree=source_tree,
            msg="swapping")
        if errstr:
            return errstr

        # prevent modifying the source or target tree if they are the same
        if source_tree == self:
            source_tree = None

        target_parent = target.parent
        node_parent = node.parent

        if not node_parent:
            return ("Node '{0}'(\"{1}\") has ".format(node.hash, node.name) +
                "no parent; the swapping cannot proceed.")
 
        if not target_parent:
             return ("Target node '{0}'(\"{1}\") has ".format(target.hash,
                target.name) + "no parent; the swapping cannot proceed.")

        # remove the target from its parent,
        # add the node to the target's parent
        if isinstance(target_parent, CompositeNode):
            target_index = target_parent.children.index(target)
            target_parent.children.remove(target)
            target_parent.children.insert(target_index, node)
        else:
            target_parent.children = node
        target_parent.on_remove_child(target)

        # remove the node from its parent,
        # add the target to the node's parent
        if isinstance(node_parent, CompositeNode):
            node_index = node_parent.children.index(node)
            node_parent.children.remove(node)
            node_parent.children.insert(node_index, target)
        else:
            node_parent.children = target
        node_parent.on_remove_child(node)

        # modify the source_tree and this tree to account for the
        # two nodes' transitions
        if source_tree:
            self.recursive_remove_hash(target)
            source_tree.recursive_remove_hash(node)
            self.recursive_add_hash(node)
            source_tree.recursive_add_hash(target)

        node.parent = target_parent
        target_parent.on_add_child(node)

        target.parent = node_parent
        node_parent.on_add_child(target)

        return None # No error occurred

    def interpose(self, node, target, position=None, copying=True, 
        source_tree=None):
        """
        Places a node between the target and its parent. If the target's
        parent is a composite node, the node will be placed at the same
        position in that parent's list of children as the target.
        If the node itself is a composite node, a position value may
        be added to determine where the target node should be inserted
        in the node's list of children.

        The interpose method is very useful for decorators.

        See the add() method for a description of the arguments.
        """
        if not isinstance(node, Node):
            return ("{0} is a {1}, not a node; ".format(node, type(node)) +
                "expected a node.")
        if not isinstance(target, Node):
            return ("target {0} is a {1}, not a ".format(node, type(node)) +
                "node; expected a node.")

        if node == target:
            return ("node '{0}'(\"{1}\") is ".format(node.hash, node.name) + 
                "also the target of interposing; cannot interpose a node " +
                "onto itself.")

        if isinstance(node, RootNode):
            return ("Node '{0}'(\"{1}\") ".format(node.hash, node.name) +
                "is a root node, cannot interpose it over any other node.")

        # check that the node is in the source tree or the target tree
        errstr = self.check_node_in_tree(node, source_tree=source_tree,
            msg="interposition")
        if errstr:
            return errstr

        # prevent modifying the source or target tree if they are the same
        if source_tree == self:
            source_tree = None

        old_node = node
        if copying:
            node = copy.deepcopy(node)

        node_parent = node.parent
        target_parent = target.parent

        if not target_parent:
            return ("Target node '{0}'(\"{1}\") has no ".format(
                target.hash, target.name) + "parent, " +
                "cannot interpose over it.")

        # add the node to the target's parent's list of children
        # and remove the target from that list
        if isinstance(target_parent, CompositeNode):
            target_index = target_parent.children.index(target)
            target_parent.children.remove(target)
            target_parent.on_remove_child(target)
            target_parent.children.insert(target_index, node)
            target_parent.on_add_child(node)
        else:
            target_parent.children = node
            target_parent.on_remove_child(target)
            target_parent.on_add_child(node)
        node.parent = target_parent

        # remove the node from its former parent's list of children
        if not copying:
            if isinstance(node_parent, CompositeNode):
                node_parent.children.remove(old_node)
                node_parent.on_remove_child(old_node)       
            elif node_parent:
                node_parent.children = None
                node_parent.on_remove_child(old_node)

        if source_tree and not copying:
            source_tree.recursive_remove_hash(old_node)
            
        # add the target to the node's list of children 
        if isinstance(node, CompositeNode):
            if position != None:
                node.children.insert(position, target)
            else:
                node.children.append(target)
        else:
            node.children = target
        node.on_add_child(target)
        target.parent = node

        if source_tree or copying:
            self.recursive_add_hash(node)

        return None # No error occurred

    def remove(self, node):
        """
        removes a node and its children from the tree
        """
        if not isinstance(node, Node):
            return ("{0} is a {1}, not a node; ".format(node, type(node)) +
                "expected a node.")

        if isinstance(node, RootNode):
            return ("Node '{0}'(\"{1}\") ".format(node.hash, node.name) +
                "is a root node and so cannot be removed from its tree.")

        self.recursive_remove_hash(node)

        parent = node.parent
        if isinstance(node.parent, CompositeNode):
            node.parent.children.remove(node)
        elif node.parent:
            node.parent.children = None
        node.parent = None
        parent.on_remove_child(node)

        return None # No error occurred        


class BehaviorBlackboardDB(SharedMemoryModel):
    """
    The BehaviorBlackboard provides the following properties:

     - key - main name
     - name - alias for 'key'
     - db_date_created - time stamp of object creation
     - tree - the behavior tree  
     - running_now - a list of all the nodes that are running in the
        current tick. 
     - running_pre - a list of all the nodes that were running in the
        previous tick.
     - nodes - a dictionary of node-specific data. The dictionary's keys are
        the hash values of the nodes, and its values are in turn dictionaries.
     - global - a dictionary of global data.
    """

    db_key = models.CharField('key', max_length=80, db_index=True)
    db_date_created = models.DateTimeField('date created', editable=False,
        auto_now_add=True, db_index=False)
    db_tree = models.ForeignKey(BehaviorTreeDB, verbose_name='tree', null=True)
    db_agent = models.ForeignKey('objects.ObjectDB', verbose_name='agent', 
        null=True)
    db_running_now = models.TextField('active', default='[]', null=True, 
        blank=True)
    db_running_pre = models.TextField('active pre', default='[]', null=True, 
        blank=True)
    db_nodes = models.TextField('node data', default='', null=True, 
        blank=True)
    db_global = models.TextField('global data', default='', null=True, 
        blank=True)

    class Meta(object):
        verbose_name = 'behavior blackboard'
        app_label = 'aisystem'

    def __unicode__(self):
        return u"%s(behavior blackboard #%s)" % (self.name, selfbid)

    @property
    def name(self):
        """
        Alternative name for db_key
        """
        return self.db_key

    @name.setter
    def name(self, value):
        self.db_key = value

    def tick(self):
        """
        Prepare the behavior tree for the new tick, then go through the tree
        starting from the root node.
        """
        # close all nodes that were running two ticks ago but were not running
        # in the past tick
        for node in self.db_running_pre.keys:
            if node not in self.db_running_now:
                node.close()

        # swap the list of currently running nodes with the list of previously
        # running nodes, clear the list of currently running nodes
        self.db_running_pre = self.db_running_now 
        self.db_running_now = []

        # tick the root node
        return self.db_tree.db_root.tick(self)

    def setup(self):
        pass        



