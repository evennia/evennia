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
from evennia.contrib.tutorials import evadventure
from evennia.contrib.tutorials.evadventure import npcs
from evennia.contrib.tutorials.evadventure.combat_turnbased import EvAdventureCombatHandler
from evennia.contrib.tutorials.evadventure.objects import (
    EvAdventureConsumable,
    EvAdventureObject,
    EvAdventureObjectFiller,
    EvAdventureRunestone,
    EvAdventureWeapon,
)
from evennia.contrib.tutorials.evadventure.rooms import EvAdventurePvPRoom, EvAdventureRoom

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
# link to/back to hub
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
