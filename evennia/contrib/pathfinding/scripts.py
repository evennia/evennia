"""
PathfinderScript

Contrib - Johnny 2018

A batteries-included abstraction for in-MUD navigation.

Upon initialization, the Pathfinder will quietly build a "map" (directional 
graph) of all of your game's Rooms and Exits, even accounting for one-way 
travel.

Requires the `networkx` library, not included with Evennia, but only a
`pip install networkx` away.

---

Installation:

Get or create an instance of this script at server start/reload.

To do so, modify `yourgame/server/conf/at_server_startstop.py`:

Add this import to the top of the file:

    from evennia.contrib.pathfinding.scripts import PathfinderScript
    
Add this line to the beginning or end of your `at_server_start()` function, but
replace the word 'pass' if it's there:

    # This will preload graph creation before the game is live
    pathfinder = PathfinderScript.spawn()
    
That's it! It is now running and will update itself every 30 minutes.

To use it:

    from evennia.contrib.pathfinding.scripts import PathfinderScript
    pfind = PathfinderScript.spawn()
    
    pfind.map.get_directions(room_obj1, room_obj2)
    >> ['down', 'east', 'down', 'north', 'down']
    
"""

from evennia import DefaultScript
from evennia.contrib.pathfinding.pathfinder import Pathfinder
from evennia.utils import create, logger

class PathfinderScript(DefaultScript):
    """Generates and maintains a global Pathfinder instance."""
    
    @property
    def map(self):
        """
        Returns a reference to the stored Pathfinder.
        """
        return self.pathfinder
        
    @classmethod
    def spawn(cls, **kwargs):
        """
        Gets the first existing script instance, or creates new
        
        Kwargs:
            any (any): Forwarded to create.create_script
            
        Returns:
            obj (PathfinderScript): PathfinderScript
        """
        if kwargs:
            obj = cls.objects.get(**kwargs)
        else:
            obj = cls.objects.first()
            
        kwargs['obj'] = None
        if not obj: obj = create.create_script(cls, **kwargs)
        return obj
    
    def at_script_creation(self):
        self.key = "pathfinder"
        self.desc = "Maintains a global Pathfinder instance."
        self.interval = 60 * 30 # every 30 minutes
        self.persistent = True
        
        self.pathfinder = Pathfinder()
        logger.log_info('PathfinderScript initialized.')

    def at_repeat(self):
        "Periodically updates the graph to add or remove rooms and exits."        
        try: result = self.pathfinder.update()
        except Exception as e:
            logger.log_err('PathfinderScript failed to update.')
            logger.log_err(e)
        
        if result:
            logger.log_info('PathfinderScript successfully updated.')