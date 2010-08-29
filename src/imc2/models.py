from django.db import models
from django.conf import settings
from src.comms.models import Channel

class IMC2ChannelMapping(models.Model):
    """
    Each IMC2ChannelMapping object determines which in-game channel incoming
    IMC2 messages are routed to.
    """
    channel = models.ForeignKey(Channel)
    imc2_server_name = models.CharField(max_length=78)
    imc2_channel_name = models.CharField(max_length=78)
    is_enabled = models.BooleanField(default=True)
        
    class Meta:
        verbose_name = "IMC2 Channel mapping"
        verbose_name_plural = "IMC2 Channel mappings"
        #permissions = settings.PERM_IMC2
        
    def __str__(self):
        return "%s <-> %s" % (self.channel, self.imc2_channel_name)
