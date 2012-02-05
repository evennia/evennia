"""
The base Command class.

All commands in Evennia inherit from the 'Command' class in this module. 

"""

from src.locks.lockhandler import LockHandler
from src.utils.utils import is_iter

class CommandMeta(type):
    """
    This metaclass makes some minor on-the-fly convenience fixes to the command
    class in case the admin forgets to put things in lowercase etc. 
    """    
    def __init__(mcs, *args, **kwargs):
        """
        Simply make sure all data are stored as lowercase and
        do checking on all properties that should be in list form.
        Sets up locks to be more forgiving. 
        """
        mcs.key = mcs.key.lower()
        if mcs.aliases and not is_iter(mcs.aliases):
            try:
                mcs.aliases = mcs.aliases.split(',')
            except Exception: 
                mcs.aliases = []
        mcs.aliases = [str(alias).strip() for alias in mcs.aliases]

        # pre-process locks as defined in class definition
        temp = []
        if hasattr(mcs, 'permissions'):
            mcs.locks = mcs.permissions
        if not hasattr(mcs, 'locks'):
            # default if one forgets to define completely
            mcs.locks = "cmd:all()"
        for lockstring in mcs.locks.split(';'):
            if lockstring and not ':' in lockstring:
                lockstring = "cmd:%s" % lockstring
            temp.append(lockstring)
        mcs.lock_storage = ";".join(temp)

        mcs.help_category = mcs.help_category.lower()
        super(CommandMeta, mcs).__init__(*args, **kwargs)

#    The Command class is the basic unit of an Evennia command; when
#    defining new commands, the admin subclass this class and
#    define their own parser method to handle the input. The
#    advantage of this is inheritage; commands that have similar
#    structure can parse the input string the same way, minimizing
#    parsing errors. 
 
class Command(object):
    """
    Base command

    Usage:
      command [args]
    
    This is the base command class. Inherit from this
    to create new commands.         
    
    The cmdhandler makes the following variables available to the 
    command methods (so you can always assume them to be there):
    self.caller - the game object calling the command
    self.cmdstring - the command name used to trigger this command (allows
                     you to know which alias was used, for example)
    cmd.args - everything supplied to the command following the cmdstring
               (this is usually what is parsed in self.parse())
    cmd.cmdset - the cmdset from which this command was matched (useful only
                seldomly, notably for help-type commands, to create dynamic
                help entries and lists)
    cmd.obj - the object on which this command is defined. If a default command,
                 this is usually the same as caller. 

    (Note that this initial string is also used by the system to create the help
    entry for the command, so it's a good idea to format it similar to this one)
    """
    # Tie our metaclass, for some convenience cleanup
    __metaclass__ = CommandMeta

    # the main way to call this command (e.g. 'look')
    key = "command"
    # alternative ways to call the command (e.g. 'l', 'glance', 'examine')
    aliases = []
    # a list of lock definitions on the form cmd:[NOT] func(args) [ AND|OR][ NOT] func2(args)
    locks = ""
    # used by the help system to group commands in lists.
    help_category = "general"
    # There is also the property 'obj'. This gets set by the system 
    # on the fly to tie this particular command to a certain in-game entity.
    # self.obj should NOT be defined here since it will not be overwritten 
    # if it already exists. 

    def __init__(self):
        self.lockhandler = LockHandler(self)
    
    def __str__(self):
        "Print the command"
        return self.key
    
    def __eq__(self, cmd):
        """
        Compare two command instances to each other by matching their
        key and aliases.
        input can be either a cmd object or the name of a command.
        """
        try:
            return self.match(cmd.key)
        except AttributeError: # got a string
            return self.match(cmd)

    def __contains__(self, query):
        """
        This implements searches like 'if query in cmd'. It's a fuzzy matching
        used by the help system, returning True if query can be found
        as a substring of the commands key or its aliases. 

        input can be either a command object or a command name.
        """
        try:
            query = query.key
        except AttributeError: # we got a string
            pass
        return (query in self.key) or any(query in alias for alias in self.aliases)

    def match(self, cmdname):
        """
        This is called by the system when searching the available commands,
        in order to determine if this is the one we wanted. cmdname was
        previously extracted from the raw string by the system.
        cmdname is always lowercase when reaching this point.
        """
        return cmdname and ((cmdname == self.key) or (cmdname in self.aliases))

    def access(self, srcobj, access_type="cmd", default=False):
        """
        This hook is called by the cmdhandler to determine if srcobj
        is allowed to execute this command. It should return a boolean
        value and is not normally something that need to be changed since
        it's using the Evennia permission system directly. 
        """
        return self.lockhandler.check(srcobj, access_type, default=default)

    # Common Command hooks         

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
        Once the cmdhandler has identified this as the command we
        want, this function is run. If many of your commands have
        a similar syntax (for example 'cmd arg1 = arg2') you should simply
        define this once and just let other commands of the same form
        inherit from this. See the docstring of this module for 
        which object properties are available to use 
        (notably self.args).
        """        
        pass
        
    def func(self):
        """
        This is the actual executing part of the command. 
        It is called directly after self.parse(). See the docstring
        of this module for which object properties are available
        (beyond those set in self.parse()) 
        """        
                # a simple test command to show the available properties
        string = "-" * 50
        string += "\n{w%s{n - Command variables from evennia:\n" % self.key 
        string += "-" * 50
        string += "\nname of cmd (self.key): {w%s{n\n" % self.key 
        string += "cmd aliases (self.aliases): {w%s{n\n" % self.aliases
        string += "cmd perms (self.permissions): {w%s{n\n" % self.permissions
        string += "help category (self.help_category): {w%s{n\n" % self.help_category
        string += "object calling (self.caller): {w%s{n\n" % self.caller
        string += "object storing cmdset (self.obj): {w%s{n\n" % self.obj
        string += "command string given (self.cmdstring): {w%s{n\n" % self.cmdstring        
        # show cmdset.key instead of cmdset to shorten output
        string += utils.fill("current cmdset (self.cmdset): {w%s{n\n" % self.cmdset)
        
        self.caller.msg(string)
