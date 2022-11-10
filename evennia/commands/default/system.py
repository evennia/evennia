"""

System commands

"""


import code
import datetime
import os
import sys
import time
import traceback

import django
import twisted
from django.conf import settings

from evennia.accounts.models import AccountDB
from evennia.scripts.taskhandler import TaskHandlerTask
from evennia.server.sessionhandler import SESSIONS
from evennia.utils import gametime, logger, search, utils
from evennia.utils.eveditor import EvEditor
from evennia.utils.evmenu import ask_yes_no
from evennia.utils.evtable import EvTable
from evennia.utils.utils import class_from_module, iter_to_str

COMMAND_DEFAULT_CLASS = class_from_module(settings.COMMAND_DEFAULT_CLASS)
_TASK_HANDLER = None
_BROADCAST_SERVER_RESTART_MESSAGES = settings.BROADCAST_SERVER_RESTART_MESSAGES

# delayed imports
_RESOURCE = None
_IDMAPPER = None

# limit symbol import for API
__all__ = (
    "CmdAccounts",
    "CmdReload",
    "CmdReset",
    "CmdShutdown",
    "CmdPy",
    "CmdService",
    "CmdAbout",
    "CmdTime",
    "CmdServerLoad",
    "CmdTasks",
    "CmdTickers",
)


class CmdReload(COMMAND_DEFAULT_CLASS):
    """
    reload the server

    Usage:
      reload [reason]

    This restarts the server. The Portal is not
    affected. Non-persistent scripts will survive a reload (use
    reset to purge) and at_reload() hooks will be called.
    """

    key = "@reload"
    aliases = ["@restart"]
    locks = "cmd:perm(reload) or perm(Developer)"
    help_category = "System"

    def func(self):
        """
        Reload the system.
        """
        reason = ""
        if self.args:
            reason = "(Reason: %s) " % self.args.rstrip(".")
        if _BROADCAST_SERVER_RESTART_MESSAGES:
            SESSIONS.announce_all(f" Server restart initiated {reason}...")
        SESSIONS.portal_restart_server()


class CmdReset(COMMAND_DEFAULT_CLASS):
    """
    reset and reboot the server

    Usage:
      reset

    Notes:
      For normal updating you are recommended to use reload rather
      than this command. Use shutdown for a complete stop of
      everything.

    This emulates a cold reboot of the Server component of Evennia.
    The difference to shutdown is that the Server will auto-reboot
    and that it does not affect the Portal, so no users will be
    disconnected. Contrary to reload however, all shutdown hooks will
    be called and any non-database saved scripts, ndb-attributes,
    cmdsets etc will be wiped.

    """

    key = "@reset"
    aliases = ["@reboot"]
    locks = "cmd:perm(reload) or perm(Developer)"
    help_category = "System"

    def func(self):
        """
        Reload the system.
        """
        SESSIONS.announce_all(" Server resetting/restarting ...")
        SESSIONS.portal_reset_server()


class CmdShutdown(COMMAND_DEFAULT_CLASS):

    """
    stop the server completely

    Usage:
      shutdown [announcement]

    Gracefully shut down both Server and Portal.
    """

    key = "@shutdown"
    locks = "cmd:perm(shutdown) or perm(Developer)"
    help_category = "System"

    def func(self):
        """Define function"""
        # Only allow shutdown if caller has session
        if not self.caller.sessions.get():
            return
        self.msg("Shutting down server ...")
        announcement = "\nServer is being SHUT DOWN!\n"
        if self.args:
            announcement += "%s\n" % self.args
        logger.log_info(f"Server shutdown by {self.caller.name}.")
        SESSIONS.announce_all(announcement)
        SESSIONS.portal_shutdown()


def _py_load(caller):
    return ""


def _py_code(caller, buf):
    """
    Execute the buffer.
    """
    measure_time = caller.db._py_measure_time
    client_raw = caller.db._py_clientraw
    string = "Executing code%s ..." % (" (measure timing)" if measure_time else "")
    caller.msg(string)
    _run_code_snippet(
        caller, buf, mode="exec", measure_time=measure_time, client_raw=client_raw, show_input=False
    )
    return True


def _py_quit(caller):
    del caller.db._py_measure_time
    caller.msg("Exited the code editor.")


def _run_code_snippet(
    caller, pycode, mode="eval", measure_time=False, client_raw=False, show_input=True
):
    """
    Run code and try to display information to the caller.

    Args:
        caller (Object): The caller.
        pycode (str): The Python code to run.
        measure_time (bool, optional): Should we measure the time of execution?
        client_raw (bool, optional): Should we turn off all client-specific escaping?
        show_input (bookl, optional): Should we display the input?

    """
    # Try to retrieve the session
    session = caller
    if hasattr(caller, "sessions"):
        sessions = caller.sessions.all()

    available_vars = evennia_local_vars(caller)

    if show_input:
        for session in sessions:
            try:
                caller.msg(">>> %s" % pycode, session=session, options={"raw": True})
            except TypeError:
                caller.msg(">>> %s" % pycode, options={"raw": True})

    try:
        # reroute standard output to game client console
        old_stdout = sys.stdout
        old_stderr = sys.stderr

        class FakeStd:
            def __init__(self, caller):
                self.caller = caller

            def write(self, string):
                if string.endswith("\n"):
                    self.caller.msg(string[:-1])
                else:
                    self.caller.msg(string)

        fake_std = FakeStd(caller)
        sys.stdout = fake_std
        sys.stderr = fake_std

        try:
            pycode_compiled = compile(pycode, "", mode)
        except Exception:
            mode = "exec"
            pycode_compiled = compile(pycode, "", mode)

        duration = ""
        if measure_time:
            t0 = time.time()
            ret = eval(pycode_compiled, {}, available_vars)
            t1 = time.time()
            duration = " (runtime ~ %.4f ms)" % ((t1 - t0) * 1000)
            caller.msg(duration)
        else:
            ret = eval(pycode_compiled, {}, available_vars)

    except Exception:
        errlist = traceback.format_exc().split("\n")
        if len(errlist) > 4:
            errlist = errlist[4:]
        ret = "\n".join("%s" % line for line in errlist if line)
    finally:
        # return to old stdout
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    if ret is None:
        return
    elif isinstance(ret, tuple):
        # we must convert here to allow msg to pass it (a tuple is confused
        # with a outputfunc structure)
        ret = str(ret)

    for session in sessions:
        try:
            caller.msg(ret, session=session, options={"raw": True, "client_raw": client_raw})
        except TypeError:
            caller.msg(ret, options={"raw": True, "client_raw": client_raw})


def evennia_local_vars(caller):
    """Return Evennia local variables usable in the py command as a dictionary."""
    import evennia

    return {
        "self": caller,
        "me": caller,
        "here": getattr(caller, "location", None),
        "evennia": evennia,
        "ev": evennia,
        "inherits_from": utils.inherits_from,
    }


class EvenniaPythonConsole(code.InteractiveConsole):

    """Evennia wrapper around a Python interactive console."""

    def __init__(self, caller):
        super().__init__(evennia_local_vars(caller))
        self.caller = caller

    def write(self, string):
        """Don't send to stderr, send to self.caller."""
        self.caller.msg(string)

    def push(self, line):
        """Push some code, whether complete or not."""
        old_stdout = sys.stdout
        old_stderr = sys.stderr

        class FakeStd:
            def __init__(self, caller):
                self.caller = caller

            def write(self, string):
                self.caller.msg(string.split("\n", 1)[0])

        fake_std = FakeStd(self.caller)
        sys.stdout = fake_std
        sys.stderr = fake_std
        result = None
        try:
            result = super().push(line)
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
        return result


class CmdPy(COMMAND_DEFAULT_CLASS):
    """
    execute a snippet of python code

    Usage:
      py [cmd]
      py/edit
      py/time <cmd>
      py/clientraw <cmd>
      py/noecho

    Switches:
      time - output an approximate execution time for <cmd>
      edit - open a code editor for multi-line code experimentation
      clientraw - turn off all client-specific escaping. Note that this may
        lead to different output depending on prototocol (such as angular brackets
        being parsed as HTML in the webclient but not in telnet clients)
      noecho - in Python console mode, turn off the input echo (e.g. if your client
        does this for you already)

    Without argument, open a Python console in-game. This is a full console,
    accepting multi-line Python code for testing and debugging. Type `exit()` to
    return to the game. If Evennia is reloaded, the console will be closed.

    Enter a line of instruction after the 'py' command to execute it
    immediately.  Separate multiple commands by ';' or open the code editor
    using the /edit switch (all lines added in editor will be executed
    immediately when closing or using the execute command in the editor).

    A few variables are made available for convenience in order to offer access
    to the system (you can import more at execution time).

    Available variables in py environment:
      self, me                   : caller
      here                       : caller.location
      evennia                    : the evennia API
      inherits_from(obj, parent) : check object inheritance

    You can explore The evennia API from inside the game by calling
    the `__doc__` property on entities:
        py evennia.__doc__
        py evennia.managers.__doc__

    |rNote: In the wrong hands this command is a severe security risk.  It
    should only be accessible by trusted server admins/superusers.|n

    """

    key = "@py"
    aliases = ["@!"]
    switch_options = ("time", "edit", "clientraw", "noecho")
    locks = "cmd:perm(py) or perm(Developer)"
    help_category = "System"
    arg_regex = ""

    def func(self):
        """hook function"""

        caller = self.caller
        pycode = self.args

        noecho = "noecho" in self.switches

        if "edit" in self.switches:
            caller.db._py_measure_time = "time" in self.switches
            caller.db._py_clientraw = "clientraw" in self.switches
            EvEditor(
                self.caller,
                loadfunc=_py_load,
                savefunc=_py_code,
                quitfunc=_py_quit,
                key="Python exec: :w  or :!",
                persistent=True,
                codefunc=_py_code,
            )
            return

        if not pycode:
            # Run in interactive mode
            console = EvenniaPythonConsole(self.caller)
            banner = (
                "|gEvennia Interactive Python mode{echomode}\n"
                "Python {version} on {platform}".format(
                    echomode=" (no echoing of prompts)" if noecho else "",
                    version=sys.version,
                    platform=sys.platform,
                )
            )
            self.msg(banner)
            line = ""
            main_prompt = "|x[py mode - quit() to exit]|n"
            prompt = main_prompt
            while line.lower() not in ("exit", "exit()"):
                try:
                    line = yield (prompt)
                    if noecho:
                        prompt = "..." if console.push(line) else main_prompt
                    else:
                        if line:
                            self.caller.msg(f">>> {line}")
                        prompt = line if console.push(line) else main_prompt
                except SystemExit:
                    break
            self.msg("|gClosing the Python console.|n")
            return

        _run_code_snippet(
            caller,
            self.args,
            measure_time="time" in self.switches,
            client_raw="clientraw" in self.switches,
        )


class CmdAccounts(COMMAND_DEFAULT_CLASS):
    """
    Manage registered accounts

    Usage:
      accounts [nr]
      accounts/delete <name or #id> [: reason]

    Switches:
      delete    - delete an account from the server

    By default, lists statistics about the Accounts registered with the game.
    It will list the <nr> amount of latest registered accounts
    If not given, <nr> defaults to 10.
    """

    key = "@accounts"
    aliases = ["@account"]
    switch_options = ("delete",)
    locks = "cmd:perm(listaccounts) or perm(Admin)"
    help_category = "System"

    def func(self):
        """List the accounts"""

        caller = self.caller
        args = self.args

        if "delete" in self.switches:
            account = getattr(caller, "account")
            if not account or not account.check_permstring("Developer"):
                caller.msg("You are not allowed to delete accounts.")
                return
            if not args:
                caller.msg("Usage: accounts/delete <name or #id> [: reason]")
                return
            reason = ""
            if ":" in args:
                args, reason = [arg.strip() for arg in args.split(":", 1)]
            # We use account_search since we want to be sure to find also accounts
            # that lack characters.
            accounts = search.account_search(args)
            if not accounts:
                self.msg("Could not find an account by that name.")
                return
            if len(accounts) > 1:
                string = "There were multiple matches:\n"
                string += "\n".join(" %s %s" % (account.id, account.key) for account in accounts)
                self.msg(string)
                return
            account = accounts.first()
            if not account.access(caller, "delete"):
                self.msg("You don't have the permissions to delete that account.")
                return
            username = account.username
            # ask for confirmation
            confirm = (
                "It is often better to block access to an account rather than to delete it. "
                "|yAre you sure you want to permanently delete "
                "account '|n{}|y'|n yes/[no]?".format(username)
            )
            answer = yield (confirm)
            if answer.lower() not in ("y", "yes"):
                caller.msg("Canceled deletion.")
                return

            # Boot the account then delete it.
            self.msg("Informing and disconnecting account ...")
            string = f"\nYour account '{username}' is being *permanently* deleted.\n"
            if reason:
                string += " Reason given:\n  '%s'" % reason
            account.msg(string)
            logger.log_sec(
                f"Account Deleted: {account} (Reason: {reason}, Caller: {caller}, IP:"
                f" {self.session.address})."
            )
            account.delete()
            self.msg("Account %s was successfully deleted." % username)
            return

        # No switches, default to displaying a list of accounts.
        if self.args and self.args.isdigit():
            nlim = int(self.args)
        else:
            nlim = 10

        naccounts = AccountDB.objects.count()

        # typeclass table
        dbtotals = AccountDB.objects.object_totals()
        typetable = self.styled_table(
            "|wtypeclass|n", "|wcount|n", "|w%%|n", border="cells", align="l"
        )
        for path, count in dbtotals.items():
            typetable.add_row(path, count, "%.2f" % ((float(count) / naccounts) * 100))
        # last N table
        plyrs = AccountDB.objects.all().order_by("db_date_created")[max(0, naccounts - nlim) :]
        latesttable = self.styled_table(
            "|wcreated|n", "|wdbref|n", "|wname|n", "|wtypeclass|n", border="cells", align="l"
        )
        for ply in plyrs:
            latesttable.add_row(
                utils.datetime_format(ply.date_created), ply.dbref, ply.key, ply.path
            )

        string = f"\n|wAccount typeclass distribution:|n\n{typetable}"
        string += f"\n|wLast {min(naccounts, nlim)} Accounts created:|n\n{latesttable}"
        caller.msg(string)


class CmdService(COMMAND_DEFAULT_CLASS):
    """
    manage system services

    Usage:
      service[/switch] <service>

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
    switch_options = ("list", "start", "stop", "delete")
    locks = "cmd:perm(service) or perm(Developer)"
    help_category = "System"

    def func(self):
        """Implement command"""

        caller = self.caller
        switches = self.switches

        if switches and switches[0] not in ("list", "start", "stop", "delete"):
            caller.msg("Usage: service/<list|start|stop|delete> [servicename]")
            return

        # get all services
        service_collection = SESSIONS.server.services

        if not switches or switches[0] == "list":
            # Just display the list of installed services and their
            # status, then exit.
            table = self.styled_table(
                "|wService|n (use services/start|stop|delete)", "|wstatus", align="l"
            )
            for service in service_collection.services:
                table.add_row(service.name, service.running and "|gRunning" or "|rNot Running")
            caller.msg(str(table))
            return

        # Get the service to start / stop

        try:
            service = service_collection.getServiceNamed(self.args)
        except Exception:
            string = "Invalid service name. This command is case-sensitive. "
            string += "See service/list for valid service name (enter the full name exactly)."
            caller.msg(string)
            return

        if switches[0] in ("stop", "delete"):
            # Stopping/killing a service gracefully closes it and disconnects
            # any connections (if applicable).

            delmode = switches[0] == "delete"
            if not service.running:
                caller.msg("That service is not currently running.")
                return
            if service.name[:7] == "Evennia":
                if delmode:
                    caller.msg("You cannot remove a core Evennia service (named 'Evennia*').")
                    return
                string = (
                    "|RYou seem to be shutting down a core Evennia "
                    "service (named 'Evennia*').\nNote that stopping "
                    "some TCP port services will *not* disconnect users "
                    "*already* connected on those ports, but *may* "
                    "instead cause spurious errors for them.\nTo safely "
                    "and permanently remove ports, change settings file "
                    "and restart the server.|n\n"
                )
                caller.msg(string)

            if delmode:
                service.stopService()
                service_collection.removeService(service)
                caller.msg(f"|gStopped and removed service '{self.args}'.|n")
            else:
                caller.msg(f"Stopping service '{self.args}'...")
                try:
                    service.stopService()
                except Exception as err:
                    caller.msg(
                        f"|rErrors were reported when stopping this service{err}.\n"
                        "If there are remaining problems, try reloading "
                        "or rebooting the server."
                    )
                caller.msg(f"|g... Stopped service '{self.args}'.|n")
            return

        if switches[0] == "start":
            # Attempt to start a service.
            if service.running:
                caller.msg("That service is already running.")
                return
            caller.msg(f"Beginner-Tutorial service '{self.args}' ...")
            try:
                service.startService()
            except Exception as err:
                caller.msg(
                    f"|rErrors were reported when starting this service{err}.\n"
                    "If there are remaining problems, try reloading the server, changing the "
                    "settings if it's a non-standard service.|n"
                )
            caller.msg("|gService started.|n")


class CmdAbout(COMMAND_DEFAULT_CLASS):
    """
    show Evennia info

    Usage:
      about

    Display info about the game engine.
    """

    key = "@about"
    aliases = "@version"
    locks = "cmd:all()"
    help_category = "System"

    def func(self):
        """Display information about server or target"""

        string = """
         |cEvennia|n MU* development system

         |wEvennia version|n: {version}
         |wOS|n: {os}
         |wPython|n: {python}
         |wTwisted|n: {twisted}
         |wDjango|n: {django}

         |wHomepage|n https://evennia.com
         |wCode|n https://github.com/evennia/evennia
         |wDemo|n https://demo.evennia.com
         |wGame listing|n https://games.evennia.com
         |wChat|n https://discord.gg/AJJpcRUhtF
         |wForum|n https://github.com/evennia/evennia/discussions
         |wLicence|n https://opensource.org/licenses/BSD-3-Clause
         |wMaintainer|n (2010-)   Griatch (griatch AT gmail DOT com)
         |wMaintainer|n (2006-10) Greg Taylor

        """.format(
            version=utils.get_evennia_version(),
            os=os.name,
            python=sys.version.split()[0],
            twisted=twisted.version.short(),
            django=django.get_version(),
        )
        self.caller.msg(string)


class CmdTime(COMMAND_DEFAULT_CLASS):
    """
    show server time statistics

    Usage:
      time

    List Server time statistics such as uptime
    and the current time stamp.
    """

    key = "@time"
    aliases = "@uptime"
    locks = "cmd:perm(time) or perm(Player)"
    help_category = "System"

    def func(self):
        """Show server time data in a table."""
        table1 = self.styled_table("|wServer time", "", align="l", width=78)
        table1.add_row("Current uptime", utils.time_format(gametime.uptime(), 3))
        table1.add_row("Portal uptime", utils.time_format(gametime.portal_uptime(), 3))
        table1.add_row("Total runtime", utils.time_format(gametime.runtime(), 2))
        table1.add_row("First start", datetime.datetime.fromtimestamp(gametime.server_epoch()))
        table1.add_row("Current time", datetime.datetime.now())
        table1.reformat_column(0, width=30)
        table2 = self.styled_table(
            "|wIn-Game time",
            "|wReal time x %g" % gametime.TIMEFACTOR,
            align="l",
            width=78,
            border_top=0,
        )
        epochtxt = "Epoch (%s)" % ("from settings" if settings.TIME_GAME_EPOCH else "server start")
        table2.add_row(epochtxt, datetime.datetime.fromtimestamp(gametime.game_epoch()))
        table2.add_row("Total time passed:", utils.time_format(gametime.gametime(), 2))
        table2.add_row(
            "Current time ", datetime.datetime.fromtimestamp(gametime.gametime(absolute=True))
        )
        table2.reformat_column(0, width=30)
        self.caller.msg(str(table1) + "\n" + str(table2))


class CmdServerLoad(COMMAND_DEFAULT_CLASS):
    """
    show server load and memory statistics

    Usage:
       server[/mem]

    Switches:
        mem - return only a string of the current memory usage
        flushmem - flush the idmapper cache

    This command shows server load statistics and dynamic memory
    usage. It also allows to flush the cache of accessed database
    objects.

    Some Important statistics in the table:

    |wServer load|n is an average of processor usage. It's usually
    between 0 (no usage) and 1 (100% usage), but may also be
    temporarily higher if your computer has multiple CPU cores.

    The |wResident/Virtual memory|n displays the total memory used by
    the server process.

    Evennia |wcaches|n all retrieved database entities when they are
    loaded by use of the idmapper functionality. This allows Evennia
    to maintain the same instances of an entity and allowing
    non-persistent storage schemes. The total amount of cached objects
    are displayed plus a breakdown of database object types.

    The |wflushmem|n switch allows to flush the object cache. Please
    note that due to how Python's memory management works, releasing
    caches may not show you a lower Residual/Virtual memory footprint,
    the released memory will instead be re-used by the program.

    """

    key = "@server"
    aliases = ["@serverload"]
    switch_options = ("mem", "flushmem")
    locks = "cmd:perm(list) or perm(Developer)"
    help_category = "System"

    def func(self):
        """Show list."""

        global _IDMAPPER
        if not _IDMAPPER:
            from evennia.utils.idmapper import models as _IDMAPPER

        if "flushmem" in self.switches:
            # flush the cache
            prev, _ = _IDMAPPER.cache_size()
            nflushed = _IDMAPPER.flush_cache()
            now, _ = _IDMAPPER.cache_size()
            string = (
                "The Idmapper cache freed |w{idmapper}|n database objects.\n"
                "The Python garbage collector freed |w{gc}|n Python instances total."
            )
            self.caller.msg(string.format(idmapper=(prev - now), gc=nflushed))
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
                rmem = _mem.used / (1000.0 * 1000)
                pmem = _mem.percent

                if "mem" in self.switches:
                    string = "Total computer memory usage: |w%g|n MB (%g%%)"
                    self.caller.msg(string % (rmem, pmem))
                    return
                # Display table
                loadtable = self.styled_table("property", "statistic", align="l")
                loadtable.add_row("Total CPU load", "%g %%" % loadavg)
                loadtable.add_row("Total computer memory usage", "%g MB (%g%%)" % (rmem, pmem))
                loadtable.add_row("Process ID", "%g" % pid),
            else:
                loadtable = (
                    "Not available on Windows without 'psutil' library "
                    "(install with |wpip install psutil|n)."
                )

        else:
            # Linux / BSD (OSX) - proper pid-based statistics

            global _RESOURCE
            if not _RESOURCE:
                import resource as _RESOURCE

            loadavg = os.getloadavg()[0]
            rmem = (
                float(os.popen("ps -p %d -o %s | tail -1" % (pid, "rss")).read()) / 1000.0
            )  # resident memory
            vmem = (
                float(os.popen("ps -p %d -o %s | tail -1" % (pid, "vsz")).read()) / 1000.0
            )  # virtual memory
            pmem = float(
                os.popen("ps -p %d -o %s | tail -1" % (pid, "%mem")).read()
            )  # % of resident memory to total
            rusage = _RESOURCE.getrusage(_RESOURCE.RUSAGE_SELF)

            if "mem" in self.switches:
                string = "Memory usage: RMEM: |w%g|n MB (%g%%), VMEM (res+swap+cache): |w%g|n MB."
                self.caller.msg(string % (rmem, pmem, vmem))
                return

            loadtable = self.styled_table("property", "statistic", align="l")
            loadtable.add_row("Server load (1 min)", "%g" % loadavg)
            loadtable.add_row("Process ID", "%g" % pid),
            loadtable.add_row("Memory usage", "%g MB (%g%%)" % (rmem, pmem))
            loadtable.add_row("Virtual address space", "")
            loadtable.add_row("|x(resident+swap+caching)|n", "%g MB" % vmem)
            loadtable.add_row(
                "CPU time used (total)",
                "%s (%gs)" % (utils.time_format(rusage.ru_utime), rusage.ru_utime),
            )
            loadtable.add_row(
                "CPU time used (user)",
                "%s (%gs)" % (utils.time_format(rusage.ru_stime), rusage.ru_stime),
            )
            loadtable.add_row(
                "Page faults",
                "%g hard,  %g soft, %g swapouts"
                % (rusage.ru_majflt, rusage.ru_minflt, rusage.ru_nswap),
            )
            loadtable.add_row(
                "Disk I/O", "%g reads, %g writes" % (rusage.ru_inblock, rusage.ru_oublock)
            )
            loadtable.add_row("Network I/O", "%g in, %g out" % (rusage.ru_msgrcv, rusage.ru_msgsnd))
            loadtable.add_row(
                "Context switching",
                "%g vol, %g forced, %g signals"
                % (rusage.ru_nvcsw, rusage.ru_nivcsw, rusage.ru_nsignals),
            )

        # os-generic

        string = "|wServer CPU and Memory load:|n\n%s" % loadtable

        # object cache count (note that sys.getsiseof is not called so this works for pypy too.
        total_num, cachedict = _IDMAPPER.cache_size()
        sorted_cache = sorted(
            [(key, num) for key, num in cachedict.items() if num > 0],
            key=lambda tup: tup[1],
            reverse=True,
        )
        memtable = self.styled_table("entity name", "number", "idmapper %", align="l")
        for tup in sorted_cache:
            memtable.add_row(tup[0], "%i" % tup[1], "%.2f" % (float(tup[1]) / total_num * 100))

        string += "\n|w Entity idmapper cache:|n %i items\n%s" % (total_num, memtable)

        # return to caller
        self.caller.msg(string)


class CmdTickers(COMMAND_DEFAULT_CLASS):
    """
    View running tickers

    Usage:
      tickers

    Note: Tickers are created, stopped and manipulated in Python code
    using the TickerHandler. This is merely a convenience function for
    inspecting the current status.

    """

    key = "@tickers"
    help_category = "System"
    locks = "cmd:perm(tickers) or perm(Builder)"

    def func(self):
        from evennia import TICKER_HANDLER

        all_subs = TICKER_HANDLER.all_display()
        if not all_subs:
            self.caller.msg("No tickers are currently active.")
            return
        table = self.styled_table("interval (s)", "object", "path/methodname", "idstring", "db")
        for sub in all_subs:
            table.add_row(
                sub[3],
                "%s%s"
                % (
                    sub[0] or "[None]",
                    sub[0] and " (#%s)" % (sub[0].id if hasattr(sub[0], "id") else "") or "",
                ),
                sub[1] if sub[1] else sub[2],
                sub[4] or "[Unset]",
                "*" if sub[5] else "-",
            )
        self.caller.msg("|wActive tickers|n:\n" + str(table))


class CmdTasks(COMMAND_DEFAULT_CLASS):
    """
    Display or terminate active tasks (delays).

    Usage:
        tasks[/switch] [task_id or function_name]

    Switches:
        pause   - Pause the callback of a task.
        unpause - Process all callbacks made since pause() was called.
        do_task - Execute the task (call its callback).
        call    - Call the callback of this task.
        remove  - Remove a task without executing it.
        cancel  - Stop a task from automatically executing.

    Notes:
        A task is a single use method of delaying the call of a function. Calls are created
        in code, using `evennia.utils.delay`.
        See |luhttps://www.evennia.com/docs/latest/Command-Duration.html|ltthe docs|le for help.

        By default, tasks that are canceled and never called are cleaned up after one minute.

    Examples:
        - `tasks/cancel move_callback` - Cancels all movement delays from the slow_exit contrib.
            In this example slow exits creates it's tasks with
            `utils.delay(move_delay, move_callback)`
        - `tasks/cancel 2` - Cancel task id 2.

    """

    key = "@tasks"
    aliases = ["@delays", "@task"]
    switch_options = ("pause", "unpause", "do_task", "call", "remove", "cancel")
    locks = "perm(Developer)"
    help_category = "System"

    @staticmethod
    def coll_date_func(task):
        """Replace regex characters in date string and collect deferred function name."""
        t_comp_date = str(task[0]).replace("-", "/")
        t_func_name = str(task[1]).split(" ")
        t_func_mem_ref = t_func_name[3] if len(t_func_name) >= 4 else None
        return t_comp_date, t_func_mem_ref

    def do_task_action(self, *args, **kwargs):
        """
        Process the action of a tasks command.

        This exists to gain support with yes or no function from EvMenu.
        """
        task_id = self.task_id

        # get a reference of the global task handler
        global _TASK_HANDLER
        if _TASK_HANDLER is None:
            from evennia.scripts.taskhandler import TASK_HANDLER as _TASK_HANDLER

        # verify manipulating the correct task
        task_args = _TASK_HANDLER.tasks.get(task_id, False)
        if not task_args:  # check if the task is still active
            self.msg("Task completed while waiting for input.")
            return
        else:
            # make certain a task with matching IDs has not been created
            t_comp_date, t_func_mem_ref = self.coll_date_func(task_args)
            if self.t_comp_date != t_comp_date or self.t_func_mem_ref != t_func_mem_ref:
                self.msg("Task completed while waiting for input.")
                return

        # Do the action requested by command caller
        action_return = self.task_action()
        self.msg(f"{self.action_request} request completed.")
        self.msg(f"The task function {self.action_request} returned: {action_return}")

    def func(self):
        # get a reference of the global task handler
        global _TASK_HANDLER
        if _TASK_HANDLER is None:
            from evennia.scripts.taskhandler import TASK_HANDLER as _TASK_HANDLER
        # handle no tasks active.
        if not _TASK_HANDLER.tasks:
            self.msg("There are no active tasks.")
            if self.switches or self.args:
                self.msg("Likely the task has completed and been removed.")
            return

        # handle caller's request to manipulate a task(s)
        if self.switches and self.lhs:

            # find if the argument is a task id or function name
            action_request = self.switches[0]
            try:
                arg_is_id = int(self.lhslist[0])
            except ValueError:
                arg_is_id = False

            # if the argument is a task id, proccess the action on a single task
            if arg_is_id:

                err_arg_msg = "Switch and task ID are required when manipulating a task."
                task_comp_msg = "Task completed while processing request."

                # handle missing arguments or switches
                if not self.switches and self.lhs:
                    self.msg(err_arg_msg)
                    return

                # create a handle for the task
                task_id = arg_is_id
                task = TaskHandlerTask(task_id)

                # handle task no longer existing
                if not task.exists():
                    self.msg(f"Task {task_id} does not exist.")
                    return

                # get a reference of the function caller requested
                switch_action = getattr(task, action_request, False)
                if not switch_action:
                    self.msg(
                        f"{self.switches[0]}, is not an acceptable task action or "
                        f"{task_comp_msg.lower()}"
                    )

                # verify manipulating the correct task
                if task_id in _TASK_HANDLER.tasks:
                    task_args = _TASK_HANDLER.tasks.get(task_id, False)
                    if not task_args:  # check if the task is still active
                        self.msg(task_comp_msg)
                        return
                    else:
                        t_comp_date, t_func_mem_ref = self.coll_date_func(task_args)
                        t_func_name = str(task_args[1]).split(" ")
                        t_func_name = t_func_name[1] if len(t_func_name) >= 2 else None

                if task.exists():  # make certain the task has not been called yet.
                    prompt = (
                        f"{action_request.capitalize()} task {task_id} with completion date "
                        f"{t_comp_date} ({t_func_name}) {{options}}?"
                    )
                    no_msg = f"No {action_request} processed."
                    # record variables for use in do_task_action method
                    self.task_id = task_id
                    self.t_comp_date = t_comp_date
                    self.t_func_mem_ref = t_func_mem_ref
                    self.task_action = switch_action
                    self.action_request = action_request
                    ask_yes_no(
                        self.caller,
                        prompt=prompt,
                        yes_action=self.do_task_action,
                        no_action=no_msg,
                        default="Y",
                        allow_abort=True,
                    )
                    return True
                else:
                    self.msg(task_comp_msg)
                    return

            # the argument is not a task id, process the action on all task deferring the function
            # specified as an argument
            else:

                name_match_found = False
                arg_func_name = self.lhslist[0].lower()

                # repack tasks into a new dictionary
                current_tasks = {}
                for task_id, task_args in _TASK_HANDLER.tasks.items():
                    current_tasks.update({task_id: task_args})

                # call requested action on all tasks with the function name
                for task_id, task_args in current_tasks.items():
                    t_func_name = str(task_args[1]).split(" ")
                    t_func_name = t_func_name[1] if len(t_func_name) >= 2 else None
                    # skip this task if it is not for the function desired
                    if arg_func_name != t_func_name:
                        continue
                    name_match_found = True
                    task = TaskHandlerTask(task_id)
                    switch_action = getattr(task, action_request, False)
                    if switch_action:
                        action_return = switch_action()
                        self.msg(f"Task action {action_request} completed on task ID {task_id}.")
                        self.msg(f"The task function {action_request} returned: {action_return}")

                # provide a message if not tasks of the function name was found
                if not name_match_found:
                    self.msg(f"No tasks deferring function name {arg_func_name} found.")
                    return
                return True

        # check if an maleformed request was created
        elif self.switches or self.lhs:
            self.msg("Task command misformed.")
            self.msg("Proper format tasks[/switch] [function name or task id]")
            return

        # No task manupilation requested, build a table of tasks and display it
        # get the width of screen in characters
        width = self.client_width()
        # create table header and list to hold tasks data and actions
        tasks_header = (
            "Task ID",
            "Completion Date",
            "Function",
            "Arguments",
            "KWARGS",
            "persistent",
        )
        # empty list of lists, the size of the header
        tasks_list = [list() for i in range(len(tasks_header))]
        for task_id, task in _TASK_HANDLER.tasks.items():
            # collect data from the task
            t_comp_date, t_func_mem_ref = self.coll_date_func(task)
            t_func_name = str(task[1]).split(" ")
            t_func_name = t_func_name[1] if len(t_func_name) >= 2 else None
            t_args = str(task[2])
            t_kwargs = str(task[3])
            t_pers = str(task[4])
            # add task data to the tasks list
            task_data = (task_id, t_comp_date, t_func_name, t_args, t_kwargs, t_pers)
            for i in range(len(tasks_header)):
                tasks_list[i].append(task_data[i])
        # create and display the table
        tasks_table = EvTable(
            *tasks_header, table=tasks_list, maxwidth=width, border="cells", align="c"
        )
        actions = (f"/{switch}" for switch in self.switch_options)
        helptxt = f"\nActions: {iter_to_str(actions)}"
        self.msg(str(tasks_table) + helptxt)
