"""
Usable Objects Module
=====================

Contribution - Henddher 2014

This module allows the creation of puzzle-like objects in which
some existing objects -the parts- must be combined, via the in character
'use' command, to materialize another object - the produced object.

There are two commands in this module: 
- The 'use' command (UseCmd) for Players 
- The '@mkusable' (MakeUsableCmd) for Builders

Use Command (for Players)
-------------------------

The use command allows to combine multiple objects, parts, 
and materialize a new one, the produced object. This command
is intended for players. A player may come accross objects
and by combining them, a new object is materialized. 
The command provides hints, as messages to the caller, when 
objects are usable or not.

Usage:
    use <object> [, another object [, another object [ , ...]]]

Any object may be listed, including the current location.

Example:

Cliff
    Deep chasm in front of you ... birds take off as you get closer to
    the edge. A sturdy tree grows near. Across the void, the other side ...
You see: jetpack, rope, tree

    use jetpack, here
    ... 
    Awesome! you make it to the other side ...

OR

    use rope, tree
    ...
    Awesome! you make it to the other side ...


The Make Usable Command (for Builders)
--------------------------------------

The make usable command, @mkusable, allows builders to 
create puzzle-like objects. It tags an existing object as
the produced object by declaring which objects are its parts.
This command does not create objects, it just sets a use
relationship among them. More about use relationship below.

Usage:
    @mkusable <produced object> = <part object> [, another part [, ...] ]

    When 'here' is used, the current room becomes a member of 
    the use relationship (either as part or as produced object).

Example:

Cliff
    Deep chasm in front of you ... birds take off as you get closer to
    the edge. A sturdy tree grows near. Across the void, the other side ...
You see: jetpack, rope, tree

    @mkusable The Other Side of Cliff = jetpack, Cliff
OR
    @mkusable The Other Side of Cliff = rope, tree

Installation:
-------------

To test, make sure to follow the instructions in 
game/gamesrc/commands/examples/cmdset.py (copy the template up
one level and change settings to point to the relevant cmdsets within).

Import this module in your custom cmdset module and add the 
following lines to the end of DefaultCmdSet's
at_cmdset_creation():

   from contrib import use_objects
   self.add(use_objects.UseCmd())
   self.add(use_objects.MakeUsableCmd())

After @reload, both commands will be available in-game.

Alternatively, the commands can be added on the fly:

    @py self.cmdset.add(use_objects.UseCmd())
    @py self.cmdset.add(use_objects.MakeUsableCmd())

The Use Module Under the Hood
-----------------------------

Under the hood, the module associates an object - the produced object -
to other objects as its parts. Any existing object can become part
of a use relationship.

The USE relationship:

The incarnation of one use is represented by a directed graph.
In this object graph, there are two types of nodes: one node that 
represents the produced object, and one or mode nodes that represent 
the constituting objects, the parts. Any object can be a produced 
object, but also a part in another graph. Multiple graphs can have nodes
that act as parts and/or produced objects. In summary, a single 
object can be produced by different combinations of parts and a single
part can be used to produced multiple objects.

The graph has two types of directed edges: 'usages' and 'objs_needed'. 
Each edge is represented by the 'dbref' of the destination object-node. 
The produced object has a set of edges 'objs_needed' 
from itself to its parts. At the same time, each part has a set of 
edges to all the produced objects it's part of, this set is named 
'usages'. 

Appart from set of edges, a produced object has 2 special persisted 
attributes: 'is_portable' and 'successfully_used_msg'. 
The first one defines if the object can be added to the inventory 
of the command caller. The second attribute is a message displayed 
to the caller when all parts needed are present and listed in the 
invocation of the use command. Parts must be either at the caller's 
location or in the caller's inventory.

Creating one USE relationship graph:

The following snippet of MUX commands depics the creation of a 
USE relationship graph. All objects must be created before the use 
relationship graph can be defined; this is because each object's 'dbref' 
is used as edge. In this example, a 'pile of snow', and a 'bunch
of snow' are used to produce a 'large snowball'.

# Create all objects participating in the use relationship

# creation of the parts
@create/drop bunch of snow
@find bunch of snow
    bunch of snow(#325) - src.objects.objects.Object
@create/drop pile of snow
@find pile of snow
    pile of snow(#326) - src.objects.objects.Object

# creation of the produced object
@create large snowball
@find large snowball
    large snowball(#327) - src.objects.objects.Object

The @mkusable command simplifies the creation of a USE relationship.
The invocation declares the produced object (lhs) and the parts (rhs).

Example:

    @mkusable large snowball = pile of snow, bunch of snow

@mkusable, under the hood, populates all edges: 'usages' and 'objs_needed'.

Alternative, builders may create edges using @py commands:

# Declare the 'usages' edges 

    @py ev.search_object("#325")[0].db.usages = set(["#327"])
    @py ev.search_object("#326")[0].db.usages = set(["#327"])

# Declare the 'objs_needed' edges 

    @py ev.search_object("#327")[0].db.objs_needed = set(["#325", "#326"])

# Declare if the produced object can be carried around (added to inventory)

    @py ev.search_object("#327")[0].db.is_portable = True

Finally, declaring successfully_used_msg and is_portable allows
to add more flavor to the use relationship

# Declare the success message when the produced object is materialized

    @py ev.search_object("#327")[0].db.successfully_used_msg = 
        "Though you feel your fingers tickling after a while, you manage to 
        roll a large snowball"

Notes about the produced object, its parts, and locations:

Given that all objects must exists prior defining their use
relationship, it's imperative that all appropriate locks are in placed
to prevent that a produced object can be found without its parts being
used. Hence, it's strongly recommended that the initial location of the 
produced object is one that the users have no access to. Under this 
condition, the only viable means to materialize the produced object would
be by invoking the use command with all parts available.

Also, once the produced object is materialized, all its parts are 
placed in the produced object contents. This is to prevent that 
the same parts are used by someone else later to produce the 
same object and remove it from its current owner inventory. 
Once again, appropriate locks must be added to all objects so 
the extraction of the parts is not possible. 

Finally, rooms can participate in any USE relationship graph. Either 
as a part or as a produced object. If the room is a part, the 
caller of the command would need to list the current room in the use
command. When the produced object is a room, the caller would be 
automatically teleported to the room. 

"""

from ev import Command
from ev import default_cmds
from ev import utils
from ev import Room
from ev import Object
import random

__all__ = ("UseCmd", "MakeUsableCmd")

class UseCmd(default_cmds.MuxCommand):
    """
    Use command

    Usage:
        use <object> [, another object [, another object [, ...]]]

        Use an object or a group of objects. If more than one object 
        is listed, the use command combines all objects to 
        materialize a new object.

        The current room may be listed as argument.

        Example: 

        Cliff
            use jetpack, here
        You strap the jetpack to your back, press the ignition button
        and SHMM ... you are flying over the chasm to the other edge 
        of the cliff

    """
    key = "use"
    locks = "cmd:all()"
    arg_regex = r"\s.*?|$"

    def func(self):
        """
        Implements the command.
        """

        # list of objects, separated by commas
        targets = [t for t in self.lhslist if len(t) > 0]

        # no arguments? show 'error'
        if len(targets) == 0:
            self.caller.msg("Use what?")
            return

        # messages to hint the player if an object has any use or none
        # bad msgs: the object has no use
        # good msgs: the object has some use
        bad_msgs = ["You hurt your finger trying to use {0}.",
                    "As you try to use {0} with the others, it drops and hurts your left foot.", 
                    "While trying to hold {0} steady, it slips and hits you in the face."]
        good_msgs = ["You look closely at {0} but you can't figure out what to do next.",
                "You examine {0} but you have no clue how to go about.",
                "As you shake {0}, you hear rattling noises but nothing else happens."]

        # set of usable objects (those with a use), aka 'parts'
        usable_objs = set()
        for t in targets:
            if t.lower() == "here":
                objs = [self.caller.location];
            else:
                objs = self.caller.search(t, quiet = True)
            if not objs:
                # caller doesn't have it or it's not in caller's location
                self.caller.msg("You don't have any {0}".format(t))
                return
            else:
                if len(objs) > 1:
                    # too many matches
                    self.caller.msg("Among {0} ...".format(",".join([o.name for o in objs])))
                    self.caller.msg("Which one in particular?")
                    return
                else:
                    # one match
                    obj = objs[0]
                    if obj.db.usages and len(obj.db.usages) > 0:
                        # it's usable - somehow
                        usable_objs.add(objs[0])
                    else:
                        # it has no usages
                        self.caller.msg(random.choice(bad_msgs).format(obj))
                        self.caller.msg("You are sure this has no use.")
                        return

        # combine usages of all parts (i.e. set intersection) 
        # to see if the parts can be 
        # used together to materialize a produced object
        usages = random.choice(list(usable_objs)).db.usages # start with one object usages
        objs_avail = set()
        for uobj in usable_objs:
            usages &= uobj.db.usages
            objs_avail.add(uobj.dbref)
        for usage in usages:
            # usage is the dbref of the object produced 
            # by combining all usable_objs
            prod_obj = self.caller.search(usage)
            objs_needed = prod_obj.db.objs_needed
            usable_objs_names = ", ".join([uo.name for uo in usable_objs])
            if objs_avail.issuperset(objs_needed):
                # all needed are avail (perhaps even some extras)
                for uo in usable_objs:
                    # must put uo inside prod_obj to "hide" it 
                    if uo.dbref in objs_needed:
                        uo.move_to(prod_obj, quiet = True)
                # show success message - the produced object can be materialized
                self.caller.msg("You start experimenting with {0} in multiple ways ...".format(usable_objs_names))
                if len(usable_objs) > 1:
                    list_usable_objs = list(usable_objs)
                    self.caller.msg("First {0} ... ".format(list_usable_objs[0].name))
                    for i in range(1, len(list_usable_objs)):
                        self.caller.msg("... then {0} ... ".format(list_usable_objs[i].name))
                voila_msgs = ["Voila", "Eureka", "Awesome", "Genius"]
                self.caller.msg("... {0}!!! \n{1}".format(random.choice(voila_msgs), prod_obj.db.successfully_used_msg))
                if prod_obj.is_typeclass(Room):
                    # a room, teleport into it
                    self.caller.move_to(prod_obj, quiet = True)
                    return
                elif prod_obj.db.is_portable:
                    # portable can be carried around
                    self.caller.msg("You now have {0}.".format(prod_obj.name))
                    prod_obj.move_to(self.caller, quiet = True)
                    return
                else:
                    # let it appear here
                    self.caller.msg("{0} is here now.".format(prod_obj.name))
                    prod_obj.move_to(self.caller.location, quiet = True)
                    return
            else:
                # something's missing - one or more parts are still needed
                self.caller.msg(random.choice(good_msgs).format(usable_objs_names))
                self.caller.msg("You are sure that something else is missing.")
                return

class MakeUsableCmd(default_cmds.MuxCommand):
    """
    Make Usable command

    The make usable command allows builders to 
    create puzzle-like objects. It tags an existing object as
    the produced object and the other objects are parts.

    Usage:
        @mkusable <produced object> = <part object> [, another part object [, ...]]]

    When 'here' is used as part object, the current room becomes a part.

    Example:

    Cliff
        Deep chasm in front of you ... birds take off as you get closer to
        the edge. A sturdy tree grows near. Across the void, the other side ...
    You see: jetpack, rope, tree

        @mkusable The Other Side of Cliff = jetpack, Cliff
    OR
        @mkusable The Other Side of Cliff = rope, tree

    """

    __usage_msg = \
    """
    Usage: @mkusable <produced object> = [part object [, another part object [, ...]]]
   
    Or 'help @mkusable' for detailed info
    """

    key = "@mkusable"
    locks = "cmd: perm(mkusable) or perm(Builders)"
    help_category = "Building"

    def func(self):
        """
        Creates a Use relationship among the specified objects

        Inherits ObjManipCommand.parse()
        Expects one lhslist and one or mode rhslist

        """
        if len(self.lhslist) != 1 \
            or not self.rhs \
            or len(self.rhslist) == 0:

            # incorrect invocation, show usage msg
            self.caller.msg(self.__usage_msg)
            return

        # retrieve the produced object
        prod_obj = self.caller.search(self.lhslist[0])

        # retrieve the parts
        parts = set()
        for pon in self.rhslist:
            po = self.caller.search(pon)
            if po:
                parts.add(po)
            else:
                self.caller.msg("{} couldn't be found".format(pon))
                return

        # create use relationship
        for po in parts:
            self.add_as_part(prod_obj, po)

        # init default success message and not portable
        self.init_produced_obj(prod_obj)

        # show success
        self.caller.msg( \
        "Usable object {} is ready.\nIt can be materialized by executing" \
        " the command 'use {}'".format(prod_obj.name, \
        ",".join([po.name for po in parts])))
        
        # remind caller to set success message and is_portable
        # and to hide the objects or move them to a suitable location
        helpmsg = \
        "Please remember to locate the objects according to the puzzle.\n" \
        + "You should also set the success message and set define if" \
        + " the object is portable by issuing the following commands:\n" \
        + "@set {0}/is_portable = True/False\n" \
        + "@set {0}/successfully_used_msg = message\n"
        self.caller.msg(helpmsg.format(prod_obj.name))

    def init_produced_obj(self, prod_obj, success_msg="", is_portable=False): 
        """ 
        Sets success message and portability of produced object 
        """
        prod_obj.db.successfully_used_msg = success_msg
        prod_obj.db.is_portable = is_portable

    def add_as_part(self, prod_obj, another_object):
        """
        Helper method to create USE relationship graph
        
        Populates edges 'usage' and 'objs_needed'
        """
        if prod_obj.db.objs_needed == None:
            prod_obj.db.objs_needed = set()
        prod_obj.db.objs_needed.add(another_object.dbref)
        if another_object.db.usages == None:
            another_object.db.usages = set()
        another_object.db.usages.add(prod_obj.dbref)
