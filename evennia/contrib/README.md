
# Contrib folder

`evennia/contrib/` contains 'contributions': extra snippets of code that are
potentially very useful for the game coder but which are considered
too game-specific to be a part of the main Evennia game server.  These
modules are not used unless you explicitly import them. See each file
for more detailed instructions on how to install.

Modules in this folder are distributed under the same licence as
Evennia unless noted differently in the individual module.

If you want to edit, tweak or expand on this code you should copy the
things you want from here into your game folder and change them there.

## Contrib modules

* Barter system (Griatch 2012) - A safe and effective barter-system
  for any game. Allows safe trading of any goods (including coin).
* Building menu (vincent-lg 2018) - An `@edit` command for modifying
  objects using a generated menu. Customizable for different games.
* CharGen (Griatch 2011) - A simple Character creator for OOC mode.
  Meant as a starting point for a more fleshed-out system.
* Clothing (FlutterSprite 2017) - A layered clothing system with
  slots for different types of garments auto-showing in description.
* Color-markups (Griatch, 2017) - Alternative in-game color markups.
* Custom gametime (Griatch, vlgeoff 2017) - Implements Evennia's
  gametime module but for custom game world-specific calendars.
* Dice (Griatch 2012) - A fully featured dice rolling system.
* Email-login (Griatch 2012) - A variant of the standard login system
  that requires an email to login rather then just name+password.
* Evscaperoom (Griatch 2019) - A full engine for making escaperoom puzzles
* Extended Room (Griatch 2012) - An expanded Room typeclass with
  multiple descriptions for time and season as well as details.
* Field Fill (FlutterSprite 2018) - A simple system for creating an
  EvMenu that presents a player with a highly customizable fillable
  form
* GenderSub (Griatch 2015) - Simple example (only) of storing gender
  on a character and access it in an emote with a custom marker.
* Health Bar (Tim Ashley Jenkins 2017) - Tool to create colorful bars/meters.
* Mail (grungies1138 2016) - An in-game mail system for communication.
* Menu login (Griatch 2011, 2019, Vincent-lg 2016) - A login system using menus asking
  for name/password rather than giving them as one command.
* Map Builder (CloudKeeper 2016) - Build a game area based on a 2D
  "graphical" unicode map. Supports assymmetric exits.
* Menu Login (Vincent-lg 2016) - Alternate login system using EvMenu.
* Multidescer (Griatch 2016) - Advanced descriptions combined from
  many separate description components, inspired by MUSH.
* Puzzles (Hendher 2019) - Combine objects to create new items, adventure-game style
* Random String Generator (Vincent Le Goff 2017) - Simple pseudo-random
  generator of strings with rules, avoiding repetitions.
* RPLanguage (Griatch 2015) - Dynamic obfuscation of emotes when
  speaking unfamiliar languages. Also obfuscates whispers.
* RPSystem (Griatch 2015) - Full director-style emoting system
  replacing names with sdescs/recogs. Supports wearing masks.
* Security/Auditing (Johhny 2018) - Log server input/output for debug/security.
* Simple Door - Example of an exit that can be opened and closed.
* Slow exit (Griatch 2014) - Custom Exit class that takes different
  time to pass depending on if you are walking/running etc.
* Talking NPC (Griatch 2011) - A talking NPC object that offers a
  menu-driven conversation tree.
* Tree Select (FlutterSprite 2017) - A simple system for creating a
  branching EvMenu with selection options sourced from a single
  multi-line string.
* Wilderness (titeuf87 2017) - Make infinitely large wilderness areas
  with dynamically created locations.
* UnixCommand (Vincent Le Geoff 2017) - Add commands with UNIX-style syntax.

## Contrib packages

* In-game Python (Vincent Le Goff 2017) - Allow trusted builders to script
  objects and events using Python from in-game.
* Turnbattle (FlutterSprite 2017) - A turn-based combat engine meant
  as a start to build from. Has attack/disengage and turn timeouts,
  and includes optional expansions for equipment and combat movement, magic 
  and ranged combat.
* Tutorial examples (Griatch 2011, 2015) - A folder of basic
  example objects, commands and scripts.
* Tutorial world (Griatch 2011, 2015) - A folder containing the
  rooms, objects and commands for building the Tutorial world.
