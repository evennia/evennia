"""
Puzzle Objects Module
=====================

Contribution - Henddher 2014

This module allows the creation of puzzles.
One or more objects may be combined to form
a new object.

Example:

(Builder only)
A Builder creates a puzzle by listing the puzzle 
object and all the required parts. This
is done via the '@mkpuzzle' command (CmdMakePuzzle).

    @create/drop wood pieces
    @create/drop tools
    @create/drop bird house

    @mkpuzzle bird house = wood pieces, tools

Later, when a player combines all the parts, by
invoking the 'use' command, the puzzle object is revealed.  

(Players)
You see: wood pieces, tools

    use wood pieces, tools
    ...
    Great! 
    You have built a bird house.


Installation:
-------------

To test, make sure to follow the instructions in 
game/gamesrc/commands/examples/cmdset.py (copy the template up
one level and change settings to point to the relevant cmdsets within).

Import this module in your custom cmdset module and add the 
following lines to the end of DefaultCmdSet's
at_cmdset_creation():

   from contrib import puzzle_objects
   self.add(puzzle_objects.CmdUse())
   self.add(puzzle_objects.CmdMakePuzzle())

After @reload, both commands will be available in-game.

Alternatively, the commands can be added on the fly:

    @py self.cmdset.add(puzzle_objects.CmdUse())
    @py self.cmdset.add(puzzle_objects.CmdMakePuzzle())

Notes:
------

* '@mkpuzzle' does not create new objects. Instead,
  it uses existing objects.

* 'use' command does not change locks in any of the
  objects. Instead, it moves the puzzle object to the location
  of the player calling 'use'. Then, it moves the parts
  into the contents of the puzzle object so these cannot
  be used again.

* Any object can be used in a puzzle, this includes characters,
  mobs, rooms and exits - even self. There are no restrictions. 
  
* When a room (or exit) is the 'puzzle' object,
  the player solving the puzzle is automatically teleported to the room.  
  When a room is used as part, the player must be present in that room 
  and list it as one of the parts.

      Example:

      (builder)
      @dig Cliff
      @tel Cliff
      @create/drop paper sheet
      @create/drop paper airplane
      @mkpuzzle paper airplane = paper sheet, Cliff

      (players)
      Cliff
      You see: paper sheet
        use paper sheet, here
        ...
      Genius!
      You fold the paper sheet and make an airplane. You toss it 
      and watch it fly away over the chasm ...

"""

from ev import Command
from ev import default_cmds
from ev import utils
from ev import Room
from ev import Object
import random

__all__ = ("CmdUse", "CmdMakePuzzle")

class CmdUse(default_cmds.MuxCommand):
    """
    Use command

    You may combine one or more objects to create a new object.

    The command gives hints if an object is usable or not.

    You may use any object in your current location or in your 
    inventory. Exits, rooms, and even characters may be used. 

    Usage:
        use <object> [, another object [, another object [, ...]]]

    Example: 

        You see: wood pieces, tools
            use wood pieces, tools
        ...
        Great! 
        You have built a bird house.

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

class CmdMakePuzzle(default_cmds.MuxCommand):
    """
    Make Puzzle command

    Allows the creation of a puzzle by declaring the 
    the puzzle object and the parts needed to solve it.

    Usage:
        @mkpuzzle <puzzle object> = <part object> [, another part object [, ...]]]

    When 'here' is used as part object, the current room becomes a part.

    Note: All objects must be in the current location or within
    the builder's inventory.

    Example:

        @create/drop wood pieces
        @create/drop tools 
        @create/drop bird house

        @mkpuzzle bird house = wood pieces, tools

    """

    __usage_msg = \
    """
    Usage: @mkpuzzle <puzzle object> = [part object [, another part object [, ...]]]
   
    Or 'help @mkpuzzle' for detailed info
    """

    key = "@mkpuzzle"
    locks = "cmd: perm(mkpuzzle) or perm(Builders)"
    help_category = "Building"

    def func(self):
        """
        Creates a Use relationship among the specified objects

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
        if not prod_obj:
            # incorrect invocation, show usage msg
            self.caller.msg(self.__usage_msg)
            return

        # retrieve the parts
        parts = set()
        for pon in self.rhslist:
            po = self.caller.search(pon)
            if po:
                parts.add(po)
            else:
                # incorrect invocation, show usage msg
                self.caller.msg(self.__usage_msg)
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
