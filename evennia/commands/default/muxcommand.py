"""
The command template for the default MUX-style command set. There
is also an Account/OOC version that makes sure caller is an Account object.
"""

from evennia.commands.command import Command
from evennia.utils import utils

# limit symbol import for API
__all__ = ("MuxCommand", "MuxAccountCommand")


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
        return super().has_perm(srcobj)

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

        Optional variables to aid in parsing, if set:
          self.switch_options  - (tuple of valid /switches expected by this
                                  command (without the /))
          self.rhs_split       - Alternate string delimiter or tuple of strings
                                 to separate left/right hand sides. tuple form
                                 gives priority split to first string delimiter.

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
        # Without explicitly setting these attributes, they assume default values:
        if not hasattr(self, "switch_options"):
            self.switch_options = None
        if not hasattr(self, "rhs_split"):
            self.rhs_split = "="
        if not hasattr(self, "account_caller"):
            self.account_caller = False

        # split out switches
        switches, delimiters = [], self.rhs_split
        if self.switch_options:
            self.switch_options = [opt.lower() for opt in self.switch_options]
        if args and len(args) > 1 and raw[0] == "/":
            # we have a switch, or a set of switches. These end with a space.
            switches = args[1:].split(None, 1)
            if len(switches) > 1:
                switches, args = switches
                switches = switches.split("/")
            else:
                args = ""
                switches = switches[0].split("/")
            # If user-provides switches, parse them with parser switch options.
            if switches and self.switch_options:
                valid_switches, unused_switches, extra_switches = [], [], []
                for element in switches:
                    option_check = [opt for opt in self.switch_options if opt == element]
                    if not option_check:
                        option_check = [
                            opt for opt in self.switch_options if opt.startswith(element)
                        ]
                    match_count = len(option_check)
                    if match_count > 1:
                        extra_switches.extend(
                            option_check
                        )  # Either the option provided is ambiguous,
                    elif match_count == 1:
                        valid_switches.extend(option_check)  # or it is a valid option abbreviation,
                    elif match_count == 0:
                        unused_switches.append(element)  # or an extraneous option to be ignored.
                if extra_switches:  # User provided switches
                    self.msg(
                        "|g%s|n: |wAmbiguous switch supplied: Did you mean /|C%s|w?"
                        % (self.cmdstring, " |nor /|C".join(extra_switches))
                    )
                if unused_switches:
                    plural = "" if len(unused_switches) == 1 else "es"
                    self.msg(
                        '|g%s|n: |wExtra switch%s "/|C%s|w" ignored.'
                        % (self.cmdstring, plural, "|n, /|C".join(unused_switches))
                    )
                switches = valid_switches  # Only include valid_switches in command function call
        arglist = [arg.strip() for arg in args.split()]

        # check for arg1, arg2, ... = argA, argB, ... constructs
        lhs, rhs = args.strip(), None
        if lhs:
            if delimiters and hasattr(delimiters, "__iter__"):  # If delimiter is iterable,
                best_split = delimiters[0]  # (default to first delimiter)
                for this_split in delimiters:  # try each delimiter
                    if this_split in lhs:  # to find first successful split
                        best_split = this_split  # to be the best split.
                        break
            else:
                best_split = delimiters
            # Parse to separate left into left/right sides using best_split delimiter string
            if best_split in lhs:
                lhs, rhs = lhs.split(best_split, 1)
        # Trim user-injected whitespace
        rhs = rhs.strip() if rhs is not None else None
        lhs = lhs.strip()
        # Further split left/right sides by comma delimiter
        lhslist = [arg.strip() for arg in lhs.split(",")] if lhs is not None else []
        rhslist = [arg.strip() for arg in rhs.split(",")] if rhs is not None else []
        # save to object properties:
        self.raw = raw
        self.switches = switches
        self.args = args.strip()
        self.arglist = arglist
        self.lhs = lhs
        self.lhslist = lhslist
        self.rhs = rhs
        self.rhslist = rhslist

        # if the class has the account_caller property set on itself, we make
        # sure that self.caller is always the account if possible. We also create
        # a special property "character" for the puppeted object, if any. This
        # is convenient for commands defined on the Account only.
        if self.account_caller:
            if utils.inherits_from(self.caller, "evennia.objects.objects.DefaultObject"):
                # caller is an Object/Character
                self.character = self.caller
                self.caller = self.caller.account
            elif utils.inherits_from(self.caller, "evennia.accounts.accounts.DefaultAccount"):
                # caller was already an Account
                self.character = self.caller.get_puppet(self.session)
            else:
                self.character = None

    def get_command_info(self):
        """
        Update of parent class's get_command_info() for MuxCommand.
        """
        variables = "\n".join(
            " |w{}|n ({}): {}".format(key, type(val), val) for key, val in self.__dict__.items()
        )
        string = f"""
Command {self} has no defined `func()` - showing on-command variables: No child func() defined for {self} - available variables:
{variables}
        """
        self.caller.msg(string)
        # a simple test command to show the available properties
        string = "-" * 50
        string += f"\n|w{self.key}|n - Command variables from evennia:\n"
        string += "-" * 50
        string += f"\nname of cmd (self.key): |w{self.key}|n\n"
        string += f"cmd aliases (self.aliases): |w{self.aliases}|n\n"
        string += f"cmd locks (self.locks): |w{self.locks}|n\n"
        string += f"help category (self.help_category): |w{self.help_category}|n\n"
        string += f"object calling (self.caller): |w{self.caller}|n\n"
        string += f"object storing cmdset (self.obj): |w{self.obj}|n\n"
        string += f"command string given (self.cmdstring): |w{self.cmdstring}|n\n"
        # show cmdset.key instead of cmdset to shorten output
        string += utils.fill(f"current cmdset (self.cmdset): |w{self.cmdset}|n\n")
        string += "\n" + "-" * 50
        string += "\nVariables from MuxCommand baseclass\n"
        string += "-" * 50
        string += f"\nraw argument (self.raw): |w{self.raw}|n \n"
        string += f"cmd args (self.args): |w{self.args}|n\n"
        string += f"cmd switches (self.switches): |w{self.switches}|n\n"
        string += f"cmd options (self.switch_options): |w{self.switch_options}|n\n"
        string += f"cmd parse left/right using (self.rhs_split): |w{self.rhs_split}|n\n"
        string += f"space-separated arg list (self.arglist): |w{self.arglist}|n\n"
        string += f"lhs, left-hand side of '=' (self.lhs): |w{self.lhs}|n\n"
        string += f"lhs, comma separated (self.lhslist): |w{self.lhslist}|n\n"
        string += f"rhs, right-hand side of '=' (self.rhs): |w{self.rhs}|n\n"
        string += f"rhs, comma separated (self.rhslist): |w{self.rhslist}|n\n"
        string += "-" * 50
        self.caller.msg(string)

    def func(self):
        """
        This is the hook function that actually does all the work. It is called
         by the cmdhandler right after self.parser() finishes, and so has access
         to all the variables defined therein.
        """
        self.get_command_info()


class MuxAccountCommand(MuxCommand):
    """
    This is an on-Account version of the MuxCommand. Since these commands sit
    on Accounts rather than on Characters/Objects, we need to check
    this in the parser.

    Account commands are available also when puppeting a Character, it's
    just that they are applied with a lower priority and are always
    available, also when disconnected from a character (i.e. "ooc").

    This class makes sure that caller is always an Account object, while
    creating a new property "character" that is set only if a
    character is actually attached to this Account and Session.
    """

    account_caller = True  # Using MuxAccountCommand explicitly defaults the caller to an account
