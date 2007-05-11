from apps.objects.models import CommChannel
import session_mgr
import commands_privileged
import commands_general
import commands_comsys
import commands_unloggedin
import ansi
"""
Comsys functions.
"""

def set_new_title(channel, player, title):
  pass

def get_com_who(channel, muted=False, disconnected=False):
  """
  Get all users on a channel.

  If muted = True, return users who have it muted as well.
  If disconnected = True, return users who are not connected as well.
  """
  pass

def get_user_channels(player):
  pass

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
   new_chan.header = "[%s]" % (ansi.parse_ansi(cdat["name"]),)
   new_chan.set_owner(cdat["owner"])
   new_chan.save()
   return new_chan