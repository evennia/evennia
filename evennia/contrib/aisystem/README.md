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



### Working with behavior trees in-game
















### Coding behavior trees

If you want to create a new behavior tree or behavior blackboard via code
rather than in-game, be sure to give this object a name 
(```<object>.name = name```), assign it a tree if it is a blackboard
(```<object>.tree = <tree>```), also assign it an agent if it is a blackboard
(```<object>.agent = <agent>```), and finally run the object's setup()
method, which assigns default values to all database-stored properties and,
if the object is a behavior tree, generates a root node.




### Limitations

No tree, node or blackboard may be named 'this', as the name 'this' is a keyword
in some commands signifying the currently browsed tree or blackboard. Also, the
names of trees, nodes and blackboards must not contain single quotes, as these
are also used by various commands.

The names of your trees, blackboards AI agents and AI scripts should ideally
not be numbers, as you will otherwise have to refer to them via their database
ids in the aisystem commands.

The data properties of any nodes you create should not have a __call__ method.
If they do, they will not be displayed appropriately by the @ailook command, 
which attempts to avoid displaying the node's methods.



