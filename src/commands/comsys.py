"""
Comsys command module. Pretty much every comsys command should go here for
now.
"""
import time

from django.conf import settings

import src.comsys
from src import defines_global
from src import ansi
from src.util import functions_general

def cmd_addcom(command):
    """
    addcom

    Adds an alias for a channel.
    addcom foo=Bar
    """
    session = command.session
    pobject = session.get_pobject()

    if not command.command_argument:
        session.msg("You need to specify a channel alias and name.")
        return
    
    eq_args = command.command_argument.split('=', 1)
           
    chan_alias = eq_args[0]
    chan_name = eq_args[1]
    
    if len(eq_args) < 2 or len(chan_name) == 0:
        session.msg("You need to specify a channel name.")
        return

    if chan_alias in session.channels_subscribed:
        session.msg("You are already on that channel.")
        return

    name_matches = src.comsys.cname_search(chan_name, exact=True)

    if name_matches:
        chan_name_parsed = name_matches[0].get_name()
        session.msg("You join %s, with an alias of %s." % \
            (chan_name_parsed, chan_alias))
        src.comsys.plr_set_channel(session, chan_alias, chan_name_parsed, True)

        # Announce the user's joining.
        join_msg = "[%s] %s has joined the channel." % \
            (chan_name_parsed, pobject.get_name(show_dbref=False))
        src.comsys.send_cmessage(chan_name_parsed, join_msg)
    else:
        session.msg("Could not find channel %s." % (chan_name,))

def cmd_delcom(command):
    """
    delcom

    Removes the specified alias to a channel. If this is the last alias,
    the user is effectively removed from the channel.
    """
    session = command.session
    pobject = session.get_pobject()

    if not command.command_argument:
        session.msg("You must specify a channel alias.")
        return

    if command.command_argument not in session.channels_subscribed:
        session.msg("You are not on that channel.")
        return

    chan_name = session.channels_subscribed[command.command_argument][0]
    session.msg("You have left %s." % (chan_name,))
    src.comsys.plr_del_channel(session, command.command_argument)

    # Announce the user's leaving.
    leave_msg = "[%s] %s has left the channel." % \
        (chan_name, pobject.get_name(show_dbref=False))
    src.comsys.send_cmessage(chan_name, leave_msg)

def cmd_comlist(command):
    """
    Lists the channels a user is subscribed to.
    """
    session = command.session

    session.msg("Alias     Channel             Status")
    for chan in session.channels_subscribed:
        if session.channels_subscribed[chan][1]:
            chan_on = "On"
        else:
            chan_on = "Off"
            
        session.msg("%-9.9s %-19.19s %s" %
            (chan, session.channels_subscribed[chan][0], chan_on))
    session.msg("-- End of comlist --")
    
def cmd_allcom(command):
    """
    allcom

    Allows the user to universally turn off or on all channels they are on,
    as well as perform a "who" for all channels they are on.
    """
    # TODO: Implement cmd_allcom
    pass

def cmd_clearcom(command):
    """
    clearcom

    Effectively runs delcom on all channels the user is on.  It will remove their aliases,
    remove them from the channel, and clear any titles they have set.
    """
    # TODO: Implement cmd_clearcom
    pass

def cmd_clist(command):
    """
    @clist

    Lists all available channels on the game.
    """
    session = command.session
    session.msg("** Channel       Owner         Description")
    for chan in src.comsys.get_all_channels():
        session.msg("%s%s %-13.13s %-15.15s   %-45.45s" %
            ('-', '-', chan.get_name(), chan.get_owner().get_name(), 
             'No Description'))
    session.msg("-- End of Channel List --")

def cmd_cdestroy(command):
    """
    @cdestroy

    Destroys a channel.
    """
    session = command.session
    cname = command.command_argument

    if cname == '':
        session.msg("You must supply a name!")
        return

    name_matches = src.comsys.cname_search(cname, exact=True)

    if not name_matches:
        session.msg("Could not find channel %s." % (cname,))
    else:
        is_controlled_by_plr = name_matches[0].controlled_by(pobject)
        if is_controlled_by_plr: 
            session.msg("Channel %s destroyed." % (name_matches[0],))
            name_matches.delete()
        else:
            session.msg("Permission denied.")
            return
        
def cmd_cset(command):
    """
    @cset

    Sets various flags on a channel.
    """
    # TODO: Implement cmd_cset
    pass


def cmd_ccharge(command):
    """
    @ccharge

    Sets the cost to transmit over a channel.  Default is free.
    """
    # TODO: Implement cmd_ccharge
    pass

def cmd_cboot(command):
    """
    @cboot

    Kicks a player or object from the channel.
    """
    # TODO: Implement cmd_cboot
    pass

def cmd_cemit(command):
    """
    @cemit <channel>=<message>
    @cemit/noheader <channel>=<message>
    @cemit/sendername <channel>=<message>

    Allows the user to send a message over a channel as long as
    they own or control it. It does not show the user's name unless they
    provide the /sendername switch.
    """
    session = command.session
    pobject = session.get_pobject()

    if not command.command_argument:
        session.msg("Channel emit what?")
        return

    eq_args = command.command_argument.split('=', 1)
    
    if len(eq_args) != 2:
        session.msg("You must provide a channel name and a message to emit.")
        return
    
    cname = eq_args[0]
    cmessage = eq_args[1]
    
    if len(cname) == 0:
        session.msg("You must provide a channel name to emit to.")
        return
    if len(cmessage) == 0:
        session.msg("You must provide a message to emit.")
        return

    name_matches = src.comsys.cname_search(cname, exact=True)
    if name_matches:
        cname_parsed = name_matches[0].get_name()
    else:
        session.msg("Could not find channel %s." % (cname,))
        return

    if "noheader" in command.command_switches:
        if not pobject.user_has_perm("objects.emit_commchannel"):
            session.msg(defines_global.NOPERMS_MSG)
            return
        final_cmessage = cmessage
    else:
        if "sendername" in command.command_switches:
            if not src.comsys.plr_has_channel(session, cname_parsed, 
                                              return_muted=False):
                session.msg("You must be on %s to do that." % (cname_parsed,))
                return
            final_cmessage = "[%s] %s: %s" % (cname_parsed, 
                                              pobject.get_name(show_dbref=False), 
                                              cmessage)
        else:
            if not pobject.user_has_perm("objects.emit_commchannel"):
                session.msg(defines_global.NOPERMS_MSG)
                return
            final_cmessage = "[%s] %s" % (cname_parsed, cmessage)

    if not "quiet" in command.command_switches:
        session.msg("Sent - %s" % (name_matches[0],))
    src.comsys.send_cmessage(cname_parsed, final_cmessage)

def cmd_cwho(command):
    """
    @cwho

    Displays the name, status and object type for a given channel.
    Adding /all after the channel name will list disconnected players
    as well.
    """
    session = command.session
    pobject = session.get_pobject()

    if not command.command_argument:
        session.msg("You must specify a channel name.")
        return
    
    channel_name = command.command_argument
    
    if channel_name.strip() == '':
        session.msg("You must specify a channel name.")
        return

    name_matches = src.comsys.cname_search(channel_name, exact=True)

    if name_matches:
        # Check to make sure the user has permission to use @cwho.
        is_channel_admin = pobject.user_has_perm("objects.channel_admin")
        is_controlled_by_plr = name_matches[0].controlled_by(pobject)
        
        if is_controlled_by_plr or is_channel_admin:
            src.comsys.msg_cwho(session, channel_name)
        else:
            session.msg("Permission denied.")
            return
    else:
        session.msg("No channel with that name was found.")
        return

def cmd_ccreate(command):
    """
    @ccreate

    Creates a new channel with the invoker being the default owner.
    """
    # TODO: Implement cmd_ccreate
    session = command.session
    pobject = session.get_pobject()

    if not command.command_argument:
        session.msg("You must supply a name!")
        return
    
    if not pobject.user_has_perm("objects.channel_admin"):
        session.msg("Permission denied.")
        return
    
    cname = command.command_argument

    name_matches = src.comsys.cname_search(cname, exact=True)

    if name_matches:
        session.msg("A channel with that name already exists.")
    else:
        # Create and set the object up.
        new_chan = src.comsys.create_channel(cname, pobject)
        session.msg("Channel %s created." % (new_chan.get_name(),))

def cmd_cchown(command):
    """
    @cchown

    Changes the owner of a channel.
    """
    # TODO: Implement cmd_cchown.
    pass
