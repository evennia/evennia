# Contrib modules

Contribs are found in [evennia/contrib/](api:evennia.contrib) and are optional game-specific code-snippets 
or even full systems you can use for your game. They are contributed by the Evennia community and 
released under the same license as Evennia itself. Each contrib has its own installation instructions. 
Bugs are reported to the Evennia [issue tracker](github:issue) as usual.

## Character-related 

Contribs related to characters and character displays.

### CharGen 

*Griatch 2011*

A simple Character creator for OOC mode. Meant as a starting point for a more fleshed-out system.

### Clothing 

*FlutterSprite 2017*

A layered clothing system with slots for different types of garments auto-showing in description.

### Health Bar 

*Tim Ashley Jenkins 2017*

Tool to create colorful bars/meters.

### Multidescer 

*Griatch 2016*

Advanced descriptions combined from many separate description components, inspired by MUSH.

---

## Rooms, movement and grid

Contribs modifying locations, movement or helping to creating rooms.

### Extended Room 

*Griatch 2012*

An expanded Room typeclass with multiple descriptions for time and season as well as details.

### Map Builder 

*CloudKeeper 2016*

Build a game area based on a 2D "graphical" unicode map. Supports asymmetric exits.

- [Static in-game map](./Static-In-Game-Map)

### Simple Door 

*Griatch 2014*

Example of an exit that can be opened and closed from both sides.

###  Slow exit 

*Griatch 2014*

Custom Exit class that takes different time to pass depending on if you are walking/running etc.

### Wilderness 

*titeuf87 2017*

Make infinitely large wilderness areas with dynamically created locations.

- [Dynamic in-game map](./Dynamic-In-Game-Map)

----

## Roleplaying and rules

Contribs supporting roleplay and in-game roleplaying actions.

### Barter system 

*Griatch 2012*

A safe and effective barter-system for any game. Allows safe trading of any goods (including coin).

### Crafting

*Griatch 2020*

A full, extendable crafting system.

- [Crafting overview](./Crafting)
- [Crafting API documentation](api:evennia.contrib.crafting.crafting)
- [Example of a sword crafting tree](api:evennia.contrib.crafting.example_recipes)

### Dice 

*Griatch 2012*

A fully featured dice rolling system.

### Mail 

*grungies1138 2016*

An in-game mail system for communication.

### Puzzles 

*Hendher 2019*

Combine objects to create new items, adventure-game style

### RP System 

*Griatch 2015*

Full director-style emoting system replacing names with sdescs/recogs. Supports wearing masks.

### RP Language

*Griatch 2015*

Dynamic obfuscation of emotes when speaking unfamiliar languages. Also obfuscates whispers.

### Turnbattle 

*FlutterSprite 2017*

A turn-based combat engine meant as a start to build from. Has attack/disengage and turn timeouts,
and includes optional expansions for equipment and combat movement, magic and ranged combat.

----

## Building and server systems

### Building menu

*vincent-lg 2018*

An `@edit` command for modifying objects using a generated menu. Customizable for different games.

### Field Fill 

*FlutterSprite 2018*

A simple system for creating an EvMenu that presents a player with a highly customizable fillable form

### In-Game-Python

*Vincent Le Geoff 2017*

Allow Builders to add Python-scripted events to their objects (OBS-not for untrusted users!)

- [A voice-operated elevator using events](./A-voice-operated-elevator-using-events)
- [Dialogues using events](./Dialogues-in-events)

### Menu-builder

A tool for building using an in-game menu instead of the normal build commands. Meant to 
be expanded for the needs of your game.

- [Building Menus](./Building-menus)

### Security/Auditing 

*Johhny 2018*

Log server input/output for debug/security.

### Tree Select 

*FlutterSprite 2017*

A simple system for creating a branching EvMenu with selection options sourced from a single
multi-line string.

---

## Snippets and config

Contribs meant to be used as part of other code, or as replacements for default settings.

### Color-markups 

*Griatch, 2017*

Alternative in-game color markups.

### Custom gametime 

*Griatch, vlgeoff 2017*

Implements Evennia's gametime module but for custom game world-specific calendars.

### Logins

#### Email login

*Griatch 2012*

A variant of the standard login system that requires an email to login rather then just name+password.

#### Menu login 

*Griatch 2011, 2019, Vincent-lg 2016*

A login system using menus asking for name/password rather than giving them as one command.

### Random String Generator 

*Vincent Le Goff 2017*

Simple pseudo-random generator of strings with rules, avoiding repetitions.

### UnixCommand 

*Vincent Le Geoff 2017*

Add commands with UNIX-style syntax.

----

## Examples

Contribs not meant to be used as-is, but just as examples to learn from.

### GenderSub 

*Griatch 2015*

Simple example (only) of storing gender on a character and access it in an emote with a custom marker.

### Talking NPC 

*Griatch 2011*

A talking NPC object that offers a menu-driven conversation tree.

### Tutorial examples 

*Griatch 2011, 2015*

A folder of basic example objects, commands and scripts.

### The tutorial-world

*Griatch 2011, 2015*

The Evennia single-player sole quest. Made to be analyzed to learn.

- [The tutorial world introduction](../Howto/Starting/Part1/Tutorial-World-Introduction)

----

## Full game systems

Full game-dir replacement systems.

### Ainneve 

*Evennia community 2015-?*

This is a community attempt to make an Evennia 'example game' using good practices. It is also a good 
place to jump in if you want to help in another project rather than run it alone. Development of this 
has stalled a bit so we are looking for enthusiastic people to lead the charge.

- [evennia/ainneve repository](https://github.com/evennia/ainneve)
- [Original discussion thread](https://groups.google.com/g/evennia/c/48PMDirb7go/m/Z9EAuvXZn7UJ) (external link)

### Arxcode

*Tehom 2019*

Open source code release of the popular Evennia-based [Arx, after the reckoning](https://play.arxgame.org/). 
This is a fantasy game with a focus on roleplay and code-supported political intrigue. This code-release 
is maintained by Tehom in its own repository so bug reports should be directed there.

- [Arxcode repository on github](https://github.com/Arx-Game/arxcode)
- [Arxcode issue tracker](https://github.com/Arx-Game/arxcode/issues)
- [Arxcode installation help](./Arxcode-installing-help) - this may not always be fully up-to-date with 
  latest Evennia. Report your findings!
  
### Evscaperoom 

*Griatch 2019*

A full engine for making multiplayer 'escape-rooms' completely in code. 
This is based on the 2019 MUD Game jam winner *Evscaperoom*. 

- [contrib/evscaperoom](api:evennia.contrib.evscaperoom) - game engine to make your own escape rooms.
- [https://demo.evennia.com](https://demo.evennia.com) - a full installation of the original game can 
  be played by entering the *evscaperoom* exit in the first Limbo room.
- https://github.com/Griatch/evscaperoom - the original game's source code (warning for spoilers if you 
  want to solve the puzzles and mystery yourself).




```toctree::
    :hidden:

    ./Crafting
    ../api/evennia.contrib.crafting.crafting 
    ../api/evennia.contrib.crafting.example_recipes
    ./A-voice-operated-elevator-using-events
    ./Dialogues-in-events
    ./Dynamic-In-Game-Map
    ./Static-In-Game-Map
    ../Howto/Starting/Part1/Tutorial-World-Introduction
    ./Building-menus

```
