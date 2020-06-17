# Tutorial Searching For Objects


You will often want to operate on a specific object in the database. For example when a player
attacks a named target you'll need to find that target so it can be attacked. Or when a rain storm
draws in you need to find all outdoor-rooms so you can show it raining in them. This tutorial
explains Evennia's tools for searching.

## Things to search for

The first thing to consider is the base type of the thing you are searching for. Evennia organizes
its database into a few main tables: [Objects](Component/Objects), [Accounts](Component/Accounts), [Scripts](Component/Scripts),
[Channels](Component/Communications#channels), [Messages](Communication#Msg) and [Help Entries](Component/Help-System).
Most of the time you'll likely spend your time searching for Objects and the occasional Accounts.

So to find an entity, what can be searched for? 

 - The `key` is the name of the entity. While you can get this from `obj.key` the *database field*
is actually named `obj.db_key` - this is useful to know only when you do [direct database
queries](Tutorial-Searching-For-Objects#queries-in-django). The one exception is `Accounts`, where
the database field for `.key` is instead named `username` (this is a Django requirement). When you
don't specify search-type, you'll usually search based on key. *Aliases* are extra names given to
Objects using something like `@alias` or `obj.aliases.add('name')`. The main search functions (see
below) will automatically search for aliases whenever you search by-key.
 - [Tags](Component/Tags) are the main way to group and identify objects in Evennia. Tags can most often be
used (sometimes together with keys) to uniquely identify an object. For example, even though you
have two locations with the same name, you can separate them by their tagging (this is how Evennia
implements 'zones' seen in other systems). Tags can also have categories, to further organize your
data for quick lookups.
 - An object's [Attributes](Component/Attributes) can also used to find an object. This can be very useful but
since Attributes can store almost any data they are far less optimized to search for than Tags or
keys.
- The object's [Typeclass](Component/Typeclasses) indicate the sub-type of entity. A Character, Flower or
Sword are all types of Objects. A Bot is a kind of Account. The database field is called
`typeclass_path` and holds the full Python-path to the class. You can usually specify the
`typeclass` as an argument to Evennia's search functions as well as use the class directly to limit
queries.
- The `location` is only relevant for [Objects](Component/Objects) but is a very common way to weed down the
number of candidates before starting to search. The reason is that most in-game commands tend to
operate on things nearby (in the same room) so the choices can be limited from the start.
- The database id or the '#dbref' is unique (and never re-used) within each database table. So while
there is one and only one Object with dbref `#42` there could also be an Account or  Script with the
dbref `#42` at the same time. In almost all search methods you can replace the "key" search
criterion with `"#dbref"` to search for that id. This can occasionally be practical and may be what
you are used to from other code bases. But it is considered *bad practice* in Evennia to rely on
hard-coded #dbrefs to do your searches. It makes your code tied to the exact layout of the database.
It's also not very maintainable to have to remember abstract numbers. Passing the actual objects
around and searching by Tags and/or keys will usually get you what you need.


## Getting objects inside another

All in-game [Objects](Component/Objects) have a `.contents` property that returns all objects 'inside' them
(that is, all objects which has its `.location` property set to that object. This is a simple way to
get everything in a room and is also faster since this lookup is cached and won't hit the database.

- `roomobj.contents` returns a list of all objects inside `roomobj`. 
- `obj.contents` same as for a room, except this usually represents the object's inventory 
- `obj.location.contents` gets everything in `obj`'s location (including `obj` itself).
- `roomobj.exits` returns all exits starting from `roomobj` (Exits are here defined as Objects with
their `destination` field set).
- `obj.location.contents_get(exclude=obj)` - this helper method returns all objects in `obj`'s
location except `obj`.

## Searching using `Object.search`

Say you have a [command](Component/Commands), and you want it to do something to a target. You might be
wondering how you retrieve that target in code, and that's where Evennia's search utilities come in.
In the most common case, you'll often use the `search` method of the `Object` or `Account`
typeclasses. In a command, the `.caller` property will refer back to the object using the command
(usually a `Character`, which is a type of `Object`) while `.args` will contain Command's arguments:

```python
# e.g. in file mygame/commands/command.py

from evennia import default_cmds

class CmdPoke(default_cmds.MuxCommand):
    """
    Pokes someone.

    Usage: poke <target>
    """
    key = "poke"

    def func(self):
        """Executes poke command"""
        target = self.caller.search(self.args)  
        if not target:  
            # we didn't find anyone, but search has already let the 
            # caller know. We'll just return, since we're done
            return
        # we found a target! we'll do stuff to them.
        target.msg("You have been poked by %s." % self.caller)
        self.caller.msg("You have poked %s." % target)
```
By default, the search method of a Character will attempt to find a unique object match for the
string sent to it (`self.args`, in this case, which is the arguments passed to the command by the
player) in the surroundings of the Character - the room or their inventory. If there is no match
found, the return value (which is assigned to `target`) will be `None`, and an appropriate failure
message will be sent to the Character. If there's not a unique match, `None` will again be returned,
and a different error message will be sent asking them to disambiguate the multi-match. By default,
the user can then pick out a specific match using with a number and dash preceding the name of the
object: `character.search("2-pink unicorn")` will try to find the second pink unicorn in the room.

The search method has many [arguments](github:evennia.objects.objects#defaultcharactersearch) that
allow you to refine the search, such as by designating the location to search in or only matching
specific typeclasses.

## Searching using `utils.search`

Sometimes you will want to find something that isn't tied to the search methods of a character or
account. In these cases, Evennia provides a [utility module with a number of search
functions](github:evennia.utils.search). For example, suppose you want a command that will find and
display all the rooms that are tagged as a 'hangout', for people to gather by. Here's a simple
Command to do this:

```python
# e.g. in file mygame/commands/command.py

from evennia import default_cmds
from evennia.utils.search import search_tag

class CmdListHangouts(default_cmds.MuxCommand):
    """Lists hangouts"""
    key = "hangouts"

    def func(self):
        """Executes 'hangouts' command"""
        hangouts = search_tag(key="hangout", 
                              category="location tags")        
        self.caller.msg("Hangouts available: {}".format(
                        ", ".join(str(ob) for ob in hangouts)))
```

This uses the `search_tag` function to find all objects previously tagged with [Tags](Component/Tags)
"hangout" and with category "location tags".

Other important search methods in `utils.search` are

- `search_object`
- `search_account`
- `search_scripts`
- `search_channel`
- `search_message`
- `search_help`
- `search_tag` - find Objects with a given Tag. 
- `search_account_tag` - find Accounts with a given Tag.
- `search_script_tag` - find Scripts with a given Tag.
- `search_channel_tag` - find Channels with a given Tag.
- `search_object_attribute` - find Objects with a given Attribute.
- `search_account_attribute` - find Accounts with a given Attribute.
- `search_attribute_object` - this returns the actual Attribute, not the object it sits on.

> Note: All search functions return a Django `queryset` which is technically a list-like
representation of the database-query it's about to do. Only when you convert it to a real list, loop
over it or try to slice or access any of its contents will the datbase-lookup happen. This means you
could yourself customize the query further if you know what you are doing (see the next section).

## Queries in Django

*This is an advanced topic.*

Evennia's search methods should be sufficient for the vast majority of situations. But eventually
you might find yourself trying to figure out how to get searches for unusual circumstances: Maybe
you want to find all characters who are *not* in rooms tagged as hangouts *and* have the lycanthrope
tag *and* whose names start with a vowel, but *not* with 'Ab', and *only if* they have 3 or more
objects in their inventory ... You could in principle use one of the earlier search methods to find
all candidates and then loop over them with a lot of if statements in raw Python. But you can do
this much more efficiently by querying the database directly.
 
Enter [django's querysets](https://docs.djangoproject.com/en/1.11/ref/models/querysets/). A QuerySet
is the representation of a database query and can be modified as desired. Only once one tries to
retrieve the data of that query is it *evaluated* and does an actual database request. This is
useful because it means you can modify a query as much as you want (even pass it around) and only
hit the database once you are happy with it.
Evennia's search functions are themselves an even higher level wrapper around Django's queries, and
many search methods return querysets. That means that you could get the result from a search
function and modify the resulting query to your own ends to further tweak what you search for.

Evaluated querysets can either contain objects such as Character objects, or lists of values derived
from the objects. Queries usually use the 'manager' object of a class, which by convention is the
`.objects` attribute of a class. For example, a query of Accounts that contain the letter 'a' could
be:

```python
    from typeclasses.accounts import Account

queryset = Account.objects.filter(username__contains='a')

```

The `filter` method of a manager takes arguments that allow you to define the query, and you can
continue to refine the query by calling additional methods until you evaluate the queryset, causing
the query to be executed and return a result. For example, if you have the result above, you could,
without causing the queryset to be evaluated yet, get rid of matches that contain the letter 'e by
doing this:

```python
queryset = result.exclude(username__contains='e')

```

> You could also have chained `.exclude` directly to the end of the previous line. 

Once you try to access the result, the queryset will be evaluated automatically under the hood:

```python
accounts = list(queryset)  # this fills list with matches

for account in queryset:
    # do something with account

accounts = queryset[:4]  # get first four matches
account = queryset[0]  # get first match
# etc

```

### Limiting by typeclass

Although `Character`s, `Exit`s, `Room`s, and other children of `DefaultObject` all shares the same
underlying database table, Evennia provides a shortcut to do more specific queries only for those
typeclasses. For example, to find only `Character`s whose names start with 'A', you might do:

```python
Character.objects.filter(db_key__startswith="A")

```

If Character has a subclass `Npc` and you wanted to find only Npc's you'd instead do

```python
Npc.objects.filter(db_key__startswith="A")

```

If you wanted to search both Characters and all its subclasses (like Npc) you use the `*_family`
method which is added by Evennia:


```python
Character.objects.filter_family(db_key__startswith="A")
```

The higher up in the inheritance hierarchy you go the more objects will be included in these
searches. There is one special case, if you really want to include *everything* from a given
database table. You do that by searching on the database model itself. These are named `ObjectDB`,
`AccountDB`, `ScriptDB` etc.

```python
from evennia import AccountDB

# all Accounts in the database, regardless of typeclass
all = AccountDB.objects.all()

```

Here are the most commonly used methods to use with the `objects` managers: 

- `filter` - query for a listing of objects based on search criteria. Gives empty queryset if none
were found.
- `get` - query for a single match - raises exception if none were found, or more than one was
found.
- `all` - get all instances of the particular type.
- `filter_family` - like `filter`, but search all sub classes as well.
- `get_family` - like `get`, but search all sub classes as well.
- `all_family` - like `all`, but return entities of all subclasses as well. 

## Multiple conditions

If you pass more than one keyword argument to a query method, the query becomes an `AND`
relationship. For example, if we want to find characters whose names start with "A" *and* are also
werewolves (have the `lycanthrope` tag), we might do:

```python
queryset = Character.objects.filter(db_key__startswith="A", db_tags__db_key="lycanthrope")
```

To exclude lycanthropes currently in rooms tagged as hangouts, we might tack on an `.exclude` as
before:

```python
queryset = quersyet.exclude(db_location__db_tags__db_key="hangout")
```

Note the syntax of the keywords in building the queryset. For example, `db_location` is the name of
the database field sitting on (in this case) the `Character` (Object). Double underscore `__` works
like dot-notation in normal Python (it's used since dots are not allowed in keyword names). So the
instruction `db_location__db_tags__db_key="hangout"` should be read as such:

1. "On the `Character` object ... (this comes from us building this queryset using the
`Character.objects` manager)
2. ... get the value of the `db_location` field ... (this references a Room object, normally)
3. ... on that location, get the value of the `db_tags` field ... (this is a many-to-many field that
can be treated like an object for this purpose. It references all tags on the location)
4. ... through the `db_tag` manager, find all Tags having a field `db_key` set to the value
"hangout"."

This may seem a little complex at first, but this syntax will work the same for all queries. Just
remember that all *database-fields* in Evennia are prefaced with `db_`. So even though Evennia is
nice enough to alias the `db_key` field so you can normally just do `char.key` to get a character's
name, the database field is actually called `db_key` and the real name must be used for the purpose
of building a query.

> Don't confuse database fields with [Attributes](Component/Attributes) you set via `obj.db.attr = 'foo'` or
`obj.attributes.add()`. Attributes are custom database entities *linked* to an object. They are not
separate fields *on* that object like `db_key` or `db_location` are. You can get attached Attributes
manually through the `db_attributes` many-to-many field in the same way as `db_tags` above.

### Complex queries

What if you want to have a query with with `OR` conditions or negated requirements (`NOT`)? Enter
Django's Complex Query object,
[Q](https://docs.djangoproject.com/en/1.11/topics/db/queries/#complex-lookups-with-q-objects). `Q()`
objects take a normal django keyword query as its arguments. The special thing is that these Q
objects can then be chained together with set operations: `|` for OR, `&` for AND, and preceded with
`~` for NOT to build a combined, complex query.

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