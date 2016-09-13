"""

System commands

"""
from __future__ import division

import traceback
import os
import datetime
import sys
import django
import twisted
from time import time as timemeasure

from django.conf import settings
from evennia.server.sessionhandler import SESSIONS
from evennia.scripts.models import ScriptDB
from evennia.objects.models import ObjectDB
from evennia.players.models import PlayerDB
from evennia.utils import logger, utils, gametime, create, prettytable
from evennia.utils.evtable import EvTable
from evennia.utils.utils import crop, class_from_module

COMMAND_DEFAULT_CLASS = class_from_module(settings.COMMAND_DEFAULT_CLASS)

# delayed imports
_RESOURCE = None
_IDMAPPER = None

# limit symbol import for API
__all__ = ("CmdReload", "CmdReset", "CmdShutdown", "CmdPy",
           "CmdScripts", "CmdObjects", "CmdService", "CmdAbout",
           "CmdTime", "CmdServerLoad")


class CmdReload(COMMAND_DEFAULT_CLASS):
    """
    reload the server

    Usage:
      @reload [reason]

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
        reason = ""
        if self.args:
            reason = "(Reason: %s) " % self.args.rstrip(".")
        SESSIONS.announce_all(" Server restarting %s..." % reason)
        SESSIONS.server.shutdown(mode='reload')


class CmdReset(COMMAND_DEFAULT_CLASS):
    """
    reset and reboot the server

    Usage:
      @reset

    Notes:
      For normal updating you are recommended to use @reload rather
      than this command. Use @shutdown for a complete stop of
      everything.

    This emulates a cold reboot of the Server component of Evennia.
    The difference to @shutdown is that the Server will auto-reboot
    and that it does not affect the Portal, so no users will be
    disconnected. Contrary to @reload however, all shutdown hooks will
    be called and any non-database saved scripts, ndb-attributes,
    cmdsets etc will be wiped.

    """
    key = "@reset"
    aliases = ['@reboot']
    locks = "cmd:perm(reload) or perm(Immortals)"
    help_category = "System"

    def func(self):
        """
        Reload the system.
        """
        SESSIONS.announce_all(" Server resetting/restarting ...")
        SESSIONS.server.shutdown(mode='reset')


class CmdShutdown(COMMAND_DEFAULT_CLASS):

    """
    stop the server completely

    Usage:
      @shutdown [announcement]

    Gracefully shut down both Server and Portal.
    """
    key = "@shutdown"
    locks = "cmd:perm(shutdown) or perm(Immortals)"
    help_category = "System"

    def func(self):
        "Define function"
        # Only allow shutdown if caller has session
        if not self.caller.sessions.get():
            return
        self.msg('Shutting down server ...')
        announcement = "\nServer is being SHUT DOWN!\n"
        if self.args:
            announcement += "%s\n" % self.args
        logger.log_info('Server shutdown by %s.' % self.caller.name)
        SESSIONS.announce_all(announcement)
        SESSIONS.server.shutdown(mode='shutdown')
        SESSIONS.portal_shutdown()


class CmdPy(COMMAND_DEFAULT_CLASS):
    """
    execute a snippet of python code

    Usage:
      @py <cmd>

    Switch:
      time - output an approximate execution time for <cmd>

    Separate multiple commands by ';'.  A few variables are made
    available for convenience in order to offer access to the system
    (you can import more at execution time).

    Available variables in @py environment:
      self, me                   : caller
      here                       : caller.location
      ev                         : the evennia API
      inherits_from(obj, parent) : check object inheritance

    You can explore The evennia API from inside the game by calling
    evennia.help(), evennia.managers.help() etc.

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
            self.msg(string)
            return

        # check if caller is a player

        # import useful variables
        import evennia
        available_vars = {'self': caller,
                          'me': caller,
                          'here': hasattr(caller, "location") and caller.location or None,
                          'evennia': evennia,
                          'ev': evennia,
                          'inherits_from': utils.inherits_from}

        try:
            self.msg(">>> %s" % pycode, session=self.session, options={"raw":True})
        except TypeError:
            self.msg(">>> %s" % pycode, options={"raw":True})

        mode = "eval"
        try:
            try:
                pycode_compiled = compile(pycode, "", mode)
            except Exception:
                mode = "exec"
                pycode_compiled = compile(pycode, "", mode)

            duration = ""
            if "time" in self.switches:
                t0 = timemeasure()
                ret = eval(pycode_compiled, {}, available_vars)
                t1 = timemeasure()
                duration = " (runtime ~ %.4f ms)" % ((t1 - t0) * 1000)
            else:
                ret = eval(pycode_compiled, {}, available_vars)
            if mode == "eval":
                ret = "%s%s" % (str(ret), duration)
            else:
                ret = " Done (use self.msg() if you want to catch output)%s" % duration
        except Exception:
            errlist = traceback.format_exc().split('\n')
            if len(errlist) > 4:
                errlist = errlist[4:]
            ret = "\n".join("%s" % line for line in errlist if line)

        try:
            self.msg(ret, session=self.session, options={"raw":True})
        except TypeError:
            self.msg(ret, options={"raw":True})


# helper function. Kept outside so it can be imported and run
# by other commands.

def format_script_list(scripts):
    "Takes a list of scripts and formats the output."
    if not scripts:
        return "<No scripts>"

    table = EvTable("{wdbref{n", "{wobj{n", "{wkey{n", "{wintval{n", "{wnext{n",
                    "{wrept{n", "{wdb", "{wtypeclass{n", "{wdesc{n",
                    align='r', border="tablecols")
    for script in scripts:
        nextrep = script.time_until_next_repeat()
        if nextrep is None:
            nextrep = "PAUS" if script.db._paused_time else "--"
        else:
            nextrep = "%ss" % nextrep

        maxrepeat = script.repeats
        if maxrepeat:
            rept = "%i/%i" % (maxrepeat - script.remaining_repeats(), maxrepeat)
        else:
            rept = "-/-"

        table.add_row(script.id,
                      script.obj.key if (hasattr(script, 'obj') and script.obj) else "<Global>",
                      script.key,
                      script.interval if script.interval > 0 else "--",
                      nextrep,
                      rept,
                      "*" if script.persistent else "-",
                      script.typeclass_path.rsplit('.', 1)[-1],
                      crop(script.desc, width=20))
    return "%s" % table


class CmdScripts(COMMAND_DEFAULT_CLASS):
    """
    list and manage all running scripts

    Usage:
      @scripts[/switches] [#dbref, key, script.path or <obj>]

    Switches:
      start - start a script (must supply a script path)
      stop - stops an existing script
      kill - kills a script - without running its cleanup hooks
      validate - run a validation on the script(s)

    If no switches are given, this command just views all active
    scripts. The argument can be either an object, at which point it
    will be searched for all scripts defined on it, or a script name
    or #dbref. For using the /stop switch, a unique script #dbref is
    required since whole classes of scripts often have the same name.

    Use @script for managing commands on objects.
    """
    key = "@scripts"
    aliases = ["@globalscript", "@listscripts"]
    locks = "cmd:perm(listscripts) or perm(Wizards)"
    help_category = "System"

    def func(self):
        "implement method"

        caller = self.caller
        args = self.args

        string = ""
        if args:
            if "start" in self.switches:
                # global script-start mode
                new_script = create.create_script(args)
                if new_script:
                    caller.msg("Global script %s was started successfully." % args)
                else:
                    caller.msg("Global script %s could not start correctly. See logs." % args)
                return

            # test first if this is a script match
            scripts = ScriptDB.objects.get_all_scripts(key=args)
            if not scripts:
                # try to find an object instead.
                objects = ObjectDB.objects.object_search(args)
                if objects:
                    scripts = []
                    for obj in objects:
                        # get all scripts on the object(s)
                        scripts.extend(ScriptDB.objects.get_all_scripts_on_obj(obj))
        else:
            # we want all scripts.
            scripts = ScriptDB.objects.get_all_scripts()
            if not scripts:
                caller.msg("No scripts are running.")
                return

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


class CmdObjects(COMMAND_DEFAULT_CLASS):
    """
    statistics on objects in the database

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

        nobjs = ObjectDB.objects.count()
        base_char_typeclass = settings.BASE_CHARACTER_TYPECLASS
        nchars = ObjectDB.objects.filter(db_typeclass_path=base_char_typeclass).count()
        nrooms = ObjectDB.objects.filter(db_location__isnull=True).exclude(db_typeclass_path=base_char_typeclass).count()
        nexits = ObjectDB.objects.filter(db_location__isnull=False, db_destination__isnull=False).count()
        nother = nobjs - nchars - nrooms - nexits

        nobjs = nobjs or 1 # fix zero-div error with empty database

        # total object sum table
        totaltable = EvTable("{wtype{n", "{wcomment{n", "{wcount{n", "{w%%{n", border="table", align="l")
        totaltable.align = 'l'
        totaltable.add_row("Characters", "(BASE_CHARACTER_TYPECLASS)", nchars, "%.2f" % ((float(nchars) / nobjs) * 100))
        totaltable.add_row("Rooms", "(location=None)", nrooms, "%.2f" % ((float(nrooms) / nobjs) * 100))
        totaltable.add_row("Exits", "(destination!=None)", nexits, "%.2f" % ((float(nexits) / nobjs) * 100))
        totaltable.add_row("Other", "", nother, "%.2f" % ((float(nother) / nobjs) * 100))

        # typeclass table
        typetable = EvTable("{wtypeclass{n", "{wcount{n", "{w%%{n", border="table", align="l")
        typetable.align = 'l'
        dbtotals = ObjectDB.objects.object_totals()
        for path, count in dbtotals.items():
            typetable.add_row(path, count, "%.2f" % ((float(count) / nobjs) * 100))

        # last N table
        objs = ObjectDB.objects.all().order_by("db_date_created")[max(0, nobjs - nlim):]
        latesttable = EvTable("{wcreated{n", "{wdbref{n", "{wname{n", "{wtypeclass{n", align="l", border="table")
        latesttable.align = 'l'
        for obj in objs:
            latesttable.add_row(utils.datetime_format(obj.date_created),
                                obj.dbref, obj.key, obj.path)

        string = "\n{wObject subtype totals (out of %i Objects):{n\n%s" % (nobjs, totaltable)
        string += "\n{wObject typeclass distribution:{n\n%s" % typetable
        string += "\n{wLast %s Objects created:{n\n%s" % (min(nobjs, nlim), latesttable)
        caller.msg(string)


class CmdPlayers(COMMAND_DEFAULT_CLASS):
    """
    list all registered players

    Usage:
      @players [nr]

    Lists statistics about the Players registered with the game.
    It will list the <nr> amount of latest registered players
    If not given, <nr> defaults to 10.
    """
    key = "@players"
    aliases = ["@listplayers"]
    locks = "cmd:perm(listplayers) or perm(Wizards)"
    help_category = "System"

    def func(self):
        "List the players"

        caller = self.caller
        if self.args and self.args.isdigit():
            nlim = int(self.args)
        else:
            nlim = 10

        nplayers = PlayerDB.objects.count()

        # typeclass table
        dbtotals = PlayerDB.objects.object_totals()
        typetable = EvTable("{wtypeclass{n", "{wcount{n", "{w%%{n", border="cells", align="l")
        for path, count in dbtotals.items():
            typetable.add_row(path, count, "%.2f" % ((float(count) / nplayers) * 100))
        # last N table
        plyrs = PlayerDB.objects.all().order_by("db_date_created")[max(0, nplayers - nlim):]
        latesttable = EvTable("{wcreated{n", "{wdbref{n", "{wname{n", "{wtypeclass{n", border="cells", align="l")
        for ply in plyrs:
            latesttable.add_row(utils.datetime_format(ply.date_created), ply.dbref, ply.key, ply.path)

        string = "\n{wPlayer typeclass distribution:{n\n%s" % typetable
        string += "\n{wLast %s Players created:{n\n%s" % (min(nplayers, nlim), latesttable)
        caller.msg(string)


class CmdService(COMMAND_DEFAULT_CLASS):
    """
    manage system services

    Usage:
      @service[/switch] <service>

    Switches:
      list   - shows all available services (default)
      start  - activates or reactivate a service
      stop   - stops/inactivate a service (can often be restarted)
      delete - tries to permanently remove a service

    Service management system. Allows for the listing,
    starting, and stopping of services. If no switches
    are given, services will be listed. Note that to operate on the
    service you have to supply the full (green or red) name as given
    in the list.
    """

    key = "@service"
    aliases = ["@services"]
    locks = "cmd:perm(service) or perm(Immortals)"
    help_category = "System"

    def func(self):
        "Implement command"

        caller = self.caller
        switches = self.switches

        if switches and switches[0] not in ("list", "start", "stop", "delete"):
            caller.msg("Usage: @service/<list|start|stop|delete> [servicename]")
            return

        # get all services
        service_collection = SESSIONS.server.services

        if not switches or switches[0] == "list":
            # Just display the list of installed services and their
            # status, then exit.
            table = prettytable.PrettyTable(["{wService{n (use @services/start|stop|delete)", "{wstatus"])
            table.align = 'l'
            for service in service_collection.services:
                table.add_row([service.name, service.running and "{gRunning" or "{rNot Running"])
            caller.msg(str(table))
            return

        # Get the service to start / stop

        try:
            service = service_collection.getServiceNamed(self.args)
        except Exception:
            string = 'Invalid service name. This command is case-sensitive. '
            string += 'See @service/list for valid service name (enter the full name exactly).'
            caller.msg(string)
            return

        if switches[0] in ("stop", "delete"):
            # Stopping/killing a service gracefully closes it and disconnects
            # any connections (if applicable).

            delmode = switches[0] == "delete"
            if not service.running:
                caller.msg('That service is not currently running.')
                return
            if service.name[:7] == 'Evennia':
                if delmode:
                    caller.msg("You cannot remove a core Evennia service (named 'Evennia***').")
                    return
                string = "You seem to be shutting down a core Evennia service (named 'Evennia***'). Note that"
                string += "stopping some TCP port services will *not* disconnect users *already*"
                string += "connected on those ports, but *may* instead cause spurious errors for them. To "
                string += "safely and permanently remove ports, change settings file and restart the server."
                caller.msg(string)

            if delmode:
                service.stopService()
                service_collection.removeService(service)
                caller.msg("Stopped and removed service '%s'." % self.args)
            else:
                service.stopService()
                caller.msg("Stopped service '%s'." % self.args)
            return

        if switches[0] == "start":
            #Starts a service.
            if service.running:
                caller.msg('That service is already running.')
                return
            caller.msg("Starting service '%s'." % self.args)
            service.startService()


class CmdAbout(COMMAND_DEFAULT_CLASS):
    """
    show Evennia info

    Usage:
      @about

    Display info about the game engine.
    """

    key = "@about"
    aliases = "@version"
    locks = "cmd:all()"
    help_category = "System"

    def func(self):
        "Show the version"

        string = """
         {cEvennia{n %s{n
         MUD/MUX/MU* development system

         {wLicence{n BSD 3-Clause Licence
         {wWeb{n http://www.evennia.com
         {wIrc{n #evennia on FreeNode
         {wForum{n http://www.evennia.com/discussions
         {wMaintainer{n (2010-)   Griatch (griatch AT gmail DOT com)
         {wMaintainer{n (2006-10) Greg Taylor

         {wOS{n %s
         {wPython{n %s
         {wTwisted{n %s
         {wDjango{n %s
        """ % (utils.get_evennia_version(),
               os.name,
               sys.version.split()[0],
               twisted.version.short(),
               django.get_version())
        self.caller.msg(string)


class CmdTime(COMMAND_DEFAULT_CLASS):
    """
    show server time statistics

    Usage:
      @time

    List Server time statistics such as uptime
    and the current time stamp.
    """
    key = "@time"
    aliases = "@uptime"
    locks = "cmd:perm(time) or perm(Players)"
    help_category = "System"

    def func(self):
        "Show server time data in a table."
        table = prettytable.PrettyTable(["{wserver time statistic","{wtime"])
        table.align = 'l'
        table.add_row(["Current server uptime", utils.time_format(gametime.uptime(), 3)])
        table.add_row(["Total server running time", utils.time_format(gametime.runtime(), 2)])
        table.add_row(["Total in-game time (realtime x %g)" % (gametime.TIMEFACTOR), utils.time_format(gametime.gametime(), 2)])
        table.add_row(["Server time stamp", datetime.datetime.now()])
        self.caller.msg(str(table))


class CmdServerLoad(COMMAND_DEFAULT_CLASS):
    """
    show server load and memory statistics

    Usage:
       @server[/mem]

    Switch:
        mem - return only a string of the current memory usage
        flushmem - flush the idmapper cache

    This command shows server load statistics and dynamic memory
    usage. It also allows to flush the cache of accessed database
    objects.

    Some Important statistics in the table:

    {wServer load{n is an average of processor usage. It's usually
    between 0 (no usage) and 1 (100% usage), but may also be
    temporarily higher if your computer has multiple CPU cores.

    The {wResident/Virtual memory{n displays the total memory used by
    the server process.

    Evennia {wcaches{n all retrieved database entities when they are
    loaded by use of the idmapper functionality. This allows Evennia
    to maintain the same instances of an entity and allowing
    non-persistent storage schemes. The total amount of cached objects
    are displayed plus a breakdown of database object types.

    The {wflushmem{n switch allows to flush the object cache. Please
    note that due to how Python's memory management works, releasing
    caches may not show you a lower Residual/Virtual memory footprint,
    the released memory will instead be re-used by the program.

    """
    key = "@server"
    aliases = ["@serverload", "@serverprocess"]
    locks = "cmd:perm(list) or perm(Immortals)"
    help_category = "System"

    def func(self):
        "Show list."

        global _IDMAPPER
        if not _IDMAPPER:
            from evennia.utils.idmapper import models as _IDMAPPER

        if "flushmem" in self.switches:
            # flush the cache
            prev, _ = _IDMAPPER.cache_size()
            nflushed = _IDMAPPER.flush_cache()
            now, _ = _IDMAPPER.cache_size()
            string = "The Idmapper cache freed |w{idmapper}|n database objects.\n" \
                     "The Python garbage collector freed |w{gc}|n Python instances total."
            self.caller.msg(string.format(idmapper=(prev-now), gc=nflushed))
            return

        # display active processes

        os_windows = os.name == "nt"
        pid = os.getpid()

        if os_windows:
            # Windows requires the psutil module to even get paltry
            # statistics like this (it's pretty much worthless,
            # unfortunately, since it's not specific to the process) /rant
            try:
                import psutil
                has_psutil = True
            except ImportError:
                has_psutil = False

            if has_psutil:
                loadavg = psutil.cpu_percent()
                _mem = psutil.virtual_memory()
                rmem = _mem.used  / (1000.0 * 1000)
                pmem = _mem.percent

                if "mem" in self.switches:
                    string = "Total computer memory usage: {w%g{n MB (%g%%)"
                    self.caller.msg(string % (rmem, pmem))
                    return
                # Display table
                loadtable = EvTable("property", "statistic", align="l")
                loadtable.add_row("Total CPU load", "%g %%" % loadavg)
                loadtable.add_row("Total computer memory usage","%g MB (%g%%)" % (rmem, pmem))
                loadtable.add_row("Process ID", "%g" % pid),
            else:
                loadtable = "Not available on Windows without 'psutil' library " \
                            "(install with {wpip install psutil{n)."

        else:
            # Linux / BSD (OSX) - proper pid-based statistics

            global _RESOURCE
            if not _RESOURCE:
                import resource as _RESOURCE

            loadavg = os.getloadavg()[0]
            rmem = float(os.popen('ps -p %d -o %s | tail -1' % (pid, "rss")).read()) / 1000.0  # resident memory
            vmem = float(os.popen('ps -p %d -o %s | tail -1' % (pid, "vsz")).read()) / 1000.0  # virtual memory
            pmem = float(os.popen('ps -p %d -o %s | tail -1' % (pid, "%mem")).read())  # percent of resident memory to total
            rusage = _RESOURCE.getrusage(_RESOURCE.RUSAGE_SELF)

            if "mem" in self.switches:
                string = "Memory usage: RMEM: {w%g{n MB (%g%%), " \
                         " VMEM (res+swap+cache): {w%g{n MB."
                self.caller.msg(string % (rmem, pmem, vmem))
                return

            loadtable = EvTable("property", "statistic", align="l")
            loadtable.add_row("Server load (1 min)", "%g" % loadavg)
            loadtable.add_row("Process ID", "%g" % pid),
            loadtable.add_row("Memory usage","%g MB (%g%%)" % (rmem, pmem))
            loadtable.add_row("Virtual address space", "")
            loadtable.add_row("{x(resident+swap+caching){n", "%g MB" % vmem)
            loadtable.add_row("CPU time used (total)", "%s (%gs)" % (utils.time_format(rusage.ru_utime), rusage.ru_utime))
            loadtable.add_row("CPU time used (user)", "%s (%gs)" % (utils.time_format(rusage.ru_stime), rusage.ru_stime))
            loadtable.add_row("Page faults", "%g hard,  %g soft, %g swapouts" % (rusage.ru_majflt, rusage.ru_minflt, rusage.ru_nswap))
            loadtable.add_row("Disk I/O", "%g reads, %g writes" % (rusage.ru_inblock, rusage.ru_oublock))
            loadtable.add_row("Network I/O", "%g in, %g out" % (rusage.ru_msgrcv, rusage.ru_msgsnd))
            loadtable.add_row("Context switching", "%g vol, %g forced, %g signals" % (rusage.ru_nvcsw, rusage.ru_nivcsw, rusage.ru_nsignals))


        # os-generic

        string = "{wServer CPU and Memory load:{n\n%s" % loadtable

        # object cache count (note that sys.getsiseof is not called so this works for pypy too.
        total_num, cachedict = _IDMAPPER.cache_size()
        sorted_cache = sorted([(key, num) for key, num in cachedict.items() if num > 0],
                                key=lambda tup: tup[1], reverse=True)
        memtable = EvTable("entity name", "number", "idmapper %", align="l")
        for tup in sorted_cache:
            memtable.add_row(tup[0], "%i" % tup[1], "%.2f" % (float(tup[1]) / total_num * 100))

        string += "\n{w Entity idmapper cache:{n %i items\n%s" % (total_num, memtable)

        # return to caller
        self.caller.msg(string)

class CmdTickers(COMMAND_DEFAULT_CLASS):
    """
    View running tickers

    Usage:
      @tickers

    Note: Tickers are created, stopped and manipulated in Python code
    using the TickerHandler. This is merely a convenience function for
    inspecting the current status.

    """
    key = "@tickers"
    help_category = "System"
    locks = "cmd:perm(tickers) or perm(Builders)"

    def func(self):
        from evennia import TICKER_HANDLER
        all_subs = TICKER_HANDLER.all_display()
        if not all_subs:
            self.caller.msg("No tickers are currently active.")
            return
        table = EvTable("interval (s)", "object", "path/methodname", "idstring", "db")
        for sub in all_subs:
            table.add_row(sub[3],
                          "%s%s" % (sub[0] or "[None]", sub[0] and " (#%s)" % (sub[0].id if hasattr(sub[0], "id") else "") or ""),
                          sub[1] if sub[1] else sub[2],
                          sub[4] or "[Unset]",
                          "*" if sub[5] else "-")
        self.caller.msg("|wActive tickers|n:\n" + unicode(table))





