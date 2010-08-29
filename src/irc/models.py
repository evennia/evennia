from django.db import models
from django.conf import settings
from src.comms.models import Channel

class IRCChannelMapping(models.Model):
    """
    Each IRCChannelMapping object determines which in-game channel incoming
    IRC messages are routed to.
    """
    channel = models.ForeignKey(Channel)
    irc_server_name = models.CharField(max_length=78)
    irc_channel_name = models.CharField(max_length=78)
    is_enabled = models.BooleanField(default=True)
        
    class Meta:
        verbose_name = "IRC Channel mapping"
        verbose_name_plural = "IRC Channel mappings"        
        #permissions = settings.PERM_IRC

    def __str__(self):
        return "%s <-> %s (%s)" % (self.channel, self.irc_channel_name,
                                   self.irc_server_name)
