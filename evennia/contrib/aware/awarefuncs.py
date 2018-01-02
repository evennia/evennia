"""
Module containing the awarefuncs (the default actions).
"""

from evennia.utils.logger import log_err

def cmd(obj, signal, storage, cmd):
    """
    Execute a simple command.
    """
    obj.execute_cmd(cmd)
    return True

def move(obj, signal, storage, exit):
    """Ask the object to move in the specified direction."""
    if isinstance(exit, basestring):
        exits = obj.search(exit, quiet=True)
        exits = [ex for ex in exits if ex.destination]
        if len(exits) == 1:
            exit = exits[0]
        else:
            raise ValueError("ambiguous exit name: {}".format(exit))

    obj.move_to(exit)
    return True

def follow(obj, signal, storage, path=None, pace=1):
    """Force the object to move several rooms to follow the signal."""
    if obj.location is signal.location:
        return True
    
    if path is None:
        path = getattr(signal, "toward", None)

    if path is None:
        log_err("Action 'follow': obj={}, the specified path wasn't valid and/or the signal had no path toward it".format(obj))
        return True
    
    if obj.location not in path or path[obj.location] is None:
        log_err("Action 'follow': obj={}, the specified path doesn't know what to do with location={}".format(obj, obj.location))
        return True
    
    # Have the object move a room
    exit = path[obj.location]
    obj.move_to(exit)
    return pace

