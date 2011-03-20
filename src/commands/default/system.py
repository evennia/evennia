"""

System commands

"""

import traceback
import os, datetime
import django, twisted

from django.contrib.auth.models import User
from django.conf import settings
from src.server.sessionhandler import SESSIONS
from src.scripts.models import ScriptDB
from src.objects.models import ObjectDB
from src.players.models import PlayerDB
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
    locks = "cmd:perm(reload) or perm(Immortals)"
    help_category = "System"

    def func(self):
        """
        Reload the system. 
        """        
        caller = self.caller 
        reloads.start_reload_loop()

        #reloads.reload_modules()                         
        # max_attempts = 4 
        # for attempt in range(max_attempts):            
        #     # if reload modules take a long time,
        #     # we might end up in a situation where
        #     # the subsequent commands fail since they
        #     # can't find the reloads module (due to it
        #     # not yet fully loaded). So we retry a few 
        #     # times before giving up. 
        #     try:
        #         reloads.reload_scripts()
        #         reloads.reload_commands()
        #         break
        #     except AttributeError:
        #         if attempt < max_attempts-1:
        #             caller.msg("            Waiting for modules(s) to finish (%s) ..." % attempt)
        #         else:
        #             string =  "{r            ... The module(s) took too long to reload, "
        #             string += "\n            so the remaining reloads where skipped."
        #             string += "\n            Re-run @reload again when modules have fully "
        #             string += "\n            re-initialized.{n"
        #             caller.msg(string)

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
    locks = "cmd:perm(py) or perm(Immortals)"
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

class CmdScripts(MuxCommand):
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
    locks = "cmd:perm(listscripts) or perm(Wizards)"
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



class CmdObjects(MuxCommand):
    """
    Give a summary of object types in database

    Usage:
      @objects [<nr>]

    Gives statictics on objects in database as well as 
    a list of <nr> latest objects in database. If not 
    given, <nr> defaults to 10.
    """
    key = "@objects"
    aliases = ["@listobjects", "@listobjs", '@stats', '@db']
    locks = "cmd:perm(listobjects) or perm(Builders)"
    help_category = "System"

    def func(self):
        "Implement the command"

        caller = self.caller

        if self.args and self.args.isdigit():
            nlim = int(self.args)
        else:
            nlim = 10

        string = "\n{wDatabase totals:{n"

        nplayers = PlayerDB.objects.count()
        nobjs = ObjectDB.objects.count()
        base_typeclass = settings.BASE_CHARACTER_TYPECLASS
        nchars = ObjectDB.objects.filter(db_typeclass_path=base_typeclass).count()
        nrooms = ObjectDB.objects.filter(db_location=None).exclude(db_typeclass_path=base_typeclass).count()
        nexits = sum([1 for obj in ObjectDB.objects.filter(db_location=None) if obj.get_attribute('_destination')])

        string += "\n{wPlayers:{n %i" % nplayers     
        string += "\n{wObjects:{n %i" % nobjs
        string += "\n{w Characters (base type):{n %i" % nchars 
        string += "\n{w Rooms (location==None):{n %i" % nrooms
        string += "\n{w Exits (.db._destination!=None):{n %i" % nexits
        string += "\n{w Other:{n %i\n" % (nobjs - nchars - nrooms - nexits)
        
        dbtotals = ObjectDB.objects.object_totals()
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
    locks = "cmd:perm(service) or perm(Immortals)"
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
        service_collection = SESSIONS.server.services

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
    locks = "cmd:perm(shutdown) or perm(Immortals)"
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
    locks = "cmd:perm(time) or perm(Players)"
    help_category = "System"

    def func(self):
        "Show times."

        table = [["Current server uptime:",
                  "Total server running time:",
                  "Total in-game time (realtime x %g):" % (gametime.TIMEFACTOR),
                  "Server time stamp:"
                  ],
                 [utils.time_format(gametime.uptime(format=False), 2),
                  utils.time_format(gametime.runtime(format=False), 2),
                  utils.time_format(gametime.gametime(format=False), 2),
                  datetime.datetime.now()
                  ]]
        if utils.host_os_is('posix'):
            loadavg = os.getloadavg()
            table[0].append("Server load (per minute):")
            table[1].append("{w%g%%{n" % (100 * loadavg[0]))            
        stable = []
        for col in table:
            stable.append([str(val).strip() for val in col])
        ftable = utils.format_table(stable, 5)
        string = ""
        for row in ftable:
            string += "\n " + "{w%s{n" % row[0] + "".join(row[1:])
        self.caller.msg(string)

class CmdServerLoad(MuxCommand):
    """ 
    server load statistics

    Usage:
       @serverload

    Show server load statistics in a table. 
    """
    key = "@serverload"
    locks = "cmd:perm(list) or perm(Immortals)"
    help_category = "System"

    def func(self):
        "Show list."

        caller = self.caller        

        # display active processes

        if not utils.host_os_is('posix'):
            string = "Process listings are only available under Linux/Unix."
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
                                
        caller.msg(string)
            

#TODO - expand @ps as we add irc/imc2 support. 
class CmdPs(MuxCommand):
    """
    list processes
    
    Usage
      @ps 

    Shows the process/event table.
    """
    key = "@ps"
    locks = "cmd:perm(ps) or perm(Builders)"
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


