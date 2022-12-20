"""
System commands

These are the default commands called by the system commandhandler
when various exceptions occur. If one of these commands are not
implemented and part of the current cmdset, the engine falls back
to a default solution instead.

Some system commands are shown in this module
as a REFERENCE only (they are not all added to Evennia's
default cmdset since they don't currently do anything differently from the
default backup systems hard-wired in the engine).

Overloading these commands in a cmdset can be used to create
interesting effects. An example is using the NoMatch system command
to implement a line-editor where you don't have to start each
line with a command (if there is no match to a known command,
the line is just added to the editor buffer).
"""

from django.conf import settings

# The command keys the engine is calling
# (the actual names all start with __)
from evennia.commands.cmdhandler import CMD_MULTIMATCH, CMD_NOINPUT, CMD_NOMATCH
from evennia.comms.models import ChannelDB
from evennia.utils import create, utils
from evennia.utils.utils import at_search_result

COMMAND_DEFAULT_CLASS = utils.class_from_module(settings.COMMAND_DEFAULT_CLASS)

# Command called when there is no input at line
# (i.e. an lone return key)


class SystemNoInput(COMMAND_DEFAULT_CLASS):
    """
    This is called when there is no input given
    """

    key = CMD_NOINPUT
    locks = "cmd:all()"

    def func(self):
        "Do nothing."
        pass


#
# Command called when there was no match to the
# command name
#
class SystemNoMatch(COMMAND_DEFAULT_CLASS):
    """
    No command was found matching the given input.
    """

    key = CMD_NOMATCH
    locks = "cmd:all()"

    def func(self):
        """
        This is given the failed raw string as input.
        """
        self.msg("Huh?")


#
# Command called when there were multiple matches to the command.
#
class SystemMultimatch(COMMAND_DEFAULT_CLASS):
    """
    Multiple command matches.

    The cmdhandler adds a special attribute 'matches' to this
    system command.

      matches = [(cmdname, args, cmdobj, cmdlen, mratio, raw_cmdname) , (cmdname, ...), ...]

    Here, `cmdname` is the command's name and `args` the rest of the incoming string,
    without said command name. `cmdobj` is the Command instance, the cmdlen is
    the same as len(cmdname) and mratio is a measure of how big a part of the
    full input string the cmdname takes up - an exact match would be 1.0. Finally,
    the `raw_cmdname` is the cmdname unmodified by eventual prefix-stripping.

    """

    key = CMD_MULTIMATCH
    locks = "cmd:all()"

    def func(self):
        """
        Handle multiple-matches by using the at_search_result default handler.

        """
        # this was set by the cmdparser and is a tuple
        #    (cmdname, args, cmdobj, cmdlen, mratio, raw_cmdname). See
        # evennia.commands.cmdparse.create_match for more details.
        matches = self.matches
        # at_search_result will itself msg the multimatch options to the caller.
        at_search_result([match[2] for match in matches], self.caller, query=matches[0][0])
