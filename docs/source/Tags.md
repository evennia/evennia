# Tags


A common task of a game designer is to organize and find groups of objects and do operations on them. A classic example is to have a weather script affect all "outside" rooms. Another would be for a player casting a magic spell that affects every location "in the dungeon", but not those "outside". Another would be to quickly find everyone joined with a particular guild or everyone currently dead. 

*Tags* are short text labels that you attach to objects so as to easily be able to retrieve and group them. An Evennia entity can be tagged with any number of Tags. On the database side, Tag entities are *shared* between all objects with that tag. This makes them very efficient but also fundamentally different from [Attributes](Attributes), each of which always belongs to one *single* object. 

In Evennia, Tags are technically also used to implement `Aliases` (alternative names for objects) and `Permissions` (simple strings for [Locks](Locks) to check for). 


## Properties of Tags (and Aliases and Permissions)

Tags are *unique*. This means that there is only ever one Tag object with a given key and category. 

> Not specifying a category (default) gives the tag a category of `None`, which is also considered a unique key + category combination. 

When Tags are assigned to game entities, these entities are actually sharing the same Tag. This means that Tags are not suitable for storing information about a single object - use an [Attribute](Attributes) for this instead. Tags are a lot more limited than Attributes but this also makes them very quick to lookup in the database - this is the whole point.

Tags have the following properties, stored in the database:

- **key** - the name of the Tag. This is the main property to search for when looking up a Tag.
- **category** - this category allows for retrieving only specific subsets of tags used for different purposes. You could have one category of tags for "zones", another for "outdoor locations", for example. If not given, the category will be `None`, which is also considered a separate, default, category. 
- **data** - this is an optional text field with information about the tag. Remember that Tags are shared between entities, so this field cannot hold any object-specific information. Usually it would be used to hold info about the group of entities the Tag is tagging - possibly used for contextual help like a tool tip. It is not used by default.

There are also two special properties. These should usually not need to be changed or set, it is used internally by Evennia to implement various other uses it makes of the `Tag` object:
- **model** - this holds a *natural-key* description of the model object that this tag deals with, on the form *application.modelclass*, for example `objects.objectdb`. It used by the TagHandler of each entity type for correctly storing the data behind the  scenes. 
- **tagtype** - this is a "top-level category" of sorts for the inbuilt children of Tags, namely *Aliases* and *Permissions*. The Taghandlers using this special field are especially intended to free up the *category* property for any use you desire. 

## Adding/Removing Tags

You can tag any *typeclassed* object, namely [Objects](Objects), [Accounts](Accounts), [Scripts](Scripts) and [Channels](Communications). General tags are added by the *Taghandler*.  The tag handler is accessed as a property `tags` on the relevant entity: 

```python
     mychair.tags.add("furniture")
     mychair.tags.add("furniture", category="luxurious")
     myroom.tags.add("dungeon#01")
     myscript.tags.add("weather", category="climate")
     myaccount.tags.add("guestaccount")

     mychair.tags.all()  # returns a list of Tags
     mychair.tags.remove("furniture") 
     mychair.tags.clear()    
```

Adding a new tag will either create a new Tag or re-use an already existing one. Note that there are _two_ "furniture" tags, one with a `None` category, and one with the "luxurious" category. 

When using `remove`, the `Tag` is not deleted but are just disconnected from the tagged object. This makes for very quick operations. The `clear` method removes (disconnects) all Tags from the object. You can also use the default `@tag` command: 

     @tag mychair = furniture

This tags the chair with a 'furniture' Tag (the one with a `None` category). 

## Searching for objects with a given tag

Usually tags are used as a quick way to find tagged database entities. You can retrieve all objects with a given Tag like this in code: 

```python
     import evennia
     
     # all methods return Querysets

     # search for objects 
     objs = evennia.search_tag("furniture")
     objs2 = evennia.search_tag("furniture", category="luxurious")
     dungeon = evennia.search_tag("dungeon#01")
     forest_rooms = evennia.search_tag(category="forest") 
     forest_meadows = evennia.search_tag("meadow", category="forest")
     magic_meadows = evennia.search_tag("meadow", category="magical")

     # search for scripts
     weather = evennia.search_tag_script("weather")
     climates = evennia.search_tag_script(category="climate")

     # search for accounts
     accounts = evennia.search_tag_account("guestaccount")          
```

> Note that searching for just "furniture" will only return the objects tagged with the "furniture" tag that 
has a category of `None`. We must explicitly give the category to get the "luxurious" furniture. 

Using any of the `search_tag` variants will all return [Django Querysets](https://docs.djangoproject.com/en/2.1/ref/models/querysets/), including if you only have one match. You can treat querysets as lists and iterate over them, or continue building search queries with them. 

Remember when searching that not setting a category means setting it to `None` - this does *not* mean that category is undefined, rather `None` is considered the default, unnamed category. 

```python
import evennia 

myobj1.tags.add("foo")  # implies category=None
myobj2.tags.add("foo", category="bar")

# this returns a queryset with *only* myobj1 
objs = evennia.search_tag("foo")

# these return a queryset with *only* myobj2
objs = evennia.search_tag("foo", category="bar")
# or
objs = evennia.search_tag(category="bar")

```



There is also an in-game command that deals with assigning and using ([Object-](Objects)) tags:

     @tag/search furniture

## Using Aliases and Permissions

Aliases and Permissions are implemented using normal TagHandlers that simply save Tags with a different `tagtype`. These handlers are named `aliases` and `permissions` on all Objects. They are used in the same way as Tags above:

```python
    boy.aliases.add("rascal")
    boy.permissions.add("Builders")
    boy.permissions.remove("Builders")

    all_aliases = boy.aliases.all()
```

and so on. Similarly to how `@tag` works in-game, there is also the `@perm` command for assigning permissions and `@alias` command for aliases. 

## Assorted notes

Generally, tags are enough on their own for grouping objects. Having no tag `category` is perfectly fine and the normal operation. Simply adding a new Tag for grouping objects is often better than making a new category. So think hard before deciding you really need to categorize your Tags. 

That said, tag categories can be useful if you build some game system that uses tags. You can then use tag categories to make sure to separate tags created with this system from any other tags created elsewhere. You can then supply custom search methods that *only* find objects tagged with tags of that category. An example of this 
is found in the [Zone tutorial](Zones). 
