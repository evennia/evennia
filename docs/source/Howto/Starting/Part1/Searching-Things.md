# Searching for things

We have gone through how to create the various entities in Evennia. But creating something is of little use 
if we cannot find and use it afterwards. 

## Main search functions

The base tools are the `evennia.search_*` functions, such as `evennia.search_object`. 

        rose = evennia.search_object(key="rose")
        acct = evennia.search_account(key="MyAccountName", email="foo@bar.com")

```sidebar:: Querysets

    What is returned from the main search functions is actually a `queryset`. They can be 
    treated like lists except that they can't modified in-place. We'll discuss querysets in
    the `next lesson` <Django-queries>`_.
```

Strings are always case-insensitive, so searching for `"rose"`, `"Rose"` or `"rOsE"` give the same results.
It's important to remember that what is returned from these search methods is a _listing_ of 0, one or more 
elements - all the matches to your search. To get the first match: 

    rose = rose[0] 

Often you really want all matches to the search parameters you specify. In other situations, having zero or 
more than one match is a sign of a problem and you need to handle this case yourself. 

    the_one_ring = evennia.search_object(key="The one Ring")
    if not the_one_ring:
        # handle not finding the ring at all
    elif len(the_one_ring) > 1:
        # handle finding more than one ring
    else:
        # ok - exactly one ring found
        the_one_ring = the_one_ring[0]

There are equivalent search functions for all the main resources. You can find a listing of them 
[in the Search functions section](../../../Evennia-API) of the API frontpage. 

## Searching using Object.search

On the `DefaultObject` is a `.search` method which we have already tried out when we made Commands. For 
this to be used you must already have an object available: 

    rose = obj.search("rose")
    
The `.search` method wraps `evennia.search_object` and handles its output in various ways.

- By default it will always search for objects among those in `obj.location.contents` and `obj.contents` (that is,
things in obj's inventory or in the same room).
- It will always return exactly one match. If it found zero or more than one match, the return is `None`.
- On a no-match or multimatch, `.search` will automatically send an error message to `obj`.

So this method handles error messaging for you. A very common way to use it is in commands: 

```python
from evennia import Command

class MyCommand(Command):

    key = "findfoo"

    def func(self):

        foo = self.caller.search("foo")
        if not foo:
            return
```

Remember, `self.caller` is the one calling the command. This is usually a Character, which 
inherits from `DefaultObject`! This (rather stupid) Command searches for an object named "foo" in 
the same location. If it can't find it, `foo` will be `None`. The error has already been reported 
to `self.caller` so we just abort with `return`. 

You can use `.search` to find anything, not just stuff in the same room: 

    volcano = self.caller.search("Volcano", global=True)

If you only want to search for a specific list of things, you can do so too: 

    stone = self.caller.search("MyStone", candidates=[obj1, obj2, obj3, obj4])
    
This will only return a match if MyStone is one of the four provided candidate objects. This is quite powerful,
here's how you'd find something only in your inventory: 

    potion = self.caller.search("Healing potion", candidates=self.caller.contents)

You can also turn off the automatic error handling:

    swords = self.caller.search("Sword", quiet=True)

With `quiet=True` the user will not be notified on zero or multi-match errors. Instead you are expected to handle this 
yourself and what you get back is now a list of zero, one or more matches! 

## What can be searched for

These are the main database entities one can search for:

- [Objects](../../../Components/Objects)
- [Accounts](../../../Components/Accounts)
- [Scripts](../../../Components/Scripts),
- [Channels](../../../Components/Communications#channels), 
- [Messages](Communication#Msg) 
- [Help Entries](../../../Components/Help-System).

Most of the time you'll likely spend your time searching for Objects and the occasional Accounts.

So to find an entity, what can be searched for? 

### Search by key 

The `key` is the name of the entity. Searching for this is always case-insensitive.

### Search by aliases

Objects and Accounts can have any number of aliases. When searching for `key` these will searched too,
you can't easily search only for aliases.

    rose.aliases.add("flower")
    
If the above `rose` has a `key` `"Rose"`, it can now also be found by searching for `flower`. In-game 
you can assign new aliases to things with the `alias` command.

### Search by location
    
Only Objects (things inheriting from `evennia.DefaultObject`) has a location. This is usually a room. 
The `Object.search` method will automatically limit it search by location, but it also works for the
general search function. If we assume `room` is a particular Room instance, 

    chest = evennia.search_object("Treasure chest", location=room) 

### Search by Tags 

Think of a [Tag](../../../Components/Tags) as the label the airport puts on your luggage when flying. 
Everyone going on the same plane gets a tag grouping them together so the airport can know what should 
go to which plane. Entities in Evennia can be grouped in the same way. Any number of tags can be attached
to each object. 

    rose.tags.add("flowers")
    daffodil.tags.add("flowers")
    tulip.tags.add("flowers")
    
You can now find all flowers using the `search_tag` function:

    all_flowers = evennia.search_tag("flowers")

Tags can also have categories. By default this category is `None` which is also considered a category.

    silmarillion.tags.add("fantasy", category="books")
    ice_and_fire.tags.add("fantasy", category="books")
    mona_lisa_overdrive.tags.add("cyberpunk", category="books")
    
Note that if you specify the tag you _must_ also include its category, otherwise that category 
will be `None` and find no matches.

    all_fantasy_books = evennia.search_tag("fantasy")  # no matches! 
    all_fantasy_books = evennia.search_tag("fantasy", category="books") 
    
Only the second line above returns the two fantasy books. If we specify a category however,
we can get all tagged entities within that category: 

    all_books = evennia.search_tag(category="books")
 
This gets all three books. 
 
### Search by Attribute

We can also search by the [Attributes](../../../Components/Attributes) associated with entities. 

For example, let's give our rose thorns: 

    rose.db.has_thorns = True
    wines.db.has_thorns = True
    daffodil.db.has_thorns = False 
    
Now we can find things attribute and the value we want it to have: 
     
    is_ouch = evennia.search_object_attribute("has_thorns", True)

This returns the rose and the wines. 

> Searching by Attribute can be very practical. But if you plan to do a search very often, searching
> by-tag is generally faster. 


### Search by Typeclass

Sometimes it's useful to find all objects of a specific Typeclass. All of Evennia's search tools support this.

    all_roses = evennia.search_object(typeclass="typeclasses.flowers.Rose") 

If you have the `Rose` class already imported you can also pass it directly:

    all_roses = evennia.search_object(typeclass=Rose)
    
You can also search using the typeclass itself:

    all_roses = Rose.objects.all()
    
This last way of searching is a simple form of a Django _query_. This is a way to express SQL queries using 
Python. We'll cover this some more as an [Extra-credits](#Extra-Credits) section at the end of this lesson.
    
### Search by dbref 

The database id or `#dbref` is unique and never-reused within each database table. In search methods you can 
replace the search for `key` with the dbref to search for. This must be written as a string `#dbref`: 

    the_answer = self.caller.search("#42")
    eightball = evennia.search_object("#8") 

Since `#dbref` is always unique, this search is always global. 

```warning:: Relying on #dbrefs

    You may be used to using #dbrefs a lot from other codebases. It is however considered 
    `bad practice` in Evennia to rely on hard-coded #dbrefs. It makes your code hard to maintain
    and tied to the exact layout of the database. In 99% of cases you should pass the actual objects 
    around and search by key/tags/attribute instead. 
```

## Finding objects relative each other

Let's consider a `chest` with a `coin` inside it. The chests stand in a room `dungeon`. In the dungeon is also
a `door`. This is an exit leading outside. 

- `coin.location` is `chest`.
- `chest.location` is `dungeon`.
- `door.location` is `dungeon`.
- `room.location` is `None` since it's not inside something else. 

One can use this to find what is inside what. For example, `coin.location.location` is the `room`. 
We can also find what is inside each object. This is a list of things.

- `room.contents` is `[chest, door]`
- `chest.contents` is `[coin]`
- `coin.contents` is `[]`, the empty list since there's nothing 'inside' the coin.
- `door.contents` is `[]` too. 

A convenient helper is `.contents_get` - this allows to restrict what is returned: 

- `room.contents_get(exclude=chest)` - this returns everything in the room except the chest (maybe it's hidden?)

There is a special property for finding exits: 

- `room.exits` is `[door]` 
- `coin.exits` is `[]` (same for all the other objects)

There is a property `.destination` which is only used by exits:

- `door.destination` is `outside` (or wherever the door leads)
- `room.destination` is `None` (same for all the other non-exit objects)

## Summary 

Knowing how to find things is important and the tools from this section will serve you well. For most of your needs
these tools will be all you need ...

... but not always. In the next lesson we will dive further into more complex searching when we look at 
Django queries and querysets in earnest.

