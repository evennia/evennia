"""
Legacy Mux comms tests (extracted from 0.9.5)

"""

from evennia.commands.default.tests import BaseEvenniaCommandTest

from . import mux_comms_cmds as comms


class TestLegacyMuxComms(BaseEvenniaCommandTest):
    """
    Test the legacy comms contrib.
    """

    def setUp(self):
        super().setUp()
        self.call(
            comms.CmdChannelCreate(),
            "testchan;test=Test Channel",
            "Created channel testchan and connected to it.",
            receiver=self.account,
        )

    def test_toggle_com(self):
        self.call(
            comms.CmdAddCom(),
            "tc = testchan",
            "You are already connected to channel testchan.| You can now",
            receiver=self.account,
        )
        self.call(
            comms.CmdDelCom(),
            "tc",
            "Any alias 'tc' for channel testchan was cleared.",
            receiver=self.account,
        )

    def test_all_com(self):
        self.call(
            comms.CmdAllCom(),
            "",
            "Available channels:",
            receiver=self.account,
        )

    def test_clock(self):
        self.call(
            comms.CmdClock(),
            "testchan=send:all()",
            "Lock(s) applied. Current locks on testchan:",
            receiver=self.account,
        )

    def test_cdesc(self):
        self.call(
            comms.CmdCdesc(),
            "testchan = Test Channel",
            "Description of channel 'testchan' set to 'Test Channel'.",
            receiver=self.account,
        )

    def test_cwho(self):
        self.call(
            comms.CmdCWho(),
            "testchan",
            "Channel subscriptions\ntestchan:\n  TestAccount",
            receiver=self.account,
        )

    def test_cboot(self):
        # No one else connected to boot
        self.call(
            comms.CmdCBoot(),
            "",
            "Usage: cboot[/quiet] <channel> = <account> [:reason]",
            receiver=self.account,
        )

    def test_cdestroy(self):
        self.call(
            comms.CmdCdestroy(),
            "testchan",
            "[testchan] TestAccount: testchan is being destroyed. Make sure to change your aliases."
            "|Channel 'testchan' was destroyed.",
            receiver=self.account,
        )
