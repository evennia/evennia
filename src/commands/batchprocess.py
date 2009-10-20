"""
Batch processor

The batch processor accepts 'batchcommand files' e.g 'batch.ev', containing a
sequence of valid evennia commands in a simple format. The engine
runs each command in sequence, as if they had been run at the terminal prompt.

This way entire game worlds can be created and planned offline; it is
especially useful in order to create long room descriptions where a
real offline text editor is often much better than any online text editor
or prompt.

Example of batch.ev file:
---------------------------- 

# batch file
# all lines starting with # are comments; they also indicate
# that a command definition is over. 

@create box

# this comment ends the @create command.

@set box=desc: A large box.

Inside are some scattered piles of clothing. 


It seems the bottom of the box is a bit loose. 

# Again, this comment indicates the @set command is over. Note how
# the description could be freely added. Excess whitespace on a line
# is ignored.  An empty line in the command definition is parsed as a \n
# (so two empty lines becomes a new paragraph).

@teleport #221

# (Assuming #221 is a warehouse or something.)
# (remember, this comment ends the @teleport command! Don'f forget it)

@drop box

# Done, the box is in the warehouse! (this last comment is not necessary to
# close the @drop command since it's the end of the file)
-------------------------

An example batch file is found in game/gamesrc/commands/examples. 
"""
import os
import re
from django.conf import settings
from src import logger
from src import defines_global
from src.cmdtable import GLOBAL_CMD_TABLE
from src.statetable import GLOBAL_STATE_TABLE

#global defines for storage

STATENAME="_interactive batch processor"
CMDSTACKS={} # user:cmdstack pairs (for interactive)
STACKPTRS={} # user:stackpointer pairs (for interactive)
FILENAMES={} # user:filename pairs (for interactive/reload)

cwhite = r"%cn%ch%cw"
cred = r"%cn%ch%cw"
cgreen = r"%cn%ci%cg"
cyellow = r"%cn%ch%cy"
cnorm = r"%cn"

def read_batchbuild_file(filename):
    """
    This reads the contents of batchfile.
    Filename is considered to be the name of the batch file
    relative the directory specified in settings.py
    """    
    filename = os.path.abspath("%s/%s" % (settings.BATCH_IMPORT_PATH, filename))
    try:
        f = open(filename)
    except IOError:
        logger.log_errmsg("file %s not found." % filename)
        return None
    lines = f.readlines()
    f.close()
    return lines


def parse_batchbuild_file(filename):
    """
    This parses the lines of a batchfile according to the following
    rules:
      1) # at the beginning of a line marks the end of the command before it.
           It is also a comment and any number of # can exist on subsequent
           lines (but not inside comments).
      2) Commands are placed alone at the beginning of a line and their
         arguments are considered to be everything following (on any
         number of lines) until the next comment line beginning with #.
      3) Newlines are ignored in command definitions
      4) A completely empty line in a command line definition is condered
         a newline (so two empty lines is a paragraph).
      5) Excess spaces and indents inside arguments are stripped. 
    """

    #read the indata, if possible.
    lines = read_batchbuild_file(filename)
    if not lines:
        logger.log_errmsg("File %s not found." % filename)
        return

    #helper function
    def identify_line(line):
        """
        Identifies the line type (comment, commanddef or empty)
        """
        try:
            if line.strip()[0] == '#':
                return "comment"
            else:
                return "commanddef"
        except IndexError:
            return "empty"

    commands = []
    curr_cmd = ""

    #purge all superfluous whitespace and newlines from lines
    reg1 = re.compile(r"\s+")
    lines = [reg1.sub(" ",l) for l in lines]

    #parse all command definitions into a list.
    for line in lines:
        typ = identify_line(line)
        if typ == "commanddef":
            curr_cmd += line
        elif typ == "empty" and curr_cmd:
            curr_cmd += "\r\n"
        else: #comment
            if curr_cmd:
                commands.append(curr_cmd.strip())                
            curr_cmd = ""
    if curr_cmd: commands.append(curr_cmd.strip())

    #second round to clean up now merged line edges etc.
    reg2 = re.compile(r"[ \t\f\v]+")
    commands = [reg2.sub(" ",c) for c in commands]   

    #remove eventual newline at the end of commands
    commands = [c.strip('\r\n') for c in commands]

    return commands
    
def batch_process(source_object, commands):
    """
    Process a file straight off.
    """    
    for i, command in enumerate(commands):
        cmdname = command[:command.find(" ")]        
        source_object.emit_to("%s== %s%02i/%02i: %s %s%s" % (cgreen,cwhite,i+1,
                                                             len(commands),
                                                             cmdname,
                                                             cgreen,"="*(50-len(cmdname))))
        source_object.execute_cmd(command)        

#main access function @batchprocess

def cmd_batchprocess(command):
    """    
    @batchprocess - build from batch file

    Usage:
     @batchprocess[/interactive] <filename with full path>

    Runs batches of commands from a batchfile. This is a
    superuser command, intended for large-scale offline world
    development.

    Interactive mode allows the user more control over the
    processing of the file.     
    """
    global CMDSTACKS,STACKPTRS,FILENAMES
    
    source_object = command.source_object

    #check permissions; this is a superuser only command.
    if not source_object.is_superuser():
        source_object.emit_to(defines_global.NOPERMS_MSG)
        return

    args = command.command_argument
    if not args:
        source_object.emit_to("Usage: @batchprocess[/interactive] <filename with full path>")
        return    
    filename = args.strip()

    #parse indata file
    commands = parse_batchbuild_file(filename)
    if not commands:
        source_object.emit_to("'%s' not found.\nYou have to supply the real path to the file relative to \nyour batch-file directory (e.g. game/gamesrc/world)." % filename)
        return
    switches = command.command_switches
    if switches and switches[0] in ['inter','interactive']:
        # allow more control over how batch file is executed
        if not source_object.set_state(STATENAME):        
            source_object.emit_to("You cannot use the interactive mode while you have the flag ADMIN_NOSTATE set.")
            return

        CMDSTACKS[source_object] = commands
        STACKPTRS[source_object] = 0
        FILENAMES[source_object] = filename
        source_object.emit_to("\nBatch processor - Interactive mode ...")
        show_curr(source_object)
    else:
        source_object.emit_to("Running Batch processor - Automatic mode ...")
        source_object.clear_state()
        batch_process(source_object, commands)
        source_object.emit_to("%s== Batchfile '%s' applied." % (cgreen,filename))

GLOBAL_CMD_TABLE.add_command("@batchprocess", cmd_batchprocess,
                             priv_tuple=("genperms.process_control",), help_category="Building")

#interactive state commands

def printfooter():
    "prints a nice footer"
    #s = "%s\n== nn/bb/jj == pp/ss == ll == rr/rrr == cc/qq == (hh for help) ==" % cgreen
    s = ""
    return s

def show_curr(source_object,showall=False):
    "Show the current command."
    global CMDSTACKS,STACKPTRS
    ptr = STACKPTRS[source_object]
    commands = CMDSTACKS[source_object]
    if ptr >= len(commands):
        s = "\n You have reached the end of the batch file."
        s += "\n Use qq to exit or bb to go back."        
        source_object.emit_to(s)       
        STACKPTRS[source_object] = len(commands)-1
        show_curr(source_object)
        return 
    command = commands[ptr]            
    cmdname = command[:command.find(" ")]            
    s = "%s== %s%02i/%02i: %s %s===== %s %s%s" % (cgreen,cwhite,
                                                ptr+1,len(commands),
                                                cmdname,cgreen,
                                                "(hh for help)",
                                                "="*(35-len(cmdname)),
                                                cnorm)
    if showall:
        s += "\n%s" % command
    s += printfooter()
    source_object.emit_to(s)

def process_commands(source_object, steps=0):
    "process one or more commands "
    global CMDSTACKS,STACKPTRS
    ptr = STACKPTRS[source_object]
    commands = CMDSTACKS[source_object]
    if steps:
        try:
            cmds = commands[ptr:ptr+steps]
        except IndexError:
            cmds = commands[ptr:]
        for cmd in cmds:
            #this so it is kept in case of traceback
            STACKPTRS[source_object] = ptr + 1 
            show_curr(source_object)
            source_object.execute_cmd(cmd)
    else:
        show_curr(source_object)
        source_object.execute_cmd(commands[ptr])
    
def reload_stack(source_object):
    "reload the stack"
    global CMDSTACKS,FILENAMES
    commands = parse_batchbuild_file(FILENAMES[source_object])
    if commands:
        CMDSTACKS[source_object] = commands
    else:
        source_object.emit_to("Commands in file could not be reloaded. Was it moved?")

def move_in_stack(source_object, step=1):
    "store data in stack"
    global CMDSTACKS, STACKPTRS
    N = len(CMDSTACKS[source_object])    
    currpos = STACKPTRS[source_object]    
    STACKPTRS[source_object] = max(0,min(N-1,currpos+step)) 

def exit_state(source_object):    
    "Quit the state"
    global CMDSTACKS,STACKPTRS,FILENAMES
    try:
        del CMDSTACKS[source_object]
        del STACKPTRS[source_object]
        del FILENAMES[source_object]
    except KeyError:
        logger.log_errmsg("Batchprocessor quit error: all state vars could not be deleted.")
    # since clear_state() is protected against exiting the interactive mode
    # (to avoid accidental drop-outs by rooms clearing a player's state),
    # we have to clear the state directly here. 
    source_object.state = None 

def cmd_state_ll(command):
    """
    ll
    
    Look at the full source for the current
    command definition. 
    """
    show_curr(command.source_object,showall=True)

def cmd_state_pp(command):
    """
    pp
    
    Process the currently shown command definition.
    """
    process_commands(command.source_object)
    command.source_object.emit_to(printfooter())
    
def cmd_state_rr(command):
    """
    rr

    Reload the batch file, keeping the current
    position in it. 
    """
    reload_stack(command.source_object)
    command.source_object.emit_to("\nFile reloaded. Staying on same command.\n")
    show_curr(command.source_object)

def cmd_state_rrr(command):
    """
    rrr

    Reload the batch file, starting over
    from the beginning.
    """
    global STACKPTRS
    reload_stack(command.source_object)
    STACKPTRS[command.source_object] = 0
    command.source_object.emit_to("\nFile reloaded. Restarting from top.\n")
    show_curr(command.source_object)

def cmd_state_nn(command):
    """
    nn

    Go to next command. No commands are executed.
    """
    source_object = command.source_object
    arg = command.command_argument
    if arg and arg.isdigit():
        step = int(command.command_argument)
    else:
        step = 1
    move_in_stack(source_object, step)
    show_curr(source_object)

def cmd_state_nl(command):
    """
    nl

    Go to next command, viewing its full source.
    No commands are executed.
    """
    source_object = command.source_object
    arg = command.command_argument
    if arg and arg.isdigit():
        step = int(command.command_argument)
    else:
        step = 1
    move_in_stack(source_object, step)
    show_curr(source_object, showall=True)

def cmd_state_bb(command):
    """
    bb

    Backwards to previous command. No commands
    are executed.
    """
    source_object = command.source_object
    arg = command.command_argument
    if arg and arg.isdigit():
        step = -int(command.command_argument)
    else:
        step = -1    
    move_in_stack(source_object, step)
    show_curr(source_object)

def cmd_state_bl(command):
    """
    bl

    Backwards to previous command, viewing its full
    source. No commands are executed.
    """
    source_object = command.source_object
    arg = command.command_argument
    if arg and arg.isdigit():
        step = -int(command.command_argument)
    else:
        step = -1    
    move_in_stack(source_object, step)
    show_curr(source_object, showall=True)

def cmd_state_ss(command):
    """
    ss [steps]

    Process current command, then step to the next
    one. If steps is given,
    process this many commands.
    """
    source_object = command.source_object
    arg = command.command_argument
    if arg and arg.isdigit():
        step = int(command.command_argument)
    else:
        step = 1    
    process_commands(source_object,step)
    show_curr(source_object)

def cmd_state_sl(command):
    """
    sl [steps]

    Process current command, then step to the next
    one, viewing its full source. If steps is given,
    process this many commands. 
    """
    source_object = command.source_object
    arg = command.command_argument
    if arg and arg.isdigit():
        step = int(command.command_argument)
    else:
        step = 1    
    process_commands(source_object,step)
    show_curr(source_object, showall=True)

def cmd_state_cc(command):
    """
    cc

    Continue to process all remaining
    commands.
    """
    global CMDSTACKS,STACKPTRS
    source_object = command.source_object
    N = len(CMDSTACKS[source_object])
    ptr = STACKPTRS[source_object]
    step = N - ptr
    process_commands(source_object,step)
    exit_state(source_object)
    source_object.emit_to("Finished processing batch file.")
    
def cmd_state_jj(command):
    """
    j <command number>

    Jump to specific command number
    """
    global STACKPTRS    
    source_object = command.source_object
    arg = command.command_argument
    if arg and arg.isdigit():
        no = int(command.command_argument)-1
    else:
        source_object.emit_to("You must give a number index.")
        return 
    ptr = STACKPTRS[source_object]
    step = no - ptr    
    move_in_stack(source_object, step)
    show_curr(source_object)

def cmd_state_jl(command):
    """
    jl <command number>

    Jump to specific command number and view its full source.
    """
    global STACKPTRS    
    source_object = command.source_object
    arg = command.command_argument
    if arg and arg.isdigit():
        no = int(command.command_argument)-1
    else:
        source_object.emit_to("You must give a number index.")
        return 
    ptr = STACKPTRS[source_object]
    step = no - ptr    
    move_in_stack(source_object, step)
    show_curr(source_object, showall=True)

def cmd_state_qq(command):
    """
    qq 

    Quit the batchprocessor.
    """
    exit_state(command.source_object)
    command.source_object.emit_to("Aborted interactive batch mode.")
    
def cmd_state_hh(command):
    "Help command"
    s = """
    Interactive batch processing commands:
     nn [steps] - next command (no processing)
     nl [steps] - next & look 
     bb [steps] - back to previous command (no processing)
     bl [steps] - back & look 
     jj   <N>   - jump to command no N (no processing)
     jl   <N>   - jump & look 
     pp         - process currently shown command (no step)
     ss [steps] - process & step
     ll         - look at full definition of current command
     rr         - reload batch file (stay on current)
     rrr        - reload batch file (start from first)
     hh         - this help list

     cc         - continue processing to end, then quit.
     qq         - quit (abort all remaining commands)
    """
    command.source_object.emit_to(s)

#create the state; we want it as open as possible so we can do everything
# in our batch processing. 
GLOBAL_STATE_TABLE.add_state(STATENAME,global_cmds='all',
                             allow_exits=True,allow_obj_cmds=True,exit_command=True)
#add state commands 
GLOBAL_STATE_TABLE.add_command(STATENAME,"nn",cmd_state_nn)
GLOBAL_STATE_TABLE.add_command(STATENAME,"nl",cmd_state_nl)
GLOBAL_STATE_TABLE.add_command(STATENAME,"bb",cmd_state_bb)
GLOBAL_STATE_TABLE.add_command(STATENAME,"bl",cmd_state_bl)
GLOBAL_STATE_TABLE.add_command(STATENAME,"jj",cmd_state_jj)
GLOBAL_STATE_TABLE.add_command(STATENAME,"jl",cmd_state_jl)
GLOBAL_STATE_TABLE.add_command(STATENAME,"pp",cmd_state_pp)
GLOBAL_STATE_TABLE.add_command(STATENAME,"ss",cmd_state_ss)
GLOBAL_STATE_TABLE.add_command(STATENAME,"sl",cmd_state_sl)
GLOBAL_STATE_TABLE.add_command(STATENAME,"cc",cmd_state_cc)
GLOBAL_STATE_TABLE.add_command(STATENAME,"ll",cmd_state_ll)
GLOBAL_STATE_TABLE.add_command(STATENAME,"rr",cmd_state_rr)
GLOBAL_STATE_TABLE.add_command(STATENAME,"rrr",cmd_state_rrr)
GLOBAL_STATE_TABLE.add_command(STATENAME,"hh",cmd_state_hh)
GLOBAL_STATE_TABLE.add_command(STATENAME,"qq",cmd_state_qq)
