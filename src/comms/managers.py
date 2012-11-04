"""
These managers handles the
"""

import itertools
from django.db import models
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType

_GA = object.__getattribute__
_PlayerDB = None
_ObjectDB = None
_Channel = None
_ExternalConnection = None
_User = None

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
    # load global stores
    global _PlayerDB, _ObjectDB, _Channel, _ExternalConnection, _User
    if not _PlayerDB:
        from src.players.models import PlayerDB as _PlayerDB
    if not _ObjectDB:
        from src.objects.models import ObjectDB as _ObjectDB
    if not _Channel:
        from src.comms.models import Channel as _Channel
    if not _ExternalConnection:
        from src.comms.models import ExternalChannelConnection as _ExternalConnection
    if not _User:
        from django.contrib.auth.models import User as _User
    if not inp:
        return inp, None
    # try to identify the type
    try:
        obj = _GA(inp, "dbobj") # this works for all typeclassed entities
    except AttributeError:
        obj = inp
    typ = type(obj)
    if typ == _PlayerDB: return obj, "player"
    if typ == _User: return obj.get_profile(), "player"
    elif typ == _ObjectDB: return obj, "object"
    elif typ == _Channel: return obj, "channel"
    elif dbref(obj): return dbref(obj), "dbref"
    elif typ == basestring: return obj, "string"
    elif typ == _ExternalConnection: return obj, "external"
    return obj, None   # Something else

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
        if typ == 'object': return obj.player
        if typ == 'string': return _PlayerDB.objects.get(user_username__iexact=obj)
        if typ == 'dbref': return _PlayerDB.objects.get(id=obj)
        print objtype, inp, obj, typ, type(inp)
        raise CommError()
    elif objtype == 'object':
        if typ == 'player': return obj.obj
        if typ == 'string': return _ObjectDB.objects.get(db_key__iexact=obj)
        if typ == 'dbref': return _ObjectDB.objects.get(id=obj)
        print objtype, inp, obj, typ, type(inp)
        raise CommError()
    elif objtype == 'channel':
        if typ == 'string': return _Channel.objects.get(db_key__iexact=obj)
        if typ == 'dbref': return _Channel.objects.get(id=obj)
        print objtype, inp, obj, typ, type(inp)
        raise CommError()
    elif objtype == 'external':
        if typ == 'string': return _ExternalConnection.objects.get(db_key=inp)
        if typ == 'dbref': return _ExternalConnection.objects.get(id=obj)
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
     message_search (equivalent to ev.search_messages)
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
        Get all messages sent by one entity - this could be either a player or an object

        only_non_channel: only return messages -not- aimed at a channel (e.g. private tells)
        """
        obj, typ = identify_object(obj)
        if exclude_channel_messages:
            # explicitly exclude channel recipients
            if typ == 'player':
                return list(self.filter(db_sender_players=obj, db_receivers_channels__isnull=True).exclude(db_hide_from_players=obj))
            elif typ == 'object':
                return list(self.filter(db_sender_objects=obj, db_receivers_channels__isnull=True).exclude(db_hide_from_objects=obj))
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
                all other search crieteria since it's unique and
                always gives a list with only one match.
        """
        # unique msg id
        if dbref:
            msg = self.objects.filter(id=dbref)
            if msg:
                return msg[0]

        # We use Q objects to gradually build up the query - this way we only need to do one
        # database lookup at the end rather than gradually refining with multiple filter:s.
        # Django Note: Q objects can be combined with & and | (=AND,OR). ~ negates the queryset

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

class ChannelManager(models.Manager):
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
    get_channel
    del_channel
    get_all_connections
    channel_search (equivalent to ev.search_channel)

    """

    def get_all_channels(self):
        """
        Returns all channels in game.
        """
        return self.all()

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
                        if channelkey in channel.aliases]
        if channels:
            return channels[0]
        return None

    def del_channel(self, channelkey):
        """
        Delete channel matching channelkey.
        Also cleans up channelhandler.
        """
        channels = self.filter(db_key__iexact=channelkey)
        if not channels:
            # no aliases allowed for deletion.
            return False
        for channel in channels:
            channel.delete()
        from src.comms.channelhandler import CHANNELHANDLER
        CHANNELHANDLER.update()
        return None

    def get_all_connections(self, channel):
        """
        Return the connections of all players listening
        to this channel
        """
        # import here to avoid circular imports
        #from src.comms.models import PlayerChannelConnection
        PlayerChannelConnection = ContentType.objects.get(app_label="comms",
                                                          model="playerchannelconnection").model_class()
        ExternalChannelConnection = ContentType.objects.get(app_label="comms",
                                                            model="externalchannelconnection").model_class()
        return itertools.chain(PlayerChannelConnection.objects.get_all_connections(channel),
                               ExternalChannelConnection.objects.get_all_connections(channel))

    def channel_search(self, ostring):
        """
        Search the channel database for a particular channel.

        ostring - the key or database id of the channel.
        """
        channels = []
        try:
            # try an id match first
            dbref = int(ostring.strip('#'))
            channels = self.filter(id=dbref)
        except Exception:
            pass
        if not channels:
            # no id match. Search on the key.
            channels = self.filter(db_key__iexact=ostring)
        if not channels:
            # still no match. Search by alias.
            channels = [channel for channel in self.all() if ostring.lower in [a.lower for a in channel.aliases]]
        return channels

#
# PlayerChannelConnection manager
#
class PlayerChannelConnectionManager(models.Manager):
    """
    This PlayerChannelConnectionManager implements methods for searching
    and manipulating PlayerChannelConnections directly from the database.

    These methods will all return database objects
    (or QuerySets) directly.

    A PlayerChannelConnection defines a user's subscription to an in-game
    channel - deleting the connection object will disconnect the player
    from the channel.

    Evennia-specific:
    get_all_player_connections
    has_connection
    get_all_connections
    create_connection
    break_connection

    """

    def get_all_player_connections(self, player):
        "Get all connections that the given player has."
        player = to_object(player)
        return self.filter(db_player=player)

    def has_player_connection(self, player, channel):
        "Checks so a connection exists player<->channel"
        if player and channel:
            return self.filter(db_player=player).filter(db_channel=channel).count() > 0
        return False

    def get_all_connections(self, channel):
        """
        Get all connections for a channel
        """
        channel = to_object(channel, objtype='channel')
        return self.filter(db_channel=channel)

    def create_connection(self, player, channel):
        """
        Connect a player to a channel. player and channel
        can be actual objects or keystrings.
        """
        player = to_object(player)
        channel = to_object(channel, objtype='channel')
        if not player or not channel:
            raise CommError("NOTFOUND")
        new_connection = self.model(db_player=player, db_channel=channel)
        new_connection.save()
        return new_connection

    def break_connection(self, player, channel):
        "Remove link between player and channel"
        player = to_object(player)
        channel = to_object(channel, objtype='channel')
        if not player or not channel:
            raise CommError("NOTFOUND")
        conns = self.filter(db_player=player).filter(db_channel=channel)
        for conn in conns:
            conn.delete()

class ExternalChannelConnectionManager(models.Manager):
    """
    This ExternalChannelConnectionManager implements methods for searching
    and manipulating HelpEntries directly from the database.

    These methods will all return database objects
    (or QuerySets) directly.

    An ExternalChannelConnetion describes the connection between an in-game
    channel and some external source, such as an IRC or IMC channel.

    Evennia-specific:
    get_all_external_connections
    has_connection
    get_all_connections
    create_connection
    break_connection

    """

    def get_all_external_connections(self, external):
        "Get all connections that the given as external."
        external = to_object(external, objtype='external')
        return self.filter(db_external_key=external)

    def has_connection(self, external, channel):
        "Checks so a connection exists external<->channel"
        external = to_object(external, objtype='external')
        channel = to_object(channel, objtype="channel")
        if external and channel:
            return self.filter(db_external_key=external).filter(db_channel=channel).count() > 0
        return False

    def get_all_connections(self, channel):
        """
        Get all connections for a channel
        """
        channel = to_object(channel, objtype='channel')
        return self.filter(db_channel=channel)

    def create_connection(self, external, channel, config=""):
        """
        Connect a external to a channel. external and channel
        can be actual objects or keystrings.
        """
        channel = to_object(channel, objtype='channel')
        if not channel:
            raise CommError("NOTFOUND")
        new_connection = self.model(db_external_key=external, db_channel=channel, db_external_config=config)
        new_connection.save()
        return new_connection

    def break_connection(self, external, channel):
        "Remove link between external and channel"
        external = to_object(external)
        channel = to_object(channel, objtype='channel')
        if not external or not channel:
            raise CommError("NOTFOUND")
        conns = self.filter(db_external_key=external).filter(db_channel=channel)
        for conn in conns:
            conn.delete()
