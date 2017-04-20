## Behavior tree-based AI
The AI this system provides is based on behavior trees, structures that evaluate
situations and perform actions in a specified order. As of 2016, behavior trees
are widely used throughout the games industry due to their ease of use and
modularity. A behavior tree is composed of nodes, each node having a single 
parent and possibly one or more children, with the exception of the tree's 
__root node__, which has no parent. The various nodes are assembled together to
generate various behaviors, as you will see below. Even if you are completely
unfamiliar with behavior trees, this document will serve as a hopefully decent
tutorial.

There are other tutorials you can follow online, notably the ones by
[Renato Pererio][RP] and [Chris Simpson][CS], as well as a highly technical
[research paper][paper] that goes into behavior trees.

[RP](http://guineashots.com/2014/07/25/an-introduction-to-behavior-trees-part-1/)
[CS](http://www.gamasutra.com/blogs/ChrisSimpson/20140717/221339/Behavior_trees_for_AI_How_they_work.php)
[paper](http://www.csc.kth.se/~miccol/Michele_Colledanchise/Publications_files/2013_ICRA_mcko.pdf)

During each iteration of an AI tree, the tree starts from its root node and
progresses to that node's child, then to any children of that child and so
forth. When it comes upon a node with multiple children, called a __composite
node__, it goes through this node's children either in sequence or in parallel.
The nodes that do not have children themselves, called __leaf nodes__, either
check whether a condition is true or perform an action. A given AI can be
associated with a single character or object, or with multiple characters
(as happens with the AIs of real-time strategy games), or even with no
characters at all, when for instance there might be an AI that decides how to
compose a text that will later be narrated or influences the weather.

This package's implementation of behavior trees provides a standard set of
commonly used nodes, such as sequences and selectors (see below), as well as
enabling developers to generate new nodes by subclassing already-existent ones.
The trees can be assembled either outside the game, within python modules, or
inside the game, by using the various commands provided by this package. You can
also navigate, inspect and debug the trees conveniently inside the game, using
both built-in commands and nodes that can echo various messages. While coders
are required to create new nodes, the assembly of these nodes into behavior
trees and the testing of these trees can all be done by builders.

Using Transition nodes, you can have the AI descend from one tree into another, which means you can design trees in a modular fashion, making one tree perform
a behavior that can be invoked by many other trees. For instance, you can create
a "move through exit" tree that checks whether the target exit is closed or
locked, attempts to open or unlock it if that is the case, etc. and then attach
that tree to other AI trees wherever there is a need to move through an exit.
By making your trees modular this way, you can ensure that you never need to
edit more than one tree when you want to improve upon a given behavior.

#### Basic node types
Behavior trees have four fundamental node types: __root nodes__ that have no
parent and one child, __leaf nodes__ that have one parent and no children,
__decorator nodes__ that have one parent and one child, and __composite nodes__
that have one parent and multiple children. A tree has exactly one root node.

In the code, these types of nodes comprise the `RootNode`, `LeafNode`,
`DecoratorNode` and `CompositeNode` classes. All of them subclass from
the basic `Node` class , from which you should probably never subclass
directly.

When the AI reaches a given node in a tree, it "ticks" that node, performing a
single procedure and issuing a __return status__ to its parent. This status is
defined in the code as either SUCCESS, FAILURE, RUNNING or ERROR. A status of
ERROR arises when the execution of the node's code halts because of an error.
A status of RUNNING arises when the node has yet to attain either success or
failure at the end of the procedure that it just performed. For example, if a
node called "go to target" requires an agent to move multiple times, it will
return RUNNING while the agent is moving towards the targent.

Throughout the text below, you will find references to node "instances". This is
because each of the various AI agents in your game stores its own copy of some
of the data found in the tree or trees it uses, and is able to modify its data
(thus modifying "instances" of a given node) without affecting the tree itself
or its nodes.

#### Leaf nodes
The AI system provides three basic leaf nodes:

`Condition` - a condition node returns either SUCCESS or FAILURE based on
whether a specified condition is met. In the code, you must subclass
the condition class and overload that class' condition method with your own
method that returns True (making the node return SUCCESS) or False (making the
node return FAILURE).

`Command` - a node that executes a specified command and returns SUCCESS. It
does not check whether the command has actually succeeded, so it should only
be used for debugging and possibly sending emotes. You can specify the command
by setting the node's `command` property or a given node's instance's 'command'
entry to a specified string.

`Transition` - a node that descends into the root node of the target tree and
returns that node's return status. You can specify the name or ID of the tree
(as a string) in the node's `target\_tree` property or a given node instance's
'target\_tree' entry. The `target\_tree` property can also be an actual
reference to the tree if you specify it within the code itself.

Be aware that you can create infinite loops using this command, if the tree
you specify is upstream of the Transition node's own tree.

`EchoLeaf` - a node that sends a specified room echo and returns SUCCESS. If no
echo is specified (as happens by default), it returns FAILURE. You can specify
the echo by setting the node's `msg` property or a given node instance's 'msg'
entry to a specified string. This node may only be used when its agent is an
AIObject, not an AIScript (see the section on setting up the AI system for more
information).

#### Composite nodes
The AI system provides the following basic composite nodes:

`Sequence` - a node that iterates through its children from first to last,
checking their return status. If the return status of a child is not SUCCESS,
the sequence returns with that status. If all children have returned a status
of SUCCESS, the sequence returns SUCCESS.

You can put condition leaf nodes throughout a sequence to stop the sequence
from going forward if any of the conditions is not met. For instance, a sequence
called "attack" might have a node called "is an enemy visible?" as its first
node. If no enemy is visible, the AI agent will not try to attack.

Use sequences when you want an action or set of actions to be performed only
when all prerequisite actions have been performed and all prerequisite
conditions have been met.

`MemSequence` - a node that is identical to a Sequence except for the fact that
it records which of its children (if any) returned RUNNING on the last iteration
of the AI, and will begin going through its children from that particular child
on the next iteration of the AI, whereas a simple Sequence always starts from
the first child in its list of children regardless of whether a child was
running on the previous iteration.

`Selector` - a node that iterates through its children from first to last,
checking their return status. If the return status of a child is not FAILURE,
the selector returns with that status. If all children have returned a status
of FAILURE, the selector returns FAILURE.

Use selectors when you want a behavior to attempt multiple actions and stop at
the first one that provides a desired result. For instance, a "go through door"
selector might have the child nodes "open door", "knock on door", "pick lock"
and "bash down door". If opening the door fails, try knocking on it etc.

`MemSelector` - a node that is identical to a Selector except for the fact that
it records its running child like a MemSequence does.

`ProbSequence` - a node that goes through its children probabilistically rather
than sequentially, using the children's different _probability weights_ to bias
their chances of being picked. In a given iteration, a ProbSequence keeps
going through its children until one of them gives a return status other than
SUCCESS, in which case the ProbSequence returns that status. When all children
have been picked, the ProbSequence returns SUCCESS. A child can only be picked
once during a given iteration of the ProbSequence.

Every node in the AI system has a weight property that can be edited. By
default, all weights are equal to 1.0. You can also edit a given node instance's
'weight' entry.

`ProbSelector` - identical to the ProbSequence except that it returns the status
of any child that does not return FAILURE, and returns FAILURE when all children
have returned FAILURE.

`Parallel` - a node that goes through all of its children in "parallel". In
fact, it goes through them in sequence, but keeps going through them regardless
of their individual return statuses unless one of the return statuses is ERROR,
in which case that status is returned, or unless the conditions of a return
policy are met.

Parallel nodes have four return policies, all of which may be active at once:

primary\_child: you can specify an index as a primary child, or set this to
`None` to disable this return policy. When specified, the child that has the
given index in the node's list of children will become the primary child. When
the primary child returns SUCCESS or FAILURE, the parallel node itself returns
that status.

req\_successes: you can specify the number of successes required during a given
iteration in order for the node to immediately return SUCCESS. Instead of an
integer, this can be set to `None` to disable this return policy.

req\_failures: same as req\_successes, except it determines when to return
FAILURE.

default\_success: can be set to either `True` or `False`. `True` by default.
When `True`, the node returns SUCCESS once all child nodeshave returned a
status other than RUNNING or ERROR. When `False`, it returns FAILURE once all
child nodes have returned a status other than RUNNING or ERROR.

All of these are properties of the node that you can modify, as well as entries
in all of the node's instances.

After the parallel node has gone through its children, if any of them return
RUNNING, the node will return RUNNING.

#### Decorators
The AI system provides the following decorator nodes:

`Verifier` - this node checks whether a given condition is met. If so, it
returns the return status of its child. Otherwise, it returns False. In the
code, you must subclass the verifier class and overload that class' condition
method with your own method that returns True (making the node return SUCCESS)
or False (making the node return FAILURE).

`Inverter` - this node returns SUCCESS when its child returns FAILURE, and
returns FAILURE when its child returns SUCCESS. When its child returns ERROR
or RUNNING, the inverter returns the same status.

Inverters are useful in a lot of situations, such as when you want a particular
sequence of actions to go ahead after a condition has not been met. For
instance, you may want a character to wander off only when there are no enemies
nearby. Instead of coding a new node that returns SUCCESS when no enemies are
sighted, you can use one of your nodes that returns SUCCESS when enemies are
sighted, and put it under an inverter, ensuring that the inverter returns
SUCCESS when no enemies are sighted.

`Succeeder` - this node returns SUCCESS both when its child returns FAILURE and
when its child returns SUCCESS. It otherwise returns its child's status.

`Failer` - this node returns FAILURE both when its child returns FAILURE and
when its child returns SUCCESS. It otherwise returns its child's status.

`Repeater` - each time it is run, this node runs its child multiple times, up
to the number of times specified by its `repeats` property, while the child is
returning SUCCESS or FAILURE. Afterwards, the Repeater returns SUCCESS. If at
any point the child returns ERROR or RUNNING, the repeater immediately returns
that status. Each node instance keeps track of the current number of repeats
via its 'ticks' entry.

`Limiter` - each time it is run, a given instance of this node increments its
'ticks' entry by one, up to the point where that counter reaches the value of
the node's `repeats` property. Before reaching this threshold, the node simply
returns its child's return status. After reaching this threshold, however, it
returns FAILURE without ever running its child. The Limiter node can be used
for only allowing its subtree to be run a limited number of times. Keep in mind
that you can reset its 'ticks' entry from other nodes that you code yourself,
so the node's limiting effect need not be a permanent one.

`Allocator` - an allocator only runs its child (and returns that child's return
status) when none of the resources it requires are claimed. When one or more of
the needed resources is claimed, it returns RUNNING without running its child.

Note to coders: resources are entries in the node's `resources` property. They
are of the type _string_. The 'globals' entry of a given blackboard has a
'resources' entry that is a dictionary storing such strings as keys. If no key
in this dictionary matches the name of a string entry in the node's `resources`
property, or if such a key exists but is set to None, False, or an empty
container (i.e. it returns False when converted to a _bool_), then the resource
described by this string entry is considered freed. Otherwise, it is not
considered freed and will prevent allocator nodes that rely on it from running
their children until some bit of code frees it.

`EchoDecorator` - the EchoDecorator sends a message to the room and runs its
child, then returns that child's return status. It stores this message in the
node's `msg` property and a given node instance's 'msg' entry. If no message is
provided (this is the default scenario), the EchoDecorator returns FAILURE
without sending a message or running its child. Note that this node may only be
used when its agent is an AIObject, not an AIScript (see the section on setting
up the AI system for more information.)

#### Blackboards

Because it would be inefficient to store an instance of a tree on each agent
that used that tree, a given agent only stores certain data pertaining to the
nodes of the tree(s) it uses, but not data related to the structures of these
trees such as the nodes' parent-child relationships or default values for their
various properties. The data that an agent stores is called the agent's
blackboard. It contains information related to its various nodes, to the agent
itself and several other bits of data that are used internally by the AI system.
Each blackboard is associated to a tree called its __origin tree__, from whose
root node it begins every iteration of the AI, but it can potentially store
data related to numerous trees due to the availability of Transition nodes.

Some nodes, such as parallel nodes, store their operational parameters,
such as how many successes must be returned by the node's children in order
for the node itself to succeed, in their blackboards as well as on the node
objects themselves. Although you can assign these parameters manually on
the blackboard, it is highly recommended that you do not, as any changes
you happen to later make to the trees that the blackboard uses will require the
blackboard to be reset in order to incorporate them, thus overriding your
manually assigned parameters. Instead, the blackboard data should only be
modified from within the game's code, unless you are debugging that code and
want to see what happens when the data has certain values. In all other cases, 
you should modify the properties of the node objects themselves.

Each blackboard contains the following node-related properties (you can consult
them later and skip straight to the section on setting up the AI system if you
prefer):

weight (float) - the probabilistic weight of a given node. When the node is the
                 direct child of a probabilistic composite node, its weight
                 affects the probability that it will be ticked before the
                 composite node's other child nodes. Note that probabilistic
                 composite nodes treat weight-less nodes as if their weight
                 is 1.

child\_weights (dict of floats) - a dict of the weights of all child nodes.
                                 The keys are the child nodes' indices in the
                                 parent node's list of children. When used by
                                 a probabilistic node, this dict allows a
                                 random number to determine which of the nodes
                                 will be selected next.

avail\_weights (dict of floats) - a dict of the weights of all child nodes that
                                 are available for ticking. The keys are the
                                 nodes' indices in the parent node's list of
                                 children.

states (list of ints) - a list of the states returned by all children of the
                        node; can include values of None for children that have
                        not yet returned a state. Used by parallel nodes.

primary\_child (int) - for parallel nodes, one child of the node whose
                      completion immediately triggers the parallel node's own
                      completion, the parallel node's return status being the
                      same as that of the primary child.

req\_successes (int) - used by parallel nodes; represents the number of child
                      nodes that must return success for the parallel node
                      itself to immediately return success.

req\_failures (int) - used by parallel nodes; represents the number of child
                     nodes that must return success for the parallel node
                     itself to immediately return success.

default\_success (bool) - used by parallel nodes to decide whether to return
                         success when all child nodes have completed but
                         no other condition has been met for returning a status

running (bool) - whether or not the node is currently running or was running
                 during its last tick.

running\_child (int) - the currently running child of a MemSequence or
                      MemSelector node.

ticks (int) - for repeater nodes, this is the number of repeats that have
              already been performed since the repeater started running. For
              limiter nodes, this is the number of repeats left before the
              limiter shuts down.

watchers (list) - a list of all the players that are currently watching the node

Each blackboard also contains the following global data:

resources (dict) - a dictionary with the names of resources as keys and the
                   things using them as values. See the resource allocator
                   node for details about this.

errors (dict) - a dictionary with the hashes of nodes as keys and the error
                strings they returned during the most recent iteration of the
                blackboard as values.

### Setting up the ai system

First, subclass the classes of any AI-using objects, characters or other
entities from the AIObject class:

```
from evennia.contrib.aisystem import AIObject

class MyClass(AIObject, <other superclasses>)
```

Also set up any script classes that you want to have an AI blackboard by
subclassing them from the AIScript class, or simply use the AIScript class
directly.

```
from evennia.contrib.aisystem import AIScript

class MyScript(AIScript, <other superclasses>)
```

You can assign each class that inherits from AIObject or AIScript a property
called `aitree`, whose value can be either a BehaviorTree or a string that
references the name or database id of a given tree. For instance:

```
from evennia.contrib.aisystem import AIScript

class MyScript(AIScript, <other superclasses>)
    aitree = 'fighter tree'
```

Also set up the player class of any players that you want to have access to
the AI system commands by subclassing it from AIPlayer.

```
from evennia.contrib.aisystem import AIPlayer

new_nodes = [...]

class MyPlayerClass(AIPlayer, <other superclasses>)
    [...]
    def at_player_creation(self):
        super(MyPlayerClass, self). at_player_creation()
        self.ainodes.update(new_nodes)
```

Here, new\_nodes is a dictionary whose keys are the names of node classes that
you will reference in-game when adding new nodes to your trees, and whose items
are the respective node classes. For instance, if new\_nodes is
`{'my_node': MyNode}, then you can add a node of class MyNode to the currently
browsed node by using the "@aiadd my_node 'my node'" command. Node names should
only contain alphanumeric characters and underscores, never spaces.

Even if they are subclassed from this class, players will only have access to
the AI system commands if they are wizards, immortals or the superuser.

Finally, you need to load the AI system's command set into your game. One way
to do this is to go into your game's commands/default\_cmdsets.py file and
add the following:

```
from evennia.contrib.aisystem import AICmdSet

[...]

class PlayerCmdSet(default_cmds.PlayerCmdSet)
    [...]
    def at_cmdset_creation(self):
        [...]
        self.add(AICmdSet())
```

All newly created AIPlayers, AIObjects and AIScripts are automatically set up
upon creation. Those that already exist in the database when you start using
the AI system, however, need to be set up manually. To set up everything once
you have gone through the above steps, simply enter the game and run the
@aisetup command without any arguments. Note that you must be a wizard or
higher to do so.

When you want a piece of code, such as a script or a tickerhandler, to go
through an agent's AI tree once, simply have it run the agent's tick method:

```
status = my_object_or_script.ai.tick()
```

Here, `status` is the return status of the root node of the AI tree.
The value of status will be equal to either FAILURE, SUCCESS, RUNNING or ERROR.
All four of these are constants that can be imported from the AIsystem module:

```
from evennia.contrib.aisystem import FAILURE, SUCCESS, RUNNING, ERROR
```

### Working with behavior trees in-game

The following commands allow you to navigate, view and modify behavior trees,
their nodes and these nodes' properties, as well as AI agents and their
blackboards, from within the game itself.

@aisetup - sets up all or some of the agents and players that use the AI system.

@ainewtree - creates a new BehaviorTree from within the game.

@aiclonetree - creates a copy of the specified BehaviorTree.

@airenametree - renames the specified BehaviorTree.

@aideltree - deletes the specified BehaviorTree.

@aiassigntree - assigns the specified BehaviorTree as the origin tree of a given
                agent.

@ailist - shows a list of all BehaviorTrees currently in the game.

@ailook - displays a node's data, a node instance's data or the global data of
          a given agent.

@aistatus - displays what tree, node and agent the player is currently browsing

@aiwatch - adds a node instance to the player's watchlist, ensuring that
           information about it is displayed whenever the node is run.

@aiunwatch - removes a node instance from the player's watchlist

@aigo - sets the player's browsing cursor to a given tree and node

@aibb - sets the player's browsing cursor to a given agent

@aiup - moves the browsing cursor to the currently browsed node's parent

@aidown - moves the browsing cursor to one of the currently browsed node's
          children

@aisetprop - assigns a value to a node's property, a node instance's entry or
             an agent's global data

@aidelprop - removes a node's property, a node instance's entry or an agent's
             global data

@aiaddnode - adds a node of the specified type to a location in the target tree

@aicopynode - attaches a copy of the specified node to another node

@aimovenode - moves a specified node under another node

@aiswap - swaps the locations of two nodes

@aishift - shifts the position of a node in its parent node's list of children

@airemove - removes a node from its tree

Note that, at present, there is no way to convert AI trees stored in the
game's database into Python code. I can make that feature available on
request, however.

### Adding your own node types

If you are not a coder, this section will not be useful to you.

The AI system provides barebones functionality, but you will want to create
a set of nodes tailored to your own game. To this end, you need to subclass
either one of the fully functional node classes that come with the AI system,
or the LeafNode, DecoratorNode and CompositeNode classes, which have no
functionality. You should never subclass your nodes from the Node or RootNode
class.

Each node you create has a `weight` property that should not be overriden, but
can be assigned a float value to determine how likely this node is to be picked
by a ProbSelector or ProbSequence node.

Each node also has a `name` property that contains the name you assigned it,
as well as a `hash` property, which contains three alphanumeric characters that
are unique to the node within a given tree, followed by an underscore character
and the id number of its tree. For instance: `H5q_1566`, `Zmr_43`, `7Fl_5425163`
The first three characters of this hash are used by the AI system's various
commands and can be used to reference the nodes when two or more nodes in the
tree share the same name.

Each node contains the following methods, all of which may be overridden.
With the exception of the update() method, all of them should feature a call to
`super()`. Many of the methods have the `bb` argument, which is the blackboard
of the agent whose AI is running.

`update(self, bb)` - this method performs the procedure that occurs whenever the
node runs. If the node has a child, it should probably call it at some
point via a line such as the following:

```
status = node.children.tick(bb)
```

Here, status is the child's return status, either SUCCESS, FAILURE, RUNNING or
ERROR. As mentioned above in the "Setting up the AI system" section, all these
statuses are constants that may be imported from the `evennia.contrib.aisystem`
module.

If the node is a composite node, it will have a list of children rather than
one child. In this case, you will probably want to run some or all of its
children. For instance:

```
for child in node.children: 
    [...]
    child.tick(bb)
    [...]
```

Be sure to have the update method return a status, either SUCCESS, FAILURE,
RUNNING or ERROR. Exceptions are automatically handled by the ai system (see
below), but you can override the system's functionality.

The tick method should always have one argument, the blackboard in the update
method's own arguments list.

`open(self, bb)` - this method sets up a node instance that did not return
RUNNING during the previous iteration of the AI. It is called immediately before
`update(bb)`. You can use it to, for instance, reset the node instance's
node-specific data. 

`close(self, bb)` - this method cleans up a node that did not return RUNNING
during the previous iteration of the AI. It is called after the AI has finished
iterating through the tree.

`on_add_child(self, node)` - called after a node (specified in the arguments
list) is set as this node's child or added to this node's list of children.

`on_remove_child(self, node)` - called after a node (specified in the arguments
list) is no longer this node's child or is removed from this node's list of
children.

`on_blackboard_setup(self, bb, override=False)` - called whenever the blackboard
associated with an instance of this node is set up. The override argument
supplied is the same one provided by the @aisetup command (if no override
argument is provided to that command, the override argument for
on\_blackboard\_setup is set to False, else it is True).

You should ideally set blackboard data within the on\_blackboard\_setup method
using the following pattern:
```
    if not bb['nodes'][self.hash].has_key(key_name) or override:
        bb['nodes'][self.hash][key_name] = value

    if not bb['globals'].has_key(globals_key_name) or override:
        bb['globals'][globals_key_name] = globals_value
```

The following blackboard data is available:

`bb['agent']` - the agent that holds the blackboard

`bb['tree']` - the agent's origin tree

`bb['nodes'][some_node.hash]` - the dictionary of node-specific data for
                                `some_node`

`bb['globals']` - the dictionary of the agent's global data

For more information on the entries of the latter two dictionaries, see the
"Blackboards" section.

Nodes automatically handle exceptions encountered within the `update` method by
storing the error message and returning the ERROR status. Ultimately, if the
nodes you have coded are set up properly (i.e. they return ERROR whenever one of
their children returns ERROR) the entire tree will return the ERROR status, so
you can check for that status within your scripts or tickerhandlers and display
that error message accordingly. Errors are stored in the dictionary
`bb['globals']['errors']`, whose keys are the full hash values of the nodes
that have encountered errors. To add an error string to the dictionary, do this:

```
bb['globals']['errors'][node.hash] = error_string
```

The tree does not clean up its error strings automatically. To do so, you should
run the agent's `ai.clean()` method:

```
agent.ai.clean()
```

Finally, you should never need to overload the node's \_\_init\_\_ method.

### Limitations

The theoretical upper limit for the number of nodes in a tree is 238,328.
There is a risk of nodes failing to be generated as you approach that limit. 
You should probably split your tree up into multiple trees connected by 
Transition nodes well before this starts to happen, however.

In theory, in extremely rare cases, a node might fail to generate a hash due to
too many failed attempts at creating a hash that does not match the hashes of
any nodes that already exist in the tree. Should you be informed that this
has happened, simply create the node again.

No tree, node or blackboard may be named 'this', as the name 'this' is a 
keyword in some commands signifying the currently browsed tree or blackboard.
Also, the names of trees, nodes and blackboards must not contain single quotes
or equals signs, as these are also used by various commands.

The names of your trees, blackboards AI agents and AI scripts should ideally
not be numbers, as you will otherwise have to refer to them exclusively via
their database ids in the aisystem commands.

The data properties of any nodes you create should not have a __call__ method.
If they do, they will not be displayed appropriately by the @ailook command, 
which attempts to avoid displaying the node's methods by ignoring properties
with a __call__ method and will also therefore fail to display your own.

If there is a feature you would like added to this system, or if you find a
bug or typo that needs fixing, don't hesitate to contact me on my github
account, andrei-pmbcn, or at my email address, andreipmbcn at yahoo dot com.
I am Andrei Pambuccian, the maintainer of this contrib.
