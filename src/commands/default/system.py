"""

System commands

"""

import traceback
import os, datetime, time
import django, twisted

from django.conf import settings
from src.server.sessionhandler import SESSIONS
from src.scripts.models import ScriptDB
from src.objects.models import ObjectDB
from src.players.models import PlayerDB
from src.utils import logger, utils, gametime
from src.commands.default.muxcommand import MuxCommand

# limit symbol import for API
__all__ = ("CmdReload", "CmdReset", "CmdShutdown", "CmdPy",
           "CmdScripts", "CmdObjects", "CmdService", "CmdVersion",
           "CmdTime", "CmdServerLoad")

class CmdReload(MuxCommand):
    """
    Reload the system

    Usage:
      @reload

    This restarts the server. The Portal is not
    affected. Non-persistent scripts will survive a @reload (use
    @reset to purge) and at_reload() hooks will be called.
    """
    key = "@reload"
    locks = "cmd:perm(reload) or perm(Immortals)"
    help_category = "System"

    def func(self):
        """
        Reload the system.
        """
        SESSIONS.announce_all(" Server restarting ...")
        SESSIONS.server.shutdown(mode='reload')

class CmdReset(MuxCommand):
    """
    Reset and reboot the system

    Usage:
      @reset

    A cold reboot. This works like a mixture of @reload and @shutdown,
    - all shutdown hooks will be called and non-persistent scrips will
    be purged. But the Portal will not be affected and the server will
    automatically restart again.
    """
    key = "@reset"
    aliases = ['@reboot']
    locks = "cmd:perm(reload) or perm(Immortals)"
    help_category = "System"

    def func(self):
        """
        Reload the system.
        """
        SESSIONS.announce_all(" Server restarting ...")
        SESSIONS.server.shutdown(mode='reset')


class CmdShutdown(MuxCommand):

    """
    @shutdown

    Usage:
      @shutdown [announcement]

    Gracefully shut down both Server and Portal.
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
        SESSIONS.portal_shutdown()
        SESSIONS.server.shutdown(mode='shutdown')

class CmdPy(MuxCommand):
    """
    Execute a snippet of python code

    Usage:
      @py <cmd>

    Separate multiple commands by ';'.  A few variables are made
    available for convenience in order to offer access to the system
    (you can import more at execution time).

    Available variables in @py environment:
      self, me                   : caller
      here                       : caller.location
      ev                         : the evennia API
      inherits_from(obj, parent) : check object inheritance

    {rNote: In the wrong hands this command is a severe security risk.
    It should only be accessible by trusted server admins/superusers.{n

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

        # import useful variables
        import ev
        available_vars = {'self':caller,
                          'me':caller,
                          'here':caller.location,
                          'ev':ev,
                          'inherits_from':utils.inherits_from}

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

# helper function. Kept outside so it can be imported and run
# by other commands.

def format_script_list(scripts):
    "Takes a list of scripts and formats the output."
    if not scripts:
        return "<No scripts>"

    table = [["id"], ["obj"], ["key"], ["intval"], ["next"], ["rept"], ["db"], ["typeclass"], ["desc"]]
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
            table[5].append("%s" % script.repeats)
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


class CmdScripts(MuxCommand):
    """
    Operate on scripts.

    Usage:
      @scripts[/switches] [<obj or scriptid>]

    Switches:
      stop - stops an existing script
      kill - kills a script - without running its cleanup hooks
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
                objects = ObjectDB.objects.object_search(args, caller=caller, global_search=True)
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

        if self.switches and self.switches[0] in ('stop', 'del', 'delete', 'kill'):
            # we want to delete something
            if not scripts:
                string = "No scripts/objects matching '%s'. " % args
                string += "Be more specific."
            elif len(scripts) == 1:
                # we have a unique match!
                if 'kill' in self.switches:
                    string = "Killing script '%s'" % scripts[0].key
                    scripts[0].stop(kill=True)
                else:
                    string = "Stopping script '%s'." % scripts[0].key
                    scripts[0].stop()
                #import pdb
                #pdb.set_trace()
                ScriptDB.objects.validate() #just to be sure all is synced
            else:
                # multiple matches.
                string = "Multiple script matches. Please refine your search:\n"
                string += format_script_list(scripts)
        elif self.switches and self.switches[0] in ("validate", "valid", "val"):
            # run validation on all found scripts
            nr_started, nr_stopped = ScriptDB.objects.validate(scripts=scripts)
            string = "Validated %s scripts. " % ScriptDB.objects.all().count()
            string += "Started %s and stopped %s scripts." % (nr_started, nr_stopped)
        else:
            # No stopping or validation. We just want to view things.
            string = format_script_list(scripts)
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
        base_char_typeclass = settings.BASE_CHARACTER_TYPECLASS
        nchars = ObjectDB.objects.filter(db_typeclass_path=base_char_typeclass).count()
        nrooms = ObjectDB.objects.filter(db_location__isnull=True).exclude(db_typeclass_path=base_char_typeclass).count()
        nexits = ObjectDB.objects.filter(db_location__isnull=False, db_destination__isnull=False).count()

        string += "\n{wPlayers:{n %i" % nplayers
        string += "\n{wObjects:{n %i" % nobjs
        string += "\n{w Characters (BASE_CHARACTER_TYPECLASS):{n %i" % nchars
        string += "\n{w Rooms (location==None):{n %i" % nrooms
        string += "\n{w Exits (destination!=None):{n %i" % nexits
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

        string += "\n\n{wLast %s Objects created:{n" % min(nobjs, nlim)
        objs = ObjectDB.objects.all().order_by("db_date_created")[max(0, nobjs - nlim):]

        table = [["Created"], ["dbref"], ["name"], ["typeclass"]]
        for i, obj in enumerate(objs):
            table[0].append(utils.datetime_format(obj.date_created))
            table[1].append(obj.dbref)
            table[2].append(obj.key)
            table[3].append(str(obj.typeclass.path))
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
      list   - shows all available services (default)
      start  - activates a service
      stop   - stops a service

    Service management system. Allows for the listing,
    starting, and stopping of services. If no switches
    are given, services will be listed.
    """

    key = "@service"
    aliases = ["@services"]
    locks = "cmd:perm(service) or perm(Immortals)"
    help_category = "System"

    def func(self):
        "Implement command"

        caller = self.caller
        switches = self.switches

        if switches and switches[0] not in ["list", "start", "stop"]:
            caller.msg("Usage: @service/<start|stop|list> [service]")
            return

        # get all services
        sessions = caller.sessions
        if not sessions:
            return
        service_collection = SESSIONS.server.services

        if not switches or switches[0] == "list":
            # Just display the list of installed services and their
            # status, then exit.
            string = "-" * 78
            string += "\n{wServices{n (use @services/start|stop):"

            for service in service_collection.services:
                if service.running:
                    status = 'Running'
                    string += '\n * {g%s{n (%s)' % (service.name, status)
                else:
                    status = 'Inactive'
                    string += '\n   {R%s{n (%s)' % (service.name, status)
            string += "\n" + "-" * 78
            caller.msg(string)
            return

        # Get the service to start / stop

        try:
            service = service_collection.getServiceNamed(self.args)
        except Exception:
            string = 'Invalid service name. This command is case-sensitive. '
            string += 'See @service/list for valid services.'
            caller.msg(string)
            return

        if switches[0] == "stop":
            # Stopping a service gracefully closes it and disconnects
            # any connections (if applicable).

            if not service.running:
                caller.msg('That service is not currently running.')
                return
            if service.name[:7] == 'Evennia':
                string = "You seem to be shutting down a core Evennia* service. Note that"
                string += "Stopping some TCP port services will *not* disconnect users *already*"
                string += "connected on those ports, but *may* instead cause spurious errors for them. To "
                string += "safely and permanently remove ports, change settings file and restart the server."
                caller.msg(string)

            service.stopService()
            caller.msg("Stopping service '%s'." % self.args)
            return

        if switches[0] == "start":
            #Starts a service.
            if service.running:
                caller.msg('That service is already running.')
                return
            caller.msg("Starting service '%s'." % self.args)
            service.startService()

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
        string = "-" * 50 + "\n\r"
        string += " {cEvennia{n %s\n\r" % version
        string += " (Django %s, " % (django.get_version())
        string += " Twisted %s)\n\r" % (twisted.version.short())
        string += "-" * 50
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
                 [utils.time_format(time.time() - SESSIONS.server.start_time, 3),
                  utils.time_format(gametime.runtime(format=False), 2),
                  utils.time_format(gametime.gametime(format=False), 2),
                  datetime.datetime.now()
                  ]]
        if utils.host_os_is('posix'):
            loadavg = os.getloadavg()
            table[0].append("Server load (per minute):")
            table[1].append("%g" % (loadavg[0]))
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
            pid = os.getpid()
            rmem = float(os.popen('ps -p %d -o %s | tail -1' % (pid, "rss")).read()) / 1024.0
            vmem = float(os.popen('ps -p %d -o %s | tail -1' % (pid, "vsz")).read()) / 1024.0

            rusage = resource.getrusage(resource.RUSAGE_SELF)
            table = [["Server load (1 min):",
                      "Process ID:",
                      "Bytes per page:",
                      "CPU time used:",
                      "Resident memory:",
                      "Virtual memory:",
                      "Page faults:",
                      "Disk I/O:",
                      "Network I/O:",
                      "Context switching:"
                      ],
                     ["%g" % loadavg[0],
                      "%10d" % pid,
                      "%10d " % psize,
                      "%s (%gs)" % (utils.time_format(rusage.ru_utime), rusage.ru_utime),
                      #"%10d shared" % rusage.ru_ixrss,
                      #"%10d pages" % rusage.ru_maxrss,
                      "%10d Mb" % rmem,
                      "%10d Mb" % vmem,
                      "%10d hard" % rusage.ru_majflt,
                      "%10d reads" % rusage.ru_inblock,
                      "%10d in" % rusage.ru_msgrcv,
                      "%10d vol" % rusage.ru_nvcsw
                    ],
                     ["", "", "",
                      "(user: %gs)" % rusage.ru_stime,
                      "", #"%10d private" % rusage.ru_idrss,
                      "", #"%10d bytes" % (rusage.ru_maxrss * psize),
                      "%10d soft" % rusage.ru_minflt,
                      "%10d writes" % rusage.ru_oublock,
                      "%10d out" % rusage.ru_msgsnd,
                      "%10d forced" % rusage.ru_nivcsw
                      ],
                     ["", "", "", "",
                      "", #"%10d stack" % rusage.ru_isrss,
                      "",
                      "%10d swapouts" % rusage.ru_nswap,
                      "", "",
                      "%10d sigs" % rusage.ru_nsignals
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

# class CmdPs(MuxCommand):
#     """
#     list processes

#     Usage
#       @ps

#     Shows the process/event table.
#     """
#     key = "@ps"
#     locks = "cmd:perm(ps) or perm(Builders)"
#     help_category = "System"

#     def func(self):
#         "run the function."

#         nscripts = ScriptDB.objects.count()
#         repeat_scripts = ScriptDB.objects.filter(db_interval__gt=0)
#         nrepeat_scripts = ScriptDB.objects.filter(db_interval__le=0)

#         string = "\n{wNon-timed scripts:{n -- PID name desc --"
#         if not nrepeat_scripts:
#             string += "\n <None>"
#         for script in nrepeat_scripts:
#             string += "\n {w%i{n %s %s" % (script.id, script.key, script.desc)

#         string += "\n{wTimed scripts:{n -- PID name [time/interval][repeats] desc --"
#         if not repeat_scripts:
#             string += "\n <None>"
#         for script in repeat_scripts:
#             repeats = "[inf] "
#             if script.repeats:
#                 repeats = "[%i] " % script.repeats
#             time_next = "[inf/inf]"
#             if script.time_until_next_repeat() != None:
#                 time_next = "[%d/%d]" % (script.time_until_next_repeat(), script.interval)
#             string += "\n {w%i{n %s %s%s%s" % (script.id, script.key,
#                                            time_next, repeats, script.desc)
#         string += "\n{wTotal{n: %d scripts." % len(all_scripts)
#         self.caller.msg(string)


