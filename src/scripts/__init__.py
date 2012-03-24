"""
Makes it easier to import by grouping all relevant things already at this level. 

You can henceforth import most things directly from src.scripts
Also, the initiated object manager is available as src.scripts.manager.

"""

from src.scripts.scripts import * 
from src.scripts.models import ScriptDB

manager = ScriptDB.objects
