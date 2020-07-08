## Django Database queries

[prev lesson](Searching-Things) | [next lesson]()

```important:: More advanced lesson!
  
    Learning about Django's queryset language is very useful once you start doing more advanced things 
    in Evennia. But it's not strictly needed out the box and can be a little overwhelming for a first 
    reading. So if you are new to Python and Evennia, feel free to just skim this lesson and refer 
    back to it later when you've gained more experience.
```

The search functions and methods we used in the previous lesson are enough for most cases. 
But sometimes you need to be more specific: 

- You want to find all `Characters` ...
- ... who are in Rooms tagged as `moonlit` ... 
- ... _and_ who has the Attribute `lycantrophy` with a level higher than 2 ...
- ... because they'll should immediately transform to werewolves! 

In principle you could achieve this with the existing search functions combined with a lot of loops 
and if statements. But for something non-standard like this, querying the database directly will be 
much more efficient.

Evennia uses [Django](https://www.djangoproject.com/) to handle its connection to the database.
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

To  limit your search by other criteria than the Typeclass you need to use `.filter` 
(or `.filter_family`) instead: 

    roses = Flower.objects.filter(db_key="rose")
    
This is a queryset representing all objects having a `db_key` equal to `"rose"`. 
Since this is a queryset you can keep adding to it; this will act as an `AND` condition.

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
create a new queryset if we wanted to find some other result. Other ways to evaluate the queryset is to
print it, convert it to a list with `list()` and otherwise try to access its results.
    
Note how we use `db_key` and `db_location`. This is the actual names of these database fields. By convention
Evennia uses `db_` in front of every database field. When you use the normal Evennia search helpers and objects
you can skip the `db_` but here we are calling the database directly and need to use the 'real' names. 

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
    roses = Flower.objects.filter(db_key__iexact="rose")
    
The Django field query language uses `__` in the same way as Python uses `.` to access resources. This 
is because `.` is not allowed in a function keyword. 

    roses = Flower.objects.filter(db_key__icontains="rose")
    
This will find all flowers whose name contains the string `"rose"`, like `"roses"`, `"wild rose"` etc. The 
`i` in the beginning makes the search case-insensitive. Other useful variations to use 
are `__istartswith` and `__iendswith`. You can also use `__gt`, `__ge` for "greater-than"/"greater-or-equal-than" 
comparisons (same for `__lt` and `__le`). There is also `__in`:

    swords = Weapons.objects.filter(db_key__in=("rapier", "two-hander", "shortsword"))
    
One also uses `__` to access foreign objects like Tags. Let's for example assume this is how we identify mages:

    char.tags.add("mage", category="profession")

Now, in this case we have an Evennia helper to do this search: 

    mages = evennia.search_tags("mage", category="profession")

But this will find all Objects with this tag+category. Maybe you are only looking for Vampire mages:

    sparkly_mages = Vampire.objects.filter(db_tags__db_key="mage", db_tags__db_category="profession")
    
This looks at the `db_tags` field on the `Vampire` and filters on the values of each tag's 
`db_key` and `db_category` together.
    
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
imported from Django directly: 

    from django.db.models import Q 

The `Q` is an object that is created with the same arguments as `.filter`, for example

    Q(db_key="foo")

You can then use this `Q` instance as argument in a `filter`:

    q1 = Q(db_key="foo")
    Character.objects.filter(q1)
    

The useful thing about `Q` is that these objects can be chained together with special symbols (bit operators): 
`|` for `OR` and `&` for `AND`. A tilde `~` in front negates the expression inside the `Q` and thus 
works like `NOT`. 

    q1 = Q(db_key="Dalton")
    q2 = Q(db_location=prison)
    Character.objects.filter(q1 | ~q2)
    
Would get all Characters that are either named "Dalton" _or_ which is _not_ in prison. The result is a mix
of Daltons and non-prisoners. 

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

```sidebar:: SQL 

    These Python structures are internally converted to SQL, the native language of the database.
    If you are familiar with SQL, these are many-to-many tables joined with `LEFT OUTER JOIN`,
    which may lead to multiple merged rows combining the same object with different relations.

```

This reads as "Find all Characters in a moonlit room that either has the Attribute `lycantrophy` higher
than two _or_ which has the Tag `recently_bitten`". With an OR-query like this it's possible to find the 
same Character via different paths, so we add `.distinct()` at the end. This makes sure that there is only 
one instance of each Character in the result.

### Annotations

What if we wanted to filter on some condition that isn't represented easily by a field on the
object? Maybe we want to find rooms only containing five or more objects?

We *could* do it like this (don't actually do it this way!): 

```python
    from typeclasses.rooms import Room

      all_rooms = Rooms.objects.all()  

      rooms_with_five_objects = []
      for room in all_rooms: 
          if len(room.contents) >= 5:
              rooms_with_five_objects.append(room)
```

Above we get all rooms and then use `list.append()` to keep adding the right rooms 
to an ever-growing list. This is _not_ a good idea, once your database grows this will 
be unnecessarily computing-intensive. The database is much more suitable for this. 

_Annotations_ allow you to set a 'variable' inside the query that you can
then access from other parts of the query. Let's do the same example as before directly in the database:

```python
from typeclasses.rooms import Room
from django.db.models import Count

rooms = (
    Room.objects
    .annotate(
        num_objects=Count('locations_set'))
    .filter(num_objects__gte=5)
)
```

`Count` is a Django class for counting the number of things in the database. 

Here we first create an annotation `num_objects` of type `Count`. It creates an in-database function
that will count the number of results inside the database. 

> Note the use of `location_set` in that `Count`. The `*_set` is a back-reference automatically created by
Django. In this case it allows you to find all objects that *has the current object as location*.

Next we filter on this annotation, using the name `num_objects` as something we can filter for. We
use `num_objects__gte=5` which means that `num_objects` should be greater than 5. This is a little
harder to get one's head around but much more efficient than lopping over all objects in Python.

### F-objects

What if we wanted to compare two dynamic parameters against one another in a query? For example, what if
instead of having 5 or more objects, we only wanted objects that had a bigger inventory than they had 
tags (silly example, but ...)? This can be with Django's 
[F objects](https://docs.djangoproject.com/en/1.11/ref/models/expressions/#f-expressions).
So-called F expressions allow you to do a query that looks at a value of each object in the database. 

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

### Grouping and returning only certain properties

Suppose you used tags to mark someone belonging to an organization. Now you want to make a list and
need to get the membership count of every organization all at once. 

The `.annotate`, `.values_list`, and `.order_by` queryset methods are useful for this. Normally when 
you run a `.filter`, what you get back is a bunch of full typeclass instances, like roses or swords. 
Using `.values_list` you can instead choose to only get back certain properties on objects. 
The `.order_by` method finally allows for sorting the results according to some criterion:


```python
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
- ... has a tag of category "organization" on them
- ... along the way we count how many different Characters (each `id` is unique) we find  for each organization
  and store it in a 'variable' `tagcount` using `.annotate` and `Count`
- ... we use this count to sort the result in descending order of `tagcount` (descending because there is a minus sign,
  default is increasing order but we want the most popular organization to be first). 
- ... and finally we make sure to only return exactly the properties we want, namely the name of the organization tag
and how many matches we found for that organization.

The result queryset will be a list of tuples ordered in descending order by the number of matches,
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

# Conclusions 

We have covered a lot of ground in this lesson and covered several more complex topics. Knowing how to 
query using Django is a powerful skill to have. 

This concludes the first part of the Evennia starting tutorial - "What we have". Now we have a good foundation
to understand how to plan what our tutorial game will be about.


[prev lesson](Searching-Things) | [next lesson]()
