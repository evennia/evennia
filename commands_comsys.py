import os
import time

import settings
import functions_general
import functions_db
import functions_help
import functions_comsys
import defines_global
import session_mgr
import ansi
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
   session = cdat['session']
   pobject = session.get_pobject()
   server = cdat['server']
   args = cdat['uinput']['splitted'][1:]
   
   if len(args) == 0:
      session.msg("You need to specify a channel alias and name.")
      return
      
   eq_args = args[0].split('=')

   if len(eq_args) < 2:
      session.msg("You need to specify a channel name.")
      return
   
   chan_alias = eq_args[0]
   chan_name = eq_args[1]

   if len(chan_name) == 0:
      session.msg("You need to specify a channel name.")
      return

   if chan_alias in session.channels_subscribed:
      session.msg("You are already on that channel.")
      return

   name_matches = functions_comsys.cname_search(chan_name, exact=True)

   if name_matches:
      chan_name_parsed = name_matches[0].get_name()
      session.msg("You join %s, with an alias of %s." % \
         (chan_name_parsed, chan_alias))
      functions_comsys.plr_set_channel(session, chan_alias, chan_name_parsed, True)

      # Announce the user's joining.
      join_msg = "[%s] %s has joined the channel." % \
         (chan_name_parsed, pobject.get_name(show_dbref=False))
      functions_comsys.send_cmessage(chan_name_parsed, join_msg)
   else:
      session.msg("Could not find channel %s." % (chan_name,))

def cmd_delcom(cdat):
   """
   delcom

   Removes the specified alias to a channel. If this is the last alias,
   the user is effectively removed from the channel.
   """
   session = cdat['session']
   pobject = session.get_pobject()
   uinput= cdat['uinput']['splitted']
   chan_alias = ' '.join(uinput[1:])

   if len(chan_alias) == 0:
      session.msg("You must specify a channel alias.")
      return

   if chan_alias not in session.channels_subscribed:
      session.msg("You are not on that channel.")
      return

   chan_name = session.channels_subscribed[chan_alias][0]
   session.msg("You have left %s." % (chan_name,))
   functions_comsys.plr_del_channel(session, chan_alias)

   # Announce the user's leaving.
   leave_msg = "[%s] %s has left the channel." % \
      (chan_name, pobject.get_name(show_dbref=False))
   functions_comsys.send_cmessage(chan_name, leave_msg)

def cmd_comlist(cdat):
   """
   Lists the channels a user is subscribed to.
   """
   session = cdat['session']

   session.msg("Alias     Channel             Status")
   for chan in session.channels_subscribed:
      if session.channels_subscribed[chan][1]:
         chan_on = "On"
      else:
         chan_on = "Off"
         
      session.msg("%-9.9s %-19.19s %s" %
         (chan, session.channels_subscribed[chan][0], chan_on))
   session.msg("-- End of comlist --")
   
def cmd_allcom(cdat):
   """
   allcom

   Allows the user to universally turn off or on all channels they are on,
   as well as perform a "who" for all channels they are on.
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
   session.msg("** Channel       Owner           Description")
   for chan in functions_comsys.get_all_channels():
      session.msg("%s%s %-13.13s %-15.15s %-45.45s" %
         ('-', '-', chan.get_name(), chan.get_owner().get_name(), 'No Description'))
   session.msg("-- End of Channel List --")

def cmd_cdestroy(cdat):
   """
   @cdestroy

   Destroys a channel.
   """
   session = cdat['session']
   uinput= cdat['uinput']['splitted']
   cname = ' '.join(uinput[1:])

   if cname == '':
      session.msg("You must supply a name!")
      return

   name_matches = functions_comsys.cname_search(cname, exact=True)

   if not name_matches:
      session.msg("Could not find channel %s." % (cname,))
   else:
      session.msg("Channel %s destroyed." % (name_matches[0],))
      name_matches.delete()
      
def cmd_cset(cdat):
   """
   @cset

   Sets various flags on a channel.
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
   @cemit/noheader <message>
   @cemit/sendername <message>

   Allows the user to send a message over a channel as long as
   they own or control it. It does not show the user's name unless they
   provide the /sendername switch.
   """
   session = cdat['session']
   pobject = session.get_pobject()
   server = cdat['server']
   args = cdat['uinput']['splitted'][1:]
   switches = cdat['uinput']['root_chunk'][1:]

   if len(args) == 0:
      session.msg("Channel emit what?")
      return

   # Combine the arguments into one string, split it by equal signs into
   # channel (entry 0 in the list), and message (entry 1 and above).
   eq_args = ' '.join(args).split('=')
   cname = eq_args[0]
   cmessage = ' '.join(eq_args[1:])
   if len(eq_args) != 2:
      session.msg("You must provide a channel name and a message to emit.")
      return
   if len(cname) == 0:
      session.msg("You must provide a channel name to emit to.")
      return
   if len(cmessage) == 0:
      session.msg("You must provide a message to emit.")
      return

   name_matches = functions_comsys.cname_search(cname, exact=True)

   try:
      # Safety first, kids!
      cname_parsed = name_matches[0].get_name()
   except:
      session.msg("Could not find channel %s." % (cname,))
      return

   if "noheader" in switches:
      if not pobject.user_has_perm("objects.emit_commchannel"):
         session.msg(defines_global.NOPERMS_MSG)
         return
      final_cmessage = cmessage
   else:
      if "sendername" in switches:
         if not functions_comsys.plr_has_channel(session, cname_parsed, return_muted=False):
            session.msg("You must be on %s to do that." % (cname_parsed,))
            return
         final_cmessage = "[%s] %s: %s" % (cname_parsed, pobject.get_name(show_dbref=False), cmessage)
      else:
         if not pobject.user_has_perm("objects.emit_commchannel"):
            session.msg(defines_global.NOPERMS_MSG)
            return
         final_cmessage = "[%s] %s" % (cname_parsed, cmessage)

   if not "quiet" in switches:
      session.msg("Sent - %s" % (name_matches[0],))
   functions_comsys.send_cmessage(cname_parsed, final_cmessage)

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
      return

   name_matches = functions_comsys.cname_search(cname, exact=True)

   if name_matches:
      session.msg("A channel with that name already exists.")
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
