"""
Commands that are part of the actions system but occur instantaneously
and typically allow for the tweaking of the character's settings as pertain
to that system.
"""

from evennia import CmdSet
from evennia.commands.command import Command
from evennia.utils import evmore
from evennia.contrib.actions.actions import MoveOut
from evennia.contrib.actions.utils import format_action_desc

class ActionCmdSet(CmdSet):
    """CmdSet for action-related commands."""
    key = "equip_cmdset"
    priority = 1

    def at_cmdset_creation(self):
        self.add(CmdTurnbased())
        self.add(CmdActSettings())
        self.add(CmdActions())
        self.add(CmdStop())
        self.add(CmdDone())
        self.add(CmdQueue())


class CmdTurnbased(Command):
    """
    activate, deactivate or check whether the character is in turn-based mode.

    Usage:
      turnbased [<on/off/status>]
      turns [<on/off/status>]
      tb [<on/off/status>]

    When typed without arguments, the command activates turn-based mode.

    If at least one character in a given room has activated turn-based mode, 
    that room will be in turn-based mode.
    """
    key = "turnbased"
    aliases = ["tb", "turns"]
    locks = "cmd:all()"
    #arg_regex = r"$"

    def func(self):
        if self.args.find("on") != -1 or not self.args:
            if not self.caller.actions.turnbased:
                self.caller.actions.turnbased = True

            else:
                self.caller.msg("{0} is already in turn-based mode.".format(
                    self.caller.key.capitalize()))

        elif self.args.find("off") != -1:
            if self.caller.actions.turnbased:
                self.caller.actions.turnbased = False

            else:
                self.caller.msg("{0} was not in turn-based mode ".format(
                    self.caller.key.capitalize()) + "to begin with.")

        elif self.args.find("stat") != -1:
            status = "" if self.caller.actions.turnbased else "not "
            self.caller.msg("{0} is {1}in turn-based mode.".format(
                self.caller.key.capitalize(), status))

        else:
            self.caller.msg("Invalid argument for the \"turnbased\" " + 
                "command. Please specify \"on\", \"off\", \"status\" or no " +
                "argument at all.")


class CmdActSettings(Command):
    """
    modify your actions system settings

    Usage:
        actsettings <argument> <value>
        actset <argument> <value>
    
    possible arguments:
        new <ignore/override/queue> - if a new action issued by the character
            shares the same bodyparts as an action previously issued by the
            character, this setting decides whether the new action is ignored,
            the old action is overriden or the new action is added to a queue,
            to be processed once all actions sharing the same bodyparts as it
            are completed.

    On its own, displays the character's current settings in relation to the
    actions system.
    """

    key = "actsettings"
    aliases = ["actset"]
    locks = "cmd:all()"
    #arg_regex = r"$"

    def func(self):
        arglist = self.args.split(" ")
        arglist = [x for x in arglist if x] # Remove empty entries

        if arglist:
            arg1 = arglist[0]

            if len(arglist) > 1:
                arg2 = arglist[1]
            else:
                arg2 = None
        else:
            self.caller.msg("Please specify an argument for the actsettings " +
                "command.")
            return

        if arg1.find("new") != -1:
            if not arg2:
                self.caller.msg("Please specify an argument for " +
                    "\"actsettings new\". Acceptable arguments are " +
                    "\"ignore\", \"override\" and \"queue\".")
                return

            if arg2.find("ignore") != -1:
                self.caller.actions.new = "ignore"
                self.caller.msg("\"New\" actions setting is now "+
                    "\"ignore\". \n"+
                    "New actions of yours that use the same " +
                    "bodyparts as ongoing actions will be ignored.")

            elif arg2.find("over") != -1:
                self.caller.actions.new = "override"
                self.caller.msg("\"New\" actions setting is now "+
                    "\"override\". \n"+
                    "Ongoing actions of yours that use the same " +
                    "bodypart as a new action of yours will be overridden.")

            elif arg2.find("queue") != -1:
                self.caller.actions.new = "queue"
                self.caller.msg("\"New\" actions setting is now "+
                    "\"queue\". \n"+
                    "New actions of yours that use the same " +
                    "bodyparts as ongoing actions will be queued.")

            else:
                self.caller.msg("The only acceptable arguments to " +
                    "\"actsettings new\" are \"ignore\", \"override\" " + 
                    "and \"queue\".")
        else:
            self.caller.msg("The only acceptable argument to \"actsettings\""+
            "is \"new\".")


class CmdActions(Command):
    """
    display all ongoing actions in the room

    Usage:
        actions
        act
        acts
    """
    key = "actions"
    aliases = ["act", "acts"]
    locks = "cmd:all()"
    #arg_regex = r"$"

    def func(self):
        room = self.caller.location
        s = "Ongoing actions in {0}:\n".format(room.key)
        if room.actions.list:
            for action in room.actions.list:
                desc = format_action_desc(room, action['owner'], 
                    action['desc'], action['target'], data=action['data'])

                if room.actions.view:
                    name = room.actions.view(action['owner'], self.caller)
                else:
                    name = action['owner'].key.capitalize()
                if not name == False:
                    s += "* {0} is {1}.\n".format(name, desc)
        else:
            s += "None"

        evmore.msg(self.caller, s)


class CmdStop(Command):
    """
    stop all of your ongoing and/or queued actions

    Usage:
        stop [<ongoing/queue>]

    Simply using "stop" will stop both ongoing and queued actions.
    """

    key = "stop"
    #aliases = [""]
    locks = "cmd:all()"
    #arg_regex = r"$"

    def func(self):
        if self.args.find("on") != -1:
            self.caller.msg("Stopping all ongoing actions.")
            self.caller.actions.stop(ongoing=True, queued=False)

        elif self.args.find("queue") != -1:
            self.caller.msg("Clearing all enqueued actions.")
            self.caller.actions.stop(ongoing=False, queued=True)

        elif self.args == "":
            self.caller.msg("Stopping all ongoing and enqueued actions.")
            self.caller.actions.stop(ongoing=True, queued=True)

        else:
            self.caller.msg("Invalid argument. Either type \"stop\" "+
                "on its own or with the \"ongoing\" or \"queue\" argument.")


class CmdDone(Command):
    """
    ends the character's turn during turn-based situations

    Usage:
        done
        do
    """
    key = "done"
    aliases = ["do"]
    locks = "cmd:all()"

    def func(self):
        self.caller.actions.done()


class CmdQueue(Command):
    """
    displays the character's action queue

    Usage:
        queue
        que
    """
    key="queue"
    aliases=["que"]
    locks = "cmd:all()"

    def func(self):
        s = "You currently have the following actions enqueued: \n"
        if self.caller.actions.list:
            for action in self.caller.actions.list:
                desc = format_action_desc(action['room'], self.caller, 
                    action['desc'], action['target'], data=action['data'])
                s += " * " + desc + "\n"
        else:
            s += "None\n"
        evmore.msg(self.caller, s)


class ActionExitCommand(Command):
    """
    This command will assign a movement action to the object and is to
    be used by the ActionExit typeclass. The duration of the action
    equals the exit's distance value divided by the character's movement
    speed (if the character has a movement speed value at all).
    """
    obj = None
   
    def func(self): 
        if self.obj.access(self.caller, 'traverse'):
            # we may begin the movement attempt.
            MoveOut(self.caller, self.caller.location, self.obj)

        else:
            # exit is locked
            if self.obj.db.err_traverse:
                # if exit has a better error message, let's use it.
                self.caller.msg(self.obj.db.err_traverse)
            else:
                # No shorthand error message. Call hook.
                self.obj.at_failed_traverse(self.caller)
		
