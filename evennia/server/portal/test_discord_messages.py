"""Tests for forwarding Discord messages with optional member information."""

from unittest import TestCase, skipIf
from unittest.mock import Mock

try:
    from evennia.server.portal.discord import DiscordClient
except ModuleNotFoundError as err:
    if err.name != "OpenSSL":
        raise
    DiscordClient = None


@skipIf(DiscordClient is None, "Discord tests require the optional pyopenssl dependency.")
class TestDiscordMessages(TestCase):
    """Exercise message handling without a database or Discord connection."""

    def setUp(self):
        """Prepare a guild message and a client with a mocked Server boundary."""
        self.client = DiscordClient()
        self.client.discord_id = "100"
        self.client.sessionhandler = Mock()
        self.message = {
            "author": {"id": "200", "username": "Sender"},
            "content": "Hello from Discord!",
            "channel_id": "300",
            "guild_id": "400",
        }
        self.expected = {
            "channel_id": "300",
            "type": "channel",
            "sender": ("200", "Sender"),
            "guild_id": "400",
        }

    def test_guild_webhook_without_member(self):
        """A webhook message without member data reaches the Server."""
        self.message["webhook_id"] = "200"

        self.client.data_in({"t": "MESSAGE_CREATE", "d": self.message})

        self.client.sessionhandler.data_in.assert_called_once_with(
            self.client, bot_data_in=("Hello from Discord!", self.expected)
        )

    def test_guild_member_without_nickname(self):
        """A partial member without a nickname falls back to the username."""
        self.message["member"] = {"roles": []}

        self.client.data_in({"t": "MESSAGE_CREATE", "d": self.message})

        self.client.sessionhandler.data_in.assert_called_once_with(
            self.client, bot_data_in=("Hello from Discord!", self.expected)
        )

    def test_guild_member_with_unset_nickname(self):
        """Null and empty nicknames retain the existing username fallback."""
        for nickname in (None, ""):
            with self.subTest(nickname=nickname):
                self.client.sessionhandler.reset_mock()
                self.message["member"] = {"nick": nickname}

                self.client.data_in({"t": "MESSAGE_CREATE", "d": self.message})

                self.client.sessionhandler.data_in.assert_called_once_with(
                    self.client, bot_data_in=("Hello from Discord!", self.expected)
                )

    def test_guild_member_with_nickname(self):
        """A guild nickname still takes precedence over the username."""
        self.message["member"] = {"nick": "Guild nickname"}
        self.expected["sender"] = ("200", "Guild nickname")

        self.client.data_in({"t": "MESSAGE_CREATE", "d": self.message})

        self.client.sessionhandler.data_in.assert_called_once_with(
            self.client, bot_data_in=("Hello from Discord!", self.expected)
        )

    def test_direct_message_without_member(self):
        """Direct messages still use the username and direct-message route."""
        del self.message["guild_id"]
        del self.expected["guild_id"]
        self.expected["type"] = "direct"

        self.client.data_in({"t": "MESSAGE_CREATE", "d": self.message})

        self.client.sessionhandler.data_in.assert_called_once_with(
            self.client, bot_data_in=("Hello from Discord!", self.expected)
        )

    def test_own_message_is_ignored(self):
        """The bot's own messages remain ignored without member data."""
        self.message["author"]["id"] = self.client.discord_id

        self.client.data_in({"t": "MESSAGE_CREATE", "d": self.message})

        self.client.sessionhandler.data_in.assert_not_called()
