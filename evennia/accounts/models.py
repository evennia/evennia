"""
Account

The account class is an extension of the default Django user class,
and is customized for the needs of Evennia.

We use the Account to store a more mud-friendly style of permission
system as well as to allow the admin more flexibility by storing
attributes on the Account.  Within the game we should normally use the
Account manager's methods to create users so that permissions are set
correctly.

To make the Account model more flexible for your own game, it can also
persistently store attributes of its own. This is ideal for extra
account info and OOC account configuration variables etc.

"""
from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.encoding import smart_str

from evennia.accounts.manager import AccountDBManager
from evennia.typeclasses.models import TypedObject
from evennia.utils.utils import make_iter
from evennia.server.signals import SIGNAL_ACCOUNT_POST_RENAME

__all__ = ("AccountDB",)

# _ME = _("me")
# _SELF = _("self")

_MULTISESSION_MODE = settings.MULTISESSION_MODE

_GA = object.__getattribute__
_SA = object.__setattr__
_DA = object.__delattr__

_TYPECLASS = None


# ------------------------------------------------------------
#
# AccountDB
#
# ------------------------------------------------------------


class AccountDB(TypedObject, AbstractUser):
    """
    This is a special model using Django's 'profile' functionality
    and extends the default Django User model. It is defined as such
    by use of the variable AUTH_PROFILE_MODULE in the settings.
    One accesses the fields/methods. We try use this model as much
    as possible rather than User, since we can customize this to
    our liking.

    The TypedObject supplies the following (inherited) properties:

      - key - main name
      - typeclass_path - the path to the decorating typeclass
      - typeclass - auto-linked typeclass
      - date_created - time stamp of object creation
      - permissions - perm strings
      - dbref - #id of object
      - db - persistent attribute storage
      - ndb - non-persistent attribute storage

    The AccountDB adds the following properties:

      - is_connected - If any Session is currently connected to this Account
      - name - alias for user.username
      - sessions - sessions connected to this account
      - is_superuser - bool if this account is a superuser
      - is_bot - bool if this account is a bot and not a real account

    """

    #
    # AccountDB Database model setup
    #
    # inherited fields (from TypedObject):
    # db_key, db_typeclass_path, db_date_created, db_permissions

    # store a connected flag here too, not just in sessionhandler.
    # This makes it easier to track from various out-of-process locations
    db_is_connected = models.BooleanField(
        default=False,
        verbose_name="is_connected",
        help_text="If player is connected to game or not",
    )
    # database storage of persistant cmdsets.
    db_cmdset_storage = models.CharField(
        "cmdset",
        max_length=255,
        null=True,
        help_text="optional python path to a cmdset class. If creating a Character, this will default to settings.CMDSET_CHARACTER.",
    )
    # marks if this is a "virtual" bot account object
    db_is_bot = models.BooleanField(
        default=False, verbose_name="is_bot", help_text="Used to identify irc/rss bots"
    )

    # Database manager
    objects = AccountDBManager()

    # defaults
    __settingsclasspath__ = settings.BASE_SCRIPT_TYPECLASS
    __defaultclasspath__ = "evennia.accounts.accounts.DefaultAccount"
    __applabel__ = "accounts"

    class Meta(object):
        verbose_name = "Account"

    # cmdset_storage property
    # This seems very sensitive to caching, so leaving it be for now /Griatch
    # @property
    def __cmdset_storage_get(self):
        """
        Getter. Allows for value = self.name. Returns a list of cmdset_storage.
        """
        storage = self.db_cmdset_storage
        # we need to check so storage is not None
        return [path.strip() for path in storage.split(",")] if storage else []

    # @cmdset_storage.setter
    def __cmdset_storage_set(self, value):
        """
        Setter. Allows for self.name = value. Stores as a comma-separated
        string.
        """
        _SA(self, "db_cmdset_storage", ",".join(str(val).strip() for val in make_iter(value)))
        _GA(self, "save")()

    # @cmdset_storage.deleter
    def __cmdset_storage_del(self):
        "Deleter. Allows for del self.name"
        _SA(self, "db_cmdset_storage", None)
        _GA(self, "save")()

    cmdset_storage = property(__cmdset_storage_get, __cmdset_storage_set, __cmdset_storage_del)

    #
    # property/field access
    #

    def __str__(self):
        return smart_str(f"{self.name}(account {self.dbid})")

    def __repr__(self):
        return f"{self.name}(account#{self.dbid})"

    # @property
    def __username_get(self):
        return self.username

    def __username_set(self, value):
        old_name = self.username
        self.username = value
        self.save(update_fields=["username"])
        SIGNAL_ACCOUNT_POST_RENAME.send(self, old_name=old_name, new_name=value)

    def __username_del(self):
        del self.username

    # aliases
    name = property(__username_get, __username_set, __username_del)
    key = property(__username_get, __username_set, __username_del)

    # @property
    def __uid_get(self):
        "Getter. Retrieves the user id"
        return self.id

    def __uid_set(self, value):
        raise Exception("User id cannot be set!")

    def __uid_del(self):
        raise Exception("User id cannot be deleted!")

    uid = property(__uid_get, __uid_set, __uid_del)
