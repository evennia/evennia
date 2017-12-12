# To enable collaborative building in your game, add this line to your settings.py file:
#
# from evennia.contrib.collab.collab_settings import *
#
# ...After the line:
#
# from evennia.settings_default import *
#
#
# Next, in your commandset, add in all building commands in your game's default_cmdsets module.
# At the top of the file, add this import:
#
# from evennia.contrib.collab.commands import build_commands
#
# ...And then modify CharacterCmdSet's at_cmdset_creation to look something like:
#
# def at_cmdset_creation(self):
#     """
#     Populates the cmdset
#     """
#     super(CharacterCmdSet, self).at_cmdset_creation()
#     for command in build_commands:
#         self.add(command())
#
# Finally, reload the server and you will have the collaborative building commands with the default settings.

# First, we need to overwrite some base typeclasses so objects become collab-aware.
# If you have any custom typeclasses already made, you should change their parent classes
# to line up with these.
BASE_ACCOUNT_TYPECLASS = 'evennia.contrib.collab.typeclasses.CollabAccount'
BASE_OBJECT_TYPECLASS = 'evennia.contrib.collab.typeclasses.CollabObject'
BASE_CHARACTER_TYPECLASS = 'evennia.contrib.collab.typeclasses.CollabCharacter'
BASE_ROOM_TYPECLASS = 'evennia.contrib.collab.typeclasses.CollabRoom'
BASE_EXIT_TYPECLASS = 'evennia.contrib.collab.typeclasses.CollabExit'

# The default permission given to all new accounts
PERMISSION_ACCOUNT_DEFAULT = ("Builder",)

# The types of objects that can be created with the @create command.
# @create/room would create a room with the specified typeclass.
# This dictionary also holds important configuration points like what
# Types are available for creation and what limits are set on their creation.
COLLAB_TYPES = {
    'object': {'typeclass': 'evennia.contrib.collab.typeclasses.CollabObject',
               'quota': 30, 'create_lock': '_:perm(Builder)'},
    'room': {'typeclass': 'evennia.contrib.collab.typeclasses.CollabRoom',
             'quota': 30, 'create_lock': '_:perm(Builder)'},
    'exit': {'typeclass': 'evennia.contrib.collab.typeclasses.CollabExit',
             'quota': 100, 'create_lock': '_:perm(Builder)'}}

# If overriding the above in your own settings file, rerun this in there.
# It does a reverse map to look up object types by typeclass path.
COLLAB_REVERSE_TYPES = {
    value['typeclass']: key for key, value in COLLAB_TYPES.items()
}

# Used by @dig to pick from CREATE_TYPES
COLLAB_ROOM_TYPE = 'room'
# Used by @open to pick from CREATE_TYPES
COLLAB_EXIT_TYPE = 'exit'
# What to create if no type is specified.
COLLAB_DEFAULT_TYPE = 'object'
# If set false, users will be able to build as much as they please.
COLLAB_QUOTAS_ENABLED = True
# Set this to the permission level at which quotas are ignored.
COLLAB_QUOTA_BYPASS_LOCK = '_:pperm(Admin)'

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
    'devh': 'write:perm(Developer);read:perm(Developer)',
    # Wizard info. Special settings that affect the environment but
    # should not be shared with the account.
    'admh': 'write:perm(Admin);read:perm(Admin)',
    # Wizard editable info reviewable by users. Also used by commands
    # which need to ensure their data is not accidentally overwritten.
    'adm': 'write:perm(Admin);read:controls()',
    # Stuff that anyone's script can fiddle with. Not to
    # be trusted.
    'pub': 'write:all();read:all()',
    # Stuff the user sets, but is public to read. Default for @set.
    'usr': 'write:controls();read:all()',
    # Stuff the user sets, but is not public to read.
    'usrh': 'write:controls();read:controls()',
    # Default attributes, like stuff on .db. Used for compatibility
    # with non-collab aware code.
    '': 'write:perm(Admin);read:perm(Admin)'
}

# This lock, if passed, allows a user to act as if they have control over an
# object when they otherwise wouldn't.
COLLAB_OVERRIDE_PERM_LOCK = '_:pperm(Admin)'

# Make the gender map generator for the gender contrib work with custom
# configurations by the user, and read from usrattributes
GENDER_MAP_GENERATOR = 'evennia.contrib.collab.template.extensions.get_gender_map'

# Used for safely pulling data from attributes by making sure only recognized
# datatypes are pulled.
COLLAB_JSON_OBJECT_HOOK = ('evennia.contrib.collab.extensions.attrib_json_hook',)

# Used before saving/loading attributes to verify only recognized data types are being
# stored and fetched. The encoded string is not actually stored, the serialization is
# just used as a sanity check.
COLLAB_JSON_DECODER = ('evennia.contrib.collab.extensions.AttribJSONEncoder',)

COLLAB_TEMPLATE_EXTENSIONS = (
    'jinja2.ext.with_',
    'jinja2.ext.loopcontrols',
    'evennia.contrib.collab.template.extensions.PronounsExtension',
)
