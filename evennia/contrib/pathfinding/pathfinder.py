from evennia import DefaultRoom as Room
from networkx.readwrite import json_graph
import networkx as nx
import json

class Pathfinder(object):
    """
    Creates a graph of your entire network of rooms and exits.
    """
    # Arbitrary delimiter used to create unique keys to use as nodes
    delimiter = '#'
    
    def __init__(self):
        """
        Creates the graph and initializes it.
        """
        self._graph = nx.DiGraph()
        self.update()
        
    def get_key(self, room):
        """
        Creates unique keys for use as nodes in the graph.

        Args:
            room (Room): Room object needing a key.
            
        Returns:
            key (str): Unique key identifying the node.
        
        """
        return self.delimiter.join([room.db_key, str(room.id)])
    
    def update(self):
        """
        Updates the graph, adding or deleting any new/old Rooms and Exits.

        Returns:
            graph (DiGraph): Networkx directional graph of your game's
                rooms and exits.

        """
        graph = self._graph
        
        # Get all Room objects in play
        all_rooms = Room.objects.all().iterator()
        
        for src in all_rooms:
            # Create node for src room
            src_key = self.get_key(src)
            
            # Check if node exists
            try: graph[src_key]
            except: graph.add_node(src_key, key=src.db_key, id=src.id, type='room')
            
            for exit in src.exits:
                # Get destination room
                dst = exit.destination
                
                # Create a node for dst room
                dst_key = self.get_key(dst)
                try: graph[dst_key]
                except: graph.add_node(dst_key, key=dst.db_key, id=dst.id, type='room')
                
                # Create an edge representing the exit
                graph.add_edge(src_key, dst_key, direction=exit.db_key, id=exit.id, type='exit')
                
        return graph
                
    def get_path(self, source, dest):
        """
        Computes shortest path between source and dest objects.
        
        This is primarily an internal function; it is recommended that you use 
        one of the other helper methods to perform any queries.
        
        Args:
            source (Room): Origin Room object.
            dest (Room): Destination Room object.

        Returns:
            path (list): List of node tokens comprising the path from the source
                to the detination.

        """
        # Get keys for source and dest
        src_key = self.get_key(source)
        dst_key = self.get_key(dest)
        
        # Get the shortest path
        path = nx.shortest_path(self._graph, source=src_key, target=dst_key)
        
        return path
        
    def get_directions(self, source, dest):
        """
        Computes shortest path between source and dest objects.
        
        Returns a list of the directional commands you would need to execute to 
        move from your starting location to your desired destination.
        
        Args:
            source (Room): Origin Room object.
            dest (Room): Destination Room object.

        Returns:
            steps (list): List of directional commands.

        """
        path = self.get_path(source, dest)
        steps = []
        
        # Get the edge attributes for each hop
        edge_ids = zip(path[0:], path[1:])
        for src, dst in edge_ids:
            direction = self._graph[src][dst]['direction']
            steps.append(direction)
        
        return steps
        
    def get_line_of_sight(self, source, direction, ordered=True):
        """
        Returns a list of Room objects accessible by following the given
        direction from the given origin. The list terminates when a Room does
        not offer continued travel in that direction.
        
        Mob AI can take advantage of this by getting the list of rooms in a
        given direction and examining the contents of each, looking for victims
        at range.
        
        This is also useful if implementing something like a sniper rifle, which
        could let a player see the occupants of any number of unobstructed rooms 
        ahead of them.
        
        Args:
            source (Room): Origin Room object.
            direction (str): Any implemented direction a character can travel
                from their source location.
            ordered (bool): Whether you want results sorted in order of distance. 
                The default is True, but False makes queries more efficient.

        Returns:
            path (list): List of directional commands needed to go from point A
                to point B.

        """
        bucket = []
        
        # Get keys for source
        src_key = self.get_key(source)
        
        # Recursively crawl as far in the given direction as we can go
        def follow(src_key, direction, bucket):
            bucket.append(src_key)
            edges = ((src, dst) for src,dst in self._graph.out_edges(src_key) if self._graph[src][dst]['direction'] == direction)
            for src, dst in edges:
                follow(dst, direction, bucket)
        follow(src_key, direction, bucket)
        
        ids = [x.split(self.delimiter)[1] for x in bucket]
        if ordered:
            return [Room.objects.get(id=x) for x in ids]
        else:
            return list(Room.objects.filter(id__in=ids))

    def draw_graph(self, filename='map.png'):
        """
        Draws the graph and its connections as a PNG.
        
        Requires matplotlib, and the result lacks aesthetics. The export_json()
        method is more flexible for external rendering; this is more here for
        debugging.
        
        Args:
            filename (str): Filename for the output file.

        """
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
        except ImportError:
            msg = 'Pathfinder draw_map() feature requires matplotlib.'
            logger.log_err(msg)
            print(msg)
            return None
            
        pos = nx.spring_layout(self._graph, scale=5, k=0.5,iterations=20)
        nx.draw(self._graph, pos, with_labels=True)
        
        plt.savefig(filename)
        
    def export_json(self):
        """
        Exports graph data in JSON format so you can do fun things like
        render it in d3.js or other libraries for display on the website.
        
        Returns:
            data (str): Serialized JSON string comprising the graph data.
            
        """
        data = json_graph.node_link_data(self._graph)
        
        # Networkx 2.0 outputs labels in the links instead of ids. This breaks d3.
        # Networkx 1.x output ids in the labels. This played better with d3.
        for index, node in enumerate(data['nodes']):
            for link in data['links']:
                if link['source'] == node['id']:
                    link['source'] = index
                if link['target'] == node['id']:
                    link['target'] = index
        
        return json.dumps(data, indent=4).replace('"id"', '"name"')