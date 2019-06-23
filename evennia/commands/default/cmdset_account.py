"""

This is the cmdset for Account (OOC) commands.  These are
stored on the Account object and should thus be able to handle getting
an Account object as caller rather than a Character.

Note - in order for session-rerouting (in MULTISESSION_MODE=2) to
function, all commands in this cmdset should use the self.msg()
command method rather than caller.msg().
"""

from evennia.commands.cmdset import CmdSet
from evennia.commands.default import help, comms, admin, system
from evennia.commands.default import building, account, general


class AccountCmdSet(CmdSet):
    """
    Implements the account command set.
    """

    key = "DefaultAccount"
    priority = -10

    def at_cmdset_creation(self):
        "Populates the cmdset"

        # Account-specific commands
        self.add(account.CmdOOCLook())
        self.add(account.CmdIC())
        self.add(account.CmdOOC())
        self.add(account.CmdCharCreate())
        self.add(account.CmdCharDelete())
        # self.add(account.CmdSessions())
        self.add(account.CmdWho())
        self.add(account.CmdOption())
        self.add(account.CmdQuit())
        self.add(account.CmdPassword())
        self.add(account.CmdColorTest())
        self.add(account.CmdQuell())
        self.add(account.CmdStyle())

        # nicks
        self.add(general.CmdNick())

        # testing
        self.add(building.CmdExamine())

        # Help command
        self.add(help.CmdHelp())

        # system commands
        self.add(system.CmdReload())
        self.add(system.CmdReset())
        self.add(system.CmdShutdown())
        self.add(system.CmdPy())

        # Admin commands
        self.add(admin.CmdNewPassword())

        # Comm commands
        self.add(comms.CmdAddCom())
        self.add(comms.CmdDelCom())
        self.add(comms.CmdAllCom())
        self.add(comms.CmdChannels())
        self.add(comms.CmdCdestroy())
        self.add(comms.CmdChannelCreate())
        self.add(comms.CmdClock())
        self.add(comms.CmdCBoot())
        self.add(comms.CmdCemit())
        self.add(comms.CmdCWho())
        self.add(comms.CmdCdesc())
        self.add(comms.CmdPage())
        self.add(comms.CmdIRC2Chan())
        self.add(comms.CmdIRCStatus())
        self.add(comms.CmdRSS2Chan())
        self.add(comms.CmdGrapevine2Chan())
