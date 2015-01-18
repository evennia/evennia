"""
This module ties together all the commands default Character objects have
available (i.e. IC commands). Note that some commands, such as
communication-commands are instead put on the player level, in the
Player cmdset. Player commands remain available also to Characters.
"""
from evennia.commands.cmdset import CmdSet
from evennia.commands.default import general, help, admin, system
from evennia.commands.default import building
from evennia.commands.default import batchprocess


class CharacterCmdSet(CmdSet):
    """
    Implements the default command set.
    """
    key = "DefaultCharacter"
    priority = 0

    def at_cmdset_creation(self):
        "Populates the cmdset"

        # The general commands
        self.add(general.CmdLook())
        self.add(general.CmdHome())
        self.add(general.CmdInventory())
        self.add(general.CmdPose())
        self.add(general.CmdNick())
        self.add(general.CmdDesc())
        self.add(general.CmdGet())
        self.add(general.CmdDrop())
        self.add(general.CmdGive())
        self.add(general.CmdSay())
        self.add(general.CmdAccess())

        # The help system
        self.add(help.CmdHelp())
        self.add(help.CmdSetHelp())

        # System commands
        self.add(system.CmdPy())
        self.add(system.CmdScripts())
        self.add(system.CmdObjects())
        self.add(system.CmdPlayers())
        self.add(system.CmdService())
        self.add(system.CmdAbout())
        self.add(system.CmdTime())
        self.add(system.CmdServerLoad())
        #self.add(system.CmdPs())

        # Admin commands
        self.add(admin.CmdBoot())
        self.add(admin.CmdBan())
        self.add(admin.CmdUnban())
        self.add(admin.CmdEmit())
        self.add(admin.CmdPerm())
        self.add(admin.CmdWall())

        # Building and world manipulation
        self.add(building.CmdTeleport())
        self.add(building.CmdSetObjAlias())
        self.add(building.CmdListCmdSets())
        self.add(building.CmdWipe())
        self.add(building.CmdSetAttribute())
        self.add(building.CmdName())
        self.add(building.CmdDesc())
        self.add(building.CmdCpAttr())
        self.add(building.CmdMvAttr())
        self.add(building.CmdCopy())
        self.add(building.CmdFind())
        self.add(building.CmdOpen())
        self.add(building.CmdLink())
        self.add(building.CmdUnLink())
        self.add(building.CmdCreate())
        self.add(building.CmdDig())
        self.add(building.CmdTunnel())
        self.add(building.CmdDestroy())
        self.add(building.CmdExamine())
        self.add(building.CmdTypeclass())
        self.add(building.CmdLock())
        self.add(building.CmdScript())
        self.add(building.CmdSetHome())
        self.add(building.CmdTag())
        self.add(building.CmdSpawn())

        # Batchprocessor commands
        self.add(batchprocess.CmdBatchCommands())
        self.add(batchprocess.CmdBatchCode())
