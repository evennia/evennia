"""
Containers

Contribution by InspectorCaracal (2023)

Adds the ability to put objects into other container objects by providing a container typeclass and extending certain base commands.

To install, import and add the `ContainerCmdSet` to `CharacterCmdSet` in your `default_cmdsets.py` file:

    from evennia.contrib.game_systems.containers import ContainerCmdSet

    class CharacterCmdSet(default_cmds.CharacterCmdSet):
        # ...
        
        def at_cmdset_creation(self):
            # ...
            self.add(ContainerCmdSet)

The ContainerCmdSet includes:

 - a modified `look` command to look at or inside objects
 - a modified `get` command to get objects from your location or inside objects
 - a new `put` command to put objects from your inventory into other objects

Create objects with the `ContainerObject` typeclass to easily create containers,
or implement the same locks/hooks in your own typeclasses.

`ContainerObject` implements the following new methods:

    at_pre_get_from(getter, target, **kwargs) - called with the pre-get hooks
    at_pre_put_in(putter, target, **kwargs)   - called with the pre-put hooks
"""
from django.conf import settings

from evennia import AttributeProperty, CmdSet, DefaultObject
from evennia.commands.default.general import CmdLook, CmdGet, CmdDrop
from evennia.utils import class_from_module

# establish the right inheritance for container objects
_BASE_OBJECT_TYPECLASS = class_from_module(settings.BASE_OBJECT_TYPECLASS, DefaultObject)


class ContainerObject(_BASE_OBJECT_TYPECLASS):
    """
    A type of Object which can be used as a container.

    It implements a very basic "size" limitation that is just a flat number of objects.
    """

    # This defines how many objects the container can hold.
    capacity = AttributeProperty(default=20)

    def at_object_creation(self):
        super().at_object_creation()
        # adds a lock permission to allow items to be put inside or taken out
        # by default, a lock type not being explicitly set will fail access checks, so normal
        # objects without the get_from type set will fail get_from access checks
        self.locks.add("get_from:true()")

    def at_pre_get_from(self, getter, target, **kwargs):
        """
        This will be called when something attempts to get another object FROM this object,
        rather than when getting this object itself.

        Args:
            getter (Object): The actor attempting to take something from this object.
            target (Object): The thing this object contains that is being removed.
        """
        return True

    def at_pre_put_in(self, putter, target, **kwargs):
        """
        This will be called when something attempts to put another object into this object.

        Args:
            putter (Object): The actor attempting to put something in this object.
            target (Object): The thing being put into this object.

        NOTE:
            To add more complex capacity checks, modify this method on your child typeclass.
        """
        # check if we're already at capacity
        if len(self.contents) >= self.capacity:
            singular, _ = self.get_numbered_name(1, putter)
            putter.msg(f"You can't fit anything else in {singular}.")
            return False

        return True


class CmdContainerLook(CmdLook):
    """
    look at location or object

    Usage:
      look
      look <obj>
      look <obj> in <container>
      look *<account>

    Observes your location or objects in your vicinity.
    """

    rhs_split = (" in ",)

    def func(self):
        """
        Handle the looking.
        """
        caller = self.caller
        # by default, we don't look in anything
        container = None

        if not self.args:
            target = caller.location
            if not target:
                self.msg("You have no location to look at!")
                return
        elif self.rhs:
            # we are looking in something, find that first
            container = caller.search(self.rhs)
            if not container:
                return

        target = caller.search(self.lhs, location=container)
        if not target:
            return

        desc = caller.at_look(target)
        # add the type=look to the outputfunc to make it
        # easy to separate this output in client.
        self.msg(text=(desc, {"type": "look"}), options=None)


class CmdContainerGet(CmdGet):
    """
    pick up something

    Usage:
      get <obj>
      get <obj> from <container>

    Picks up an object from your location or a container and puts it in
    your inventory.
    """

    rhs_split = (" from ",)

    def func(self):
        caller = self.caller
        # by default, we get from the caller's location
        location = caller.location

        if not self.args:
            self.msg("Get what?")
            return

        # check for a container as the location to get from
        if self.rhs:
            location = caller.search(self.rhs)
            if not location:
                return
            # check access lock
            if not location.access(caller, "get_from"):
                # supports custom error messages on individual containers
                if location.db.get_from_err_msg:
                    self.msg(location.db.get_from_err_msg)
                else:
                    self.msg("You can't get things from that.")
                return

        obj = caller.search(self.lhs, location=location)
        if not obj:
            return
        if caller == obj:
            self.msg("You can't get yourself.")
            return
        if not obj.access(caller, "get"):
            if obj.db.get_err_msg:
                self.msg(obj.db.get_err_msg)
            else:
                self.msg("You can't get that.")
            return

        # calling possible at_pre_get_from hook on location
        if hasattr(location, "at_pre_get_from") and not location.at_pre_get_from(caller, obj):
            return
        # calling at_pre_get hook method
        if not obj.at_pre_get(caller):
            return

        success = obj.move_to(caller, quiet=True, move_type="get")
        if not success:
            self.msg("This can't be picked up.")
        else:
            singular, _ = obj.get_numbered_name(1, caller)
            if location == caller.location:
                # we're picking it up from the area
                caller.location.msg_contents(f"$You() $conj(pick) up {singular}.", from_obj=caller)
            else:
                # we're getting it from somewhere else
                container_name, _ = location.get_numbered_name(1, caller)
                caller.location.msg_contents(
                    f"$You() $conj(get) {singular} from {container_name}.", from_obj=caller
                )
            # calling at_get hook method
            obj.at_get(caller)


class CmdPut(CmdDrop):
    """
    put an object into something else

    Usage:
      put <obj> in <container>

    Lets you put an object from your inventory into another
    object in the vicinity.
    """

    key = "put"
    rhs_split = ("=", " in ", " on ")

    def func(self):
        caller = self.caller
        if not self.args:
            self.msg("Put what in where?")
            return

        if not self.rhs:
            super().func()
            return

        obj = caller.search(
            self.lhs,
            location=caller,
            nofound_string=f"You aren't carrying {self.args}.",
            multimatch_string=f"You carry more than one {self.args}:",
        )
        if not obj:
            return

        container = caller.search(self.rhs)
        if not container:
            return

        # check access lock
        if not container.access(caller, "get_from"):
            # supports custom error messages on individual containers
            if container.db.put_err_msg:
                self.msg(container.db.put_err_msg)
            else:
                self.msg("You can't get things from that.")
            return

        # Call the object script's at_pre_drop() method.
        if not obj.at_pre_drop(caller):
            return

        # Call the container's possible at_pre_put_in method.
        if hasattr(container, "at_pre_put_in") and not container.at_pre_put_in(caller, obj):
            return

        success = obj.move_to(container, quiet=True, move_type="drop")
        if not success:
            self.msg("This couldn't be dropped.")
        else:
            obj_name, _ = obj.get_numbered_name(1, caller)
            container_name, _ = container.get_numbered_name(1, caller)
            caller.location.msg_contents(
                f"$You() $conj(put) {obj_name} in {container_name}.", from_obj=caller
            )
            # Call the object script's at_drop() method.
            obj.at_drop(caller)


class ContainerCmdSet(CmdSet):
    """
    Extends the basic `look` and `get` commands to support containers,
    and adds an additional `put` command.
    """

    key = "Container CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()

        self.add(CmdContainerLook)
        self.add(CmdContainerGet)
        self.add(CmdPut)
