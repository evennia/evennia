"""

XYZ-aware commands

Just add the XYZGridCmdSet to the default character cmdset to override
the commands with XYZ-aware equivalents.

"""

from collections import namedtuple

from django.conf import settings

from evennia import CmdSet, InterruptCommand, default_cmds
from evennia.commands.default import building
from evennia.contrib.grid.xyzgrid.xyzgrid import get_xyzgrid
from evennia.contrib.grid.xyzgrid.xyzroom import XYZRoom
from evennia.utils import ansi
from evennia.utils.utils import class_from_module, delay, list_to_string

COMMAND_DEFAULT_CLASS = class_from_module(settings.COMMAND_DEFAULT_CLASS)


# temporary store of goto/path data when using the auto-stepper
PathData = namedtuple("PathData", ("target", "xymap", "directions", "step_sequence", "task"))


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
                self.caller.msg(
                    "Z-coordinate is also required since you are not currently "
                    "in a room with a Z coordinate of its own."
                )
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
            self.caller.msg(
                "Usage: open <new exit>[;alias...][:typeclass]"
                "[,<return exit>[;alias..][:typeclass]]] "
                "= <destination or (X,Y,Z)>"
            )
            raise InterruptCommand
        if not self.location:
            self.caller.msg("You cannot create an exit from a None-location.")
            raise InterruptCommand

        if all(char in self.rhs for char in ("(", ")", ",")):
            # search by (X,Y) or (X,Y,Z)
            inp = self.rhs.strip("()")
            X, Y, *Z = inp.split(",", 2)
            if not Z:
                self.caller.msg("A full (X,Y,Z) coordinate must be given for the destination.")
                raise InterruptCommand
            Z = Z[0]
            # search by coordinate
            X, Y, Z = str(X).strip(), str(Y).strip(), str(Z).strip()
            try:
                self.destination = XYZRoom.objects.get_xyz(xyz=(X, Y, Z))
            except XYZRoom.DoesNotExist:
                self.caller.msg(f"Found no target XYZRoom at ({X},{Y},{Z}).")
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
    Go to a named location in this area via the shortest path.

    Usage:
        path <location>      - find shortest path to target location (don't move)
        goto <location>      - auto-move to target location, using shortest path
        path                 - show current target location and shortest path
        goto                 - abort current goto, otherwise show current path
        path clear           - clear current path

    Finds the shortest route to a location in your current area and
    can then automatically walk you there.

    Builders can optionally specify a specific grid coordinate (X,Y) to go to.

    """

    key = "goto"
    aliases = "path"
    help_category = "General"
    locks = "cmd:all()"

    # how quickly to step (seconds)
    auto_step_delay = 2
    default_xyz_path_interrupt_msg = "Pathfinding interrupted here."

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
        candidates = list(XYZRoom.objects.filter_xyz(xyz=("*", "*", Z)))
        return self.caller.search(inp, candidates=candidates)

    def _auto_step(
        self,
        caller,
        session,
        target=None,
        xymap=None,
        directions=None,
        step_sequence=None,
        step=True,
    ):

        path_data = caller.ndb.xy_path_data

        if target:
            # start/replace an old path if we provide the data for it
            if path_data and path_data.task and path_data.task.active():
                # stop any old task in its tracks
                path_data.task.cancel()
            path_data = caller.ndb.xy_path_data = PathData(
                target=target,
                xymap=xymap,
                directions=directions,
                step_sequence=step_sequence,
                task=None,
            )

        if step and path_data:

            step_sequence = path_data.step_sequence

            try:
                direction = path_data.directions.pop(0)
                current_node = path_data.step_sequence.pop(0)
                first_link = path_data.step_sequence.pop(0)
            except IndexError:
                caller.msg("Target reached.", session=session)
                caller.ndb.xy_path_data = None
                return

            # verfy our current location against the expected location
            expected_xyz = (current_node.X, current_node.Y, current_node.Z)
            location = caller.location
            try:
                xyz_start = location.xyz
            except AttributeError:
                caller.ndb.xy_path_data = None
                caller.msg("Goto aborted - outside of area.", session=session)
                return

            if xyz_start != expected_xyz:
                # we are not where we expected to be (maybe the user moved
                # manually)  - we must recalculate the path to target
                caller.msg("Path changed - recalculating ('goto' to abort)", session=session)

                try:
                    xyz_end = path_data.target.xyz
                except AttributeError:
                    caller.ndb.xy_path_data = None
                    caller.msg("Goto aborted - target outside of area.", session=session)
                    return

                if xyz_start[2] != xyz_end[2]:
                    # can't go to another map
                    caller.ndb.xy_path_data = None
                    caller.msg("Goto aborted - target outside of area.", session=session)
                    return

                # recalculate path
                xy_start = xyz_start[:2]
                xy_end = xyz_end[:2]
                directions, step_sequence = path_data.xymap.get_shortest_path(xy_start, xy_end)

                # try again with this path, rebuilding the data
                try:
                    direction = directions.pop(0)
                    current_node = step_sequence.pop(0)
                    first_link = step_sequence.pop(0)
                except IndexError:
                    caller.msg("Target reached.", session=session)
                    caller.ndb.xy_path_data = None
                    return

                path_data = caller.ndb.xy_path_data = PathData(
                    target=path_data.target,
                    xymap=path_data.xymap,
                    directions=directions,
                    step_sequence=step_sequence,
                    task=None,
                )
            # the map can itself tell the stepper to stop the auto-step prematurely
            interrupt_node_or_link = None

            # pop any extra links up until the next node - these are
            # not useful when dealing with exits
            while step_sequence:
                if not interrupt_node_or_link and step_sequence[0].interrupt_path:
                    interrupt_node_or_link = step_sequence[0]
                if hasattr(step_sequence[0], "node_index"):
                    break
                step_sequence.pop(0)

            # the exit name does not need to be the same as the cardinal direction!
            exit_name, *_ = first_link.spawn_aliases.get(
                direction, current_node.direction_spawn_defaults.get(direction, ("unknown",))
            )

            exit_obj = caller.search(exit_name)
            if not exit_obj:
                # extra safety measure to avoid trying to walk over and over
                # if there's something wrong with the exit's name
                caller.msg(f"No exit '{exit_name}' found at current location. Aborting goto.")
                caller.ndb.xy_path_data = None
                return

            if interrupt_node_or_link:
                # premature stop of pathfind-step because of map node/link of interrupt type
                if hasattr(interrupt_node_or_link, "node_index"):
                    message = exit_obj.destination.attributes.get(
                        "xyz_path_interrupt_msg", default=self.default_xyz_path_interrupt_msg
                    )
                    # we move into the node/room and then stop
                    caller.execute_cmd(exit_name, session=session)
                else:
                    # if the link is interrupted we don't cross it at all
                    message = exit_obj.attributes.get(
                        "xyz_path_interrupt_msg", default=self.default_xyz_path_interrupt_msg
                    )
                caller.msg(message)
                return

            # do the actual move - we use the command to allow for more obvious overrides
            caller.execute_cmd(exit_name, session=session)

            # namedtuples are unmutables, so we recreate and store
            # with the new task
            caller.ndb.xy_path_data = PathData(
                target=path_data.target,
                xymap=path_data.xymap,
                directions=path_data.directions,
                step_sequence=path_data.step_sequence,
                task=delay(self.auto_step_delay, self._auto_step, caller, session),
            )

    def func(self):
        """
        Implement command
        """

        caller = self.caller
        goto_mode = self.cmdname == "goto"

        # check if we have an existing path
        path_data = caller.ndb.xy_path_data

        if not self.args:
            if path_data:
                target_name = path_data.target.get_display_name(caller)
                task = path_data.task
                if goto_mode:
                    if task and task.active():
                        task.cancel()
                        caller.msg(f"Aborted auto-walking to {target_name}.")
                        return
                # goto/path-command will show current path
                current_path = list_to_string([f"|w{step}|n" for step in path_data.directions])
                moving = "(moving)" if task and task.active() else ""
                caller.msg(f"Path to {target_name}{moving}: {current_path}")
            else:
                caller.msg("Usage: goto|path [<location>]")
            return

        if not goto_mode and self.args == "clear" and path_data:
            # in case there is a target location 'clear', this is only
            # used if path data already exists.
            caller.ndb.xy_path_data = None
            caller.msg("Cleared goto-path.")
            return

        # find target
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
        directions, step_sequence = xymap.get_shortest_path(xy_start, xy_end)

        caller.msg(
            f"There are {len(directions)} steps to {target.get_display_name(caller)}: "
            f"|w{list_to_string(directions, endsep='|n, and finally|w')}|n"
        )

        # create data for display and start stepping if we used goto
        self._auto_step(
            caller,
            self.session,
            target=target,
            xymap=xymap,
            directions=directions,
            step_sequence=step_sequence,
            step=goto_mode,
        )


class CmdMap(COMMAND_DEFAULT_CLASS):
    """
    Show a map of an area

    Usage:
        map [Zcoord]
        map list

    This is a builder-command.

    """

    key = "map"
    locks = "cmd:perm(Builders)"

    def func(self):
        """Implement command"""

        xyzgrid = get_xyzgrid()
        Z = None

        if not self.args:
            # show current area's map
            location = self.caller.location
            try:
                xyz = location.xyz
            except AttributeError:
                self.caller.msg("Your current location is not on the grid.")
                return
            Z = xyz[2]

        elif self.args.strip().lower() == "list":
            xymaps = "\n ".join(str(repr(xymap)) for xymap in xyzgrid.all_maps())
            self.caller.msg(f"Maps (Z coords) on the grid:\n |w{xymaps}")
            return

        else:
            Z = self.args

        xymap = xyzgrid.get_map(Z)
        if not xymap:
            self.caller.msg(
                f"XYMap '{Z}' is not found on the grid. Try 'map list' to see "
                "available maps/Zcoords."
            )
            return

        self.caller.msg(ansi.raw(xymap.mapstring))


class XYZGridCmdSet(CmdSet):
    """
    Cmdset for easily adding the above cmds to the character cmdset.

    """

    key = "xyzgrid_cmdset"

    def at_cmdset_creation(self):
        self.add(CmdXYZTeleport())
        self.add(CmdXYZOpen())
        self.add(CmdGoto())
        self.add(CmdMap())
