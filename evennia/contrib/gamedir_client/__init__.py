import warnings

from evennia.contrib.egi_client import EvenniaGameIndexService


class EvenniaGameDirService(EvenniaGameIndexService):
    """
    This is a compatibility shim to get us through the EGD to EGI rename.
    """

    def __init__(self):
        warnings.warn(
            "evennia.contrib.gamedir_client is deprecated and pending immediate "
            "removal. Please update your game's server_services_plugins.py to use "
            "evennia.contrib.egi_client.EvenniaGameIndexService instead.",
            DeprecationWarning)
        super(EvenniaGameDirService, self).__init__()
