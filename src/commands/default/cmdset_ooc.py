"""

This is the cmdset for OutOfCharacter (OOC) commands.  These are
stored on the Player object and should thus be able to handle getting
a Player object as caller rather than a Character.

"""
from src.commands.cmdset import CmdSet
from src.commands.default import help, comms, general, admin, system

class OOCCmdSet(CmdSet):
    """
    Implements the player command set.
    """

    key = "DefaultOOC"
    priority = -5

    def at_cmdset_creation(self):
        "Populates the cmdset"

        # General commands
        self.add(general.CmdOOCLook())
        self.add(general.CmdIC())
        self.add(general.CmdOOC())
        self.add(general.CmdEncoding())
        self.add(general.CmdQuit())
        self.add(general.CmdPassword())

        # Help command
        self.add(help.CmdHelp())

        # system commands
        self.add(system.CmdReload())
        self.add(system.CmdReset())
        self.add(system.CmdShutdown())

        # Admin commands
        self.add(admin.CmdDelPlayer())
        self.add(admin.CmdNewPassword())

        # Comm commands
        self.add(comms.CmdAddCom())
        self.add(comms.CmdDelCom())
        self.add(comms.CmdAllCom())
        self.add(comms.CmdChannels())
        self.add(comms.CmdCdestroy())
        self.add(comms.CmdChannelCreate())
        self.add(comms.CmdCset())
        self.add(comms.CmdCBoot())
        self.add(comms.CmdCemit())
        self.add(comms.CmdCWho())
        self.add(comms.CmdCdesc())
        self.add(comms.CmdPage())
        self.add(comms.CmdIRC2Chan())
        self.add(comms.CmdIMC2Chan())
        self.add(comms.CmdIMCInfo())
        self.add(comms.CmdIMCTell())
        self.add(comms.CmdRSS2Chan())
