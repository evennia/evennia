"""
This module contains the ActionSystemScript, which runs when a given room
switches to turn-based or real-time mode as well as each time at least one
action in the room is due to be processed in either of these modes. This is
the script that handles most of the work involving actions that are already
ongoing within the room.
"""

from math import ceil
from time import time
from evennia import DefaultScript, DefaultCharacter
from evennia.utils import logger
from evennia.contrib.actions.actions import Turn
from evennia.contrib.actions.utils import (process_queue, validate, 
    handle_invalid)


class ActionSystemScript(DefaultScript):
    """
    This script has two modes, RT and TB.

    The RT mode processes all actions whose endtime is less than the current
    CPU time, pops any relevant actions enqueued by these processed actions'
    owners, and finally sets the script to run again when the next action
    is due to complete.

    The TB mode of this function gives a turn action to all characters in
    the room that do not currently have an action, tells the player whose
    turn has just ended that their turn has ended, processes the earliest
    action in the room's actions list and gives that action's owner the
    turn, providing them with either 60 seconds to act (if the owner is
    a PC) or 5 seconds (if the owner is an NPC).

    In either the RT or TB mode, if no actions are present in the room's
    actions list, the function pauses the script.
    """
    def at_script_creation(self):
        """
        Describes the ActionSystemScript and makes it persistent. Its interval
        and start_delay values are overruled by later invocations of the script.
        """
        self.key = "ActionSystemScript"
        self.desc = "Processes the real-time action system in the current room."
        self.interval = 1  # seconds
        #self.repeats = 5  # repeat only a certain number of times
        self.start_delay = False  # wait self.interval until first call
        self.persistent = True

    def at_repeat(self):
        """
        Processes actions as described in the class docstring.
        """
        room = self.obj
        handler = room.actions
        try:
            if handler.mode == "RT":
                #[DEBUG]
                for char in handler.owner.contents:
                    if (isinstance(char, DefaultCharacter) and 
                        char.tags.get("actdebug")):
                        char.msg("|mRestarting RT callback in {0}|n".format(
                            handler.owner.key))

                k_time = time()
                handler.time = k_time

                # process all pending actions on the actions list
                while (handler.list and 
                    handler.list[0]['endtime'] < k_time):
                    action = handler.list[0]

                    # process the action
                    validate_result = validate(action)
                    if validate_result == "Valid":
                        if hasattr(action['owner'], "pre_perform_action"):
                            action['owner'].pre_perform_action(action)
                        result = action['at_attempt'](action)
                        if result:
                            action['at_completion'](action)
                        else:
                            action['at_failure'](action)
                        if hasattr(action['owner'], "post_perform_action"):
                            action['owner'].post_perform_action(action, result)
                    else:
                        handle_invalid(action, validate_result)

                    # handle any actions enqueued by the action's owner
                    process_queue(action['owner'])

                # If there are still actions in the list after processing,
                # set the callback to restart when the next action is due to
                # complete. Note that the script will also be called again
                # whenever actions are added to the list.
                if handler.list:
                    interval = handler.list[0]['endtime'] - k_time
                    
                    # Round up the interval so the script will not round it
                    # down automatically.
                    interval = int(ceil(interval))

                    #[DEBUG]
                    for char in handler.owner.contents:
                        if (isinstance(char, DefaultCharacter) and
                            char.tags.get("actdebug")):
                            char.msg("|mActions being processed in RT mode." +
                        "Restarting script in {0} seconds|n".format(interval))

                    handler.schedule_script(interval)
                else:
                    # There are no actions in the actions list. Remove and 
                    # thus deactivate the script. It will be turned on again
                    # when adding actions to the actions list.

                    #[DEBUG]
                    for char in handler.owner.contents:
                        if (isinstance(char, DefaultCharacter) and
                            char.tags.get("actdebug")):
                            char.msg("|mPausing actions script|n")

                    handler.pause_script()

            elif handler.mode == "TB":
                #[DEBUG]
                for char in handler.owner.contents:
                    if (isinstance(char, DefaultCharacter) and 
                        char.tags.get("actdebug")):
                        char.msg("|mRestarting TB callback in {0}|n".format(
                            handler.owner.key))

                # Give a delayed Turn action to each characters that does
                # not have ongoing actions. Note that characters also
                # receive new non-delayed Turn actions when the room
                # switches to turn-based mode
                chars = [x for x in handler.owner.contents if 
                    isinstance(x, DefaultCharacter)]

                for char in chars:
                    if not [x for x in handler.list 
                            if x['owner'] == char]:
                        Turn(char, handler.owner, place_at_end=True)

                # Inform the player whose turn it has been (if any) that their
                # turn has expired
                k_char = handler.turnof
                if k_char:
                    if handler.acted:
                        k_char.msg("Your turn has ended.")
                    else:
                        k_char.msg("Your turn has ended. " + 
                            "You will have another turn once all actions " +
                            "underway in the area have been completed.")

                # reset actions_acted, as no one has acted yet this turn
                handler.acted = []

                # Note: actions_acted must be a list, not a boolean!!!
                # This is because actions may be cancelled during a turn, 
                # and if they are cancelled, the character should still get
                # their Turn action at the end of the turn.

                # If there are still actions in the room's action list:
                if handler.list:

                    # Extract the next pending action from the action list
                    action = handler.list[0]

                    # Increment the actions_time to the action's endtime
                    handler.time = action['endtime']

                    # process the action
                    validate_result = validate(action)
                    while validate_result != "Valid":
                        # clear the invalid actions until finding a valid one
                        handle_invalid(action, validate_result)
                        if handler.list:
                            action = handler.owner.actions.list[0]
                            handler.time = action['endtime']
                            validate_result = validate(action)
                        else:
                            break

                    if validate_result == "Valid":
                        if hasattr(action['owner'], "pre_perform_action"):
                            action['owner'].pre_perform_action(action)
                        result = action['at_attempt'](action)
                        if result:
                            action['at_completion'](action)
                        else:
                            action['at_failure'](action)
                        if hasattr(action['owner'], "post_perform_action"):
                            action['owner'].post_perform_action(action, result)
                    else:
                        handler.try_rt()
                        return

                    # Set the new turn to the owner of the action
                    handler.turnof = action['owner']

                    # The owner of the action may also have actions enqueued
                    # send each such action to the room's actions list
                    # unless it shares bodyparts with a later action in the
                    # list
                    process_queue(action['owner'])

                    # [WIP] If the character that performed the action is an
                    # NPC, run its AI to determine its next action




                    # in case an action (e.g. a movement action) removed or
                    # activated turn-based mode in the course of being processed 
                    # (~not~ in the course of being added), check if the room
                    # should still be in TB mode
                    if handler.check_for_tb():
                        # check whether it's the turn of an NPC or a PC, 
                        # determine the interval to the next invocation of the
                        # script based on that

                        if action['owner'].player:
                            # the action has been performed by a PC. 
                            # it is now that PC's turn.

                            action['owner'].msg("It is now your turn." + 
                                " You have one minute to input further" +
                                " actions or override any actions you have" +
                                " previously made.")
                            interval = 60
                        else:
                            interval = 5

                        handler.schedule_script(interval)
                    else:
                        # stop TB mode
                        handler.try_rt()

                else:
                    # No actions are occurring, not even turn actions,
                    # presumably because no characters or effects are here.
                    # Switch to RT mode and let the action system turn off.
                    handler.try_rt()

            else:
                # Mode is neither RT nor TB, something has gone wrong
                raise ValueError("invalid actions mode ({0}) ".format(
                    handler.mode) + "detected in room {0}".format(handler.owner))

        except:
            logger.log_trace()

