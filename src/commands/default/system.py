"""

System commands

"""

import traceback
import os, datetime
import django, twisted

from django.contrib.auth.models import User
from src.server.sessionhandler import SESSIONS
from src.scripts.models import ScriptDB
from src.objects.models import ObjectDB
from src.config.models import ConfigValue
from src.utils import reloads, create, logger, utils, gametime
from src.commands.default.muxcommand import MuxCommand


class CmdReload(MuxCommand):
    """
    Reload the system

    Usage:
      @reload

    This reloads the system modules and
    re-validates all scripts. 
    """
    key = "@reload"
    permissions = "cmd:reload"
    help_category = "System"

    def func(self):
        """
        Reload the system. 
        """        
        caller = self.caller 
        reloads.reload_modules()                 

        max_attempts = 4 
        for attempt in range(max_attempts):            
            # if reload modules take a long time,
            # we might end up in a situation where
            # the subsequent commands fail since they
            # can't find the reloads module (due to it
            # not yet fully loaded). So we retry a few 
            # times before giving up. 
            try:
                reloads.reload_scripts()
                reloads.reload_commands()
                break
            except AttributeError:
                if attempt < max_attempts-1:
                    caller.msg("            Waiting for modules(s) to finish (%s) ..." % attempt)
                else:
                    string =  "            ... The module(s) took too long to reload, "
                    string += "\n            so the remaining reloads where skipped."
                    string += "\n            Re-run @reload again when modules have fully "
                    string += "\n            re-initialized."
                    caller.msg(string)

class CmdPy(MuxCommand):
    """
    Execute a snippet of python code 

    Usage:
      @py <cmd>

    In this limited python environment.

    available_vars: 'self','me'  : caller
                    'here'  : caller.location
                    'obj'   : dummy obj instance
                    'script': dummy script instance
                    'config': dummy conf instance
                    'ObjectDB' : ObjectDB class
                    'ScriptDB' : ScriptDB class
                    'ConfigValue' ConfigValue class
    only two
    variables are defined: 'self'/'me' which refers to one's
    own object, and 'here' which refers to the current
    location. 
    """
    key = "@py"
    aliases = ["!"]
    permissions = "cmd:py"
    help_category = "System"
    
    def func(self):
        "hook function"
        
        caller = self.caller        
        pycode = self.args

        if not pycode:
            string = "Usage: @py <code>"
            caller.msg(string)
            return
        # create temporary test objects for playing with
        script = create.create_script("src.scripts.scripts.DoNothing",
                                      'testscript')
        obj = create.create_object("src.objects.objects.Object",
                                   'testobject')        
        conf = ConfigValue() # used to access conf values
        available_vars = {'self':caller,
                          'me':caller,
                          'here':caller.location,
                          'obj':obj,
                          'script':script,
                          'config':conf,
                          'ObjectDB':ObjectDB,
                          'ScriptDB':ScriptDB,
                          'ConfigValue':ConfigValue}

        caller.msg(">>> %s" % pycode)
        try:
            ret = eval(pycode, {}, available_vars)
            ret = "<<< %s" % str(ret)
        except Exception:
            try:
                exec(pycode, {}, available_vars)
                ret = "<<< Done."
            except Exception:
                errlist = traceback.format_exc().split('\n')
                if len(errlist) > 4:
                    errlist = errlist[4:]
                ret = "\n".join("<<< %s" % line for line in errlist if line)
        caller.msg(ret)
        obj.delete()
        script.delete()

class CmdListScripts(MuxCommand):
    """
    Operate on scripts.

    Usage:
      @scripts[/switches] [<obj or scriptid>]
      
    Switches:
      stop - stops an existing script
      validate - run a validation on the script(s)

    If no switches are given, this command just views all active
    scripts. The argument can be either an object, at which point it
    will be searched for all scripts defined on it, or an script name
    or dbref. For using the /stop switch, a unique script dbref is
    required since whole classes of scripts often have the same name.
    """
    key = "@scripts"
    aliases = "@listscripts"
    permissions = "cmd:listscripts"
    help_category = "System"

    def format_script_list(self, scripts):
        "Takes a list of scripts and formats the output."
        if not scripts:
            return "<No scripts>"

        table = [["id"], ["obj"], ["key"],["intval"],["next"],["rept"], ["db"],["typeclass"],["desc"]]
        for script in scripts:

            table[0].append(script.id)            
            if not hasattr(script, 'obj') or not script.obj:
                table[1].append("<Global>")
            else:
                table[1].append(script.obj.key)            
            table[2].append(script.key)                
            if not hasattr(script, 'interval') or script.interval < 0:
                table[3].append("--")
            else:
                table[3].append("%ss" % script.interval)                
            next = script.time_until_next_repeat()
            if not next:
                table[4].append("--")
            else:
                table[4].append("%ss" % next)

            if not hasattr(script, 'repeats') or not script.repeats:
                table[5].append("--")
            else:
                table[5].append("%ss" % script.repeats)
            if script.persistent:
                table[6].append("*")
            else:
                table[6].append("-")           
            typeclass_path = script.typeclass_path.rsplit('.', 1)
            table[7].append("%s" % typeclass_path[-1])
            table[8].append(script.desc)

        ftable = utils.format_table(table)
        string = ""
        for irow, row in enumerate(ftable):
            if irow == 0:
                srow = "\n" + "".join(row)
                srow = "{w%s{n" % srow.rstrip()
            else:
                srow = "\n" + "{w%s{n" % row[0] + "".join(row[1:])
            string += srow.rstrip()
        return string.strip()

    def func(self):
        "implement method"

        caller = self.caller
        args = self.args
        
        string = ""
        if args:

            # test first if this is a script match
            scripts = ScriptDB.objects.get_all_scripts(key=args)
            if not scripts:
                # try to find an object instead.
                objects = ObjectDB.objects.object_search(caller, 
                                                         args, 
                                                         global_search=True)
                if objects:                    
                    scripts = []
                    for obj in objects:
                        # get all scripts on the object(s)
                        scripts.extend(ScriptDB.objects.get_all_scripts_on_obj(obj))   
        else:
            # we want all scripts.
            scripts = ScriptDB.objects.get_all_scripts()

        if not scripts:
            string = "No scripts found with a key '%s', or on an object named '%s'." % (args, args)
            caller.msg(string)
            return         
            
        if self.switches and self.switches[0] in ('stop', 'del', 'delete'):
            # we want to delete something
            if not scripts:
                string = "No scripts/objects matching '%s'. " % args
                string += "Be more specific."
            elif len(scripts) == 1:
                # we have a unique match! 
                string = "Stopping script '%s'." % scripts[0].key
                scripts[0].stop()
                ScriptDB.objects.validate() #just to be sure all is synced
            else:
                # multiple matches.
                string = "Multiple script matches. Please refine your search:\n"
                string += self.format_script_list(scripts)        
        elif self.switches and self.switches[0] in ("validate", "valid", "val"):
            # run validation on all found scripts
            nr_started, nr_stopped = ScriptDB.objects.validate(scripts=scripts)
            string = "Validated %s scripts. " % ScriptDB.objects.all().count()
            string += "Started %s and stopped %s scripts." % (nr_started, nr_stopped)
        else:
            # No stopping or validation. We just want to view things.
            string = self.format_script_list(scripts)        
        caller.msg(string)



class CmdListObjects(MuxCommand):
    """
    Give a summary of object types in database

    Usage:
      @objects [<nr>]

    Gives statictics on objects in database as well as 
    a list of <nr> latest objects in database. If not 
    given, <nr> defaults to 10.
    """
    key = "@objects"
    aliases = ["@listobjects", "@listobjs"]
    permissions = "cmd:listobjects"
    help_category = "System"

    def func(self):
        "Implement the command"

        caller = self.caller

        if self.args and self.args.isdigit():
            nlim = int(self.args)
        else:
            nlim = 10
        dbtotals = ObjectDB.objects.object_totals()
        #print dbtotals 
        string = "\n{wDatase Object totals:{n"
        table = [["Count"], ["Typeclass"]]
        for path, count in dbtotals.items():            
            table[0].append(count)
            table[1].append(path)
        ftable = utils.format_table(table, 3)
        for irow, row in enumerate(ftable):
            srow = "\n" + "".join(row)
            srow = srow.rstrip()
            if irow == 0:
                srow = "{w%s{n" % srow
            string += srow

        string += "\n\n{wLast %s Objects created:{n" % nlim
        objs = list(ObjectDB.objects.all())[-nlim:]               

        table = [["Created"], ["dbref"], ["name"], ["typeclass"]]
        for i, obj in enumerate(objs):
            table[0].append(utils.datetime_format(obj.date_created))
            table[1].append(obj.dbref)
            table[2].append(obj.key)
            table[3].append(str(obj.typeclass))
        ftable = utils.format_table(table, 5)
        for irow, row in enumerate(ftable):
            srow = "\n" + "".join(row)
            srow = srow.rstrip()
            if irow == 0:
                srow = "{w%s{n" % srow
            string += srow

        caller.msg(string)
           

class CmdService(MuxCommand):
    """
    @service - manage services

    Usage:
      @service[/switch] <service>

    Switches:
      start  - activates a service
      stop   - stops a service
      list   - shows all available services
      
    Service management system. Allows for the listing,
    starting, and stopping of services.
    """

    key = "@service"
    permissions = "cmd:service"
    help_category = "System"

    def func(self):
        "Implement command"
        
        caller = self.caller
        switches = self.switches
        
        if not switches or \
                switches[0] not in ["list","start","stop"]:
            caller.msg("Usage: @service/<start|stop|list> [service]")
            return             
        switch = switches[0]

        # get all services
        sessions = caller.sessions
        if not sessions:             
            return 
        service_collection = sessions[0].server.service_collection

        if switch == "list":
            # Just display the list of installed services and their
            # status, then exit.
            string = "-" * 40
            string += "\nService Listing"     
            
            for service in service_collection.services:
                if service.running:
                    status = 'Running'
                else:
                    status = 'Inactive'
                string += '\n * %s (%s)' % (service.name, status)
            string += "\n" + "-" * 40
            caller.msg(string)
            return

        # Get the service to start / stop
        
        try:
            service = service_collection.getServiceNamed(self.args)
        except Exception:
            string = 'Invalid service name. This command is case-sensitive. ' 
            string += 'See @service/list.'
            caller.msg(string)
            return

        if switch == "stop":
            # Stopping a service gracefully closes it and disconnects
            # any connections (if applicable).

            if not service.running:
                caller.msg('That service is not currently running.')
                return
            # We don't want to kill the main Evennia TCPServer services
            # here. If wanting to kill a listening port, one needs to
            # do it through settings.py and a restart.
            if service.name[:7] == 'Evennia':
                string = "You can not stop Evennia TCPServer services this way."
                string += "\nTo e.g. remove a listening port, change settings file and restart."
                caller.msg(string)
                return        
            #comsys.cemit_mudinfo("%s is *Stopping* the service '%s'." % (sname, service.name)) #TODO!
            service.stopService()
            return

        if switch == "start":
            #Starts a service.
            if service.running:
                caller.msg('That service is already running.')
                return
            #comsys.cemit_mudinfo("%s is *Starting* the service '%s'." % (sname,service.name)) #TODO!
            service.startService()

class CmdShutdown(MuxCommand):

    """
    @shutdown

    Usage:
      @shutdown [announcement]

    Shut the game server down gracefully. 
    """    
    key = "@shutdown"
    permissions = "cmd:shutdown"
    help_category = "System"
    
    def func(self):
        "Define function"
        try:
            session = self.caller.sessions[0]
        except Exception:
            return         
        self.caller.msg('Shutting down server ...')
        announcement = "\nServer is being SHUT DOWN!\n"
        if self.args: 
            announcement += "%s\n" % self.args
        logger.log_infomsg('Server shutdown by %s.' % self.caller.name)
        SESSIONS.announce_all(announcement)          
        SESSIONS.server.shutdown()

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

        elif self.arglist[0] in ["obj", "objects"]:
            caller.execute_cmd("@objects")
        elif self.arglist[0] in ["scr", "scripts"]:
            caller.execute_cmd("@scripts")
        elif self.arglist[0] in ["perm", "perms","permissions"]:
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
 
        all_scripts = ScriptDB.objects.get_all_scripts()
        repeat_scripts = [script for script in all_scripts if script.interval > 0]
        nrepeat_scripts = [script for script in all_scripts if script.interval <= 0]

        string = "\n{wNon-timed scripts:{n -- PID name desc --"
        if not nrepeat_scripts:
            string += "\n <None>"
        for script in nrepeat_scripts:
            string += "\n {w%i{n %s %s" % (script.id, script.key, script.desc)

        string += "\n{wTimed scripts:{n -- PID name [time/interval][repeats] desc --"
        if not repeat_scripts:
            string += "\n <None>"
        for script in repeat_scripts:
            repeats = "[inf] "
            if script.repeats: 
                repeats = "[%i] " % script.repeats            
            time_next = "[inf/inf]"
            if script.time_until_next_repeat() != None:
                time_next = "[%d/%d]" % (script.time_until_next_repeat(), script.interval)
            string += "\n {w%i{n %s %s%s%s" % (script.id, script.key, 
                                           time_next, repeats, script.desc)
        string += "\n{wTotal{n: %d scripts." % len(all_scripts)
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

