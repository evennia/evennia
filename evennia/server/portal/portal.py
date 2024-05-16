"""
This module implements the main Evennia server process, the core of
the game engine.

This module should be started with the 'twistd' executable since it
sets up all the networking features.  (this is done automatically
by game/evennia.py).

"""

import os
import sys

import django
from twisted.logger import globalLogPublisher

django.setup()

import evennia

evennia._init(portal_mode=True)

from django.conf import settings

from evennia.utils import logger

# twistd requires us to define the variable 'application' so it knows
# what to execute from.
# The guts of the application are in the service.py file,
# which is instantiated and attached to application in evennia._init()
application = evennia.TWISTED_APPLICATION


if "--nodaemon" not in sys.argv and "test" not in sys.argv:
    # activate logging for interactive/testing mode
    logfile = logger.WeeklyLogFile(
        os.path.basename(settings.PORTAL_LOG_FILE),
        os.path.dirname(settings.PORTAL_LOG_FILE),
        day_rotation=settings.PORTAL_LOG_DAY_ROTATION,
        max_size=settings.PORTAL_LOG_MAX_SIZE,
    )
    globalLogPublisher.addObserver(logger.GetPortalLogObserver()(logfile))
