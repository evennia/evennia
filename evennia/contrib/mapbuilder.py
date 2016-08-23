# -*- coding: utf-8 -*-

"""

Evennia World Builder

Contribution - Cloud_Keeper 2016

This is a command capable of taking a reference to a basic 2D ASCII
map stored in the Evennia directory and  generating the rooms and exits 
necessary to populate that world. The characters of the map are iterated
over and compared to a list of trigger characters. When a match is found
it triggers the corresponding instructions. Use by importing and including 
the command in your default_cmdsets module. For example:

    # mygame/commands/default_cmdsets.py
    
    from evennia.contrib import mapbuilder
    
    ...
    
    self.add(mapbuilder.CmdMapBuilder())

You then call the command in-game using the path to the module and the
name of the variable holding the map string. The path you provide is
relative to the evennia or your mygame folder.

    @mapbuilder <path.to.module.VARNAME>

For example to generate from the sample map in this module:

    @mapbuilder evennia.contrib.mapbuilder.EXAMPLE_MAP

Whilst this map is contained here for convenience, it is suggested
that your map be stored in a separate stand alone module in the
mygame/world folder accessed with @mapbuilder world.gamemap.MAP

The rooms generated for each square of the map are generated using 
instructions for each room type. These instructions are intended 
to be changed and adapted for your purposes. In writing these 
instructions you have access to the full API just like Batchcode.

"""
# ---------- #

# This code should be in mymap.py in mygame/world.

# -*- coding: utf-8 -*-

EXAMPLE_MAP = """\
≈≈≈≈≈≈≈≈≈
≈≈≈≈≈≈≈≈≈
≈≈♣♠♣♠♣≈≈
≈≈♠n∩n♠≈≈
≈≈♣∩▲∩♣≈≈
≈≈♠n≈n♠≈≈
≈≈♣♠≈♠♣≈≈
≈≈≈≈≈≈≈≈≈
≈≈≈≈≈≈≈≈≈
"""

# ---------- #

#Add the necessary imports for your instructions here.
from evennia import create_object
from typeclasses import rooms, exits
from evennia.utils import utils
from random import randint
import random

def build_map(caller, raw_map):
    """
    This is the part of the code designed to be changed and expanded. It
    contains the instructions that are called when a match is made between
    the characters in your map and the characters that trigger the building
    instructions.
    
    """
    
    #Create a tuple containing the trigger characters
    forest = ("♣", "♠")
    #Create a function that contains the instructions.
    def create_forest(x, y):
        #This has just basic instructions, building and naming the room.
        room = create_object(rooms.Room, key="forest" + str(x) + str(y))
        room.db.desc = "Basic forest room."
        
        #Always include this at the end. Sets up for advanced functions.
        caller.msg(room.key + " " + room.dbref)
        room_list.append([room, x, y])
 
 
    mountains = ("∩", "n")
    def create_mountains(x, y):
        #We'll do something fancier in this one.
        room = create_object(rooms.Room, key="mountains" + str(x) + str(y))
        
        #We'll select a description at random from a list.
        room_desc = [
        "Mountains as far as the eye can see",
        "Your path is surrounded by sheer cliffs",
        "Haven't you seen that rock before?"]
        room.db.desc = random.choice(room_desc)
        
        #Let's populate the room with a random amount of rocks.
        for i in xrange(randint(0,3)):
            rock = create_object(key = "Rock", location = room)
            rock.db.desc = "An ordinary rock."
        
        #Mandatory.
        caller.msg(room.key + " " + room.dbref)
        room_list.append([room, x, y])
        
    temple = ("▲")
    def create_temple(x, y):
        #This room is only used once so we can be less general.
        room = create_object(rooms.Room, key="temple" + str(x) + str(y))

        room.db.desc = "In what, from the outside, appeared to be a grand " \
        "and ancient temple you've somehow found yourself in the the " \
        "Evennia Inn! It consists of one large room filled with tables. " \
        "The bardisk extends along the east wall, where multiple barrels " \
        " and bottles line the shelves. The barkeep seems busy handing " \
        "out ale and chatting with the patrons, which are a rowdy and " \
        "cheerful lot, keeping the sound level only just below thunderous" \
        ". This is a rare spot of warmth and mirth on this dread moor."
                
        #Mandatory.
        caller.msg(room.key + " " + room.dbref)
        room_list.append([room, x, y])

    #Include your keys and instructions in the master dictionary.
    master_dict = {
        forest:create_forest,
        mountains:create_mountains,
        temple:create_temple
    }

    # --- ADVANCED USERS ONLY. Altering things below may break it. ---
    
    #Create reference list and split map string to list of rows.
    room_list = []
    map = prepare_map(raw_map)
    
    caller.msg("Creating Landmass...")
    for y in xrange(len(map)):
        for x in xrange(len(map[y])):
            for key in master_dict:
                if map[y][x] in key:
                    master_dict[key](x,y)
                    
    #Creating exits
    caller.msg("Connecting Areas...")
    for location in room_list:
        x = location[1]
        y = location[2]
        
        for destination in room_list:
            #north
            if destination[1] == x and destination[2] == y-1:
                exit = create_object(exits.Exit, key="north", 
                                aliases=["n"], location=location[0], 
                                destination=destination[0])
                                
            #east
            if destination[1] == x+1 and destination[2] == y:
                exit = create_object(exits.Exit, key="east", 
                                aliases=["e"], location=location[0], 
                                destination=destination[0])                 
            #south
            if destination[1] == x and destination[2] == y+1:
                exit = create_object(exits.Exit, key="south", 
                                aliases=["s"], location=location[0], 
                                destination=destination[0])
                                
            #west
            if destination[1] == x-1 and destination[2] == y:
                exit = create_object(exits.Exit, key="west", 
                                aliases=["w"], location=location[0], 
                                destination=destination[0])   


from django.conf import settings
from evennia.utils import utils
import imp

COMMAND_DEFAULT_CLASS = utils.class_from_module(settings.COMMAND_DEFAULT_CLASS)
                                
class CmdMapBuilder(COMMAND_DEFAULT_CLASS):
    """
    Build a map from a 2D ASCII map.

    Usage:
        @mapbuilder <path.to.module.MAPNAME>

    Example:
        @mapbuilder evennia.contrib.mapbuilder.EXAMPLE_MAP
        @mapbuilder world.gamemap.MAP

    This is a simple way of building a map of placeholder or otherwise
    bare rooms from a 2D ASCII map. The command merely imports the map
    and runs the build_map function in evennia.contrib.mapbuilder.
    This function should be altered with keys and instructions that
    suit your individual needs.
    """
    key = "@mapbuilder"
    aliases = ["@buildmap"]
    locks = "cmd:superuser()"
    help_category = "Building"

    def func(self):
        "Starts the processor."

        caller = self.caller
        args = self.args
        map = None
        
        #Check if arguments passed.
        if not args:
            caller.msg("Usage: @mapbuilder <path.to.module.VARNAME>")
            return
        
        #Breaks down path into PATH, VARIABLE
        args = args.rsplit('.', 1)
        
        try:
            #Retrieves map variable from module.
            map = utils.variable_from_module(args[0],args[1])
            
        except Exception as exc:
            #Or relays error message if fails.
            caller.msg(exc)
        
        #Display map retrieved.
        caller.msg("Creating Map...") 
        caller.msg(map)
        
        #Pass map to the bulid function.
        build_map(caller, map)
        caller.msg("Map Created.")                              

#Helper function for readability.
def prepare_map(map):
    """
    Splits multi line map string into list of rows, treats for UTF-8 encoding.
    
    Args:
        map (str): An ASCII map

    Returns:
        list (list): The map split into rows
    
    """
    list_map = map.split('\n')
    return [character.decode('UTF-8') if isinstance(character, basestring) 
                else character for character in list_map]
