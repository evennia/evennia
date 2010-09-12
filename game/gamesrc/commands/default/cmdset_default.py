"""
This module ties together all the commands of the default command set. 
"""
from src.commands.cmdset import CmdSet
from game.gamesrc.commands.default import general, help, privileged
from game.gamesrc.commands.default import tests, comms, objmanip
from game.gamesrc.commands.default import info, batchprocess

class DefaultCmdSet(CmdSet):
    """
    Implements the default command set.
    """
    key = "DefaultMUX"

    def at_cmdset_creation(self):
        "Populates the cmdset"

        # The general commands
        self.add(general.CmdLook())
        self.add(general.CmdPassword())
        self.add(general.CmdWall())
        self.add(general.CmdInventory())
        self.add(general.CmdQuit())
        self.add(general.CmdPose())
        self.add(general.CmdNick())
        self.add(general.CmdEmit())
        self.add(general.CmdGet())
        self.add(general.CmdDrop())
        self.add(general.CmdWho())
        self.add(general.CmdSay())
        self.add(general.CmdGroup())

        # The help system
        self.add(help.CmdHelp())
        self.add(help.CmdSetHelp())

        # Privileged commands
        self.add(privileged.CmdReload())
        self.add(privileged.CmdPy())
        self.add(privileged.CmdListScripts())
        self.add(privileged.CmdListCmdSets())
        self.add(privileged.CmdListObjects())
        self.add(privileged.CmdBoot())
        self.add(privileged.CmdDelPlayer())
        self.add(privileged.CmdNewPassword())
        self.add(privileged.CmdHome())
        self.add(privileged.CmdService())
        self.add(privileged.CmdShutdown())
        self.add(privileged.CmdPerm())

        # Info commands
        self.add(info.CmdVersion())
        self.add(info.CmdTime())
        self.add(info.CmdList())
        self.add(info.CmdPs())
        self.add(info.CmdStats())

        # Object manipulation commands
        self.add(objmanip.CmdTeleport())
        self.add(objmanip.CmdSetObjAlias())
        self.add(objmanip.CmdWipe())
        self.add(objmanip.CmdSetAttribute())        
        self.add(objmanip.CmdName())
        self.add(objmanip.CmdDesc())
        #self.add(objmanip.CmdCpAttr()) #TODO - need testing/debugging
        #self.add(objmanip.CmdMvAttr()) #TODO - need testing/debugging
        self.add(objmanip.CmdFind())
        self.add(objmanip.CmdCopy()) #TODO - need testing/debugging
        self.add(objmanip.CmdOpen())
        self.add(objmanip.CmdLink())
        self.add(objmanip.CmdUnLink())
        self.add(objmanip.CmdCreate())        
        self.add(objmanip.CmdDig())
        self.add(objmanip.CmdDestroy())
        self.add(objmanip.CmdExamine())
        self.add(objmanip.CmdTypeclass())

        # Comm commands
        self.add(comms.CmdAddCom())
        self.add(comms.CmdDelCom())
        self.add(comms.CmdComlist())
        self.add(comms.CmdClist())
        self.add(comms.CmdCdestroy())
        self.add(comms.CmdChannelCreate())
        self.add(comms.CmdCdesc())
        self.add(comms.CmdPage())
        
        # Batchprocessor commands
        self.add(batchprocess.CmdBatchCommands())
        self.add(batchprocess.CmdBatchCode())

        # Testing commands 
        self.add(tests.CmdTest())
        self.add(tests.CmdTestState())
        self.add(tests.CmdTestPerms())
        self.add(tests.TestCom())
        self.add(tests.CmdDebug())    
