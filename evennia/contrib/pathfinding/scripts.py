from evennia import DefaultScript
from evennia.contrib.pathfinding.pathfinder import Pathfinder
from evennia.utils import logger

class PathfinderScript(DefaultScript):
    """Generates and maintains a global Pathfinder instance."""
    
    @property
    def graph(self):
        return self.db.pathfinder
    
    def at_script_creation(self):
        self.key = "pathfinder"
        self.desc = "Maintains a global Pathfinder instance."
        self.interval = 60 * 30 # every 30 minutes
        self.persistent = True
        
        self.db.pathfinder = Pathfinder()
        logger.log_info('PathfinderScript initialized.')

    def at_repeat(self):
        "Periodically updates the graph to add or remove rooms and exits."        
        try: result = self.db.pathfinder.update()
        except Exception as e:
            logger.log_err('PathfinderScript failed to update.')
            logger.log_err(e)
        
        if result:
            logger.log_info('PathfinderScript successfully updated.')