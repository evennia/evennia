"""
Paging command and support functions.
"""
from src.objects.models import Object
from src import defines_global

def get_last_paged_objects(pobject):
    """
    Returns a list of objects of the user's last paged list, or None if invalid
    or non-existant.
    """
    last_paged_dbrefs = pobject.get_attribute_value("LASTPAGED")
    if last_paged_dbrefs is not False:
        last_paged_objects = list()
        try:
            last_paged_dbref_list = [
                    x.strip() for x in last_paged_dbrefs.split(',')
            ]
            for dbref in last_paged_dbref_list:
                if not Object.objects.is_dbref(dbref):
                    raise ValueError
                last_paged_object = Object.objects.dbref_search(dbref)
                if last_paged_object is not None:
                    last_paged_objects.append(last_paged_object)
            return last_paged_objects
        except ValueError:
            # Remove the invalid LASTPAGED attribute
            pobject.clear_attribute("LASTPAGED")
            return None   

def cmd_page(command):
    """
    Send a message to target user (if online).
    """
    session = command.session
    pobject = session.get_pobject()
    # Get the last paged person(s)
    last_paged_objects = get_last_paged_objects(pobject)
    
    # If they don't give a target, or any data to send to the target
    # then tell them who they last paged if they paged someone, if not
    # tell them they haven't paged anyone.
    if not command.command_argument:
        if last_paged_objects:
            session.msg("You last paged: %s." % (
                ', '.join([x.name for x in last_paged_objects])))
            return
        else:
            # No valid LASTPAGE values
            session.msg("You have not paged anyone.")
            return
    
    # Stores a list of targets
    targets = []

    # Build a list of targets
    # If there are no targets, then set the targets to the last person they
    # paged.
    cmd_targets = command.get_arg_targets()
    if cmd_targets is None:
        targets = last_paged_objects
        
        # No valid last paged players found, error out.
        if not targets:
            session.msg("Page who?")
            return
    else:
        # For each of the targets listed, grab their objects and append
        # it to the targets list if valid.
        for target in cmd_targets:
            matched_object = Object.objects.local_and_global_search(pobject,
                    target,
                    limit_types=[defines_global.OTYPE_PLAYER])
            
            if matched_object:
                # Found a good object, store it
                targets.append(matched_object[0])
            else:
                # Search returned None
                session.msg("Player '%s' can not be found." % (
                        target))

    # Depending on the argument provided, either send the entire thing as
    # a message or break off the point after the equal sign.
    if command.arg_has_target():
        # User specified targets, get the stuff after the equal sign.
        message = command.get_arg_target_value()
    else:
        # No targets specified with equal sign, use lastpaged and the user's
        # arguments as the message to send.
        message = command.command_argument
        
    sender_name = pobject.get_name(show_dbref=False)
    # Build our messages
    target_message = "%s pages: %s"
    sender_message = "You paged %s with '%s'."
    # Handle paged emotes
    if message.startswith(':'):
        message = message[1:]
        target_message = "From afar, %s %s"
        sender_message = "Long distance to %s: %s %s"
        # Handle paged emotes without spaces
    elif message.startswith(';'):
        message = message[1:]
        target_message = "From afar, %s%s"
        sender_message = "Long distance to %s: %s%s"

    # We build a list of target_names for the sender_message later
    target_names = []
    for target in targets:
        # Check to make sure they're connected, or a player
        if target.is_connected_plr():
            target.emit_to(target_message % (sender_name, message))
            target_names.append(target.get_name(show_dbref=False))
        else:
            session.msg("Player %s does not exist or is not online." % (
                    target.get_name(show_dbref=False)))

    # Now send a confirmation to the person doing the paging.
    if len(target_names) > 0:
        target_names_string = ', '.join(target_names)
        try:
            session.msg(sender_message % (target_names_string, sender_name, message))
        except TypeError:
            session.msg(sender_message % (target_names_string, message))
        
        # Now set the LASTPAGED attribute
        pobject.set_attribute("LASTPAGED", ','.join(
                ["#%d" % (x.id) for x in targets]))