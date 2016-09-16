"""
Contains all the default node types in the aisystem.


Nodes do not store references to their tree because objects serialized
in the text field of a django model cannot contain references to django
models.

New nodes should ideally be subclassed from LeafNode, CompositeNode
and DecoratorNode.
"""

import string
import random
import copy

# status messages returned by update() functions
FAILURE = 0
SUCCESS = 1
RUNNING = 2
ERROR = 3


class Node(object):
    def __init__(self, name, tree, parent, position=None):
        """
        Creates a hash for the node and assigns it to the tree's
        nodes list
        """
        if parent and not isinstance(parent, CompositeNode) and parent.children:
            raise Exception("attempted to add a node to a non-composite " +
                "parent that already has a child node.")

        if not parent and not isinstance(self, RootNode):
            raise Exception("cannot create a node without a parent " +
                "unless that node is a root node.")

        self.name = name
        self.parent = parent
        if isinstance(parent, CompositeNode):
            if position:
                parent.children.insert(position, self)
            else:
                parent.children.append(self)
        elif parent:
            parent.children = self
        self.hash = self.rehash(tree)
        tree.db_nodes[self.hash] = self
        self.children = None

    def rehash(self, tree):
        """
        Generate a hash that is not already assigned to a node
        in the given tree
        """
        hashval = None
        pre_vals = tree.db_nodes.keys()
        hash_chars = string.letters + string.digits
        n_attempts = 0
        while not hashval or hashval in pre_vals:
            hashval = (random.choice(hash_chars) + random.choice(hash_chars) +
                random.choice(hash_chars))
            n_attempts += 1
            if n_attempts == 10000:
                raise Exception("Too many attempts at creating a hash " +
                    + "for node \"{1}\". Aborting.".format(self.name))
                return None
        return hashval

    def tick(self, bb):
        """
        Goes through the procedure of updating the node, by opening it if it
        is not running, updating its status, then closing it if the status
        returned by the updating method is not "running".

        bb is the blackboard associated with the current instance of the tree.
        """
        
        if not bb.db_nodes[self.hash]['running']:
            self.open(bb)
        status = self.update(bb)
        
        if status == RUNNING:
            if not bb.db_nodes[self.hash]['running']:
                bb.db_nodes[self.hash]['running'] = True
                bb.db_running_now.append(self)
        else:
            self.close(bb)
       
        return status

    def open(self, bb):
        """
        Prepares the node for its update. 
        Meant to be overridden by some node classes.

        bb is the blackboard associated with the current instance of the tree.
        """
        pass 

    def update(self, bb):
        """
        May perform conditional checks, perform actions on the blackboard's
        associated agent, tick its child / children and return a given status.
        Meant to be overridden by most node classes.

        Ticks the node's child. Assumes there is only one child to run.

        bb is the blackboard associated with the current instance of the tree.
        """
        if self.children:
            self.children.tick

    def close(self, bb):
        """
        Resets the node when it is no longer running.
        Meant to be overridden by some node classes, notably composite nodes.

        bb is the blackboard associated with the current instance of the tree.
        """
        bb.db_nodes[self.hash]['running'] = False

    def on_add_child(self, node):
        """
        Called after a node is added to this node's list of children.

        This is not meant to perform the actual assignment of the node's parent
        or the assignment of the node to the parent's list of children.
        """
        pass

    def on_remove_child(self, node):
        """
        Called after a node is removed from this node's list of children.

        This is not meant to perform the actual removal of the node's parent
        or the removal of the node to the parent's list of children.
        """
        pass
        
    def on_blackboard_setup(self, bb):
        """
        Called whenever a blackboard's setup() function runs. Most commonly
        used for initializing data onto the blackboard.
        """
        pass


class RootNode(Node):
    """
    The node that sits at the top of the node hierarchy and is always the
    first to be ticked. Root nodes should not be created manually by the
    coder; instead, they are automatically generated with the creation of
    the tree. 
    """
    pass


class CompositeNode(Node):
    """
    A node with multiple children.
    """
    def __init__(self, name, tree, parent, position=None):
        super(CompositeNode, self).__init__(name, tree, parent, position=None)
        self.children = []


class Selector(CompositeNode):
    """
    A selector iterates through its list of children, ticking each child in
    turn. When one of its children succeeds, it returns success. If all of
    its children fail, it returns failure. It otherwise returns the status

    of its child.

    A selector does not keep track of which child is running, and so is
    usually unsuitable for handling situations where it receives a status
    of running. In these situations, it is best to use the MemSelector class
    instead.
    """
    def update(self, bb):
        for child in self.children:
            status = child.tick(bb)
            if status != FAILURE:
                return status
        return SUCCESS


class Sequence(CompositeNode):
    """
    A sequence iterates through its list of children, ticking each child in
    turn. When one of its children fails, it returns failure. If all of
    its children succeed, it returns success. It otherwise returns the status
    of its child.

    A sequence does not keep track of which child is running, and so is
    usually unsuitable for handling situations where it receives a status
    of running. In these situations, it is best to use the MemSequence class
    instead.
    """
    def update(self, bb):
        for child in self.children:
            status = child.tick(bb)
            if status != SUCCESS:
                return status
        return SUCCESS


def build_child_weights(node, bb):
    """
    Used by all probabilistic nodes to generate their child_weights dict.
    """
    weights = []
    for i in range(len(node.children)):
        if bb.db_nodes[node.children[i].hash].has_key('weight'):
            weights[str(i)] = bb.db_nodes[node.children[i].hash]['weight']            
        else:
            weights[str(i)] = 1.0
    bb.db_nodes[node.hash]['child_weights'] = weights


def prob_select_child(node, bb):
    """
    Probabilistically select the index of one of "node"'s child nodes

    Used by all probabilistic nodes.
    """
    probs = bb.db_nodes[node.hash]['avail_weights'].values()

    # normalize the proabilities from the weights
    probs = map(lambda x: x / sum(probs), probs)

    # take the cumulative sum of the probabilities
    for i in range(1, len(probs)):
        probs[i] += probs[i - 1]

    # ensure that no rounding errors occur
    probs[-1] = 1.0

    # randomly select a child node, acquire its index in the
    # children list
    rand = random.random()
    val = filter(lambda x: x >= rand, probs)[0]
    keys = bb.db_nodes[self.hash]['avail_weights'].keys()
    probs_index = probs.index(val)
    return keys[probs_index]


class ProbSelector(CompositeNode):
    """
    A special selector that goes through its child nodes probabilistically,
    using the 'weight' data of its children to determine the probability that
    each child will be picked. If no 'weight' exists for a given child, its
    'weight' is assumed to be 1. A child that has already been selected once
    will not be selected again until the ProbSelector has closed.
    
    The class otherwise behaves like a Selector.
    """
    def open(self, bb):
        """
        Reset the list of children that are available for ticking
        """
        bb.db_nodes[self.hash]['avail_weights'] = copy.copy(
            bb.db_nodes[self.hash]['child_weights'])
        super(ProbSelector, self).open(bb)

    def update(self, bb):
        """
        Probabilistically select a child node to be ticked, tick it,
        proceed until the status returned by the child is not Failure.
        """
        while bb.db_nodes[self.hash]['avail_weights']:
            index = prob_select_child(self, bb)
            bb.db_nodes[self.hash]['avail_weights'].pop(index)
            status = self.children[int(index)].tick(bb)
            
            if status != FAILURE:
                return status

        return FAILURE

    def on_blackboard_setup(self, bb):
        build_weights(self, bb)
        super(ProbSelector, self).on_blackboard_setup(bb)

class ProbSequence(CompositeNode):
    """
    A special selector that goes through its child nodes probabilistically,
    using the 'weight' data of its children to determine the probability that
    each child will be picked. If no 'weight' exists for a given child, its
    'weight' is assumed to be 1. A child that has already been selected once
    will not be selected again until the ProbSelector has closed.
    
    The class otherwise behaves like a Sequence.
    """
    def open(self, bb):
        """
        Reset the list of children that are available for ticking
        """
        bb.db_nodes[self.hash]['avail_weights'] = copy.copy(
            bb.db_nodes[self.hash]['child_weights'])
        super(ProbSequence, self).open(bb)

    def update(self, bb):
        """
        Probabilistically select a child node to be ticked, tick it,
        proceed until the status returned by the child is not Success.
        """
        while bb.db_nodes[self.hash]['avail_weights']:
            index = prob_select_child(self, bb)
            bb.db_nodes[self.hash]['avail_weights'].pop(index)
            status = self.children[int(index)].tick(bb)
            
            if status != SUCCESS:
                return status

        return SUCCESS

    def on_blackboard_setup(self, bb):
        build_weights(self, bb)
        super(ProbSequence, self).on_blackboard_setup(bb)


class MemSelector(CompositeNode):
    """
    A selector that keeps track of which child it has last called,
    so that while the sequence is running, it will call the
    """
    def update(self, bb):
        k_child = bb.db_nodes[self.hash]['running_child']
        for i in range(k_child, len(self.children)):
            status = self.children[i].tick(bb)
            if status != FAILURE:
                return status
        return FAILURE

    def close(self, bb):
        bb.db_nodes[self.hash]['running_child'] = 0
        super(MemSelector, self).close(bb)

    def on_blackboard_setup(self, bb):
        bb.db_nodes[self.hash]['running_child'] = 0
        super(MemSelector, self).close(bb)


class MemSequence(CompositeNode):
    def update(self, bb):
        k_child = bb.db_nodes[self.hash]['running_child']
        for i in range(k_child, len(self.children)):
            status = self.children[i].tick(bb)
            if status != SUCCESS:
                return status
        return SUCCESS

    def close(self, bb):
        bb.db_nodes[self.hash]['running_child'] = 0
        super(MemSequence, self).close(bb)

    def on_blackboard_setup(self, bb):
        bb.db_nodes[self.hash]['running_child'] = 0
        super(MemSequence, self).close(bb)


class Parallel(CompositeNode):
    """
    A parallel node runs all of its child nodes at once, and returns either
    when a minimum number of nodes have returned Success, when a minimum
    number of nodes have returned Failure, when a Primary Child has returned
    any status, when an error status has been returned, or when all of its
    children have returned successes and failures. If at least one child
    has returned Running when all of its children have returned, the node
    returns Running.

    Besides those it inherits, the parallel node has the following parameters:
    
    primary_child - a child whose success or failure causes the node to return
        (int)       success or failure. Can be set to None.

    req_successes - the number of successes required for the node to return
        (int)       success

    req_failures - the number of failures required for the node to return
        (int)      failure

    default_success - whether the node should return success or failure when
        (bool)        all child nodes have completed. Overriden by the
                      primary_child parameter.
    """
    def __init__(self, primary_child=None, req_successes=None,
        req_failures=None, default_success=True):
            """
            Initialize a default policy for when to return success or
            failure based on various criteria

            For an explanation of these criteria, see the relevant entries
            in the docstring of models.py
            """
            self.primary_child = primary_child
            self.req_successes = req_successes
            self.req_failures = req_failures
            self.default_success = default_success

    def open(self):
        bb.db_nodes[self.hash]['states'] = [None] * len(self.children)

    def update(self):
        """

        """
        primary_child = bb.db_nodes[self.hash]['primary_child']
        successes = len([x for x in bb.db_nodes[self.hash]['states']
                         if x == SUCCESS])
        failures = len([x for x in bb.db_nodes[self.hash]['states']
                        if x == FAILURE])
        req_successes = bb.db_nodes[self.hash]['req_successes']
        req_failures = bb.db_nodes[self.hash]['req_failures']

        for i in range(len(self.children)):
            state = bb.db_nodes[self.hash]['states'][i]
            if state == None or state == RUNNING:
                status = self.children[i].tick(bb)
                bb.db_nodes[self.hash]['states'][i] = status
            
                if status == SUCCESS:
                    if primary_child == i:
                        return SUCCESS
                    successes += 1                    
                    if successes >= req_successes:
                        return SUCCESS
                
                elif status == FAILURE:
                    if primary_child == i:
                        return FAILURE
                    failures += 1
                    if failures >= req_failures:
                        return FAILURE           

                elif status == ERROR:
                    return ERROR

        for state in bb.db_nodes[self.hash]['states']:
            if state == RUNNING:
                return RUNNING

        if bb.db_nodes[self.hash]['default_success']:
            return SUCCESS
        else:
            return FAILURE

    def on_blackboard_setup(self, bb):
        """
        Load the tree's defaults for the node's policy on when to return a
        given signal
        """
        bb.db_nodes[self.hash]['primary_child'] = self.primary_child
        bb.db_nodes[self.hash]['req_successes'] = self.req_successes
        bb.db_nodes[self.hash]['req_failures'] = self.req_failures
        bb.db_nodes[self.hash]['default_success'] = self.default_success

class LeafNode(Node):
    """
    A node that does not have any children. Attempting to add another node
    to it yields an error.
    """
    pass


class Condition(LeafNode):
    pass


class Command(LeafNode):
    """
    Has the agent execute a single command.
    """
    pass


class DecoratorNode(Node):
    """
    A node with only one child.
    """
    pass


class Verifier(DecoratorNode):
    """
    A conditional decorator that allows the child node to proceed only
    if its condition() method returns True.
    """
    pass


class Inverter(DecoratorNode):
    """
    A decorator that sends a status of Failure when its child succeeds
    and a status of Success when its child fails. It returns Running and
    Error normally.
    """
    pass


class Succeeder(DecoratorNode):
    """
    A decorator that sends a status of Success both when its child succeeds
    and when it fails. It returns Running and Error normally.
    """
    pass


class Failer(DecoratorNode):
    """
    A decorator that sends a status of Failure both when its child succeeds
    and when it fails. It returns Running and Error normally.
    """
    pass


class Repeater(DecoratorNode):
    """
    A decorator that, when its child succeeds or fails, keeps ticking its
    child again for a certain number of times, then returns success. If it
    receives a Running or Error status from the child, it returns Running or
    Error normally.
    """
    pass


class Limiter(DecoratorNode):
    """
    A decorator that only allows the child node to be run a limited number
    of times, after which it will not run at all (unless the limiter is reset
    from outside itself).
    """
    pass


# class Allocator(DecoratorNode):
#    """
#    A decorator that only runs its children when certain resources have been freed.
#    """
#    pass


