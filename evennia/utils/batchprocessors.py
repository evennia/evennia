"""
This module contains the core methods for the Batch-command- and
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
permission-checks, and you have full access to modifying objects
etc. You also need to know Python and Evennia's API. Hence it's
recommended that the batch-code processor is limited only to
superusers or highly trusted staff.

Batch-command processor file syntax

The batch-command processor accepts 'batchcommand files' e.g
`batch.ev`, containing a sequence of valid Evennia commands in a
simple format. The engine runs each command in sequence, as if they
had been run at the game prompt.

Each Evennia command must be delimited by a line comment to mark its
end.

```
#INSERT path.batchcmdfile - this as the first entry on a line will
      import and run a batch.ev file in this position, as if it was
      written in this file.
```

This way entire game worlds can be created and planned offline; it is
especially useful in order to create long room descriptions where a
real offline text editor is often much better than any online text
editor or prompt.

Example of batch.ev file:
----------------------------

```
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

# Example of importing another file at this point.
#IMPORT examples.batch

@drop box

# Done, the box is in the warehouse! (this last comment is not necessary to
# close the @drop command since it's the end of the file)
```

-------------------------

An example batch file is `contrib/examples/batch_example.ev`.


==========================================================================


Batch-code processor file syntax

The Batch-code processor accepts full python modules (e.g. `batch.py`)
that looks identical to normal Python files with a few exceptions that
allows them to the executed in blocks. This way of working assures a
sequential execution of the file and allows for features like stepping
from block to block (without executing those coming before), as well
as automatic deletion of created objects etc. You can however also run
a batch-code Python file directly using Python.

Code blocks are separated by python comments starting with special
code words:

HEADER - this denotes commands global to the entire file, such as
          import statements and global variables. They will
          automatically be pasted at the top of all code
          blocks. Observe that changes to these variables made in one
          block is not preserved between blocks!
CODE
CODE (info)
CODE (info) objname1, objname1, ... -
           This designates a code block that will be executed like a
           stand-alone piece of code together with any #HEADER
           defined. (info) text is used by the interactive mode to
           display info about the node to run.  <objname>s mark the
           (variable-)names of objects created in the code, and which
           may be auto-deleted by the processor if desired (such as
           when debugging the script). E.g., if the code contains the
           command myobj = create.create_object(...), you could put
           'myobj' in the #CODE header regardless of what the created
           object is actually called in-game.
INSERT path.filename - This imports another batch_code.py file and
          runs it in the given position.  paths are given as python
          path. The inserted file will retain its own HEADERs which
          will not be mixed with the HEADERs of the file importing
          this file.

The following variables are automatically made available for the script:

caller - the object executing the script

Example batch.py file
-----------------------------------

```
#HEADER

from django.config import settings
from evennia.utils import create
from types import basetypes

GOLD = 10

#CODE obj, obj2

obj = create.create_object(basetypes.Object)
obj2 = create.create_object(basetypes.Object)
obj.location = caller.location
obj.db.gold = GOLD
caller.msg("The object was created!")

#INSERT another_batch_file

#CODE

script = create.create_script()
```
"""
from builtins import object

import re
import codecs
import traceback
import sys
from django.conf import settings
from evennia.utils import utils

ENCODINGS = settings.ENCODINGS
CODE_INFO_HEADER = re.compile(r"\(.*?\)")

RE_INSERT = re.compile(r"^\#INSERT (.*)", re.MULTILINE)
RE_CLEANBLOCK = re.compile(r"^\#.*?$|^\s*$", re.MULTILINE)
RE_CMD_SPLIT = re.compile(r"^\#.*?$", re.MULTILINE)
RE_CODE_SPLIT = re.compile(r"(^\#CODE.*?$|^\#HEADER)$", re.MULTILINE)


#------------------------------------------------------------
# Helper function
#------------------------------------------------------------

def read_batchfile(pythonpath, file_ending='.py'):
    """
    This reads the contents of a batch-file.  Filename is considered
    to be a python path to a batch file relative the directory
    specified in `settings.py`.

    file_ending specify which batchfile ending should be assumed (.ev
    or .py). The ending should not be included in the python path.

    Args:
        pythonpath (str): A dot-python path to a file.
        file_ending (str): The file ending of this file (.ev or .py)

    Returns:
        text (str): The text content of the batch file.

    Raises:
        IOError: If problems reading file.

    """

    # open the file
    abspaths = []
    for basepath in settings.BASE_BATCHPROCESS_PATHS:
        # note that pypath_to_realpath has already checked the file for existence
        if basepath.startswith("evennia"):
            basepath = basepath.split("evennia", 1)[-1]
        abspaths.extend(utils.pypath_to_realpath("%s.%s" % (basepath, pythonpath), file_ending))
    if not abspaths:
        raise IOError
    text = None
    decoderr = []
    for abspath in abspaths:
        # try different paths, until we get a match
        # we read the file directly into unicode.
        for file_encoding in ENCODINGS:
            # try different encodings, in order
            try:
                with codecs.open(abspath, 'r', encoding=file_encoding) as fobj:
                    text = fobj.read()
            except (ValueError, UnicodeDecodeError) as e:
                # this means an encoding error; try another encoding
                decoderr.append(str(e))
                continue
            break
    if not text and decoderr:
        raise UnicodeDecodeError("\n".join(decoderr))

    return text


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
          1) # at the beginning of a line marks the end of the command before
               it. It is also a comment and any number of # can exist on
               subsequent lines (but not inside comments).
          2) #INSERT at the beginning of a line imports another
             batch-cmd file file and pastes it into the batch file as if
             it was written there.
          3) Commands are placed alone at the beginning of a line and their
             arguments are considered to be everything following (on any
             number of lines) until the next comment line beginning with #.
          4) Newlines are ignored in command definitions
          5) A completely empty line in a command line definition is condered
             a newline (so two empty lines is a paragraph).
          6) Excess spaces and indents inside arguments are stripped.

        """

        text = "".join(read_batchfile(pythonpath, file_ending='.ev'))

        def replace_insert(match):
            "Map replace entries"
            return "\#\n".join(self.parse_file(match.group(1)))

        # insert commands from inserted files
        text = RE_INSERT.sub(replace_insert, text)
        #text = re.sub(r"^\#INSERT (.*?)", replace_insert, text, flags=re.MULTILINE)
        # get all commands
        commands = RE_CMD_SPLIT.split(text)
        #commands = re.split(r"^\#.*?$", text, flags=re.MULTILINE)
        #remove eventual newline at the end of commands
        commands = [c.strip('\r\n') for c in commands]
        commands = [c for c in commands if c]

        return commands


#------------------------------------------------------------
#
# Batch-code processor
#
#------------------------------------------------------------

def tb_filename(tb):
    "Helper to get filename from traceback"
    return tb.tb_frame.f_code.co_filename


def tb_iter(tb):
    "Traceback iterator."
    while tb is not None:
        yield tb
        tb = tb.tb_next


class BatchCodeProcessor(object):
    """
    This implements a batch-code processor

    """

    def parse_file(self, pythonpath, debug=False):
        """
        This parses the lines of a batchfile according to the following
        rules:

        Args:
            pythonpath (str): The dot-python path to the file.
            debug (bool, optional): Insert delete-commands for
                deleting created objects.

        Returns:
            codeblocks (list): A list of all #CODE blocks.

        Notes:
            1. Lines starting with #HEADER starts a header block (ends other blocks)
            2. Lines starting with #CODE begins a code block (ends other blocks)
            3. #CODE headers may be of the following form:
                                  #CODE (info) objname, objname2, ...
            4. Lines starting with #INSERT are on form #INSERT filename.
            5. All lines outside blocks are stripped.
            6. All excess whitespace beginning/ending a block is stripped.

        """

        text = "".join(read_batchfile(pythonpath, file_ending='.py'))

        def clean_block(text):
            text = RE_CLEANBLOCK.sub("", text)
            #text = re.sub(r"^\#.*?$|^\s*$", "", text, flags=re.MULTILINE)
            return "\n".join([line for line in text.split("\n") if line])

        def replace_insert(match):
            "Map replace entries"
            return "\#\n".join(self.parse_file(match.group(1)))

        text = RE_INSERT.sub(replace_insert, text)
        #text = re.sub(r"^\#INSERT (.*?)", replace_insert, text, flags=re.MULTILINE)
        blocks = RE_CODE_SPLIT.split(text)
        #blocks = re.split(r"(^\#CODE.*?$|^\#HEADER)$", text, flags=re.MULTILINE)
        headers = []
        codes = [] # list of tuples (code, info, objtuple)
        if blocks:
            if blocks[0]:
                # the first block is either empty or an unmarked code block
                code = clean_block(blocks.pop(0))
                if code:
                    codes.append((code, ""))
            iblock = 0
            for block in blocks[::2]:
                # loop over every second component; these are the #CODE/#HEADERs
                if block.startswith("#HEADER"):
                    headers.append(clean_block(blocks[iblock + 1]))
                elif block.startswith("#CODE"):
                    match = re.search(r"\(.*?\)", block)
                    info = match.group() if match else ""
                    objs = []
                    if debug:
                        # insert auto-delete lines into code
                        objs = block[match.end():].split(",")
                        objs = ["# added by Evennia's debug mode\n%s.delete()" % obj.strip() for obj in objs if obj]
                    # build the code block
                    code = "\n".join([clean_block(blocks[iblock + 1])] + objs)
                    if code:
                        codes.append((code, info))
                iblock += 2

        # join the headers together to one header
        headers = "\n".join(headers)
        if codes:
            # add the headers at the top of each non-empty block
            codes = ["%s\n%s\n%s" % ("#CODE %s: " % tup[1], headers, tup[0]) for tup in codes if tup[0]]
        else:
            codes = ["#CODE: \n" + headers]
        return codes


    def code_exec(self, code, extra_environ=None, debug=False):
        """
        Execute a single code block, including imports and appending
        global vars.

        Args:
            code (str): Code to run.
            extra_environ (dict): Environment variables to run with code.
            debug (bool, optional): Insert delete statements for objects.

        Returns:
            err (str or None): An error code or None (ok).

        """
        # define the execution environment
        environdict = {"settings_module": settings}
        environ = "settings_module.configure()"
        if extra_environ:
            for key, value in extra_environ.items():
                environdict[key] = value

        # initializing the django settings at the top of code
        code = "# auto-added by Evennia\n" \
               "try: %s\n" \
               "except RuntimeError: pass\n" \
               "finally: del settings_module\n%s" % (environ, code)

        # execute the block
        try:
            exec(code, environdict)
        except Exception:
            etype, value, tb = sys.exc_info()

            fname = tb_filename(tb)
            for tb in tb_iter(tb):
                if fname != tb_filename(tb):
                    break
            lineno = tb.tb_lineno - 1
            err = ""
            for iline, line in enumerate(code.split("\n")):
                if iline == lineno:
                    err += "\n{w%02i{n: %s" % (iline + 1, line)
                elif lineno - 5 < iline < lineno + 5:
                    err += "\n%02i: %s" % (iline + 1, line)

            err += "\n".join(traceback.format_exception(etype, value, tb))
            return err
        return None

BATCHCMD = BatchCommandProcessor()
BATCHCODE = BatchCodeProcessor()
