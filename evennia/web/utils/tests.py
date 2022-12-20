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
    @patch("evennia.web.utils.general_context.REST_API_ENABLED", True)
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
                "rest_api_enabled": True,
                "server_hostname": "localhost",
                "ssh_enabled": False,
                "ssh_ports": False,
                "telnet_enabled": True,
                "telnet_ports": [4000],
                "telnet_ssl_enabled": False,
                "telnet_ssl_ports": [4003],
            },
        )
