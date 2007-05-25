import cPickle as pickle
import time
import datetime

from apps.objects.models import CommChannel, CommChannelMessage
import session_mgr
import ansi
"""
Comsys functions.
"""

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
      send_cmessage(cname, "%s %s has left the channel." % (cobj.get_header(), 
         session.get_pobject().get_name(show_dbref=False)))

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
      send_cmessage(cname, "%s %s has joined the channel." % (cobj.get_header(), 
         session.get_pobject().get_name(show_dbref=False)))
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
         if cname == chan[0]:
            has_channel = True

            # If channel status is taken into consideration, see if the user
            # has the channel muted or not.
            if return_muted is False and not chan[1]:
               has_channel = False
            break

   return has_channel

def plr_set_channel_listening(session, alias, listening):
   """
   Add a channel to a session's channel list.
   
   session: (SessionProtocol) A reference to the player session.
   alias: (str) The channel alias.
   listening: (bool) A True or False value to determine listening status.
   """
   plr_get_cdict(session).get(alias)[1] = listening
   plr_pickle_channels(session)
   
def plr_set_channel(session, alias, cname, listening):
   """
   Set a channels alias, name, and listening status in one go, or add the
   channel if it doesn't already exist on a user's list.
   
   session: (SessionProtocol) A reference to the player session.
   alias: (str) The channel alias (also the key in the user's cdict)
   cname: (str) Desired channel name to set.
   listening: (bool) A True or False value to determine listening status.
   """
   plr_get_cdict(session)[alias] = [cname, listening]
   plr_pickle_channels(session)

def plr_pickle_channels(session):
   """
   Save the player's channel list to the CHANLIST attribute.
   
   session: (SessionProtocol) A reference to the player session.
   """
   session.get_pobject().set_attribute("CHANLIST", pickle.dumps(plr_get_cdict(session)))

def plr_del_channel(session, alias):
   """
   Remove a channel from a session's channel list.
   
   session: (SessionProtocol) A reference to the player session.
   alias: (str) The channel alias (also the key in the user's cdict)
   """
   del plr_get_cdict(session)[alias]

def msg_chan_hist(session, channel_name):
   """
   Sends a listing of subscribers to a channel given a channel name.
   
   session: (SessionProtocol) A reference to the player session.
   channel_name: (str) The channel's full name.
   """
   cobj = get_cobj_from_name(channel_name)
   hist_list = CommChannelMessage.objects.filter(channel=cobj).order_by('date_sent')[0:20]
   for entry in hist_list:
      delta_days = datetime.datetime.now() - entry.date_sent
      days_elapsed = delta_days.days
      if days_elapsed > 0:
         time_str = entry.date_sent.strftime("%m.%d / %H:%M")
      else:
         time_str = entry.date_sent.strftime("%H:%M")
      session.msg("[%s] %s" % (time_str, entry.message))
   
def msg_cwho(session, channel_name):
   """
   Sends a listing of subscribers to a channel given a channel name.
   
   session: (SessionProtocol) A reference to the player session.
   channel_name: (str) The channel's full name.
   """
   session.msg("--- Users Listening to %s ---" % (channel_name,))
   for plr_sess in get_cwho_list(channel_name):
      session.msg(plr_sess.get_pobject().get_name(show_dbref=False))
   session.msg("--- End Channel Listeners ---")
   
def get_cwho_list(channel_name, return_muted=False):
   """
   Get all users on a channel.

   channel_name: (string) The name of the channel.
   return_muted: (bool)   Return those who have the channel muted if True.
   """
   sess_list = session_mgr.get_session_list()
   result_list = []
   for sess in sess_list:
      if plr_has_channel(sess, channel_name, return_muted):
         result_list.append(sess)

   return result_list

def send_cmessage(channel_name, message):
   """
   Sends a message to all players on the specified channel.

   channel_name: (string) The name of the channel.
   message:      (string) Message to send.
   """
   for user in get_cwho_list(channel_name, return_muted=False):
      user.msg(message)
      
      chan_message = CommChannelMessage()
      
   try:
      chan_message.channel = get_cobj_from_name(channel_name)
   except:
      functions_general.log_errmsg("send_cmessage(): Can't find channel: %s" %(channel_name,))      
      
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

def create_channel(cdat):
   """
   Create a new channel. cdat is a dictionary that contains the following keys.
   REQUIRED KEYS:
    * name: The name of the new channel.
    * owner: The creator of the channel.
   """
   new_chan = CommChannel()
   new_chan.name = ansi.parse_ansi(cdat["name"], strip_ansi=True)
   new_chan.ansi_name = "[%s]" % (ansi.parse_ansi(cdat["name"]),)
   new_chan.set_owner(cdat["owner"])
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
