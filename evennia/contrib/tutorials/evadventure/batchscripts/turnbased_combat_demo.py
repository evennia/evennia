# Evadventure (Turnbased) combat demo - using a batch-code file.
#
# Sets up a combat area for testing turnbased combat.
#
# First add mygame/server/conf/settings.py:
#
#    BASE_BATCHPROCESS_PATHS += ["evadventure.batchscripts"]
#
# Run from in-game as `batchcode turnbased_combat_demo`
#

# HEADER

from evennia import DefaultExit, create_object, search_object
from evennia.contrib.tutorials.evadventure.characters import EvAdventureCharacter
from evennia.contrib.tutorials.evadventure.combat_turnbased import TurnCombatCmdSet
from evennia.contrib.tutorials.evadventure.npcs import EvAdventureNPC
from evennia.contrib.tutorials.evadventure.rooms import EvAdventureRoom

# CODE

# Make the player an EvAdventureCharacter
player = caller  # caller is injected by the batchcode runner, it's the one running this script
player.swap_typeclass(EvAdventureCharacter)

# add the Turnbased cmdset
player.cmdset.add(TurnCombatCmdSet, persistent=True)

# create a weapon and an item to use
create_object(
    "contrib.tutorials.evadventure.objects.EvAdventureWeapon",
    key="Sword",
    location=player,
    attributes=[("desc", "A sword.")],
)

create_object(
    "contrib.tutorials.evadventure.objects.EvAdventureConsumable",
    key="Potion",
    location=player,
    attributes=[("desc", "A potion.")],
)

# start from limbo
limbo = search_object("#2")[0]

arena = create_object(EvAdventureRoom, key="Arena", attributes=[("desc", "A large arena.")])

# Create the exits
arena_exit = create_object(DefaultExit, key="Arena", location=limbo, destination=arena)
back_exit = create_object(DefaultExit, key="Back", location=arena, destination=limbo)

# create the NPC dummy
create_object(
    EvAdventureNPC,
    key="Dummy",
    location=arena,
    attributes=[("desc", "A training dummy."), ("hp", 1000), ("hp_max", 1000)],
)
