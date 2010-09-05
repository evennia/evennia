"""
Commands that are generally staff-oriented that show information regarding
the server instance.
"""
import os, datetime
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
        string += " {cEvennia{n %s\n\r" % version
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

        string1 = "\nCurrent server uptime:             \t"        
        string1 += "{w%s{n" % (utils.time_format(gametime.uptime(format=False), 2))

        string2 =  "\nTotal server running time:        \t"        
        string2 += "{w%s{n" % (utils.time_format(gametime.runtime(format=False), 2))

        string3 = "\nTotal in-game time (realtime x %g):\t" % (gametime.TIMEFACTOR)
        string3 += "{w%s{n" % (utils.time_format(gametime.gametime(format=False), 2))

        string4 = "\nServer time stamp:                 \t"
        string4 += "{w%s{n" % (str(datetime.datetime.now()))
        string5 = ""
        if not utils.host_os_is('nt'):
            # os.getloadavg() is not available on Windows.
            loadavg = os.getloadavg()
            string5 += "\nServer load (per minute):         \t"
            string5 += "{w%g%%{n" % (100 * loadavg[0])
        string = "%s%s%s%s%s" % (string1, string2, string3, string4, string5)
        self.caller.msg(string)

class CmdList(MuxCommand):
    """ 
    @list - list info

    Usage:
      @list <option>

    Options:
      process - list processes
      objects - list objects
      scripts - list scripts
      perms   - list permission keys and groups    

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
            caller.msg("Usage: @list process|objects|scripts|perms")
            return 

        string = ""
        if self.arglist[0] in ["proc","process"]:

            # display active processes

            if utils.host_os_is('nt'):
                string = "Feature not available on Windows."              
            else:
                import resource                                
                loadavg = os.getloadavg()                
                psize = resource.getpagesize()
                rusage = resource.getrusage(resource.RUSAGE_SELF)                                
                table = [["Server load (1 min):", 
                          "Process ID:",
                          "Bytes per page:",
                          "Time used:",
                          "Integral memory:",
                          "Max res memory:",
                          "Page faults:",
                          "Disk I/O:",
                          "Network I/O",
                          "Context switching:"
                          ],
                         ["%g%%" % (100 * loadavg[0]),
                          "%10d" % os.getpid(),
                          "%10d " % psize,
                          "%10d" % rusage[0],
                          "%10d shared" % rusage[3],
                          "%10d pages" % rusage[2],
                          "%10d hard" % rusage[7],
                          "%10d reads" % rusage[9],
                          "%10d in" % rusage[12],
                          "%10d vol" % rusage[14]                          
                        ],
                         ["", "", "", 
                          "(user: %g)" % rusage[1],
                          "%10d private" % rusage[4],
                          "%10d bytes" % (rusage[2] * psize),
                          "%10d soft" % rusage[6],
                          "%10d writes" % rusage[10],
                          "%10d out" % rusage[11],
                          "%10d forced" % rusage[15]
                          ],
                         ["", "", "", "", 
                          "%10d stack" % rusage[5],
                          "", 
                          "%10d swapouts" % rusage[8],
                          "", "",
                          "%10d sigs" % rusage[13]
                        ]                         
                         ]
                stable = []
                for col in table:
                    stable.append([str(val).strip() for val in col])
                ftable = utils.format_table(stable, 5)
                string = ""
                for row in ftable:
                    string += "\n " + "{w%s{n" % row[0] + "".join(row[1:]) 
                                
                # string = "\n Server load (1 min) : %.2f " % loadavg[0]
                # string += "\n Process ID: %10d" % os.getpid()
                # string += "\n Bytes per page: %10d" % psize
                # string += "\n Time used: %10d, user: %g" % (rusage[0], rusage[1]) 
                # string += "\n Integral mem: %10d shared,  %10d, private, %10d stack " % \
                #     (rusage[3], rusage[4], rusage[5])
                # string += "\n Max res mem: %10d pages %10d bytes" % \
                #     (rusage[2],rusage[2] * psize)
                # string += "\n Page faults: %10d hard    %10d soft   %10d swapouts " % \
                #     (rusage[7], rusage[6], rusage[8])
                # string += "\n Disk I/O: %10d reads   %10d writes " % \
                #     (rusage[9], rusage[10])
                # string += "\n Network I/O: %10d in      %10d out " % \
                #     (rusage[12], rusage[11])
                # string += "\n Context swi: %10d vol     %10d forced %10d sigs " % \
                #     (rusage[14], rusage[15], rusage[13])

        elif self.arglist[0] in ["obj","objects"]:
            caller.execute_cmd("@objects")
        elif self.arglist[0] in ["scr","scripts"]:
            caller.execute_cmd("@scripts")
        elif self.arglist[0] in ["perm","perms","permissions"]:
            caller.execute_cmd("@perm/list")
        else:
            string = "'%s' is not a valid option." % self.arglist[0]
        # send info
        caller.msg(string)
            

#TODO - expand @ps as we add irc/imc2 support. 
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
        stats_room = ObjectDB.objects.filter(db_location=None).count()
        # get all players 
        stats_users = User.objects.all().count()

        string = "\n{wNumber of users:{n %i" % stats_users
        string += "\n{wTotal number of objects:{n %i" % stats_allobj
        string += "\n{wNumber of rooms (location==None):{n %i" % stats_room        
        string += "\n (Use @objects for detailed info)"
        self.caller.msg(string)

