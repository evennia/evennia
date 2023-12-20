# Clothing

Contribution by Tim Ashley Jenkins, 2017

Provides a typeclass and commands for wearable clothing. These 
look of these clothes are appended to the character's description when worn.

Clothing items, when worn, are added to the character's description
in a list. For example, if wearing the following clothing items:

    a thin and delicate necklace
    a pair of regular ol' shoes
    one nice hat
    a very pretty dress

Would result in this added description: 

    Tim is wearing one nice hat, a thin and delicate necklace,
    a very pretty dress and a pair of regular ol' shoes.

## Installation

To install, import this module and have your default character
inherit from ClothedCharacter in your game's characters.py file:

```python

from evennia.contrib.game_systems.clothing import ClothedCharacter

class Character(ClothedCharacter):

```

And then add `ClothedCharacterCmdSet` in your character set in
`mygame/commands/default_cmdsets.py`:

```python

from evennia.contrib.game_systems.clothing import ClothedCharacterCmdSet # <--

class CharacterCmdSet(default_cmds.CharacterCmdSet):
     # ...
     at_cmdset_creation(self):

         super().at_cmdset_creation()
         # ...
         self.add(ClothedCharacterCmdSet)    # <--

```

## Usage

Once installed, you can use the default builder commands to create clothes
with which to test the system:

    create a pretty shirt : evennia.contrib.game_systems.clothing.Clothing
    set shirt/clothing_type = 'top'
    wear shirt

A character's description may look like this:

    Superuser(#1)
    This is User #1.

    Superuser is wearing one nice hat, a thin and delicate necklace,
    a very pretty dress and a pair of regular ol' shoes.

Characters can also specify the style of wear for their clothing - I.E.
to wear a scarf 'tied into a tight knot around the neck' or 'draped
loosely across the shoulders' - to add an easy avenue of customization.
For example, after entering:

    wear scarf draped loosely across the shoulders

The garment appears like so in the description:

    Superuser(#1)
    This is User #1.

    Superuser is wearing a fanciful-looking scarf draped loosely
    across the shoulders.

Items of clothing can be used to cover other items, and many options
are provided to define your own clothing types and their limits and
behaviors. For example, to have undergarments automatically covered
by outerwear, or to put a limit on the number of each type of item
that can be worn. The system as-is is fairly freeform - you
can cover any garment with almost any other, for example - but it
can easily be made more restrictive, and can even be tied into a
system for armor or other equipment.

## Configuration

The contrib has several optional configurations which you can define in your `settings.py`
Here are the settings and their default values.

```python
# Maximum character length of 'wear style' strings, or None for unlimited.
CLOTHING_WEARSTYLE_MAXLENGTH = 50

# The order in which clothing types appear on the description.
# Untyped clothing or clothing with a type not in this list goes last.
CLOTHING_TYPE_ORDERED = [
        "hat",
        "jewelry",
        "top",
        "undershirt",
        "gloves",
        "fullbody",
        "bottom",
        "underpants",
        "socks",
        "shoes",
        "accessory",
    ]

# The maximum number of clothing items that can be worn, or None for unlimited.
CLOTHING_OVERALL_LIMIT = 20

# The maximum number for specific clothing types that can be worn.
# If the clothing item has no type or is not specified here, the only maximum is the overall limit.
CLOTHING_TYPE_LIMIT = {"hat": 1, "gloves": 1, "socks": 1, "shoes": 1}

# What types of clothes will automatically cover what other types of clothes when worn.
# Note that clothing only gets auto-covered if it's already being worn. It's perfectly possible
# to have your underpants showing if you put them on after your pants!
CLOTHING_TYPE_AUTOCOVER = {
        "top": ["undershirt"],
        "bottom": ["underpants"],
        "fullbody": ["undershirt", "underpants"],
        "shoes": ["socks"],
    }

# Any types of clothes that can't be used to cover other clothes at all.
CLOTHING_TYPE_CANT_COVER_WITH = ["jewelry"]
```


----

<small>This document page is generated from `evennia/contrib/game_systems/clothing/README.md`. Changes to this
file will be overwritten, so edit that file rather than this one.</small>
