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

Channels are central objects that act as targets for Msgs. Players can
connect to channels by use of a ChannelConnect object (this object is
necessary to easily be able to delete connections on the fly).
"""
from builtins import object

from django.conf import settings
from django.utils import timezone
from django.db import models
from evennia.typeclasses.models import TypedObject
from evennia.typeclasses.tags import Tag, TagHandler
from evennia.utils.idmapper.models import SharedMemoryModel
from evennia.comms import managers
from evennia.locks.lockhandler import LockHandler
from evennia.utils.utils import crop, make_iter, lazy_property

__all__ = ("Msg", "TempMsg", "ChannelDB")


_GA = object.__getattribute__
_SA = object.__setattr__
_DA = object.__delattr__


#------------------------------------------------------------
#
# Msg
#
#------------------------------------------------------------

class Msg(SharedMemoryModel):
    """
    A single message. This model describes all ooc messages
    sent in-game, both to channels and between players.

    The Msg class defines the following database fields (all
    accessed via specific handler methods):

    - db_sender_players: Player senders
    - db_sender_objects: Object senders
    - db_sender_external: External senders (defined as string names)
    - db_receivers_players: Receiving players
    - db_receivers_objects: Receiving objects
    - db_receivers_channels: Receiving channels
    - db_header: Header text
    - db_message: The actual message text
    - db_date_sent: time message was sent
    - db_hide_from_sender: bool if message should be hidden from sender
    - db_hide_from_receivers: list of receiver objects to hide message from
    - db_hide_from_channels: list of channels objects to hide message from
    - db_lock_storage: Internal storage of lock strings.

    """
    #
    # Msg database model setup
    #
    #
    # These databse fields are all set using their corresponding properties,
    # named same as the field, but withtout the db_* prefix.

    # Sender is either a player, an object or an external sender, like
    # an IRC channel; normally there is only one, but if co-modification of
    # a message is allowed, there may be more than one "author"
    db_sender_players = models.ManyToManyField("players.PlayerDB", related_name='sender_player_set',
                                               null=True, verbose_name='sender(player)', db_index=True)
    db_sender_objects = models.ManyToManyField("objects.ObjectDB", related_name='sender_object_set',
                                               null=True, verbose_name='sender(object)', db_index=True)
    db_sender_external = models.CharField('external sender', max_length=255, null=True, db_index=True,
          help_text="identifier for external sender, for example a sender over an "
                    "IRC connection (i.e. someone who doesn't have an exixtence in-game).")
    # The destination objects of this message. Stored as a
    # comma-separated string of object dbrefs. Can be defined along
    # with channels below.
    db_receivers_players = models.ManyToManyField('players.PlayerDB', related_name='receiver_player_set',
                                                  null=True, help_text="player receivers")
    db_receivers_objects = models.ManyToManyField('objects.ObjectDB', related_name='receiver_object_set',
                                                  null=True, help_text="object receivers")
    db_receivers_channels = models.ManyToManyField("ChannelDB", related_name='channel_set',
                                                   null=True, help_text="channel recievers")

    # header could be used for meta-info about the message if your system needs
    # it, or as a separate store for the mail subject line maybe.
    db_header = models.TextField('header', null=True, blank=True)
    # the message body itself
    db_message = models.TextField('messsage')
    # send date
    db_date_sent = models.DateTimeField('date sent', editable=False, auto_now_add=True, db_index=True)
    # lock storage
    db_lock_storage = models.TextField('locks', blank=True,
                                       help_text='access locks on this message.')

    # these can be used to filter/hide a given message from supplied objects/players/channels
    db_hide_from_players = models.ManyToManyField("players.PlayerDB", related_name='hide_from_players_set', null=True)
    db_hide_from_objects = models.ManyToManyField("objects.ObjectDB", related_name='hide_from_objects_set', null=True)
    db_hide_from_channels = models.ManyToManyField("ChannelDB", related_name='hide_from_channels_set', null=True)

    db_tags = models.ManyToManyField(Tag, null=True,
            help_text='tags on this message. Tags are simple string markers to identify, group and alias messages.')

    # Database manager
    objects = managers.MsgManager()
    _is_deleted = False

    def __init__(self, *args, **kwargs):
        SharedMemoryModel.__init__(self, *args, **kwargs)
        self.extra_senders = []

    class Meta(object):
        "Define Django meta options"
        verbose_name = "Message"

    @lazy_property
    def locks(self):
        return LockHandler(self)

    @lazy_property
    def tags(self):
        return TagHandler(self)

    # Wrapper properties to easily set database fields. These are
    # @property decorators that allows to access these fields using
    # normal python operations (without having to remember to save()
    # etc). So e.g. a property 'attr' has a get/set/del decorator
    # defined that allows the user to do self.attr = value,
    # value = self.attr and del self.attr respectively (where self
    # is the object in question).

    # sender property (wraps db_sender_*)
    #@property
    def __senders_get(self):
        "Getter. Allows for value = self.sender"
        return  list(self.db_sender_players.all()) + \
                list(self.db_sender_objects.all()) + \
                self.extra_senders

    #@sender.setter
    def __senders_set(self, senders):
        "Setter. Allows for self.sender = value"
        for sender in make_iter(senders):
            if not sender:
                continue
            if isinstance(sender, basestring):
                self.db_sender_external = sender
                self.extra_senders.append(sender)
                self.save(update_fields=["db_sender_external"])
                continue
            if not hasattr(sender, "__dbclass__"):
                raise ValueError("This is a not a typeclassed object!")
            clsname = sender.__dbclass__.__name__
            if clsname == "ObjectDB":
                self.db_sender_objects.add(sender)
            elif clsname == "PlayerDB":
                self.db_sender_players.add(sender)

    #@sender.deleter
    def __senders_del(self):
        "Deleter. Clears all senders"
        self.db_sender_players.clear()
        self.db_sender_objects.clear()
        self.db_sender_external = ""
        self.extra_senders = []
        self.save()
    senders = property(__senders_get, __senders_set, __senders_del)

    def remove_sender(self, senders):
        """
        Remove a single sender or a list of senders.

        Args:
            senders (Player, Object, str or list): Senders to remove.

        """
        for sender in make_iter(senders):
            if not sender:
                continue
            if isinstance(sender, basestring):
                self.db_sender_external = ""
                self.save(update_fields=["db_sender_external"])
            if not hasattr(sender, "__dbclass__"):
                raise ValueError("This is a not a typeclassed object!")
            clsname = sender.__dbclass__.__name__
            if clsname == "ObjectDB":
                self.db_sender_objects.remove(sender)
            elif clsname == "PlayerDB":
                self.db_sender_players.remove(sender)

    # receivers property
    #@property
    def __receivers_get(self):
        """
        Getter. Allows for value = self.receivers.
        Returns three lists of receivers: players, objects and channels.
        """
        return list(self.db_receivers_players.all()) + list(self.db_receivers_objects.all())

    #@receivers.setter
    def __receivers_set(self, receivers):
        """
        Setter. Allows for self.receivers = value.
        This appends a new receiver to the message.
        """
        for receiver in make_iter(receivers):
            if not receiver:
                continue
            if not hasattr(receiver, "__dbclass__"):
                raise ValueError("This is a not a typeclassed object!")
            clsname = receiver.__dbclass__.__name__
            if clsname == "ObjectDB":
                self.db_receivers_objects.add(receiver)
            elif clsname == "PlayerDB":
                self.db_receivers_players.add(receiver)

    #@receivers.deleter
    def __receivers_del(self):
        "Deleter. Clears all receivers"
        self.db_receivers_players.clear()
        self.db_receivers_objects.clear()
        self.save()
    receivers = property(__receivers_get, __receivers_set, __receivers_del)

    def remove_receiver(self, receivers):
        """
        Remove a single receiver or a list of receivers.

        Args:
            receivers (Player, Object, Channel or list): Receiver to remove.

        """
        for receiver in make_iter(receivers):
            if not receiver:
                continue
            if not hasattr(receiver, "__dbclass__"):
                raise ValueError("This is a not a typeclassed object!")
            clsname = receiver.__dbclass__.__name__
            if clsname == "ObjectDB":
                self.db_receivers_objects.remove(receiver)
            elif clsname == "PlayerDB":
                self.db_receivers_players.remove(receiver)

    # channels property
    #@property
    def __channels_get(self):
        "Getter. Allows for value = self.channels. Returns a list of channels."
        return self.db_receivers_channels.all()

    #@channels.setter
    def __channels_set(self, value):
        """
        Setter. Allows for self.channels = value.
        Requires a channel to be added.
        """
        for val in (v for v in make_iter(value) if v):
            self.db_receivers_channels.add(val)

    #@channels.deleter
    def __channels_del(self):
        "Deleter. Allows for del self.channels"
        self.db_receivers_channels.clear()
        self.save()
    channels = property(__channels_get, __channels_set, __channels_del)

    def __hide_from_get(self):
        """
        Getter. Allows for value = self.hide_from.
        Returns 3 lists of players, objects and channels
        """
        return self.db_hide_from_players.all(), self.db_hide_from_objects.all(), self.db_hide_from_channels.all()

    #@hide_from_sender.setter
    def __hide_from_set(self, hiders):
        "Setter. Allows for self.hide_from = value. Will append to hiders"
        for hider in make_iter(hiders):
            if not hider:
                continue
            if not hasattr(hider, "__dbclass__"):
                raise ValueError("This is a not a typeclassed object!")
            clsname = hider.__dbclass__.__name__
            if clsname == "PlayerDB":
                self.db_hide_from_players.add(hider.__dbclass__)
            elif clsname == "ObjectDB":
                self.db_hide_from_objects.add(hider.__dbclass__)
            elif clsname == "ChannelDB":
                self.db_hide_from_channels.add(hider.__dbclass__)

    #@hide_from_sender.deleter
    def __hide_from_del(self):
        "Deleter. Allows for del self.hide_from_senders"
        self.db_hide_from_players.clear()
        self.db_hide_from_objects.clear()
        self.db_hide_from_channels.clear()
        self.save()
    hide_from = property(__hide_from_get, __hide_from_set, __hide_from_del)

    #
    # Msg class methods
    #

    def __str__(self):
        "This handles what is shown when e.g. printing the message"
        senders = ",".join(obj.key for obj in self.senders)
        receivers = ",".join(["[%s]" % obj.key for obj in self.channels] + [obj.key for obj in self.receivers])
        return "%s->%s: %s" % (senders, receivers, crop(self.message, width=40))


#------------------------------------------------------------
#
# TempMsg
#
#------------------------------------------------------------

class TempMsg(object):
    """
    This is a non-persistent object for sending temporary messages
    that will not be stored.  It mimics the "real" Msg object, but
    doesn't require sender to be given.

    """
    def __init__(self, senders=None, receivers=None, channels=None, message="", header="", type="", lockstring="", hide_from=None):
        """
        Creates the temp message.

        Args:
            senders (any or list, optional): Senders of the message.
            receivers (Player, Object, Channel or list, optional): Receivers of this message.
            channels  (Channel or list, optional): Channels to send to.
            message (str, optional): Message to send.
            header (str, optional): Header of message.
            type (str, optional): Message class, if any.
            lockstring (str, optional): Lock for the message.
            hide_from (Player, Object, Channel or list, optional): Entities to hide this message from.

        """
        self.senders = senders and make_iter(senders) or []
        self.receivers = receivers and make_iter(receivers) or []
        self.channels = channels and make_iter(channels) or []
        self.type = type
        self.header = header
        self.message = message
        self.lock_storage = lockstring
        self.hide_from = hide_from and make_iter(hide_from) or []
        self.date_sent = timezone.now()

    @lazy_property
    def locks(self):
        return LockHandler(self)

    def __str__(self):
        """
        This handles what is shown when e.g. printing the message.
        """
        senders = ",".join(obj.key for obj in self.senders)
        receivers = ",".join(["[%s]" % obj.key for obj in self.channels] + [obj.key for obj in self.receivers])
        return "%s->%s: %s" % (senders, receivers, crop(self.message, width=40))

    def remove_sender(self, sender):
        """
        Remove a sender or a list of senders.

        Args:
            sender (Object, Player, str or list): Senders to remove.

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
            receiver (Object, Player, Channel, str or list): Receivers to remove.
        """

        for o in make_iter(receiver):
            try:
                self.senders.remove(o)
            except ValueError:
                pass  # nothing to remove

    def access(self, accessing_obj, access_type='read', default=False):
        """
        Checks lock access.

        Args:
            accessing_obj (Object or Player): The object trying to gain access.
            access_type (str, optional): The type of lock access to check.
            default (bool): Fallback to use if `access_type` lock is not defined.

        Returns:
            result (bool): If access was granted or not.

        """
        return self.locks.check(accessing_obj,
                                access_type=access_type, default=default)


#------------------------------------------------------------
#
# Channel
#
#------------------------------------------------------------

class SubscriptionHandler(object):
    """
    This handler manages subscriptions to the
    channel and hides away which type of entity is
    subscribing (Player or Object)
    """
    def __init__(self, obj):
        """
        Initialize the handler

        Attr:
            obj (ChannelDB): The channel the handler sits on.

        """
        self.obj = obj

    def has(self, entity):
        """
        Check if the given entity subscribe to this channel

        Args:
            entity (str, Player or Object): The entity to return. If
                a string, it assumed to be the key or the #dbref
                of the entity.

        Returns:
            subscriber (Player, Object or None): The given
                subscriber.

        """
        clsname = entity.__dbclass__.__name__
        if clsname == "PlayerDB":
            return entity in self.obj.db_subscriptions.all()
        elif clsname == "ObjectDB":
            return entity in self.obj.db_object_subscriptions.all()


    def add(self, entity):
        """
        Subscribe an entity to this channel.

        Args:
            entity (Player, Object or list): The entity or
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
                elif clsname == "PlayerDB":
                    self.obj.db_subscriptions.add(subscriber)

    def remove(self, entity):
        """
        Remove a subecriber from the channel.

        Args:
            entity (Player, Object or list): The entity or
                entities to un-subscribe from the channel.

        """
        for subscriber in make_iter(entity):
            if subscriber:
                clsname = subscriber.__dbclass__.__name__
                # chooses the right type
                if clsname == "PlayerDB":
                    self.obj.db_subscriptions.remove(entity)
                elif clsname == "ObjectDB":
                    self.obj.db_object_subscriptions.remove(entity)

    def all(self):
        """
        Get all subscriptions to this channel.

        Returns:
            subscribers (list): The subscribers. This
                may be a mix of Players and Objects!

        """
        return list(self.obj.db_subscriptions.all()) + \
               list(self.obj.db_object_subscriptions.all())

    def clear(self):
        """
        Remove all subscribers from channel.

        """
        self.obj.db_subscriptions.clear()
        self.obj.db_object_subscriptions.clear()


class ChannelDB(TypedObject):
    """
    This is the basis of a comm channel, only implementing
    the very basics of distributing messages.

    The Channel class defines the following database fields
    beyond the ones inherited from TypedObject:

      - db_subscriptions: The Player subscriptions (this is the most
        usual case, named this way for legacy.
      - db_object_subscriptions: The Object subscriptions.

    """
    db_subscriptions = models.ManyToManyField("players.PlayerDB",
                       related_name="subscription_set", null=True, verbose_name='subscriptions', db_index=True)

    db_object_subscriptions = models.ManyToManyField("objects.ObjectDB",
                       related_name="object_subscription_set", null=True, verbose_name='subscriptions', db_index=True)

    # Database manager
    objects = managers.ChannelDBManager()

    __settingclasspath__ = settings.BASE_CHANNEL_TYPECLASS
    __defaultclasspath__ = "evennia.comms.comms.DefaultChannel"
    __applabel__ = "comms"

    class Meta(object):
        "Define Django meta options"
        verbose_name = "Channel"
        verbose_name_plural = "Channels"

    def __str__(self):
        "Echoes the text representation of the channel."
        return "Channel '%s' (%s)" % (self.key, self.db.desc)

    @lazy_property
    def subscriptions(self):
        return SubscriptionHandler(self)
