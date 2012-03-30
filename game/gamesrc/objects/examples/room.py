"""

Template module for Rooms

Copy this module up one level and name it as you like, then
use it as a template to create your own Objects.

To make the default commands (such as @dig) default to creating rooms
of your new type, change settings.BASE_ROOM_TYPECLASS to point to
your new class, e.g.

settings.BASE_ROOM_TYPECLASS = "game.gamesrc.objects.myroom.MyRoom"

Note that objects already created in the database will not notice
this change, you have to convert them manually e.g. with the
@typeclass command.

"""

from ev import Room

class ExampleRoom(Room):
    """
    Rooms are like any Object, except their location is None
    (which is default). They also use basetype_setup() to
    add locks so they cannot be puppeted or picked up.
    (to change that, use at_object_creation instead)

    See examples/object.py for a list of
    properties and methods available on all Objects.
    """
    pass
