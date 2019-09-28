"""
Batch processors

These commands implements the 'batch-command' and 'batch-code'
processors, using the functionality in evennia.utils.batchprocessors.
They allow for offline world-building.

Batch-command is the simpler system. This reads a file (*.ev)
containing a list of in-game commands and executes them in sequence as
if they had been entered in the game (including permission checks
etc).

Batch-code is a full-fledged python code interpreter that reads blocks
of python code (*.py) and executes them in sequence. This allows for
much more power than Batch-command, but requires knowing Python and
the Evennia API.  It is also a severe security risk and should
therefore always be limited to superusers only.

"""
import re

from django.conf import settings
from evennia.utils.batchprocessors import BATCHCMD, BATCHCODE
from evennia.commands.cmdset import CmdSet
from evennia.utils import logger, utils


_RE_COMMENT = re.compile(r"^#.*?$", re.MULTILINE + re.DOTALL)
_RE_CODE_START = re.compile(r"^# batchcode code:", re.MULTILINE)
_COMMAND_DEFAULT_CLASS = utils.class_from_module(settings.COMMAND_DEFAULT_CLASS)

# limit symbols for API inclusion
__all__ = ("CmdBatchCommands", "CmdBatchCode")

_HEADER_WIDTH = 70
_UTF8_ERROR = """
 |rDecode error in '%s'.|n

 This file contains non-ascii character(s). This is common if you
 wrote some input in a language that has more letters and special
 symbols than English; such as accents or umlauts.  This is usually
 fine and fully supported! But for Evennia to know how to decode such
 characters in a universal way, the batchfile must be saved with the
 international 'UTF-8' encoding. This file is not.

 Please re-save the batchfile with the UTF-8 encoding (refer to the
 documentation of your text editor on how to do this, or switch to a
 better featured one) and try again.

 Error reported was: '%s'
"""

_PROCPOOL_BATCHCMD_SOURCE = """
from evennia.commands.default.batchprocess import batch_cmd_exec, step_pointer, BatchSafeCmdSet
caller.ndb.batch_stack = commands
caller.ndb.batch_stackptr = 0
caller.ndb.batch_batchmode = "batch_commands"
caller.cmdset.add(BatchSafeCmdSet)
for inum in range(len(commands)):
    print "command:", inum
    caller.cmdset.add(BatchSafeCmdSet)
    if not batch_cmd_exec(caller):
        break
    step_pointer(caller, 1)
print "leaving run ..."
"""
_PROCPOOL_BATCHCODE_SOURCE = """
from evennia.commands.default.batchprocess import batch_code_exec, step_pointer, BatchSafeCmdSet
caller.ndb.batch_stack = codes
caller.ndb.batch_stackptr = 0
caller.ndb.batch_batchmode = "batch_code"
caller.cmdset.add(BatchSafeCmdSet)
for inum in range(len(codes)):
    print "code:", inum
    caller.cmdset.add(BatchSafeCmdSet)
    if not batch_code_exec(caller):
        break
    step_pointer(caller, 1)
print "leaving run ..."
"""


# -------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------


def format_header(caller, entry):
    """
    Formats a header
    """
    width = _HEADER_WIDTH - 10
    # strip all comments for the header
    if caller.ndb.batch_batchmode != "batch_commands":
        # only do cleanup for  batchcode
        entry = _RE_CODE_START.split(entry, 1)[1]
        entry = _RE_COMMENT.sub("", entry).strip()
    header = utils.crop(entry, width=width)
    ptr = caller.ndb.batch_stackptr + 1
    stacklen = len(caller.ndb.batch_stack)
    header = "|w%02i/%02i|G: %s|n" % (ptr, stacklen, header)
    # add extra space to the side for padding.
    header = "%s%s" % (header, " " * (width - len(header)))
    header = header.replace("\n", "\\n")

    return header


def format_code(entry):
    """
    Formats the viewing of code and errors
    """
    code = ""
    for line in entry.split("\n"):
        code += "\n|G>>>|n %s" % line
    return code.strip()


def batch_cmd_exec(caller):
    """
    Helper function for executing a single batch-command entry
    """
    ptr = caller.ndb.batch_stackptr
    stack = caller.ndb.batch_stack
    command = stack[ptr]
    caller.msg(format_header(caller, command))
    try:
        caller.execute_cmd(command)
    except Exception:
        logger.log_trace()
        return False
    return True


def batch_code_exec(caller):
    """
    Helper function for executing a single batch-code entry
    """
    ptr = caller.ndb.batch_stackptr
    stack = caller.ndb.batch_stack
    debug = caller.ndb.batch_debug
    code = stack[ptr]

    caller.msg(format_header(caller, code))
    err = BATCHCODE.code_exec(code, extra_environ={"caller": caller}, debug=debug)
    if err:
        caller.msg(format_code(err))
        return False
    return True


def step_pointer(caller, step=1):
    """
    Step in stack, returning the item located.

    stackptr - current position in stack
    stack - the stack of units
    step - how many steps to move from stackptr
    """
    ptr = caller.ndb.batch_stackptr
    stack = caller.ndb.batch_stack
    nstack = len(stack)
    if ptr + step <= 0:
        caller.msg("|RBeginning of batch file.")
    if ptr + step >= nstack:
        caller.msg("|REnd of batch file.")
    caller.ndb.batch_stackptr = max(0, min(nstack - 1, ptr + step))


def show_curr(caller, showall=False):
    """
    Show the current position in stack
    """
    stackptr = caller.ndb.batch_stackptr
    stack = caller.ndb.batch_stack

    if stackptr >= len(stack):
        caller.ndb.batch_stackptr = len(stack) - 1
        show_curr(caller, showall)
        return

    entry = stack[stackptr]

    string = format_header(caller, entry)
    codeall = entry.strip()
    string += "|G(hh for help)"
    if showall:
        for line in codeall.split("\n"):
            string += "\n|G||n %s" % line
    caller.msg(string)


def purge_processor(caller):
    """
    This purges all effects running
    on the caller.
    """
    try:
        del caller.ndb.batch_stack
        del caller.ndb.batch_stackptr
        del caller.ndb.batch_pythonpath
        del caller.ndb.batch_batchmode
    except Exception:
        # something might have already been erased; it's not critical
        pass
    # clear everything back to the state before the batch call
    if caller.ndb.batch_cmdset_backup:
        caller.cmdset.cmdset_stack = caller.ndb.batch_cmdset_backup
        caller.cmdset.update()
        del caller.ndb.batch_cmdset_backup
    else:
        # something went wrong. Purge cmdset except default
        caller.cmdset.clear()

    caller.scripts.validate()  # this will purge interactive mode


# -------------------------------------------------------------
# main access commands
# -------------------------------------------------------------


class CmdBatchCommands(_COMMAND_DEFAULT_CLASS):
    """
    build from batch-command file

    Usage:
     batchcommands[/interactive] <python.path.to.file>

    Switch:
       interactive - this mode will offer more control when
                     executing the batch file, like stepping,
                     skipping, reloading etc.

    Runs batches of commands from a batch-cmd text file (*.ev).

    """

    key = "batchcommands"
    aliases = ["batchcommand", "batchcmd"]
    switch_options = ("interactive",)
    locks = "cmd:perm(batchcommands) or perm(Developer)"
    help_category = "Building"

    def func(self):
        """Starts the processor."""

        caller = self.caller

        args = self.args
        if not args:
            caller.msg("Usage: batchcommands[/interactive] <path.to.file>")
            return
        python_path = self.args

        # parse indata file

        try:
            commands = BATCHCMD.parse_file(python_path)
        except UnicodeDecodeError as err:
            caller.msg(_UTF8_ERROR % (python_path, err))
            return
        except IOError as err:
            if err:
                err = "{}\n".format(str(err))
            else:
                err = ""
            string = (
                "%s'%s' could not load. You have to supply python paths "
                "from one of the defined batch-file directories\n (%s)."
            )
            caller.msg(string % (err, python_path, ", ".join(settings.BASE_BATCHPROCESS_PATHS)))
            return
        if not commands:
            caller.msg("File %s seems empty of valid commands." % python_path)
            return

        switches = self.switches

        # Store work data in cache
        caller.ndb.batch_stack = commands
        caller.ndb.batch_stackptr = 0
        caller.ndb.batch_pythonpath = python_path
        caller.ndb.batch_batchmode = "batch_commands"
        # we use list() here to create a new copy of the cmdset stack
        caller.ndb.batch_cmdset_backup = list(caller.cmdset.cmdset_stack)
        caller.cmdset.add(BatchSafeCmdSet)

        if "inter" in switches or "interactive" in switches:
            # Allow more control over how batch file is executed

            # Set interactive state directly
            caller.cmdset.add(BatchInteractiveCmdSet)

            caller.msg("\nBatch-command processor - Interactive mode for %s ..." % python_path)
            show_curr(caller)
        else:
            caller.msg(
                "Running Batch-command processor - Automatic mode "
                "for %s (this might take some time) ..." % python_path
            )

            procpool = False
            if "PythonProcPool" in utils.server_services():
                if utils.uses_database("sqlite3"):
                    caller.msg("Batchprocessor disabled ProcPool under SQLite3.")
                else:
                    procpool = True

            if procpool:
                # run in parallel process
                def callback(r):
                    caller.msg("  |GBatchfile '%s' applied." % python_path)
                    purge_processor(caller)

                def errback(e):
                    caller.msg("  |RError from processor: '%s'" % e)
                    purge_processor(caller)

                utils.run_async(
                    _PROCPOOL_BATCHCMD_SOURCE,
                    commands=commands,
                    caller=caller,
                    at_return=callback,
                    at_err=errback,
                )
            else:
                # run in-process (might block)
                for _ in range(len(commands)):
                    # loop through the batch file
                    if not batch_cmd_exec(caller):
                        return
                    step_pointer(caller, 1)
                # clean out the safety cmdset and clean out all other
                # temporary attrs.
                string = "  Batchfile '%s' applied." % python_path
                caller.msg("|G%s" % string)
                purge_processor(caller)


class CmdBatchCode(_COMMAND_DEFAULT_CLASS):
    """
    build from batch-code file

    Usage:
     batchcode[/interactive] <python path to file>

    Switch:
       interactive - this mode will offer more control when
                     executing the batch file, like stepping,
                     skipping, reloading etc.
       debug - auto-delete all objects that has been marked as
               deletable in the script file (see example files for
               syntax). This is useful so as to to not leave multiple
               object copies behind when testing out the script.

    Runs batches of commands from a batch-code text file (*.py).

    """

    key = "batchcode"
    aliases = ["batchcodes"]
    switch_options = ("interactive", "debug")
    locks = "cmd:superuser()"
    help_category = "Building"

    def func(self):
        """Starts the processor."""

        caller = self.caller

        args = self.args
        if not args:
            caller.msg("Usage: batchcode[/interactive/debug] <path.to.file>")
            return
        python_path = self.args
        debug = "debug" in self.switches

        # parse indata file
        try:
            codes = BATCHCODE.parse_file(python_path)
        except UnicodeDecodeError as err:
            caller.msg(_UTF8_ERROR % (python_path, err))
            return
        except IOError as err:
            if err:
                err = "{}\n".format(str(err))
            else:
                err = ""
            string = (
                "%s'%s' could not load. You have to supply python paths "
                "from one of the defined batch-file directories\n (%s)."
            )
            caller.msg(string % (err, python_path, ", ".join(settings.BASE_BATCHPROCESS_PATHS)))
            return
        if not codes:
            caller.msg("File %s seems empty of functional code." % python_path)
            return

        switches = self.switches

        # Store work data in cache
        caller.ndb.batch_stack = codes
        caller.ndb.batch_stackptr = 0
        caller.ndb.batch_pythonpath = python_path
        caller.ndb.batch_batchmode = "batch_code"
        caller.ndb.batch_debug = debug
        # we use list() here to create a new copy of cmdset_stack
        caller.ndb.batch_cmdset_backup = list(caller.cmdset.cmdset_stack)
        caller.cmdset.add(BatchSafeCmdSet)

        if "inter" in switches or "interactive" in switches:
            # Allow more control over how batch file is executed

            # Set interactive state directly
            caller.cmdset.add(BatchInteractiveCmdSet)

            caller.msg("\nBatch-code processor - Interactive mode for %s ..." % python_path)
            show_curr(caller)
        else:
            caller.msg("Running Batch-code processor - Automatic mode for %s ..." % python_path)

            procpool = False
            if "PythonProcPool" in utils.server_services():
                if utils.uses_database("sqlite3"):
                    caller.msg("Batchprocessor disabled ProcPool under SQLite3.")
                else:
                    procpool = True
            if procpool:
                # run in parallel process
                def callback(r):
                    caller.msg("  |GBatchfile '%s' applied." % python_path)
                    purge_processor(caller)

                def errback(e):
                    caller.msg("  |RError from processor: '%s'" % e)
                    purge_processor(caller)

                utils.run_async(
                    _PROCPOOL_BATCHCODE_SOURCE,
                    codes=codes,
                    caller=caller,
                    at_return=callback,
                    at_err=errback,
                )
            else:
                # un in-process (will block)
                for _ in range(len(codes)):
                    # loop through the batch file
                    if not batch_code_exec(caller):
                        return
                    step_pointer(caller, 1)
                # clean out the safety cmdset and clean out all other
                # temporary attrs.
                string = "  Batchfile '%s' applied." % python_path
                caller.msg("|G%s" % string)
                purge_processor(caller)


# -------------------------------------------------------------
# State-commands for the interactive batch processor modes
# (these are the same for both processors)
# -------------------------------------------------------------


class CmdStateAbort(_COMMAND_DEFAULT_CLASS):
    """
    abort

    This is a safety feature. It force-ejects us out of the processor and to
    the default cmdset, regardless of what current cmdset the processor might
    have put us in (e.g. when testing buggy scripts etc).
    """

    key = "abort"
    help_category = "BatchProcess"
    locks = "cmd:perm(batchcommands)"

    def func(self):
        """Exit back to default."""
        purge_processor(self.caller)
        self.caller.msg("Exited processor and reset out active cmdset back to the default one.")


class CmdStateLL(_COMMAND_DEFAULT_CLASS):
    """
    ll

    Look at the full source for the current
    command definition.
    """

    key = "ll"
    help_category = "BatchProcess"
    locks = "cmd:perm(batchcommands)"

    def func(self):
        show_curr(self.caller, showall=True)


class CmdStatePP(_COMMAND_DEFAULT_CLASS):
    """
    pp

    Process the currently shown command definition.
    """

    key = "pp"
    help_category = "BatchProcess"
    locks = "cmd:perm(batchcommands)"

    def func(self):
        """
        This checks which type of processor we are running.
        """
        caller = self.caller
        if caller.ndb.batch_batchmode == "batch_code":
            batch_code_exec(caller)
        else:
            batch_cmd_exec(caller)


class CmdStateRR(_COMMAND_DEFAULT_CLASS):
    """
    rr

    Reload the batch file, keeping the current
    position in it.
    """

    key = "rr"
    help_category = "BatchProcess"
    locks = "cmd:perm(batchcommands)"

    def func(self):
        caller = self.caller
        if caller.ndb.batch_batchmode == "batch_code":
            new_data = BATCHCODE.parse_file(caller.ndb.batch_pythonpath)
        else:
            new_data = BATCHCMD.parse_file(caller.ndb.batch_pythonpath)
        caller.ndb.batch_stack = new_data
        caller.msg(format_code("File reloaded. Staying on same command."))
        show_curr(caller)


class CmdStateRRR(_COMMAND_DEFAULT_CLASS):
    """
    rrr

    Reload the batch file, starting over
    from the beginning.
    """

    key = "rrr"
    help_category = "BatchProcess"
    locks = "cmd:perm(batchcommands)"

    def func(self):
        caller = self.caller
        if caller.ndb.batch_batchmode == "batch_code":
            BATCHCODE.parse_file(caller.ndb.batch_pythonpath)
        else:
            BATCHCMD.parse_file(caller.ndb.batch_pythonpath)
        caller.ndb.batch_stackptr = 0
        caller.msg(format_code("File reloaded. Restarting from top."))
        show_curr(caller)


class CmdStateNN(_COMMAND_DEFAULT_CLASS):
    """
    nn

    Go to next command. No commands are executed.
    """

    key = "nn"
    help_category = "BatchProcess"
    locks = "cmd:perm(batchcommands)"

    def func(self):
        caller = self.caller
        arg = self.args
        if arg and arg.isdigit():
            step = int(self.args)
        else:
            step = 1
        step_pointer(caller, step)
        show_curr(caller)


class CmdStateNL(_COMMAND_DEFAULT_CLASS):
    """
    nl

    Go to next command, viewing its full source.
    No commands are executed.
    """

    key = "nl"
    help_category = "BatchProcess"
    locks = "cmd:perm(batchcommands)"

    def func(self):
        caller = self.caller
        arg = self.args
        if arg and arg.isdigit():
            step = int(self.args)
        else:
            step = 1
        step_pointer(caller, step)
        show_curr(caller, showall=True)


class CmdStateBB(_COMMAND_DEFAULT_CLASS):
    """
    bb

    Backwards to previous command. No commands
    are executed.
    """

    key = "bb"
    help_category = "BatchProcess"
    locks = "cmd:perm(batchcommands)"

    def func(self):
        caller = self.caller
        arg = self.args
        if arg and arg.isdigit():
            step = -int(self.args)
        else:
            step = -1
        step_pointer(caller, step)
        show_curr(caller)


class CmdStateBL(_COMMAND_DEFAULT_CLASS):
    """
    bl

    Backwards to previous command, viewing its full
    source. No commands are executed.
    """

    key = "bl"
    help_category = "BatchProcess"
    locks = "cmd:perm(batchcommands)"

    def func(self):
        caller = self.caller
        arg = self.args
        if arg and arg.isdigit():
            step = -int(self.args)
        else:
            step = -1
        step_pointer(caller, step)
        show_curr(caller, showall=True)


class CmdStateSS(_COMMAND_DEFAULT_CLASS):
    """
    ss [steps]

    Process current command, then step to the next
    one. If steps is given,
    process this many commands.
    """

    key = "ss"
    help_category = "BatchProcess"
    locks = "cmd:perm(batchcommands)"

    def func(self):
        caller = self.caller
        arg = self.args
        if arg and arg.isdigit():
            step = int(self.args)
        else:
            step = 1

        for _ in range(step):
            if caller.ndb.batch_batchmode == "batch_code":
                batch_code_exec(caller)
            else:
                batch_cmd_exec(caller)
            step_pointer(caller, 1)
            show_curr(caller)


class CmdStateSL(_COMMAND_DEFAULT_CLASS):
    """
    sl [steps]

    Process current command, then step to the next
    one, viewing its full source. If steps is given,
    process this many commands.
    """

    key = "sl"
    help_category = "BatchProcess"
    locks = "cmd:perm(batchcommands)"

    def func(self):
        caller = self.caller
        arg = self.args
        if arg and arg.isdigit():
            step = int(self.args)
        else:
            step = 1

        for _ in range(step):
            if caller.ndb.batch_batchmode == "batch_code":
                batch_code_exec(caller)
            else:
                batch_cmd_exec(caller)
            step_pointer(caller, 1)
            show_curr(caller)


class CmdStateCC(_COMMAND_DEFAULT_CLASS):
    """
    cc

    Continue to process all remaining
    commands.
    """

    key = "cc"
    help_category = "BatchProcess"
    locks = "cmd:perm(batchcommands)"

    def func(self):
        caller = self.caller
        nstack = len(caller.ndb.batch_stack)
        ptr = caller.ndb.batch_stackptr
        step = nstack - ptr

        for _ in range(step):
            if caller.ndb.batch_batchmode == "batch_code":
                batch_code_exec(caller)
            else:
                batch_cmd_exec(caller)
            step_pointer(caller, 1)
            show_curr(caller)

        purge_processor(self)
        caller.msg(format_code("Finished processing batch file."))


class CmdStateJJ(_COMMAND_DEFAULT_CLASS):
    """
    jj <command number>

    Jump to specific command number
    """

    key = "jj"
    help_category = "BatchProcess"
    locks = "cmd:perm(batchcommands)"

    def func(self):
        caller = self.caller
        arg = self.args
        if arg and arg.isdigit():
            number = int(self.args) - 1
        else:
            caller.msg(format_code("You must give a number index."))
            return
        ptr = caller.ndb.batch_stackptr
        step = number - ptr
        step_pointer(caller, step)
        show_curr(caller)


class CmdStateJL(_COMMAND_DEFAULT_CLASS):
    """
    jl <command number>

    Jump to specific command number and view its full source.
    """

    key = "jl"
    help_category = "BatchProcess"
    locks = "cmd:perm(batchcommands)"

    def func(self):
        caller = self.caller
        arg = self.args
        if arg and arg.isdigit():
            number = int(self.args) - 1
        else:
            caller.msg(format_code("You must give a number index."))
            return
        ptr = caller.ndb.batch_stackptr
        step = number - ptr
        step_pointer(caller, step)
        show_curr(caller, showall=True)


class CmdStateQQ(_COMMAND_DEFAULT_CLASS):
    """
    qq

    Quit the batchprocessor.
    """

    key = "qq"
    help_category = "BatchProcess"
    locks = "cmd:perm(batchcommands)"

    def func(self):
        purge_processor(self.caller)
        self.caller.msg("Aborted interactive batch mode.")


class CmdStateHH(_COMMAND_DEFAULT_CLASS):
    """Help command"""

    key = "hh"
    help_category = "BatchProcess"
    locks = "cmd:perm(batchcommands)"

    def func(self):
        string = """
    Interactive batch processing commands:

     nn [steps] - next command (no processing)
     nl [steps] - next & look
     bb [steps] - back to previous command (no processing)
     bl [steps] - back & look
     jj   <N>   - jump to command nr N (no processing)
     jl   <N>   - jump & look
     pp         - process currently shown command (no step)
     ss [steps] - process & step
     sl [steps] - process & step & look
     ll         - look at full definition of current command
     rr         - reload batch file (stay on current)
     rrr        - reload batch file (start from first)
     hh         - this help list

     cc         - continue processing to end, then quit.
     qq         - quit (abort all remaining commands)

     abort - this is a safety command that always is available
              regardless of what cmdsets gets added to us during
              batch-command processing. It immediately shuts down
              the processor and returns us to the default cmdset.
    """
        self.caller.msg(string)


# -------------------------------------------------------------
#
# Defining the cmdsets for the interactive batchprocessor
# mode (same for both processors)
#
# -------------------------------------------------------------


class BatchSafeCmdSet(CmdSet):
    """
    The base cmdset for the batch processor.
    This sets a 'safe' abort command that will
    always be available to get out of everything.
    """

    key = "Batch_default"
    priority = 150  # override other cmdsets.

    def at_cmdset_creation(self):
        """Init the cmdset"""
        self.add(CmdStateAbort())


class BatchInteractiveCmdSet(CmdSet):
    """
    The cmdset for the interactive batch processor mode.
    """

    key = "Batch_interactive"
    priority = 104

    def at_cmdset_creation(self):
        """init the cmdset"""
        self.add(CmdStateAbort())
        self.add(CmdStateLL())
        self.add(CmdStatePP())
        self.add(CmdStateRR())
        self.add(CmdStateRRR())
        self.add(CmdStateNN())
        self.add(CmdStateNL())
        self.add(CmdStateBB())
        self.add(CmdStateBL())
        self.add(CmdStateSS())
        self.add(CmdStateSL())
        self.add(CmdStateCC())
        self.add(CmdStateJJ())
        self.add(CmdStateJL())
        self.add(CmdStateQQ())
        self.add(CmdStateHH())
