"""
These managers handles the 
"""

import itertools
from django.db import models
from django.contrib.contenttypes.models import ContentType
from src.utils.utils import is_iter

class CommError(Exception):
    "Raise by comm system, to allow feedback to player when caught."
    pass

# helper function

def to_object(inp, objtype='player'):
    """
    Locates the object related to the given
    playername or channel key. If input was already
    the correct object, return it.
    inp - the input object/string 
    objtype - 'player' or 'channel'
    """
    from src.players.models import PlayerDB
    if objtype == 'player':
        if type(inp) == PlayerDB:
            return inp
        if hasattr(inp, 'player'):
            return inp.player
        else:
            umatch = PlayerDB.objects.filter(user__username__iexact=inp)
            if umatch:
                return umatch[0]    
    elif objtype == 'external':
        from src.comms.models import ExternalChannelConnection
        if type (inp) == ExternalChannelConnection:
            return inp
        umatch = ExternalChannelConnection.objects.filter(db_key=inp)
        if umatch:
            return umatch[0]        
    else:
        # have to import this way to avoid circular imports
        from src.comms.models import Channel 
        #= ContentType.objects.get(app_label="comms", 
        #                                  model="channel").model_class()
        if type(inp) == Channel:
            return inp
        cmatch = Channel.objects.filter(db_key__iexact=inp)
        if cmatch:
            return cmatch[0]
    return None 
    
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
    
    def get_message_by_id(self, idnum):
        "Retrieve message by its id."        
        try:
            idnum = int(idnum)
            return self.get(id=id)
        except Exception:
            return None
        
    def get_messages_by_sender(self, player):
        """
        Get all messages sent by one player
        """
        player = to_object(player, objtype='player')        
        if not player:
            return None 
        return self.filter(db_sender=player).exclude(db_hide_from_sender=True)

    def get_messages_by_receiver(self, receiver):
        """
        Get all messages sent to one player
        """
        receiver = to_object(receiver)
        if not receiver:
            return None 
        return [msg for msg in self.all()
                if receiver in msg.receivers
                and receiver not in msg.hide_from_receivers]

    def get_messages_by_channel(self, channel):
        """
        Get all messages sent to one channel
        """
        channel = to_object(channel, objtype='channel')
        if not channel:
            return None 
        return [msg for msg in self.all()
                if channel in msg.channels 
                and channel not in msg.hide_from_channels]

    #TODO add search limited by send_times 
    def text_search(self, searchstring, filterdict=None):
        """
        Returns all messages that contain the matching
        search string. To avoid too many results, and also
        since this can be a very computing-
        heavy operation, it's recommended to be filtered
        by at least channel or sender/receiver. 
        searchstring - string to search for
        filterdict -
            {'channels':[list],
             'senders':[list],
             'receivers':[list]}
            lists can contain either the name/keys of the
            objects or the actual objects to filter by. 
        """        

        if filterdict:
            # obtain valid objects for all filters 
            channels = [chan for chan in
                        [to_object(chan, objtype='channel')
                         for chan in filterdict.get('channels',[])]
                        if chan]
            senders = [sender for sender in
                       [to_object(sender)
                        for sender in filterdict.get('senders',[])]
                        if sender]                       
            receivers = [receiver for receiver in
                         [to_object(receiver)
                          for receiver in filterdict.get('receivers',[])]
                         if receiver]
            # filter the messages lazily using the filter objects        
            msgs = []
            for sender in senders:
                msgs = list(sender.message_set.filter(
                        db_message__icontains=searchstring))                
            for receiver in receivers:
                rec_msgs = receiver.message_set.filter(
                        db_message__icontains=searchstring)
                if msgs:
                    msgs = [msg for msg in rec_msgs if msg in msgs]
                else:
                    msgs = rec_msgs 
            for channel in channels:
                chan_msgs = list(channel.message_set.filter(
                        db_message__icontains=searchstring))
                if msgs:
                    msgs = [msg for msg in chan_msgs if msg in msgs]
                else:
                    msgs = chan_msgs
            return list(set(msgs))
        return list(self.all().filter(db_message__icontains=searchstring))

    def message_search(self, sender=None, receiver=None, channel=None, freetext=None, dbref=None):    
        """
        Search the message database for particular messages. At least one 
        of the arguments must be given to do a search. 

        sender - get messages sent by a particular player
        receiver - get messages received by a certain player or players
        channel - get messages sent to a particular channel or channels
        freetext - Search for a text string in a message. 
                   NOTE: This can potentially be slow, so make sure to supply
                   one of the other arguments to limit the search.                     
        dbref - (int) the exact database id of the message. This will override 
                all other search crieteria since it's unique and
                always gives a list with only one match.
        """        
        if dbref:
            return self.filter(id=dbref)
        if freetext:
            if sender:
                sender = [sender]
            if receiver and not is_iter(receiver):
                receiver = [receiver]
            if channel and not is_iter(channel):
                channel = [channel]
            filterdict = {"senders":sender,
                          "receivers":receiver,
                          "channels":channel}
            return self.textsearch(freetext, filterdict)
        msgs = []
        if sender:
            msgs = self.get_messages_by_sender(sender)
        if receiver:           
            rec_msgs = self.get_messages_by_receiver(receiver)
            if msgs:
                msgs = [msg for msg in rec_msgs if msg in msgs]
            else:
                msgs = rec_msgs        
        if channel:
            chan_msgs = self.get_messaqge_by_channel(channel)
            if msgs:
                msgs = [msg for msg in chan_msgs if msg in msgs]
            else:
                msgs = chan_msgs
        return msgs
            
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

    def has_connection(self, player, channel):
        "Checks so a connection exists player<->channel"
        player = to_object(player)
        channel = to_object(channel, objtype="channel")
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
