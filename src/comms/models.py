"""
Models for the comsystem.

The comsystem's main component is the Message, which
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

from django.db import models
from src.utils.idmapper.models import SharedMemoryModel
from src.server.sessionhandler import SESSIONS
from src.comms import managers 
from src.locks.lockhandler import LockHandler
from src.utils.utils import is_iter
from src.utils.utils import dbref as is_dbref


#------------------------------------------------------------
#
# Utils
#
#------------------------------------------------------------

def obj_to_id(inp):
    """
    Converts input object to an id string.
    """
    dbref = is_dbref(inp)
    if dbref:
        return str(dbref) 
    if hasattr(inp, 'id'):
        return str(inp.id)
    if hasattr(inp, 'dbobj') and hasattr(inp.dbobj, 'id'):
        return str(inp.dbobj.id)
    return str(inp) 

def id_to_obj(dbref, db_model='PlayerDB'):
    """
    loads from dbref to object. Uses the db_model to search
    for the id. 
    """    
    if db_model == 'PlayerDB':
        from src.players.models import PlayerDB as db_model
    else:
        db_model = Channel
    try:
        dbref = int(dbref.strip())
        return db_model.objects.get(id=dbref)
    except Exception:
        return None 

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

    # There must always be one sender of the message.
    db_sender = models.ForeignKey("players.PlayerDB", related_name='sender_set')
    # The destination objects of this message. Stored as a
    # comma-separated string of object dbrefs. Can be defined along
    # with channels below.
    db_receivers = models.CharField(max_length=255, null=True, blank=True)                                       
    # The channels this message was sent to. Stored as a
    # comma-separated string of channel dbrefs. A message can both
    # have channel targets and destination objects.
    db_channels = models.CharField(max_length=255, null=True, blank=True)
    # The actual message and a timestamp. The message field
    # should itself handle eventual headers etc. 
    db_message = models.TextField()
    db_date_sent = models.DateTimeField(editable=False, auto_now_add=True)
    # lock storage
    db_lock_storage = models.TextField(blank=True)
    # These are settable by senders/receivers/channels respectively.
    # Stored as a comma-separated string of dbrefs. Can be used by the
    # game to mask out messages from being visible in the archive (no
    # messages are actually deleted)
    db_hide_from_sender = models.BooleanField(default=False)
    db_hide_from_receivers = models.CharField(max_length=255, null=True, blank=True)
    db_hide_from_channels = models.CharField(max_length=255, null=True, blank=True)
    # Storage of lock strings
    db_lock_storage = models.TextField(null=True)    
 
    # Database manager 
    objects = managers.MsgManager()

    def __init__(self, *args, **kwargs):
        SharedMemoryModel.__init__(self, *args, **kwargs)
        self.locks = LockHandler(self)

    class Meta:
        "Define Django meta options"
        verbose_name = "Message"
        verbose_name_plural = "Messages"

    # Wrapper properties to easily set database fields. These are
    # @property decorators that allows to access these fields using
    # normal python operations (without having to remember to save()
    # etc). So e.g. a property 'attr' has a get/set/del decorator
    # defined that allows the user to do self.attr = value, 
    # value = self.attr and del self.attr respectively (where self 
    # is the object in question).

    # sender property (wraps db_sender)
    #@property
    def sender_get(self):
        "Getter. Allows for value = self.sender"
        return self.db_sender
    #@sender.setter
    def sender_set(self, value):
        "Setter. Allows for self.sender = value"
        self.db_sender = value
        self.save()
    #@sender.deleter
    def sender_del(self):
        "Deleter. Allows for del self.sender"
        raise Exception("You cannot delete the sender of a message!")
    sender = property(sender_get, sender_set, sender_del)

    # receivers property
    #@property
    def receivers_get(self):
        "Getter. Allows for value = self.receivers. Returns a list of receivers."
        if self.db_receivers:
            return [id_to_obj(dbref) for dbref in self.db_receivers.split(',')]
        return []
    #@receivers.setter
    def receivers_set(self, value):
        "Setter. Allows for self.receivers = value. Stores as a comma-separated string."
        if is_iter(value):
            value = ",".join([obj_to_id(val) for val in value])
        self.db_receivers = obj_to_id(value)
        self.save()        
    #@receivers.deleter
    def receivers_del(self):
        "Deleter. Allows for del self.receivers"
        self.db_receivers = ""
        self.save()
    receivers = property(receivers_get, receivers_set, receivers_del)

    # channels property
    #@property
    def channels_get(self):
        "Getter. Allows for value = self.channels. Returns a list of channels."
        if self.db_channels:
            return [id_to_obj(dbref, 'Channel') for dbref in self.db_channels.split(',')]
        return []
    #@channels.setter
    def channels_set(self, value):
        "Setter. Allows for self.channels = value. Stores as a comma-separated string."
        if is_iter(value):
            value = ",".join([obj_to_id(val) for val in value])
        self.db_channels = obj_to_id(value)
        self.save()        
    #@channels.deleter
    def channels_del(self):
        "Deleter. Allows for del self.channels"
        self.db_channels = ""
        self.save()
    channels = property(channels_get, channels_set, channels_del)

    # message property (wraps db_message)
    #@property
    def message_get(self):
        "Getter. Allows for value = self.message"
        return self.db_message
    #@message.setter
    def message_set(self, value):
        "Setter. Allows for self.message = value"
        self.db_message = value
        self.save()
    #@message.deleter
    def message_del(self):
        "Deleter. Allows for del self.message"
        self.db_message = ""
        self.save()
    message = property(message_get, message_set, message_del)

    # date_sent property (wraps db_date_sent)
    #@property
    def date_sent_get(self):
        "Getter. Allows for value = self.date_sent"
        return self.db_date_sent
    #@date_sent.setter
    def date_sent_set(self, value):
        "Setter. Allows for self.date_sent = value"
        raise Exception("You cannot edit date_sent!")
    #@date_sent.deleter
    def date_sent_del(self):
        "Deleter. Allows for del self.date_sent"
        raise Exception("You cannot delete the date_sent property!")
    date_sent = property(date_sent_get, date_sent_set, date_sent_del)

    # hide_from_sender property
    #@property
    def hide_from_sender_get(self):
        "Getter. Allows for value = self.hide_from_sender."
        return self.db_hide_from_sender
    #@hide_from_sender.setter
    def hide_from_sender_set(self, value):
        "Setter. Allows for self.hide_from_senders = value."
        self.db_hide_from_sender = value
        self.save()        
    #@hide_from_sender.deleter
    def hide_from_sender_del(self):
        "Deleter. Allows for del self.hide_from_senders"
        self.db_hide_from_sender = False
        self.save()
    hide_from_sender = property(hide_from_sender_get, hide_from_sender_set, hide_from_sender_del)

    # hide_from_receivers property
    #@property
    def hide_from_receivers_get(self):
        "Getter. Allows for value = self.hide_from_receivers. Returns a list of hide_from_receivers."
        if self.db_hide_from_receivers:
            return [id_to_obj(dbref) for dbref in self.db_hide_from_receivers.split(',')]
        return []
    #@hide_from_receivers.setter
    def hide_from_receivers_set(self, value):
        "Setter. Allows for self.hide_from_receivers = value. Stores as a comma-separated string."
        if is_iter(value):
            value = ",".join([obj_to_id(val) for val in value])
        self.db_hide_from_receivers = obj_to_id(value)
        self.save()        
    #@hide_from_receivers.deleter
    def hide_from_receivers_del(self):
        "Deleter. Allows for del self.hide_from_receivers"
        self.db_hide_from_receivers = ""
        self.save()
    hide_from_receivers = property(hide_from_receivers_get, hide_from_receivers_set, hide_from_receivers_del)

    # hide_from_channels property
    #@property
    def hide_from_channels_get(self):
        "Getter. Allows for value = self.hide_from_channels. Returns a list of hide_from_channels."
        if self.db_hide_from_channels:            
            return [id_to_obj(dbref) for dbref in self.db_hide_from_channels.split(',')]
        return []
    #@hide_from_channels.setter
    def hide_from_channels_set(self, value):
        "Setter. Allows for self.hide_from_channels = value. Stores as a comma-separated string."
        if is_iter(value):
            value = ",".join([obj_to_id(val) for val in value])
        self.db_hide_from_channels = obj_to_id(value)
        self.save()        
    #@hide_from_channels.deleter
    def hide_from_channels_del(self):
        "Deleter. Allows for del self.hide_from_channels"
        self.db_hide_from_channels = ""
        self.save()
    hide_from_channels = property(hide_from_channels_get, hide_from_channels_set, hide_from_channels_del)

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


    # 
    # Msg class methods
    # 

    def __str__(self):
        "Print text"
        if self.channels:            
            return "%s -> %s: %s" % (self.sender.key, 
                                       ", ".join([chan.key for chan in self.channels]), 
                                       self.message)
        else:
            return "%s -> %s: %s" % (self.sender.key,
                                       ", ".join([rec.key for rec in self.receivers]),
                                       self.message)
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
    db_key = models.CharField(max_length=255, unique=True)
    # optional description of channel 
    db_desc = models.CharField(max_length=80, blank=True, null=True)       
    # aliases for the channel. These are searched by cmdhandler
    # as well to determine if a command is the name of a channel.
    # Several aliases are separated by commas. 
    db_aliases = models.CharField(max_length=255) 
    # Whether this channel should remember its past messages
    db_keep_log = models.BooleanField(default=True)
    # Storage of lock definitions
    db_lock_storage = models.TextField(blank=True)
 
    # Database manager
    objects = managers.ChannelManager()

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
        return ChannelConnection.objects.has_connection(player, self)

    def msg(self, msgobj, from_obj=None):
        """
        Send the given message to all players connected to channel. Note that
        no permission-checking is done here; it is assumed to have been
        done before calling this method. 

        msgobj - a Msg instance. May be a message string.
        from_obj - if msgobj is not an Msg-instance, this is used to create
                   a message on the fly. The advantage of this is that such
                   messages are logged. 

        """
        if not type(msgobj) == Msg:            
            # the given msgobj is not an Msg instance. If it is a string and from_obj
            # was given, we create the message on the fly instead. 
            if from_obj and isinstance(msgobj, basestring):
                msgobj = Msg(db_sender=from_obj, db_message=msgobj)
                msgobj.save()
                msgobj.channels = [self]                                                
                msg = msgobj.message 
            else:
                # this just sends a message, without any sender 
                # (and without storing it in a persistent Msg object)
                msg = str(msgobj)
        else:
            msg = msgobj.message

        # get all players connected to this channel
        conns = Channel.objects.get_all_connections(self)        

        # send message to all connected players 
        for conn in conns:
            for session in \
                    SESSIONS.sessions_from_player(conn.player):
                session.msg(msg)
        return True 
            
    def connect_to(self, player):
        "Connect the user to this channel"
        if not self.access(player, 'listen'):
            return False
        conn = ChannelConnection.objects.create_connection(player, self)
        if conn:
            return True
        return False 

    def disconnect_from(self, player):
        "Disconnect user from this channel."
        ChannelConnection.objects.break_connection(player, self)

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

class ChannelConnection(SharedMemoryModel):
    """
    This connects a user object to a particular comm channel.
    The advantage of making it like this is that one can easily
    break the connection just by deleting this object. 
    """
    # Player connected to a channel
    db_player = models.ForeignKey("players.PlayerDB")
    # Channel the player is connected to
    db_channel = models.ForeignKey(Channel)

    # Database manager
    objects = managers.ChannelConnectionManager()

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

