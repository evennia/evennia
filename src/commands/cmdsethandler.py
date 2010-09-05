"""
CmdSethandler

The Cmdhandler tracks an object's 'Current CmdSet', which is the
current merged sum of all CmdSets added to it.

A CmdSet constitues a set of commands. The CmdSet works as a special
intelligent container that, when added to other CmdSet make sure that
same-name commands are treated correctly (usually so there are no
doublets).  This temporary but up-to-date merger of CmdSet is jointly
called the Current Cmset. It is this Current CmdSet that the
commandhandler looks through whenever a player enters a command (it
also adds CmdSets from objects in the room in real-time). All player
objects have a 'default cmdset' containing all the normal in-game mud
commands (look etc).

So what is all this cmdset complexity good for?

In its simplest form, a CmdSet has no commands, only a key name. In
this case the cmdset's use is up to each individual game - it can be
used by an AI module for example (mobs in cmdset 'roam' move from room
to room, in cmdset 'attack' they enter combat with players).

Defining commands in cmdsets offer some further powerful game-design
consequences however. Here are some examples:

As mentioned above, all players always have at least the Default
CmdSet.  This contains the set of all normal-use commands in-game,
stuff like look and @desc etc. Now assume our players end up in a dark
room. You don't want the player to be able to do much in that dark
room unless they light a candle. You could handle this by changing all
your normal commands to check if the player is in a dark room. This
rapidly goes unwieldly and error prone. Instead you just define a
cmdset with only those commands you want to be available in the 'dark'
cmdset - maybe a modified look command and a 'light candle' command -
and have this completely replace the default cmdset.

Another example: Say you want your players to be able to go
fishing. You could implement this as a 'fish' command that fails
whenever the player has no fishing rod. Easy enough.  But what if you
want to make fishing more complex - maybe you want four-five different
commands for throwing your line, reeling in, etc? Most players won't
(we assume) have fishing gear, and having all those detailed commands
is cluttering up the command list. And what if you want to use the
'throw' command also for throwing rocks etc instead of 'using it up'
for a minor thing like fishing?

So instead you put all those detailed fishing commands into their own
CommandSet called 'Fishing'. Whenever the player gives the command
'fish' (presumably the code checks there is also water nearby), only
THEN this CommandSet is added to the Cmdhandler of the player. The
'throw' command (which normally throws rocks) is replaced by the
custom 'fishing variant' of throw. What has happened is that the
Fishing CommandSet was merged on top of the Default ones, and due to
how we defined it, its command overrules the default ones.

When we are tired of fishing, we give the 'go home' command (or
whatever) and the Cmdhandler simply removes the fishing CommandSet
so that we are back at defaults (and can throw rocks again).

Since any number of CommandSets can be piled on top of each other, you
can then implement separate sets for different situations. For
example, you can have a 'On a boat' set, onto which you then tack on
the 'Fishing' set. Fishing from a boat? No problem!
"""
import traceback 
from src.utils import logger
from src.utils import create
from src.commands.cmdset import CmdSet
from src.scripts.scripts import AddCmdSet

CACHED_CMDSETS = {}

def import_cmdset(python_path, cmdsetobj, emit_to_obj=None, no_logging=False):
    """
    This helper function is used by the cmdsethandler to load a cmdset
    instance from a python module, given a python_path. It's usually accessed
    through the cmdsethandler's add() and add_default() methods. 
    python_path - This is the full path to the cmdset object. 
    cmsetobj - the database object/typeclass on which this cmdset is to be assigned 
               (this can be also channels and exits, as well as players but there will 
               always be such an object)
    emit_to_obj - if given, error is emitted to this object (in addition to logging)
    no_logging - don't log/send error messages. This can be useful if import_cmdset is just
                  used to check if this is a valid python path or not. 
    function returns None if an error was encountered or path not found.
    """        

    try:
        try:                        
            wanted_cache_key = python_path            
            cmdsetclass = CACHED_CMDSETS.get(wanted_cache_key, None)
            errstring = ""
            if not cmdsetclass:
                #print "cmdset %s not in cache. Reloading." % wanted_cache_key
                # Not in cache. Reload from disk.
                modulepath, classname = python_path.rsplit('.', 1)
                module = __import__(modulepath, fromlist=[True])
                cmdsetclass = module.__dict__[classname]                
                CACHED_CMDSETS[wanted_cache_key] = cmdsetclass            
            #print "cmdset %s found." % wanted_cache_key 
            #instantiate the cmdset (and catch its errors)
            if callable(cmdsetclass):
                cmdsetclass = cmdsetclass(cmdsetobj) 
            return cmdsetclass

        except ImportError:
            errstring = "Error loading cmdset: Couldn't import module '%s'."
            errstring = errstring % modulepath
            raise
        except KeyError:
            errstring = "Error in loading cmdset: No cmdset class '%s' in %s."
            errstring = errstring % (modulepath, classname)
            raise
        except Exception:            
            errstring = "\n%s\nCompile/Run error when loading cmdset '%s'."
            errstring = errstring % (traceback.format_exc(), python_path)
            raise
    except Exception:            
        if errstring and not no_logging:
            logger.log_trace()    
            if emit_to_obj:
                emit_to_obj.msg(errstring)
        raise # have to raise, or we will not see any errors in some situations!

# classes 

class CmdSetHandler(object):
    """
    The CmdSetHandler is always stored on an object, supplied as the argument.

    The 'current' cmdset is the merged set currently active for this object.
    This is the set the game engine will retrieve when determining which
    commands are available to the object. The cmdset_stack holds a history of all CmdSets
    to allow the handler to remove/add cmdsets at will. Doing so will re-calculate
    the 'current' cmdset. 
    """

    def __init__(self, obj, outside_access=True):
        """
        This method is called whenever an object is recreated. 

        obj - this is a reference to the game object this handler
              belongs to.
        outside_access - if false, the cmdparser will only retrieve
             this cmdset when it is its obj itself that is calling for it.
             (this is is good to use for player objects, since they
             should not have access to the cmdsets of other player
             objects).
        """
        self.obj = obj                
        # if false, only the object itself may use this handler
        # (this should be set especially by character objects)
        self.outside_access = outside_access

        # the id of the "merged" current cmdset for easy access. 
        self.key = None
        # this holds the "merged" current command set 
        self.current = None
        # this holds a history of CommandSets 
        self.cmdset_stack = [CmdSet(cmdsetobj=self.obj, key="Empty")]
        # this tracks which mergetypes are actually in play in the stack
        self.mergetype_stack = ["Union"] 
        self.update()
                                                                
    def __str__(self):
        "Display current commands"                
            
        string = ""
        if len(self.cmdset_stack) > 1:
            # We have more than one cmdset in stack; list them all
            num = 0
            #print self.cmdset_stack, self.mergetype_stack
            for snum, cmdset in enumerate(self.cmdset_stack):
                num = snum
                mergetype = self.mergetype_stack[snum]
                if mergetype != cmdset.mergetype:
                    mergetype = "%s^" % (mergetype)            
                string += "\n %i: <%s (%s, prio %i)>: %s" % \
                          (snum, cmdset.key, mergetype,
                           cmdset.priority, cmdset)
            string += "\n (combining %i cmdsets):" % (num+1)    
        else:
            string += "\n "

        # Display the currently active cmdset 
        mergetype = self.mergetype_stack[-1]  
        if mergetype != self.current.mergetype:
            merged_on = self.cmdset_stack[-2].key
            mergetype = "custom %s on %s" % (mergetype, merged_on)        
        string += " <%s (%s)> %s" % (self.current.key,
                                     mergetype, self.current)
        return string.strip() 

    def update(self):        
        """
        Re-adds all sets in the handler to have an updated
        current set. 
        """
        updated = None 
        self.mergetype_stack = []
        for cmdset in self.cmdset_stack:                
            try:
                # for cmdset's '+' operator, order matters.                 
                updated = cmdset + updated 
            except TypeError:
                continue
            self.mergetype_stack.append(updated.actual_mergetype)
        self.current = updated

    def import_cmdset(self, cmdset_path, emit_to_obj=None):
        """
        load a cmdset from a module.
        cmdset_path - the python path to an cmdset object. 
        emit_to_obj - object to send error messages to
        """
        if not emit_to_obj:
            emit_to_obj = self.obj
        return import_cmdset(cmdset_path, self.obj, emit_to_obj)
                    
    def add(self, cmdset, emit_to_obj=None, permanent=False):
        """
        Add a cmdset to the handler, on top of the old ones.
        Default is to not make this permanent (i.e. no script
        will be added to add the cmdset every server start/login).

        cmdset - can be a cmdset object or the python path to
                 such an object.
        emit_to_obj - an object to receive error messages. 
        permanent - create a script to automatically add the cmdset
                    every time the server starts/the object logins. 

        Note: An interesting feature of this method is if you were to
        send it an *already instantiated cmdset* (i.e. not a class),
        the current cmdsethandler's obj attribute will then *not* be
        transferred over to this already instantiated set (this is
        because it might be used elsewhere and can cause strange effects). 
        This means you could in principle have the handler
        launch command sets tied to a *different* object than the
        handler. Not sure when this would be useful, but it's a 'quirk'
        that has to be documented. 
        """
        if callable(cmdset):
            cmdset = cmdset(self.obj)
        elif isinstance(cmdset, basestring):
            # this is (maybe) a python path. Try to import from cache.
            cmdset = self.import_cmdset(cmdset, emit_to_obj)
        if cmdset:
            self.cmdset_stack.append(cmdset)                
            self.update()
        if permanent:
            # create a script to automatically add this cmdset at
            # startup. We don't start it here since the cmdset was 
            # already added above. 
            try:
                cmdset = "%s.%s" % (cmdset.__module__, cmdset.__name__)
            except Exception:
                logger.log_trace()
                return
            script = create.create_script(AddCmdSet)
            script.db.cmdset = cmdset
            script.db.add_default = False 
            self.obj.scripts.add(script, autostart=False)

    def add_default(self, cmdset, emit_to_obj=None, permanent=False):
        """
        Add a new default cmdset. If an old default existed,
        it is replaced. If permanent is set, a script will be created to 
                        add the cmdset to the object.
        cmdset - can be a cmdset object or the python path to
                 an instance of such an object. 
        emit_to_obj - an object to receive error messages. 
        permanent - create a script that assigns this script every
                    startup/login.
        See also the notes for self.add(), which applies here too.
        """       
        if callable(cmdset):
            cmdset = cmdset(self.obj)
        elif isinstance(cmdset, basestring):
            # this is (maybe) a python path. Try to import from cache.
            cmdset = self.import_cmdset(cmdset, emit_to_obj)            
        if cmdset:
            self.cmdset_stack[0] = cmdset 
            self.mergetype_stack[0] = cmdset.mergetype
            self.update()
        #print "add_default:", permanent
        if permanent:
            # create a script to automatically add this cmdset at
            # startup. We don't start it here since the cmdset was
            # already added above. 
            try:
                cmdset = "%s.%s" % (cmdset.__module__, cmdset.__class__.__name__)
            except Exception:
                #print traceback.format_exc()
                logger.log_trace()
                return
            #print "cmdset to add:", cmdset
            script = create.create_script(AddCmdSet)
            script.db.cmdset = cmdset
            script.db.add_default = True
            self.obj.scripts.add(script, key="add_default_cmdset", autostart=False)
        
    def delete(self, key_or_class=None):
        """
        Remove a cmdset from the  handler. If a key is supplied,
        it attempts to remove this. If no key is given,
        the last cmdset in the stack is removed. Whenever
        the cmdset_stack changes, the cmdset is updated.
        The default cmdset (first entry in stack) is never
        removed - remove it explicitly with delete_default.

        key_or_class - a specific cmdset key or a cmdset class (in
                       the latter case, *all* cmdsets of this class 
                       will be removed from handler!) 
        """
        if len(self.cmdset_stack) < 2:
            # don't allow deleting default cmdsets here. 
            return

        if not key_or_class:
            # remove the last one in the stack (except the default position)
            self.cmdset_stack.pop()
        else:
            # argument key is given, is it a key or a class?
            
            default_cmdset = self.cmdset_stack[0]

            if callable(key_or_class) and hasattr(key_or_class, '__name__'):
                # this is a callable with __name__ - we assume it's a class          
                self.cmdset_stack = [cmdset for cmdset in self.cmdset_stack[1:]
                                     if cmdset.__class__.__name__ != key_or_class.__name__]
            else:
                # try it as a string
                self.cmdset_stack = [cmdset for cmdset in self.cmdset_stack[1:]
                                     if cmdset.key != key_or_class]  

            self.cmdset_stack.insert(0, default_cmdset)

        # re-sync the cmdsethandler. 
        self.update()

    def delete_default(self):
        "This explicitly deletes the default cmdset. It's the only command that can."
        self.cmdset_stack[0] = CmdSet(cmdsetobj=self.obj, key="Empty")
        self.update()

    def all(self):
        """
        Returns the list of cmdsets. Mostly useful to check if stack if empty or not.
        """
        return self.cmdset_stack

    def clear(self):
        """
        Removes all extra Command sets from the handler, leaving only the
        default one.
        """
        self.cmdset_stack = [self.cmdset_stack[0]]
        self.mergetype_stack = [self.cmdset_stack[0].mergetype]
        self.update()
