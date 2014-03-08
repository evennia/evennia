
######################################################################
# Evennia MU* server configuration file
#
# You may customize your setup by copy&pasting the variables you want
# to change from the master config file src/settings_default.py to
# this file. Try to *only* copy over things you really need to customize
# and do *not* make any changes to src/settings_default.py directly.
# This way you'll always have a sane default to fall back on
# (also, the master config file may change with server updates).
#
######################################################################

from src.settings_default import *

######################################################################
# Custom settings
######################################################################
MULTISESSION_MODE = 2
MAX_NR_CHARACTERS = 4
INSTALLED_APPS = INSTALLED_APPS + ('game.gamesrc.codesuite.lib.IPLog',
                                   'game.gamesrc.codesuite.lib.EVJobs',
                                   'game.gamesrc.codesuite.lib.EVInfo',
                                   'game.gamesrc.codesuite.lib.EVDesc',)

CMDSET_PLAYER = "game.gamesrc.codesuite.cmdsets.PlayerCmdSet"
CMDSET_CHARACTER = "game.gamesrc.codesuite.cmdsets.CharacterCmdSet"
CMDSET_UNLOGGEDIN = "game.gamesrc.codesuite.cmdsets.UnloggedinCmdSet"

BASE_PLAYER_TYPECLASS = "game.gamesrc.codesuite.typeclasses.MainPlayer"
BASE_CHARACTER_TYPECLASS = "game.gamesrc.codesuite.typeclasses.MainCharacter"
BASE_CHANNEL_TYPECLASS = "game.gamesrc.codesuite.typeclasses.MainChannel"



######################################################################
# SECRET_KEY was randomly seeded when settings.py was first created.
# Don't share this with anybody. It is used by Evennia to handle
# cryptographic hashing for things like cookies on the web side.
######################################################################
SECRET_KEY = 'dtG>kzn^FoA_6T|sWm)REO0KDuPi/+XbvV?2@3hw'

