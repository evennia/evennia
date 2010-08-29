"""
Batch processors

These commands implements the 'batch-command' and 'batch-code' 
processors, using the functionality in src.utils.batchprocessors. 
They allow for offline world-building. 

Batch-command is the simpler system. This reads a file (*.ev)
containing a list of in-game commands and executes them in sequence as
if they had been entered in the game (including permission checks
etc).

Example batch-command file: game/gamesrc/commands/examples/example_batch_cmd.ev 

Batch-code is a full-fledged python code interpreter that reads blocks
of python code (*.py) and executes them in sequence. This allows for
much more power than Batch-command, but requires knowing Python and
the Evennia API.  It is also a severe security risk and should
therefore always be limited to superusers only.

Example batch-code file: game/gamesrc/commands/examples/example_batch_code.py 

"""
from traceback import format_exc
from django.conf import settings
from src.utils import batchprocessors
from game.gamesrc.commands.default.muxcommand import MuxCommand
from src.commands.cmdset import CmdSet

#global defines for storage

CWHITE = r"%cn%ch%cw"
CRED = r"%cn%ch%cr"
CGREEN = r"%cn%ci%cg"
CYELLOW = r"%cn%ch%cy"
CNORM = r"%cn"


#------------------------------------------------------------
# Helper functions
#------------------------------------------------------------

def batch_cmd_exec(caller):
    """
    Helper function for executing a single batch-command entry
    """
    ptr = caller.ndb.batch_stackptr
    stack = caller.ndb.batch_stack
    command = stack[ptr]
    cmdname = command[:command.find(" ")]        
    caller.msg("%s   %02i/%02i: %s %s%s" % (CGREEN, ptr+1,
                                            len(stack),
                                            cmdname,
                                            CGREEN, " "*(50-len(cmdname))))
    try:
        caller.execute_cmd(command)        
    except Exception:
        caller.msg(format_exc())
        return False
    return True


def batch_code_exec(caller):
    """
    Helper function for executing a single batch-code entry
    """    
    ptr = caller.ndb.batch_stackptr
    stack = caller.ndb.batch_stack
    debug = caller.ndb.batch_debug
    
    codedict = stack[ptr]
    caller.msg("%s   %02i/%02i: %s %s%s" % (CGREEN, ptr + 1,
                                            len(stack),
                                            codedict["firstline"],
                                            CGREEN, " "*(50-len(codedict["firstline"])))) 
    err = batchprocessors.batch_code_exec(codedict, 
                                          extra_environ={"caller":caller}, debug=debug)       
    if err:
        caller.msg(err)
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
        caller.msg("Beginning of batch file.")
    if ptr + step >= nstack:
        caller.msg("End of batch file.")
    caller.ndb.batch_stackptr = max(0, min(nstack-1, ptr + step))

def show_curr(caller, showall=False):
    "Show the current position in stack."
    stackptr = caller.ndb.batch_stackptr
    stack = caller.ndb.batch_stack

    if stackptr >= len(stack):
        caller.ndb.batch_stackptr = len(stack) - 1
        show_curr(caller, showall)
        return     
    entry = stack[stackptr]           
    if type(entry) == dict:
        # we first try the batch-code syntax
        firstline = entry['code'][:min(35, len(entry['code'])-1)]
        codeall = entry['code']
    else:
        # we try the batch-cmd syntax instead
        firstline = entry[:min(35, len(entry)-1)]
        codeall = entry
    string = "%s   %02i/%02i: %s %s      %s %s%s" % (CGREEN,
                                                     stackptr+1, len(stack),
                                                     firstline, CGREEN,
                                                     "(hh for help)",
                                                     " "*(35-len(firstline.strip())),
                                                     CNORM)
    if showall:
        string += "\n%s" % codeall
    caller.msg(string)


#------------------------------------------------------------
# main access commands 
#------------------------------------------------------------

class CmdBatchCommands(MuxCommand):
    """    
    Build from batch-command file

    Usage:
     @batchcommands[/interactive] <python path to file>

    Switch:
       interactive - this mode will offer more control when
                     executing the batch file, like stepping,
                     skipping, reloading etc. 

    Runs batches of commands from a batch-cmd text file (*.ev). 

    """
    key = "@batchcommands"
    aliases = ["@batchcommand", "@batchcmd"]
    permissions = "cmd:batchcommands"
    help_category = "Building"

    def func(self):
        "Starts the processor."
        
        caller = self.caller

        args = self.args
        if not args:
            caller.msg("Usage: @batchcommands[/interactive] <path.to.file>")
            return    
        python_path = self.args

        #parse indata file
        
        commands = batchprocessors.parse_batchcommand_file(python_path)
        if not commands:
            string = "'%s' not found.\nYou have to supply the python path "
            string += "of the file relative to \nyour batch-file directory (%s)."
            caller.msg(string % (python_path, settings.BASE_BATCHPROCESS_PATH))
            return
        switches = self.switches

        # Store work data in cache 
        caller.ndb.batch_stack = commands
        caller.ndb.batch_stackptr = 0
        caller.ndb.batch_pythonpath = python_path
        caller.ndb.batch_batchmode = "batch_commands"
        caller.cmdset.add(BatchSafeCmdSet) 

        if 'inter' in switches or 'interactive' in switches:
            # Allow more control over how batch file is executed

            # Set interactive state directly 
            caller.cmdset.add(BatchInteractiveCmdSet)

            caller.msg("\nBatch-command processor - Interactive mode for %s ..." % python_path)
            show_curr(caller)
        else:
            caller.msg("Running Batch-command processor - Automatic mode for %s ..." % python_path)
            # add the 'safety' cmdset in case the batch processing adds cmdsets to us
            for inum in range(len(commands)):
                # loop through the batch file 
                if not batch_cmd_exec(caller):
                    return 
                step_pointer(caller, 1)
            # clean out the safety cmdset and clean out all other temporary attrs.
            caller.cmdset.delete(BatchSafeCmdSet)
            del caller.ndb.batch_stack
            del caller.ndb.batch_stackptr
            del caller.ndb.batch_pythonpath
            del caller.ndb.batch_batchmode
            string = "  Batchfile '%s' applied." % python_path 
            caller.msg("%s%s%s" % (CGREEN, string, " "*(60-len(string))))

class CmdBatchCode(MuxCommand):
    """    
    Build from batch-code file

    Usage:
     @batchcode[/interactive] <python path to file>

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
    key = "@batchcode"
    aliases = ["@batchcodes"]
    permissions = "cmd:batchcodes"
    help_category = "Building"

    def func(self):
        "Starts the processor."
        
        caller = self.caller

        args = self.args
        if not args:
            caller.msg("Usage: @batchcode[/interactive/debug] <path.to.file>")
            return    
        python_path = self.args

        #parse indata file
        codes = batchprocessors.parse_batchcode_file(python_path)
        if not codes:
            string = "'%s' not found.\nYou have to supply the python path "
            string += "of the file relative to \nyour batch-file directory (%s)."
            caller.msg(string % (python_path, settings.BASE_BATCHPROCESS_PATH))
            return
        switches = self.switches

        debug = False
        if 'debug' in switches:
            debug  = True

        # Store work data in cache
        caller.ndb.batch_stack = codes
        caller.ndb.batch_stackptr = 0
        caller.ndb.batch_pythonpath = python_path
        caller.ndb.batch_batchmode = "batch_code"
        caller.ndb.batch_debug = debug
        caller.cmdset.add(BatchSafeCmdSet) 

        if 'inter' in switches or 'interactive'in switches:
            # Allow more control over how batch file is executed

            # Set interactive state directly 
            caller.cmdset.add(BatchInteractiveCmdSet)

            caller.msg("\nBatch-code processor - Interactive mode for %s ..." % python_path)
            show_curr(caller)
        else:
            caller.msg("Running Batch-code processor - Automatic mode for %s ..." % python_path)
            # add the 'safety' cmdset in case the batch processing adds cmdsets to us
            for inum in range(len(codes)):
                # loop through the batch file 
                if not batch_code_exec(caller):
                    return 
                step_pointer(caller, 1)
            # clean out the safety cmdset and clean out all other temporary attrs.
            caller.cmdset.delete(BatchSafeCmdSet)
            del caller.ndb.batch_stack
            del caller.ndb.batch_stackptr
            del caller.ndb.batch_pythonpath
            del caller.ndb.batch_batchmode
            string = "  Batchfile '%s' applied." % python_path 
            caller.msg("%s%s%s" % (CGREEN, string, " "*(60-len(string))))

#------------------------------------------------------------
# State-commands for the interactive batch processor modes
# (these are the same for both processors)
#------------------------------------------------------------

class CmdStateAbort(MuxCommand):
    """
    @abort

    Exits back the default cmdset, regardless of what state
    we are currently in.
    """
    key = "@abort"
    help_category = "BatchProcess"

    def func(self):
        "Exit back to default."
        caller = self.caller
        del caller.ndb.batch_stack
        del caller.ndb.batch_stackptr
        del caller.ndb.batch_pythonpath
        del caller.ndb.batch_batchmode
        # clear everything but the default cmdset.        
        caller.cmdset.delete(BatchSafeCmdSet)        
        caller.cmdset.clear()        
        caller.msg("Exit: Cleared back to default state.")
    
class CmdStateLL(MuxCommand):
    """
    ll
    
    Look at the full source for the current
    command definition. 
    """
    key = "ll"
    help_category = "BatchProcess"

    def func(self):        
        show_curr(self.caller, showall=True)

class CmdStatePP(MuxCommand):
    """
    pp
    
    Process the currently shown command definition.
    """
    key = "pp"
    help_category = "BatchProcess"

    def func(self):
        """
        This checks which type of processor we are running.
        """
        caller = self.caller
        if caller.ndb.batch_batchmode == "batch_code":
            batch_code_exec(caller)
        else:
            batch_cmd_exec(caller)

            
class CmdStateRR(MuxCommand):
    """
    rr

    Reload the batch file, keeping the current
    position in it. 
    """
    key = "rr"
    help_category = "BatchProcess"

    def func(self):
        caller = self.caller
        if caller.ndb.batch_batchmode == "batch_code":
            batchprocessors.read_batchcommand_file(caller.ndb.batch_pythonpath)
        else:
            batchprocessors.read_batchcode_file(caller.ndb.batch_pythonpath)
        caller.msg("\nFile reloaded. Staying on same command.\n")
        show_curr(caller)

class CmdStateRRR(MuxCommand):
    """
    rrr

    Reload the batch file, starting over
    from the beginning.
    """
    key = "rrr"
    help_category = "BatchProcess"

    def func(self):
        caller = self.caller
        if caller.ndb.batch_batchmode == "batch_code":
            batchprocessors.read_batchcommand_file(caller.ndb.batch_pythonpath)
        else:
            batchprocessors.read_batchcode_file(caller.ndb.batch_pythonpath)
        caller.ndb.batch_stackptr = 0
        caller.msg("\nFile reloaded. Restarting from top.\n")
        show_curr(caller)

class CmdStateNN(MuxCommand):
    """
    nn

    Go to next command. No commands are executed.
    """
    key = "nn"
    help_category = "BatchProcess"

    def func(self):
        caller = self.caller
        arg = self.args
        if arg and arg.isdigit():
            step = int(self.args)
        else:
            step = 1
        step_pointer(caller, step)
        show_curr(caller)

class CmdStateNL(MuxCommand):
    """
    nl

    Go to next command, viewing its full source.
    No commands are executed.
    """
    key = "nl"
    help_category = "BatchProcess"

    def func(self):
        caller = self.caller
        arg = self.args
        if arg and arg.isdigit():
            step = int(self.args)
        else:
            step = 1
        step_pointer(caller, step)
        show_curr(caller, showall=True)

class CmdStateBB(MuxCommand):
    """
    bb

    Backwards to previous command. No commands
    are executed.
    """
    key = "bb"
    help_category = "BatchProcess"

    def func(self):
        caller = self.caller
        arg = self.args
        if arg and arg.isdigit():
            step = -int(self.args)
        else:
            step = -1    
        step_pointer(caller, step)
        show_curr(caller)

class CmdStateBL(MuxCommand):
    """
    bl

    Backwards to previous command, viewing its full
    source. No commands are executed.
    """
    key = "bl"
    help_category = "BatchProcess"

    def func(self):
        caller = self.caller
        arg = self.args
        if arg and arg.isdigit():
            step = -int(self.args)
        else:
            step = -1    
        step_pointer(caller, step)
        show_curr(caller, showall=True)        

class CmdStateSS(MuxCommand):
    """
    ss [steps]

    Process current command, then step to the next
    one. If steps is given,
    process this many commands.
    """
    key = "ss"
    help_category = "BatchProcess"

    def func(self):
        caller = self.caller
        arg = self.args
        if arg and arg.isdigit():
            step = int(self.args)
        else:
            step = 1    

        for istep in range(step):
            if caller.ndb.batch_batchmode == "batch_code":
                batch_code_exec(caller)
            else:
                batch_cmd_exec(caller)
            step_pointer(caller, 1)            
            show_curr(caller)

class CmdStateSL(MuxCommand):
    """
    sl [steps]

    Process current command, then step to the next
    one, viewing its full source. If steps is given,
    process this many commands. 
    """
    key = "sl"
    help_category = "BatchProcess"

    def func(self):
        caller = self.caller
        arg = self.args
        if arg and arg.isdigit():
            step = int(self.args)
        else:
            step = 1    

        for istep in range(step):
            if caller.ndb.batch_batchmode == "batch_code":
                batch_code_exec(caller)
            else:
                batch_cmd_exec(caller)
            step_pointer(caller, 1)
            show_curr(caller)

class CmdStateCC(MuxCommand):
    """
    cc

    Continue to process all remaining
    commands.
    """
    key = "cc"
    help_category = "BatchProcess"

    def func(self):
        caller = self.caller
        nstack = len(caller.ndb.batch_stack)
        ptr = caller.ndb.batch_stackptr
        step = nstack - ptr

        for istep in range(step):
            if caller.ndb.batch_batchmode == "batch_code":
                batch_code_exec(caller)
            else:
                batch_cmd_exec(caller)
            step_pointer(caller, 1)
            show_curr(caller)

        del caller.ndb.batch_stack
        del caller.ndb.batch_stackptr
        del caller.ndb.batch_pythonpath
        del caller.ndb.batch_batchmode
        caller.msg("Finished processing batch file.")
    
class CmdStateJJ(MuxCommand):
    """
    j <command number>

    Jump to specific command number
    """
    key = "j"
    help_category = "BatchProcess"

    def func(self):
        caller = self.caller
        arg = self.args
        if arg and arg.isdigit():
            number = int(self.args)-1
        else:
            caller.msg("You must give a number index.")
            return 
        ptr = caller.ndb.batch_stackptr
        step = number - ptr    
        step_pointer(caller, step)
        show_curr(caller)

class CmdStateJL(MuxCommand):
    """
    jl <command number>

    Jump to specific command number and view its full source.
    """
    key = "jl"
    help_category = "BatchProcess"

    def func(self):
        caller = self.caller
        arg = self.args
        if arg and arg.isdigit():
            number = int(self.args)-1
        else:
            caller.msg("You must give a number index.")
            return 
        ptr = caller.ndb.batch_stackptr
        step = number - ptr    
        step_pointer(caller, step)
        show_curr(caller, showall=True)

class CmdStateQQ(MuxCommand):
    """
    qq 

    Quit the batchprocessor.
    """
    key = "qq"
    help_category = "BatchProcess"

    def func(self):
        caller = self.caller
        del caller.ndb.batch_stack
        del caller.ndb.batch_stackptr
        del caller.ndb.batch_pythonpath
        del caller.ndb.batch_batchmode
        caller.cmdset.delete(BatchSafeCmdSet)
        caller.cmdset.delete(BatchInteractiveCmdSet)
        caller.scripts.validate() # this will clear interactive mode.
        caller.msg("Aborted interactive batch mode.")
    
class CmdStateHH(MuxCommand):
    "Help command"

    key = "help"
    aliases = "hh"
    help_category = "BatchProcess"

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
    """
        self.caller.msg(string)



#------------------------------------------------------------
#
# Defining the cmdsets for the interactive batchprocessor
# mode (same for both processors)
#
#------------------------------------------------------------

class BatchSafeCmdSet(CmdSet):
    """
    The base cmdset for the batch processor.
    This sets a 'safe' @abort command that will
    always be available to get out of everything.
    """
    key = "Batch_default"
    priority = 104 # override other cmdsets.

    def at_cmdset_creation(self):
        "Init the cmdset"
        self.add(CmdStateAbort())

class BatchInteractiveCmdSet(CmdSet):
    """
    The cmdset for the interactive batch processor mode.
    """
    key = "Batch_interactive"
    priority = 104

    def at_cmdset_creation(self):
        "init the cmdset"
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
