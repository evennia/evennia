"""

Template module for Exits

Copy this module up one level and name it as you like, then
use it as a template to create your own Exits.

To make the default commands (such as @dig/@open) default to creating exits
of your new type, change settings.BASE_EXIT_TYPECLASS to point to
your new class, e.g.

settings.BASE_EXIT_TYPECLASS = "game.gamesrc.objects.myexit.MyExit"

Note that objects already created in the database will not notice
this change, you have to convert them manually e.g. with the
@typeclass command.

"""
from ev import Exit

class ExampleExit(Exit):
    """
    Exits are connectors between rooms. Exits are normal Objects except
    they defines the 'destination' property. It also does work in the
    following methods:

     basetype_setup() - sets default exit locks (to change, use at_object_creation instead)
     at_cmdset_get() - this auto-creates and caches a command and a command set on itself
                     with the same name as the Exit object. This
                     allows users to use the exit by only giving its
                     name alone on the command line.
     at_failed_traverse() - gives a default error message ("You cannot
                            go there") if exit traversal fails and an
                            attribute err_traverse is not defined.

    Relevant hooks to overload (compared to other types of Objects):
    at_before_traverse(traveller) - called just before traversing
    at_after_traverse(traveller, source_loc) - called just after traversing
    at_failed_traverse(traveller) - called if traversal failed for some reason. Will
                                    not be called if the attribute 'err_traverse' is
                                    defined, in which case that will simply be echoed.
    """
    pass
