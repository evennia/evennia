# Searching for things

We have gone through how to create the various entities in Evennia. But creating something is of little use if we cannot find and use it afterwards.

```{sidebar} Python code vs using the py command
Most of these tools are intended to be used in Python code, as you create your game. We 
give examples of how to test things out from the `py` command, but that's just for experimenting and normally not how you code your game. 
```

To test out the examples in this tutorial, let's create a few objects we can search for in the current location. 

    > create/drop Rose 
    
## Searching using Object.search

On the `DefaultObject` is a `.search` method which we have already tried out when we made Commands. For this to be used you must already have an object available, and if you are using `py` you can use yourself: 

    py self.search("rose")
    Rose

- This searches by `key` or `alias` of the object. Strings are always case-insensitive, so searching for `"rose"`, `"Rose"` or `"rOsE"` give the same results. 
- By default it will always search for objects among those in `obj.location.contents` and `obj.contents` (that is, things in obj's inventory or in the same room).
- It will always return exactly one match. If it found zero or more than one match, the return is `None`. This is different from `evennia.search` (see below), which always returns a list.
- On a no-match or multimatch, `.search` will automatically send an error message to `obj`. So you don't have to worry about reporting messages if the result is `None`.

In other words, this method handles error messaging for you. A very common way to use it is in commands. You can put your command anywhere, but let's try the pre-filled-in `mygame/commands/command.py`.

```python
# in for example mygame/commands/command.py

from evennia import Command as BaseCommand

class Command(BaseCommand): 
    # ... 

class CmdQuickFind(Command):
    """ 
    Find an item in your current location.

    Usage: 
        quickfind <query>
        
	"""

    key = "quickfind"

    def func(self):
        query = self.args
        result = self.caller.search(query)
        if not result:
            return
        self.caller.msg(f"Found match for {query}: {result}")
```

If you want to test this command out, add it to the default cmdset (see [the Command tutorial](./Beginner-Tutorial-Adding-Commands.md) for more details) and then reload the server with `reload`: 

```python
# in mygame/commands/default_cmdsets.py

# ...

from commands.command import CmdQuickFind    # <-------

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    # ... 
    def at_cmdset_creation(self): 
        # ... 
        self.add(CmdQuickFind())   # <------

```


Remember, `self.caller` is the one calling the command. This is usually a Character, which
inherits from `DefaultObject`. So it has `.search()` available on it.

This simple little Command takes its arguments and searches for a match. If it can't find it, `result` will be `None`. The error has already been reported to `self.caller` so we just abort with `return`.

With the `global_search` flag, you can use `.search` to find anything, not just stuff in the same room:

```python
volcano = self.caller.search("Vesuvio", global_search=True)
```

You can limit your matches to particular typeclasses: 

```python
water_glass = self.caller.search("glass", typeclass="typeclasses.objects.WaterGlass")
```

If you only want to search for a specific list of things, you can do so too:

```python
stone = self.caller.search("MyStone", candidates=[obj1, obj2, obj3, obj4])
```

This will only return a match if "MyStone"  is in the room (or in your inventory) _and_ is one of the four provided candidate objects. This is quite powerful, here's how you'd find something only in your inventory:

```python
potion = self.caller.search("Healing potion", candidates=self.caller.contents)
```

You can also turn off the automatic error handling:

```python
swords = self.caller.search("Sword", quiet=True)  # returns a list!
```

With `quiet=True` the user will not be notified on zero or multi-match errors. Instead you are expected to handle this yourself. Furthermore, what is returned is now a list of zero, one or more matches!
    
## Main search functions

The base search tools of Evennia are the `evennia.search_*` functions, such as `evennia.search_object`. These are normally used in your code, but you can also try them out in-game using `py`:

     > py evennia.search_object("rose")
     <Queryset [Rose]>

```{sidebar} Querysets

What is returned from the main search functions is actually a `queryset`. They can be treated like lists except that they can't modified in-place. We'll discuss querysets in the [next lesson](./Beginner-Tutorial-Django-queries.md)

```
This searches for objects based on `key` or `alias`.  The `.search` method we talked about in the previous section in fact wraps `evennia.search_object` and handles its output in various ways. Here's the same example in Python code, for example as part of a command or coded system: 

```python
import evennia 

roses = evennia.search_object("rose")
accts = evennia.search_account("YourName")
```

Above we find first the rose and then an Account. You can try both using `py`: 

    > py evennia.search_object("rose")[0]
    Rose
    > py evennia.search_account("YourName")[0]
    <Player: YourName>

The `search_object/account` returns all matches. We use `[0]` to only get the first match of the queryset, which in this case gives us the rose and your Account respectively. Note that if you don't find any matches, using `[0]` like this leads to an error, so it's mostly useful for debugging.

In other situations, having zero or more than one match is a sign of a problem and you need to handle this case yourself. This is too detailed for testing out just with `py`, but good to know if you want to make your own search methods:

```python
    the_one_ring = evennia.search_object("The one Ring")
    if not the_one_ring:
        # handle not finding the ring at all
    elif len(the_one_ring) > 1:
        # handle finding more than one ring
    else:
        # ok - exactly one ring found
        the_one_ring = the_one_ring[0]
```

There are equivalent search functions for all the main resources. You can find a listing of them [in the Search functions section](../../../Evennia-API.md) of the API front page.

## Understanding object relationships

It's important to understand how objects relate to one another when searching. 

Let's consider a `chest` with a `coin` inside it. The chest stands in a `dungeon` room. In the dungeon is also a `door` (an exit leading outside).

```
┌───────────────────────┐
│dungeon                │
│    ┌─────────┐        │
│    │chest    │ ┌────┐ │
│    │  ┌────┐ │ │door│ │
│    │  │coin│ │ └────┘ │
│    │  └────┘ │        │
│    │         │        │
│    └─────────┘        │
│                       │
└───────────────────────┘
```

If you have access to any in-game Object, you can find related objects by use if its `.location` and `.contents` properties.

- `coin.location` is `chest`.
- `chest.location` is `dungeon`.
- `door.location` is `dungeon`.
- `room.location` is `None` since it's not inside something else.

One can use this to find what is inside what. For example, `coin.location.location` is the `dungeon`. 

- `room.contents` is `[chest, door]`
- `chest.contents` is `[coin]`
- `coin.contents` is `[]`, the empty list since there's nothing 'inside' the coin.
- `door.contents` is `[]` too.

A convenient helper is `.contents_get` - this allows to restrict what is returned:

- `room.contents_get(exclude=chest)` - this returns everything in the room except the chest (maybe it's hidden?)

There is a special property for finding exits:

- `room.exits` is `[door]`
- `coin.exits` is `[]` since it has no exits (same for all the other objects)

There is a property `.destination` which is only used by exits:

- `door.destination` is `outside` (or wherever the door leads)
- `room.destination` is `None` (same for all the other non-exit objects)

## What can be searched for

These are the main database entities one can search for:

- [Objects](../../../Components/Objects.md)
- [Accounts](../../../Components/Accounts.md)
- [Scripts](../../../Components/Scripts.md),
- [Channels](../../../Components/Channels.md) 
- [Messages](../../../Components/Msg.md)   (used by `page` command by default)
- [Help Entries](../../../Components/Help-System.md) (help entries created manually)

Most of the time you'll likely spend your time searching for Objects and the occasional Accounts.

Most search methods are available directly from `evennia`. But there are also a lot of useful search helpers found via `evennia.search`.

So to find an entity, what can be searched for?

### Search by key

The `key` is the name of the entity. Searching for this is always case-insensitive.

### Search by aliases

Objects and Accounts can have any number of aliases. When searching for `key` these will searched too, you can't easily search only for aliases. Let's add an alias to our rose with the default `alias` command:

    > alias rose = flower

Alternatively you can achieve the same thing manually (this is what the `alias` command does for you automatically):

    > py self.search("rose").aliases.add("flower")

If the above example `rose` has a `key` `"Rose"`, it can now also be found by searching for its alias `flower`.

    > py self.search("flower")
    Rose 

> All default commands uses the same search functionality, so you can now do `look flower` to look at the rose as well.

### Search by location

Only Objects (things inheriting from `evennia.DefaultObject`) has a `.location` property. 

The `Object.search` method will automatically limit its search by the object's location, so assuming you are in the same room as the rose, this will work:

    > py self.search("rose")
    Rose

Let's make another location and move to it - you will no longer find the rose:

    > tunnel n = kitchen
    north 
    > py self.search("rose")
    Could not find "rose"

However, using `search_object` will find the rose wherever it's located: 

     > py evennia.search_object("rose") 
     <QuerySet [Rose]> 

The `evennia.search_object` method doesn't have a `location` argument. What you do instead is to limit the search by setting its `candidates` keyword to the `.contents` of the current location. This is the same as a location search, since it will only accept matches among those in the room. In this example we'll (correctly) find the rose is not in the room.

    > py evennia.search_object("rose", candidate=here.contents)
    <QuerySet []>

In general, the `Object.search` is a shortcut for doing the very common searches of things in the same location, whereas the `search_object` finds objects anywhere.

### Search by Tags

Think of a [Tag](../../../Components/Tags.md) as the label the airport puts on your luggage when flying. Everyone going on the same plane gets a tag, grouping them together so the airport can know what should go to which plane. Entities in Evennia can be grouped in the same way. Any number of tags can be attached to each object.

Go back to the location of your `rose` and let's create a few more plants:

    > create/drop Daffodil
    > create/drop Tulip
    > create/drop Cactus

Then let's add the "thorny" and "flowers" tags as ways to group these based on if they are flowers and/or have thorns: 

    py self.search("rose").tags.add("flowers")
	py self.search("rose").tags.add("thorny")
    py self.search("daffodil").tags.add("flowers")
    py self.search("tulip").tags.add("flowers")
    py self.search("cactus").tags.add("flowers")
    py self.search("cactus").tags.add("thorny")	

You can now find all flowers using the `search_tag` function:

    py evennia.search_tag("flowers")
    <QuerySet [Rose, Daffodil, Tulip, Cactus]>
    py evennia.search_tag("thorny")
    <QuerySet [Rose, Cactus]>

Tags can also have categories. By default this category is `None` , which is considered a category of its own.  Here are some examples of using categories in plain Python code (you can also try this out with `py` if you want to create the objects first): 

    silmarillion.tags.add("fantasy", category="books")
    ice_and_fire.tags.add("fantasy", category="books")
    mona_lisa_overdrive.tags.add("cyberpunk", category="books")

Note that if you specify the tag  with a category, you _must_ also include its category when searching, otherwise the tag-category of `None` will be searched. 

    all_fantasy_books = evennia.search_tag("fantasy")  # no matches!
    all_fantasy_books = evennia.search_tag("fantasy", category="books")

Only the second line above returns the two fantasy books. 

    all_books = evennia.search_tag(category="books")

This gets all three books.

### Search by Attribute

We can also search by the [Attributes](../../../Components/Attributes.md) associated with entities.

For example, let's say our plants have a 'growth state' that updates as it grows: 

    > py self.search("rose").db.growth_state = "blooming"
    > py self.search("daffodil").db.growth_state = "withering"

Now we can find the things that have a given growth state:

    > py evennia.search_object("withering", attribute_name="growth_state")
    <QuerySet [Rose]> 

> Searching by Attribute can be very practical. But if you want to group entities or search very often, using Tags and search by Tags is faster and more resource-efficient.

### Search by Typeclass

Sometimes it's useful to limit your search by which Typeclass they have. 

Let's say you for example have two types of flower, `CursedFlower` and `BlessedFlower` defined under `mygame/typeclasses.flowers.py`. Each class contains custom code that grants curses and blessings respectively. You may have two `rose` objects, and the player doesn't know which one is the bad or the good one. To separate them in your search, you can make sure to get the right one like this (in Python code)

```python
cursed_roses = evennia.search_object("rose", typeclass="typeclasses.flowers.CursedFlower")
```

If you e.g. have the `BlessedRose` class already imported you can also pass it directly:

```python
from typeclasses.flowers import BlessedFlower
blessed_roses = evennia.search_object("rose", typeclass=BlessedFlower)
```

A common use case is finding _all_ items of a given typeclass, no matter what they are named. For this you don't use `search_object`, but search with the typeclass directly: 

```python
from typeclasses.objects.flowers import Rose
all_roses = Rose.objects.all()
```

This last way of searching is a simple form of a Django _query_. This is a way to express SQL queries using Python. See [the next lesson](./Beginner-Tutorial-Django-queries.md), where we'll explore this way to searching in more detail.

### Search by dbref

```{sidebar} Will I run out of dbrefs?

Since dbrefs are not reused, do you need to worry about your database ids 'running out' in the future? [No, and here's why](../../../Components/Typeclasses.md#will-i-run-out-of-dbrefs).
```
The database id or `#dbref` is unique and never-reused within each database table. In search methods you can replace the search for `key` with the dbref to search for. This must be written as a string `#dbref`:

    the_answer = self.caller.search("#42")
    eightball = evennia.search_object("#8")

Since `#dbref` is always unique, this search is always global.

```{warning} Relying on #dbrefs

In legacy code bases you may be used to relying a lot on #dbrefs to find and track things. Looking something up by #dbref can be practical - if used occationally. It is however considered **bad practice** to *rely* on hard-coded #dbrefs in Evennia. Especially to expect end users to know them. It makes your code fragile and hard to maintain, while tying your code to the exact layout of the database. In 99% of use cases you should organize your code such that you pass the actual objects around and search by key/tags/attribute instead.
```


## Summary

Knowing how to find things is important and the tools from this section will serve you well. These tools will cover most of your regular needs.

Not always though. If we go back to the example of a coin in a chest from before, you _could_ use the following to dynamically figure out if there are any chests in the room with coins inside:

```python 
from evennia import search_object

# we assume only one match of each 
dungeons = search_object("dungeon", typeclass="typeclasses.rooms.Room")
chests = search_object("chest", location=dungeons[0])
# find if there are any skulls in the chest 
coins = search_object("coin", candidates=chests[0].contents)
```

This would work but is both quite inefficient, fragile and a lot to type. This kind of thing is better done by directly querying the database.

In the next lesson we will dive further into more complex searching when we look at Django queries and querysets in earnest.