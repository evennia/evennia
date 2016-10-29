#
# This file defines global variables that will always be
# available in a view context without having to repeatedly
# include it. For this to work, this file is included in
# the settings file, in the TEMPLATE_CONTEXT_PROCESSORS
# tuple.
#

from django.conf import settings
from evennia.utils.utils import get_evennia_version

# Determine the site name and server version

try:
    GAME_NAME = settings.SERVERNAME.strip()
except AttributeError:
    GAME_NAME = "Evennia"
SERVER_VERSION = get_evennia_version()
try:
    GAME_SLOGAN = settings.GAME_SLOGAN.strip()
except AttributeError:
    GAME_SLOGAN = SERVER_VERSION


# Setup lists of the most relevant apps so
# the adminsite becomes more readable.

PLAYER_RELATED = ['Players']
GAME_ENTITIES = ['Objects', 'Scripts', 'Comms', 'Help']
GAME_SETUP = ['Permissions', 'Config']
CONNECTIONS = ['Irc']
WEBSITE = ['Flatpages', 'News', 'Sites']


# The main context processor function
WEBCLIENT_ENABLED = settings.WEBCLIENT_ENABLED
WEBSOCKET_CLIENT_ENABLED = settings.WEBSOCKET_CLIENT_ENABLED
WEBSOCKET_PORT = settings.WEBSOCKET_CLIENT_PORT
WEBSOCKET_URL = settings.WEBSOCKET_CLIENT_URL

def general_context(request):
    """
    Returns common Evennia-related context stuff, which
    is automatically added to context of all views.
    """
    return {
        'game_name': GAME_NAME,
        'game_slogan': GAME_SLOGAN,
        'evennia_userapps': PLAYER_RELATED,
        'evennia_entityapps': GAME_ENTITIES,
        'evennia_setupapps': GAME_SETUP,
        'evennia_connectapps': CONNECTIONS,
        'evennia_websiteapps':WEBSITE,
        "webclient_enabled" : WEBCLIENT_ENABLED,
        "websocket_enabled" : WEBSOCKET_CLIENT_ENABLED,
        "websocket_port" : WEBSOCKET_PORT,
        "websocket_url" : WEBSOCKET_URL
    }
