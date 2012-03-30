"""
Example command set template module.

To create new commands to populate the cmdset, see
examples/command.py.

To extend the default command set:
  - copy this file up one level to gamesrc/commands and name it
    something fitting.
  - change settings.CMDSET_DEFAULT to point to the new module's
    DefaultCmdSet
  - import/add commands at the end of DefaultCmdSet's add() method.

To extend OOC cmdset:
  - like default set, but point settings.CMDSET_OOC on your new cmdset.

To extend Unloggedin cmdset:
  - like default set, but point settings.CMDSET_UNLOGGEDIN on your new cmdset.

To add a wholly new command set:
  - copy this file up one level to gamesrc/commands and name it
    something fitting.
  - add a new cmdset class
  - add it to objects e.g. with obj.cmdset.add(path.to.the.module.and.class)

"""

from ev import CmdSet, Command
from ev import default_cmds

#from contrib import menusystem, lineeditor
#from contrib import misc_commands
#from contrib import chargen

class ExampleCmdSet(CmdSet):
    """
    Implements an empty, example cmdset.
    """

    key = "ExampleSet"

    def at_cmdset_creation(self):
        """
        This is the only method defined in a cmdset, called during
        its creation. It should populate the set with command instances.

        Here we just add the empty base Command object. It prints some info.
        """
        self.add(Command())


class DefaultCmdSet(default_cmds.DefaultCmdSet):
    """
    This is an example of how to overload the default command
    set defined in src/commands/default/cmdset_default.py.

    Here we copy everything by calling the parent, but you can
    copy&paste any combination of the default command to customize
    your default set. Next you change settings.CMDSET_DEFAULT to point
    to this class.
    """
    key = "DefaultMUX"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        # calling setup in src.commands.default.cmdset_default
        super(DefaultCmdSet, self).at_cmdset_creation()

        #
        # any commands you add below will overload the default ones.
        #
        #self.add(menusystem.CmdMenuTest())
        #self.add(lineeditor.CmdEditor())
        #self.add(misc_commands.CmdQuell())

class UnloggedinCmdSet(default_cmds.UnloggedinCmdSet):
    """
    This is an example of how to overload the command set of the
    unloggedin commands, defined in
    src/commands/default/cmdset_unloggedin.py.

    Here we copy everything by calling the parent, but you can
    copy&paste any combination of the default command to customize
    your default set. Next you change settings.CMDSET_UNLOGGEDIN to
    point to this class.
    """
    key = "Unloggedin"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        # calling setup in src.commands.default.cmdset_unloggedin
        super(UnloggedinCmdSet, self).at_cmdset_creation()

        #
        # any commands you add below will overload the default ones.
        #

class OOCCmdSet(default_cmds.OOCCmdSet):
    """
    This is set is available to the player when they have no
    character connected to them (i.e. they are out-of-character, ooc).
    """
    key = "OOC"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        # calling setup in src.commands.default.cmdset_ooc
        super(OOCCmdSet, self).at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
