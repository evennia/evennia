"""
This defines some generally useful scripts for the tutorial world. 
"""

import random
from ev import Script

#------------------------------------------------------------
#
# IrregularEvent - script firing at random intervals
#
# This is a generally useful script for updating 
# objects at irregular intervals. This is used by as diverse
# entities as Weather rooms and mobs. 
#
# 
#
#------------------------------------------------------------

class IrregularEvent(Script):
    """
    This script, which should be tied to a particular object upon
    instantiation, calls update_irregular on the object at random
    intervals.
    """        
    def at_script_creation(self):
        "This setups the script"

        self.key = "update_irregular"
        self.desc = "Updates at irregular intervals"
        self.interval = random.randint(30, 70) # interval to call.
        self.start_delay = True # wait at least self.interval seconds before calling at_repeat the first time
        self.persistent = True 

        # this attribute determines how likely it is the
        # 'update_irregular' method gets called on self.obj (value is
        # 0.0-1.0 with 1.0 meaning it being called every time.)
        self.db.random_chance = 0.2

    def at_repeat(self):
        "This gets called every self.interval seconds."
        rand = random.random()
        if rand <= self.db.random_chance:
            try:
                #self.obj.msg_contents("irregular event for %s(#%i)" % (self.obj, self.obj.id))
                self.obj.update_irregular()
            except Exception:
                pass

class FastIrregularEvent(IrregularEvent):
    "A faster updating irregular event"
    def at_script_creation(self):
        super(FastIrregularEvent, self).at_script_creation()
        self.interval = 5 # every 5 seconds, 1/5 chance of firing


#------------------------------------------------------------
#
# Tutorial world Runner - root reset timer for TutorialWorld
#
# This is a runner that resets the world
#
#------------------------------------------------------------

# #
# # This sets up a reset system -- it resets the entire tutorial_world domain
# # and all objects inheriting from it back to an initial state, MORPG style. This is useful in order for
# # different players to explore it without finding things missing.
# #
# # Note that this will of course allow a single player to end up with multiple versions of objects if
# # they just wait around between resets; In a real game environment this would have to be resolved e.g.
# # with custom versions of the 'get' command not accepting doublets. 
# #

# # setting up an event for reseting the world.

# UPDATE_INTERVAL = 60 * 10 # Measured in seconds


# #This is a list of script parent objects that subscribe to the reset functionality.
# RESET_SUBSCRIBERS = ["examples.tutorial_world.p_weapon_rack",
#                      "examples.tutorial_world.p_mob"]

# class EventResetTutorialWorld(Script):
#     """
#     This calls the reset function on all subscribed objects
#     """
#     def __init__(self):
#         super(EventResetTutorialWorld, self).__init__()
#         self.name = 'reset_tutorial_world'
#         #this you see when running @ps in game:
#         self.description = 'Reset the tutorial world .'
#         self.interval = UPDATE_INTERVAL
#         self.persistent = True 

#     def event_function(self):
#         """
#         This is called every self.interval seconds.
#         """
#         #find all objects inheriting the subscribing parents
#         for parent in RESET_SUBSCRIBERS:            
#             objects = Object.objects.global_object_script_parent_search(parent)
#             for obj in objects:
#                 try: 
#                     obj.scriptlink.reset()
#                 except:
#                     logger.log_errmsg(traceback.print_exc())
        


