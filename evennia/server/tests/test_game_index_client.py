import urllib.parse
from unittest.mock import patch

from django.test import TestCase, override_settings
from twisted.internet import defer

from evennia.server.game_index_client.client import EvenniaGameIndexClient


class _DummyResponse:
    code = 200


class _RecordingAgent:
    latest_data = None

    def __init__(self, *args, **kwargs):
        pass

    def request(self, method, url, headers=None, bodyProducer=None):
        _RecordingAgent.latest_data = bodyProducer.body.decode("utf-8")
        return defer.succeed(_DummyResponse())


@override_settings(
    GAME_INDEX_LISTING={
        "game_status": "pre-alpha",
        "game_name": "TestGame",
        "short_description": "Short",
        "long_description": "Line 1\\nLine 2",
        "listing_contact": "admin@example.com",
    }
)
class TestGameIndexClient(TestCase):
    @patch("evennia.server.game_index_client.client.AccountDB.objects.num_total_accounts", return_value=0)
    @patch("evennia.server.game_index_client.client.evennia.SESSION_HANDLER.account_count", return_value=0)
    @patch("evennia.server.game_index_client.client.Agent", _RecordingAgent)
    def test_backslash_n_in_long_description_becomes_newline(self, *_):
        client = EvenniaGameIndexClient()
        d = client._form_and_send_request()

        result = []
        d.addCallback(result.append)

        payload = urllib.parse.parse_qs(_RecordingAgent.latest_data)
        self.assertEqual(payload["long_description"][0], "Line 1\nLine 2")
        self.assertEqual(result, [(200, "OK")])
