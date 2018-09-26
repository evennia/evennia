from evennia import create_script, DefaultScript
from evennia.contrib.pathfinding.pathfinder import Pathfinder
from evennia.contrib.pathfinding.scripts import PathfinderScript
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

class PathfinderTest(EvenniaTest):
    
    def test_script(self):
        "Tests handling of script"
        # Initialize script globally
        obj = create_script('evennia.contrib.pathfinding.scripts.PathfinderScript', key='pathfinder', obj=None)
        self.assertTrue(obj, 'Pathfinder script was not created.')
        
        # Recall the script as an obj
        pf_script = next((x for x in PathfinderScript.objects.all() if x.key == 'pathfinder'), None)
        self.assertTrue(pf_script, 'The Pathfinder script was not retrieved.')
        
        # Ask script for directions
        directions = pf_script.graph.get_directions(self.basement, self.bedmaster)
        self.assertTrue(directions, 'No directions were returned!')
        self.assertTrue(len(directions) > 2, 'Too few directions were returned!')
    
    def test_get_path(self):
        "Get path from Kitchen to Lair"
        path = self.pfinder.get_path(self.kitchen, self.lair)
        self.assertTrue(path, 'No path was computed from kitchen to lair.')
        
        # Get path from bedroom to treasure room
        path = self.pfinder.get_path(self.bed1, self.treasure_room)
        self.assertTrue(path, 'No path was computed from bedroom to treasure room.')
        
    def test_get_directions(self):
        "Get list of fewest movements required to go from Kitchen to Lair"
        path = self.pfinder.get_directions(self.kitchen, self.lair)
        correct = ['down', 'east', 'down', 'north', 'down']
        self.assertEqual(list(path), correct, "Did not return the correct path.")
        
    def test_get_line_of_sight(self):
        "Returns all objects in line of sight from source"
        objs = self.pfinder.get_line_of_sight(self.kitchen, 'down')
        self.assertTrue(objs)
        self.assertEqual(2, len(objs))
        
    def test_json_export(self):
        "Should return a JSON serialized graph."
        self.assertTrue(self.pfinder.export_json())
        
    def setUp(self):
        super(PathfinderTest, self).setUp()
        
        # Create some rooms to make this more interesting
        self.frontyard = create.create_object(self.room_typeclass, key="Front Yard", nohome=True)
        self.foyer = create.create_object(self.room_typeclass, key="Foyer", nohome=True)
        self.parlor = create.create_object(self.room_typeclass, key="Parlor", nohome=True)
        self.diningroom = create.create_object(self.room_typeclass, key="Dining Room", nohome=True)
        self.kitchen = create.create_object(self.room_typeclass, key="Kitchen", nohome=True)
        
        self.uphall = create.create_object(self.room_typeclass, key="Upstairs Hallway", nohome=True)
        self.bed1 = create.create_object(self.room_typeclass, key="Bedroom", nohome=True)
        self.bed2 = create.create_object(self.room_typeclass, key="Bedroom", nohome=True)
        self.bed3 = create.create_object(self.room_typeclass, key="Bedroom", nohome=True)
        self.bedmaster = create.create_object(self.room_typeclass, key="Your Parents' Bedroom", nohome=True)
        self.dungeon = create.create_object(self.room_typeclass, key="Creepy Dungeon", nohome=True)
        self.cells = create.create_object(self.room_typeclass, key="Cell Block", nohome=True)
        
        self.basement = create.create_object(self.room_typeclass, key="Basement", nohome=True)
        self.crawlspace = create.create_object(self.room_typeclass, key="Basement Crawlspace", nohome=True)
        self.depths = create.create_object(self.room_typeclass, key="Basement Depths", nohome=True)
        
        self.cavern = create.create_object(self.room_typeclass, key="Strange Cavern", nohome=True)
        self.treasure_room = create.create_object(self.room_typeclass, key="Treasure Room", nohome=True)
        
        self.lair = create.create_object(self.room_typeclass, key="Cthulhu's Lair", nohome=True)
        
        # Create some exits between them all
        # Yard to foyer bidirectional
        create.create_object(self.exit_typeclass, key='in', location=self.frontyard, destination=self.foyer)
        create.create_object(self.exit_typeclass, key='out', location=self.foyer, destination=self.frontyard)
        # Foyer to parlor bidirectional
        create.create_object(self.exit_typeclass, key='east', location=self.foyer, destination=self.parlor)
        create.create_object(self.exit_typeclass, key='west', location=self.parlor, destination=self.foyer)
        # Foyer to upstairs bidirectional
        create.create_object(self.exit_typeclass, key='up', location=self.foyer, destination=self.uphall)
        create.create_object(self.exit_typeclass, key='down', location=self.uphall, destination=self.foyer)
        # Foyer to dining room bidirectional
        create.create_object(self.exit_typeclass, key='west', location=self.foyer, destination=self.diningroom)
        create.create_object(self.exit_typeclass, key='east', location=self.diningroom, destination=self.foyer)
        
        # Upstairs to bedrooms bidirectional
        create.create_object(self.exit_typeclass, key='east', location=self.uphall, destination=self.bed1)
        create.create_object(self.exit_typeclass, key='west', location=self.bed1, destination=self.uphall)
        create.create_object(self.exit_typeclass, key='north', location=self.uphall, destination=self.bed2)
        create.create_object(self.exit_typeclass, key='south', location=self.bed2, destination=self.uphall)
        create.create_object(self.exit_typeclass, key='west', location=self.uphall, destination=self.bed3)
        create.create_object(self.exit_typeclass, key='east', location=self.bed3, destination=self.uphall)
        
        # Entry to master bedroom is one-way
        create.create_object(self.exit_typeclass, key='south', location=self.uphall, destination=self.bedmaster)
        
        # Master bedroom to dungeon bidirectional
        create.create_object(self.exit_typeclass, key='in', location=self.bedmaster, destination=self.dungeon)
        create.create_object(self.exit_typeclass, key='out', location=self.dungeon, destination=self.bedmaster)
        # Dungeon to cells bidirectional
        create.create_object(self.exit_typeclass, key='west', location=self.dungeon, destination=self.cells)
        create.create_object(self.exit_typeclass, key='east', location=self.cells, destination=self.dungeon)
        # Dungeon to lair one-way
        create.create_object(self.exit_typeclass, key='west', location=self.dungeon, destination=self.lair)
        
        # Dining room to kitchen
        create.create_object(self.exit_typeclass, key='north', location=self.diningroom, destination=self.kitchen)
        # Kitchen to basement
        create.create_object(self.exit_typeclass, key='down', location=self.kitchen, destination=self.basement)
        # Basement to crawlspace
        create.create_object(self.exit_typeclass, key='east', location=self.basement, destination=self.crawlspace)
        # Crawlspace to depths
        create.create_object(self.exit_typeclass, key='down', location=self.crawlspace, destination=self.depths)
        # Depths to cavern
        create.create_object(self.exit_typeclass, key='north', location=self.depths, destination=self.cavern)
        # Cavern to treasury
        create.create_object(self.exit_typeclass, key='west', location=self.cavern, destination=self.treasure_room)
        # Cavern to lair
        create.create_object(self.exit_typeclass, key='down', location=self.cavern, destination=self.lair)
        
        # Lair to yard
        create.create_object(self.exit_typeclass, key='up', location=self.lair, destination=self.frontyard)
        
        # map is a reserved keyword
        self.pfinder = Pathfinder()