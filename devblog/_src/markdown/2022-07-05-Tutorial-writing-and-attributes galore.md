title: Tutorial-writing and Attributes galore
copyrights: [Alpha Stock Images](http://alphastockimages.com/) (released under [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) )

---

![Tutorial sign](images/tutorial.jpg)

It has been a while since I wrote anything for the dev blog of Evennia, the MU creation system - so it's about time!

It's been a busy spring and early summer for me, with lots of real-life work going on away from Evennia land. But that hasn't meant activity on the Evennia code base has slowed!

## Many eyes on Evennia 1.0-dev

Earlier this year I [invited people to try the Evennia develop branch](https://github.com/evennia/evennia/discussions/2640) - what will become Evennia 1.0. A lot of bold beta-testers have since swapped to using the 1.0 branch. While there are plenty of issues being reported, most seem pretty happy about it so far. As mentioned in earlier dev blogs, Evennia 1.0 has a [lot of improvements and new features](https://github.com/evennia/evennia/blob/master/CHANGELOG.md)!

As part of this, the amount of PRs being made against develop branch has increased a lot, with awesome community members stepping up to fix bugs and even address long-standing annoyances. This includes everything from big improvements in ANSI parsing, fixes to the 1.0 FuncParser, RPSystem contrib optimizations and much more - [the list of closed PRs is long](https://github.com/evennia/evennia/pulls?page=2&q=is%3Apr+is%3Aclosed).

Another big part are everyone helping to answer questions in chat and suggesting improvements to the community in general. Thanks everyone!


## The upcoming beginner tutorial

On my end, I'm working on the Beginner Tutorial for the new 1.0 documentation. This will be a multi-part tutorial where you get to make a little MUD game from scratch. It goes through the basics of Evennia all the way to releasing your little game and I hope it will help people get started. This will also lead to a new contrib - the `evadventure` package, which should (I plan) have everything the tutorial needs to run. This is useful for those that prefer picking apart existing code over reading about it.

The tutorial game itself is based on [Knave](https://www.gmbinder.com/share/-LZGcbbCQaqjIV0TmLx3), an light Old-School-Renaissance (OSR) tabletop roleplaying ruleset inspired by early editions Dungeons & Dragons. It's simple enough to fit in a tutorial but with enough wrinkles to showcase how to create some basic rpg systems in Evennia:

- Using Attributes (STR, DEX etc)
- Rules (dice rolls, advantage, contested rolls etc)
- Character generation (Knave chargen is mostly random, but it still showcases Evennia's menu system EvMenu).
- Inventory management and equipment (including limited storage as well as items worn or wielded).
- Turn-based combat system (menu based)
- - Attacking with wielded weapons (or spell rune)
- - Stunts to give you advantages for later turns or give enemies disadvantage for later turns
- - Using items for healing or other effects
- - Fleeing and chasing
- Alternative Twitch-based combat system (might be a stretch goal)
- NPCs with very simple AI, Death and respawn
- Simple Questing system with NPC quest givers and quest states
- A small example world (tech-demo)

I won't include how to make a Crafting system, since I've added a full [Crafting contrib](https://www.evennia.com/docs/1.0-dev/Contribs/Contrib-Crafting.html) to Evennia 1.0 for devs to be inspired by or tear apart.

## Some nice new things about Attributes

In general news, Evennia 1.0 will see two big improvements when it comes to [Attributes](https://www.evennia.com/docs/1.0-dev/Components/Attributes.html).

### AttributeProperty

This is a new way to write - and particularly initialize - Attributes. Traditionally in Evennia you need to initialize your object's Attributes something like this:

```python
from evennia import DefaultCharacter

class Character(DefaultCharacter):
    def at_object_creation(self):
        self.db.strength = 10
        self.db.mana = 12
```

This still works. But with the new `AttributeProperty` you can now write it like this instead:

```python
from evennia import DefaultCharacter
from evennia.typeclasses.attributes import AttributeProperty

class Character(DefaultCharacter):
    strength = AttributeProperty(10)
    mana = AttributeProperty(10)
```

This makes Attributes look more like Django fields, sitting directly on the class.  They can also have `category` and all other values you'd expect. You can still access those Attributes like normal:

```python
strength = char.db.strength
mana = char.attributes.get("mana")
```

But you can now also do just

```python
strength = char.strength
mana = char.mana
```

directly (you'll need to be careful to not override any existing properties on objects this way of course).

An interesting feature of using an `AttributeProperty` is that you can choose to _not_ actually create the `Attribute` under the hood unless the default changed:

```python
class Character(DefaultCharacter):
    strength = AttributeProperty(10, autocreate=False)
    mana = AttributeProperty(10, autocreate=False)
```

When you now access `char.strength` you will get `10` back but you won't actually be hitting the database to load anything - it's just giving you the default. Not until you _change_ the default will the actual `Attribute` be created. While this can be very powerful for optimization, note that you can of course not access such data via `char.db` or `char.attributes.get` either (because no `Attribute` yet exists). So this functionality can be confusing unless you know what you are doing. Hence `autocreate` defaults to `True`.

### Saving Attributes with hidden database objects

This is one of those classical quirks of Evennia that many have encountered. While Evennia can save a lot of things in an `Attribute`, including database objects, it cannot do so if it doesnt _know_ those database objects are there. This is fine if you are saving a list or a dict with objects in it - Evennia will go through it and make sure to serialize each db-object in turn.

But if you "hide away" your db-object you will be in trouble:

```python
class MyStore:
    def __init__(self, dbobj):
        self.dbobj = dbjobj

char = Character.objects.get(id=1)
obj.db.mystore = MyStore(char)   # leads to Traceback!
```

This fails because we store `char` inside `MyStore` and there is no way for Evennia to know it's there and to handle it properly.

For the longest time, this was just a limitation you had to accept. But with Evennia 1.0-dev you can now help Evennia out:

```python
from evennia.utils.dbserialize import dbserialize, dbunserialize

class MyStore:
    def __init__(self, dbobj):
        self.dbobj = dbobj
    def __serialize_dbobjs__(self):
        self.dbobj = dbserialize(self.dbobj)
    def __deserialize_dbobjs__(self):
        self.dbobj = dbunserialize(self.dbobj)

char = Character.objects.get(id=1)
obj.db.mystore = MyStore(char)   # now OK!
```

With the new `__serialize_dbobjs__` and `__deserialize_dbobjs__`, Evennia is told how to properly stow away the db-object (using the tools from `evennia.utils`) before trying to serialize the entire `MyStore`. And later, when loading it up, Evennia is helped to know how to restore the db-object back to normal again after the rest of `MyStore` was already loaded up.


## Moving forward ...

For Evennia 1.0, the tutorial-writing is the single biggest project that remains - that and the general documentation cleanup of our entirely rewritten documentation.

After that I will dive back in with the issues that has popped up during beta-testing of 1.0-dev and try to wrap up the most serious ones before release. Still some time away, but it's getting there ... slowly!
