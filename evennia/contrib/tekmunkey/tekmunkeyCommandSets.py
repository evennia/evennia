#
# To add any of these CommandSets to your game, open mygame/commands/default_cmdsets.py and add them to the appropriate commandset.
#   * For example, add tekmunkeyCharacterCmdSet to CharacterCmdSet or add tekmunkeyPlayerCmdSet to PlayerCmdSet
# The proper syntax for this is:
#   * self.add( tekmunkeyCommandSets.tekmunkeyCharacterCmdSet )
# Note that there are no parentheses when you add a COMMAND SET to another CommandSet.
#
# In this manner you include these CommandSets automatically and will never need to update your own command sets again, even though you may update your tekmunkey utilities.
#
# 
#

from evennia import CmdSet
from tekmunkey.devUtils import devUtilsCommandSets
from tekmunkey.adaptiveDisplay import adaptiveDisplayCommandSets

class tekmunkeyCharacterCmdSet(CmdSet):
    """
    The CharacterCmdSet contains general in-game commands like look,
    get etc available on in-game Character objects. It is merged with
    the PlayerCmdSet when a Player puppets a Character.
    """
    key = "tekmunkeyCharacterCmdSet"
    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        pass

class tekmunkeyPlayerCmdSet( CmdSet ):
    """
    This is the cmdset available to the Player at all times. It is
    combined with the CharacterCmdSet when the Player puppets a
    Character. It holds game-account-specific commands, channel
    commands etc.
    """
    key = "tekmunkeyPlayerCmdSet"
    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        self.add( devUtilsCommandSets.PlayerCmdSet )
        self.add( adaptiveDisplayCommandSets.PlayerCmdSet )
        pass

class tekmunkeyUnloggedinCmdSet(CmdSet):
    """
    Command set available to the Session before being logged in.  This
    holds commands like creating a new account, logging in etc.
    """
    key = "tekmunkeyUnloggedinCmdSet"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        pass

class tekmunkeySessionCmdSet(CmdSet):
    """
    This cmdset is made available on Session level once logged in. It
    is empty by default.
    """
    key = "tekmunkeySessionCmdSet"
    def at_cmdset_creation(self):
        """
        This is the only method defined in a cmdset, called during
        its creation. It should populate the set with command instances.

        As and example we just add the empty base Command object.
        It prints some info.
        """
        pass
