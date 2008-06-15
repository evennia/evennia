"""
Commands that are generally staff-oriented that show information regarding
the server instance.
"""
import os
import time

from src.util import functions_general

if not functions_general.host_os_is('nt'):
    # Don't import the resource module if the host OS is Windows.
    import resource

import django

from apps.objects.models import Object
from src import scheduler
from src import defines_global

def cmd_version(cdat):
    """
    Version info command.
    """
    session = cdat['session']
    retval = "-"*50 +"\n\r"
    retval += " Evennia %s\n\r" % (defines_global.EVENNIA_VERSION,)
    retval += " Django %s\n\r" % (django.get_version())
    retval += "-"*50
    session.msg(retval)

def cmd_time(cdat):
    """
    Server local time.
    """
    session = cdat['session']
    session.msg('Current server time : %s' % (time.strftime('%a %b %d %H:%M %Y (%Z)', time.localtime(),)))

def cmd_uptime(cdat):
    """
    Server uptime and stats.
    """
    session = cdat['session']
    server = cdat['server']
    start_delta = time.time() - server.start_time
    loadavg = os.getloadavg()
    session.msg('Current server time : %s' % (time.strftime('%a %b %d %H:%M %Y (%Z)', time.localtime(),)))
    session.msg('Server start time   : %s' % (time.strftime('%a %b %d %H:%M %Y', time.localtime(server.start_time),)))
    session.msg('Server uptime       : %s' % functions_general.time_format(start_delta, style=2))
    session.msg('Server load (1 min) : %.2f' % loadavg[0])

def cmd_list(cdat):
    """
    Shows some game related information.
    """
    session = cdat['session']
    pobject = session.get_pobject()
    args = cdat['uinput']['splitted'][1:]
    argstr = ''.join(args)
    
    msg_invalid = "Unknown option. Use one of: commands, flags, process"
    
    if len(argstr) == 0:    
        session.msg(msg_invalid)
    elif argstr == "commands":
        session.msg('Commands: '+ ' '.join(session.server.command_list()))
    elif argstr == "process":
        if not functions_general.host_os_is('nt'):
            loadvg = os.getloadavg()
            psize = resource.getpagesize()
            rusage = resource.getrusage(resource.RUSAGE_SELF)
            session.msg("Process ID:  %10d         %10d bytes per page" % (os.getpid(), psize))
            session.msg("Time used:   %10d user    %10d sys" % (rusage[0],rusage[1]))
            session.msg("Integral mem:%10d shared  %10d private%10d stack" % (rusage[3], rusage[4], rusage[5]))
            session.msg("Max res mem: %10d pages   %10d bytes" % (rusage[2],rusage[2] * psize))
            session.msg("Page faults: %10d hard    %10d soft   %10d swapouts" % (rusage[7], rusage[6], rusage[8]))
            session.msg("Disk I/O:    %10d reads   %10d writes" % (rusage[9], rusage[10]))
            session.msg("Network I/O: %10d in      %10d out" % (rusage[12], rusage[11]))
            session.msg("Context swi: %10d vol     %10d forced %10d sigs" % (rusage[14], rusage[15], rusage[13]))
        else:
            session.msg("Feature not available on Windows.")
            return
    elif argstr == "flags":
        session.msg("Flags: "+" ".join(defines_global.SERVER_FLAGS))
    else:
        session.msg(msg_invalid)

def cmd_ps(cdat):
    """
    Shows the process/event table.
    """
    session = cdat['session']
    session.msg("-- Interval Events --")
    for event in scheduler.schedule:
        session.msg(" [%d/%d] %s" % (scheduler.get_event_nextfire(event),
            scheduler.get_event_interval(event),
            scheduler.get_event_description(event)))
    session.msg("Totals: %d interval events" % (len(scheduler.schedule),))

def cmd_stats(cdat):
    """
    Shows stats about the database.
    4012 objects = 144 rooms, 212 exits, 613 things, 1878 players. (1165 garbage)
    """
    session = cdat['session']
    stats_dict = Object.objects.object_totals()
    session.msg("%d objects = %d rooms, %d exits, %d things, %d players. (%d garbage)" % (stats_dict["objects"],
        stats_dict["rooms"],
        stats_dict["exits"],
        stats_dict["things"],
        stats_dict["players"],
        stats_dict["garbage"]))
