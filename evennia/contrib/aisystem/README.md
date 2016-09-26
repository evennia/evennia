## Behavior tree-based AI





#### Trees





#### Basic node types





#### Composite nodes





#### Decorators





#### Blackboards






Some nodes, such as parallel nodes, store their operational parameters,
such as how many successes must be returned by the node's children in order
for the node itself to succeed, in their blackboards as well as on the node
objects themselves. Although you can assign these parameters manually on
the blackboard, it is highly recommended that you do not, as any changes
to the tree that the blackboard maps onto will require the blackboard to
be reset, thus overriding your manual assignments. Instead, only use the
blackboard to make changes to the parameters that would arise automatically
in the course of iterating through the behavior tree. For instance, one
node might modify another node's parameters when it is ticked. In all other
cases, you should modify the parameters on the node objects directly.


### Setting up the ai system


* subclass players that will build the AI system from AIPlayer, 
objects / characters that will incorporate AI from AIObject and
scripts that will store AI trees from AIScript

* player builder data


You do not need to set up any trees you create, as all their attributes
are assigned automatically on creation, but the option exists in case future
expansions add new features that require setting up.









### Working with behavior trees in-game















### Adding your own node types



```on_add_child()```
```on_remove_child()```




```bb['globals']['errors'][node.hash] = error_string```







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
not be numbers, as you will otherwise have to refer to them via their database
ids in the aisystem commands.

The data properties of any nodes you create should not have a __call__ method.
If they do, they will not be displayed appropriately by the @ailook command, 
which attempts to avoid displaying the node's methods.



