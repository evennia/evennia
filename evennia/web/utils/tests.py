from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase
from mock import MagicMock, patch
from . import general_context


class TestGeneralContext(TestCase):
    maxDiff = None

    @patch("evennia.web.utils.general_context.GAME_NAME", "test_name")
    @patch("evennia.web.utils.general_context.GAME_SLOGAN", "test_game_slogan")
    @patch(
        "evennia.web.utils.general_context.WEBSOCKET_CLIENT_ENABLED",
        "websocket_client_enabled_testvalue",
    )
    @patch("evennia.web.utils.general_context.WEBCLIENT_ENABLED", "webclient_enabled_testvalue")
    @patch("evennia.web.utils.general_context.WEBSOCKET_PORT", "websocket_client_port_testvalue")
    @patch("evennia.web.utils.general_context.WEBSOCKET_URL", "websocket_client_url_testvalue")
    def test_general_context(self):
        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        request.session = {"account": None, "puppet": None}

        response = general_context.general_context(request)

        self.assertEqual(
            response,
            {
                "account": None,
                "puppet": None,
                "game_name": "test_name",
                "game_slogan": "test_game_slogan",
                "evennia_userapps": ["Accounts"],
                "evennia_entityapps": ["Objects", "Scripts", "Comms", "Help"],
                "evennia_setupapps": ["Permissions", "Config"],
                "evennia_connectapps": ["Irc"],
                "evennia_websiteapps": ["Flatpages", "News", "Sites"],
                "webclient_enabled": "webclient_enabled_testvalue",
                "websocket_enabled": "websocket_client_enabled_testvalue",
                "websocket_port": "websocket_client_port_testvalue",
                "websocket_url": "websocket_client_url_testvalue",
            },
        )

    # spec being an empty list will initially raise AttributeError in set_game_name_and_slogan to test defaults
    @patch("evennia.web.utils.general_context.settings", spec=[])
    @patch("evennia.web.utils.general_context.get_evennia_version")
    def test_set_game_name_and_slogan(self, mock_get_version, mock_settings):
        mock_get_version.return_value = "version 1"
        # test default/fallback values
        general_context.set_game_name_and_slogan()
        self.assertEqual(general_context.GAME_NAME, "Evennia")
        self.assertEqual(general_context.GAME_SLOGAN, "version 1")
        # test values when the settings are defined
        mock_settings.SERVERNAME = "test_name"
        mock_settings.GAME_SLOGAN = "test_game_slogan"
        general_context.set_game_name_and_slogan()
        self.assertEqual(general_context.GAME_NAME, "test_name")
        self.assertEqual(general_context.GAME_SLOGAN, "test_game_slogan")

    @patch("evennia.web.utils.general_context.settings")
    def test_set_webclient_settings(self, mock_settings):
        mock_settings.WEBCLIENT_ENABLED = "webclient"
        mock_settings.WEBSOCKET_CLIENT_URL = "websocket_url"
        mock_settings.WEBSOCKET_CLIENT_ENABLED = "websocket_client"
        mock_settings.WEBSOCKET_CLIENT_PORT = 5000
        general_context.set_webclient_settings()
        self.assertEqual(general_context.WEBCLIENT_ENABLED, "webclient")
        self.assertEqual(general_context.WEBSOCKET_URL, "websocket_url")
        self.assertEqual(general_context.WEBSOCKET_CLIENT_ENABLED, "websocket_client")
        self.assertEqual(general_context.WEBSOCKET_PORT, 5000)
