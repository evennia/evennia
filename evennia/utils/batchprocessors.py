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
that looks identical to normal Python files. The difference from
importing and running any Python module is that the batch-code module
is loaded as a file and executed directly, so changes to the file will
apply immediately without a server @reload.

Optionally, one can add some special commented tokens to split the
execution of the code for the benefit of the batchprocessor's
interactive- and debug-modes. This allows to conveniently step through
the code and re-run sections of it easily during development.

Code blocks are marked by commented tokens alone on a line:

#HEADER - This denotes code that should be pasted at the top of all
         other code. Multiple HEADER statements - regardless of where
         it exists in the file - is the same as one big block.
         Observe that changes to variables made in one block is not
         preserved between blocks!
#CODE - This designates a code block that will be executed like a
       stand-alone piece of code together with any HEADER(s)
       defined. It is mainly used as a way to mark stop points for
       the interactive mode of the batchprocessor. If no CODE block
       is defined in the module, the entire module (including HEADERS)
       is assumed to be a CODE block.
#INSERT path.filename - This imports another batch_code.py file and
      runs it in the given position. The inserted file will retain
      its own HEADERs which will not be mixed with the headers of
      this file.

Importing works as normal. The following variables are automatically
made available in the script namespace.

- `caller` -  The object executing the batchscript
- `DEBUG` - This is a boolean marking if the batchprocessor is running
            in debug mode. It can be checked to e.g. delete created objects
            when running a CODE block multiple times during testing.
            (avoids creating a slew of same-named db objects)


Example batch.py file
-----------------------------------

```
#HEADER

from django.conf import settings
from evennia.utils import create
from types import basetypes

GOLD = 10

#CODE

obj = create.create_object(basetypes.Object)
obj2 = create.create_object(basetypes.Object)
obj.location = caller.location
obj.db.gold = GOLD
caller.msg("The object was created!")

if DEBUG:
    obj.delete()
    obj2.delete()

#INSERT another_batch_file

#CODE

script = create.create_script()
```
"""
import re
import codecs
import traceback
import sys
from django.conf import settings
from evennia.utils import utils

_ENCODINGS = settings.ENCODINGS
_RE_INSERT = re.compile(r"^\#INSERT (.*)$", re.MULTILINE)
_RE_CLEANBLOCK = re.compile(r"^\#.*?$|^\s*$", re.MULTILINE)
_RE_CMD_SPLIT = re.compile(r"^\#.*?$", re.MULTILINE)
_RE_CODE_OR_HEADER = re.compile(
    r"((?:\A|^)#CODE|(?:/A|^)#HEADER|\A)(.*?)$(.*?)(?=^#CODE.*?$|^#HEADER.*?$|\Z)",
    re.MULTILINE + re.DOTALL,
)


# -------------------------------------------------------------
# Helper function
# -------------------------------------------------------------


def read_batchfile(pythonpath, file_ending=".py"):
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

    # find all possible absolute paths
    abspaths = utils.pypath_to_realpath(pythonpath, file_ending, settings.BASE_BATCHPROCESS_PATHS)
    if not abspaths:
        raise IOError("Absolute batchcmd paths could not be found.")
    text = None
    decoderr = []
    for abspath in abspaths:
        # try different paths, until we get a match
        # we read the file directly into string.
        for file_encoding in _ENCODINGS:
            # try different encodings, in order
            try:
                with codecs.open(abspath, "r", encoding=file_encoding) as fobj:
                    text = fobj.read()
            except (ValueError, UnicodeDecodeError) as e:
                # this means an encoding error; try another encoding
                decoderr.append(str(e))
                continue
            break
    if not text and decoderr:
        raise UnicodeDecodeError("\n".join(decoderr), bytearray(), 0, 0, "")

    return text


# -------------------------------------------------------------
#
# Batch-command processor
#
# -------------------------------------------------------------


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

        text = "".join(read_batchfile(pythonpath, file_ending=".ev"))

        def replace_insert(match):
            """Map replace entries"""
            try:
                path = match.group(1)
                return "\n#\n".join(self.parse_file(path))
            except IOError as err:
                raise IOError("#INSERT {} failed.".format(path))

        text = _RE_INSERT.sub(replace_insert, text)
        commands = _RE_CMD_SPLIT.split(text)
        commands = [c.strip("\r\n") for c in commands]
        commands = [c for c in commands if c]

        return commands


# -------------------------------------------------------------
#
# Batch-code processor
#
# -------------------------------------------------------------


def tb_filename(tb):
    """Helper to get filename from traceback"""
    return tb.tb_frame.f_code.co_filename


def tb_iter(tb):
    """Traceback iterator."""
    while tb is not None:
        yield tb
        tb = tb.tb_next


class BatchCodeProcessor(object):
    """
    This implements a batch-code processor

    """

    def parse_file(self, pythonpath):
        """
        This parses the lines of a batchfile according to the following
        rules:

        Args:
            pythonpath (str): The dot-python path to the file.

        Returns:
            codeblocks (list): A list of all #CODE blocks, each with
                prepended #HEADER data. If no #CODE blocks were found,
                this will be a list of one element.

        Notes:
            1. Code before a #CODE/HEADER block are considered part of
                the first code/header block or is the ONLY block if no
                #CODE/HEADER blocks are defined.
            2. Lines starting with #HEADER starts a header block (ends other blocks)
            3. Lines starting with #CODE begins a code block (ends other blocks)
            4. Lines starting with #INSERT are on form #INSERT filename. Code from
               this file are processed with their headers *separately* before
               being inserted at the point of the #INSERT.
            5. Code after the last block is considered part of the last header/code
               block

        """

        text = "".join(read_batchfile(pythonpath, file_ending=".py"))

        def replace_insert(match):
            """Run parse_file on the import before sub:ing it into this file"""
            path = match.group(1)
            try:
                return "# batchcode insert (%s):" % path + "\n".join(self.parse_file(path))
            except IOError as err:
                raise IOError("#INSERT {} failed.".format(path))

        # process and then insert code from all #INSERTS
        text = _RE_INSERT.sub(replace_insert, text)

        headers = []
        codes = []
        for imatch, match in enumerate(list(_RE_CODE_OR_HEADER.finditer(text))):
            mtype = match.group(1).strip()
            # we need to handle things differently at the start of the file
            if mtype:
                istart, iend = match.span(3)
            else:
                istart, iend = match.start(2), match.end(3)
            code = text[istart:iend]
            if mtype == "#HEADER":
                headers.append(code)
            else:  # either #CODE or matching from start of file
                codes.append(code)

        # join all headers together to one
        header = "# batchcode header:\n%s\n\n" % "\n\n".join(headers) if headers else ""
        # add header to each code block
        codes = ["%s# batchcode code:\n%s" % (header, code) for code in codes]
        return codes

    def code_exec(self, code, extra_environ=None, debug=False):
        """
        Execute a single code block, including imports and appending
        global vars.

        Args:
            code (str): Code to run.
            extra_environ (dict): Environment variables to run with code.
            debug (bool, optional): Set the DEBUG variable in the execution
                namespace.

        Returns:
            err (str or None): An error code or None (ok).

        """
        # define the execution environment
        environdict = {"settings_module": settings, "DEBUG": debug}
        for key, value in extra_environ.items():
            environdict[key] = value

        # initializing the django settings at the top of code
        code = (
            "# batchcode evennia initialization: \n"
            "try: settings_module.configure()\n"
            "except RuntimeError: pass\n"
            "finally: del settings_module\n\n%s" % code
        )

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
                    err += "\n|w%02i|n: %s" % (iline + 1, line)
                elif lineno - 5 < iline < lineno + 5:
                    err += "\n%02i: %s" % (iline + 1, line)

            err += "\n".join(traceback.format_exception(etype, value, tb))
            return err
        return None


BATCHCMD = BatchCommandProcessor()
BATCHCODE = BatchCodeProcessor()
