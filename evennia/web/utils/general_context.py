#
# This file defines global variables that will always be
# available in a view context without having to repeatedly
# include it. For this to work, this file is included in
# the settings file, in the TEMPLATE_CONTEXT_PROCESSORS
# tuple.
#

import os
from django.conf import settings
from evennia.utils.utils import get_evennia_version

# Determine the site name and server version
def set_game_name_and_slogan():
    """
    Sets global variables GAME_NAME and GAME_SLOGAN which are used by
    general_context.

    Notes:
        This function is used for unit testing the values of the globals.
    """
    global GAME_NAME, GAME_SLOGAN, SERVER_VERSION
    try:
        GAME_NAME = settings.SERVERNAME.strip()
    except AttributeError:
        GAME_NAME = "Evennia"
    SERVER_VERSION = get_evennia_version()
    try:
        GAME_SLOGAN = settings.GAME_SLOGAN.strip()
    except AttributeError:
        GAME_SLOGAN = SERVER_VERSION


set_game_name_and_slogan()

# Setup lists of the most relevant apps so
# the adminsite becomes more readable.

ACCOUNT_RELATED = ["Accounts"]
GAME_ENTITIES = ["Objects", "Scripts", "Comms", "Help"]
GAME_SETUP = ["Permissions", "Config"]
CONNECTIONS = ["Irc"]
WEBSITE = ["Flatpages", "News", "Sites"]


def set_webclient_settings():
    """
    As with set_game_name_and_slogan above, this sets global variables pertaining
    to webclient settings.

    Notes:
        Used for unit testing.
    """
    global WEBCLIENT_ENABLED, WEBSOCKET_CLIENT_ENABLED, WEBSOCKET_PORT, WEBSOCKET_URL
    WEBCLIENT_ENABLED = settings.WEBCLIENT_ENABLED
    WEBSOCKET_CLIENT_ENABLED = settings.WEBSOCKET_CLIENT_ENABLED
    # if we are working through a proxy or uses docker port-remapping, the webclient port encoded
    # in the webclient should be different than the one the server expects. Use the environment
    # variable WEBSOCKET_CLIENT_PROXY_PORT if this is the case.
    WEBSOCKET_PORT = int(
        os.environ.get("WEBSOCKET_CLIENT_PROXY_PORT", settings.WEBSOCKET_CLIENT_PORT)
    )
    # this is determined dynamically by the client and is less of an issue
    WEBSOCKET_URL = settings.WEBSOCKET_CLIENT_URL


set_webclient_settings()

# The main context processor function
def general_context(request):
    """
    Returns common Evennia-related context stuff, which
    is automatically added to context of all views.
    """
    account = None
    if request.user.is_authenticated:
        account = request.user

    puppet = None
    if account and request.session.get("puppet"):
        pk = int(request.session.get("puppet"))
        puppet = next((x for x in account.characters if x.pk == pk), None)

    return {
        "account": account,
        "puppet": puppet,
        "game_name": GAME_NAME,
        "game_slogan": GAME_SLOGAN,
        "evennia_userapps": ACCOUNT_RELATED,
        "evennia_entityapps": GAME_ENTITIES,
        "evennia_setupapps": GAME_SETUP,
        "evennia_connectapps": CONNECTIONS,
        "evennia_websiteapps": WEBSITE,
        "webclient_enabled": WEBCLIENT_ENABLED,
        "websocket_enabled": WEBSOCKET_CLIENT_ENABLED,
        "websocket_port": WEBSOCKET_PORT,
        "websocket_url": WEBSOCKET_URL,
    }
