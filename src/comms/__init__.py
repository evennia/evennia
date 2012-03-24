"""
Makes it easier to import by grouping all relevant things already at this level. 

You can henceforth import most things directly from src.comms
Also, the initiated object manager is available as src.comms.msgmanager and src.comms.channelmanager.

"""

from src.comms.models import * 

msgmanager = Msg.objects
channelmanager = Channel.objects
