# Advanced searching - Django Database queries

```{important} More advanced lesson!

Learning about Django's query language is very useful once you start doing more
advanced things in Evennia. But it's not strictly needed out the box and can be
a little overwhelming for a first reading. So if you are new to Python and
Evennia, feel free to just skim this lesson and refer back to it later when
you've gained more experience.
```

The search functions and methods we used in the previous lesson are enough for most cases.
But sometimes you need to be more specific:

- You want to find all `Characters` ...
- ... who are in Rooms tagged as `moonlit` ...
- ... _and_ who has the Attribute `lycantrophy` with a level higher than 2 ...
- ... because they should immediately transform to werewolves!

In principle you could achieve this with the existing search functions combined with a lot of loops
and if statements. But for something non-standard like this, querying the database directly will be
much more efficient.

Evennia uses [Django](https://www.djangoproject.com/) to handle its connection to the database.
A [django queryset](https://docs.djangoproject.com/en/3.0/ref/models/querysets/) represents a database query. One can add querysets together to build ever-more complicated queries. Only when you are trying to use the results of the queryset will it actually call the database.

The normal way to build a queryset is to define what class of entity you want to search by getting its `.objects` resource, and then call various methods on that. We've seen variants of this before: 

    all_weapons = Weapon.objects.all()

This is now a queryset representing all instances of `Weapon`. If `Weapon` had a subclass `Cannon` and we only wanted the cannons, we would do

    all_cannons = Cannon.objects.all()

Note that `Weapon` and `Cannon` are _different_ typeclasses. This means that you won't find any `Weapon`-typeclassed results in `all_cannons`. Vice-versa, you won't find any `Cannon`-typeclassed results in `all_weapons`. This may not be what you expect.

If you want to get all entities with typeclass `Weapon` _as well_ as all the subclasses of `Weapon`, such as `Cannon`, you need to use the `_family` type of query:

```{sidebar} _family

The `all_family` and `filter_family` (as well as `get_family` for getting exactly one result) are Evennia-specific. They are not part of regular Django.
```

    really_all_weapons = Weapon.objects.all_family()

This result now contains both `Weapon` and `Cannon` instances (and any other
entities whose typeclasses inherit at any distance from `Weapon`, like `Musket` or
`Sword`).

To limit your search by other criteria than the Typeclass you need to use `.filter`
(or `.filter_family`) instead:

    roses = Flower.objects.filter(db_key="rose")

This is a queryset representing all flowers having a `db_key` equal to `"rose"`.
Since this is a queryset you can keep adding to it; this will act as an `AND` condition.

    local_roses = roses.filter(db_location=myroom)

We could also have written this in one statement:

    local_roses = Flower.objects.filter(db_key="rose", db_location=myroom)

We can also `.exclude` something from results

    local_non_red_roses = local_roses.exclude(db_key="red_rose")

It's important to note that we haven't called the database yet! Not until we
actually try to examine the result will the database be called. Here the
database is called when we try to loop over it (because now we need to actually
get results out of it to be able to loop):

    for rose in local_non_red_roses:
        print(rose)

From now on, the queryset is _evaluated_ and we can't keep adding more queries to it - we'd need to create a new queryset if we wanted to find some other result. Other ways to evaluate the queryset is to print it, convert it to a list with `list()` and otherwise try to access its results.

```{sidebar} database fields
Each database table have only a few fields. For `DefaultObject`, the most common ones are `db_key`, `db_location` and `db_destination`. When accessing them they are normally accessed just as `obj.key`, `obj.location` and `obj.destination`.  You only need to remember the `db_` when using them in database queries. The object description, `obj.db.desc` is not such a hard-coded field, but one of many
Attributes attached to the Object.
```
Note how we use `db_key` and `db_location`. This is the actual names of these database fields. By convention Evennia uses `db_` in front of every database field. When you use the normal Evennia search helpers and objects you can skip the `db_` but here we are calling the database directly and need to use the 'real' names.


Here are the most commonly used methods to use with the `objects` managers:

- `filter` - query for a listing of objects based on search criteria. Gives empty queryset if none
were found.
- `get` - query for a single match - raises exception if none were found, or more than one was
found.
- `all` - get all instances of the particular type.
- `filter_family` - like `filter`, but search all subclasses as well.
- `get_family` - like `get`, but search all subclasses as well.
- `all_family` - like `all`, but return entities of all subclasses as well.

> All of Evennia search functions use querysets under the hood. The `evennia.search_*` functions actually return querysets (we have just been treating them as lists so far). This means you could in principle add a `.filter` query to the result of `evennia.search_object` to further refine the search.


## Queryset field lookups

Above we found roses with exactly the `db_key` `"rose"`. This is an _exact_ match that is _case sensitive_,
so it would not find `"Rose"`.

```python
# this is case-sensitive and the same as =
roses = Flower.objects.filter(db_key__exact="rose"

# the i means it's case-insensitive
roses = Flower.objects.filter(db_key__iexact="rose")
```
The Django field query language uses `__` similarly to how Python uses `.` to access resources. This
is because `.` is not allowed in a function keyword.

```python
roses = Flower.objects.filter(db_key__icontains="rose")
```

This will find all flowers whose name contains the string `"rose"`, like `"roses"`, `"wild rose"` etc. The `i` in the beginning makes the search case-insensitive. Other useful variations to use
are `__istartswith` and `__iendswith`. You can also use `__gt`, `__ge` for "greater-than"/"greater-or-equal-than" comparisons (same for `__lt` and `__le`). There is also `__in`:

```python
swords = Weapons.objects.filter(db_key__in=("rapier", "two-hander", "shortsword"))
```

One also uses `__` to access foreign objects like Tags. Let's for example assume
this is how we have identified mages:

```python
char.tags.add("mage", category="profession")
```

Now, in this case we already have an Evennia helper to do this search:

```python
mages = evennia.search_tags("mage", category="profession")
```

Here is what it would look as a query if you were only looking for Vampire mages:

```{sidebar} Breaking lines of code
In Python you can wrap code in `(...)` to break it over multiple lines. Doing this doesn't affect functionality, but can make it easier to read.
```

```python
sparkly_mages = (
	Vampire.objects.filter(									   
           db_tags__db_key="mage", 
           db_tags__db_category="profession")
    )
```

This looks at the `db_tags` field on the `Vampire` and filters on the values of each tag's
`db_key` and `db_category` together.

For more field lookups, see the [django docs](https://docs.djangoproject.com/en/3.0/ref/models/querysets/#field-lookups) on the subject.

## Let's get that werewolf ...

Let's see if we can make a query for the werewolves in the moonlight we mentioned at the beginning
of this lesson.

Firstly, we make ourselves and our current location match the criteria, so we can test:

    > py here.tags.add("moonlit")
    > py me.db.lycantrophy = 3

This is an example of a more complex query. We'll consider it an example of what is
possible.

```{code-block} python
:linenos:
:emphasize-lines: 4,6,7,8

from typeclasses.characters import Character

will_transform = (
    Character.objects
    .filter(
        db_location__db_tags__db_key__iexact="moonlit",
        db_attributes__db_key="lycantrophy",
        db_attributes__db_value__gt=2
    )
)
```

```{sidebar} Attributes vs database fields
Don't confuse database fields with [Attributes](../../../Components/Attributes.md) you set via `obj.db.attr = 'foo'` or `obj.attributes.add()`. Attributes are custom database entities *linked* to an object. They are not separate fields *on* that object like `db_key` or `db_location` are.
```
- **Line 4** We want to find `Character`s, so we access `.objects` on the `Character` typeclass.
- We start to filter ...
    - **Line 6**: ... by accessing the `db_location` field (usually this is a Room)
	    - ... and on that location, we get the value of `db_tags` (this is a _many-to-many_ database field
        that we can treat like an object for this purpose; it references all Tags on the location)
	    - ... and from those `Tags`, we looking for `Tags` whose `db_key` is "monlit" (non-case sensitive).
     - **Line 7**: ... We also want only Characters with `Attributes` whose `db_key` is exactly `"lycantrophy"`
    - **Line 8** :... at the same time as the `Attribute`'s `db_value` is greater-than 2.

Running this query makes our newly lycantrophic Character appear in `will_transform` so we
know to transform it. Success!

## Queries with OR or NOT 

All examples so far used `AND` relations. The arguments to `.filter` are added together with `AND`
("we want tag room to be "monlit" _and_ lycantrhopy be > 2").

For queries using `OR` and `NOT` we need Django's [Q object](https://docs.djangoproject.com/en/1.11/topics/db/queries/#complex-lookups-with-q-objects). It is imported from Django directly:

    from django.db.models import Q

The `Q` is an object that is created with the same arguments as `.filter`, for example

    Q(db_key="foo")

You can then use this `Q` instance as argument in a `filter`:

    q1 = Q(db_key="foo")
    Character.objects.filter(q1)
	# this is the same as 
	Character.objects.filter(db_key="foo")

The useful thing about `Q` is that these objects can be chained together with special symbols (bit operators): `|` for `OR` and `&` for `AND`. A tilde `~` in front negates the expression inside the `Q` and thus
works like `NOT`.

    q1 = Q(db_key="Dalton")
    q2 = Q(db_location=prison)
    Character.objects.filter(q1 | ~q2)

Would get all Characters that are either named "Dalton" _or_ which is _not_ in prison. The result is a mix
of Daltons and non-prisoners.

Let us expand our original werewolf query. Not only do we want to find all Characters in a moonlit room with a certain level of `lycanthrophy` - we decide that if they have been _newly bitten_, they should also turn, _regardless_ of their lycantrophy level (more dramatic that way!).

Let's say that getting bitten means that you'll get assigned a Tag `recently_bitten`.

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
          | Q(db_tags__db_key__iexact="recently_bitten")
        ))
    .distinct()
)
```

That's quite compact. It may be easier to see what's going on if written this way:

```python
from django.db.models import Q

q_moonlit = Q(db_location__db_tags__db_key__iexact="moonlit")
q_lycantropic = Q(db_attributes__db_key="lycantrophy", db_attributes__db_value__gt=2)
q_recently_bitten = Q(db_tags__db_key__iexact="recently_bitten")

will_transform = (
    Character.objects
    .filter(q_moonlit & (q_lycantropic | q_recently_bitten))
    .distinct()
)
```

```{sidebar} SQL

These Python structures are internally converted to SQL, the native language of
the database.  If you are familiar with SQL, these are many-to-many tables
joined with `LEFT OUTER JOIN`, which may lead to multiple merged rows combining
the same object with different relations.

```

This reads as "Find all Characters in a moonlit room that either has the
Attribute `lycantrophy` higher than two, _or_ which has the Tag
`recently_bitten`". With an OR-query like this it's possible to find the same
Character via different paths, so we add `.distinct()` at the end. This makes
sure that there is only one instance of each Character in the result.

## Annotations

What if we wanted to filter on some condition that isn't represented easily by a
field on the object? An example would wanting to find rooms only containing _five or more objects_.

We *could* do it like this (don't actually do it this way!):

```python
from typeclasses.rooms import Room

  all_rooms = Rooms.objects.all()

  rooms_with_five_objects = []
  for room in all_rooms:
      if len(room.contents) >= 5:
          rooms_with_five_objects.append(room)
```

```{sidebar} list.append, extend and .pop

Use `mylist.append(obj)` to add new items to a list. Use `mylist.extend(another_list))` or `list1 + list2` to merge two lists together. Use `mylist.pop()` to remove an item from the end or `.pop(0)` to remove from the beginning of the list. Remember all indices start from `0` in Python.
```

Above we get _all_ rooms and then use `list.append()` to keep adding the right
rooms to an ever-growing list. This is _not_ a good idea, once your database
grows this will be unnecessarily compute-intensive. It's much better to query the 
database directly

_Annotations_ allow you to set a 'variable' inside the query that you can then
access from other parts of the query. Let's do the same example as before
directly in the database:

```{code-block} python
:linenos:
:emphasize-lines: 6,8

from typeclasses.rooms import Room
from django.db.models import Count

rooms = (
    Room.objects
    .annotate(
        num_objects=Count('locations_set'))
    .filter(num_objects__gte=5)
)
```

```{sidebar} locations_set
Note the use of `locations_set` in that `Count`. The `*s_set` is a back-reference automatically created by Django. In this case it allows you to find all objects that *has the current object as location*.
```

`Count` is a Django class for counting the number of things in the database.

- **Line 6-7**: Here we first create an annotation `num_objects` of type `Count`. It creates an in-database function that will count the number of results inside the database. The fact annotation means that now `num_objects` is avaiable to be used in other parts of the query.
- **Line 8** We filter on this annotation, using the name `num_objects` as something we
can filter for. We use `num_objects__gte=5` which means that `num_objects`
should be greater than or equal to 5. 

Annotations can be a little harder to get one's head around but much more efficient than lopping over all objects in Python.

## F-objects

What if we wanted to compare two dynamic parameters against one another in a
query? For example, what if instead of having 5 or more objects, we only wanted
objects that had a bigger inventory than they had tags (silly example, but ...)?

This can be with Django's [F objects](https://docs.djangoproject.com/en/4.1/ref/models/expressions/#f-expressions). So-called F expressions allow you to do a query that looks at a value of each object in the database.

```python
from django.db.models import Count, F
from typeclasses.rooms import Room

result = (
    Room.objects
    .annotate(
        num_objects=Count('locations_set'),
        num_tags=Count('db_tags'))
    .filter(num_objects__gt=F('num_tags'))
)
```

Here we used `.annotate` to create two in-query 'variables' `num_objects` and `num_tags`. We then
directly use these results in the filter. Using `F()` allows for also the right-hand-side of the filter
condition to be calculated on the fly, completely within the database.

## Grouping and returning only certain properties

Suppose you used tags to mark someone belonging to an organization. Now you want to make a list and need to get the membership count of every organization all at once.

The `.annotate`, `.values_list`, and `.order_by` queryset methods are useful for this. Normally when you run a `.filter`, what you get back is a bunch of full typeclass instances, like roses or swords. Using `.values_list` you can instead choose to only get back certain properties on objects. The `.order_by` method finally allows for sorting the results according to some criterion:


```{code-block} python 
:linenos:
:emphasize-lines: 6,7,8,9 

from django.db.models import Count
from typeclasses.rooms import Room

result = (
    Character.objects
    .filter(db_tags__db_category="organization")
    .annotate(tagcount=Count('id'))
    .order_by('-tagcount'))
    .values_list('db_tags__db_key', "tagcount")
```

Here we fetch all Characters who ...
- **Line 6**: ... has a tag of category "organization" on them
- **Line 7**:... along the way we count how many different Characters (each `id` is unique) we find  for each organization and store it in a 'variable' `tagcount` using `.annotate` and `Count`
- **Line 8**: ... we use this count to sort the result in descending order of `tagcount` (descending because there is a minus sign, default is increasing order but we want the most popular organization to be first).
- **Line 9**:  ... and finally we make sure to only return exactly the properties we want, namely the name of the organization tag and how many matches we found for that organization. For this we use the `values_list` method on the queryset. This will evaluate the queryset immediately.

The result will be a list of tuples ordered in descending order by the number of matches,
in a format like the following:
```
[
 ('Griatch's poets society', 3872),
 ("Chainsol's Ainneve Testers", 2076),
 ("Blaufeuer's Whitespace Fixers", 1903),
 ("Volund's Bikeshed Design Crew", 1764),
 ("Tehom's Glorious Misanthropes", 1763)
]
```

## Conclusions

We have covered a lot of ground in this lesson and covered several more complex topics. Knowing how to query using Django is a powerful skill to have. 

This concludes the first part of the Evennia starting tutorial - "What we have".
Now we have a good foundation to understand how to plan what our tutorial game
will be about.