"""
Handlers for the actions system.

There are two handlers in the system, CharacterActionHandler for characters and
RoomActionHandler for rooms. Each of them is stored in its owner's "actions" 
attr, as set inside the typeclasses.characters and typeclasses.rooms files.

The brunt of the work in the actions system is done by the ActionSystemScript
attached to each room, referenced via the RoomActionHandler's "script" property.
"""


# Because world.actions.typeclasses.ActionCharacter uses CharacterActionHandler,
# world.actions.handlers.py cannot import world.actions.typeclasses.py as it
# would be a circular import. Thus, we use DefaultCharacter instead.

from time import time
from evennia import DefaultCharacter 
from evennia.utils import logger
from evennia.contrib.actions.actions import Turn
from evennia.contrib.actions.scripts import ActionSystemScript
from evennia.contrib.actions.utils import (process_queue, format_action_desc,
    handle_invalid)


class CharacterActionHandler(object):
    """
    
    """

    def __init__(self, owner):
        """
        sets owner (Character), the character to which this handler is attached
        """
        self.owner = owner


    def setup(self, override=False):
        if not self.owner.attributes.has("actions") or override:
            self.owner.db.actions = {}

        if not self.owner.db.actions.has_key('list') or override:
            # reset the character's action list
            self.list = []

        if not self.owner.db.actions.has_key('new') or override:
            self.new = "ignore"

        if not self.owner.db.actions.has_key('alarm') or override:
            self.alarm = False

        if not self.owner.db.actions.has_key('movespeed') or override:
            self.movespeed = None

        if not self.owner.db.actions.has_key('movetype') or override:
            self.movetype = None

        if not self.owner.db.actions.has_key('movebps') or override:
            self.movebps = None

        if not self.owner.db.actions.has_key('active') or override:
            self.active = True


    @property
    def alarm(self):
        """
        True or False; states whether the character's alarm state is on or off.
        Whenever any character in the room has their alarm set to True, the
        room should be in turn-based mode. When all of the characters in the
        room have their alarm set to false, the room should be in real-time
        mode.
        """
        return self.owner.db.actions['alarm']


    @alarm.setter
    def alarm(self, value):
        """
        If an alarm becomes set, attempt to enter TB mode. If an alarm becomes
        unset, attempt to leave TB mode.
        """
        room = self.owner.location 

        if not self.owner.db.actions.has_key("alarm"): 
            # This should only happen when the object is being created
            self.owner.db.actions['alarm'] = value

        elif value == True and not self.alarm:
            # Send a message to all characters in the room.
            # If the character is invisibile, they will still give a room echo
            # when raising their alarm, but will show up as "Someone".
            room.actions.display(self.owner, " has become alarmed.", default=True)

            # Activate the character's alarm status
            self.owner.db.actions['alarm'] = True

            self.owner.location.actions.try_tb()

        elif value == False and self.alarm:
            # check if the character is the target or the performer of
            # any alarming actions. The character's alarm cannot be turned off
            # in these cases.
            actions = self.owner.location.actions.list
            l1 = [action for action in actions if action['owner'] == self.owner
                  and action['invokes_tb']]
            l2 = [action for action in actions if action['target'] and
                  action['target'] == self.owner and action['invokes_tb']]
            if l1 or l2:
                self.owner.msg("Cannot turn off the alarmed status for " +
                    "{0} due to ongoing alarming actions.".format(
                    self.owner.key))
            else:
                # The character's alarm can be deactivated.

                # Send a message to all characters in the room.
                # If the character is invisibile, they will still give a room
                # echo when raising their alarm, but will show up as "Someone".
                room.actions.display(self.owner, " has stopped being alarmed.", 
                    default=True)

                # Deactivate the character's alarm status            
                self.owner.db.actions['alarm'] = False
            
                self.owner.location.actions.try_rt()


    @property
    def list(self):
        """
        Returns a list of the actions queued up by the character.
        This does not include the character's ongoing actions.
        """
        return self.owner.db.actions['list']


    @list.setter
    def list(self, value):
        self.owner.db.actions['list'] = value


    @property
    def new(self):
        """
        Values are either "override", "queue" or "ignore".
        A value of "override" means that new actions input by the character
        override and cancel any current actions that use the same bodyparts.
        A value of "queue" means that newly-input actions that use the same
        bodyparts as ongoing actions are queued and will only be performed
        once the current actions sharing the same bodyparts are finished.
        A value of "ignore" means that newly-input actions that use the same
        bodyparts as ongoing actions will not be performed at all.
        """
        return self.owner.db.actions['new']


    @new.setter
    def new(self, value):
        if value == "override" or value == "queue" or value == "ignore":
            self.owner.db.actions['new'] = value
        else:
            raise ValueError("Attempting to set value of {0}".format(value) +
                " to actions new setting for character {0};".fomat(self.owner) + 
                " actions new setting must be either \"override\", \"queue\"" +
                " or \"ignore\".") 


    @property
    def movespeed(self):
        """        
        A function that takes a Character (the owner) as an argument and
        returns the character's movement speed.
        """
        return self.owner.db.actions['movespeed']


    @movespeed.setter
    def movespeed(self, value):
        self.owner.db.actions['movespeed'] = value


    @property
    def movetype(self):
        """
        A string that describes the character's current movement mode.
        It is used in automatic invocations of the movebps function
        by MoveOut actions (described in actions.py)
        """
        return self.owner.db.actions['movetype']


    @movetype.setter
    def movetype(self, value):

        # To prevent characters from moving in multiple directions
        # at once, changing a character's movement type cancels that
        # character's present MoveOut action and is impossible if
        # the character is performing a MoveIn action.

        if owner.actions.movebps and owner.actions.movetype:
            bodyparts = owner.actions.movebps(owner.actions.movetype)
        else:
            self.owner.db.actions['movetype'] = value
            return

        actions = [x for x in self.owner.location.db.actions if
            x['owner'] == self.owner and x['bodyparts'] == bodyparts]
        if actions:
            # Check whether an uncancellable action with the same bodyparts
            # as the present movement mode (e.g. MoveIn) is being undertaken
            # by the character.
            if [x for x in actions if not x['cancellable']]:
                self.owner.msg("The movement mode cannot be changed at " +
                    "present.")
                return

            for action in actions:
                # Cancel all actions that use the same bodyparts as the
                # present movement mode (e.g. Moveout)

                # The reason we are not selecting actions by key is that
                # someone, somewhere may want to subclass MoveOut and MoveIn.
                action['at_cancel'](action)            

        self.owner.db.actions['movetype'] = value

    @property
    def movebps(self):
        """
        A function that determines which bodyparts are to be used for a given
        movement mode. The function takes one argument, the movement mode
        itself (a string). 
        """
        return self.owner.db.actions['movebps']


    @movebps.setter
    def movebps(self, value):
        self.owner.db.actions['movebps'] = value

    
    @property
    def active(self):
        """
        A boolean value that states whether or not the character is active.
        Inactive characters are stunned, paralyzed, dead or in another
        incapacitating condition.
        """
        return self.owner.db.actions['active']   


    @active.setter
    def active(self, value):
        """
        Setting this to True renders the character inactive, clearing 
        their actions and preventing them from adding actions to the room's
        actions list.

        Setting it to False renders the character active again, processing
        their queue.
        """
        if type(value) != bool:
            raise ValueError("Cannot set the active property for character " +
                "{0}: value must be a boolean.".format(self.owner.key))
        
        if value:
            self.owner.db.actions['active'] = True
            process_queue(self.owner)
        else:
            self.stop(ongoing=True, queued=False)
            self.owner.db.actions['active'] = False


    def add(self, action):
        """
        add the action to the bottom of the owner's actions queue
        """
        self.owner.msg("|madding {0} to action queue|n".format(action['key']))
        self.list.append(action)


    def pop(self, action):
        """
        bring the action up from the queue to the room's action list
        (assumes it's already been ensured that no other actions from the 
        owner sharing similar bodyparts are in the room's action list)

        Note: In turn-based mode, popping must only occur while the popped
        action's owner is referenced by the actions_turnof variable
        """
        self.remove(action)
        action = dict(action)
        self.owner.location.actions.add(action)


    def remove(self, action):
        """
        remove the action from the owner's actions queue
        """
        self.owner.msg("|mremoving {0} from action queue|n".format(action['key']))
        self.list.remove(action)
 

    def done(self):
        """
        During turn-based mode, concludes the turn for the owner

        [WIP] Prohibit "done" from working when the character has issued a
        movement action, crafting action or any other action with a sufficiently
        large duration this turn, in order to prevent abuse of turn-based mode
        for performing large numbers of commands very quickly.
        """
        mode = self.owner.location.actions.mode
        turnof = self.owner.location.actions.turnof
        if mode == "TB" and turnof == self.owner:
            # Bring the action system forward
            self.owner.location.actions.run_script()
        elif mode == "TB":
            self.owner.msg("You cannot finish your turn without it being " +
                "your turn to begin with.")
        else:
            self.owner.msg("You cannot finish your turn without being in " +
                "turn-based mode to begin with.")

    def stop(self, ongoing=True, queued=False):
        """
        Cancels the character's ongoing actions if ongoing is set to True,
        and removes the character's queued actions if queued is set to True.
        """
        if queued:
            # First stop all enqueued actions if the action calls for it, 
            # to ensure that cancelling the ongoing actions will not load
            # any actions from the queue
            for action in self.owner.actions.list:
                self.owner.actions.remove(action)

        if ongoing:
            # Then cancel all ongoing actions
            for action in self.owner.location.actions.list:
                if action['owner'] == self.owner:
                    action['at_cancel'](action)


    def unpuppet(self):
        """
        Cancels all of the character's queued and ongoing actions, then
        removes the character's alert, which causes the room to attempt to
        enter real-time mode.
        """
        self.stop(ongoing=True, queued=True)
        self.alarm = False


class RoomActionHandler(object):
    """
    Lists the ongoing action in the room, keeps track of turn-related
    information and provides methods for 
    """

    def __init__(self, owner):
        """
        sets owner (Room), the room to which this handler is attached
        """
        self.owner = owner


    def setup(self, override=False):
        if not self.owner.db.actions or override:
            self.owner.db.actions = {}

        if not self.owner.db.actions.has_key("list") or override:
            self.list = []

        if not self.owner.db.actions.has_key("time") or override:
            self.time = time() 

        if not self.owner.db.actions.has_key("mode") or override:
            self.mode = "RT"

        if not self.owner.db.actions.has_key("turnof") or override:
            self.turnof = None
 
        if not self.owner.db.actions.has_key("acted") or override:
            self.acted = []

        if not self.owner.db.actions.has_key("view") or override:
            self.view = None

        if override:
            for script in self.owner.scripts.all():
                if type(script) == ActionSystemScript:
                    self.owner.scripts.stop(script)
        if not self.owner.scripts.get("ActionSystemScript"):
            self.owner.scripts.add(ActionSystemScript, autostart=False)
            self.script = self.owner.scripts.get("ActionSystemScript")[0]
            self.script.start()

    @property
    def list(self):
        """
        the list of all ongoing actions in the room
        """
        return self.owner.db.actions['list']


    @list.setter
    def list(self, value):
        self.owner.db.actions['list'] = value


    @property
    def mode(self):
        """  
        Either "RT" or "TB". Says whether the room is in real-time
        or turn-based mode.
        """
        return self.owner.db.actions['mode']


    @mode.setter
    def mode(self, value):
        if value == "RT" or value == "TB":
            self.owner.db.actions['mode'] = value
        else:
            raise ValueError("Attempting to set value of {0}".format(value) +
                " to actions mode in room {0};".fomat(self.owner) + 
                " actions mode must be either \"RT\" or \"TB\". " )


    @property
    def turnof(self):
        """
        The Character object whose turn it is (applicable only in TB mode)
        """
        return self.owner.db.actions['turnof']


    @turnof.setter
    def turnof(self, value):
        self.owner.db.actions['turnof'] = value


    @property
    def time(self):
        """
        The current time as measured by the actions system. In real-time
        mode, this is likely the CPU time when the last action was performed.
        In turn-based mode, its value is not dependent on CPU time, but on
        the durations of the actions that have been performed so far.
        """
        return self.owner.db.actions['time']


    @time.setter
    def time(self, value):
        self.owner.db.actions['time'] = value


    @property
    def acted(self):
        """
        In turn-based mode, a list of all the actions that have been initiated
        this turn. Whether or not this list is empty determines what message a
        character gets when their turn ends.
        """
        return self.owner.db.actions['acted']


    @acted.setter
    def acted(self, value):
        self.owner.db.actions['acted'] = value


    @property
    def view(self):
        """
        A function that takes an object being viewed and a character viewing
        it, and returns the string representing a name of description of the
        object being viewed, which will be seen by the viewing character.
        The function may also return False, in which case no message is sent
        to the viewing character (useful in situations involving stealth).

        This function is used in the various messages echoed by the actions
        system. If it is not set or is set to None, the messages will display
        the key of the character being viewed.
        """
        return self.owner.db.actions['view']


    @view.setter
    def view(self, value):
        self.owner.db.actions['view'] = value


    @property
    def script(self):
        """
        Reference to the room's action script
        """
        return self.owner.db.actions['script']
    

    @script.setter
    def script(self, value):
        self.owner.db.actions['script'] = value


    def add(self, action):
        """
        add the new action to the room's action list in its proper position
        note that "action" must be an action dict, not an Action object
        """

       #[DEBUG]
        if action['owner'].tags.get("debug"):
            action['owner'].msg(
                "|mAdding action {0} to the actions queue of room {1}|n".format(
                action['key'], self.owner))

       # assign the action an appropriate onset and endtime
        if self.mode == 'RT':
            action['onset'] = time()
            action['endtime'] = action['onset'] + action['duration']

        elif self.mode == 'TB':
            action['onset'] = action['room'].actions.time
            action['endtime'] = action['onset'] + action['duration']

            # mark the room as having experienced the action this turn
            self.acted.append(action)

        actions = self.list

        # find the action on the list whose endtime exceeds that of the 
        # new action, insert the new action before it
        for other in actions:
            if other['endtime'] > action['endtime']:
                index = actions.index(other)
                actions.insert(index, action)
                break
        else:
            # if no such actions exist, just add the new action to the end
            # of the list
            index = len(actions)
            actions.append(action)

        # if in real-time mode, check if the action being processed is meant
        # to bring the room into turn-based mode
        if self.mode == 'RT':
            if action['invokes_tb']:

                # if the action is meant to switch to turn-based mode,
                # set an alarm on its owner as well as its target (if any
                # exists) and attempt to switch to turn-based mode.
                action['owner'].actions.alarm = True
                if (action['target'] and 
                    isinstance(action['target'], DefaultCharacter)):
                    action['target'].actions.alarm = True

            elif index == 0:

                #trigger the ActionSystemScript now
                self.run_script()

        # in turn-based mode, the person whose turn it is is deliberating on
        # their action. The freshly added action will only take effect after
        # their turn ends, i.e. after the turn-based script is restarted.
        # Thus, the add() method does not restart the script while in
        # turn-based mode.

        return True


    def remove(self, action):
        """
        remove the action from the room's action list
        """
        self.list.remove(action)


    def display(self, viewed, msg, target=None, data="", default=False):
        """
        Formats a message so that it is viewed by each character in the
        room according to the room's actions.view function.
        """
        for char in self.owner.contents:
            if isinstance(char, DefaultCharacter):
                if target or data:
                    parsed_msg = format_action_desc(self.owner, char, msg, 
                        target, data=data)
                else:
                    parsed_msg = msg

                if self.owner.actions.view:
                    name_viewed = self.owner.actions.view(viewed, char)
                else:
                    name_viewed = viewed.key.capitalize()

                if name_viewed == False and default:
                    name_viewed = "Someone"

                if parsed_msg[0] == " ":
                    parsed_msg = name_viewed + parsed_msg
                else:
                    parsed_msg = name_viewed + " " + parsed_msg

                if name_viewed:
                    char.msg(parsed_msg)

                # if name_viewed == False and not default, 
                # the message is not shown


    def handle_invalid(action, validate_result):
        """
        Handles an invalid action. By default, it notifies the MudInfo channel
        and removes the action from its room's actions list (if the room 
        exists) and from the owner's actions queue (if the owner exists).

        Overload this if you want invalid actions to be handled in a different
        way.
        """
        handle_invalid(action, validate_result)


    def try_rt(self):
        """
        attempt to switch to real-time mode
        """

        # first confirm that we are not already in real-time mode
        if self.mode == 'RT':
            return False

        # ensure that the room should not remain in TB mode
        if self.check_for_tb():
            return False

        # We have confirmed that the room is ready to enter RT mode.

        # convert the room's parameters to RT
        self.mode = "RT"
        self.turnof = None
        self.acted = []

        # convert all timers from TB to RT
        pre_time = self.time
        k_time = time()
        self.time = k_time
        for action in self.list:
            action['onset'] += k_time - pre_time
            action['endtime'] += k_time - pre_time

        # [WIP] Give each character a custom message based on their preferred
        # level of verbosity
        self.owner.msg_contents("Real-time mode has now begun. " + 
            "Characters are no longer affected by turn order.")

        # run the ActionSystemScript in real-time mode
        self.run_script()

        return True


    def try_tb(self):
        """
        attempt to switch to turn-based mode
        """
        # first confirm that we are not already in TB mode
        if self.mode == 'TB':
            return False

        # ensure that the room should not remain in RT mode
        if not self.check_for_tb():
            return False

        # We have confirmed that the room is ready to enter TB mode.
    
        # convert the room's parameters to TB
        self.mode = "TB"
        self.turnof = None # Should be set to None so that no one's turn 
            # is reported to have ended at the very start of TB mode
        self.owner.acted = []
        
        # convert all timers from RT to TB
        pre_time = self.time
        self.time = 0
        for action in self.list:
            action['onset'] -= pre_time
            action['endtime'] -= pre_time

        # Give everyone in the room a Turn action,
        # place all these actions at the start of the actions queue
        chars = [x for x in self.owner.contents 
                 if isinstance(x, DefaultCharacter)]
        for char in chars:
            char.msg("You have been given a turn action. ")
            Turn(char, self.owner, place_at_end=False)

        # [WIP] Give each character a custom message based on their preferred
        # level of verbosity
        self.owner.msg_contents("Turn-based mode has now begun. " + 
            "You may study the turn order and impending actions " + 
            "using the \"actions\" command.")

        # run the ActionSystemScript in turn-based mode
        self.run_script()

        return True

        
    def check_for_tb(self):
        """
        check whether the room should be in turn-based mode
        """
        # check for alarms
        chars = [x for x in self.owner.contents 
                 if isinstance(x, DefaultCharacter)]         
        for char in chars:
            if char.actions.alarm:
                return True
        return False


    def pause_script(self):
        """
        Pause the room's action script
        """
        self.script.pause()


    def schedule_script(self, interval):
        """
        Start a new iteration of the ActionSystemScript after <interval> seconds 
        """
        if not self.script.is_active:
            self.script.unpause()
        self.script.restart(interval=interval, repeats=0, start_delay=True)


    def run_script(self):
        """
        Start the ActionSystemScript immediately.
        """
        if not self.script.is_active:
            self.script.unpause()
        self.script.restart(interval=None, repeats=0, start_delay=False)



