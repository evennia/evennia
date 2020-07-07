# Searching for things

[prev lesson](Creating-Things) | [next lesson]()

We have gone through how to create the various entities in Evennia. But creating something is of little use 
if we cannot find and use it afterwards. 

## Main search functions

The base tools are the `evennia.search_*` functions, such as `evennia.search_object`. 

        rose = evennia.search_object(key="rose")
        acct = evennia.search_account(key="MyAccountName", email="foo@bar.com")

```sidebar:: Querysets

    What is returned from the main search functions is actually a `queryset`. They can be 
    treated like lists except that they can't modified in-place. We'll discuss querysets at 
    the end of this lesson.
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

    swords = self.search("Sword", quiet=True)

With `quiet=True` the user will not be notified on zero or multi-match errors. Instead you are expected to handle this 
yourself and what you get back is now a list of zero, one or more matches! 

## What can be searched for

These are the main database entities one can search for:

- [Objects](../../../Component/Objects)
- [Accounts](../../../Component/Accounts)
- [Scripts](../../../Component/Scripts),
- [Channels](../../../Component/Communications#channels), 
- [Messages](Communication#Msg) 
- [Help Entries](../../../Component/Help-System).

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

Think of a [Tag](../../../Component/Tags) as the label the airport puts on your luggage when flying. 
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

We can also search by the [Attributes](../../../Component/Attributes) associated with entities. 

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

## Database queries

The search functions and methods above are enough for most cases. But sometimes you need to be 
more specific: 

- You want to find all `Characters` ...
- ... who are in Rooms tagged as `moonlit` ... 
- ... _and_ who has the Attribute `lycantrophy` with a level higher than 2 ...
- ... because they'll immediately become werewolves! 

In principle you could achieve this with the existing search functions combined with a lot of loops 
and if statements. But for something non-standard like this querying the database directly will be 
more efficient.

A [django queryset](https://docs.djangoproject.com/en/3.0/ref/models/querysets/) represents 
a database query. One can add querysets together to build ever-more complicated queries. Only when 
you are trying to use the results of the queryset will it actually call the database. 

The normal way to build a queryset is to define what class of entity you want to search by getting its 
`.objects` resource, and then call various methods on that. We've seen this one before: 

    all_weapons = Weapon.objects.all()
    
This is now a queryset representing all instances of `Weapon`. If `Weapon` had a subclass `Cannon` and we 
only wanted the cannons, we would do

    all_cannons = Cannon.objects.all()

Note that `Weapon` and `Cannon` are different typeclasses. You won't find any `Cannon` instances in 
the `all_weapon` result above, confusing as that may sound. To get instances of a Typeclass _and_ the 
instances of all its children classes you need to use `_family`:

```sidebar:: _family

    The all_family, filter_family etc is an Evennia-specific 
    thing. It's not part of regular Django.

```

    really_all_weapons = Weapon.objects.all_family()
    
This result now contains both `Weapon` and `Cannon` instances. 

To actually limit your search by other criteria than the Typeclass you need to use `.filter` 
(or `.filter_family`) instead: 

    roses = Flower.objects.filter(db_key="rose")
    
This is a queryset representing all objects having a `db_key` equal to `"rose"`. 
Since this is a queryset you can keep adding to it: 

    local_roses = roses.filter(db_location=myroom)
    
We could also have written this in one statement: 

    local_roses = Flower.objects.filter(db_key="rose", db_location=myroom)
    
We can also `.exclude` something from results

    local_non_red_roses = local_roses.exclude(db_key="red_rose")
    
Only until we actually try to examine the result will the database be called. Here it's called when we 
try to loop over the queryset: 

    for rose in local_non_red_roses:
        print(rose)
    
From now on, the queryset is _evaluated_ and we can't keep adding more queries to it - we'd need to 
create a new queryset if we wanted to find some other result. 
    
Note how we use `db_key` and `db_location`. This is the actual names of these database fields. By convention
Evennia uses `db_` in front of every database field, but when you access it in Python you can skip the `db_`. This
is why you can use `obj.key` and `obj.location` in normal code. Here we are calling the database directly though
and need to use the 'real' names. 

Here are the most commonly used methods to use with the `objects` managers: 

- `filter` - query for a listing of objects based on search criteria. Gives empty queryset if none
were found.
- `get` - query for a single match - raises exception if none were found, or more than one was
found.
- `all` - get all instances of the particular type.
- `filter_family` - like `filter`, but search all sub classes as well.
- `get_family` - like `get`, but search all sub classes as well.
- `all_family` - like `all`, but return entities of all subclasses as well. 

> All of Evennia search functions use querysets under the hood. The `evennia.search_*` functions actually 
> return querysets, which means you could in principle keep adding queries to their results as well.


### Queryset field lookups

Above we found roses with exactly the `db_key` `"rose"`. This is an _exact_ match that is _case sensitive_, 
so it would not find `"Rose"`. 

    # this is case-sensitive and the same as =
    roses = Flower.objects.filter(db_key__exact="rose"
    # the i means it's case-insensitive
    roses = Flower.objects.filter(db_key__iequals="rose")
    
The Django field query language uses `__` in the same way as Python uses `.` to access resources. This 
is because `.` is not allowed in a function keyword. 

    roses = Flower.objects.filter(db_key__icontains="rose")
    
This will find all flowers whose name contains the string `"rose"`, like `"roses"`, `"wild rose"` etc. The 
`i` in the beginning makes the search case-insensitive. Other useful variations to use 
are `__istartswith` and `__iendswith`. You can also use `__gt`, `__ge` for "greater-than"/"greater-or-equal-than" 
comparisons (same for `__lt` and `__le`). There is also `__in`:

    swords = Weapons.objects.filter(db_key__in=("rapier", "two-hander", "shortsword"))
    
For more field lookups, see the 
[django docs](https://docs.djangoproject.com/en/3.0/ref/models/querysets/#field-lookups) on the subject.

### Get that werewolf ...

Let's see if we can make a query for the werewolves in the moonlight we mentioned at the beginning 
of this section. 

Firstly, we make ourselves and our current location match the criteria, so we can test: 

    > py here.tags.add("moonlit")
    > py me.db.lycantrophy = 3
    
This is an example of a more complex query. We'll consider it an example of what is 
possible.

```sidebar:: Line breaks

    Note the way of writing this code. It would have been very hard to read if we just wrote it in 
    one long line. But since we wrapped it in `(...)` we can spread it out over multiple lines
    without worrying about line breaks! 
```

```python
from typeclasses.characters import Character

will_transform = (
    Character.objects
    .filter(
        db_location__db_tags__db_key__iexact="moonlit",
        db_attributes__db_key="lycantrophy",
        db_attributes__db_value__gt=2)
)
```

- **Line 3** - We want to find `Character`s, so we access `.objects` on the `Character` typeclass.
- **Line 4** - We start to filter ...
- **Line 5** 
    - ... by accessing the `db_location` field (usually this is a Room)
    - ... and on that location, we get the value of `db_tags` (this is a _many-to-many_ database field
        that we can treat like an object for this purpose; it references all Tags on the location) 
    - ... and from those `Tags`, we looking for `Tags` whose `db_key` is "monlit" (non-case sensitive).
- **Line 6** - ... We also want only Characters with `Attributes` whose `db_key` is exactly `"lycantrophy"`
- **Line 7** - ... at the same time as the `Attribute`'s `db_value` is greater-than 2. 
        
Running this query makes our newly lycantrrophic Character appear in `will_transform`. Success! 

> Don't confuse database fields with [Attributes](../../../Component/Attributes) you set via `obj.db.attr = 'foo'` or
`obj.attributes.add()`. Attributes are custom database entities *linked* to an object. They are not
separate fields *on* that object like `db_key` or `db_location` are. 

### Complex queries

All examples so far used `AND` relations. The arguments to `.filter` are added together with `AND`
("we want tag room to be "monlit" _and_ lycantrhopy be > 2").

For queries using `OR` and `NOT` we need Django's 
[Q object](https://docs.djangoproject.com/en/1.11/topics/db/queries/#complex-lookups-with-q-objects). It is 
import from Django directly: 

    from django.db.models import Q 

`Q()` objects take the same arguments like `.filter`: 

    Q(db_key="foo")

The special thing is that these `Q` objects can then be chained together with special symbols: 
`|` for `OR`, `&` for `AND`. A tilde `~` in front negates the expression inside the `Q` and thus works like `NOT`. 

Let us expand our original werewolf query. Not only do we want to find all Characters in a moonlit room
with a certain level of `lycanthrophy`. Now we also want the full moon to immediately transform people who were 
recently bitten, even if their `lycantrophy` level is not yet high enough (more dramatic this way!). Let's say there is
a Tag "recently_bitten" that controls this.

This is how we'd change our query: 

```python
from django.db.models import Q 

will_transform = (

    Character.objects
    .filter(
        Q(db_location__db_tags__db_key__iexact="moonlit")
        & (
          Q(db_attributes__db_key="lycantrophy",
            db_attributes__db_value__gt=2)
          | Q(db__tags__db__key__iexact="recently_bitten")
        )
    )
)
```

We now grouped the filter

In our original Lycanthrope example we wanted our werewolves to have names that could start with any
vowel except for the specific beginning "ab".

```python
from django.db.models import Q
from typeclasses.characters import Character

query = Q()
for letter in ("aeiouy"):
    query |= Q(db_key__istartswith=letter)
query &= ~Q(db_key__istartswith="ab")
query = Character.objects.filter(query)

list_of_lycanthropes = list(query)      
```

In the above example, we construct our query our of several Q objects that each represent one part
of the query. We iterate over the list of vowels, and add an `OR` condition to the query using `|=`
(this is the same idea as using `+=` which may be more familiar). Each `OR` condition checks that
the name starts with one of the valid vowels. Afterwards, we add (using `&=`) an `AND` condition
that is negated with the `~` symbol. In other words we require that any match should *not* start
with the string "ab". Note that we don't actually hit the database until we convert the query to a
list at the end (we didn't need to do that either, but could just have kept the query until we
needed to do something with the matches).

### Annotations and `F` objects

What if we wanted to filter on some condition that isn't represented easily by a field on the
object? Maybe we want to find rooms only containing five or more objects?

We *could* retrieve all interesting candidates and run them through a for-loop to get and count
their `.content` properties. We'd then just return a list of only those objects with enough
contents. It would look something like this (note: don't actually do this!):

```python
# probably not a good idea to do it this way

from typeclasses.rooms import Room

queryset = Room.objects.all()  # get all Rooms
rooms = [room for room in queryset if len(room.contents) >= 5]

```

Once the number of rooms in your game increases, this could become quite expensive. Additionally, in
some particular contexts, like when using the web features of Evennia, you must have the result as a
queryset in order to use it in operations, such as in Django's admin interface when creating list
filters.

Enter [F objects](https://docs.djangoproject.com/en/1.11/ref/models/expressions/#f-expressions) and
*annotations*. So-called F expressions allow you to do a query that looks at a value of each object
in the database, while annotations allow you to calculate and attach a value to a query. So, let's
do the same example as before directly in the database:

```python
from typeclasses.rooms import Room
from django.db.models import Count

room_count = Room.objects.annotate(num_objects=Count('locations_set'))
queryset = room_count.filter(num_objects__gte=5)

rooms = (Room.objects.annotate(num_objects=Count('locations_set'))
                     .filter(num_objects__gte=5))

rooms = list(rooms)

```
Here we first create an annotation `num_objects` of type `Count`, which is a Django class. Note that
use of `location_set` in that `Count`. The `*_set` is a back-reference automatically created by
Django. In this case it allows you to find all objects that *has the current object as location*.
Once we have those, they are counted.
Next we filter on this annotation, using the name `num_objects` as something we can filter for. We
use `num_objects__gte=5` which means that `num_objects` should be greater than 5. This is a little
harder to get one's head around but much more efficient than lopping over all objects in Python.

What if we wanted to compare two parameters against one another in a query? For example, what if
instead of having 5 or more objects, we only wanted objects that had a bigger inventory than they
had tags? Here an F-object comes in handy:

```python
from django.db.models import Count, F
from typeclasses.rooms import Room

result = (Room.objects.annotate(num_objects=Count('locations_set'), 
                                num_tags=Count('db_tags'))
                      .filter(num_objects__gt=F('num_tags')))
```

F-objects allows for wrapping an annotated structure on the right-hand-side of the expression. It
will be evaluated on-the-fly as needed.

### Grouping By and Values

Suppose you used tags to mark someone belonging an organization. Now you want to make a list and
need to get the membership count of every organization all at once. That's where annotations and the
`.values_list` queryset method come in. Values/Values Lists are an alternate way of returning a
queryset - instead of objects, you get a list of dicts or tuples that hold selected properties from
the the matches. It also allows you a way to 'group up' queries for returning information. For
example, to get a display about each tag per Character and the names of the tag:

```python
result = (Character.objects.filter(db_tags__db_category="organization")
                           .values_list('db_tags__db_key')
                           .annotate(cnt=Count('id'))
                           .order_by('-cnt'))
```
The result queryset will be a list of tuples ordered in descending order by the number of matches,
in a format like the following:
```
[('Griatch Fanclub', 3872), ("Chainsol's Ainneve Testers", 2076), ("Blaufeuer's Whitespace Fixers",
1903),
 ("Volund's Bikeshed Design Crew", 1764), ("Tehom's Misanthropes", 1)]

[prev lesson](Creating-Things) | [next lesson]()
