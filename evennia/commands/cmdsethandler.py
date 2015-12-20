"""
CmdSethandler

The Cmdsethandler tracks an object's 'Current CmdSet', which is the
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
from builtins import object
from future.utils import raise_
import sys
from importlib import import_module
from inspect import trace
from django.conf import settings
from evennia.utils import logger, utils
from evennia.commands.cmdset import CmdSet
from evennia.server.models import ServerConfig

from django.utils.translation import ugettext as _
__all__ = ("import_cmdset", "CmdSetHandler")

_CACHED_CMDSETS = {}
_CMDSET_PATHS = utils.make_iter(settings.CMDSET_PATHS)

class _ErrorCmdSet(CmdSet):
    """
    This is a special cmdset used to report errors.
    """
    key = "_CMDSET_ERROR"
    errmessage = "Error when loading cmdset."

class _EmptyCmdSet(CmdSet):
    """
    This cmdset represents an empty cmdset
    """
    key = "_EMPTY_CMDSET"
    priority = -101
    mergetype = "Union"

def import_cmdset(path, cmdsetobj, emit_to_obj=None, no_logging=False):
    """
    This helper function is used by the cmdsethandler to load a cmdset
    instance from a python module, given a python_path. It's usually accessed
    through the cmdsethandler's add() and add_default() methods.
    path - This is the full path to the cmdset object on python dot-form

    Args:
        path (str): The path to the command set to load.
        cmdsetobj (CmdSet): The database object/typeclass on which this cmdset is to be
            assigned (this can be also channels and exits, as well as players
            but there will always be such an object)
        emit_to_obj (Object, optional): If given, error is emitted to
            this object (in addition to logging)
        no_logging (bool, optional): Don't log/send error messages.
            This can be useful if import_cmdset is just used to check if
            this is a valid python path or not.
    Returns:
        cmdset (CmdSet): The imported command set. If an error was
            encountered, `commands.cmdsethandler._ErrorCmdSet` is returned
            for the benefit of the handler.

    """
    python_paths = [path] + ["%s.%s" % (prefix, path)
                                    for prefix in _CMDSET_PATHS if not path.startswith(prefix)]
    errstring = ""
    for python_path in python_paths:

        if "." in  path:
            modpath, classname = python_path.rsplit(".", 1)
        else:
            raise ImportError("The path '%s' is not on the form modulepath.ClassName" % path)

        try:
            # first try to get from cache
            cmdsetclass = _CACHED_CMDSETS.get(python_path, None)

            if not cmdsetclass:
                try:
                    module = import_module(modpath, package="evennia")
                except ImportError:
                    if len(trace()) > 2:
                        # error in module, make sure to not hide it.
                        exc = sys.exc_info()
                        raise_(exc[1], None, exc[2])
                    else:
                        # try next suggested path
                        errstring += _("\n(Unsuccessfully tried '%s')." % python_path)
                        continue
                try:
                    cmdsetclass = getattr(module, classname)
                except AttributeError:
                    if len(trace()) > 2:
                        # Attribute error within module, don't hide it
                        exc = sys.exc_info()
                        raise_(exc[1], None, exc[2])
                    else:
                        errstring += _("\n(Unsuccessfully tried '%s')." % python_path)
                        continue
                _CACHED_CMDSETS[python_path] = cmdsetclass

            #instantiate the cmdset (and catch its errors)
            if callable(cmdsetclass):
                cmdsetclass = cmdsetclass(cmdsetobj)
            errstring = ""
            return cmdsetclass
        except ImportError as e:
            logger.log_trace()
            errstring += _("\nError loading cmdset {path}: \"{error}\"")
            errstring = errstring.format(path=python_path, error=e)
            break
        except KeyError:
            logger.log_trace()
            errstring += _("\nError in loading cmdset: No cmdset class '{classname}' in {path}.")
            errstring = errstring.format(classname=classname, path=python_path)
            break
        except SyntaxError as e:
            logger.log_trace()
            errstring += _("\nSyntaxError encountered when loading cmdset '{path}': \"{error}\".")
            errstring = errstring.format(path=python_path, error=e)
            break
        except Exception as e:
            logger.log_trace()
            errstring += _("\nCompile/Run error when loading cmdset '{path}': \"{error}\".")
            errstring = errstring.format(path=python_path, error=e)
            break

    if errstring:
        # returning an empty error cmdset
        errstring = errstring.strip()
        if not no_logging:
            logger.log_err(errstring)
            if emit_to_obj and not ServerConfig.objects.conf("server_starting_mode"):
                emit_to_obj.msg(errstring)
        err_cmdset = _ErrorCmdSet()
        err_cmdset.errmessage = errstring +  _("\n (See log for details.)")
        return err_cmdset

# classes


class CmdSetHandler(object):
    """
    The CmdSetHandler is always stored on an object, this object is supplied
    as an argument.

    The 'current' cmdset is the merged set currently active for this object.
    This is the set the game engine will retrieve when determining which
    commands are available to the object. The cmdset_stack holds a history of
    all CmdSets to allow the handler to remove/add cmdsets at will. Doing so
    will re-calculate the 'current' cmdset.
    """

    def __init__(self, obj, init_true=True):
        """
        This method is called whenever an object is recreated.

        Args:
            obj (Object): An reference to the game object this handler
                belongs to.
            init_true (bool, optional): Set when the handler is initializing
                and loads the current cmdset.

        """
        self.obj = obj

        # the id of the "merged" current cmdset for easy access.
        self.key = None
        # this holds the "merged" current command set
        self.current = None
        # this holds a history of CommandSets
        self.cmdset_stack = [_EmptyCmdSet(cmdsetobj=self.obj)]
        # this tracks which mergetypes are actually in play in the stack
        self.mergetype_stack = ["Union"]

        # the subset of the cmdset_paths that are to be stored in the database
        self.permanent_paths = [""]

        if init_true:
            self.update(init_mode=True) #is then called from the object __init__.

    def __str__(self):
        """
        Display current commands
        """

        string = ""
        mergelist = []
        if len(self.cmdset_stack) > 1:
            # We have more than one cmdset in stack; list them all
            for snum, cmdset in enumerate(self.cmdset_stack):
                mergetype = self.mergetype_stack[snum]
                permstring = "non-perm"
                if cmdset.permanent:
                    permstring = "perm"
                if mergetype != cmdset.mergetype:
                    mergetype = "%s^" % (mergetype)
                string += "\n %i: <%s (%s, prio %i, %s)>: %s" % \
                    (snum, cmdset.key, mergetype,
                     cmdset.priority, permstring, cmdset)
                mergelist.append(str(snum))
            string += "\n"

        # Display the currently active cmdset, limited by self.obj's permissions
        mergetype = self.mergetype_stack[-1]
        if mergetype != self.current.mergetype:
            merged_on = self.cmdset_stack[-2].key
            mergetype = _("custom {mergetype} on cmdset '{cmdset}'")
            mergetype = mergetype.format(mergetype=mergetype, cmdset=merged_on)
        if mergelist:
            tmpstring = _(" <Merged {mergelist} {mergetype}, prio {prio}>: {current}")
            string += tmpstring.format(mergelist="+".join(mergelist),
                                      mergetype=mergetype, prio=self.current.priority,
                                      current=self.current)
        else:
            permstring = "non-perm"
            if self.current.permanent:
                permstring = "perm"
            tmpstring = _(" <{key} ({mergetype}, prio {prio}, {permstring})>:\n {keylist}")
            string += tmpstring.format(key=self.current.key, mergetype=mergetype,
                                       prio=self.current.priority,
                                       permstring=permstring,
                                       keylist=", ".join(cmd.key for
                                           cmd in sorted(self.current, key=lambda o: o.key)))
        return string.strip()

    def _import_cmdset(self, cmdset_path, emit_to_obj=None):
        """
        Method wrapper for import_cmdset; Loads a cmdset from a
        module.

        Args:
            cmdset_path (str): The python path to an cmdset object.
            emit_to_obj (Object): The object to send error messages to

        Returns:
            cmdset (Cmdset): The imported cmdset.

        """
        if not emit_to_obj:
            emit_to_obj = self.obj
        return import_cmdset(cmdset_path, self.obj, emit_to_obj)

    def update(self, init_mode=False):
        """
        Re-adds all sets in the handler to have an updated current
        set.

        Args:
            init_mode (bool, optional): Used automatically right after
                this handler was created; it imports all permanent cmdsets
                from the database.
        """
        if init_mode:
            # reimport all permanent cmdsets
            storage = self.obj.cmdset_storage
            if storage:
                self.cmdset_stack = []
                for pos, path in enumerate(storage):
                    if pos == 0 and not path:
                        self.cmdset_stack = [_EmptyCmdSet(cmdsetobj=self.obj)]
                    elif path:
                        cmdset = self._import_cmdset(path)
                        if cmdset:
                            cmdset.permanent = cmdset.key != '_CMDSET_ERROR'
                            self.cmdset_stack.append(cmdset)

        # merge the stack into a new merged cmdset
        new_current = None
        self.mergetype_stack = []
        for cmdset in self.cmdset_stack:
            try:
                # for cmdset's '+' operator, order matters.
                new_current = cmdset + new_current
            except TypeError:
                continue
            self.mergetype_stack.append(new_current.actual_mergetype)
        self.current = new_current

    def add(self, cmdset, emit_to_obj=None, permanent=False, default_cmdset=False):
        """
        Add a cmdset to the handler, on top of the old ones, unless it
        is set as the default one (it will then end up at the bottom of the stack)

        Args:
            cmdset (CmdSet or str): Can be a cmdset object or the python path
                to such an object.
            emit_to_obj (Object, optional): An object to receive error messages.
            permanent (bool, optional): This cmdset will remain across a server reboot.
            default_cmdset (Cmdset, optional): Insert this to replace the
                default cmdset position (there is only one such position,
                always at the bottom of the stack).

        Notes:
          An interesting feature of this method is if you were to send
          it an *already instantiated cmdset* (i.e. not a class), the
          current cmdsethandler's obj attribute will then *not* be
          transferred over to this already instantiated set (this is
          because it might be used elsewhere and can cause strange
          effects).  This means you could in principle have the
          handler launch command sets tied to a *different* object
          than the handler. Not sure when this would be useful, but
          it's a 'quirk' that has to be documented.

        """
        if not (isinstance(cmdset, basestring) or utils.inherits_from(cmdset, CmdSet)):
            string = _("Only CmdSets can be added to the cmdsethandler!")
            raise Exception(string)

        if callable(cmdset):
            cmdset = cmdset(self.obj)
        elif isinstance(cmdset, basestring):
            # this is (maybe) a python path. Try to import from cache.
            cmdset = self._import_cmdset(cmdset)
        if cmdset and cmdset.key != '_CMDSET_ERROR':
            cmdset.permanent = permanent
            if permanent and cmdset.key != '_CMDSET_ERROR':
                # store the path permanently
                storage = self.obj.cmdset_storage or [""]
                if default_cmdset:
                    storage[0] = cmdset.path
                else:
                    storage.append(cmdset.path)
                self.obj.cmdset_storage = storage
            if default_cmdset:
                self.cmdset_stack[0] = cmdset
            else:
                self.cmdset_stack.append(cmdset)
            self.update()

    def add_default(self, cmdset, emit_to_obj=None, permanent=True):
        """
        Shortcut for adding a default cmdset.

        Args:
            cmdset (Cmdset): The Cmdset to add.
            emit_to_obj (Object, optional): Gets error messages
            permanent (bool, optional): The new Cmdset should survive a server reboot.

        """
        self.add(cmdset, emit_to_obj=emit_to_obj, permanent=permanent, default_cmdset=True)

    def remove(self, cmdset=None, default_cmdset=False):
        """
        Remove a cmdset from the  handler.

        Args:
            cmdset (CommandSet or str, optional): This can can be supplied either as a cmdset-key,
                an instance of the CmdSet or a python path to the cmdset.
                If no key is given, the last cmdset in the stack is
                removed. Whenever the cmdset_stack changes, the cmdset is
                updated. If default_cmdset is set, this argument is ignored.
            default_cmdset (bool, optional): If set, this will remove the
                default cmdset (at the bottom of the stack).

        """
        if default_cmdset:
            # remove the default cmdset only
            if self.cmdset_stack:
                cmdset = self.cmdset_stack[0]
                if cmdset.permanent:
                    storage = self.obj.cmdset_storage or [""]
                    storage[0] = ""
                    self.obj.cmdset_storage = storage
                self.cmdset_stack[0] = _EmptyCmdSet(cmdsetobj=self.obj)
            else:
                self.cmdset_stack = [_EmptyCmdSet(cmdsetobj=self.obj)]
            self.update()
            return

        if len(self.cmdset_stack) < 2:
            # don't allow deleting default cmdsets here.
            return

        if not cmdset:
            # remove the last one in the stack
            cmdset = self.cmdset_stack.pop()
            if cmdset.permanent:
                storage = self.obj.cmdset_storage
                storage.pop()
                self.obj.cmdset_storage = storage
        else:
            # try it as a callable
            if callable(cmdset) and hasattr(cmdset, 'path'):
                delcmdsets = [cset for cset in self.cmdset_stack[1:]
                              if cset.path == cmdset.path]
            else:
                # try it as a path or key
                delcmdsets = [cset for cset in self.cmdset_stack[1:]
                              if cset.path == cmdset or cset.key == cmdset]
            storage = []

            if any(cset.permanent for cset in delcmdsets):
                # only hit database if there's need to
                storage = self.obj.cmdset_storage
                updated = False
                for cset in delcmdsets:
                    if cset.permanent:
                        try:
                            storage.remove(cset.path)
                            updated = True
                        except ValueError:
                            pass
                if updated:
                    self.obj.cmdset_storage = storage
            for cset in delcmdsets:
                # clean the in-memory stack
                try:
                    self.cmdset_stack.remove(cset)
                except ValueError:
                    pass
        # re-sync the cmdsethandler.
        self.update()
    # legacy alias
    delete = remove

    def remove_default(self):
        """
        This explicitly deletes only the default cmdset.

        """
        self.remove(default_cmdset=True)
    # legacy alias
    delete_default = remove_default


    def all(self):
        """
        Show all cmdsets.

        Returns:
            cmdsets (list): All the command sets currently in the handler.

        """
        return self.cmdset_stack

    def clear(self):
        """
        Removes all Command Sets from the handler except the default one
        (use `self.remove_default` to remove that).

        """
        self.cmdset_stack = [self.cmdset_stack[0]]
        storage = self.obj.cmdset_storage
        if storage:
            storage = storage[0]
            self.obj.cmdset_storage = storage
        self.update()

    def has_cmdset(self, cmdset_key, must_be_default=False):
        """
        checks so the cmdsethandler contains a cmdset with the given key.

        Args:
            cmdset_key (str): Cmdset key to check
            must_be_default (bool, optional): Only return True if
                the checked cmdset is the default one.

        Returns:
            has_cmdset (bool): Whether or not the cmdset is in the handler.

        """
        if must_be_default:
            return self.cmdset_stack and self.cmdset_stack[0].key == cmdset_key
        else:
            return any([cmdset.key == cmdset_key for cmdset in self.cmdset_stack])

    def reset(self):
        """
        Force reload of all cmdsets in handler. This should be called
        after _CACHED_CMDSETS have been cleared (normally this is
        handled automatically by @reload).

        """
        new_cmdset_stack = []
        for cmdset in self.cmdset_stack:
            if cmdset.key == "_EMPTY_CMDSET":
                new_cmdset_stack.append(cmdset)
            else:
                new_cmdset_stack.append(self._import_cmdset(cmdset.path))
        self.cmdset_stack = new_cmdset_stack
        self.update()
