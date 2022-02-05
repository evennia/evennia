# Gendersub

Contribution by Griatch 2015

This is a simple gender-aware Character class for allowing users to
insert custom markers in their text to indicate gender-aware
messaging. It relies on a modified msg() and is meant as an
inspiration and starting point to how to do stuff like this.

An object can have the following genders:

- male (he/his)
- female (her/hers)
- neutral (it/its)
- ambiguous (they/them/their/theirs)

## Installation

Import and add the `SetGender` command to your default cmdset in
`mygame/commands/default_cmdset.py`:

```python
# mygame/commands/default_cmdsets.py

# ...

from evennia.contrib.game_systems.gendersub import SetGender   # <---

# ...

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    # ...
    def at_cmdset_creation(self):
        # ...
        self.add(SetGender())   # <---
```

Make your `Character` inherit from `GenderCharacter`.

```python
# mygame/typeclasses/characters.py

# ...

from evennia.contrib.game_systems.gendersub import GenderCharacter  # <---

class Character(GenderCharacter):  # <---
    # ...
```

Reload the server (`evennia reload` or `reload` from inside the game).


## Usage

When in use, messages can contain special tags to indicate pronouns gendered
based on the one being addressed. Capitalization will be retained.

- `|s`, `|S`: Subjective form: he, she, it, He, She, It, They
- `|o`, `|O`: Objective form: him, her, it, Him, Her, It, Them
- `|p`, `|P`: Possessive form: his, her, its, His, Her, Its, Their
- `|a`, `|A`: Absolute Possessive form: his, hers, its, His, Hers, Its, Theirs

For example,

```
char.msg("%s falls on |p face with a thud." % char.key)
"Tom falls on his face with a thud"
```

The default gender is "ambiguous" (they/them/their/theirs).

To use, have DefaultCharacter inherit from this, or change
setting.DEFAULT_CHARACTER to point to this class.

The `gender` command is used to set the gender. It needs to be added to the
default cmdset before it becomes available.

