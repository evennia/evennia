# Tags

```{code-block}
:caption: In game 
> tag obj = tagname
```
```{code-block} python 
:caption: In code, using .tags (TagHandler)

obj.tags.add("mytag", category="foo")
obj.tags.get("mytag", category="foo")
```

```{code-block} python
:caption: In code, using TagProperty or TagCategoryProperty

from evennia import DefaultObject
from evennia import TagProperty, TagCategoryProperty

class Sword(DefaultObject): 
    # name of property is the tagkey, category as argument
    can_be_wielded = TagProperty(category='combat')
    has_sharp_edge = TagProperty(category='combat')

    # name of property is the category, tag-keys are arguments
    damage_type = TagCategoryProperty("piercing", "slashing")
    crafting_element = TagCategoryProperty("blade", "hilt", "pommel") 
        
```

In-game, tags are controlled `tag` command:

     > tag Chair = furniture
     > tag Chair = furniture
     > tag Table = furniture
     
     > tag/search furniture 
     Chair, Sofa, Table
     
_Tags_ are short text lables one can 'hang' on objects in order to organize, group and quickly find out their properties. An Evennia entity can be tagged by any number of tags. They are more efficient than [Attributes](./Attributes.md) since on the database-side, Tags are _shared_ between all objects with that particular tag. A tag does not carry a value in itself; it either sits on the entity 

You manage Tags using the `TagHandler` (`.tags`) on typeclassed entities. You can also assign Tags on the class level through the `TagProperty` (one tag, one category per line) or the `TagCategoryProperty` (one category, multiple tags per line). Both of these use the `TagHandler` under the hood, they are just convenient ways to add tags already when you define your class. 

Above, the tags inform us that the `Sword` is both sharp and can be wielded. If that's all they do, they could just be a normal Python flag. When tags become important is if there are a lot of objects with different combinations of tags. Maybe you have a magical spell that dulls _all_ sharp-edged objects in the castle - whether sword, dagger, spear or kitchen knife! You can then just grab all objects with the `has_sharp_edge` tag. 
Another example would be a weather script affecting all rooms tagged as `outdoors` or finding all characters tagged with `belongs_to_fighter_guild`. 

In Evennia, Tags are technically also used to implement `Aliases` (alternative names for objects) and `Permissions` (simple strings for [Locks](./Locks.md) to check for).


## Working with Tags

### Searching for tags 

The common way to use tags (once they have been set) is find all objects tagged with a particular tag combination: 

    objs = evennia.search_tag(key=("foo", "bar"), category='mycategory')

As shown above, you can also have tags without a category (category of `None`). 

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

> Note that searching for just "furniture" will only return the objects tagged with the "furniture" tag that has a category of `None`. We must explicitly give the category to get the "luxurious" furniture. 

Using any of the `search_tag` variants will all return [Django Querysets](https://docs.djangoproject.com/en/4.1/ref/models/querysets/), including if you only have one match. You can treat querysets as lists and iterate over them, or continue building search queries with them.

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

There is also an in-game command that deals with assigning and using ([Object-](./Objects.md)) tags:

     tag/search furniture


### TagHandler 

This is  the main way to work with tags when you have the entry already. This handler sits on all typeclassed entities as `.tags` and you use `.tags.add()`, `.tags.remove()` and `.tags.has()` to manage Tags on the object. [See the api docs](evennia.typeclasses.tags.TagHandler) for more useful methods. 

The TagHandler can be found on any of the base *typeclassed* objects, namely [Objects](./Objects.md), [Accounts](./Accounts.md), [Scripts](./Scripts.md) and [Channels](./Channels.md) (as well as their children). Here are some examples of use:

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

When using `remove`, the `Tag` is not deleted but are just disconnected from the tagged object. This makes for very quick operations. The `clear` method removes (disconnects) all Tags from the object.


### TagProperty 

This is used as a property when you create a new class: 

```python
from evennia import TagProperty 
from typeclasses import Object 

class MyClass(Object):
    mytag = TagProperty(tagcategory)
```

This will create a Tag named `mytag` and category `tagcategory` in the database. You'll be able to find it by `obj.mytag` but more useful you can find it with the normal Tag searching methods in the database. 

Note that if you were to delete this tag with `obj.tags.remove("mytag", "tagcategory")`, that tag will be _re-added_ to the object next time this property is accessed! 

### TagCategoryProperty 

This is the inverse of `TagProperty`: 

```python
from evennia import TagCategoryProperty 
from typeclasses import Object 

class MyClass(Object): 
    tagcategory = TagCategroyProperty(tagkey1, tagkey2)
```

The above example means you'll have two tags (`tagkey1` and `tagkey2`), each with the `tagcategory` category, assigned to this object. 

Note that similarly to how it works for `TagProperty`, if you were to delete these tags from the object with the `TagHandler` (`obj.tags.remove("tagkey1", "tagcategory")`, then these tags will be _re-added_ automatically next time the property is accessed. 

The reverse is however not true: If you were to _add_ a new tag of the same category to the object, via the `TagHandler`, then this property will include that in the list of returned tags. 

If you want to 're-sync' the tags in the property with that in the database, you can use the `del` operation on it - next time the property is accessed, it will then only show the default keys you specify in it. Here's how it works: 

```python
>>> obj.tagcategory 
["tagkey1", "tagkey2"]

# remove one of the default tags outside the property
>>> obj.tags.remove("tagkey1", "tagcategory")
>>> obj.tagcategory 
["tagkey1", "tagkey2"]   # missing tag is auto-created! 

# add a new tag from outside the property 
>>> obj.tags.add("tagkey3", "tagcategory")
>>> obj.tagcategory 
["tagkey1", "tagkey2", "tagkey3"]  # includes the new tag! 

# sync property with datbase 
>>> del obj.tagcategory 
>>> obj.tagcategory 
["tagkey1", "tagkey2"]   # property/database now in sync 
```

## Properties of Tags (and Aliases and Permissions)

Tags are *unique*. This means that there is only ever one Tag object with a given key and category.

```{important}
Not specifying a category (default) gives the tag a category of `None`, which is also considered a unique key + category combination. You cannot use `TagCategoryProperty` to set Tags with `None` categories, since the property name may not be `None`. Use the `TagHandler` (or `TagProperty`) for this.

```
When Tags are assigned to game entities, these entities are actually sharing the same Tag. This means that Tags are not suitable for storing information about a single object - use an
[Attribute](./Attributes.md) for this instead. Tags are a lot more limited than Attributes but this also
makes them very quick to lookup in the database - this is the whole point.

Tags have the following properties, stored in the database:

- **key** - the name of the Tag. This is the main property to search for when looking up a Tag.
- **category** - this category allows for retrieving only specific subsets of tags used for different purposes. You could have one category of tags for "zones", another for "outdoor locations", for example. If not given, the category will be `None`, which is also considered a separate, default, category.
- **data** - this is an optional text field with information about the tag. Remember that Tags are shared between entities, so this field cannot hold any object-specific information. Usually it would be used to hold info about the group of entities the Tag is tagging - possibly used for contextual help like a tool tip. It is not used by default.

There are also two special properties. These should usually not need to be changed or set, it is used internally by Evennia to implement various other uses it makes of the `Tag` object:

- **model** - this holds a *natural-key* description of the model object that this tag deals with, on the form *application.modelclass*, for example `objects.objectdb`. It used by the TagHandler of each entity type for correctly storing the data behind the  scenes.
- **tagtype** - this is a "top-level category" of sorts for the inbuilt children of Tags, namely *Aliases* and *Permissions*. The Taghandlers using this special field are especially intended to free up the *category* property for any use you desire.

## Aliases and Permissions

Aliases and Permissions are implemented using normal TagHandlers that simply save Tags with a
different `tagtype`. These handlers are named `aliases` and `permissions` on all Objects. They are
used in the same way as Tags above:

```python
    boy.aliases.add("rascal")
    boy.permissions.add("Builders")
    boy.permissions.remove("Builders")

    all_aliases = boy.aliases.all()
```

and so on. Similarly to how `tag` works in-game, there is also the `perm` command for assigning permissions and `@alias` command for aliases.