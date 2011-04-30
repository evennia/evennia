"""
This handler creates cmdsets on the fly, by searching
an object's location for valid exit objects. 
"""

from src.commands import cmdset, command


class ExitCommand(command.Command):
    "Simple identifier command"
    is_exit = True
    locks = "cmd:all()" # should always be set to this.
    destination = None 
    obj = None
    
    def func(self):
        "Default exit traverse if no syscommand is defined."

        if self.obj.access(self.caller, 'traverse'):
            # we may traverse the exit. 

            old_location = None 
            if hasattr(self.caller, "location"):
                old_location = self.caller.location                

            # call pre/post hooks and move object.
            self.obj.at_before_traverse(self.caller)
            self.caller.move_to(self.destination)            
            self.obj.at_after_traverse(self.caller, old_location)

        else:
            if self.obj.db.err_traverse:
                # if exit has a better error message, let's use it.
                self.caller.msg(self.obj.db.err_traverse)
            else:
                # No shorthand error message. Call hook.
                self.obj.at_fail_traverse(self.caller)
            
class ExitHandler(object):
    """
    The exithandler auto-creates 'commands' to represent exits in the
    room. It is called by cmdhandler when building its index of all
    viable commands.  This allows for exits to be processed along with
    all other inputs the player gives to the game. The handler tries 
    to intelligently cache exit objects to cut down on processing. 
    
    """
    
    def __init__(self):        
        "Setup cache storage"
        self.cached_exit_cmds = {}

    def clear(self, exitcmd=None):
        """
        Reset cache storage. If obj is given, only remove
        that object from cache. 
        """
        if exitcmd:
            # delete only a certain object from cache
            try:
                del self.cached_exit_cmds[exitcmd.id]
            except KeyError:
                pass
            return 
        # reset entire cache
        self.cached_exit_cmds = {}
    
    def get_cmdset(self, srcobj):
        """
        Search srcobjs location for valid exits, and
        return objects as stored in command set
        """    
        # create a quick "throw away" cmdset 
        exit_cmdset = cmdset.CmdSet(None)
        exit_cmdset.key = '_exitset'
        exit_cmdset.priority = 9
        exit_cmdset.duplicates = True 
        try:
            location = srcobj.location
        except Exception:
            location = None 
        if not location:
            # there can be no exits if there's no location
            return exit_cmdset

        # use exits to create searchable "commands" for the cmdhandler
        for exi in location.exits:
            if exi.id in self.cached_exit_cmds:
                # retrieve from cache 
                exit_cmdset.add(self.cached_exit_cmds[exi.id])
            else:
                # not in cache, create a new exit command
                cmd = ExitCommand()
                cmd.key = exi.name.strip().lower()
                cmd.obj = exi
                if exi.aliases:
                    cmd.aliases = exi.aliases
                cmd.destination = exi.destination
                exit_cmdset.add(cmd)
                self.cached_exit_cmds[exi.id] = cmd 
        return exit_cmdset

# The actual handler - call this to get exits 
EXITHANDLER = ExitHandler()
