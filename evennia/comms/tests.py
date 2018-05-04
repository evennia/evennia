from evennia.comms.models import ChannelDB

from evennia.utils.test_resources import EvenniaTest


class HiddenChannelTest(EvenniaTest):
    def test_hidden_channel_not_returned_by_manager(self):
        hidden_channel = ChannelDB(is_hidden=True)
        hidden_channel.save()
        channels = ChannelDB.objects.get_all_channels()

        assert hidden_channel not in channels

    def test_hidden_channel_returned_with_arg(self):
        hidden_channel = ChannelDB(is_hidden=True)
        hidden_channel.save()
        channels = ChannelDB.objects.get_all_channels(include_hidden=True)

        assert hidden_channel in channels
