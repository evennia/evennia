"""
Dummyrunner mixin. Add this at the end of the settings file before
running dummyrunner, like this:

    from evennia.server.profiling.settings_mixin import *

Note that these mixin-settings are not suitable for production
servers!

"""

# the dummyrunner will check this variable to make sure
# the mixin is present
DUMMYRUNNER_MIXIN = True
# a faster password hasher suitable for multiple simultaneous
# account creations. The default one is safer but deliberately
# very slow to make cracking harder.
PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)
# make dummy clients able to test all commands
PERMISSION_ACCOUNT_DEFAULT = "Developer"
# disable throttles which would otherwise block the runner
CREATION_THROTTLE_LIMIT = None
CREATION_THROTTLE_TIMEOUT = None
LOGIN_THROTTLE_LIMIT = None
LOGIN_THROTTLE_TIMEOUT = None
MAX_COMMAND_RATE = 100000
MAX_CONNECTION_RATE = 100000
MAX_CHAR_LIMIT = 100000

print(
    """
    Dummyrunner settings_mixin added (ONLY FOR PROFILING, NOT FOR PRODUCTION!)

    PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)
    PERMISSION_ACCOUNT_DEFAULT = "Developer"
    CREATION_THROTTLE_LIMIT = None
    CREATION_THROTTLE_TIMEOUT = None
    LOGIN_THROTTLE_LIMIT = None
    LOGIN_THROTTLE_TIMEOUT = None
    MAX_COMMAND_RATE = 100000
    MAX_CONNECTION_RATE = 100000
    MAX_CHAR_LIMIT = 100000
"""
)
