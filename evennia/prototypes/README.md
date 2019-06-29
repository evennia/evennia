# Prototypes

A 'Prototype' is a normal Python dictionary describing unique features of individual instance of a
Typeclass. The prototype is used to 'spawn' a new instance with custom features detailed by said
prototype. This allows for creating variations without having to create a large number of actual
Typeclasses. It is a good way to allow Builders more freedom of creation without giving them full
Python access to create Typeclasses.

For example, if a Typeclass 'Cat' describes all the coded differences between a Cat and
other types of animals, then prototypes could be used to quickly create unique individual cats with
different Attributes/properties (like different colors, stats, names etc) without having to make a new
Typeclass for each. Prototypes have inheritance and can be scripted when they are applied to create
a new instance of a typeclass - a common example would be to randomize stats and name.

The prototype is a normal dictionary with specific keys. Almost all values can be callables
triggered when the prototype is used to spawn a new instance. Below is an example:

```
{
# meta-keys - these are used only when listing prototypes in-game. Only prototype_key is mandatory,
# but it must be globally unique.

 "prototype_key": "base_goblin",
 "prototype_desc": "A basic goblin",
 "prototype_locks": "edit:all();spawn:all()",
 "prototype_tags": "mobs",

# fixed-meaning keys, modifying the spawned instance. 'typeclass' may be
# replaced by 'parent', referring to the prototype_key of an existing prototype
# to inherit from.

 "typeclass": "types.objects.Monster",
 "key": "goblin grunt",
 "tags": ["mob", "evil", ('greenskin','mob')]   # tags as well as tags with category etc
 "attrs": [("weapon", "sword")]  # this allows to set Attributes with categories etc

# non-fixed keys are interpreted as Attributes and their

 "health": lambda: randint(20,30),
 "resists": ["cold", "poison"],
 "attacks": ["fists"],
 "weaknesses": ["fire", "light"]
 }

```
## Using prototypes

Prototypes are generally used as inputs to the `spawn` command:

    @spawn prototype_key

This will spawn a new instance of the prototype in the caller's current location unless the
`location` key of the prototype was set (see below). The caller must pass the prototype's 'spawn'
lock to be able to use it.

    @spawn/list [prototype_key]

will show all available prototypes along with meta info, or look at a specific prototype in detail.


## Creating prototypes

The `spawn` command can also be used to directly create/update prototypes from in-game.

    spawn/save {"prototype_key: "goblin", ... }

but it is probably more convenient to use the menu-driven prototype wizard:

    spawn/menu goblin

In code:

```python

from evennia import prototypes

goblin = {"prototype_key": "goblin:, ... }

prototype = prototypes.save_prototype(goblin)

```

Prototypes will normally be stored in the database (internally this is done using a Script, holding
the meta-info and the prototype). One can also define prototypes outside of the game by assigning
the prototype dictionary to a global variable in a module defined by `settings.PROTOTYPE_MODULES`:

```python
# in e.g. mygame/world/prototypes.py

GOBLIN = {
    "prototype_key": "goblin",
    ...
    }

```

Such prototypes cannot be modified from inside the game no matter what `edit` lock they are given
(we refer to them as 'readonly') but can be a fast and efficient way to give builders a starting
library of prototypes to inherit from.

## Valid Prototype keys

Every prototype key also accepts a callable (taking no arguments) for producing its value or a
string with an $protfunc definition. That callable/protfunc must then return a value on a form the
prototype key expects.

    - `prototype_key` (str):  name of this prototype. This is used when storing prototypes and should
        be unique. This should always be defined but for prototypes defined in modules, the
        variable holding the prototype dict will become the prototype_key if it's not explicitly
        given.
    - `prototype_desc` (str, optional): describes prototype in listings
    - `prototype_locks` (str, optional): locks for restricting access to this prototype. Locktypes
        supported are 'edit' and 'use'.
    - `prototype_tags` (list, optional): List of tags or tuples (tag, category) used to group prototype
        in listings

    - `parent` (str or tuple, optional): name (`prototype_key`) of eventual parent prototype, or a
	list of parents for multiple left-to-right inheritance.
    - `prototype`: Deprecated. Same meaning as 'parent'.
    - `typeclass` (str, optional): if not set, will use typeclass of parent prototype or use
        `settings.BASE_OBJECT_TYPECLASS`
    - `key` (str, optional): the name of the spawned object. If not given this will set to a
        random hash
    - `location` (obj, optional): location of the object - a valid object or #dbref
    - `home` (obj or str, optional): valid object or #dbref
    - `destination` (obj or str, optional): only valid for exits (object or #dbref)

    - `permissions` (str or list, optional): which permissions for spawned object to have
    - `locks` (str,  optional): lock-string for the spawned object
    - `aliases` (str or list, optional): Aliases for the spawned object.
    - `exec` (str, optional): this is a string of python code to execute or a list of such
        codes.  This can be used e.g. to trigger custom handlers on the object. The execution
        namespace contains 'evennia' for the library and 'obj'. All default spawn commands limit
        this functionality to Developer/superusers. Usually it's better to use callables or
        prototypefuncs instead of this.
    - `tags` (str, tuple or list, optional): string or list of strings or tuples
        `(tagstr, category)`. Plain strings will be result in tags with no category (default tags).
    - `attrs` (tuple or list, optional): tuple or list of tuples of Attributes to add. This
        form allows more complex Attributes to be set. Tuples at least specify `(key, value)`
        but can also specify up to `(key, value, category, lockstring)`. If you want to specify a
        lockstring but not a category, set the category to `None`.
    - `ndb_<name>` (any): value of a nattribute (`ndb_` is stripped). This is usually not useful to
	put in a prototype unless the NAttribute is used immediately upon spawning.
    - `other` (any): any other name is interpreted as the key of an Attribute with
        its value. Such Attributes have no categories.
