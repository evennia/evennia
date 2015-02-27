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

from evennia.comms.models import ChannelDB
from evennia.utils import create

# The command keys the engine is calling
# (the actual names all start with __)
from evennia.commands.cmdhandler import CMD_NOINPUT
from evennia.commands.cmdhandler import CMD_NOMATCH
from evennia.commands.cmdhandler import CMD_MULTIMATCH
from evennia.commands.cmdhandler import CMD_CHANNEL

from evennia.commands.default.muxcommand import MuxCommand

# Command called when there is no input at line
# (i.e. an lone return key)


class SystemNoInput(MuxCommand):
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
class SystemNoMatch(MuxCommand):
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
# Command called when there were mulitple matches to the command.
#
class SystemMultimatch(MuxCommand):
    """
    Multiple command matches.

    The cmdhandler adds a special attribute 'matches' to this
    system command.

      matches = [(candidate, cmd) , (candidate, cmd), ...],

    where candidate is an instance of evennia.commands.cmdparser.CommandCandidate
    and cmd is an an instantiated Command object matching the candidate.
    """
    key = CMD_MULTIMATCH
    locks = "cmd:all()"

    def format_multimatches(self, caller, matches):
        """
        Format multiple command matches to a useful error.

        This is copied directly from the default method in
        evennia.commands.cmdhandler.

        """
        string = "There were multiple matches:"
        for num, match in enumerate(matches):
            # each match is a tuple (candidate, cmd)
            candidate, cmd = match

            is_channel = hasattr(cmd, "is_channel") and cmd.is_channel
            if is_channel:
                is_channel = " (channel)"
            else:
                is_channel = ""
            is_exit = hasattr(cmd, "is_exit") and cmd.is_exit
            if is_exit and cmd.destination:
                is_exit = " (exit to %s)" % cmd.destination
            else:
                is_exit = ""

            id1 = ""
            id2 = ""
            if not (is_channel or is_exit) and (hasattr(cmd, 'obj') and cmd.obj != caller):
                # the command is defined on some other object
                id1 = "%s-" % cmd.obj.name
                id2 = " (%s-%s)" % (num + 1, candidate.cmdname)
            else:
                id1 = "%s-" % (num + 1)
                id2 = ""
            string += "\n  %s%s%s%s%s" % (id1, candidate.cmdname, id2, is_channel, is_exit)
        return string

    def func(self):
        """
        argument to cmd is a comma-separated string of
        all the clashing matches.
        """
        string = self.format_multimatches(self.caller, self.matches)
        self.msg(string)


# Command called when the command given at the command line
# was identified as a channel name, like there existing a
# channel named 'ooc' and the user wrote
#  > ooc Hello!

class SystemSendToChannel(MuxCommand):
    """
    This is a special command that the cmdhandler calls
    when it detects that the command given matches
    an existing Channel object key (or alias).
    """

    key = CMD_CHANNEL
    locks = "cmd:all()"

    def parse(self):
        channelname, msg = self.args.split(':', 1)
        self.args = channelname.strip(), msg.strip()

    def func(self):
        """
        Create a new message and send it to channel, using
        the already formatted input.
        """
        caller = self.caller
        channelkey, msg = self.args
        if not msg:
            caller.msg("Say what?")
            return
        channel = ChannelDB.objects.get_channel(channelkey)
        if not channel:
            caller.msg("Channel '%s' not found." % channelkey)
            return
        if not channel.has_connection(caller):
            string = "You are not connected to channel '%s'."
            caller.msg(string % channelkey)
            return
        if not channel.access(caller, 'send'):
            string = "You are not permitted to send to channel '%s'."
            caller.msg(string % channelkey)
            return
        msg = "[%s] %s: %s" % (channel.key, caller.name, msg)
        msgobj = create.create_message(caller, msg, channels=[channel])
        channel.msg(msgobj)
