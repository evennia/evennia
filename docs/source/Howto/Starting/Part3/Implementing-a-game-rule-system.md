# Implementing a game rule system


The simplest way to create an online roleplaying game (at least from a code perspective) is to
simply grab a paperback RPG rule book, get a staff of game masters together and start to run scenes
with whomever logs in. Game masters can roll their dice in front of their computers and tell the
players the results. This is only one step away from a traditional tabletop game and puts heavy
demands on the staff - it is unlikely staff will be able to keep up around the clock even if they
are very dedicated.

Many games, even the most roleplay-dedicated, thus tend to allow for players to mediate themselves
to some extent. A common way to do this is to introduce *coded systems* - that is, to let the
computer do some of the heavy lifting. A basic thing is to add an online dice-roller so everyone can
make rolls and make sure noone is cheating. Somewhere at this level you find the most bare-bones
roleplaying MUSHes.

The advantage of a coded system is that as long as the rules are fair the computer is too - it makes
no judgement calls and holds no personal grudges (and cannot be accused of holding any). Also, the
computer doesn't need to sleep and can always be online regardless of when a player logs on. The
drawback is that a coded system is not flexible and won't adapt to the unprogrammed actions human
players may come up with in role play. For this reason many roleplay-heavy MUDs do a hybrid
variation - they use coded systems for things like combat and skill progression but leave role play
to be mostly freeform, overseen by staff game masters.

Finally, on the other end of the scale are less- or no-roleplay games, where game mechanics (and
thus player fairness) is the most important aspect. In such games the only events with in-game value
are those resulting from code. Such games are very common and include everything from hack-and-slash
MUDs to various tactical simulations.

So your first decision needs to be just what type of system you are aiming for. This page will try
to give some ideas for how to organize the "coded" part of your system, however big that may be.

## Overall system infrastructure

We strongly recommend that you code your rule system as stand-alone as possible. That is, don't
spread your skill check code, race bonus calculation, die modifiers or what have you all over your
game.

- Put everything you would need to look up in a rule book into a module in `mygame/world`. Hide away
as much as you can.  Think of it as a black box (or maybe the code representation of an all-knowing
game master). The rest of your game will ask this black box questions and get answers back. Exactly
how it arrives at those results should not need to be known outside the box.  Doing it this way
makes it easier to change and update things in one place later.
- Store only the minimum stuff you need with each game object. That is, if your Characters need
values for Health, a list of skills etc, store those things on the Character - don't store how to
roll or change them.
- Next is to determine just how you want to store things on your Objects and Characters. You can
choose to either store things as individual [Attributes](../../../Components/Attributes), like `character.db.STR=34` and
`character.db.Hunting_skill=20`. But you could also use some custom storage method, like a
dictionary `character.db.skills = {"Hunting":34, "Fishing":20, ...}`. A much more fancy solution is
to look at the Ainneve [Trait
handler](https://github.com/evennia/ainneve/blob/master/world/traits.py). Finally you could even go
with a [custom django model](../../../Concepts/New-Models). Which is the better depends on your game and the
complexity of your system.
- Make a clear [API](https://en.wikipedia.org/wiki/Application_programming_interface) into your
rules. That is, make methods/functions that you feed with, say, your Character and which skill you
want to check. That is, you want something similar to this:

    ```python
        from world import rules
        result = rules.roll_skill(character, "hunting")
        result = rules.roll_challenge(character1, character2, "swords")
    ```

You might need to make these functions more or less complex depending on your game. For example the
properties of the room might matter to the outcome of a roll (if the room is dark, burning etc).
Establishing just what you need to send into your game mechanic module is a great way to also get a
feel for what you need to add to your engine.

## Coded systems

Inspired by tabletop role playing games, most game systems mimic some sort of die mechanic. To this
end Evennia offers a full [dice
roller](https://github.com/evennia/evennia/blob/master/evennia/contrib/dice.py) in its `contrib`
folder. For custom implementations, Python offers many ways to randomize a result using its in-built
`random` module. No matter how it's implemented, we will in this text refer to the action of
determining an outcome as a "roll".

In a freeform system, the result of the roll is just compared with values and people (or the game
master) just agree on what it means. In a coded system the result now needs to be processed somehow.
There are many things that may happen as a result of rule enforcement:

- Health may be added or deducted. This can effect the character in various ways.
- Experience may need to be added, and if a level-based system is used, the player might need to be
informed they have increased a level.
- Room-wide effects need to be reported to the room, possibly affecting everyone in the room.

There are also a slew of other things that fall under "Coded systems", including things like
weather, NPC artificial intelligence and game economy. Basically everything about the world that a
Game master would control in a tabletop role playing game can be mimicked to some level by coded
systems.


## Example of Rule module

Here is a simple example of a rule module. This is what we assume about our simple example game:
- Characters have only four numerical values:
    - Their `level`, which starts at 1.
    - A skill `combat`, which determines how good they are at hitting things. Starts between 5 and
10.
    - Their Strength, `STR`, which determine how much damage they do. Starts between 1 and 10.
    - Their Health points, `HP`, which starts at 100.
- When a Character reaches `HP = 0`, they are presumed "defeated". Their HP is reset and they get a
failure message (as a stand-in for death code).
- Abilities are stored as simple Attributes on the Character.
- "Rolls" are done by rolling a 100-sided die. If the result is below the `combat` value, it's a
success and damage is rolled. Damage is rolled as a six-sided die + the value of `STR` (for this
example we ignore weapons and assume `STR` is all that matters).
- Every successful `attack` roll gives 1-3 experience points (`XP`). Every time the number of `XP`
reaches `(level + 1) ** 2`, the Character levels up. When leveling up, the Character's `combat`
value goes up by 2 points and `STR` by one (this is a stand-in for a real progression system).

### Character

The Character typeclass is simple. It goes in `mygame/typeclasses/characters.py`. There is already
an empty `Character` class there that Evennia will look to and use.

```python
from random import randint
from evennia import DefaultCharacter

class Character(DefaultCharacter):
    """
    Custom rule-restricted character. We randomize
    the initial skill and ability values bettween 1-10.
    """
    def at_object_creation(self):
        "Called only when first created"
        self.db.level = 1
        self.db.HP = 100
        self.db.XP = 0
        self.db.STR = randint(1, 10)
        self.db.combat = randint(5, 10)
```

`@reload` the server to load up the new code. Doing `examine self` will however *not* show the new
Attributes on yourself. This is because the `at_object_creation` hook is only called on *new*
Characters. Your Character was already created and will thus not have them. To force a reload, use
the following command:

```
@typeclass/force/reset self
```

The `examine self` command will now show the new Attributes.

### Rule module

This is a module `mygame/world/rules.py`.

```python
from random import randint

def roll_hit():
    "Roll 1d100"
    return randint(1, 100)

def roll_dmg():
    "Roll 1d6"
    return randint(1, 6)

def check_defeat(character):
    "Checks if a character is 'defeated'."
    if character.db.HP <= 0:
       character.msg("You fall down, defeated!")
       character.db.HP = 100   # reset

def add_XP(character, amount):
    "Add XP to character, tracking level increases."
    character.db.XP += amount
    if character.db.XP >= (character.db.level + 1) ** 2:
        character.db.level += 1
        character.db.STR += 1
        character.db.combat += 2
        character.msg(f"You are now level {character.db.level}!")

def skill_combat(*args):
    """
    This determines outcome of combat. The one who
    rolls under their combat skill AND higher than
    their opponent's roll hits.
    """
    char1, char2 = args
    roll1, roll2 = roll_hit(), roll_hit()
    failtext_template = "You are hit by {attacker} for {dmg} damage!"
    wintext_template = "You hit {target} for {dmg} damage!"
    xp_gain = randint(1, 3)
    if char1.db.combat >= roll1 > roll2:
        # char 1 hits
        dmg = roll_dmg() + char1.db.STR
        char1.msg(wintext_template.format(target=char2, dmg=dmg))
        add_XP(char1, xp_gain)
        char2.msg(failtext_template.format(attacker=char1, dmg=dmg))
        char2.db.HP -= dmg
        check_defeat(char2)
    elif char2.db.combat >= roll2 > roll1:
        # char 2 hits
        dmg = roll_dmg() + char2.db.STR
        char1.msg(failtext_template.format(attacker=char2, dmg=dmg))
        char1.db.HP -= dmg
        check_defeat(char1)
        char2.msg(wintext_template.format(target=char1, dmg=dmg))
        add_XP(char2, xp_gain)
    else:
        # a draw
        drawtext = "Neither of you can find an opening."
        char1.msg(drawtext)
        char2.msg(drawtext)

SKILLS = {"combat": skill_combat}

def roll_challenge(character1, character2, skillname):
    """
    Determine the outcome of a skill challenge between
    two characters based on the skillname given.
    """
    if skillname in SKILLS:
        SKILLS[skillname](character1, character2)
    else:
        raise RunTimeError(f"Skillname {skillname} not found.")
```

These few functions implement the entirety of our simple rule system.  We have a function to check
the "defeat" condition and reset the `HP` back to 100 again. We define a generic "skill" function.
Multiple skills could all be added with the same signature; our `SKILLS` dictionary makes it easy to
look up the skills regardless of what their actual functions are called. Finally, the access
function `roll_challenge` just picks the skill and gets the result.

In this example, the skill function actually does a lot - it not only rolls results, it also informs
everyone of their results via `character.msg()` calls.

Here is an example of usage in a game command:

```python
from evennia import Command
from world import rules

class CmdAttack(Command):
    """
    attack an opponent

    Usage:
      attack <target>

    This will attack a target in the same room, dealing
    damage with your bare hands.
    """
    def func(self):
        "Implementing combat"

        caller = self.caller
        if not self.args:
            caller.msg("You need to pick a target to attack.")
            return

        target = caller.search(self.args)
        if target:
            rules.roll_challenge(caller, target, "combat")
```

Note how simple the command becomes and how generic you can make it.  It becomes simple to offer any
number of Combat commands by just extending this functionality - you can easily roll challenges and
pick different skills to check. And if you ever decided to, say, change how to determine hit chance,
you don't have to change every command, but need only change the single `roll_hit` function inside
your `rules` module.