"""
Evadventure Techdemo area

This is is used for testing specific features without any story or overall gameplay

While this looks like a Python module, it is meant to run with the `batchcode` processor in-game:

    batchcode evadventure.build_techdemo

This will step through the #CODE blocks of this file to build the tech demo. For help with using
the batchcode processor, see the
[processor documentation](https://www.evennia.com/docs/latest/Components/Batch-Code-Processor.html).

You can also build/rebuild individiaul #CODE blocks in the `batchcode/interactive` mode.

"""

# HEADER

# this is loaded at the top of every #CODE block

from evennia import DefaultExit, create_object, search_object
from evennia.contrib.tutorials.evadventure import npcs
from evennia.contrib.tutorials.evadventure.dungeon import (
    EvAdventureDungeonStartRoom,
    EvAdventureDungeonStartRoomExit,
)
from evennia.contrib.tutorials.evadventure.objects import EvAdventureWeapon
from evennia.contrib.tutorials.evadventure.rooms import (
    EvAdventurePvPRoom,
    EvAdventureRoom,
)

# CODE

# Hub room evtechdemo#00
# for other test areas to link back to. Connects in turn back to Limbo.

limbo = search_object("Limbo")[0]
hub_room = create_object(
    EvAdventureRoom,
    key="Techdemo Hub",
    aliases=("evtechdemo#00",),
    attributes=[("desc", "Central hub for EvAdventure tech demo.")],
)
create_object(
    DefaultExit,
    key="EvAdventure Techdemo",
    aliases=("techdemo", "demo", "evadventure"),
    location=limbo,
    destination=hub_room,
)
create_object(
    DefaultExit,
    key="Back to Limbo",
    aliases=("limbo", "back"),
    location=hub_room,
    destination=limbo,
)


# CODE

# A combat room evtechdemo#01
# with a static enemy

combat_room = create_object(EvAdventurePvPRoom, key="Combat Arena", aliases=("evtechdemo#01",))
# link to/back to/from hub
hub_room = search_object("evtechdemo#00")[0]
create_object(
    DefaultExit, key="combat test", aliases=("combat",), location=hub_room, destination=combat_room
)
create_object(
    DefaultExit,
    key="Back to Hub",
    aliases=("back", "hub"),
    location=combat_room,
    destination=hub_room,
)
# create training dummy with a stick
combat_room_enemy = create_object(
    npcs.EvAdventureMob, key="Training Dummy", aliases=("dummy",), location=combat_room
)
weapon_stick = create_object(EvAdventureWeapon, key="stick", attributes=(("damage_roll", "1d2"),))
combat_room_enemy.weapon = weapon_stick


# CODE

# A dungeon start room for testing the dynamic dungeon generation.

dungeon_start_room = create_object(
    EvAdventureDungeonStartRoom,
    key="Dungeon start room",
    aliases=("evtechdemo#02",),
    attributes=(("desc", "A central room, with dark exits leading to mysterious fates."),),
)
# link to/back to/from hub
hub_room = search_object("evtechdemo#00")[0]
create_object(
    DefaultExit,
    key="dungeon test",
    aliases=("dungeon",),
    location=hub_room,
    destination=dungeon_start_room,
)
create_object(
    DefaultExit,
    key="Back to Hub",
    aliases=("back", "hub"),
    location=dungeon_start_room,
    destination=hub_room,
)

# add special exits out of the dungeon start room.
# These must have one of the 8 cardinal directions
# we point these exits back to the same location, which
# is what the system will use to trigger generating a new room
create_object(
    EvAdventureDungeonStartRoomExit,
    key="north",
    aliases=("n",),
    location=dungeon_start_room,
    destination=dungeon_start_room,
)
create_object(
    EvAdventureDungeonStartRoomExit,
    key="east",
    aliases=("e",),
    location=dungeon_start_room,
    destination=dungeon_start_room,
)
create_object(
    EvAdventureDungeonStartRoomExit,
    key="south",
    aliases=("s",),
    location=dungeon_start_room,
    destination=dungeon_start_room,
)
create_object(
    EvAdventureDungeonStartRoomExit,
    key="west",
    aliases=("w",),
    location=dungeon_start_room,
    destination=dungeon_start_room,
)
