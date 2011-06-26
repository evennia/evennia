"""
This file contains the core methods for the Batch-command- and
Batch-code-processors respectively. In short, these are two different
ways to build a game world using a normal text-editor without having
to do so 'on the fly' in-game. They also serve as an automatic backup
so you can quickly recreate a world also after a server reset. The
functions in this module is meant to form the backbone of a system
called and accessed through game commands.

The Batch-command processor is the simplest. It simply runs a list of
in-game commands in sequence by reading them from a text file. The
advantage of this is that the builder only need to remember the normal
in-game commands. They are also executing with full permission checks
etc, making it relatively safe for builders to use. The drawback is
that in-game there is really a builder-character walking around
building things, and it can be important to create rooms and objects
in the right order, so the character can move between them. Also
objects that affects players (such as mobs, dark rooms etc) will
affect the building character too, requiring extra care to turn
off/on.

The Batch-code processor is a more advanced system that accepts full
Python code, executing in chunks. The advantage of this is much more
power; practically anything imaginable can be coded and handled using
the batch-code processor. There is no in-game character that moves and
that can be affected by what is being built - the database is
populated on the fly. The drawback is safety and entry threshold - the
code is executed as would any server code, without mud-specific
permission checks and you have full access to modifying objects
etc. You also need to know Python and Evennia's API. Hence it's
recommended that the batch-code processor is limited only to
superusers or highly trusted staff.


Batch-command processor file syntax

The batch-command processor accepts 'batchcommand files' e.g 'batch.ev',
containing a sequence of valid evennia commands in a simple
format. The engine runs each command in sequence, as if they had been
run at the game prompt.

This way entire game worlds can be created and planned offline; it is
especially useful in order to create long room descriptions where a
real offline text editor is often much better than any online text
editor or prompt.

Example of batch.ev file:
---------------------------- 

# batch file
# all lines starting with # are comments; they also indicate
# that a command definition is over. 

@create box

# this comment ends the @create command.

@set box/desc = A large box.

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

An example batch file is game/gamesrc/commands/examples/batch_example.ev. 



Batch-code processor file syntax

The Batch-code processor accepts full python modules (e.g. "batch.py") that
looks identical to normal Python files with a few exceptions that allows them
to the executed in blocks. This way of working assures a sequential execution
of the file and allows for features like stepping from block to block
(without executing those coming before), as well as automatic deletion
of created objects etc. You can however also run a batch-code python file
directly using Python (and can also be de). 

Code blocks are separated by python comments starting with special code words. 

#HEADER - this denotes commands global to the entire file, such as
          import statements and global variables. They will
          automatically be pasted at the top of all code blocks. Observe
          that changes to these variables made in one block is not
          preserved between blocks!
#CODE [objname, objname, ...] - This designates a code block that will be executed like a 
           stand-alone piece of code together with any #HEADER
           defined. <objname>s mark the (variable-)names of objects created in the code, 
           and which may be auto-deleted by the processor if desired (such as when 
           debugging the script). E.g., if the code contains the command 
           myobj = create.create_object(...), you could put 'myobj' in the #CODE header
           regardless of what the created object is actually called in-game. 

The following variables are automatically made available for the script:

caller - the object executing the script

Example batch.py file
-----------------------------------

#HEADER 

import traceback 
from django.config import settings
from src.utils import create
from game.gamesrc.typeclasses import basetypes 

GOLD = 10

#CODE obj, obj2

obj = create.create_object(basetypes.Object)
obj2 = create.create_object(basetypes.Object)
obj.location = caller.location
obj.db.gold = GOLD
caller.msg("The object was created!")

#CODE

script = create.create_script()

"""

import re
import codecs
from traceback import format_exc
from django.conf import settings
from django.core.management import setup_environ
from src.utils import logger
from src.utils import utils
from game import settings as settings_module

ENCODINGS = settings.ENCODINGS

#------------------------------------------------------------
# Helper function
#------------------------------------------------------------

def read_batchfile(pythonpath, file_ending='.py'):
    """
    This reads the contents of a batch-file.
    Filename is considered to be the name of the batch file
    relative the directory specified in settings.py.

    file_ending specify which batchfile ending should be 
    assumed (.ev or .py).
    """    

    # open the file
    if pythonpath and not (pythonpath.startswith('src.') or pythonpath.startswith('game.') 
                           or pythonpath.startswith('contrib.')):
        abspaths = []
        for basepath in settings.BASE_BATCHPROCESS_PATHS:
            abspaths.append(utils.pypath_to_realpath("%s.%s" % (basepath, pythonpath), file_ending))
    else:
        abspaths = [utils.pypath_to_realpath(pythonpath, file_ending)]
    fobj, lines, err = None, [], None
    for file_encoding in ENCODINGS:
        # try different encodings, in order 
        load_errors = []
        for abspath in abspaths:
            # try different paths, until we get a match 
            try:        
                # we read the file directly into unicode.
                fobj = codecs.open(abspath, 'r', encoding=file_encoding)
            except IOError:
                load_errors.append("Could not open batchfile '%s'." % abspath)
                continue 
            break
        if not fobj:
            continue 

        load_errors = []
        err =None 
        # We have successfully found and opened the file. Now actually
        # try to decode it using the given protocol. 
        try:
            lines = fobj.readlines()
        except UnicodeDecodeError:
            # give the line of failure
            fobj.seek(0)
            try:
                lnum = 0
                for lnum, line in enumerate(fobj):
                    pass
            except UnicodeDecodeError, err:
                # lnum starts from 0, so we add +1 line, 
                # besides the faulty line is never read
                # so we add another 1 (thus +2) to get
                # the actual line number seen in an editor. 
                err.linenum = lnum + 2                
            fobj.close()
            # possibly try another encoding
            continue 
        # if we get here, the encoding worked. Stop iteration.
        break 
    if load_errors: 
        logger.log_errmsg("\n".join(load_errors))
    if err: 
        return err
    else:
        return lines

#------------------------------------------------------------
#
# Batch-command processor
#
#------------------------------------------------------------

class BatchCommandProcessor(object):
    """
    This class implements a batch-command processor.

    """   
    def parse_file(self, pythonpath):
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

        #read the indata, if possible.
        lines = read_batchfile(pythonpath, file_ending='.ev')
        
        #line = utils.to_unicode(line)
        if not lines:
            return None 

        commands = []
        curr_cmd = ""

        #purge all superfluous whitespace and newlines from lines
        reg1 = re.compile(r"\s+")
        lines = [reg1.sub(" ", l) for l in lines]

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
        if curr_cmd: 
            commands.append(curr_cmd.strip())

        #second round to clean up now merged line edges etc.
        reg2 = re.compile(r"[ \t\f\v]+")
        commands = [reg2.sub(" ", c) for c in commands]   

        #remove eventual newline at the end of commands
        commands = [c.strip('\r\n') for c in commands]
        return commands

#------------------------------------------------------------
#
# Batch-code processor
#
#------------------------------------------------------------


class BatchCodeProcessor(object):
    """
    This implements a batch-code processor
 
    """

    def parse_file(self, pythonpath):
        """
        This parses the lines of a batchfile according to the following
        rules:

        1) Lines starting with #HEADER starts a header block (ends other blocks)
        2) Lines starting with #CODE begins a code block (ends other blocks)
        3) #CODE headers may be of the following form: #CODE (info) objname, objname2, ...
        3) All lines outside blocks are stripped.
        4) All excess whitespace beginning/ending a block is stripped.

        """

        # helper function
        def parse_line(line):
            """
            Identifies the line type: block command, comment, empty or normal code.          

            """    
            line = line.strip()

            if line.startswith("#HEADER"):
                return ("header", "", "")
            elif line.startswith("#CODE"):
                # parse code command
                line = line.lstrip("#CODE").strip()
                objs = []
                info = ""
                if line and '(' in line and ')' in line:
                    # a code description
                    lp = line.find('(')
                    rp = line.find(')')
                    info = line[lp:rp+1]
                    line = line[rp+1:] 
                if line:
                    objs = [obj.strip() for obj in line.split(',')]                
                return ("codeheader", info, objs)
            elif line.startswith('#'):
                return ('comment', "", "\n%s" % line)
            else:
                #normal line - return it with a line break.
                return ('line', "", "\n%s" % line)

        # read indata

        lines = read_batchfile(pythonpath, file_ending='.py')
        if not lines:
            return None

        # parse file into blocks

        header = ""
        codes = []

        in_header = False
        in_code = False

        for line in lines:
            # parse line 
            mode, info, line = parse_line(line)
            # try:
            #     print "::", in_header, in_code, mode, line.strip() 
            # except:
            #     print "::", in_header, in_code, mode, line             
            if mode == 'header':
                in_header = True
                in_code = False
            elif mode == 'codeheader':                
                in_header = False
                in_code = True
                # the line is a list of object variable names
                # (or an empty list) at this point.
                codedict = {'objs':line,
                            'info':info,
                            'code':""}
                codes.append(codedict)
            elif mode == 'comment' and in_header:
                continue
            else:
                # another type of line (empty, comment or code)
                if line and in_header:
                    header += line
                elif line and in_code:
                    codes[-1]['code'] += line
                else:
                    # not in a block (e.g. first in file). Ignore.
                    continue

        # last, we merge the headers with all codes.
        for codedict in codes:
            codedict["code"] = "#CODE %s %s\n%s\n\n%s" % (codedict['info'],
                                                          ", ".join(codedict["objs"]),
                                                          header.strip(), 
                                                          codedict["code"].strip())
        return codes

    def code_exec(self, codedict, extra_environ=None, debug=False):
        """
        Execute a single code block, including imports and appending global vars

        extra_environ - dict with environment variables
        """

        # define the execution environment
        environ = "setup_environ(settings_module)"
        environdict = {"setup_environ":setup_environ, 
                       "settings_module":settings_module}
        if extra_environ:
            for key, value in extra_environ.items():
                environdict[key] = value

        # merge all into one block
        code = "%s\n%s" % (environ, codedict['code'])
        if debug:
            # try to delete marked objects
            for obj in codedict['objs']:
                code += "\ntry:    %s.delete()\nexcept:    pass" % obj

        # execute the block 
        try:
            exec(code, environdict)
        except Exception:
            errlist = format_exc().split('\n')
            if len(errlist) > 4:
                errlist = errlist[4:]
            err = "\n".join(" %s" % line for line in errlist if line)
            if debug:
                # try to delete objects again.
                try:
                    for obj in codedict['objs']:
                        eval("%s.delete()" % obj, environdict)
                except Exception:
                    pass
            return err
        return None

BATCHCMD = BatchCommandProcessor()
BATCHCODE = BatchCodeProcessor()
