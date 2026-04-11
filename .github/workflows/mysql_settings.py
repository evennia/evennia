"""
Evennia settings file.

The available options are found in the default settings file found
here:

/home/griatch/Devel/Home/evennia/evennia/evennia/settings_default.py

Remember:

Don't copy more from the default file than you actually intend to
change; this will make sure that you don't overload upstream updates
unnecessarily.

When changing a setting requiring a file system path (like
path/to/actual/file.py), use GAME_DIR and EVENNIA_DIR to reference
your game folder and the Evennia library folders respectively. Python
paths (path.to.module) should be given relative to the game's root
folder (typeclasses.foo) whereas paths within the Evennia library
needs to be given explicitly (evennia.foo).

If you want to share your game dir, including its settings, you can
put secret game- or server-specific settings in secret_settings.py.

"""

import os

# Use the defaults from Evennia unless explicitly overridden
from evennia.settings_default import *

######################################################################
# Evennia base server config
######################################################################

# This is the name of your game. Make it catchy!
SERVERNAME = "testing_mygame"

# Testing database types

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "evennia",
        "USER": "evennia",
        "PASSWORD": "password",
        "HOST": "127.0.0.1",
        "PORT": "",  # use default port
        "OPTIONS": {
            "charset": "utf8mb3",
            # Note: MySQL server global settings (character set, collation, row format) are set
            # in setup-database action before migrations run. The init_command sets per-connection
            # variables that don't require special privileges.
            "init_command": (
                "SET collation_connection=utf8mb3_unicode_ci, "
                "sql_mode='STRICT_TRANS_TABLES', innodb_strict_mode=1"
            ),
        },
        "TEST": {
            "NAME": "evennia",
            "OPTIONS": {
                "charset": "utf8mb3",
                "init_command": (
                    "SET collation_connection=utf8mb3_unicode_ci, "
                    "sql_mode='STRICT_TRANS_TABLES', innodb_strict_mode=1"
                ),
            },
        },
    }
}


######################################################################
# Settings given in secret_settings.py override those in this file.
######################################################################
try:
    from server.conf.secret_settings import *
except ImportError:
    print("secret_settings.py file not found or failed to import.")
