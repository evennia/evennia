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

from evennia.contrib.game_systems.clothing import ClothedCharacterCmdSet <--

class CharacterCmdSet(default_cmds.CharacterCmdSet):
     # ...
     at_cmdset_creation(self):

         super().at_cmdset_creation()
         ...
         self.add(ClothedCharacterCmdSet)    # <--

```

From here, you can use the default builder commands to create clothes
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

