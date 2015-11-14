"""
The command template for the default MUX-style command set. There
is also an Player/OOC version that makes sure caller is a Player object.
"""

from evennia.utils import utils
from evennia.commands.command import Command

# limit symbol import for API
__all__ = ("MuxCommand", "MuxPlayerCommand")

class MuxCommand(Command):
    """
    This sets up the basis for a MUX command. The idea
    is that most other Mux-related commands should just
    inherit from this and don't have to implement much
    parsing of their own unless they do something particularly
    advanced.

    Note that the class's __doc__ string (this text) is
    used by Evennia to create the automatic help entry for
    the command, so make sure to document consistently here.
    """
    def has_perm(self, srcobj):
        """
        This is called by the cmdhandler to determine
        if srcobj is allowed to execute this command.
        We just show it here for completeness - we
        are satisfied using the default check in Command.
        """
        return super(MuxCommand, self).has_perm(srcobj)

    def at_pre_cmd(self):
        """
        This hook is called before self.parse() on all commands
        """
        pass

    def at_post_cmd(self):
        """
        This hook is called after the command has finished executing
        (after self.func()).
        """
        pass

    def parse(self):
        """
        This method is called by the cmdhandler once the command name
        has been identified. It creates a new set of member variables
        that can be later accessed from self.func() (see below)

        The following variables are available for our use when entering this
        method (from the command definition, and assigned on the fly by the
        cmdhandler):
           self.key - the name of this command ('look')
           self.aliases - the aliases of this cmd ('l')
           self.permissions - permission string for this command
           self.help_category - overall category of command

           self.caller - the object calling this command
           self.cmdstring - the actual command name used to call this
                            (this allows you to know which alias was used,
                             for example)
           self.args - the raw input; everything following self.cmdstring.
           self.cmdset - the cmdset from which this command was picked. Not
                         often used (useful for commands like 'help' or to
                         list all available commands etc)
           self.obj - the object on which this command was defined. It is often
                         the same as self.caller.

        A MUX command has the following possible syntax:

          name[ with several words][/switch[/switch..]] arg1[,arg2,...] [[=|,] arg[,..]]

        The 'name[ with several words]' part is already dealt with by the
        cmdhandler at this point, and stored in self.cmdname (we don't use
        it here). The rest of the command is stored in self.args, which can
        start with the switch indicator /.

        This parser breaks self.args into its constituents and stores them in the
        following variables:
          self.switches = [list of /switches (without the /)]
          self.raw = This is the raw argument input, including switches
          self.args = This is re-defined to be everything *except* the switches
          self.lhs = Everything to the left of = (lhs:'left-hand side'). If
                     no = is found, this is identical to self.args.
          self.rhs: Everything to the right of = (rhs:'right-hand side').
                    If no '=' is found, this is None.
          self.lhslist - [self.lhs split into a list by comma]
          self.rhslist - [list of self.rhs split into a list by comma]
          self.arglist = [list of space-separated args (stripped, including '=' if it exists)]

          All args and list members are stripped of excess whitespace around the
          strings, but case is preserved.
        """
        raw = self.args
        args = raw.strip()

        # split out switches
        switches = []
        if args and len(args) > 1 and args[0] == "/":
            # we have a switch, or a set of switches. These end with a space.
            switches = args[1:].split(None, 1)
            if len(switches) > 1:
                switches, args = switches
                switches = switches.split('/')
            else:
                args = ""
                switches = switches[0].split('/')
        arglist = [arg.strip() for arg in args.split()]

        # check for arg1, arg2, ... = argA, argB, ... constructs
        lhs, rhs = args, None
        lhslist, rhslist = [arg.strip() for arg in args.split(',')], []
        if args and '=' in args:
            lhs, rhs = [arg.strip() for arg in args.split('=', 1)]
            lhslist = [arg.strip() for arg in lhs.split(',')]
            rhslist = [arg.strip() for arg in rhs.split(',')]

        # save to object properties:
        self.raw = raw
        self.switches = switches
        self.args = args.strip()
        self.arglist = arglist
        self.lhs = lhs
        self.lhslist = lhslist
        self.rhs = rhs
        self.rhslist = rhslist

    def func(self):
        """
        This is the hook function that actually does all the work. It is called
         by the cmdhandler right after self.parser() finishes, and so has access
         to all the variables defined therein.
        """
        # a simple test command to show the available properties
        string = "-" * 50
        string += "\n{w%s{n - Command variables from evennia:\n" % self.key
        string += "-" * 50
        string += "\nname of cmd (self.key): {w%s{n\n" % self.key
        string += "cmd aliases (self.aliases): {w%s{n\n" % self.aliases
        string += "cmd locks (self.locks): {w%s{n\n" % self.locks
        string += "help category (self.help_category): {w%s{n\n" % self.help_category
        string += "object calling (self.caller): {w%s{n\n" % self.caller
        string += "object storing cmdset (self.obj): {w%s{n\n" % self.obj
        string += "command string given (self.cmdstring): {w%s{n\n" % self.cmdstring
        # show cmdset.key instead of cmdset to shorten output
        string += utils.fill("current cmdset (self.cmdset): {w%s{n\n" % self.cmdset)


        string += "\n" + "-" * 50
        string +=  "\nVariables from MuxCommand baseclass\n"
        string += "-" * 50
        string += "\nraw argument (self.raw): {w%s{n \n" % self.raw
        string += "cmd args (self.args): {w%s{n\n" % self.args
        string += "cmd switches (self.switches): {w%s{n\n" % self.switches
        string += "space-separated arg list (self.arglist): {w%s{n\n" % self.arglist
        string += "lhs, left-hand side of '=' (self.lhs): {w%s{n\n" % self.lhs
        string += "lhs, comma separated (self.lhslist): {w%s{n\n" % self.lhslist
        string += "rhs, right-hand side of '=' (self.rhs): {w%s{n\n" % self.rhs
        string += "rhs, comma separated (self.rhslist): {w%s{n\n" % self.rhslist
        string += "-" * 50
        self.caller.msg(string)

class MuxPlayerCommand(MuxCommand):
    """
    This is an on-Player version of the MuxCommand. Since these commands sit
    on Players rather than on Characters/Objects, we need to check
    this in the parser.

    Player commands are available also when puppeting a Character, it's
    just that they are applied with a lower priority and are always
    available, also when disconnected from a character (i.e. "ooc").

    This class makes sure that caller is always a Player object, while
    creating a new property "character" that is set only if a
    character is actually attached to this Player and Session.
    """
    def parse(self):
        """
        We run the parent parser as usual, then fix the result
        """
        super(MuxPlayerCommand, self).parse()

        if utils.inherits_from(self.caller, "evennia.objects.objects.DefaultObject"):
            # caller is an Object/Character
            self.character = self.caller
            self.caller = self.caller.player
        elif utils.inherits_from(self.caller, "evennia.players.players.DefaultPlayer"):
            # caller was already a Player
            self.character = self.caller.get_puppet(self.session)
        else:
            self.character = None
