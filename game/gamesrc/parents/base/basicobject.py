"""
This is the base object type/interface that all parents are derived from by
default. Each object type sub-classes this class and over-rides methods as
needed. 

NOTE: This file should NOT be directly modified. Sub-class the BasicObject
class in game/gamesrc/parents/base/basicobject.py and change the 
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
    """
    return BasicObject(source_obj)     