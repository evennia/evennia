"""
Module containing the UnixCommand class.

This command allows to use unix-like options in game commands.  It is
not the best parser for players, but can be really useful for builders
when they need to have a single command to do many things with many
options.

The UnixCommand can be ovverridden to have your commands parsed.
You will need to override two methods:
- The `init` method, which adds options to the parser.
- The `func` method, called to execute the command once parsed.

Here's a short example:

```python
class CmdPlant(UnixCommand):

    '''
    Plant a tree or plant.

    This command is used to plant a tree or plant in the room you are in.

    Examples:
      plant orange -a 8
      plant strawberry --hidden
      plant potato --hidden --age 5

    '''

    key = "plant"

    def init(self):
        "Add the arguments to the parser."
        # 'self.parser' inherits `argparse.ArgumentParser`
        self.parser.add_argument("key",
                help="the key of the plant to be planted here")
        self.parser.add_argument("-a", "--age", type=int,
                default=1, help="the age of the plant to be planted")
        self.parser.add_argument("--hidden", action="store_true",
                help="should the newly-planted plant be hidden to players?")

    def func(self):
        "func is called only if the parser succeeded."
        # 'self.opts' contains the parsed options
        key = self.opts.key
        age = self.opts.age
        hidden = self.opts.hidden
        self.msg("Going to plant '{}', age={}, hidden={}.".format(
                key, age, hidden))
```

To see the full power of argparse and the types of supported options, visit
[the documentation of argparse](https://docs.python.org/2/library/argparse.html).

"""

import argparse
import shlex
from textwrap import dedent

from evennia import Command, InterruptCommand
from evennia.utils.ansi import raw

class UnixCommand(Command):
    """
    Unix-type commands, supporting short and long options.

    This command syntax uses the Unix-style commands with short options
    (-X) and long options (--something).  The `argparse` module is
    used to parse the command.

    In order to use it, you should override two methods:
    - `init`: the init method is called when the command is created.
      It can be used to set options in the parser.  `self.parser`
      contains the `argparse.ArgumentParser`, so you can add arguments
      here.
    - `func`: this method is called to execute the command, but after
      the parser has checked the arguments given to it are valid.
      You can access the namespace of valid arguments in `self.opts`
      at this point.

    The help of UnixCommands is derived from the docstring, in a
    slightly different way than usual: the first line of the docstring
    is used to represent the program description (the very short
    line at the top of the help message).  The other lines below are
    used as the program's "epilog", displayed below the options.  It
    means in your docstring, you don't have to write the options.
    They will be automatically provided by the parser and displayed
    accordingly.  The `argparse` module provides a default '-h' or
    '--help' option on the command.  Typing |whelp commandname|n will
    display the same as |wcommandname -h|n, though this behavior can
    be changed.

    """

    def __init__(self, **kwargs):
        super(UnixCommand, self).__init__()

        # Create the empty EvenniaParser, inheriting argparse.ArgumentParser
        lines = dedent(self.__doc__.strip("\n")).splitlines()
        description = lines[0].strip()
        epilog = "\n".join(lines[1:]).strip()
        self.parser = EvenniaParser(None, description, epilog, command=self)

        # Fill the argument parser
        self.init()

    def init(self):
        """
        Configure the argument parser, adding in options.

        Note:
            This method is to be overridden in order to add options
            to the argument parser.  Use `self.parser`, which contains
            the `argparse.ArgumentParser`.  You can, for instance,
            use its `add_argument` method.

        """
        pass

    def func(self):
        """Override to handle the command execution."""
        pass

    def get_help(self, caller, cmdset):
        """
        Return the help message for this command and this caller.

        Args:
            caller (Object or Player): the caller asking for help on the command.
            cmdset (CmdSet): the command set (if you need additional commands).

        Returns:
            docstring (str): the help text to provide the caller for this command.

        """
        return self.parser.format_help()

    def parse(self):
        """
        Process arguments provided in `self.args`.

        Note:
            You should not override this method.  Consider overriding
            `init` instead.

        """
        try:
            self.opts = self.parser.parse_args(shlex.split(self.args))
        except ParseError as err:
            msg = str(err)
            if msg:
                self.msg(msg)
            raise InterruptCommand


class ParseError(Exception):

    """An error occurred during parsing."""

    pass


class EvenniaParser(argparse.ArgumentParser):

    """A parser just for Evennia."""

    def __init__(self, prog, description="", epilog="", command=None, **kwargs):
        prog = prog or command.key
        super(EvenniaParser, self).__init__(
                prog=prog, description=description,
                conflict_handler='resolve', add_help=False, **kwargs)
        self.command = command
        self.post_help = epilog
        def n_exit(code=None, msg=None):
            raise ParseError(msg)

        self.exit = n_exit

        # Replace the -h/--help
        self.add_argument("-h", "--hel", nargs=0, action=HelpAction, help="display heeeelp")

    def format_usage(self):
        """Return the usage line."""
        return raw(super(EvenniaParser, self).format_usage())

    def format_help(self):
        """Return the parser help, including its epilog."""
        autohelp = raw(super(EvenniaParser, self).format_help())
        return "\n" + autohelp + "\n" + self.post_help

    def print_usage(self, file=None):
        """Print the usage to the caller."""
        if self.command:
            self.command.msg(self.format_usage().strip())

    def print_help(self, file=None):
        """Print the help to the caller."""
        if self.command:
            self.command.msg(self.format_help().strip())


class HelpAction(argparse.Action):

    """Override the -h/--he.p."""

    def __call__(self, parser, namespace, values, option_string=None):
        if parser.command:
            parser.command.msg(parser.format_help().strip())
            parser.exit(0, "")
