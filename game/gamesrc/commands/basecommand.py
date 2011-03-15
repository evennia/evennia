
"""


Inherit from this and 
overload the member functions to define your own commands. 
See src/commands/default/muxcommand.py for an example. 

"""

from src.commands.command import Command as BaseCommand
from src.commands.default.muxcommand import MuxCommand as BaseMuxCommand
from src.utils import utils 

class MuxCommand(BaseMuxCommand):
    """
    This sets up the basis for a Evennia's 'MUX-like' command
    style. The idea is that most other Mux-related commands should
    just inherit from this and don't have to implement much parsing of
    their own unless they do something particularly advanced.

    Note that the class's __doc__ string (this text) is used by
    Evennia to create the automatic help entry for the command, so
    make sure to document consistently here.

    Most of the time your child classes should not need to implement
    parse() at all, but only the main func() method for doing useful 
    things. See examples in src/commands/default.
 
    """
    
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
           self.locks - lock definition for this command, usually cmd:<func>
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
        it here). The rest of the command is stored in self.args, which can start
        with the switch indicator /. 

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
        # parse all that makes it a MUX command (don't remove this)
        super(MuxCommand, self).parse()
        
    def func(self):
        """
        This is the hook function that actually does all the work. It is called
        by the cmdhandler right after self.parser() finishes, and so has access
        to all the variables defined therein.         
        """    
        # this can be removed in your child class, it's just 
        # printing the ingoing variables as a demo
        super(MuxCommand, self).func()



class Command(BaseCommand):
    """
    This is the basic command class (MuxCommand is a child of
    this). Inherit from this if you want to create your own 
    command styles.

    Note that the class's __doc__ string (this text) is
    used by Evennia to create the automatic help entry for
    the command, so make sure to document consistently here. 
    """
    def access(self, srcobj):
        """
        This is called by the cmdhandler to determine
        if srcobj is allowed to execute this command. This
        also determines if the command appears in help etc.

        By default, We use checks of the 'cmd' type of lock to determine
        if the command should be run. 
        """
        return super(Command, self).access(srcobj)

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
        """
        pass


    def func(self):
        """
        This is the hook function that actually does all the work. It is called
         by the cmdhandler right after self.parser() finishes, and so has access
         to all the variables defined therein.         
        """

        # this can be removed in your child class, it's just 
        # printing the ingoing variables as a demo
        super(MuxCommand, self).func()


