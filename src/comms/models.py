"""
Models for the comsystem. The Commsystem is intended to be
used by Players (thematic IC communication is probably
best handled by custom commands instead).

The comm system could take the form of channels, but can also
be adopted for storing tells or in-game mail.

The comsystem's main component is the Message (Msg), which
carries the actual information between two parties.
Msgs are stored in the database and usually not
deleted.
A Msg always have one sender (a user), but can have
any number targets, both users and channels.

Channels are central objects that act as targets for
Msgs. Players can connect to channels by use of a
ChannelConnect object (this object is necessary to easily
be able to delete connections on the fly).
"""

from datetime import datetime
from django.db import models
from src.utils.idmapper.models import SharedMemoryModel
from src.comms import managers
from src.comms.managers import identify_object
from src.locks.lockhandler import LockHandler
from src.utils import logger
from src.utils.utils import is_iter, to_str, crop, make_iter

__all__ = ("Msg", "TempMsg", "Channel", "PlayerChannelConnection", "ExternalChannelConnection")

#------------------------------------------------------------
#
# Msg
#
#------------------------------------------------------------

class Msg(SharedMemoryModel):
    """
    A single message. This model describes all ooc messages
    sent in-game, both to channels and between players.

    The Msg class defines the following properties:
      sender - sender of message
      receivers - list of target objects for message
      channels - list of channels message was sent to
      message - the text being sent
      date_sent - time message was sent
      hide_from_sender - bool if message should be hidden from sender
      hide_from_receivers - list of receiver objects to hide message from
      hide_from_channels - list of channels objects to hide message from
      permissions - perm strings

    """
    #
    # Msg database model setup
    #
    #
    # These databse fields are all set using their corresponding properties,
    # named same as the field, but withtout the db_* prefix.

    # Sender is either a player, an object or an external sender, like an IRC channel
    # normally there is only one, but if co-modification of a message is allowed, there
    # may be more than one "author"
    db_sender_players = models.ManyToManyField("players.PlayerDB", related_name='sender_player_set', null=True, verbose_name='sender(player)', db_index=True)
    db_sender_objects = models.ManyToManyField("objects.ObjectDB", related_name='sender_object_set', null=True, verbose_name='sender(object)', db_index=True)
    db_sender_external = models.CharField('external sender', max_length=255, null=True, db_index=True,
          help_text="identifier for external sender, for example a sender over an IRC connection (i.e. someone who doesn't have an exixtence in-game).")
    # The destination objects of this message. Stored as a
    # comma-separated string of object dbrefs. Can be defined along
    # with channels below.
    db_receivers_players = models.ManyToManyField('players.PlayerDB', related_name='receiver_player_set', null=True, help_text="player receivers")
    db_receivers_objects = models.ManyToManyField('objects.ObjectDB', related_name='receiver_object_set', null=True, help_text="object receivers")
    db_receivers_channels = models.ManyToManyField("Channel", related_name='channel_set', null=True, help_text="channel recievers")

    # header could be used for meta-info about the message if your system needs it, or as a separate
    # store for the mail subject line maybe.
    db_header = models.CharField('header', max_length=128, null=True, blank=True, db_index=True)
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
    db_hide_from_channles = models.ManyToManyField("Channel", related_name='hide_from_channels_set', null=True)

    # Database manager
    objects = managers.MsgManager()

    def __init__(self, *args, **kwargs):
        SharedMemoryModel.__init__(self, *args, **kwargs)
        self.locks = LockHandler(self)

    class Meta:
        "Define Django meta options"
        verbose_name = "Message"

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
        return [hasattr(o, "typeclass") and o.typeclass or o for o in
                list(self.db_sender_players.all()) + list(self.db_sender_objects.all())]
    #@sender.setter
    def __senders_set(self, value):
        "Setter. Allows for self.sender = value"
        for val in (v for v in make_iter(value) if v):
            obj, typ = identify_object(val)
            if typ == 'player':
                self.db_sender_players.add(obj)
            elif typ == 'object':
                self.db_sender_objects.add(obj)
            elif isinstance(typ, basestring):
                self.db_sender_external = obj
            elif not obj:
                return
            else:
                raise ValueError(obj)
            self.save()
    #@sender.deleter
    def __senders_del(self):
        "Deleter. Clears all senders"
        self.db_sender_players.clear()
        self.db_sender_objects.clear()
        self.db_sender_external = ""
        self.save()
    senders = property(__senders_get, __senders_set, __senders_del)

    def remove_sender(self, value):
        "Remove a single sender or a list of senders"
        for val in make_iter(value):
            obj, typ = identify_object(val)
            if typ == 'player':
                self.db_sender_players.remove(obj)
            elif typ == 'object':
                self.db_sender_objects.remove(obj)
            elif isinstance(obj, basestring) and self.db_sender_external == obj:
                self.db_sender_external = ""
            else:
                raise ValueError(obj)
            self.save()

    # receivers property
    #@property
    def __receivers_get(self):
        "Getter. Allows for value = self.receivers. Returns three lists of receivers: players, objects and channels."
        return [hasattr(o, "typeclass") and o.typeclass or o for o in
                list(self.db_receivers_players.all()) + list(self.db_receivers_objects.all())]
    #@receivers.setter
    def __receivers_set(self, value):
        "Setter. Allows for self.receivers = value. This appends a new receiver to the message."
        for val in (v for v in make_iter(value) if v):
            obj, typ = identify_object(val)
            if typ == 'player':
                self.db_receivers_players.add(obj)
            elif typ == 'object':
                self.db_receivers_objects.add(obj)
            elif not obj:
                return
            else:
                raise ValueError
            self.save()
    #@receivers.deleter
    def __receivers_del(self):
        "Deleter. Clears all receivers"
        self.db_receivers_players.clear()
        self.db_receivers_objects.clear()
        self.save()
    receivers = property(__receivers_get, __receivers_set, __receivers_del)

    def remove_receiver(self, obj):
        "Remove a single recevier"
        obj, typ = identify_object(obj)
        if typ == 'player':
            self.db_receivers_players.remove(obj)
        elif typ == 'object':
            self.db_receivers_objects.remove(obj)
        else:
            raise ValueError
        self.save()

    # channels property
    #@property
    def __channels_get(self):
        "Getter. Allows for value = self.channels. Returns a list of channels."
        return self.db_receivers_channels.all()
    #@channels.setter
    def __channels_set(self, value):
        "Setter. Allows for self.channels = value. Requires a channel to be added."
        for val in (v for v in make_iter(value) if v):
            self.db_receivers_channels.add(val)
    #@channels.deleter
    def __channels_del(self):
        "Deleter. Allows for del self.channels"
        self.db_receivers_channels.clear()
        self.save()
    channels = property(__channels_get, __channels_set, __channels_del)

    # header property (wraps db_header)
    #@property
    def __header_get(self):
        "Getter. Allows for value = self.message"
        return self.db_header
    #@message.setter
    def __header_set(self, value):
        "Setter. Allows for self.message = value"
        if value:
            self.db_header = value
            self.save()
    #@message.deleter
    def __header_del(self):
        "Deleter. Allows for del self.message"
        self.db_header = ""
        self.save()
    header = property(__header_get, __header_set, __header_del)

    # message property (wraps db_message)
    #@property
    def __message_get(self):
        "Getter. Allows for value = self.message"
        return self.db_message
    #@message.setter
    def __message_set(self, value):
        "Setter. Allows for self.message = value"
        self.db_message = value
        self.save()
    #@message.deleter
    def __message_del(self):
        "Deleter. Allows for del self.message"
        self.db_message = ""
        self.save()
    message = property(__message_get, __message_set, __message_del)

    # date_sent property (wraps db_date_sent)
    #@property
    def __date_sent_get(self):
        "Getter. Allows for value = self.date_sent"
        return self.db_date_sent
    #@date_sent.setter
    def __date_sent_set(self, value):
        "Setter. Allows for self.date_sent = value"
        raise Exception("You cannot edit date_sent!")
    #@date_sent.deleter
    def __date_sent_del(self):
        "Deleter. Allows for del self.date_sent"
        raise Exception("You cannot delete the date_sent property!")
    date_sent = property(__date_sent_get, __date_sent_set, __date_sent_del)

    # hide_from property
    #@property
    def __hide_from_get(self):
        "Getter. Allows for value = self.hide_from. Returns 3 lists of players, objects and channels"
        return self.db_hide_from_players.all(), self.db_hide_from_objects.all(), self.db_hide_from_channels.all()
    #@hide_from_sender.setter
    def __hide_from_set(self, value):
        "Setter. Allows for self.hide_from = value. Will append to hiders"
        obj, typ = identify_object(value)
        if typ == "player":
            self.db_hide_from_players.add(obj)
        elif typ == "object":
            self.db_hide_from_objects.add(obj)
        elif typ == "channel":
            self.db_hide_from_channels.add(obj)
        else:
            raise ValueError
        self.save()
    #@hide_from_sender.deleter
    def __hide_from_del(self):
        "Deleter. Allows for del self.hide_from_senders"
        self.db_hide_from_players.clear()
        self.db_hide_from_objects.clear()
        self.db_hide_from_channels.clear()
        self.save()
    hide_from = property(__hide_from_get, __hide_from_set, __hide_from_del)

    # lock_storage property (wraps db_lock_storage)
    #@property
    def __lock_storage_get(self):
        "Getter. Allows for value = self.lock_storage"
        return self.db_lock_storage
    #@nick.setter
    def __lock_storage_set(self, value):
        """Saves the lock_storagetodate. This is usually not called directly, but through self.lock()"""
        self.db_lock_storage = value
        self.save()
    #@nick.deleter
    def __lock_storage_del(self):
        "Deleter is disabled. Use the lockhandler.delete (self.lock.delete) instead"""
        logger.log_errmsg("Lock_Storage (on %s) cannot be deleted. Use obj.lock.delete() instead." % self)
    lock_storage = property(__lock_storage_get, __lock_storage_set, __lock_storage_del)

    _db_model_name = "msg" # used by attributes to safely store objects

    #
    # Msg class methods
    #

    def __str__(self):
        "This handles what is shown when e.g. printing the message"
        senders = ",".join(obj.key for obj in self.senders)
        receivers = ",".join(["[%s]" % obj.key for obj in self.channels] + [obj.key for obj in self.receivers])
        return "%s->%s: %s" % (senders, receivers, crop(self.message, width=40))

    def access(self, accessing_obj, access_type='read', default=False):
        """
        Determines if another object has permission to access.
        accessing_obj - object trying to access this one
        access_type - type of access sought
        default - what to return if no lock of access_type was found
        """
        return self.locks.check(accessing_obj, access_type=access_type, default=default)


#------------------------------------------------------------
#
# TempMsg
#
#------------------------------------------------------------

class TempMsg(object):
    """
    This is a non-persistent object for sending
    temporary messages that will not be stored.
    It mimics the "real" Msg object, but don't require
    sender to be given.

    """
    def __init__(self, senders=None, receivers=None, channels=None, message="", header="", type="", lockstring="", hide_from=None):
        self.senders = senders and make_iter(senders) or []
        self.receivers = receivers and make_iter(receivers) or []
        self.channels = channels and make_iter(channels) or []
        self.type = type
        self.header = header
        self.message = message
        self.lock_storage = lockstring
        self.locks = LockHandler(self)
        self.hide_from = hide_from and make_iter(hide_from) or []
        self.date_sent = datetime.now()

    def __str__(self):
        "This handles what is shown when e.g. printing the message"
        senders = ",".join(obj.key for obj in self.senders)
        receivers = ",".join(["[%s]" % obj.key for obj in self.channels] + [obj.key for obj in self.receivers])
        return "%s->%s: %s" % (senders, receivers, crop(self.message, width=40))

    def remove_sender(self, obj):
        "Remove a sender or a list of senders"
        for o in make_iter(obj):
            try:
                self.senders.remove(o)
            except ValueError:
                pass # nothing to remove

    def remove_receiver(self, obj):
        "Remove a sender or a list of senders"
        for o in make_iter(obj):
            try:
                self.senders.remove(o)
            except ValueError:
                pass # nothing to remove

    def access(self, accessing_obj, access_type='read', default=False):
        "checks lock access"
        return self.locks.check(accessing_obj, access_type=access_type, default=default)


#------------------------------------------------------------
#
# Channel
#
#------------------------------------------------------------

class Channel(SharedMemoryModel):
    """
    This is the basis of a comm channel, only implementing
    the very basics of distributing messages.

    The Channel class defines the following properties:
      key - main name for channel
      desc - optional description of channel
      aliases - alternative names for the channel
      keep_log - bool if the channel should remember messages
      permissions - perm strings

    """

    #
    # Channel database model setup
    #
    #
    # These databse fields are all set using their corresponding properties,
    # named same as the field, but withtout the db_* prefix.

    # unique identifier for this channel
    db_key = models.CharField('key', max_length=255, unique=True, db_index=True)
    # optional description of channel
    db_desc = models.CharField('description', max_length=80, blank=True, null=True)
    # aliases for the channel. These are searched by cmdhandler
    # as well to determine if a command is the name of a channel.
    # Several aliases are separated by commas.
    db_aliases = models.CharField('aliases', max_length=255)
    # Whether this channel should remember its past messages
    db_keep_log = models.BooleanField(default=True)
    # Storage of lock definitions
    db_lock_storage = models.TextField('locks', blank=True)


    # Database manager
    objects = managers.ChannelManager()

    class Meta:
        "Define Django meta options"
        verbose_name = "Channel"

    def __init__(self, *args, **kwargs):
        SharedMemoryModel.__init__(self, *args, **kwargs)
        self.locks = LockHandler(self)

    # Wrapper properties to easily set database fields. These are
    # @property decorators that allows to access these fields using
    # normal python operations (without having to remember to save()
    # etc). So e.g. a property 'attr' has a get/set/del decorator
    # defined that allows the user to do self.attr = value,
    # value = self.attr and del self.attr respectively (where self
    # is the object in question).

    # key property (wraps db_key)
    #@property
    def key_get(self):
        "Getter. Allows for value = self.key"
        return self.db_key
    #@key.setter
    def key_set(self, value):
        "Setter. Allows for self.key = value"
        self.db_key = value
        self.save()
    #@key.deleter
    def key_del(self):
        "Deleter. Allows for del self.key"
        raise Exception("You cannot delete the channel key!")
    key = property(key_get, key_set, key_del)

    # desc property (wraps db_desc)
    #@property
    def desc_get(self):
        "Getter. Allows for value = self.desc"
        return self.db_desc
    #@desc.setter
    def desc_set(self, value):
        "Setter. Allows for self.desc = value"
        self.db_desc = value
        self.save()
    #@desc.deleter
    def desc_del(self):
        "Deleter. Allows for del self.desc"
        self.db_desc = ""
        self.save()
    desc = property(desc_get, desc_set, desc_del)

    # aliases property
    #@property
    def aliases_get(self):
        "Getter. Allows for value = self.aliases. Returns a list of aliases."
        if self.db_aliases:
            return [perm.strip() for perm in self.db_aliases.split(',')]
        return []
    #@aliases.setter
    def aliases_set(self, value):
        "Setter. Allows for self.aliases = value. Stores as a comma-separated string."
        if is_iter(value):
            value = ",".join([str(val).strip().lower() for val in value])
        self.db_aliases = value
        self.save()
    #@aliases_del.deleter
    def aliases_del(self):
        "Deleter. Allows for del self.aliases"
        self.db_aliases = ""
        self.save()
    aliases = property(aliases_get, aliases_set, aliases_del)

    # keep_log property (wraps db_keep_log)
    #@property
    def keep_log_get(self):
        "Getter. Allows for value = self.keep_log"
        return self.db_keep_log
    #@keep_log.setter
    def keep_log_set(self, value):
        "Setter. Allows for self.keep_log = value"
        self.db_keep_log = value
        self.save()
    #@keep_log.deleter
    def keep_log_del(self):
        "Deleter. Allows for del self.keep_log"
        self.db_keep_log = False
        self.save()
    keep_log = property(keep_log_get, keep_log_set, keep_log_del)

    # lock_storage property (wraps db_lock_storage)
    #@property
    def lock_storage_get(self):
        "Getter. Allows for value = self.lock_storage"
        return self.db_lock_storage
    #@nick.setter
    def lock_storage_set(self, value):
        """Saves the lock_storagetodate. This is usually not called directly, but through self.lock()"""
        self.db_lock_storage = value
        self.save()
    #@nick.deleter
    def lock_storage_del(self):
        "Deleter is disabled. Use the lockhandler.delete (self.lock.delete) instead"""
        logger.log_errmsg("Lock_Storage (on %s) cannot be deleted. Use obj.lock.delete() instead." % self)
    lock_storage = property(lock_storage_get, lock_storage_set, lock_storage_del)

    db_model_name = "channel" # used by attributes to safely store objects

    class Meta:
        "Define Django meta options"
        verbose_name = "Channel"
        verbose_name_plural = "Channels"

    #
    # Channel class methods
    #

    def __str__(self):
        return "Channel '%s' (%s)" % (self.key, self.desc)

    def has_connection(self, player):
        """
        Checks so this player is actually listening
        to this channel.
        """
        # also handle object.player calls
        player, typ = identify_object(player)
        if typ == 'object':
            player = player.player
            player, typ = identify_object(player)
        if player and not typ == "player":
            logger.log_errmsg("Channel.has_connection received object of type '%s'. It only accepts players/characters." % typ)
            return
        # do the check
        return PlayerChannelConnection.objects.has_player_connection(player, self)

    def msg(self, msgobj, header=None, senders=None, persistent=True):
        """
        Send the given message to all players connected to channel. Note that
        no permission-checking is done here; it is assumed to have been
        done before calling this method. The optional keywords are not used if persistent is False.

        msgobj - a Msg/TempMsg instance or a message string. If one of the former, the remaining
              keywords will be ignored. If a string, this will either be sent as-is (if persistent=False) or
              it will be used together with header and senders keywords to create a Msg instance on the fly.
        senders (object, player or a list of objects or players) - ignored if msgobj is a Msg or TempMsg, or if
                 persistent=False.
        persistent (bool) - ignored if msgobj is a Msg or TempMsg. If True, a Msg will be created, using
                header and senders keywords. If False, other keywords will be ignored.

        """

        if isinstance(msgobj, basestring):
            # given msgobj is a string
            if persistent:
                msg = msgobj
                msgobj = Msg()
                msgobj.save()
                if senders:
                    msgobj.senders = make_iter(senders)
                msgobj.header = header
                msgobj.message = msg
                msgobj.channels = [self] # add this channel
            else:
                # just use the msg as-is
                msg = msgobj
        else:
            # already in a Msg/TempMsg
            msg = msgobj.message

        # get all players connected to this channel and send to them
        for conn in Channel.objects.get_all_connections(self):
            try:
                conn.player.msg(msg, senders)
            except AttributeError:
                try:
                    conn.to_external(msg, senders, from_channel=self)
                except Exception:
                    logger.log_trace("Cannot send msg to connection '%s'" % conn)
        return True

    def tempmsg(self, message, header=None, senders=None):
        """
        A wrapper for sending non-persistent messages.
        """
        self.msg(message, senders=senders, header=header, persistent=False)

    def connect_to(self, player):
        "Connect the user to this channel"
        if not self.access(player, 'listen'):
            return False
        conn = PlayerChannelConnection.objects.create_connection(player, self)
        if conn:
            return True
        return False

    def disconnect_from(self, player):
        "Disconnect user from this channel."
        PlayerChannelConnection.objects.break_connection(player, self)

    def delete(self):
        "Clean out all connections to this channel and delete it."
        for connection in Channel.objects.get_all_connections(self):
            connection.delete()
        super(Channel, self).delete()
    def access(self, accessing_obj, access_type='listen', default=False):
        """
        Determines if another object has permission to access.
        accessing_obj - object trying to access this one
        access_type - type of access sought
        default - what to return if no lock of access_type was found
        """
        return self.locks.check(accessing_obj, access_type=access_type, default=default)

class PlayerChannelConnection(SharedMemoryModel):
    """
    This connects a player object to a particular comm channel.
    The advantage of making it like this is that one can easily
    break the connection just by deleting this object.
    """

    # Player connected to a channel
    db_player = models.ForeignKey("players.PlayerDB", verbose_name='player')
    # Channel the player is connected to
    db_channel = models.ForeignKey(Channel, verbose_name='channel')

    # Database manager
    objects = managers.PlayerChannelConnectionManager()

    # player property (wraps db_player)
    #@property
    def player_get(self):
        "Getter. Allows for value = self.player"
        return self.db_player
    #@player.setter
    def player_set(self, value):
        "Setter. Allows for self.player = value"
        self.db_player = value
        self.save()
    #@player.deleter
    def player_del(self):
        "Deleter. Allows for del self.player. Deletes connection."
        self.delete()
    player = property(player_get, player_set, player_del)

    # channel property (wraps db_channel)
    #@property
    def channel_get(self):
        "Getter. Allows for value = self.channel"
        return self.db_channel
    #@channel.setter
    def channel_set(self, value):
        "Setter. Allows for self.channel = value"
        self.db_channel = value
        self.save()
    #@channel.deleter
    def channel_del(self):
        "Deleter. Allows for del self.channel. Deletes connection."
        self.delete()
    channel = property(channel_get, channel_set, channel_del)

    def __str__(self):
        return "Connection Player '%s' <-> %s" % (self.player, self.channel)

    class Meta:
        "Define Django meta options"
        verbose_name = "Channel<->Player link"
        verbose_name_plural = "Channel<->Player links"


class ExternalChannelConnection(SharedMemoryModel):
    """
    This defines an external protocol connecting to
    a channel, while storing some critical info about
    that connection.
    """
    # evennia channel connecting to
    db_channel = models.ForeignKey(Channel, verbose_name='channel',
                                   help_text='which channel this connection is tied to.')
    # external connection identifier
    db_external_key = models.CharField('external key', max_length=128,
                                       help_text='external connection identifier, used by calling protocol.')
    # eval-code to use when the channel tries to send a message
    # to the external protocol.
    db_external_send_code = models.TextField('executable code', blank=True,
           help_text='this is a custom snippet of Python code to connect the external protocol to the in-game channel.')
    # custom config for the connection
    db_external_config = models.TextField('external config', blank=True,
                                          help_text='configuration options on form understood by connection.')
    # activate the connection
    db_is_enabled = models.BooleanField('is enabled', default=True, help_text='turn on/off the connection.')

    objects = managers.ExternalChannelConnectionManager()

    class Meta:
        verbose_name = "External Channel Connection"

    def __str__(self):
        return "%s <-> external %s" % (self.channel.key, self.db_external_key)

    # channel property (wraps db_channel)
    #@property
    def channel_get(self):
        "Getter. Allows for value = self.channel"
        return self.db_channel
    #@channel.setter
    def channel_set(self, value):
        "Setter. Allows for self.channel = value"
        self.db_channel = value
        self.save()
    #@channel.deleter
    def channel_del(self):
        "Deleter. Allows for del self.channel. Deletes connection."
        self.delete()
    channel = property(channel_get, channel_set, channel_del)

    # external_key property (wraps db_external_key)
    #@property
    def external_key_get(self):
        "Getter. Allows for value = self.external_key"
        return self.db_external_key
    #@external_key.setter
    def external_key_set(self, value):
        "Setter. Allows for self.external_key = value"
        self.db_external_key = value
        self.save()
    #@external_key.deleter
    def external_key_del(self):
        "Deleter. Allows for del self.external_key. Deletes connection."
        self.delete()
    external_key = property(external_key_get, external_key_set, external_key_del)

    # external_send_code property (wraps db_external_send_code)
    #@property
    def external_send_code_get(self):
        "Getter. Allows for value = self.external_send_code"
        return self.db_external_send_code
    #@external_send_code.setter
    def external_send_code_set(self, value):
        "Setter. Allows for self.external_send_code = value"
        self.db_external_send_code = value
        self.save()
    #@external_send_code.deleter
    def external_send_code_del(self):
        "Deleter. Allows for del self.external_send_code. Deletes connection."
        self.db_external_send_code = ""
        self.save()
    external_send_code = property(external_send_code_get, external_send_code_set, external_send_code_del)

    # external_config property (wraps db_external_config)
    #@property
    def external_config_get(self):
        "Getter. Allows for value = self.external_config"
        return self.db_external_config
    #@external_config.setter
    def external_config_set(self, value):
        "Setter. Allows for self.external_config = value"
        self.db_external_config = value
        self.save()
    #@external_config.deleter
    def external_config_del(self):
        "Deleter. Allows for del self.external_config. Deletes connection."
        self.db_external_config = ""
        self.save()
    external_config = property(external_config_get, external_config_set, external_config_del)

    # is_enabled property (wraps db_is_enabled)
    #@property
    def is_enabled_get(self):
        "Getter. Allows for value = self.is_enabled"
        return self.db_is_enabled
    #@is_enabled.setter
    def is_enabled_set(self, value):
        "Setter. Allows for self.is_enabled = value"
        self.db_is_enabled = value
        self.save()
    #@is_enabled.deleter
    def is_enabled_del(self):
        "Deleter. Allows for del self.is_enabled. Deletes connection."
        self.delete()
    is_enabled = property(is_enabled_get, is_enabled_set, is_enabled_del)

    #
    # methods
    #

    def to_channel(self, message, from_obj=None):
        "Send external -> channel"
        if not from_obj:
            from_obj = self.external_key
        self.channel.msg(message, senders=[self])

    def to_external(self, message, senders=None, from_channel=None):
        "Send channel -> external"

        # make sure we are not echoing back our own message to ourselves
        # (this would result in a nasty infinite loop)
        if self in make_iter(senders):#.external_key:
            return

        try:
            # we execute the code snippet that should make it possible for the
            # connection to contact the protocol correctly (as set by the protocol).
            # Note that the code block has access to the variables here, such
            # as message, from_obj and from_channel.
            exec(to_str(self.external_send_code))
        except Exception:
            logger.log_trace("Channel %s could not send to External %s" % (self.channel, self.external_key))
