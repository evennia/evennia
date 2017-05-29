"""
This module contains the Action class, along with the default actions Turn,
MoveIn and MoveOut. All actions used by the action system must be subclassed
from the Action class.

Note: always include a call to super when overloading the base functions
    at_creation, at_completion, at_failure and at_cancel. See the function
    MoveOut for an example.
"""

from copy import deepcopy
from time import time
from evennia import DefaultCharacter
from evennia.contrib.actions.utils import (triage, process_queue, validate,
    format_action_desc)


"""
* Action dict keys:

key (string) - the name of the action

desc (string) - a description of the action, used in messages to the owner
                and room. Include the $t token as a placeholder for the target
                and the $d token as a placeholder for the data if it is a
                string.
                The desc should not end with a period.

owner (Character) - the character that is performing the action

room (Room) - the room where the action is taking place

bodyparts (list/string) - a list of strings that represent the bodyparts
                          employed in performing the action, or a single
                          string if only one bodypart is employed

target (Object) - the target of the action, if any

has_target (boolean) - whether the action has a target. It would be insufficient
                       to simply check if target == None, because sometimes that
                       happens when the target is removed.
                       has_target is set automatically in Action.__init__()

data (various) - any extra data appended to the action, such as a telepathic
                 message that is meant to be sent, an object that is meant to
                 be given or a dict containing extra information about a craft

cancellable (boolean) - whether the action can be cancelled. Some actions,
                        such as falling, happen without the character's intent
                        and so cannot be cancelled.
                        Defaults to False

invokes_tb (boolean) - whether the action causes the room to switch to 
                       turn-based mode
                       Defaults to False

non_turn (boolean) - whether the action can be performed outside of the owner's
                     turn
                     Defaults to False

passive (boolean) - whether the action can be performed even when the character's
                    actions.active property is set to False. Please note that all
                    passive actions are non-cancellable.
                    Defaults to False

msg_defaults (boolean) - whether to show the default messages for beginning, 
                         completing, failing or canceling the action. Set this
                         to False if you want to put your own messages in
                         at_completion, at_failure and at_cancel, as well as
                         your own custom begin_msg (see below).
                         Defaults to True

begin_msg (string) - The message that will be displayed when the action is  
                     initiated if msg_defaults is set to True. The message
                     can contain the same formatting as the action's desc.
                     If set to the empty string, no message will be shown at
                     all.

onset (float) - the time at which the action began

duration (float) - the time between the action's onset and the action's endtime

endtime (float) - the time at which the action will be completed

reach (string or value) - the reach of the action, reflecting the maximum
                          physical distance that the action can cross. Actions
                          that provide a target should also supply a reach.

at_creation (function) - to be called when the action is created. Takes the
                         action itself as its argument.

at_attempt (function) - to be called at the action's endtime, when the
                        action is attempted, just before its completion.
                        Returns a boolean that is checked against to
                        determine whether the action succeeds or fails.
                        Takes the action itself as its argument.    

at_completion (function) - to be called when the action has been attempted and
                           has succeeded. Takes the action itself as its
                           argument.

at_failure (function) - to be called when the action has been attempted and
                        has failed. Takes the action itself as its argument.

at_cancel (function) - to be called when the action has been cancelled. Takes
                       the action itself as its argument.
"""


base_action = {'key': "",
               'desc': "",
               'owner': None,
               'room': None,
               'bodyparts': '',
               'target': None,
               'has_target': False,
               'data': None,
               'cancellable': True,
               'invokes_tb': False,
               'non_turn': False,
               'passive': False,
               'onset': None,
               'duration': None,
               'endtime': None,
               'reach': None,
               'at_creation': None,
               'at_attempt': None,
               'at_completion': None,
               'at_failure': None,
               'at_cancel': None,
}


class Action(object):
    def __init__(self, key="", desc="", owner=None, room=None, 
                 bodyparts=None, target=None, data=None,
                 cancellable=True, invokes_tb=False, non_turn=False,
                 passive=False, msg_defaults=True, begin_msg="",
                 duration=None, reach=None):

        action = deepcopy(base_action)

        action['key'] = key
        action['desc'] = desc

        action['owner'] = owner
        action['room'] = room
        action['bodyparts'] = bodyparts
        action['target'] = target
        action['has_target'] = True if target else False
        action['data'] = data

        action['cancellable'] = cancellable if not passive else False
        action['invokes_tb'] = invokes_tb
        action['non_turn'] = non_turn
        action['passive'] = passive
        action['msg_defaults'] = msg_defaults

        action['begin_msg'] = begin_msg

        action['duration'] = duration
        action['reach'] = reach

        action['at_creation'] = self.at_creation
        action['at_attempt'] = self.at_attempt
        action['at_completion'] = self.at_completion
        action['at_failure'] = self.at_failure
        action['at_cancel'] = self.at_cancel

        # only proceed with creating the action once it has been validated
        if validate(action) == "Valid":
            self.at_creation(action)

    def at_creation(self, action):
        """
        Runs when the action is created, just after __init__().
        """

        # prevent the action from being carried out if its owner is not active
        if not action['owner'].actions.active and action['cancellable']:
            s = self.format(action)
            action['owner'].msg("{0} is inactive and will not be {1}.".format(
                action['owner'].key, s))
            return 

        # If the action will be queued, add it to the owner's action list. 
        # Otherwise, add it to the room's action list.        
        handler = triage(action)

        if handler:
            handler.add(action)

    def at_attempt(self, action):
        """
        Runs when the action's duration has passed and it is about to be
        completed. If the method returns "True", the action succeeds and
        at_completion is run. If the method returns "False", the action
        fails and at_failure is run.
        """
        return True

    def at_completion(self, action):
        """
        Runs when the action has succeeded.
        """
        if action['msg_defaults']:
            # message everyone according to what they can see
            s = "has finished {0}.".format(action['desc'])
            action['room'].actions.display(action['owner'], s,
                target=action['target'], data=action['data'])

        # remove the action and replace it with an enqueued action if necessary
        self.cleanup(action)

    def at_failure(self, action):
        """        
        Runs when the action has failed.
        """
        if action['msg_defaults']:
            # message everyone according to what they can see
            s = "has failed at {0}.".format(action['desc'])
            action['room'].actions.display(action['owner'], s,
                target=action['target'], data=action['data'])

        # remove the action and replace it with an enqueued action if necessary
        self.cleanup(action)

    def at_cancel(self, action):
        """
        Runs when the action has been cancelled, whether deliberately by the
        action's owner or due to circumstances such as incapacitation.
        """
        if action['cancellable']:
            if action['msg_defaults']:
                # message everyone according to what they see.
                s = " has cancelled {0}.".format(action['desc'])
                action['room'].actions.display(action['owner'], s,
                    target=action['target'], data=action['data'])

            # if the action is being cancelled in turn-based mode,
            # check if the action has been added this very turn
            if action['room'].actions.mode == 'TB':
                if action in action['room'].actions.acted:
                    # remove the action from the actions_acted list
                    action['room'].actions.acted.remove(action)

                else:
                    # add a Turn action to the character, so that the character
                    # may act immediately after the current turn is done
                    Turn(action['owner'], action['room'], place_at_end=False)
            
            self.cleanup(action)

            # In real-time mode, as well as in turn-based mode if it is the
            # character's turn, start any suitable enqueued actions, provided
            # that the character is active
            mode = action['room'].actions.mode
            if mode == 'RT' or (mode == 'TB' and 
                action['room'].actions.turnof == action['owner']):
                process_queue(action['owner'])

            return True
        else:
            return False

    def cleanup(self, action):
        """
        Called after the action is either completed or cancelled,
        hence it should be in the room's actions list
        """

        # remove the action from the room's action list
        action['room'].actions.list.remove(action)

    def format(self, action):
        """
        Returns a formatted version of the action's description
        that replaces the $t token (if any) with a suitable description
        of the target.
        """
        return format_action_desc(action['room'], action['owner'],
            action['desc'], action['target'], data=action['data'])


class Turn(Action):
    """
    Dummy action that simply generates turn order in the event that a new
    turn-based situation arises or a character skips their turn.
    """
    def __init__(self, owner, room, place_at_end=False, hide=False):
        if place_at_end and room.actions.list:
            # Place the turn action at the end of the actions list
            # the duration of the turn action will equal the endtime of the 
            # final action in the actions list, minus the present time
            duration = room.actions.list[-1]['endtime'] - room.actions.time
        else:
            # Place the turn action at the start of the actions list
            duration = 0


        super(Turn, self).__init__(
            key="turn",
            desc="waiting for their turn", 
            owner=owner,
            room=room,
            bodyparts=None,
            target=None,
            reach=None,
            data=None,
            cancellable=False,
            invokes_tb=False,
            non_turn=True, # should be non-turn because it is sometimes given
                           # out to all characters in the room that have no
                           # actions
            msg_defaults=not hide,
            begin_msg="",
            duration=duration,
            )

        def at_creation(self, action):
            # Remove the character's later Turn actions to ensure that only
            # one Turn action exists for each character at a given time 
            action['room'].actions.list = (
                [x for x in action['room'].actions.list
                if not (x['key'] == 'turn' and x['endtime'] > action['endtime']
                and x['owner'] == action['owner'])])

            super(Turn, self).at_creation(action)

    def at_completion(self, action):
        """
        Ensures that the turn completion message shows even if begin_msg is set
        to False.
        """
        action['msg_defaults']=True
        super(Turn, self).at_completion(action) 


class MoveIn(Action):
    def __init__(self, owner, room, prev_room):
        if (owner.actions.bodypart_movement_map and 
            owner.actions.movetype):
            bodyparts = owner.actions.bodypart_movement_map(
                owner.actions.movetype)
        else:
            bodyparts = ""

     	# determine the required duration for the movement
        # This assumes there is exactly one exit from the current room
        # to the previous one.

        exit = [x for x in room.exits if x.db_destination == prev_room]
        if exit:
            # There is at least one exit
            exit = max(exit, key=lambda x: x.db.distance)
            distance = exit.db.distance
        else:
            # No exits back to the previous room were found, default to using
            # the distance of the exit from the previous room to the current one
            exit = [x for x in prev_room.exits if x.db_destination == room]
            if exit:
                exit = max(exit, key=lambda x: x.db.distance)
                distance = exit.db.distance
            else:
                # Exceptional situation where the entrance from the previous
                # room to this one has disappeared just as, or perhaps because,
                # the character has passed through it
                distance = 1.0

        if owner.actions.movespeed:
            duration = distance / owner.actions.movespeed(owner)
        else:
            duration = distance

        super(MoveIn, self).__init__(
            key="movein",
            desc="moving into the area",
            owner=owner,
            room=room,
            bodyparts=bodyparts,
            target=None,
            reach=None,
            data=None,
            cancellable=False,
            invokes_tb=False,
            non_turn=True, # must be non_turn because it is not the character's
                           # turn when they arrive in a room that is in TB mode
            duration=duration,
            )

    def at_completion(self, action):
        """
        Continues to move the character towards their next destination if the
        destination's key matches the key of any exit in the room
        """
        super(MoveIn, self).at_completion(action)
        actions = action['owner'].actions.list
        moves = [x for x in actions if x['key'] == 'moveout']
        exits = action['owner'].location.exits
        while moves:
            for dest in exits:
                if str(dest.key) == str(moves[0]['target'].key):
                    moves[0]['room'] = action['owner'].location
                    moves[0]['target'] = dest
                    action['owner'].actions.pop(moves[0])
                    return
            action['owner'].actions.list.remove(moves[0])
            action['owner'].msg("Unable to continue heading " + 
                moves[0]['target'].key + "; movement action stopped.")
            moves.remove(moves[0])


class MoveOut(Action):
    """
    Moves the character out of the room through the target exit.
    """

    def __init__(self, owner, room, target):
        """
        Evaluate the bodyparts used by the action and its time to completion,
        then package it.

        The target is the exit object that the character is attempting to
        traverse.
        """

        # Determine which bodyparts fit the character's current movement type
        # and apply them to the action.
        if (owner.actions.bodypart_movement_map and 
            owner.actions.movetype):
            bodyparts = owner.actions.bodypart_movement_map(
                owner.actions.movetype)
        else:
            bodyparts = ""

    	# determine the required duration for the movement
        if owner.actions.movespeed:
            duration = target.db.distance / owner.actions.movespeed(owner)
        else:
            duration = target.db.distance

        super(MoveOut, self).__init__(
            key="moveout",
            desc="moving $t",
            owner=owner,
            room=room,
            bodyparts=bodyparts,
            target=target,
            reach='contact',
            data=None,
            cancellable=False,
            invokes_tb=False,
            non_turn=False,
            duration=duration,
            )

    def at_attempt(self, action):
        """
        Checks whether the acting character can traverse the target exit
        """
	if action['target'].access(action['owner'], 'traverse'):
		    # the movement is successful.
            return True
        else:
            return False

    def at_completion(self, action):
        """
        Moves the character to the next room, transfers the character's actions
        there and cleans up the previous room to account for the character's
        departure
        """
        prev_room = action['room']
        next_room = action['target'].db_destination

        # Remove any of the owner's actions in "actions_acted"
        for acted in action['room'].actions.acted:
            acted = dict(acted)
            if acted['owner'] == action['owner']:
                action['room'].actions.acted.remove(action)

        # set the room's turnof value to None if it is set to the owner
        if action['room'].actions.turnof == action['owner']:
            action['room'].actions.turnof = None

        # transfer the character's actions from the previous room to the
        # current one, ensuring that their durations are adjusted accordingly
        for temp_action in prev_room.actions.list:
            if (temp_action['owner'] == action['owner'] and 
                temp_action != action):
                
                temp_action = dict(temp_action)
                if prev_room.actions.mode == "RT":
                    k_time = time()
                else:
                    k_time = prev_room.actions.time 
 
                if (temp_action['target'] and 
                    temp_action['target'] != action['owner']):
                    # cancel all actions that have a target other than the
                    # owner. This is cruder than checking whether their
                    # target is gone from the room in at_attempt(), as the 
                    # owner could be trying to go ahead of the target and
                    # affect them once the target reaches the next room,
                    # but these situations are unlikely and it is better
                    # for the action to be found invalid whenever its
                    # target is missing, in order to catch errors.
                    temp_action['at_cancel'](temp_action)
                else:
                    # move all actions that do not have a target other than
                    # the owner (or no target) into the next room 
                    prev_room.actions.remove(temp_action)
                    temp_action['duration'] -= k_time - temp_action['onset']
                    temp_action['room'] = next_room
                    next_room.actions.add(temp_action)

            elif temp_action['target'] == action['owner']:
                # cancel all ongoing actions by other characters that target
                # the moving character
                temp_action['at_cancel'](temp_action)

       # as always, include the super when overloading the base function
        super(MoveOut, self).at_completion(action)

        # Move the character between rooms
        action['owner'].move_to(action['target'])

        MoveIn(action['owner'], next_room, prev_room)

        # if the character has activated their turn-based status, attempt to 
        # enter TB mode in the next room and leave TB mode in the previous room
        if action['owner'].actions.turnbased:
            prev_room.actions.try_rt()
            next_room.actions.try_tb()

    def at_failure(self, action):
        """
        Sends a message to the failing character and possibly the room, 
        depending on the exit's settings
        """
        if action['target'].db.err_traverse:
            # if exit has a better error message, let's use it.
            action['owner'].msg(action['target'].db.err_traverse)
        else:
            # No shorthand error message. Call hook.
            action['target'].at_failed_traverse(action['object'])

