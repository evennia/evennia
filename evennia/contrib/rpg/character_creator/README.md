# Character Creator contrib
by InspectorCaracal

This contrib is designed to be used in MULTISESSION_MODE = 2 or higher, where characters are not automatically created to match the account. To use this with lower modes, you'll need to implement your own solution for preventing the built-in automatic character creation.

## Installation

In your game folder `commands/default_cmdsets.py`, import and add `ContribCmdCharCreate` to your `AccountCmdSet`.

Example:
```python
from evennia.contrib.rpg.character_creator.character_creator import ContribCmdCharCreate

class AccountCmdSet(default_cmds.AccountCmdSet):
    
    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(ContribCmdCharCreate)
```

In your game folder `typeclasses/accounts.py`, import and inherit from `ContribChargenAccount` on your Account class.

(Alternatively, you can copy the `at_look` method directly into your own class.)

Example:
```python
from evennia.contrib.rpg.character_creator.character_creator import ContribChargenAccount

class Account(ContribChargenAccount):
    # your Account class code
```

By default, the new `charcreate` command will reference the example menu provided by the contrib, so you can test it
out before building your own menu. You can reference [the example menu here](/evennia/contrib/rpg/character_creator/example_menu.py) for ideas on how to build your own.

Once you have your own menu, just add it to your settings to use it. e.g. if your menu is in mygame/word/chargen_menu.py,
you'd add the following to your settings file:

```python
CHARGEN_MENU = "world.chargen_menu"
```

## Usage

### The EvMenu

In order to use the contrib, you will need to create your own chargen EvMenu. The included `example_menu.py` gives a number of useful menu node techniques with basic attribute examples for you to reference. It can be run as-is as a tutorial for yourself/your devs, or used as base for your own menu.

The example menu includes code, tips, and instructions for the following types of decision nodes:

#### Informational Pages

A small set of nodes that let you page through information on different choices before committing to one.

#### Option Categories

A pair of nodes which let you divide an arbitrary number of options into separate categories.

The base node has a list of categories as the options, and the child node displays the actual character choices.

#### Multiple Choice

Allows players to select and deselect options from the list in order to choose more than one.

#### Starting Objects

Allows players to choose from a selection of starting objects, which are then created on chargen completion.

#### Choosing a Name

The contrib assumes the player will choose their name during character creation, so the necessary code for doing so is of course included!


### `charcreate` command

The contrib overrides the character creation command - `charcreate` - to use a character creator menu, as well as supporting exiting/resuming the process. In addition, unlike the core command, it's designed for the character name to be chosen later on via the menu, so it won't parse any arguments passed to it.

### Changes to `Account.at_look`

The contrib version works mostly the same as core evennia, but adds an additional check to recognize an in-progress character. If you've modified your own `at_look` hook, it's an easy addition to make: just add this section to the playable character list loop.
```python
    for char in characters:
        # contrib code starts here
        if char.db.chargen_step:
            # currently in-progress character; don't display placeholder names
            result.append("\n - |Yin progress|n (|wcharcreate|n to continue)")
            continue
        # the rest of your code continues here
```

