"""
Makes it easier to import by grouping all relevant things already at this level. 

You can henceforth import most things directly from src.player
Also, the initiated object manager is available as src.players.manager.

"""

from src.players.player import * 
from src.players.models import PlayerDB

manager = PlayerDB.objects
