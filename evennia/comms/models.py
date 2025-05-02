"""
Models for the in-game communication system.

The comm system could take the form of channels, but can also be
adopted for storing tells or in-game mail.

The comsystem's main component is the Message (Msg), which carries the
actual information between two parties.  Msgs are stored in the
database and usually not deleted.  A Msg always have one sender (a
user), but can have any number targets, both users and channels.

For non-persistent (and slightly faster) use one can also use the
TempMsg, which mimics the Msg API but without actually saving to the
database.

Channels are central objects that act as targets for Msgs. Accounts can
connect to channels by use of a ChannelConnect object (this object is
necessary to easily be able to delete connections on the fly).

"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from evennia.comms import managers
from evennia.locks.lockhandler import LockHandler
from evennia.typeclasses.models import TypedObject
from evennia.typeclasses.tags import Tag, TagHandler
from evennia.utils.idmapper.models import SharedMemoryModel
from evennia.utils.utils import crop, lazy_property, make_iter

__all__ = ("Msg", "TempMsg", "ChannelDB", "SubscriptionHandler")


_GA = object.__getattribute__
_SA = object.__setattr__
_DA = object.__delattr__


# ------------------------------------------------------------
#
# Msg
#
# ------------------------------------------------------------


class Msg(SharedMemoryModel):
    """
    A single message. This model describes all ooc messages
    sent in-game, both to channels and between accounts.

    The Msg class defines the following database fields (all
    accessed via specific handler methods):

    - db_sender_accounts: Account senders
    - db_sender_objects: Object senders
    - db_sender_scripts: Script senders
    - db_sender_external: External sender (defined as string name)
    - db_receivers_accounts: Receiving accounts
    - db_receivers_objects: Receiving objects
    - db_receivers_scripts: Receiveing scripts
    - db_receiver_external: External sender (defined as string name)
    - db_header: Header text
    - db_message: The actual message text
    - db_date_created: time message was created / sent
    - db_hide_from_sender: bool if message should be hidden from sender
    - db_hide_from_receivers: list of receiver objects to hide message from
    - db_lock_storage: Internal storage of lock strings.

    """

    #
    # Msg database model setup
    #
    #
    # These databse fields are all set using their corresponding properties,
    # named same as the field, but withtout the db_* prefix.

    db_sender_accounts = models.ManyToManyField(
        "accounts.AccountDB",
        related_name="sender_account_set",
        blank=True,
        verbose_name="Senders (Accounts)",
        db_index=True,
    )

    db_sender_objects = models.ManyToManyField(
        "objects.ObjectDB",
        related_name="sender_object_set",
        blank=True,
        verbose_name="Senders (Objects)",
        db_index=True,
    )
    db_sender_scripts = models.ManyToManyField(
        "scripts.ScriptDB",
        related_name="sender_script_set",
        blank=True,
        verbose_name="Senders (Scripts)",
        db_index=True,
    )
    db_sender_external = models.CharField(
        "external sender",
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text=(
            "Identifier for single external sender, for use with senders "
            "not represented by a regular database model."
        ),
    )

    db_receivers_accounts = models.ManyToManyField(
        "accounts.AccountDB",
        related_name="receiver_account_set",
        blank=True,
        verbose_name="Receivers (Accounts)",
        help_text="account receivers",
    )

    db_receivers_objects = models.ManyToManyField(
        "objects.ObjectDB",
        related_name="receiver_object_set",
        blank=True,
        verbose_name="Receivers (Objects)",
        help_text="object receivers",
    )
    db_receivers_scripts = models.ManyToManyField(
        "scripts.ScriptDB",
        related_name="receiver_script_set",
        blank=True,
        verbose_name="Receivers (Scripts)",
        help_text="script_receivers",
    )

    db_receiver_external = models.CharField(
        "external receiver",
        max_length=1024,
        null=True,
        blank=True,
        db_index=True,
        help_text=(
            "Identifier for single external receiver, for use with recievers "
            "not represented by a regular database model."
        ),
    )

    # header could be used for meta-info about the message if your system needs
    # it, or as a separate store for the mail subject line maybe.
    db_header = models.TextField("header", null=True, blank=True)
    # the message body itself
    db_message = models.TextField("message")
    # send date (note - this is in UTC.  Use the .date_created property to get it in local time)
    db_date_created = models.DateTimeField(
        "date sent", editable=False, auto_now_add=True, db_index=True
    )
    # lock storage
    db_lock_storage = models.TextField(
        "locks", blank=True, help_text="access locks on this message."
    )

    # these can be used to filter/hide a given message from supplied objects/accounts
    db_hide_from_accounts = models.ManyToManyField(
        "accounts.AccountDB", related_name="hide_from_accounts_set", blank=True
    )

    db_hide_from_objects = models.ManyToManyField(
        "objects.ObjectDB", related_name="hide_from_objects_set", blank=True
    )

    db_tags = models.ManyToManyField(
        Tag,
        blank=True,
        help_text=(
            "tags on this message. Tags are simple string markers to "
            "identify, group and alias messages."
        ),
    )

    # Database manager
    objects = managers.MsgManager()
    _is_deleted = False

    class Meta(object):
        "Define Django meta options"

        verbose_name = "Msg"

    @lazy_property
    def locks(self):
        return LockHandler(self)

    @lazy_property
    def tags(self):
        return TagHandler(self)

    @property
    def date_created(self):
        """Return the field in localized time based on settings.TIME_ZONE."""
        return timezone.localtime(self.db_date_created)

    # Wrapper properties to easily set database fields. These are
    # @property decorators that allows to access these fields using
    # normal python operations (without having to remember to save()
    # etc). So e.g. a property 'attr' has a get/set/del decorator
    # defined that allows the user to do self.attr = value,
    # value = self.attr and del self.attr respectively (where self
    # is the object in question).

    @property
    def senders(self):
        "Getter. Allows for value = self.senders"
        return (
            list(self.db_sender_accounts.all())
            + list(self.db_sender_objects.all())
            + list(self.db_sender_scripts.all())
            + ([self.db_sender_external] if self.db_sender_external else [])
        )

    @senders.setter
    def senders(self, senders):
        "Setter. Allows for self.sender = value"

        if isinstance(senders, str):
            self.db_sender_external = senders
            self.save(update_fields=["db_sender_external"])
            return

        for sender in make_iter(senders):
            if not sender:
                continue
            if not hasattr(sender, "__dbclass__"):
                raise ValueError("This is a not a typeclassed object!")
            clsname = sender.__dbclass__.__name__
            if clsname == "ObjectDB":
                self.db_sender_objects.add(sender)
            elif clsname == "AccountDB":
                self.db_sender_accounts.add(sender)
            elif clsname == "ScriptDB":
                self.db_sender_scripts.add(sender)

    @senders.deleter
    def senders(self):
        "Deleter. Clears all senders"
        self.db_sender_accounts.clear()
        self.db_sender_objects.clear()
        self.db_sender_scripts.clear()
        self.db_sender_external = ""
        self.save()

    def remove_sender(self, senders):
        """
        Remove a single sender or a list of senders.

        Args:
            senders (Account, Object, str or list): Senders to remove.
                If a string, removes the external sender.

        """
        if isinstance(senders, str):
            self.db_sender_external = ""
            self.save(update_fields=["db_sender_external"])
            return

        for sender in make_iter(senders):
            if not sender:
                continue
            if not hasattr(sender, "__dbclass__"):
                raise ValueError("This is a not a typeclassed object!")
            clsname = sender.__dbclass__.__name__
            if clsname == "ObjectDB":
                self.db_sender_objects.remove(sender)
            elif clsname == "AccountDB":
                self.db_sender_accounts.remove(sender)
            elif clsname == "ScriptDB":
                self.db_sender_accounts.remove(sender)

    @property
    def receivers(self):
        """
        Getter. Allows for value = self.receivers.
        Returns four lists of receivers: accounts, objects, scripts and
            external_receivers.

        """
        return (
            list(self.db_receivers_accounts.all())
            + list(self.db_receivers_objects.all())
            + list(self.db_receivers_scripts.all())
            + ([self.db_receiver_external] if self.db_receiver_external else [])
        )

    @receivers.setter
    def receivers(self, receivers):
        """
        Setter. Allows for self.receivers = value.  This appends a new receiver
        to the message. If a string, replaces an external receiver.

        """
        if isinstance(receivers, str):
            self.db_receiver_external = receivers
            self.save(update_fields=["db_receiver_external"])
            return

        for receiver in make_iter(receivers):
            if not receiver:
                continue
            if not hasattr(receiver, "__dbclass__"):
                raise ValueError("This is a not a typeclassed object!")
            clsname = receiver.__dbclass__.__name__
            if clsname == "ObjectDB":
                self.db_receivers_objects.add(receiver)
            elif clsname == "AccountDB":
                self.db_receivers_accounts.add(receiver)
            elif clsname == "ScriptDB":
                self.db_receivers_scripts.add(receiver)

    @receivers.deleter
    def receivers(self):
        "Deleter. Clears all receivers"
        self.db_receivers_accounts.clear()
        self.db_receivers_objects.clear()
        self.db_receivers_scripts.clear()
        self.db_receiver_external = ""
        self.save()

    def remove_receiver(self, receivers):
        """
        Remove a single receiver, a list of receivers, or a single extral receiver.

        Args:
            receivers (Account, Object, Script, list or str): Receiver
                to remove. A string removes the external receiver.

        """
        if isinstance(receivers, str):
            self.db_receiver_external = ""
            self.save(update_fields="db_receiver_external")
            return

        for receiver in make_iter(receivers):
            if not receiver:
                continue
            elif not hasattr(receiver, "__dbclass__"):
                raise ValueError("This is a not a typeclassed object!")
            clsname = receiver.__dbclass__.__name__
            if clsname == "ObjectDB":
                self.db_receivers_objects.remove(receiver)
            elif clsname == "AccountDB":
                self.db_receivers_accounts.remove(receiver)
            elif clsname == "ScriptDB":
                self.db_receivers_scripts.remove(receiver)

    @property
    def hide_from(self):
        """
        Getter. Allows for value = self.hide_from.
        Returns two lists of accounts and objects.

        """
        return (
            self.db_hide_from_accounts.all(),
            self.db_hide_from_objects.all(),
        )

    @hide_from.setter
    def hide_from(self, hiders):
        """
        Setter. Allows for self.hide_from = value. Will append to hiders.

        """
        for hider in make_iter(hiders):
            if not hider:
                continue
            if not hasattr(hider, "__dbclass__"):
                raise ValueError("This is a not a typeclassed object!")
            clsname = hider.__dbclass__.__name__
            if clsname == "AccountDB":
                self.db_hide_from_accounts.add(hider.__dbclass__)
            elif clsname == "ObjectDB":
                self.db_hide_from_objects.add(hider.__dbclass__)

    @hide_from.deleter
    def hide_from(self):
        """
        Deleter. Allows for del self.hide_from_senders

        """
        self.db_hide_from_accounts.clear()
        self.db_hide_from_objects.clear()
        self.save()

    #
    # Msg class methods
    #

    def __str__(self):
        """
        This handles what is shown when e.g. printing the message.

        """
        senders = ",".join(getattr(obj, "key", str(obj)) for obj in self.senders)
        receivers = ",".join(getattr(obj, "key", str(obj)) for obj in self.receivers)
        return "%s->%s: %s" % (senders, receivers, crop(self.message, width=40))

    def access(self, accessing_obj, access_type="read", default=False):
        """
        Checks lock access.

        Args:
            accessing_obj (Object or Account): The object trying to gain access.
            access_type (str, optional): The type of lock access to check.
            default (bool): Fallback to use if `access_type` lock is not defined.

        Returns:
            result (bool): If access was granted or not.

        """
        return self.locks.check(accessing_obj, access_type=access_type, default=default)


# ------------------------------------------------------------
#
# TempMsg
#
# ------------------------------------------------------------


class TempMsg:
    """
    This is a non-persistent object for sending temporary messages that will not be stored.  It
    mimics the "real" Msg object, but doesn't require sender to be given.

    """

    def __init__(
        self,
        senders=None,
        receivers=None,
        message="",
        header="",
        type="",
        lockstring="",
        hide_from=None,
    ):
        """
        Creates the temp message.

        Args:
            senders (any or list, optional): Senders of the message.
            receivers (Account, Object, Script or list, optional): Receivers of this message.
            message (str, optional): Message to send.
            header (str, optional): Header of message.
            type (str, optional): Message class, if any.
            lockstring (str, optional): Lock for the message.
            hide_from (Account, Object, or list, optional): Entities to hide this message from.

        """
        self.senders = senders and make_iter(senders) or []
        self.receivers = receivers and make_iter(receivers) or []
        self.type = type
        self.header = header
        self.message = message
        self.lock_storage = lockstring
        self.hide_from = hide_from and make_iter(hide_from) or []
        self.date_created = timezone.now()

    @lazy_property
    def locks(self):
        return LockHandler(self)

    def __str__(self):
        """
        This handles what is shown when e.g. printing the message.

        """
        senders = ",".join(obj.key for obj in self.senders)
        receivers = ",".join(obj.key for obj in self.receivers)
        return "%s->%s: %s" % (senders, receivers, crop(self.message, width=40))

    def remove_sender(self, sender):
        """
        Remove a sender or a list of senders.

        Args:
            sender (Object, Account, str or list): Senders to remove.

        """
        for o in make_iter(sender):
            try:
                self.senders.remove(o)
            except ValueError:
                pass  # nothing to remove

    def remove_receiver(self, receiver):
        """
        Remove a receiver or a list of receivers

        Args:
            receiver (Object, Account, Script, str or list): Receivers to remove.

        """

        for o in make_iter(receiver):
            try:
                self.senders.remove(o)
            except ValueError:
                pass  # nothing to remove

    def access(self, accessing_obj, access_type="read", default=False):
        """
        Checks lock access.

        Args:
            accessing_obj (Object or Account): The object trying to gain access.
            access_type (str, optional): The type of lock access to check.
            default (bool): Fallback to use if `access_type` lock is not defined.

        Returns:
            result (bool): If access was granted or not.

        """
        return self.locks.check(accessing_obj, access_type=access_type, default=default)


# ------------------------------------------------------------
#
# Channel
#
# ------------------------------------------------------------


class SubscriptionHandler:
    """
    This handler manages subscriptions to the
    channel and hides away which type of entity is
    subscribing (Account or Object)

    """

    def __init__(self, obj):
        """
        Initialize the handler

        Attr:
            obj (ChannelDB): The channel the handler sits on.

        """
        self.obj = obj
        self._cache = None

    def _recache(self):
        self._cache = {
            account: True
            for account in self.obj.db_account_subscriptions.all().order_by("pk")
            if hasattr(account, "pk") and account.pk
        }
        self._cache.update(
            {
                obj: True
                for obj in self.obj.db_object_subscriptions.all().order_by("pk")
                if hasattr(obj, "pk") and obj.pk
            }
        )

    def has(self, entity):
        """
        Check if the given entity subscribe to this channel

        Args:
            entity (str, Account or Object): The entity to return. If
                a string, it assumed to be the key or the #dbref
                of the entity.

        Returns:
            subscriber (Account, Object or None): The given
                subscriber.

        """
        if self._cache is None:
            self._recache()
        return entity in self._cache

    def add(self, entity):
        """
        Subscribe an entity to this channel.

        Args:
            entity (Account, Object or list): The entity or
                list of entities to subscribe to this channel.

        Note:
            No access-checking is done here, this must have
                been done before calling this method. Also
                no hooks will be called.

        """
        for subscriber in make_iter(entity):
            if subscriber:
                clsname = subscriber.__dbclass__.__name__
                # chooses the right type
                if clsname == "ObjectDB":
                    self.obj.db_object_subscriptions.add(subscriber)
                elif clsname == "AccountDB":
                    self.obj.db_account_subscriptions.add(subscriber)
        self._recache()

    def remove(self, entity):
        """
        Remove a subscriber from the channel.

        Args:
            entity (Account, Object or list): The entity or
                entities to un-subscribe from the channel.

        """
        for subscriber in make_iter(entity):
            if subscriber:
                clsname = subscriber.__dbclass__.__name__
                # chooses the right type
                if clsname == "AccountDB":
                    self.obj.db_account_subscriptions.remove(entity)
                elif clsname == "ObjectDB":
                    self.obj.db_object_subscriptions.remove(entity)
        self._recache()

    def all(self):
        """
        Get all subscriptions to this channel.

        Returns:
            subscribers (list): The subscribers. This
                may be a mix of Accounts and Objects!

        """
        if self._cache is None:
            self._recache()
        return self._cache

    get = all  # alias

    def online(self):
        """
        Get all online accounts from our cache
        Returns:
            subscribers (list): Subscribers who are online or
                are puppeted by an online account.
        """
        subs = []
        recache_needed = False
        for obj in self.all():
            from django.core.exceptions import ObjectDoesNotExist

            try:
                if not obj.is_connected:
                    continue
            except ObjectDoesNotExist:
                # a subscribed object has already been deleted. Mark that we need a recache and
                # ignore it
                recache_needed = True
                continue
            subs.append(obj)
        if recache_needed:
            self._recache()
        return subs

    def clear(self):
        """
        Remove all subscribers from channel.

        """
        self.obj.db_account_subscriptions.clear()
        self.obj.db_object_subscriptions.clear()
        self._cache = None


class ChannelDB(TypedObject):
    """
    This is the basis of a comm channel, only implementing
    the very basics of distributing messages.

    The Channel class defines the following database fields
    beyond the ones inherited from TypedObject:

      - db_account_subscriptions: The Account subscriptions.
      - db_object_subscriptions: The Object subscriptions.

    """

    db_account_subscriptions = models.ManyToManyField(
        "accounts.AccountDB",
        related_name="account_subscription_set",
        blank=True,
        verbose_name="account subscriptions",
        db_index=True,
    )

    db_object_subscriptions = models.ManyToManyField(
        "objects.ObjectDB",
        related_name="object_subscription_set",
        blank=True,
        verbose_name="object subscriptions",
        db_index=True,
    )

    # Database manager
    objects = managers.ChannelDBManager()

    __settingclasspath__ = settings.BASE_CHANNEL_TYPECLASS
    __defaultclasspath__ = "evennia.comms.comms.DefaultChannel"
    __applabel__ = "comms"

    class Meta:
        "Define Django meta options"

        verbose_name = "Channel"
        verbose_name_plural = "Channels"

    def __str__(self):
        "Echoes the text representation of the channel."
        return "Channel '%s' (%s)" % (self.key, self.db.desc)

    @lazy_property
    def subscriptions(self):
        return SubscriptionHandler(self)
