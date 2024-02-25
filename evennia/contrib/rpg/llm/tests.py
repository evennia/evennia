"""
Unit tests for the LLM Client and npc.

"""

from anything import Something
from django.test import override_settings
from mock import Mock, patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import BaseEvenniaTestCase

from .llm_npc import LLMNPC


class TestLLMClient(BaseEvenniaTestCase):
    """
    Test the LLMNPC class.

    """

    def setUp(self):
        self.npc = create_object(LLMNPC, key="Test NPC")
        self.npc.db_home = None  # fix a bug in test suite
        self.npc.save()

    def tearDown(self):
        self.npc.delete()
        super().tearDown()

    @override_settings(LLM_PROMPT_PREFIX="You are a test bot.")
    @patch("evennia.contrib.rpg.llm.llm_npc.task.deferLater")
    def test_npc_at_talked_to(self, mock_deferLater):
        """
        Test the npc's at_talked_to method.
        """
        mock_LLMClient = Mock()
        self.npc.ndb.llm_client = mock_LLMClient

        self.npc.at_talked_to("Hello", self.npc)

        mock_deferLater.assert_called_with(Something, self.npc.thinking_timeout, Something)
        mock_LLMClient.get_response.assert_called_with("You are a test bot.\nTest NPC: Hello")
