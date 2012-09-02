"""
Makes it easier to import by grouping all relevant things already at this level.

You can henceforth import most things directly from src.server
Also, the initiated object manager is available as src.server.manager.

"""

from src.server.models import *
manager = ServerConfig.objects
