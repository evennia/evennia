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

_TREE_FROM_NAME = None # delayed import

# status messages returned by update() functions
FAILURE = 0
SUCCESS = 1
RUNNING = 2
ERROR = 3

status_strings = ["FAILURE", "SUCCESS", "RUNNING", "ERROR"]


class Node(object):
    """
    Base class for all node types. You should not subclass from this directly,
    but instead subclass from one of its subclasses like LeafNode,
    CompositeNode and DecoratorNode.
    """
    weight = 1.0

    def __init__(self, name, tree, parent, position=None):
        """
        Creates a hash for the node and assigns it to the tree's
        nodes list
        """
        if parent:
            msg_err = "{0} '{1}'(\"{2}\")".format(
            type(parent).__name__, parent.hash[0:3], parent.name)

        if (parent and not isinstance(parent, CompositeNode)
                and parent.children):
            raise Exception(
                "{0} is a non-composite parent ".format(msg_err) +
                "that already has a child node. Cannot add another child " +
                "node to it.")
        if isinstance(parent, LeafNode):
            raise Exception(
                "{0} is a leaf node. ".format(msg_err) +
                "Cannot add a child node to a leaf node.")
        if not parent and not isinstance(self, RootNode):
            raise Exception(
                "Cannot create a node without a parent " +
                "unless that node is a root node.")

        self.name = name
        self.parent = parent
        self.children = None
        if isinstance(parent, CompositeNode):
            if position != None:
                parent.children.insert(position, self)
            else:
                parent.children.append(self)
        elif parent:
            parent.children = self
        self.rehash(tree)
        tree.db.nodes[self.hash] = self

    def __str__(self):
        return self.name

    def __unicode__(self):
        return unicode(self.name)

    def rehash(self, tree):
        """
        Generate a hash that is not already assigned to a node
        in the given tree
        """
        hashval = None
        pre_vals = tree.db.nodes.keys()
        hash_chars = string.letters + string.digits
        n_attempts = 0
        while not hashval or hashval in pre_vals:
            hashval = (
                random.choice(hash_chars) + random.choice(hash_chars) +
                random.choice(hash_chars))
            n_attempts += 1
            if n_attempts == 10000:
                raise Exception(
                    "Too many attempts at creating a hash " +
                    "for node \"{1}\". Aborting.".format(self.name))
                return None
        hashval += '_' + str(tree.id)
        self.hash = hashval

    def tick(self, bb):
        """
        Goes through the procedure of updating the node, by opening it if it
        is not running, updating its status, then closing it if the status
        returned by the updating method is not "running".

        bb is the blackboard associated with the current instance of the tree.
        """
        if not bb['nodes'][self.hash]['running']:
            self.open(bb)
        status = self.update(bb)

        if status == RUNNING:
            #print("running:", bb['nodes'][self.hash]['running'],
            #    "running_now:", bb['running_now'])
            if not bb['nodes'][self.hash]['running']:
                bb['nodes'][self.hash]['running'] = True
            bb['running_now'].append(self)
        else:
            self.close(bb)

        for player in bb['nodes'][self.hash]['watchers']:
            player.msg(
                "|mAI watchlist|n: {0} '{1}'(\"{2}\") ".format(
                    type(self).__name__, self.hash, self.name) +
                "ticked with return status |c{0}|n.".format(
                    status_strings[status]))

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
            self.children.tick(bb)

    def close(self, bb):
        """
        Resets the node when it is no longer running.
        Meant to be overridden by some node classes, notably composite nodes.

        bb is the blackboard associated with the current instance of the tree.
        """
        bb['nodes'][self.hash]['running'] = False
        pass

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

    def on_blackboard_setup(self, bb, override=False):
        """
        Called whenever a blackboard's setup() function runs. Most commonly
        used for initializing data onto the blackboard.
        """
        if not bb['nodes'][self.hash].has_key('weight') or override:
            bb['nodes'][self.hash]['weight'] = self.weight


class RootNode(Node):
    """
    The node that sits at the top of the node hierarchy and is always the
    first to be ticked. Root nodes should not be created manually by the
    coder; instead, they are automatically generated with the creation of
    the tree.
    """
    def update(self, bb):
        return self.children.tick(bb)


class CompositeNode(Node):
    """
    A node with multiple children.
    """
    def __init__(self, name, tree, parent, position=None):
        super(CompositeNode, self).__init__(
            name, tree, parent, position=position)
        self.children = []

    def update(self, bb):
        for child in children:
            status = child.tick(bb)
            if status == RUNNING or status == ERROR:
                return status
        return SUCCESS


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
        return FAILURE


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
    weights = {}
    for i in range(len(node.children)):
        if not bb['nodes'][node.children[i].hash].has_key('weight'):
            bb['nodes'][node.children[i].hash]['weight'] = (
                node.children[i].weight)
        weights[str(i)] = bb['nodes'][node.children[i].hash]['weight']
    bb['nodes'][node.hash]['child_weights'] = weights


def prob_select_child(node, bb):
    """
    Probabilistically select the index of one of "node"'s child nodes

    Used by all probabilistic nodes.
    """
    probs = bb['nodes'][node.hash]['avail_weights'].values()

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
    keys = bb['nodes'][node.hash]['avail_weights'].keys()
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
        super(ProbSelector, self).open(bb)
        bb['nodes'][self.hash]['avail_weights'] = copy.copy(
            bb['nodes'][self.hash]['child_weights'])

    def update(self, bb):
        """
        Probabilistically select a child node to be ticked, tick it,
        proceed until the status returned by the child is not Failure.

        If a child is running, continue ticking that child until its
        return status changes.
        """
        # If one of the children is already running, keep running it
        running_child = bb['nodes'][self.hash]['running_child']
        if running_child != None:
            status = self.children[running_child].tick(bb)
            if status != RUNNING:
                bb['nodes'][self.hash]['running_child'] = None
            return status

        # Otherwise, keep picking children at random until
        # one of them turns out to return Success, Running or Error.
        # In this case, return the child's status. If the status is
        # Running, also ensure that the running child will be ticked
        # when this node is next ticked.
        # If all of the children return False, then return False.
        while bb['nodes'][self.hash]['avail_weights']:
            index = prob_select_child(self, bb)
            status = self.children[int(index)].tick(bb)
            bb['nodes'][self.hash]['avail_weights'].pop(index)

            if status == RUNNING:
                bb['nodes'][self.hash]['running_child'] = int(index)

            if status != FAILURE and bb['nodes'][self.hash]['avail_weights']:
                return status
        return FAILURE

    def on_blackboard_setup(self, bb, override=False):
        super(ProbSelector, self).on_blackboard_setup(bb, override=override)
        if not bb['nodes'][self.hash].has_key('child_weights') or override:
            build_child_weights(self, bb)
        if not bb['nodes'][self.hash].has_key('running_child') or override:
            bb['nodes'][self.hash]['running_child'] = None

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
        super(ProbSequence, self).open(bb)
        bb['nodes'][self.hash]['avail_weights'] = copy.copy(
            bb['nodes'][self.hash]['child_weights'])

    def update(self, bb):
        """
        Probabilistically select a child node to be ticked, tick it,
        proceed until the status returned by the child is not Success.

        If a child is running, continue ticking that child until its
        return status changes.
        """
        # If one of the children is already running, keep running it
        running_child = bb['nodes'][self.hash]['running_child']
        if running_child != None:
            status = self.children[running_child].tick(bb)
            if status != RUNNING:
                bb['nodes'][self.hash]['running_child'] = None
            return status

        # Otherwise, keep picking children at random until
        # one of them turns out to return Success, Running or Error.
        # In this case, return the child's status. If the status is
        # Running, also ensure that the running child will be ticked
        # when this node is next ticked.
        # If all of the children return False, then return False.
        while bb['nodes'][self.hash]['avail_weights']:
            index = prob_select_child(self, bb)
            status = self.children[int(index)].tick(bb)
            bb['nodes'][self.hash]['avail_weights'].pop(index)

            if status == RUNNING:
                bb['nodes'][self.hash]['running_child'] = int(index)

            if status != SUCCESS and bb['nodes'][self.hash]['avail_weights']:
                return status
        return SUCCESS

    def on_blackboard_setup(self, bb, override=False):
        super(ProbSequence, self).on_blackboard_setup(bb, override=override)
        if not bb['nodes'][self.hash].has_key('child_weights') or override:
            build_child_weights(self, bb)
        if not bb['nodes'][self.hash].has_key('running_child') or override:
            bb['nodes'][self.hash]['running_child'] = None


class MemSelector(CompositeNode):
    """
    A selector that keeps track of which child it has last called,
    so that whenever the selector ticks, it starts iterating from the currently
    running node rather than from the first node in its list of children.
    """
    def update(self, bb):
        k_child = bb['nodes'][self.hash]['running_child']
        for i in range(k_child, len(self.children)):
            status = self.children[i].tick(bb)
            if status == RUNNING:
                bb['nodes'][self.hash]['running_child'] = i
            if status != FAILURE:
                return status
        return FAILURE

    def close(self, bb):
        super(MemSelector, self).close(bb)
        bb['nodes'][self.hash]['running_child'] = 0

    def on_blackboard_setup(self, bb, override=False):
        super(MemSelector, self).on_blackboard_setup(bb, override=override)
        if not bb['nodes'][self.hash].has_key('running_child') or override:
            bb['nodes'][self.hash]['running_child'] = 0


class MemSequence(CompositeNode):
    """
    A sequence that keeps track of which child it has last called,
    so that whenever the sequence ticks, it starts iterating from the currently
    running node rather than from the first node in its list of children.
    """
    def update(self, bb):
        k_child = bb['nodes'][self.hash]['running_child']
        for i in range(k_child, len(self.children)):
            status = self.children[i].tick(bb)
            if status == RUNNING:
                bb['nodes'][self.hash]['running_child'] = i
            if status != SUCCESS:
                return status
        return SUCCESS

    def close(self, bb):
        super(MemSequence, self).close(bb)
        bb['nodes'][self.hash]['running_child'] = 0

    def on_blackboard_setup(self, bb, override=False):
        super(MemSequence, self).on_blackboard_setup(bb, override=override)
        if not bb['nodes'][self.hash].has_key('running_child') or override:
            bb['nodes'][self.hash]['running_child'] = 0


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
        (int)       success. Can be set to None to indicate that no amount of
                    successes will trigger this.

    req_failures - the number of failures required for the node to return
        (int)      failure. Can be set to None to indicate that no amount of
                   failures will trigger this.

    default_success - whether the node should return success or failure when
        (bool)        all child nodes have completed. Overriden by the
                      primary_child parameter.
    """
    def __init__(
            self, name, tree, parent, position=None, primary_child=None,
            req_successes=None, req_failures=None, default_success=True):
        """
        Initialize a default policy for when to return success or
        failure based on various criteria

        For an explanation of these criteria, see the relevant entries
        in the docstring of models.py
        """
        super(Parallel, self).__init__(name, tree, parent, position=position)
        self.primary_child = primary_child
        self.req_successes = req_successes
        self.req_failures = req_failures
        self.default_success = default_success

    def open(self, bb):
        super(Parallel, self).open(bb)
        bb['nodes'][self.hash]['states'] = [None] * len(self.children)

    def update(self, bb):
        """
        Iterate through the parallel node's children and tick them, checking
        each time if one of the return conditions for the parallel node has
        been met.
        """
        primary_child = bb['nodes'][self.hash]['primary_child']
        successes = len([x for x in bb['nodes'][self.hash]['states']
                         if x == SUCCESS])
        failures = len([x for x in bb['nodes'][self.hash]['states']
                        if x == FAILURE])
        req_successes = bb['nodes'][self.hash]['req_successes']
        req_failures = bb['nodes'][self.hash]['req_failures']

        for i in range(len(self.children)):
            state = bb['nodes'][self.hash]['states'][i]
            if state == None or state == RUNNING:
                status = self.children[i].tick(bb)
                bb['nodes'][self.hash]['states'][i] = status

                if status == SUCCESS:
                    if primary_child == i:
                        return SUCCESS
                    successes += 1
                    if req_successes != None and successes >= req_successes:
                        return SUCCESS

                elif status == FAILURE:
                    if primary_child == i:
                        return FAILURE
                    failures += 1
                    if req_failures != None and failures >= req_failures:
                        return FAILURE

                elif status == ERROR:
                    return ERROR

        for state in bb['nodes'][self.hash]['states']:
            if state == RUNNING:
                return RUNNING

        if bb['nodes'][self.hash]['default_success']:
            return SUCCESS
        return FAILURE

    def on_blackboard_setup(self, bb, override=False):
        """
        Load the tree's defaults for the node's policy on when to return a
        given signal
        """
        super(Parallel, self).on_blackboard_setup(bb, override=override)
        if not bb['nodes'][self.hash].has_key('primary_child') or override:
            bb['nodes'][self.hash]['primary_child'] = self.primary_child
        if not bb['nodes'][self.hash].has_key('req_successes') or override:
            bb['nodes'][self.hash]['req_successes'] = self.req_successes
        if not bb['nodes'][self.hash].has_key('req_failures') or override:
            bb['nodes'][self.hash]['req_failures'] = self.req_failures
        if not bb['nodes'][self.hash].has_key('default_success') or override:
            bb['nodes'][self.hash]['default_success'] = self.default_success

class LeafNode(Node):
    """
    A node that does not have any children. Attempting to add another node
    to it yields an error.
    """
    pass


class Condition(LeafNode):
    """
    Checks whether the condition method's return status is True or False.
    If True, returns Success, else it returns Failure.

    You must assign its condition method manually in either the blackboard
    or the node itself. If you set it on the node, remember to run the
    blackboard's setup() method to reset it.
   """
    def update(self, bb):
        if self.condition(bb):
            return SUCCESS
        return FAILURE

    def condition(self, bb):
        pass


class Command(LeafNode):
    """
    Works for characters only, not scripts and not objects that have no CmdSets.

    Has the agent execute a single command. Always returns Success. Should
    not be relied on for anything other than debugging.

    You must set its command property manually in either the blackboard
    or the node itself. If you set it on the node, remember to run the
    blackboard's setup() method to reset it.
    """
    command = ""

    def update(self, bb):
        bb.agent.execute_cmd(bb['nodes'][self.hash]['command'])
        return SUCCESS

    def on_blackboard_setup(self, bb, override=False):
        super(Command, self).on_blackboard_setup(bb, override=override)
        if not bb['nodes'][self.hash].has_key('command') or override:
            bb['nodes'][self.hash]['command'] = self.command


class Transition(LeafNode):
    """
    Ticks the root node of the target tree, effectively attaching
    a virtual copy of that tree to this one. If no tree is provided,
    it returns an error.
    """
    target_tree = None

    def update(self, bb):
        target_tree = bb['nodes'][self.hash]['target_tree']
        if target_tree:
            return target_tree.nodes[target_tree.root].tick(bb)
        else:
            bb['globals']['errors'][self.hash] = (
                "The node does not have a target tree.")
            return ERROR

    def on_blackboard_setup(self, bb, override=False):
        super(Transition, self).on_blackboard_setup(bb, override=override)

        global _TREE_FROM_NAME
        if not _TREE_FROM_NAME:
            from evennia.contrib.aisystem.utils import (
                tree_from_name as _TREE_FROM_NAME)

        if not bb['nodes'][self.hash].has_key('target_tree') or override:
            if (isinstance(self.target_tree, str)
                    or isinstance(self.target_tree, unicode)):
                target_tree = _TREE_FROM_NAME(None, self.target_tree)
            else:
                target_tree = self.target_tree
            bb['nodes'][self.hash]['target_tree'] = target_tree


class EchoLeaf(LeafNode):
    """
    Works for objects only, not scripts.

    If the node's msg property is not empty, sends a room echo using the msg
    property's string and returns SUCCESS, else returns FAILURE.
    """
    msg = ""
    def update(self, bb):
        if bb['nodes'][self.hash]['msg']:
            bb['agent'].location.msg_contents(bb['nodes'][self.hash]['msg'])
            return SUCCESS
        return FAILURE

    def on_blackboard_setup(self, bb, override=False):
        super(EchoLeaf, self).on_blackboard_setup(bb, override=override)
        if not bb['nodes'][self.hash].has_key('msg') or override:
            bb['nodes'][self.hash]['msg'] = self.msg


class DecoratorNode(Node):
    """
    A node with only one child.
    """
    pass


class Verifier(DecoratorNode):
    """
    A conditional decorator that allows the child node to proceed only
    if its condition() method returns True.

    You must set its command property manually in either the blackboard
    or the node itself. If you set it on the node, remember to run the
    blackboard's setup() method to reset it.
    """
    def update(self, bb):
        if self.condition(bb):
            return self.children.tick(bb)
        else:
            return FAILURE

    def condition(self, bb):
        pass


class Inverter(DecoratorNode):
    """
    A decorator that sends a status of Failure when its child succeeds
    and a status of Success when its child fails. It returns Running and
    Error normally.
    """
    def update(self, bb):
        status = self.children.tick(bb)
        if status == SUCCESS:
            return FAILURE
        elif status == FAILURE:
            return SUCCESS
        else:
            return status


class Succeeder(DecoratorNode):
    """
    A decorator that sends a status of Success both when its child succeeds
    and when it fails. It returns Running and Error normally.
    """
    def update(self, bb):
        status = self.children.tick(bb)
        if status == SUCCESS or status == FAILURE:
            return SUCCESS
        return status


class Failer(DecoratorNode):
    """
    A decorator that sends a status of Failure both when its child succeeds
    and when it fails. It returns Running and Error normally.
    """
    def update(self, bb):
        status = self.children.tick(bb)
        if status == SUCCESS or status == FAILURE:
            return SUCCESS
        return status


class Repeater(DecoratorNode):
    """
    A decorator that, when its child succeeds or fails, keeps ticking its
    child again until the maximum number of repeats has been exceeded, then
    returns Success. If it receives a Running or Error status from the child,
    it returns Running or Error normally.
    """
    repeats = 0

    def update(self, bb):
        for k_repeat in range(bb['nodes'][self.hash]['ticks'], self.repeats):
            status = self.children.tick(bb)
            bb['nodes'][self.hash]['ticks'] += 1
            if status == RUNNING or status == ERROR:
                return status
        bb['nodes'][self.hash]['ticks'] = 0
        return SUCCESS

    def on_blackboard_setup(self, bb, override=False):
        super(Repeater, self).on_blackboard_setup(bb, override=override)
        if not bb['nodes'][self.hash].has_key('ticks') or override:
            bb['nodes'][self.hash]['ticks'] = 0

class Limiter(DecoratorNode):
    """
    A decorator that only allows the child node to be run a limited number
    of times equal to self.repeats, after which it will not run at all (unless
    the limiter is reset from outside itself).
    """
    repeats = 0

    def update(self, bb):
        if bb['nodes'][self.hash]['ticks']:
            status = self.children.tick(bb)
            bb['nodes'][self.hash]['ticks'] -= 1
            return status
        return FAILURE

    def on_blackboard_setup(self, bb, override=False):
        super(Limiter, self).on_blackboard_setup(bb, override=override)
        if not bb['nodes'][self.hash].has_key('ticks') or override:
            bb['nodes'][self.hash]['ticks'] = self.repeats


class Allocator(DecoratorNode):
    """
    A decorator that only runs its children when certain resources have been
    freed. If one of the intended resources has not been freed, it returns
    RUNNING.

    For a resource to be considered freed, either it needs to have no entry
    in its blackboard's ['globals']['resources'] dictionary, or its entry
    needs to be set to None, False or an empty container.

    Note that allocators do not modify the resources they query in any way;
    this must be accomplished from outside the allocators themselves.
    """
    resources = []

    def update(self, bb):
        for resource in bb['nodes'][self.hash]['resources']:
            if (bb['globals']['resources'].has_key(resource) and
                    bb['globals']['resources'][resource]):
                return RUNNING
        return self.children.tick(bb)

    def on_blackboard_setup(self, bb, override=False):
        super(Allocator, self).on_blackboard_setup(bb, override=override)
        if not bb['nodes'][self.hash].has_key('resources') or override:
            bb['nodes'][self.hash]['resources'] = self.resources


class EchoDecorator(DecoratorNode):
    """
    Works for objects only, not scripts.

    If the node's msg property is not empty, sends a room echo using the msg
    property's string and returns the child node's status, else returns FAILURE.
    """
    msg = ""
    def update(self, bb):
        if bb['nodes'][self.hash]['msg']:
            bb['agent'].location.msg_contents(bb['nodes'][self.hash]['msg'])
            return self.children.tick(bb)
        return FAILURE

    def on_blackboard_setup(self, bb, override=False):
        super(EchoDecorator, self).on_blackboard_setup(bb, override=override)
        if not bb['nodes'][self.hash].has_key('msg') or override:
            bb['nodes'][self.hash]['msg'] = self.msg


all_original_nodes = {
    'Node': Node, 'RootNode': RootNode, 'LeafNode': LeafNode,
    'CompositeNode': CompositeNode, 'DecoratorNode': DecoratorNode,
    'Condition': Condition, 'Command': Command, 'Transition': Transition,
    'EchoLeaf': EchoLeaf, 'Selector': Selector, 'Sequence': Sequence,
    'MemSelector': MemSelector, 'MemSequence': MemSequence, 
    'ProbSelector': ProbSelector, 'ProbSequence': ProbSequence, 
    'Parallel': Parallel, 'Verifier': Verifier, 'Inverter': Inverter, 
    'Succeeder': Succeeder, 'Failer': Failer, 'Repeater': Repeater,
    'Limiter': Limiter, 'Allocator': Allocator, 'EchoDecorator': EchoDecorator}
