# Turn based battle system framework

Contrib - Tim Ashley Jenkins 2017

This is a framework for a simple turn-based combat system, similar
to those used in D&D-style tabletop role playing games. It allows
any character to start a fight in a room, at which point initiative
is rolled and a turn order is established. Each participant in combat
has a limited time to decide their action for that turn (30 seconds by
default), and combat progresses through the turn order, looping through
the participants until the fight ends.

This folder contains multiple examples of how such a system can be
implemented and customized:

    tb_basic.py - The simplest system, which implements initiative and turn
            order, attack rolls against defense values, and damage to hit
            points. Only very basic game mechanics are included.
    
    tb_equip.py - Adds weapons and armor to the basic implementation of
            the battle system, including commands for wielding weapons and
            donning armor, and modifiers to accuracy and damage based on
            currently used equipment.
	
	tb_items.py - Adds usable items and conditions/status effects, and gives
            a lot of examples for each. Items can perform nearly any sort of
            function, including healing, adding or curing conditions, or
            being used to attack. Conditions affect a fighter's attributes
            and options in combat and persist outside of fights, counting
            down per turn in combat and in real time outside combat.
	
	tb_magic.py - Adds a spellcasting system, allowing characters to cast
            spells with a variety of effects by spending MP. Spells are
            linked to functions, and as such can perform any sort of action
            the developer can imagine - spells for attacking, healing and
            conjuring objects are included as examples.
    
    tb_range.py - Adds a system for abstract positioning and movement, which
            tracks the distance between different characters and objects in
            combat, as well as differentiates between melee and ranged
            attacks.

This system is meant as a basic framework to start from, and is modeled
after the combat systems of popular tabletop role playing games rather than
the real-time battle systems that many MMOs and some MUDs use. As such, it
may be better suited to role-playing or more story-oriented games, or games
meant to closely emulate the experience of playing a tabletop RPG.

Each of these modules contains the full functionality of the battle system
with different customizations added in - the instructions to install each
one is contained in the module itself. It's recommended that you install
and test tb_basic first, so you can better understand how the other
modules expand on it and get a better idea of how you can customize the
system to your liking and integrate the subsystems presented here into
your own combat system.
