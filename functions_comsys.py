from apps.objects.models import CommChannel
import session_mgr
import ansi
"""
Comsys functions.
"""

def get_cwho_list(channel_name, return_muted=False):
  """
  Get all users on a channel.

  channel_name: (string) The name of the channel.
  return_muted: (bool)   Return those who have the channel muted if True.
  """
  sess_list = session_mgr.get_session_list()
  result_list = []
  for sess in sess_list:
     if sess.has_user_channel(channel_name, return_muted):
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

def get_all_channels():
   """
   Returns all channel objects.
   """
   return CommChannel.objects.all()

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