"""
This is the basic Evennia-standard player parent. 

NOTE: This file should NOT be directly modified. Sub-class the BasicPlayer
class in game/gamesrc/parents/base/basicplayer.py and change the 
SCRIPT_DEFAULT_PLAYER variable in settings.py to point to the new class. 
"""
from src.script_parents.basicobject import EvenniaBasicObject
from src.script_parents.basicplayer import EvenniaBasicPlayer

class BasicPlayer(EvenniaBasicObject, EvenniaBasicPlayer):
    pass

def class_factory(source_obj):
    """
    This method is called any script you retrieve (via the scripthandler). It
    creates an instance of the class and returns it transparently. 
    
    source_obj: (Object) A reference to the object being scripted (the child).
    """
    return BasicPlayer(source_obj)  