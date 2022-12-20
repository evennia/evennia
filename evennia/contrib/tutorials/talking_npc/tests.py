"""
Tutorial - talking NPC tests.

"""
from evennia.commands.default.tests import BaseEvenniaCommandTest
from evennia.utils.create import create_object

from . import talking_npc


class TestTalkingNPC(BaseEvenniaCommandTest):
    def test_talkingnpc(self):
        npc = create_object(talking_npc.TalkingNPC, key="npctalker", location=self.room1)
        self.call(talking_npc.CmdTalk(), "", "(You walk up and talk to Char.)")
        npc.delete()
