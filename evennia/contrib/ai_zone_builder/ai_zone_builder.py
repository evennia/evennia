"""
AI Zone Builder

This module contains functions for procedurally generating and populating
zones in Evennia using a combination of algorithms and Large Language Models (LLMs).
"""

import networkx as nx
import matplotlib.pyplot as plt

# Mock LLM Client - replace with a real client later
class MockLLMClient:
    def get_response(self, prompt):
        return "This is a mock LLM response."

class AIZoneBuilder:
    """
    A class to manage the creation of AI-powered zones.
    """
    def __init__(self, llm_client=None):
        self.llm_client = llm_client or MockLLMClient()

    def _get_num_rooms(self, size):
        if size == 'small':
            return 10
        elif size == 'medium':
            return 20
        elif size == 'large':
            return 40
        else:
            return 15  # default to medium-small

    def build_map(self, style='cave', size='medium'):
        """
        Builds a map layout as a graph.

        Args:
            style (str): The style of the zone ('cave', 'castle', etc.).
            size (str): The desired size of the zone ('small', 'medium', 'large').

        Returns:
            networkx.Graph: A graph representing the zone layout.
        """
        num_rooms = self._get_num_rooms(size)
        G = nx.Graph()
        G.add_nodes_from(range(num_rooms))

        if style == 'cave':
            # a simple linear path
            for i in range(num_rooms - 1):
                G.add_edge(i, i + 1)
        elif style == 'castle':
            # a simple grid
            grid_size = int(num_rooms**0.5)
            for i in range(num_rooms):
                if (i + 1) % grid_size != 0: # connect to the right
                    if i + 1 < num_rooms:
                        G.add_edge(i, i + 1)
                if i + grid_size < num_rooms: # connect below
                    G.add_edge(i, i + grid_size)
        else: # default to cave
            for i in range(num_rooms - 1):
                G.add_edge(i, i + 1)

        # Designate entrance and exit
        G.nodes[0]['is_entrance'] = True
        G.nodes[num_rooms - 1]['is_exit'] = True

        return G

    def visualize_map(self, G, filename="map.png"):
        """
        Generates a visual representation of the map.

        Args:
            G (networkx.Graph): The map graph.
            filename (str): The name of the file to save the visualization to.
        """
        plt.figure(figsize=(12, 12))
        pos = nx.spring_layout(G, seed=42)
        nx.draw(G, pos, with_labels=True, node_color='lightblue', node_size=500, font_size=10, font_weight='bold')
        plt.title("Zone Map")
        plt.savefig(filename)
        print(f"Map visualization saved to {filename}")

    def generate_room_descriptions(self, G, area_type, adjectives, lore=""):
        """
        Generates descriptions for each room in the map using an LLM.

        Args:
            G (networkx.Graph): The map graph.
            area_type (str): The general type of the area (e.g., 'haunted forest').
            adjectives (list): A list of adjectives to guide the description.
            lore (str, optional): Any relevant lore for the area.
        """
        for room_id in G.nodes():
            prompt = (
                f"Describe a room in a {area_type}. The room should be "
                f"{', '.join(adjectives)}. This is room {room_id} out of {len(G.nodes())}. "
                f"The room has connections to rooms {list(G.neighbors(room_id))}. "
            )
            if G.nodes[room_id].get('is_entrance'):
                prompt += "This room is the entrance to the zone. "
            if G.nodes[room_id].get('is_exit'):
                prompt += "This room is the exit from the zone. "
            if lore:
                prompt += f"Consider the following lore: {lore}"

            description = self.llm_client.get_response(prompt)
            G.nodes[room_id]['desc'] = description

        print("Generated room descriptions.")

    def populate_items(self, G, area_type):
        """
        Populates the zone with items. (STUB)
        """
        # In the future, this would use procedural logic and/or LLM calls
        # to place items in rooms based on the area type and room description.
        for room_id in G.nodes():
            G.nodes[room_id]['items'] = []

        # for now, just add a mock item to a random room
        import random
        random_room = random.choice(list(G.nodes()))
        G.nodes[random_room]['items'].append("a rusty key")
        print(f"Added a rusty key to room {random_room}.")

    def populate_npcs(self, G, area_type):
        """
        Populates the zone with NPCs. (STUB)
        """
        # This would create instances of LLMNPC and place them in rooms.
        # The NPC's characteristics would be determined by the area type and lore.
        for room_id in G.nodes():
            G.nodes[room_id]['npcs'] = []

        # for now, just add a mock npc to a random room
        import random
        random_room = random.choice(list(G.nodes()))
        G.nodes[random_room]['npcs'].append("a grumpy goblin")
        print(f"Added a grumpy goblin to room {random_room}.")

    def generate_documentation(self, G, area_type, lore=""):
        """
        Generates player and game designer guides for the zone. (STUB)
        """
        # This would use the LLM to generate two documents:
        # 1. A player's guide with hints, lore, and interesting points.
        # 2. A game designer's guide with technical details, room IDs, and plot hooks.

        player_guide_prompt = f"Write a player's guide for a {area_type} zone. {lore}"
        designer_guide_prompt = f"Write a game designer's guide for a {area_type} zone. {lore}"

        player_guide = self.llm_client.get_response(player_guide_prompt)
        designer_guide = self.llm_client.get_response(designer_guide_prompt)

        with open("player_guide.md", "w") as f:
            f.write(player_guide)
        with open("designer_guide.md", "w") as f:
            f.write(designer_guide)

        print("Generated player and designer guides.")

    def test_zone(self, G):
        """
        Tests the generated zone by simulating navigation and interaction. (STUB)
        """
        # This would involve:
        # 1. Loading the graph data into a temporary Evennia instance.
        # 2. Creating a test character.
        # 3. Navigating the character to every room.
        # 4. Attempting to interact with every object and NPC.
        # 5. Logging any errors encountered.
        error_report = "No errors found."
        print("Testing zone... " + error_report)
        return error_report

    def fix_zone_errors(self, error_report):
        """
        Attempts to fix errors found during testing. (STUB)
        """
        # This would use an LLM to analyze the error report and suggest
        # changes to the zone data. For example, if an exit is one-way,
        # it might create a corresponding exit in the other direction.
        if "No errors" in error_report:
            print("No errors to fix.")
        else:
            print("Fixing errors... (not really, this is a stub)")


if __name__ == '__main__':
    # This block will be used for demonstrating the functionality.
    builder = AIZoneBuilder()
    cave_map = builder.build_map(style='cave', size='small')
    castle_map = builder.build_map(style='castle', size='medium')

    # In a real scenario, we'd do more than just print the edges.
    print("Cave Map Edges:", list(cave_map.edges))
    print("Castle Map Edges:", list(castle_map.edges))

    builder.visualize_map(cave_map, "cave_map.png")
    builder.visualize_map(castle_map, "castle_map.png")

    builder.generate_room_descriptions(
        cave_map, "dark cave", ["damp", "echoing"], "A forgotten mine."
    )
    # print one of the descriptions
    print("Description for room 3 in cave:", cave_map.nodes[3]['desc'])

    builder.populate_items(cave_map, "dark cave")
    builder.populate_npcs(cave_map, "dark cave")
    builder.generate_documentation(cave_map, "dark cave", "A forgotten mine.")
    error_report = builder.test_zone(cave_map)
    builder.fix_zone_errors(error_report)
