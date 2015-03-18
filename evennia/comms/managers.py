"""
These managers handles the
"""

from django.db import models
from django.db.models import Q
from evennia.typeclasses.managers import (TypedObjectManager, TypeclassManager,
                                      returns_typeclass_list, returns_typeclass)

_GA = object.__getattribute__
_PlayerDB = None
_ObjectDB = None
_ChannelDB = None
_SESSIONS = None

# error class


class CommError(Exception):
    "Raise by comm system, to allow feedback to player when caught."
    pass


#
# helper functions
#

def dbref(dbref, reqhash=True):
    """
    Valid forms of dbref (database reference number)
    are either a string '#N' or an integer N.
    Output is the integer part.
    """
    if reqhash and not (isinstance(dbref, basestring) and dbref.startswith("#")):
        return None
    if isinstance(dbref, basestring):
        dbref = dbref.lstrip('#')
    try:
        if int(dbref) < 0:
            return None
    except Exception:
        return None
    return dbref


def identify_object(inp):
    "identify if an object is a player or an object; return its database model"
    if hasattr(inp, "__dbclass__"):
        clsname = inp.__dbclass__.__name__
        if clsname == "PlayerDB":
            return inp, "player"
        elif clsname == "ObjectDB":
            return inp ,"object"
        elif clsname == "ChannelDB":
            return inp, "channel"
    if isinstance(inp, basestring):
        return inp, "string"
    elif dbref(inp):
        return dbref(inp), "dbref"
    else:
        return inp, None


def to_object(inp, objtype='player'):
    """
    Locates the object related to the given
    playername or channel key. If input was already
    the correct object, return it.
    inp - the input object/string
    objtype - 'player' or 'channel'
    """
    obj, typ = identify_object(inp)
    if typ == objtype:
        return obj
    if objtype == 'player':
        if typ == 'object':
            return obj.player
        if typ == 'string':
            return _PlayerDB.objects.get(user_username__iexact=obj)
        if typ == 'dbref':
            return _PlayerDB.objects.get(id=obj)
        print objtype, inp, obj, typ, type(inp)
        raise CommError()
    elif objtype == 'object':
        if typ == 'player':
            return obj.obj
        if typ == 'string':
            return _ObjectDB.objects.get(db_key__iexact=obj)
        if typ == 'dbref':
            return _ObjectDB.objects.get(id=obj)
        print objtype, inp, obj, typ, type(inp)
        raise CommError()
    elif objtype == 'channel':
        if typ == 'string':
            return _ChannelDB.objects.get(db_key__iexact=obj)
        if typ == 'dbref':
            return _ChannelDB.objects.get(id=obj)
        print objtype, inp, obj, typ, type(inp)
        raise CommError()

#
# Msg manager
#

class MsgManager(models.Manager):
    """
    This MsgManager implements methods for searching
    and manipulating Messages directly from the database.

    These methods will all return database objects
    (or QuerySets) directly.

    A Message represents one unit of communication, be it over a
    Channel or via some form of in-game mail system. Like an e-mail,
    it always has a sender and can have any number of receivers (some
    of which may be Channels).

    Evennia-specific:
     get_message_by_id
     get_messages_by_sender
     get_messages_by_receiver
     get_messages_by_channel
     text_search
     message_search (equivalent to evennia.search_messages)
    """

    def identify_object(self, obj):
        "method version for easy access"
        return identify_object(obj)

    def get_message_by_id(self, idnum):
        "Retrieve message by its id."
        try:
            return self.get(id=self.dbref(idnum, reqhash=False))
        except Exception:
            return None

    def get_messages_by_sender(self, obj, exclude_channel_messages=False):
        """
        Get all messages sent by one entity - this could be either a
        player or an object

        only_non_channel: only return messages -not- aimed at a channel
        (e.g. private tells)
        """
        obj, typ = identify_object(obj)
        if exclude_channel_messages:
            # explicitly exclude channel recipients
            if typ == 'player':
                return list(self.filter(db_sender_players=obj,
                            db_receivers_channels__isnull=True).exclude(db_hide_from_players=obj))
            elif typ == 'object':
                return list(self.filter(db_sender_objects=obj,
                            db_receivers_channels__isnull=True).exclude(db_hide_from_objects=obj))
            else:
                raise CommError
        else:
            # get everything, channel or not
            if typ == 'player':
                return list(self.filter(db_sender_players=obj).exclude(db_hide_from_players=obj))
            elif typ == 'object':
                return list(self.filter(db_sender_objects=obj).exclude(db_hide_from_objects=obj))
            else:
                raise CommError

    def get_messages_by_receiver(self, obj):
        """
        Get all messages sent to one give recipient
        """
        obj, typ = identify_object(obj)
        if typ == 'player':
            return list(self.filter(db_receivers_players=obj).exclude(db_hide_from_players=obj))
        elif typ == 'object':
            return list(self.filter(db_receivers_objects=obj).exclude(db_hide_from_objects=obj))
        elif typ == 'channel':
            return list(self.filter(db_receivers_channels=obj).exclude(db_hide_from_channels=obj))
        else:
            raise CommError

    def get_messages_by_channel(self, channel):
        """
        Get all messages sent to one channel
        """
        return self.filter(db_receivers_channels=channel).exclude(db_hide_from_channels=channel)

    def message_search(self, sender=None, receiver=None, freetext=None, dbref=None):
        """
        Search the message database for particular messages. At least one
        of the arguments must be given to do a search.

        sender - get messages sent by a particular player or object
        receiver - get messages received by a certain player,object or channel
        freetext - Search for a text string in a message.
                   NOTE: This can potentially be slow, so make sure to supply
                   one of the other arguments to limit the search.
        dbref - (int) the exact database id of the message. This will override
                all other search criteria since it's unique and
                always gives a list with only one match.
        """
        # unique msg id
        if dbref:
            msg = self.objects.filter(id=dbref)
            if msg:
                return msg[0]

        # We use Q objects to gradually build up the query - this way we only
        # need to do one database lookup at the end rather than gradually
        # refining with multiple filter:s. Django Note: Q objects can be
        # combined with & and | (=AND,OR). ~ negates the queryset

        # filter by sender
        sender, styp = identify_object(sender)
        if styp == 'player':
            sender_restrict = Q(db_sender_players=sender) & ~Q(db_hide_from_players=sender)
        elif styp == 'object':
            sender_restrict = Q(db_sender_objects=sender) & ~Q(db_hide_from_objects=sender)
        else:
            sender_restrict = Q()
        # filter by receiver
        receiver, rtyp = identify_object(receiver)
        if rtyp == 'player':
            receiver_restrict = Q(db_receivers_players=receiver) & ~Q(db_hide_from_players=receiver)
        elif rtyp == 'object':
            receiver_restrict = Q(db_receivers_objects=receiver) & ~Q(db_hide_from_objects=receiver)
        elif rtyp == 'channel':
            receiver_restrict = Q(db_receivers_channels=receiver) & ~Q(db_hide_from_channels=receiver)
        else:
            receiver_restrict = Q()
        # filter by full text
        if freetext:
            fulltext_restrict = Q(db_header__icontains=freetext) | Q(db_message__icontains=freetext)
        else:
            fulltext_restrict = Q()
        # execute the query
        return list(self.filter(sender_restrict & receiver_restrict & fulltext_restrict))


#
# Channel manager
#

class ChannelDBManager(TypedObjectManager):
    """
    This ChannelManager implements methods for searching
    and manipulating Channels directly from the database.

    These methods will all return database objects
    (or QuerySets) directly.

    A Channel is an in-game venue for communication. It's
    essentially representation of a re-sender: Users sends
    Messages to the Channel, and the Channel re-sends those
    messages to all users subscribed to the Channel.

    Evennia-specific:
    get_all_channels
    get_channel(channel)
    get_subscriptions(player)
    channel_search (equivalent to evennia.search_channel)

    """
    @returns_typeclass_list
    def get_all_channels(self):
        """
        Returns all channels in game.
        """
        return self.all()

    @returns_typeclass
    def get_channel(self, channelkey):
        """
        Return the channel object if given its key.
        Also searches its aliases.
        """
        # first check the channel key
        channels = self.filter(db_key__iexact=channelkey)
        if not channels:
            # also check aliases
            channels = [channel for channel in self.all()
                        if channelkey in channel.aliases.all()]
        if channels:
            return channels[0]
        return None

    @returns_typeclass_list
    def get_subscriptions(self, entity):
        """
        Return all channels a given player is subscribed to
        """
        clsname = entity.__dbclass__.__name__
        if clsname == "PlayerDB":
            return entity.subscription_set.all()
        if clsname == "ObjectDB":
            return entity.object_subscription_set.all()
        return []

    @returns_typeclass_list
    def channel_search(self, ostring, exact=True):
        """
        Search the channel database for a particular channel.

        ostring - the key or database id of the channel.
        exact - require an exact key match (still not case sensitive)
        """
        channels = []
        if not ostring: return channels
        try:
            # try an id match first
            dbref = int(ostring.strip('#'))
            channels = self.filter(id=dbref)
        except Exception:
            pass
        if not channels:
            # no id match. Search on the key.
            if exact:
                channels = self.filter(db_key__iexact=ostring)
            else:
                channels = self.filter(db_key__icontains=ostring)
        if not channels:
            # still no match. Search by alias.
            channels = [channel for channel in self.all()
                        if ostring.lower() in [a.lower
                            for a in channel.aliases.all()]]
        return channels

class ChannelManager(ChannelDBManager, TypeclassManager):
    pass


