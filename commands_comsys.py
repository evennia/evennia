import settings
import time
import functions_general
import functions_db
import functions_help
import functions_comsys
import defines_global as global_defines
import session_mgr
import ansi
import os
"""
Comsys command module. Pretty much every comsys command should go here for
now.
"""

def cmd_addcom(cdat):
   """
   addcom

   Adds an alias for a channel.
   addcom foo=Bar
   """
   pass

def cmd_allcom(cdat):
   """
   allcom

   Allows the user to universally turn off or on all channels they are on,
   as well as perform a "who" for all channels they are on.
   """
   pass

def cmd_comtitle(cdat):
   """
   comtitle

   Sets a prefix to the user's name on the specified channel.
   """
   pass

def cmd_clearcom(cdat):
   """
   clearcom

   Effectively runs delcom on all channels the user is on.  It will remove their aliases,
   remove them from the channel, and clear any titles they have set.
   """
   pass

def cmd_clist(cdat):
   """
   @clist

   Lists all available channels on the game.
   """
   session = cdat['session']
   session.msg("*** Channel       Owner           Description")
   for chan in functions_comsys.get_all_channels():
   session.msg("--- %s %s" % (chan.get_name(), chan.get_owner().get_name())

def cmd_cdestroy(cdat):
   """
   @cdestroy

   Destroys a channel.
   """
   pass

def cmd_cset(cdat):
   """
   @cset

   Sets various flags on a channel.
   """
   pass

def cmd_cpflags(cdat):
   """
   @cpflags

   Sets various flags on a channel relating to players.
   """
   pass

def cmd_coflags(cdat):
   """
   @coflags

   Sets various flags on a channel relating to objects.
   """
   pass

def cmd_ccharge(cdat):
   """
   @ccharge

   Sets the cost to transmit over a channel.  Default is free.
   """
   pass

def cmd_cboot(cdat):
   """
   @cboot

   Kicks a player or object from the channel.
   """
   pass

def cmd_cemit(cdat):
   """
   @cemit

   Allows the user to send a message over a channel as long as
   they own or control it.  It does not show the user's name.
   """
   pass

def cmd_cwho(cdat):
   """
   @cwho

   Displays the name, status and object type for a given channel.
   Adding /all after the channel name will list disconnected players
   as well.
   """
   pass

def cmd_ccreate(cdat):
   """
   @ccreate

   Creates a new channel with the invoker being the default owner.
   """
   session = cdat['session']
   pobject = session.get_pobject()
   uinput= cdat['uinput']['splitted']
   cname = ' '.join(uinput[1:])

   if cname == '':
      session.msg("You must supply a name!")
   else:
      # Create and set the object up.
      cdat = {"name": cname, "owner": pobject}
      new_chan = functions_comsys.create_channel(cdat)
      session.msg("Channel %s created." % (new_chan.get_name(),))

def cmd_cchown(cdat):
   """
   @cchown

   Changes the owner of a channel.
   """
   pass

def cmd_delcom(cdat):
   """
   delcom

   Removes the specified alias to a channel.  If this is the last alias,
   the user is effectively removed from the channel.
   """
   pass
