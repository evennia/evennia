"""
Use Command. 

The use command allows to combine multiple objects, the parts, and materialize a new one, the produced object.

The USE relationship:

The incarnation of one use is represented by a directed graph.
In this object graph, there are two types of nodes: one node that 
represents the produced object, and one or mode nodes that represent 
the constituting objects, the parts. Any object can be a produced 
object, but also a part in another graph. Multiple graphs can have nodes
that act as parts and/or produced objects. In other words, a single 
object can be produced by different combinations of parts and a single
part can be used to produced multiple objects.

A graph has two types of directed edges: 'usages' and 'objs_needed'. 
Each edge is represented by the 'dbref' of the destination object-node. 
The produced object has a set 'objs_needed' that represents edges 
from itself to its parts. At the same time, each part has a set of 
edges to all the produced objects it's part of, this set is named 
'usages'. 

Appart from set of edges, a produced object has 2 special persisted 
attributes: 'is_portable' and 'successfully_completed_msg'. 
The first one defines if the object can be added to the inventory 
of the command caller. The second attribute is a message displayed 
to the caller when all parts needed are present and listed in the 
invocation of the use command. Parts must be either at the caller's 
location or in the caller's inventory.

Creating one USE relationship graph:

The following snippet of MUX commands depics the creation of a 
USE relationship graph. All objects must be created before the use 
command graph can be defined; this is because each object's 'dbref' 
is used as edge. In this example, a 'pile of snow', and a 'bunch
of snow' are used to produce a 'large snowball'.

# Create all objects participating

# The parts
@create/drop bunch of snow
@find bunch of snow
    bunch of snow(#325) - src.objects.objects.Object
@create/drop pile of snow
@find pile of snow
    pile of snow(#326) - src.objects.objects.Object

# The produced object
@create large snowball
@find large snowball
    large snowball(#327) - src.objects.objects.Object

# Declare the 'usages' edges 
@py ev.search_object("#325")[0].db.usages = set(["#327"])
@py ev.search_object("#326")[0].db.usages = set(["#327"])

# Declare the 'objs_needed' edges 
@py ev.search_object("#327")[0].db.objs_needed = set(["#325", "#326"])

# Declare if the produced object can be carried around (added to inventory)
@py ev.search_object("#327")[0].db.is_portable = True

# Declare the success message when the produced object is materialized
@py ev.search_object("#327")[0].db.successfully_produced_msg = 
    "Though you feel your fingers tickling after a while, you manage to 
    roll a large snowball"

Notes about the produced object, its parts, and locations:

Given that all objects must exists prior defining their use
relationship, it's imperative that all appropriate locks are in placed
to prevent that a produced object can be found without its parts being
used. Hence, it's strongly recommended that the initial location of the 
produced object is one that the users have no access to. Under this 
condition, the only viable means to materialize the produced object would
be by invoking the use command with all its parts available.

Also, once the produced object is materialized, all its parts are 
placed in its contents. This is to prevent that the same parts are 
used by someone else later to produce the same object and remove it
from its current owner inventary. Once again, appropriate locks must be 
added to all objects so the extraction of the parts is not possible. 

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
import random

class CmdUse(default_cmds.MuxCommand):
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
        targets = [t for t in self.lhslist if len(t) > 0]

        # no arguments
        if len(targets) == 0:
            self.caller.msg("Use what?")
            return

        bad_msgs = ["You hurt your finger trying to use {0}.",
                    "As you try to use {0} with the others, it drops and hurts your left foot.", 
                    "While trying to hold {0} steady, it slips and hits you in the face."]
        good_msgs = ["You look closely at {0} but you can't figure out what to do next.",
                "You examine {0} but you have no clue how to go about.",
                "As you shake {0}, you hear rattling noises but nothing else happens."]

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

        # combine usages (set intersection) to see if they can be used together
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
                # show success message
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
                # something's missing
                self.caller.msg(random.choice(good_msgs).format(usable_objs_names))
                self.caller.msg("You are sure that something else is missing.")
                return
