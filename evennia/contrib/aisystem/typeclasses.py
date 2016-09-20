"""
Typeclasses for behavior trees, AI objects and free-floating AI scripts.

A behavior tree model stores all the node types and their relationships
within the tree in its root node. The root node does not contain any data
pertaining to a given instance of the tree, but merely the structure of
the tree itself, so that the same tree can be used by multiple agents,
each agent storing the tree-related data in its own blackboard.

An AI object contains a handler that can be used to access all information
related to the state of that agent's behavior tree. This information
includes which nodes are currently running, which nodes were running during
the previous tick, as well as all global and node-specific user-specified data.
"""

#[WIP] ALL METHODS THAT CHANGE A NODE'S TREE SHOULD CHANGE SELF.TREE AS WELL!!!
#[WIP] SAVE THE TREES AFTER EVERY CHANGE BY RE-ATTACHING THEIR ROOTS!
#[WIP] TAKE NODES OUT OF ALL WATCH LISTS WHEN REMOVING THEM OR THEIR (IN)DIRECT
#      PARENTS!

import copy
from evennia import DefaultObject, DefaultScript, DefaultPlayer
from evennia.utils import lazy_property
from evennia.contrib.aisystem.handlers import AIHandler, AIWizardHandler
from evennia.contrib.aisystem.nodes import (recurse, recurse_multitree, Node, 
    RootNode, CompositeNode, LeafNode, DecoratorNode, Condition, Command,
    Selector, Sequence, MemSelector, MemSequence, ProbSelector, ProbSequence,
    Parallel, Verifier, Inverter, Succeeder, Failer, Repeater, Limiter,
    Allocator)


class BehaviorTree(DefaultScript):
    """
    The BehaviorTree provides the following properties:

     - root - stores the entirety of the tree. This property is called root
        because referencing it from within the game actually references the
        root node.
     - nodes - a dictionary of all the tree's node objects, using the hash
        values of the nodes as keys. Used internally for creating, moving and
        deleting nodes as well as for populating the 'nodes' dictionary of each
        AI handler associated with the tree.
    """
    @property
    def root(self):
        return self.db.root

    @root.setter
    def root(self, value):
        self.db.root = value

    @root.deleter
    def root(self):
        del self.db.root

    @property
    def nodes(self):
        return self.db.nodes

    @nodes.setter
    def nodes(self, value):
        self.db.nodes = value

    @nodes.deleter
    def nodes(self):
        del self.db.nodes

    def at_script_creation(self):
        super(BehaviorTree, self).at_script_creation()
        self.setup()
        self.desc = "Behavior tree"
        self.persistent = True

    def setup(self):
        """
        Called when the tree is created. Gives the tree a root node.
        """
        self.pause()
        self.db.nodes = {}
        self.db.root = RootNode("root", self, None)

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
        if not self.db.nodes.has_key(node.hash):
            self.db.nodes[node.hash] = node
        elif (self.db.nodes.has_key(node.hash) and 
            self.db.nodes[node.hash] != node):
            node.rehash(self)
            self.db.nodes[node.hash] = node
        recurse(node, self.recursive_add_hash)

    def recursive_remove_hash(self, node):
        """
        Remove the node and its subtree from this tree
        """
        if (self.db.nodes.has_key(node.hash) and
            self.db.nodes[node.hash] == node):
            self.db.nodes.pop(node.hash)
        recurse(node, self.recursive_remove_hash)

    def check_node_in_tree(self, node, source_tree=None, msg="operation"):
        """
        Checks whether the node is in the source tree, or in this tree
        if source_tree=None.

        Returns an error string on failure, returns None on success.
        """
        if not source_tree and not (self.db.nodes.has_key(node.hash) and 
            self.db.nodes[node.hash] == node):
            return ("the node '{0}'(\"{1}\") ".format(node.hash[0:3], 
                node.name) +  "is not in the target tree, yet no source " +
                "tree was provided. The node {0} cannot proceed.".format(msg))
        elif source_tree and not (source_tree.db.nodes.has_key(node.hash) and
            source_tree.db.nodes[node.hash] == node):
            return ("the node '{0}'(\"{1}\") ".format(node.hash[0:3], 
                node.name) +  "could not be found in its purported source " +
                "tree. The node {0} cannot proceed.".format(msg))
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
                      No operations on any tree's db.nodes property will occur
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
            return ("node '{0}(\"{1}\") ".format(node.hash[0:3], node.name) +
                "is a root node. It may not be added as the child of any " +
                "node.")

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
            target = self.root

        if isinstance(target, CompositeNode):
            # if target is a composite node, add the node to the target
            if position != None:
                target.children.insert(position, node)
            else:    
                target.children.append(node)
        elif isinstance(target, LeafNode):
            # prohibit adding to a leaf node
            return ("target node '{0}'(\"{1}\") ".format(target.hash[0:3], 
                target.name) + "is a leaf node, cannot add node " +
                "'{0}'(\"{1}\") to it as leaf ".format(node.hash[0:3], 
                node.name) + "nodes are prohibited from having child nodes.")
        elif not target.children:
            # if target is not a leaf node and has no children, add the node
            # to the target
            target.children = node
        else:
            # prohibit adding to a non-composite target node that has a child
            return ("target node '{0}'(\"{1}\") is a ".format(target.hash[0:3],
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
            return ("node '{0}(\"{1}\") is a ".format(node.hash[0:3], 
                node.name) + "root node. It may not be shifted as it has "
                "no parent.")

        if isinstance(node.parent, CompositeNode):
            index = node.parent.children.index(node)
            node.parent.children[index] = None
            if position != None:
                node.parent.children.insert(position, node)
            else:
                node.parent.children.append(node)
            node.parent.children.remove(None)
        else:
            return ("Parent node '{0}'(\"{1}\") ".format(node.parent.hash[0:3],
                node.parent.name) + "is not a composite node, cannot shift " + 
                "node '{0}'(\"{1}\").".format(node.hash[0:3], node.name))

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
            return ("Node '{0}'(\"{1}\") has ".format(node.hash[0:3], 
                node.name) + "no parent; the swapping cannot proceed.")
 
        if not target_parent:
             return ("Target node '{0}'(\"{1}\") has ".format(target.hash[0:3],
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
            return ("node '{0}'(\"{1}\") is ".format(node.hash[0:3], 
                node.name) +  "also the target of interposing; cannot " +
                "interpose a node onto itself.")

        if isinstance(node, RootNode):
            return ("Node '{0}'(\"{1}\") ".format(node.hash[0:3], node.name) +
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
                target.hash[0:3], target.name) + "parent, " +
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
            return ("Node '{0}'(\"{1}\") ".format(node.hash[0:3], node.name) +
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

    def validate_tree(self):
        def validate(node):
            if isinstance(node, DecoratorNode) and not node.children:
                raise Exception("node '{0}'(\"{1}\")".format(node.hash[0:3],
                    node.name) + "is a decorator node but has no " +
                    "children. Please supply it with a child node or " +
                    "replace it in order for the tree to be valid.")
            elif isinstance(node, RootNode) and not node.children:
                raise Exception("node '{0}'(\"{1}\")".format(node.hash[0:3],
                    node.name) + "is a root node but has no children. " +
                    "Please supply it with a child node in order for " +
                    "the tree to be valid.")
            recurse_multitree(node, validate)

        return validate(self.root)

class AIObject(DefaultObject):
    """
    An object that contains an AI handler. Subclass your own objects from this.

    In order to initialize this object with a given tree, your class must
    provide this line:

    self.aitree = <reference to the desired BehaviorTree>

    For example, if the behavior tree has been specified in-game:

    self.aitree = ScriptDB.objects.get(db_key=<your script's name here>)

    Alternatively, you may assign a behavior tree to your individual objects
    in-game using the @assign command. Note that when calling ai.setup(), 
    unless you provide it a specific tree via ai.setup(tree=<your tree>), it
    will first attempt to select self.aitree as the tree, then whatever
    tree was already assigned to it, if self.aitree does not exist.
    """
    @lazy_property
    def ai(self):
        return AIHandler(self)

    def at_object_creation(self):
        super(AIObject, self).at_object_creation()
        self.ai.setup()


class AIScript(DefaultScript):
    """
    A script that contains an AI handler. Subclass your own scripts from this.

    In order to initialize this script with a given tree, your class must
    provide this line:

    self.aitree = <reference to the desired BehaviorTree>

    For example, if the behavior tree has been specified in-game:

    self.aitree = ScriptDB.objects.get(db_key=<your script's name here>)

    Alternatively, you may assign a behavior tree to your individual scripts
    in-game using the @assign command. Note that when calling ai.setup(), 
    unless you provide it a specific tree via ai.setup(tree=<your tree>), it
    will first attempt to select self.aitree as the tree, then whatever
    tree was already assigned to it, if self.aitree does not exist.
    """
    @lazy_property
    def ai(self):
        return AIHandler(self)

    def at_script_creation(self):
        super(AIScript, self).at_script_creation()
        self.ai.setup()
        self.desc = "Behavior tree AI script"
        self.persistent = True

class AIPlayer(DefaultPlayer):
    """
    A player that features an AI Wizard handler. The handler is used by wizards
    when browsing and editing AI trees in-game. Subclass your own player class
    to this.

    When subclassing from AI player to include your own dictionary of nodes
    (say, 'new_nodes') for your subclass (say 'MySubclass'), do:
    
    nodes = super(MySubclass, self).nodes.update(new_nodes)

    This will ensure that your new nodes will be added on to the extant
    dictionary of nodes.    
    """
    nodes = {'Node': Node, 'RootNode': RootNode, 'LeafNode': LeafNode,
        'CompositeNode': CompositeNode, 'DecoratorNode': DecoratorNode,
        'Condition': Condition, 'Command': Command, 'Selector': Selector,
        'Sequence': Sequence, 'MemSelector': MemSelector, 
        'MemSequence': MemSequence, 'ProbSelector': ProbSelector,
        'ProbSequence': ProbSequence, 'Parallel': Parallel, 
        'Verifier': Verifier, 'Inverter': Inverter, 'Succeeder': Succeeder,
        'Failer': Failer, 'Repeater': Repeater, 'Limiter': Limiter,
        'Allocator': Allocator}

    @ lazy_property
    def aiwizard(self):
        return AIWizardHandler(self)

    def at_player_creation(self):
        super(AIPlayer, self).at_player_creation()
        self.aiwizard.setup()

