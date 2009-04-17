from django.db import models
from src.objects.models import CommChannel

class IMC2ChannelMapping(models.Model):
    """
    Each IMC2ChannelMapping object determines which in-game channel incoming
    IMC2 messages are routed to.
    """
    channel = models.ForeignKey(CommChannel)
    imc2_channel_name = models.CharField(max_length=78)
    is_enabled = models.BooleanField(default=True)
        
    class Meta:
        verbose_name = "IMC2 Channel mapping"
        verbose_name_plural = "IMC2 Channel mappings"
        
    def __str__(self):
        return "%s <-> %s" % (self.channel, self.imc2_channel_name)