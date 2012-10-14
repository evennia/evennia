"""
Makes it easier to import by grouping all relevant things already at this level.

You can henceforth import most things directly from src.objects
Also, the initiated object manager is available as src.objects.manager.

"""

from src.objects.objects import *
from src.objects.models import ObjectDB

manager = ObjectDB.objects
