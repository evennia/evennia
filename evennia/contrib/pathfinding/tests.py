from evennia import create_script, DefaultScript, DefaultRoom
from evennia.contrib.pathfinding.pathfinder import Pathfinder
from evennia.contrib.pathfinding.scripts import PathfinderScript
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

class PathfinderTest(EvenniaTest):
    
    def test_script(self):
        "Tests handling of script"
        # Initialize the script as an obj
        pf_script = PathfinderScript.spawn()
        self.assertTrue(pf_script, 'The Pathfinder script was not retrieved.')
        
        # Make sure it has nodes
        self.assertTrue(pf_script.map.nodes(), 'Pathfinder has no nodes.')
        
        # Ask script for directions
        directions = pf_script.map.get_directions(self.basement, self.bedmaster)
        self.assertTrue(directions, 'No directions were returned!')
        self.assertTrue(len(directions) > 2, 'Too few directions were returned!')
    
    def test_get_path(self):
        "Get path from Kitchen to Lair"
        path = self.pfinder.get_path(self.kitchen, self.lair)
        self.assertTrue(path, 'No path was computed from kitchen to lair.')
        
        # Test path that doesn't exist
        path = self.pfinder.get_path(self.lair, self.stairs)
        self.assertFalse(path, 'There is no path from the Lair to the Infinite Stairs. %s should not have been returned.' % path)
        
        # Get path from bedroom to treasure room
        path = self.pfinder.get_path(self.bed1, self.treasure_room)
        self.assertTrue(path, 'No path was computed from bedroom to treasure room.')
        
    def test_get_usable_path(self):
        "Make sure pathfinding abides by locks"
        
        # Create a hall
        halls = [create.create_object(self.room_typeclass, key="Subway Passage %i" % x, nohome=True) for x in xrange(6)]
        hall_pairs = zip(halls[0:], halls[1:])
        for source, dest in hall_pairs:
            create.create_object(self.exit_typeclass, key='east', location=source, destination=dest)
            create.create_object(self.exit_typeclass, key='west', location=dest, destination=source)
            
        # Block traversal through the subway
        for exit in halls[-2].exits:
            exit.locks.add('traverse:none()')
        
        # Create a much longer maintenance tunnel that routes around the locked door
        tunnels = [create.create_object(self.room_typeclass, key="Maintenance Tunnel %i" % x, nohome=True) for x in xrange(15)]
        tunnel_pairs = zip(tunnels[0:], tunnels[1:])
        for source, dest in tunnel_pairs:
            create.create_object(self.exit_typeclass, key='east', location=source, destination=dest)
            create.create_object(self.exit_typeclass, key='west', location=dest, destination=source)
            
        # Tie the start/end of the tunnels to the start/end of the passage
        create.create_object(self.exit_typeclass, key='north', location=halls[0], destination=tunnels[0])
        create.create_object(self.exit_typeclass, key='south', location=tunnels[0], destination=halls[0])
        create.create_object(self.exit_typeclass, key='north', location=halls[-1], destination=tunnels[-1])
        create.create_object(self.exit_typeclass, key='south', location=tunnels[-1], destination=halls[-1])
        
        self.char3 = create.create_object(self.character_typeclass, key="Char3", location=halls[0], home=halls[0])
        for x in xrange(10):
            self.char3.execute_cmd('east')
        self.assertTrue(self.char3.location != halls[-1], 'Character walked through a locked door.')
        
        # Update pathfinder
        self.pfinder.update()
        
        path = self.pfinder.get_usable_path(halls[0], halls[-1], self.char3)
        self.assertTrue(len(path) > 6, 'Character was routed through a locked door.')
        
    def test_get_queryset(self):
        "Make sure get_queryset functionality works as intended"
        # Create a dummy pathfinder with a specific queryset
        dummy = Pathfinder(queryset=DefaultRoom.objects.all()[:10])
        
        # Make sure we get a valid generator back
        self.assertEqual(len([x for x in dummy.get_queryset()]), 10)
        
        # Try again, setting queryset after init
        dummy = Pathfinder()
        dummy.queryset = DefaultRoom.objects.all()[:10]
        
        # Make sure we get a valid generator back
        self.assertEqual(len([x for x in dummy.get_queryset()]), 10)
        
    def test_get_directions(self):
        "Get list of fewest movements required to go from Kitchen to Lair"
        path = self.pfinder.get_directions(self.kitchen, self.lair)
        correct = ['down', 'east', 'down', 'north', 'down']
        self.assertEqual(list(path), correct, "Did not return the correct path.")
        
    def test_get_line_of_sight(self):
        "Returns all Room objects in line of sight from source"
        objs = self.pfinder.get_line_of_sight(self.kitchen, 'down', None)
        self.assertTrue(objs)
        self.assertEqual(2, len(objs))
        
        # Test line of sight for invalid direction
        objs = self.pfinder.get_line_of_sight(self.kitchen, 'yonder', None)
        self.assertTrue(len(objs) == 1, 'There is no line of sight from Kitchen to "yonder"; this should not have returned anything further than the Kitchen (%s).' % objs)
        
        # Make sure distance limiter works.
        caboose = self.dungeon_train[0]
        objs = self.pfinder.get_line_of_sight(caboose, 'east', None, 3)
        self.assertEqual(len(objs), 3, 'Player should only be able to see 3 cars ahead on the Dungeon Train (sees %s).' % objs)
        
        # Make sure we break out of circular paths
        stairs = self.stairs
        # Set distance to something obscenely high so the counter doesn't get in the way
        objs = self.pfinder.get_line_of_sight(stairs, 'up', 9999999999)
        self.assertEqual(len(objs), 1, 'Infinite stairs are unacceptable!')
        
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
        
        # Create a linear set of rooms with unidirectional exits
        dungeon_train = self.dungeon_train = [create.create_object(self.room_typeclass, key="Dungeon Train Railcar #%i" % x, nohome=True) for x in xrange(10)]
        car_pairs = zip(dungeon_train[0:], dungeon_train[1:])
        for source, dest in car_pairs:
            create.create_object(self.exit_typeclass, key='east', location=source, destination=dest)
            
        # Create a circular path
        stairs = self.stairs = create.create_object(self.room_typeclass, key="Staircase", nohome=True)
        create.create_object(self.exit_typeclass, key='up', location=stairs, destination=stairs)
        create.create_object(self.exit_typeclass, key='down', location=stairs, destination=stairs)
        
        # map is a reserved keyword
        self.pfinder = Pathfinder().update()