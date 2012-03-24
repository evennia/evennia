"""
Makes it easier to import by grouping all relevant things already at this level. 

You can henceforth import most things directly from src.help
Also, the initiated object manager is available as src.help.manager.

"""

from src.help.models import * 

manager = HelpEntry.objects
