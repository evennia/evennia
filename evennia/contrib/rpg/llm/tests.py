"""
Unit tests for the LLM Client and npc.

"""

from anything import Something
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from mock import Mock, patch

from .llm_npc import LLMNPC


class TestLLMClient(EvenniaTestCase):
    @patch("evennia.contrib.rpg.llm.llm_npc.task.deferLater")
    def test_npc_at_talked_to(self, mock_deferLater):
        """
        Test the LLMNPC class.
        """
        npc = create_object(LLMNPC, key="Test NPC")
        mock_LLMClient = Mock()
        npc._llm_client = mock_LLMClient

        npc.at_talked_to("Hello", npc)

        mock_deferLater.assert_called_with(Something, npc.thinking_timeout, Something)
        mock_LLMClient.get_response.assert_called_with("Hello")
