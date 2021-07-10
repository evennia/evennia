"""

XYZ-aware commands

Just add the XYZGridCmdSet to the default character cmdset to override
the commands with XYZ-aware equivalents.

"""

from evennia import InterruptCommand
from evennia import default_cmds, CmdSet
from evennia.commands.default import building, general
from evennia.contrib.xyzgrid.xyzroom import XYZRoom
from evennia.utils.utils import inherits_from


class CmdXYZLook(general.CmdLook):

    character = '@'
    visual_range = 2
    map_mode = 'nodes'   # or 'scan'

    def func(self):
        """
        Add xymap display before the normal look command.

        """
        location = self.caller.location
        if inherits_from(location, XYZRoom):
            xyz = location.xyz
            xymap = location.xyzgrid.get_map(xyz[2])
            map_display = xymap.get_visual_range(
                (xyz[0], xyz[1]),
                dist=self.visual_range,
                mode=self.map_mode)
            maxw = min(xymap.max_x, self.client_width())
            sep = "~" * maxw
            map_display = f"|x{sep}|n\n{map_display}\n|x{sep}"
            self.msg(map_display, {"type", "xymap"}, options=None)
        # now run the normal look command
        super().func()


class CmdXYZTeleport(building.CmdTeleport):
    """
    teleport object to another location

    Usage:
      tel/switch [<object> to||=] <target location>
      tel/switch [<object> to||=] (X,Y[,Z])

    Examples:
      tel Limbo
      tel/quiet box = Limbo
      tel/tonone box
      tel (3, 3, the small cave)
      tel (4, 1)   # on the same map

    Switches:
      quiet  - don't echo leave/arrive messages to the source/target
               locations for the move.
      intoexit - if target is an exit, teleport INTO
                 the exit object instead of to its destination
      tonone - if set, teleport the object to a None-location. If this
               switch is set, <target location> is ignored.
               Note that the only way to retrieve
               an object from a None location is by direct #dbref
               reference. A puppeted object cannot be moved to None.
      loc - teleport object to the target's location instead of its contents

    Teleports an object somewhere. If no object is given, you yourself are
    teleported to the target location. If (X,Y) or (X,Y,Z) coordinates
    are given, the target is a location on the XYZGrid.

    """
    def _search_by_xyz(self, inp):
        X, Y, *Z = inp.split(",", 2)
        if Z:
            # Z was specified
            Z = Z[0]
        else:
            # use current location's Z, if it exists
            try:
                xyz = self.caller.xyz
            except AttributeError:
                self.caller.msg("Z-coordinate is also required since you are not currently "
                                "in a room with a Z coordinate of its own.")
                raise InterruptCommand
            else:
                Z = xyz[2]
        # search by coordinate
        X, Y, Z = str(X).strip(), str(Y).strip(), str(Z).strip()
        try:
            self.destination = XYZRoom.objects.get_xyz(xyz=(X, Y, Z))
        except XYZRoom.DoesNotExist:
            self.caller.msg("Found no target XYZRoom at ({X},{Y},{Y}).")
            raise InterruptCommand

    def parse(self):
        default_cmds.MuxCommand.parse(self)
        self.obj_to_teleport = self.caller
        self.destination = None

        if self.rhs:
            self.obj_to_teleport = self.caller.search(self.lhs, global_search=True)
            if not self.obj_to_teleport:
                self.caller.msg("Did not find object to teleport.")
                raise InterruptCommand
            if all(char in self.rhs for char in ("(", ")", ",")):
                # search by (X,Y) or (X,Y,Z)
                self._search_by_xyz(self.rhs)
            else:
                # fallback to regular search by name/alias
                self.destination = self.caller.search(self.rhs, global_search=True)

        elif self.lhs:
            if all(char in self.rhs for char in ("(", ")", ",")):
                self._search_by_xyz(self.lhs)
            else:
                self.destination = self.caller.search(self.lhs, global_search=True)


class CmdXYZOpen(building.CmdOpen):
    """
    open a new exit from the current room

    Usage:
      open <new exit>[;alias;..][:typeclass] [,<return exit>[;alias;..][:typeclass]]] = <destination>
      open <new exit>[;alias;..][:typeclass] [,<return exit>[;alias;..][:typeclass]]] = (X,Y,Z)

    Handles the creation of exits. If a destination is given, the exit
    will point there. The destination can also be given as an (X,Y,Z) coordinate on the
    XYZGrid - this command is used to link non-grid rooms to the grid and vice-versa.

    The <return exit> argument sets up an exit at the destination leading back to the current room.
    Apart from (X,Y,Z) coordinate, destination name can be given both as a #dbref and a name, if
    that name is globally unique.

    Examples:
        open kitchen = Kitchen
        open north, south = Town Center
        open cave mouth;cave = (3, 4, the small cave)

    """

    def parse(self):
        building.ObjManipCommand.parse(self)

        self.location = self.caller.location
        if not self.args or not self.rhs:
            self.caller.msg("Usage: open <new exit>[;alias...][:typeclass]"
                            "[,<return exit>[;alias..][:typeclass]]] "
                            "= <destination or (X,Y,Z)>")
            raise InterruptCommand
        if not self.location:
            self.caller.msg("You cannot create an exit from a None-location.")
            raise InterruptCommand

        if all(char in self.rhs for char in ("(", ")", ",")):
            # search by (X,Y) or (X,Y,Z)
            X, Y, *Z = self.rhs.split(",", 2)
            if not Z:
                self.caller.msg("A full (X,Y,Z) coordinate must be given for the destination.")
                raise InterruptCommand
            Z = Z[0]
            # search by coordinate
            X, Y, Z = str(X).strip(), str(Y).strip(), str(Z).strip()
            try:
                self.destination = XYZRoom.objects.get_xyz(xyz=(X, Y, Z))
            except XYZRoom.DoesNotExist:
                self.caller.msg("Found no target XYZRoom at ({X},{Y},{Y}).")
                raise InterruptCommand
        else:
            # regular search query
            self.destination = self.caller.search(self.rhs, global_search=True)
            if not self.destination:
                raise InterruptCommand

        self.exit_name = self.lhs_objs[0]["name"]
        self.exit_aliases = self.lhs_objs[0]["aliases"]
        self.exit_typeclass = self.lhs_objs[0]["option"]


class XYZGridCmdSet(CmdSet):
    """
    Cmdset for easily adding the above cmds to the character cmdset.

    """
    key = "xyzgrid_cmdset"

    def at_cmdset_creation(self):
        self.add(CmdXYZLook())
        self.add(CmdXYZTeleport())
        self.add(CmdXYZOpen())
