"""
Add these at the end of the settings file:

from worlddata import world_settings
INSTALLED_APPS = INSTALLED_APPS + (world_settings.WORLD_DATA_APP,)

"""

import os
from django.conf import settings

# data app name
WORLD_DATA_APP = "worlddata"

# data full path
WORLD_MODEL_PATH = os.path.join(settings.GAME_DIR, WORLD_DATA_APP)

# csv files' folder under user's game directory.
CSV_DATA_FOLDER = "worlddata/csv"

# csv files' full path
CSV_DATA_PATH = os.path.join(settings.GAME_DIR, CSV_DATA_FOLDER)

# unique rooms
WORLD_ROOMS = ("world_rooms",)

# unique exits
WORLD_EXITS = ("world_exits",)

# unique objects
WORLD_OBJECTS = ("world_objects",)

# details
WORLD_DETAILS = ("world_details",)

# normal objects
PERSONAL_OBJECTS = ("personal_objects",)

WORLD_DATA = ()
WORLD_DATA += WORLD_ROOMS
WORLD_DATA += WORLD_EXITS
WORLD_DATA += WORLD_OBJECTS
WORLD_DATA += WORLD_DETAILS
WORLD_DATA += PERSONAL_OBJECTS

BASE_AUTOOBJ_TYPECLASS = "worldloader.objects.AutoObj"
