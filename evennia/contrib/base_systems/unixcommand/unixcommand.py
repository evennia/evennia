"""
Unix-like Command style parent

Evennia contribution, Vincent Le Geoff 2017

This module contains a command class that allows for unix-style command syntax in-game, using
--options, positional arguments and stuff like -n 10 etc similarly to a unix command. It might not
the best syntax for the average player but can be really useful for builders when they need to have
a single command do many things with many options. It uses the ArgumentParser from Python's standard
library under the hood.

To use, inherit `UnixCommand` from this module from your own commands. You need
to override two methods:

- The `init_parser` method, which adds options to the parser. Note that you should normally
    *not* override the normal `parse` method when inheriting from `UnixCommand`.
- The `func` method, called to execute the command once parsed (like any Command).

Here's a short example:

```python
from evennia.contrib.base_systems.unixcommand import UnixCommand


class CmdPlant(UnixCommand):

    '''
    Plant a tree or plant.

    This command is used to plant something in the room you are in.

    Examples:
      plant orange -a 8
      plant strawberry --hidden
      plant potato --hidden --age 5

    '''

    key = "plant"

    def init_parser(self):
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


class ParseError(Exception):

    """An error occurred during parsing."""

    pass


class UnixCommandParser(argparse.ArgumentParser):

    """A modifier command parser for unix commands.

    This parser is used to replace `argparse.ArgumentParser`.  It
    is aware of the command calling it, and can more easily report to
    the caller.  Some features (like the "brutal exit" of the original
    parser) are disabled or replaced.  This parser is used by UnixCommand
    and creating one directly isn't recommended nor necessary.  Even
    adding a sub-command will use this replaced parser automatically.

    """

    def __init__(self, prog, description="", epilog="", command=None, **kwargs):
        """
        Build a UnixCommandParser with a link to the command using it.

        Args:
            prog (str): the program name (usually the command key).
            description (str): a very brief line to show in the usage text.
            epilog (str): the epilog to show below options.
            command (Command): the command calling the parser.

        Keyword Args:
            Additional keyword arguments are directly sent to
            `argparse.ArgumentParser`.  You will find them on the
            [parser's documentation](https://docs.python.org/2/library/argparse.html).

        Note:
            It's doubtful you would need to create this parser manually.
            The `UnixCommand` does that automatically.  If you create
            sub-commands, this class will be used.

        """
        prog = prog or command.key
        super().__init__(
            prog=prog, description=description, conflict_handler="resolve", add_help=False, **kwargs
        )
        self.command = command
        self.post_help = epilog

        def n_exit(code=None, msg=None):
            raise ParseError(msg)

        self.exit = n_exit

        # Replace the -h/--help
        self.add_argument(
            "-h", "--help", nargs=0, action=HelpAction, help="display the command help"
        )

    def format_usage(self):
        """Return the usage line.

        Note:
            This method is present to return the raw-escaped usage line,
            in order to avoid unintentional color codes.

        """
        return raw(super().format_usage())

    def format_help(self):
        """Return the parser help, including its epilog.

        Note:
            This method is present to return the raw-escaped help,
            in order to avoid unintentional color codes.  Color codes
            in the epilog (the command docstring) are supported.

        """
        autohelp = raw(super().format_help())
        return "\n" + autohelp + "\n" + self.post_help

    def print_usage(self, file=None):
        """Print the usage to the caller.

        Args:
            file (file-object): not used here, the caller is used.

        Note:
            This method will override `argparse.ArgumentParser`'s in order
            to not display the help on stdout or stderr, but to the
            command's caller.

        """
        if self.command:
            self.command.msg(self.format_usage().strip())

    def print_help(self, file=None):
        """Print the help to the caller.

        Args:
            file (file-object): not used here, the caller is used.

        Note:
            This method will override `argparse.ArgumentParser`'s in order
            to not display the help on stdout or stderr, but to the
            command's caller.

        """
        if self.command:
            self.command.msg(self.format_help().strip())


class HelpAction(argparse.Action):

    """Override the -h/--help action in the default parser.

    Using the default -h/--help will call the exit function in different
    ways, preventing the entire help message to be provided.  Hence
    this override.

    """

    def __call__(self, parser, namespace, values, option_string=None):
        """If asked for help, display to the caller."""
        if parser.command:
            parser.command.msg(parser.format_help().strip())
            parser.exit(0, "")


class UnixCommand(Command):
    """
    Unix-type commands, supporting short and long options.

    This command syntax uses the Unix-style commands with short options
    (-X) and long options (--something).  The `argparse` module is
    used to parse the command.

    In order to use it, you should override two methods:
    - `init_parser`: this method is called when the command is created.
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
        """
        The lockhandler works the same as for objects.
        optional kwargs will be set as properties on the Command at runtime,
        overloading evential same-named class properties.

        """
        super().__init__(**kwargs)

        # Create the empty UnixCommandParser, inheriting argparse.ArgumentParser
        lines = dedent(self.__doc__.strip("\n")).splitlines()
        description = lines[0].strip()
        epilog = "\n".join(lines[1:]).strip()
        self.parser = UnixCommandParser(None, description, epilog, command=self)

        # Fill the argument parser
        self.init_parser()

    def init_parser(self):
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
            `init_parser` instead.

        """
        try:
            self.opts = self.parser.parse_args(shlex.split(self.args))
        except ParseError as err:
            msg = str(err)
            if msg:
                self.msg(msg)
            raise InterruptCommand
