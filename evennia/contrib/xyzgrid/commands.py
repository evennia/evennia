"""

XYZ-aware commands

Just add the XYZGridCmdSet to the default character cmdset to override
the commands with XYZ-aware equivalents.

"""

from django.conf import settings
from evennia import InterruptCommand
from evennia import default_cmds, CmdSet
from evennia.commands.default import building
from evennia.contrib.xyzgrid.xyzroom import XYZRoom
from evennia.contrib.xyzgrid.xyzgrid import get_xyzgrid
from evennia.utils.utils import list_to_string, class_from_module, make_iter

COMMAND_DEFAULT_CLASS = class_from_module(settings.COMMAND_DEFAULT_CLASS)


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
      tel/map Z|mapname

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
      map - show coordinate map of given Zcoord/mapname.

    Teleports an object somewhere. If no object is given, you yourself are
    teleported to the target location. If (X,Y) or (X,Y,Z) coordinates
    are given, the target is a location on the XYZGrid.

    """
    def _search_by_xyz(self, inp):
        inp = inp.strip("()")
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
            self.caller.msg(f"Found no target XYZRoom at ({X},{Y},{Z}).")
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
            if all(char in self.lhs for char in ("(", ")", ",")):
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


class CmdGoto(COMMAND_DEFAULT_CLASS):
    """
    Go to a named location in this area.

    Usage:
        goto <location>      - get path and start walking
        path <location>      - just check the path
        goto                 - abort current goto
        path                 - show current path

    This will find the shortest route to a location in your current area and
    start automatically walk you there. Builders can also specify a specific grid
    coordinate (X,Y).

    """
    key = "goto"
    aliases = "path"
    help_category = "General"
    locks = "cmd:all()"

    def _search_by_xyz(self, inp, xyz_start):
        inp = inp.strip("()")
        X, Y = inp.split(",", 2)
        Z = xyz_start[2]
        # search by coordinate
        X, Y, Z = str(X).strip(), str(Y).strip(), str(Z).strip()
        try:
            return XYZRoom.objects.get_xyz(xyz=(X, Y, Z))
        except XYZRoom.DoesNotExist:
            self.caller.msg(f"Could not find a room at ({X},{Y}) (Z={Z}).")
            return None

    def _search_by_key_and_alias(self, inp, xyz_start):
        Z = xyz_start[2]
        candidates = list(XYZRoom.objects.filter_xyz(xyz=('*', '*', Z)))
        return self.caller.search(inp, candidates=candidates)

    def func(self):
        """
        Implement command
        """

        caller = self.caller

        current_target, *current_path = make_iter(caller.ndb.xy_current_goto)
        goto_mode = self.cmdname == 'goto'

        if not self.args:
            if current_target:
                if goto_mode:
                    caller.ndb.xy_current_goto_target = None
                    caller.msg("Aborted goto.")
                else:
                    caller.msg(f"Remaining steps: {list_to_string(current_path)}")
            else:
                caller.msg("Usage: goto <location>")
            return

        xyzgrid = get_xyzgrid()
        try:
            xyz_start = caller.location.xyz
        except AttributeError:
            self.caller.msg("Cannot path-find since the current location is not on the grid.")
            return

        allow_xyz_query = caller.locks.check_lockstring(caller, "perm(Builder)")
        if allow_xyz_query and all(char in self.args for char in ("(", ")", ",")):
            # search by (X,Y)
            target = self._search_by_xyz(self.args, xyz_start)
            if not target:
                return
        else:
            # search by normal key/alias
            target = self._search_by_key_and_alias(self.args, xyz_start)
            if not target:
                return
        try:
            xyz_end = target.xyz
        except AttributeError:
            self.caller.msg("Target location is not on the grid and cannot be auto-walked to.")
            return

        xymap = xyzgrid.get_map(xyz_start[2])
        # we only need the xy coords once we have the map
        xy_start = xyz_start[:2]
        xy_end = xyz_end[:2]
        shortest_path, _ = xymap.get_shortest_path(xy_start, xy_end)

        caller.msg(f"There are {len(shortest_path)} steps to {target.get_display_name(caller)}: "
                   f"|w{list_to_string(shortest_path, endsep='|nand finally|w')}|n")

        # store for use by the return_appearance hook on the XYZRoom
        caller.ndb.xy_current_goto = (xy_end, shortest_path)

        if self.cmdname == "goto":
            # start actually walking right away
            self.msg("Walking ... eventually")
            pass


class XYZGridCmdSet(CmdSet):
    """
    Cmdset for easily adding the above cmds to the character cmdset.

    """
    key = "xyzgrid_cmdset"

    def at_cmdset_creation(self):
        self.add(CmdXYZTeleport())
        self.add(CmdXYZOpen())
        self.add(CmdGoto())
