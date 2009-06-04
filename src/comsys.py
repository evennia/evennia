"""
Comsys functions.
"""
import time
import datetime
from django.utils import simplejson
from src.channels.models import CommChannel, CommChannelMessage, CommChannelMembership
from src import session_mgr
from src import ansi
from src import logger

def plr_get_cdict(session):
    """
    Returns the users's channel subscription dictionary. Use this instead of
    directly referring to the session object.
    
    session: (SessionProtocol) Reference to a player session.
    """
    return session.channels_subscribed

def plr_listening_channel(session, cstr, alias_search=False):
    """
    Returns a player's listening status for a channel.
    
    session: (SessionProtocol) Reference to a player session.
    cstr: (str) The channel name or alias (depending on alias_search).
    alias_search: (bool) If true, search by alias. Else search by full name.
    """
    return plr_has_channel(session, cstr, alias_search=alias_search, 
        return_muted=False)    
    
def plr_cname_from_alias(session, calias):
    """
    Returns a channel name given a channel alias.
    
    session: (SessionProtocol) Reference to a player session.
    calias: (str) The channel alias.
    """
    return plr_get_cdict(session).get(calias, None)[0]

def plr_chan_off(session, calias):
    """
    Turn a channel off for a player.
    
    session: (SessionProtocol) Reference to a player session.
    calias: (str) The channel alias.
    """
    if not plr_listening_channel(session, calias, alias_search=True):
        session.msg("You're already not listening to that channel.")
        return
    else:
        cname = plr_cname_from_alias(session, calias)
        cobj = get_cobj_from_name(cname)
        plr_set_channel_listening(session, calias, False)
        session.msg("You have left %s." % (cname,))
        send_cmessage(cname, "%s has left the channel." % ( 
            session.get_pobject().get_name(show_dbref=False),))

def plr_chan_on(session, calias):
    """
    Turn a channel on for a player.

    session: (SessionProtocol) Reference to a player session.
    calias: (str) The channel alias.
    """
    plr_listening = plr_listening_channel(session, calias, alias_search=True)
    if plr_listening:
        session.msg("You're already listening to that channel.")
        return
    else:
        cname = plr_cname_from_alias(session, calias)
        cobj = get_cobj_from_name(cname)
        send_cmessage(cname, "%s has joined the channel." % ( 
            session.get_pobject().get_name(show_dbref=False),))
        plr_set_channel_listening(session, calias, True)
        session.msg("You have joined %s." % (cname,))
    
def plr_has_channel(session, cname, alias_search=False, return_muted=False):
    """
    Is this session subscribed to the named channel?
    
    session: (SessionProtocol) Reference to a player session.
    cname: (str) The channel name or alias (depending on alias_search)
    alias_search: (bool) If False, search by full name. Else search by alias.
    return_muted: (bool) Take the user's enabling/disabling of the channel
                                into consideration?
    """
    has_channel = False

    if alias_search:
        # Search by aliases only.
        cdat = plr_get_cdict(session).get(cname, False)
        # No key match, fail immediately.
        if not cdat:
            return False
        
        # If channel status is taken into consideration, see if the user
        # has the channel muted or not.
        if return_muted:
            return True
        else:
            return cdat[1]

    else:
        # Search by complete channel name.
        chan_list = plr_get_cdict(session).values()
        for chan in chan_list:
            # Check for a name match
            if cname.lower() == chan[0].lower():
                has_channel = True

                # If channel status is taken into consideration, see if the user
                # has the channel muted or not.
                if return_muted is False and not chan[1]:
                    has_channel = False
                break

    return has_channel

def plr_set_channel_listening(session, alias, listening):
    """
    Enables or disables listening on a particular channel based on the
    user's channel alias.
    
    session: (SessionProtocol) A reference to the player session.
    alias: (str) The channel alias.
    listening: (bool) A True or False value to determine listening status.
    """
    membership = session.pobject.channel_membership_set.get(user_alias=alias)
    membership.is_listening = listening
    membership.save()
    plr_get_cdict(session).get(alias)[1] = listening
    
def plr_add_channel(source_object, alias, channel):
    """
    Adds a player to a channel via a CommChannelMembership and sets the cached
    cdict value.
    
    source_object: (Object) Reference to the object that will be listening.
    alias: (str) The channel alias (also the key in the user's cdict)
    channel: (CommChannel) The channel object to add.
    listening: (bool) A True or False value to determine listening status.
    """
    membership = CommChannelMembership(channel=channel, listener=source_object,
                                           user_alias=alias)
    membership.save()
    
    sessions = session_mgr.sessions_from_object(source_object)
    for session in sessions:
        plr_get_cdict(session)[alias] = [channel.get_name(), True]

def plr_del_channel(source_object, alias):
    """
    Remove a channel from a session's channel list.
    
    source_object: (Object) Reference to the object that will be listening.
    alias: (str) The channel alias (also the key in the user's cdict)
    """
    membership = source_object.channel_membership_set.get(user_alias=alias)
    membership.delete()
    
    sessions = session_mgr.sessions_from_object(source_object)
    for session in sessions:
        del plr_get_cdict(session)[alias]

def msg_chan_hist(target_obj, channel_name):
    """
    Sends a listing of subscribers to a channel given a channel name.
    
    target_obj: (Object) The object to send the history listing to.
    channel_name: (str) The channel's full name.
    """
    cobj = get_cobj_from_name(channel_name)
    hist_list = CommChannelMessage.objects.filter(channel=cobj).order_by('date_sent')
    
    # Negative indexing is not currently supported with QuerySet objects.
    # Figure out what the first CommChannelMessage is to return and grab the
    # next 20.
    first_msg = hist_list.count() - 20
    # Prevent a negative index from being called on.
    if first_msg < 0:
        first_msg = 0
    
    # Slice and dice, display last 20 messages.
    for entry in hist_list[first_msg:]:
        delta_days = datetime.datetime.now() - entry.date_sent
        days_elapsed = delta_days.days
        if days_elapsed > 0:
            # Message happened more than a day ago, show the date.
            time_str = entry.date_sent.strftime("%m.%d / %H:%M")
        else:
            # Recent message (within last 24 hours), show hour:minute.
            time_str = entry.date_sent.strftime("%H:%M")
        target_obj.emit_to("[%s] %s" % (time_str, entry.message))
    
def msg_cwho(target_obj, channel_name):
    """
    Sends a listing of subscribers to a channel given a channel name.
    
    target_obj: (Object) Send the cwho listing to this object.
    channel_name: (str) The channel's full name.
    """
    target_obj.emit_to("--- Users Listening to %s ---" % (channel_name,))
    for plr_sess in get_cwho_list(channel_name):
        target_obj.emit_to(plr_sess.get_pobject().get_name(show_dbref=target_obj.sees_dbrefs()))
    target_obj.emit_to("--- End Channel Listeners ---")
    
def get_cwho_list(channel_name, return_muted=False):
    """
    Get all users on a channel.

    channel_name: (string) The name of the channel.
    return_muted: (bool)    Return those who have the channel muted if True.
    """
    sess_list = session_mgr.get_session_list()
    return [sess for sess in sess_list if plr_has_channel(sess, channel_name, return_muted)]
    
def load_object_channels(pobject):
    """
    Parse JSON dict of a user's channel list from their CHANLIST attribute.
    """
    membership_list = pobject.channel_membership_set.all()
    for membership in membership_list:
        sessions = session_mgr.sessions_from_object(pobject)
        for session in sessions:
            session.channels_subscribed[membership.user_alias] = [membership.channel.name,
                                                                  membership.is_listening]

def send_cmessage(channel, message, show_header=True):
    """
    Sends a message to all players on the specified channel.

    channel: (string or CommChannel) Name of channel or a CommChannel object.
    message: (string) Message to send.
    show_header: (bool) If False, don't prefix message with the channel header.
    """
    if isinstance(channel, unicode) or isinstance(channel, str):
        # If they've passed a string as the channel argument, look up the
        # correct channel object.
        try:
            channel_obj = get_cobj_from_name(channel)
        except:
            logger.log_errmsg("send_cmessage(): Can't find channel: %s" % channel)
            return
    else:
        # Else, assume that it's a channel object and skip re-querying for
        # the channel.
        channel_obj = channel
        
    if show_header == True:
        message = "%s %s" % (channel_obj.ansi_name, message)
        
    for user in get_cwho_list(channel_obj.name, return_muted=False):
        user.msg(message)
        
    chan_message = CommChannelMessage()
    chan_message.channel = channel_obj
    chan_message.message = message
    chan_message.save()

def get_all_channels():
    """
    Returns all channel objects.
    """
    return CommChannel.objects.all()

def get_cobj_from_name(cname):
    """
    Returns the channel's object when given a name.
    """
    return CommChannel.objects.get(name=cname)

def create_channel(name, owner, description=None):
    """
    Create a new channel. 
    name: (string) Name of the new channel
    owner: (Object) Object that owns the channel
    """
    new_chan = CommChannel()
    new_chan.name = ansi.parse_ansi(name, strip_ansi=True)
    new_chan.ansi_name = "[%s]" % (ansi.parse_ansi(name),)
    new_chan.set_owner(owner)
    new_chan.description = description
    new_chan.save()
    return new_chan

def cname_search(search_text, exact=False):
    """
    Searches for a particular channel name. Returns a QuerySet with the
    results.
    
    exact: (bool) Do an exact (case-insensitive) name match if true.
    """
    if exact:
        return CommChannel.objects.filter(name__iexact=search_text)
    else:
        return CommChannel.objects.filter(name__istartswith=search_text)
