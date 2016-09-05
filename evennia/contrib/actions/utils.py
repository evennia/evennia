from evennia import DefaultRoom, DefaultCharacter, DefaultObject, ObjectDB
from evennia import search_channel




def same(action, other):
    if (action['key'] == other['key'] and 
        action['owner'] == other['owner'] and
        action['target'] == other['target'] and 
        set(action['bodyparts']) == set(other['bodyparts']) and
        action['data'] == other['data']):
        return True
    return False


def validate(action):
    """
    Sends debug messages if the action lacks essential components of the
    required type. If so, it returns a string listing the error names.
    Otherwise returns "Valid".
    """
    errors = ""

    # check that the room exists and is an actual room
    if not isinstance(action['room'], DefaultRoom):

        #[DEBUG]
        if action['owner'].tags.get("debug"):
            action['owner'].msg("|mINVALID ACTION (" + action['key'] +
                "): The action's room does not exist|n")

        errors += "NoRoom "

    # check that the owner exists and is inside the room
    # Note that this assumes actions cannot take place across rooms
    if not isinstance(action['owner'], DefaultCharacter):
        
        #[DEBUG]
        superuser = ObjectDB.objects.object_search("#1")
        if superuser:
            superuser = superuser[0]        

        if superuser.tags.get("debug"):
            superuser.msg("|mINVALID ACTION (" + action['key'] +
                "): Owner does not exist|n")

        errors += "NoOwner "

    if action['owner'].location != action['room']:

        #[DEBUG]
        if action['owner'].tags.get("debug"):
            action['owner'].msg("|mINVALID ACTION (" + action['key'] +
                "): Owner is not in action's room|n")

        errors += "OwnerNotInRoom "

    # If the action has a target, check that the target is a real object 
    # that exists in the room
    
    if action['has_target']:
        if not action['reach']:
            
            #[DEBUG]
            if action['owner'].tags.get("debug"):
                action['owner'].msg("|mINVALID ACTION (" + action['key'] + 
                    "): The action has a target but no reach|n")

            errors += "NoReach "

        if not isinstance(action['target'], DefaultObject):

            #[DEBUG]
            if action['owner'].tags.get("debug"):
                action['owner'].msg("|mINVALID ACTION (" + action['key'] + 
                    "): Target is not a valid object|n")

            errors += "NoTarget "

        if (action['target'].location != action['room'] and
            action['reach'] ):
            
            # [DEBUG]
            if action['owner'].tags.get("debug"):
                action['owner'].msg("|mINVALID ACTION (" + action['key'] + 
                    "): Target is not inside the action's room|n")

            errors += "TargetNotInRoom "

    if errors:
        return errors
    else:
        return "Valid"   


def handle_invalid(action, validate_result):
    if action['room']:
        room = action['room'].key + "({0})".format(action['room'].dbref)
    else:
        room = "None"

    search_channel("MudInfo")[0].msg("Action " + action['key'] + " in room " +
        room + " has been found invalid with error " + validate_result)

    if action['room'] and action in action['room'].actions.list:
        action['room'].actions.remove(action)

    if action['owner'] and action in action['owner'].actions.list:
        action['owner'].actions.remove(action)


def share_bps(action, other):
    # Note: "action" and "other" must be action dictionaries, not Action objects
    # The function assumes that no bodypart is repeated in either list.
    l = []
    if (action['owner'] == other['owner'] 
        and action['bodyparts'] and other['bodyparts']):
        action_bodyparts = list_bodyparts(action['bodyparts'])
        other_bodyparts = list_bodyparts(other['bodyparts'])

        for x in action_bodyparts:
            for y in other_bodyparts:
                if x == y:
                    l.append(x)
    return l


def string_action_descs(action_list):
    """
    Transforms a list of actions into a string of their descriptions, 
    partitioned by commas and the word "and".
    """
    if not action_list:
        print("ERROR in world.actions.utils.py, string_action_descs")
        return "" # This should never happen

    action = action_list[0]
    s = action_list[0]['desc']

    s = format_action_desc(action['room'], action['owner'], action['desc'],
        action['target'], data=action['data'])

    ln = len(action_list)
    if ln == 1:
        return s

    for i in range(1, ln - 1):
        action = action_list[i]
        s += ", " + format_action_desc(action['room'], action['owner'],
            action['desc'], action['target'], data=action['data'])
    action = action_list[ln - 1]
    s += " and " + format_action_desc(action['room'], action['owner'],
        action['desc'], action['target'], data=action['data'])

    return s

def string_descs(l):
    """
    Transforms a list of strings into a string containing them,
    partitioned by commas and the word "and".
    """

    if not l:
        return "" # This should never happen

    s = l[0]
    ln = len(l)
    if ln == 1:
        return s

    for i in range(1, ln - 1):
        s += ", " + l[i]
    s += " and " + l[ln - 1]
    return s


def is_same_bps_enqueued(action):
    """
    Check to see if an action using the same bodyparts 
    is enqueued by the same character

    This will be called when creating an action, as well as after 
    processing or cancelling an action in order to see whether a new action
    should be pulled from the queue to replace the processed / cancelled one
    """
    return [x for x in action['owner'].actions.list if share_bps(action, x)]


def is_same_bps_underway(action):
    """
    Check to see if an action using the same bodyparts 
    is already being performed by the same character
    """
    return [x for x in action['room'].actions.list if share_bps(action, x)]


def triage(action):
    """
    Check for and handle the situation wherein other actions that are underway
    or enqueued by the same character share bodyparts with a given action.

    [WIP]
    """
    underway = is_same_bps_underway(action)
    new = action['owner'].actions.new

    # Ensure that new actions and actions assigned via override can only be added
    # during the character's turn

    if underway:
        if new == "override":

            if (action['room'].actions.mode == 'TB' and not action['non_turn'] 
            and not action['owner'] == action['room'].actions.turnof):
                # inform the owner that they are out of turn, abort adding
                # the action. [WIP] Can queued actions be popped out-of-turn? 
                action['owner'].msg("It is not your turn. " +
                    "In turn-based mode, you can only begin most actions " +
                    "during your own turn.")
                return None

            for x in underway:
                x['at_cancel'](x)

            #[WIP][DEL] Perhaps remove this feature.
            enqueued = is_same_bps_enqueued(action)
            if enqueued:
                action['owner'].msg("Cancelling all enqueued actions " +
                    "that would use the same bodyparts as {0}.".format(
                    action['desc']))
                for x in enqueued:
                    action['owner'].actions.list.remove(x)

            # The action has begun, message everyone who can view it.
            print("msg_defaults: ", action['msg_defaults'])
            if action['msg_defaults']:
                s = " has begun {0}.".format(action['desc'])
            else:
                s = action['begin_msg']

            action['room'].actions.display(action['owner'], s,
                target=action['target'], data=action['data']) 
 
                # process the action in the room's action list
            return action['room'].actions

        elif new == "queue":
            # inform the owner that the action is being queued
            enqueued = underway + is_same_bps_enqueued(action)
            s = string_action_descs(enqueued)
            s2 = format_action_desc(action['room'], action['owner'], 
                action['desc'], action['target'], data=action['data'])
            action['owner'].msg("Once you are done {0},".format(s) +
                " you will be {0}.".format(s2))

                # process the action in the character's action list
            return action['owner'].actions

        elif new == "ignore":
            bodyparts = []
            for x in underway:
                bodyparts.extend(share_bps(action, x))

            bodyparts = list(set(bodyparts)) # remove duplicates
            bodyparts = string_descs(bodyparts)
            s = underway[0]['desc']

            action['owner'].msg(
                "You are already using your {0} for {1}.".format(bodyparts, s))
            return None
    else:
        # This action is completely new.

        if (action['room'].actions.mode == 'TB' and not action['non_turn'] and
        not action['owner'] == action['room'].actions.turnof):
            # inform the owner that they are out of turn, abort adding
            # the action. [WIP] Can queued actions be popped out-of-turn? 
            action['owner'].msg("It is not your turn. " +
                "In turn-based mode, you can only begin most actions " +
                "during your own turn.")
            return None

        # The action has begun, message everyone.
        if action['msg_defaults']:
            s = " has begun {0}.".format(action['desc'])
        else:
            s = action['begin_msg']

        action['room'].actions.display(action['owner'], s, 
            target=action['target'], data=action['data'])
 
        # process the action in the room's actions list
        return action['room'].actions


def process_queue(char):
    """
    Go through a character's actions list and find all actions that do not
    share bodyparts with ongoing actions. Transfer all such actions from the 
    character's actions list to the room's actions list.
    """
    if not char.actions.active:
        return

    for enqueued in char.actions.list:
        if not is_same_bps_underway(enqueued):
            char.actions.pop(enqueued)

            # Inform the room that the owner is performing the new action
            enqueued['owner'].msg("You undertake a queued action:")
            s = " is now {0}.".format(enqueued['desc'])
            enqueued['room'].actions.display(enqueued['owner'], s, 
                target=enqueued['target'], data=enqueued['data']) 


def list_bodyparts(bodyparts_str):
    """
    Converts a string of bodyparts to a list of bodyparts.
    Used in unpacking the bodyparts from an action's dictionary.
    """
    return bodyparts_str.split(",")


def join_bodyparts(bodyparts_list):
    """
    Converts a list of bodyparts to a string of bodyparts.
    Used in packing the bodyparts into an action's dictionary.
    Necessary because .db attributes that are lists of dictionaries of lists
    (such as the actions list) would raise errors when being indexed or removed.
    Thus, the actions list must be a list of dictionaries of strings and other
    non-list variables instead.
    """
    return ",".join(bodyparts_list)


def format_action_desc(room, viewer, s, target, data=""):
    """
    Formats an action's desc string, if it contains a $t token,
    so that it transforms the token into the target's name
    if the target can be viewed by the viewer, or into the word
    "something" if the target cannot be viewed.
    """
    if room.actions.view:
        name_target = room.actions.view(target, viewer)
        if name_target == False:
            name_target = "something"
    else:
        if target:
            name_target = target.key
        else:
            name_target = ""     

    if s.find("$t") == 0:
        name_target = name_target.capitalize()
    
    s = s.replace("$t", name_target)

    if not isinstance(data, str) and not isinstance(data, unicode):
        data = ""
    s = s.replace("$d", data)

    return s


#debug functions
def bps_legs(movetype):
    return "legs"

def view_bobo(x,y):
    return "bobo"

def view_false(x,y):
    return False

