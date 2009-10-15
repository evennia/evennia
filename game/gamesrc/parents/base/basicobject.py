"""
This is the base object type/interface that all parents are derived from by
default. Each object type sub-classes this class and over-rides methods as
needed. 

NOTE: This file should NOT be directly modified. Sub-class this in
your own class in game/gamesrc/parents and change
SCRIPT_DEFAULT_OBJECT variable in settings.py to point to the new class. 
"""
from src.script_parents.basicobject import EvenniaBasicObject

class BasicObject(EvenniaBasicObject):
    pass

def class_factory(source_obj):
    """
    This method is called any script you retrieve (via the scripthandler). It
    creates an instance of the class and returns it transparently. 
    
    source_obj: (Object) A reference to the object being scripted (the child).

    Since this is the only place where the object is actually instantiated,
    this is also the place to put commands you want to act on this object,
    do this by obj.command_table.add_command('cmd', cmd_def).
    """
    obj = BasicObject(source_obj)     
    return obj
