"""
Makes it easier to import by grouping all relevant things already at this
level.

You can henceforth import most things directly from src.scripts
Also, the initiated object manager is available as src.scripts.manager.

"""

# Note - we MUST NOT import src.scripts.scripts here, or
# proxy models will fall under Django migrations.
#from src.scripts.scripts import *
from src.scripts.models import ScriptDB

manager = ScriptDB.objects
