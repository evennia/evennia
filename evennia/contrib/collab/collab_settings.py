# To enable collaborative building in your game, add this line to your settings.py file:
#
# from evennia.contrib.collab.collab_settings import *
#
# ...After the line:
#
# from evennia.settings_default import *
#

# First, we need to overwrite some base typeclasses so objects become collab-aware.
# If you have any custom typeclasses already made, you should change their parent classes
# to line up with these.
BASE_PLAYER_TYPECLASS = 'evennia.contrib.collab.typeclasses.CollabPlayer'
BASE_OBJECT_TYPECLASS = 'evennia.contrib.collab.typeclasses.CollabObject'
BASE_CHARACTER_TYPECLASS = 'evennia.contrib.collab.typeclasses.CollabCharacter'
BASE_ROOM_TYPECLASS = 'evennia.contrib.collab.typeclasses.CollabRoom'
BASE_EXIT_TYPECLASS = 'evennia.contrib.collab.typeclasses.CollabExit'

# The types of objects that can be created with the @create command.
# @create/room would create a room with the specified typeclass.
# This dictionary also holds important configuration points like what
# Types are available for creation and what limits are set on their creation.
COLLAB_TYPES = {
    'object': {'typeclass': 'evennia.contrib.collab.typeclasses.CollabObject',
               'quota': 30, 'create_lock': '_:perm(builders)'},
    'room': {'typeclass': 'evennia.contrib.collab.typeclasses.CollabRoom',
             'quota': 30, 'create_lock': '_:perm(builders)'},
    'exit': {'typeclass': 'evennia.contrib.collab.typeclasses.CollabExit',
             'quota': 100, 'create_lock': '_:perm(builders)'}}

# Used by @dig to pick from CREATE_TYPES
COLLAB_ROOM_TYPE = 'room'
# Used by @open to pick from CREATE_TYPES
COLLAB_EXIT_TYPE = 'exit'
# What to create if no type is specified.
COLLAB_DEFAULT_TYPE = 'object'
# If set false, users will be able to build as much as they please.
COLLAB_QUOTAS_ENABLED = True
# Set this to the permission level at which quotas are ignored.
COLLAB_QUOTA_BYPASS_LOCK = '_:pperm(Wizards)'

# Spec out which scripts are available to who.
COLLAB_SCRIPT_TYPES = {
    # 'example': {'typeclass': 'path.to.typeclass.ClassName',
    #             'create_lock': '_:perm(builders)'},
}

# Used for global permissions masking on properties that match certain
# patterns. Useful for making certain attributes invisible or uneditable.
# Patterns are specified via regex.
COLLAB_PROPTYPE_PERMS = {
    # Server admin only info. User emails, IP addresses.
    'imh': 'write:perm(Immortals);read:perm(Immortals)',
    # Wizard info. Special settings that affect the environment but
    # should not be shared with the player.
    'wizh': 'write:perm(Wizards);read:perm(Wizards)',
    # Wizard editable info reviewable by users. Also used by commands
    # which need to ensure their data is not accidentally overwritten.
    'wiz': 'write:perm(Wizards);read:controls()',
    # Stuff that anyone's script can fiddle with. Not to
    # be trusted.
    'pub': 'write:all();read:all()',
    # Stuff the user sets, but is public to read. Default for @set.
    'usr': 'write:controls();read:all()',
    # Stuff the user sets, but is not public to read.
    'usrh': 'write:controls();read:controls()',
    # Default attributes, like stuff on .db. Used for compatibility
    # with non-collab aware code.
    '': 'write:perm(Wizards);read:perm(Wizards)'
}

# This lock, if passed, allows a user to act as if they have control over an
# object when they otherwise wouldn't.
COLLAB_OVERRIDE_PERM_LOCK = '_:pperm(wizards)'
