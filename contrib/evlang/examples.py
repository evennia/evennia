"""

Evlang - usage examples

Craftable object with matching command

Evennia contribution - Griatch 2012

"""

from ev import create_object
from ev import default_cmds
from contrib.evlang.objects import ScriptableObject

#------------------------------------------------------------
# Example for creating a scriptable object with a custom
# "crafting" command that sets coding restrictions on the
# object.
#------------------------------------------------------------

class CmdCraftScriptable(default_cmds.MuxCommand):
    """
     craft a scriptable object

     Usage:
       @craftscriptable <name>

    """
    key = "@craftscriptable"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):
        "Implements the command"
        caller = self.caller
        if not self.args:
           caller.msg("Usage: @craftscriptable <name>")
           return
        objname = self.args.strip()
        obj = create_object(CraftedScriptableObject, key=objname, location=caller.location)
        if not obj:
            caller.msg("There was an error creating %s!" % objname)
            return
        # set locks on the object restrictive coding only to us, the creator.
        obj.db.evlang_locks = {"get":"code:id(%s) or perm(Wizards)" % caller.dbref,
                               "drop":"code:id(%s) or perm(Wizards)" % caller.dbref,
                               "look": "code:id(%s) or perm(Wizards)" % caller.dbref}
        caller.msg("Crafted %s. Use @desc and @code to customize it." % objname)


class CraftedScriptableObject(ScriptableObject):
    """
    An object which allows customization of what happens when it is
    dropped, taken or examined. It is meant to be created with the
    special command CmdCraftScriptable above, for example as part of
    an in-game "crafting" operation. It can henceforth be expanded
    with custom scripting with the @code command (and only the crafter
    (and Wizards) will be able to do so).

    Allowed Evlang scripts:
       "get"
       "drop"
       "look"
    """
    def at_get(self, getter):
        "called when object is picked up"
        self.ndb.evlang.run_by_name("get", getter)
    def at_drop(self, dropper):
        "called when object is dropped"
        self.ndb.evlang.run_by_name("drop", dropper)
    def at_desc(self, looker):
        "called when object is being looked at."
        self.ndb.evlang.run_by_name("look", looker)
