"""
Commands that are generally staff-oriented that show information regarding
the server instance.
"""
import os
import django, twisted
from django.contrib.auth.models import User
from src.objects.models import ObjectDB
from src.scripts.models import ScriptDB
from src.utils import utils 
from src.utils import gametime 
from game.gamesrc.commands.default.muxcommand import MuxCommand
from src.commands import cmdsethandler

class CmdVersion(MuxCommand):
    """
    @version - game version

    Usage:
      @version

    Display the game version info.
    """

    key = "@version"
    help_category = "System"
    
    def func(self):
        "Show the version"
        version = utils.get_evennia_version()
        string = "-"*50 +"\n\r"
        string += " Evennia %s\n\r" % version
        string += " (Django %s, " % (django.get_version())
        string += " Twisted %s)\n\r" % (twisted.version.short())
        string += "-"*50
        self.caller.msg(string)

class CmdTime(MuxCommand):
    """
    @time

    Usage:
      @time 
    
    Server local time.
    """        
    key = "@time"
    aliases = "@uptime"
    permissions = "cmd:time"
    help_category = "System"

    def func(self):
        "Show times."

        string2 = "\nCurrent server uptime:\n %i yrs, %i months, "
        string2 += "%i weeks, %i days, %i hours, %i minutes and %i secs." 
        string2 = string2 %  gametime.uptime(format=True)

        string3 =  "\nTotal running time (gametime x %g):" % (1.0/gametime.TIMEFACTOR)
        string3 += "\n %i yrs, %i months, %i weeks, %i days, "
        string3 += "%i hours, %i minutes and %i secs." 
        string3 = string3 % gametime.runtime(format=True)
        #print "runtime:", gametime.runtime()
        string1 = "\nTotal game time (realtime x %g):" % (gametime.TIMEFACTOR)
        string1 += "\n %i yrs, %i months, %i weeks, %i days, "
        string1 += "%i hours, %i minutes and %i secs." 
        string1 = string1 % (gametime.gametime(format=True))
        #print "gametime:", gametime.gametime()
        string4 = ""
        if not utils.host_os_is('nt'):
            # os.getloadavg() is not available on Windows.
            loadavg = os.getloadavg()
            string4 = "\n Server load (1 min) : %g%%" % (100 * loadavg[0])
        string = "%s%s%s%s" % (string2, string3, string1, string4)
        self.caller.msg(string)

class CmdList(MuxCommand):
    """ 
    @list - list info

    Usage:
      @list commands | process
    
    Shows game related information depending
    on which argument is given. 
    """
    key = "@list"
    permissions = "cmd:list"
    help_category = "System"

    def func(self):
        "Show list."

        caller = self.caller        
        if not self.args:
            caller.msg("Usage: @list commands|process")
            return 

        string = ""
        if self.arglist[0] in ["com", "command", "commands"]:            
            string = "Command sets currently in cache:"
            for cmdset in cmdsethandler.get_cached_cmdsets():
                string += "\n %s" % cmdset
        elif self.arglist[0] in ["proc","process"]:
            if utils.host_os_is('nt'):
                string = "Feature not available on Windows."              
            else:
                import resource                                
                loadavg = os.getloadavg()
                string = "\n Server load (1 min) : %.2f " % loadavg[0]
                psize = resource.getpagesize()
                rusage = resource.getrusage(resource.RUSAGE_SELF)                                
                string += "\n Process ID: %10d" % os.getpid()
                string += "\n Bytes per page: %10d" % psize
                string += "\n Time used: %10d, user: %g" % (rusage[0], rusage[1]) 
                string += "\n Integral mem: %10d shared,  %10d, private, %10d stack " % \
                    (rusage[3], rusage[4], rusage[5])
                string += "\n Max res mem: %10d pages %10d bytes" % \
                    (rusage[2],rusage[2] * psize)
                string += "\n Page faults: %10d hard    %10d soft   %10d swapouts " % \
                    (rusage[7], rusage[6], rusage[8])
                string += "\n Disk I/O: %10d reads   %10d writes " % \
                    (rusage[9], rusage[10])
                string += "\n Network I/O: %10d in      %10d out " % \
                    (rusage[12], rusage[11])
                string += "\n Context swi: %10d vol     %10d forced %10d sigs " % \
                    (rusage[14], rusage[15], rusage[13])
        else:
            string = "Not a valid option."
        # send info
        caller.msg(string)
            
class CmdPs(MuxCommand):
    """
    @ps - list processes
    Usage
      @ps 

    Shows the process/event table.
    """
    key = "@ps"
    permissions = "cmd:ps"
    help_category = "System"

    def func(self):
        "run the function."
 
        string = "Processes Scheduled:\n-- PID [time/interval] [repeats] description --"
        all_scripts = ScriptDB.objects.get_all_scripts()
        repeat_scripts = [script for script in all_scripts if script.interval]
        nrepeat_scripts = [script for script in all_scripts if script not in repeat_scripts]
        
        string = "\nNon-timed scripts:"
        for script in nrepeat_scripts:
            string += "\n %i %s %s" % (script.id, script.key, script.desc)

        string += "\n\nTimed scripts:"
        for script in repeat_scripts:
            repeats = "[inf] "
            if script.repeats: 
                repeats = "[%i] " % script.repeats            
            string += "\n %i %s [%d/%d] %s%s" % (script.id, script.key, 
                                                 script.time_until_next_repeat(),
                                                 script.interval,
                                                 repeats,
                                                 script.desc)
        string += "\nTotals: %d interval scripts" % len(all_scripts)
        self.caller.msg(string)

class CmdStats(MuxCommand):
    """
    @stats - show object stats

    Usage:
      @stats

    Shows stats about the database.
    """
    
    key = "@stats"   
    aliases = "@db"
    permissions = "cmd:stats"
    help_category = "System"

    def func(self):
        "Show all stats"

        # get counts for all typeclasses 
        stats_dict = ObjectDB.objects.object_totals()
        # get all objects
        stats_allobj = ObjectDB.objects.all().count()
        # get all rooms 
        stats_room = ObjectDB.objects.filter(obj_location=None).count()
        # get all players 
        stats_users = User.objects.all().count()

        string = "-"*60
        string += "\n Number of users: %i" % stats_users
        string += "\n Total number of objects: %i" % stats_allobj
        string += "\n Number of rooms (location==None): %i" % stats_room        
        string += "\n Object type statistics:"
        for path, num in stats_dict.items():
            string += "\n %i - %s" % (num, path) 
        self.caller.msg(string)
