from evennia.contrib.collab.perms import collab_check


def controls(accessing_obj, accessed_obj):
    """
    Checks to see if the accessing object owns or has escalated
    privileges over an object.
    """
    return collab_check(accessing_obj, accessed_obj)
