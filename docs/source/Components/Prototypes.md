# Spawner and Prototypes


The *spawner* is a system for defining and creating individual objects from a base template called a
*prototype*. It is only designed for use with in-game [Objects](./Objects.md), not any other type of
entity.

The normal way to create a custom object in Evennia is to make a [Typeclass](./Typeclasses.md). If you
haven't read up on Typeclasses yet, think of them as normal Python classes that save to the database
behind the scenes. Say you wanted to create a "Goblin" enemy. A common way to do this would be to
first create a `Mobile` typeclass that holds everything common to mobiles in the game, like generic
AI, combat code and various movement methods. A  `Goblin` subclass is then made to inherit from
`Mobile`. The `Goblin` class adds stuff unique to goblins, like group-based AI (because goblins are
smarter in a group), the ability to panic, dig for gold etc.

But now it's time to actually start to create some goblins and put them in the world. What if we
wanted those goblins to not all look the same? Maybe we want grey-skinned and green-skinned goblins
or some goblins that can cast spells or which wield different weapons? We *could* make subclasses of
`Goblin`, like `GreySkinnedGoblin` and `GoblinWieldingClub`. But that seems a bit excessive (and a
lot of Python code for every little thing). Using classes can also become impractical when wanting
to combine them - what if we want a grey-skinned goblin shaman wielding a spear - setting up a web
of classes inheriting each other with multiple inheritance can be tricky.

This is what the *prototype* is for. It is a Python dictionary that describes these per-instance
changes to an object. The prototype also has the advantage of allowing an in-game builder to
customize an object without access to the Python backend. Evennia also allows for saving and
searching prototypes so other builders can find and use (and tweak) them later. Having a library of
interesting prototypes is a good reasource for builders. The OLC system allows for creating, saving,
loading and manipulating prototypes using a menu system.

The *spawner* takes a prototype and uses it to create (spawn) new, custom objects.

## Using the OLC

Enter the `olc` command or `@spawn/olc` to enter the prototype wizard. This is a menu system for
creating, loading, saving and manipulating prototypes. It's intended to be used by in-game builders
and will give a better understanding of prototypes in general. Use `help` on each node of the menu
for more information. Below are further details about how prototypes work and how they are used.

## The prototype

The prototype dictionary can either be created for you by the OLC (see above), be  written manually
in a Python module (and then referenced by the `@spawn` command/OLC), or created on-the-fly and
manually loaded into the spawner function or `@spawn` command.

The dictionary defines all possible database-properties of an Object. It has a fixed set of allowed
keys. When preparing to store the prototype in the database (or when using the OLC), some
of these keys are mandatory. When just passing a one-time prototype-dict to the spawner the system
is
more lenient and will use defaults for keys not explicitly provided.

In dictionary form, a prototype can look something like this:

```python
{
   "prototype_key": "house"
   "key": "Large house"
   "typeclass": "typeclasses.rooms.house.House"
 }
```
If you wanted to load it into the spawner in-game you could just put all on one line:

    @spawn {"prototype_key="house", "key": "Large house", ...}

> Note that the prototype dict as given on the command line must be a valid Python structure -
so you need to put quotes around strings etc. For security reasons, a dict inserted from-in game
cannot have any
other advanced Python functionality, such as executable code, `lambda` etc. If builders are supposed
to be able to use such features, you need to offer them through [$protfuncs](Spawner-and-
Prototypes#protfuncs), embedded runnable functions that you have full control to check and vet
before running.

### Prototype keys

All keys starting with `prototype_` are for book keeping.

 - `prototype_key` - the 'name' of the prototype, used for referencing the prototype
    when spawning and inheritance. If defining a prototype in a module and this
    not set, it will be auto-set to the name of the prototype's variable in the module.
 - `prototype_parent` - If given, this should be the `prototype_key` of another prototype stored in
    the system or available in a module. This makes this prototype *inherit* the keys from the
    parent and only override what is needed. Give a tuple `(parent1, parent2, ...)` for multiple
    left-right inheritance. If this is not given, a `typeclass` should usually be defined (below).
 - `prototype_desc` - this is optional and used when listing the prototype in in-game listings.
 - `protototype_tags` - this is optional and allows for tagging the prototype in order to find it
   easier later.
 - `prototype_locks` - two lock types are supported: `edit` and `spawn`. The first lock restricts
   the copying and editing of the prototype when loaded through the OLC. The second determines who
   may use the prototype to create new objects.


The remaining keys determine actual aspects of the objects to spawn from this prototype:

 - `key` - the main object identifier. Defaults to "Spawned Object *X*", where *X* is a random
integer.
 - `typeclass` - A full python-path (from your gamedir) to the typeclass you want to use. If not
set, the `prototype_parent` should be
   defined, with `typeclass` defined somewhere in the parent chain. When creating a one-time
prototype
   dict just for spawning, one could omit this - `settings.BASE_OBJECT_TYPECLASS` will be used
instead.
 - `location` - this should be a `#dbref`.
 - `home` - a valid `#dbref`. Defaults to `location` or `settings.DEFAULT_HOME` if location does not
exist.
 - `destination` - a valid `#dbref`. Only used by exits.
 - `permissions` - list of permission strings, like `["Accounts", "may_use_red_door"]`
 - `locks` - a [lock-string](./Locks.md) like `"edit:all();control:perm(Builder)"`
 - `aliases` - list of strings for use as aliases
 - `tags` - list [Tags](./Tags.md). These are given as tuples `(tag, category, data)`.
 - `attrs` - list of [Attributes](./Attributes.md). These are given as tuples `(attrname, value,
category, lockstring)`
 - Any other keywords are interpreted as non-category [Attributes](./Attributes.md) and their values.
This is convenient for simple Attributes - use `attrs` for full control of Attributes.

#### More on prototype inheritance

- A prototype can inherit by defining a `prototype_parent` pointing to the name
  (`prototype_key` of another prototype). If a list of `prototype_keys`, this
  will be stepped through from left to right, giving priority to the first in
  the list over those appearing later. That is, if your inheritance is
  `prototype_parent = ('A', 'B,' 'C')`, and all parents contain colliding keys,
  then the one from `A` will apply.
- The prototype keys that start with `prototype_*` are all unique to each
  prototype. They are _never_ inherited from parent to child.
- The prototype fields `'attr': [(key, value, category, lockstring),...]`
  and `'tags': [(key, category, data), ...]` are inherited in a _complementary_
  fashion. That means that only colliding key+category matches will be replaced, not the entire list.
  Remember that the category `None` is also considered a valid category!
- Adding an Attribute as a simple `key:value` will under the hood be translated
  into an Attribute tuple `(key, value, None, '')` and may replace an Attribute
  in the parent if it the same key  and a `None` category.
- All other keys (`permissions`, `destination`, `aliases` etc) are completely
  _replaced_ by the child's value if given. For the parent's value to be
  retained, the child must not define these keys at all.

### Prototype values

The prototype supports values of several different types.

It can be a hard-coded value:

```python
    {"key": "An ugly goblin", ...}

```

It can also be a *callable*. This callable is called without arguments whenever the prototype is
used to
spawn a new object:

```python
    {"key": _get_a_random_goblin_name, ...}

```

By use of Python `lambda` one can wrap the callable so as to make immediate settings in the
prototype:

```python
    {"key": lambda: random.choice(("Urfgar", "Rick the smelly", "Blargh the foul", ...)), ...}

```

#### Protfuncs

Finally, the value can be a *prototype function* (*Protfunc*). These look like simple function calls
that you embed in strings and that has a `$` in front, like

```python
    {"key": "$choice(Urfgar, Rick the smelly, Blargh the foul)",
     "attrs": {"desc": "This is a large $red(and very red) demon. "
                       "He has $randint(2,5) skulls in a chain around his neck."}
```
At execution time, the place of the protfunc will be replaced with the result of that protfunc being
called (this is always a string). A protfunc is a [FuncParser function](./FuncParser.md) run
every time the prototype is used to spawn a new object.

Here is how a protfunc is defined (same as an inlinefunc).

```python
# this is a silly example, you can just color the text red with |r directly!
def red(*args, **kwargs):
   """
   Usage: $red(<text>)
   Returns the same text you entered, but red.
   """
   if not args or len(args) > 1:
      raise ValueError("Must have one argument, the text to color red!")
   return f"|r{args[0]}|n"
```

> Note that we must make sure to validate input and raise `ValueError` if that fails. Also, it is
*not* possible to use keywords in the call to the protfunc (so something like `$echo(text,
align=left)` is invalid). The `kwargs` requred is for internal evennia use and not used at all for
protfuncs (only by inlinefuncs).

To make this protfunc available to builders in-game, add it to a new module and add the path to that
module to `settings.PROT_FUNC_MODULES`:

```python
# in mygame/server/conf/settings.py

PROT_FUNC_MODULES += ["world.myprotfuncs"]

```
All *global callables* in your added module will be considered a new protfunc. To avoid this (e.g.
to have helper functions that are not protfuncs on their own), name your function something starting
with `_`.

The default protfuncs available out of the box are defined in `evennia/prototypes/profuncs.py`. To
override the ones available, just add the same-named function in your own protfunc module.

| Protfunc | Description |
| --- | --- |
| `$random()` | Returns random value in range [0, 1) |
| `$randint(start, end)` | Returns random value in range [start, end] |
| `$left_justify(<text>)` | Left-justify text |
| `$right_justify(<text>)` | Right-justify text to screen width |
| `$center_justify(<text>)` | Center-justify text to screen width |
| `$full_justify(<text>)` | Spread text across screen width by adding spaces |
| `$protkey(<name>)` | Returns value of another key in this prototype (self-reference) |
| `$add(<value1>, <value2>)` | Returns value1 + value2. Can also be lists, dicts etc |
| `$sub(<value1>, <value2>)` | Returns value1 - value2 |
| `$mult(<value1>, <value2>)` | Returns value1 * value2 |
| `$div(<value1>, <value2>)` | Returns value2 / value1 |
| `$toint(<value>)` | Returns value converted to integer (or value if not possible) |
| `$eval(<code>)` | Returns result of [literal-eval](https://docs.python.org/2/library/ast.html#ast.literal_eval) of code string. Only simple python expressions. |
| `$obj(<query>)` | Returns object #dbref searched globally by key, tag or #dbref. Error if more than one found. |
| `$objlist(<query>)` | Like `$obj`, except always returns a list of zero, one or more results. |
| `$dbref(dbref)` | Returns argument if it is formed as a #dbref (e.g. #1234), otherwise error. |

For developers with access to Python, using protfuncs in prototypes is generally not useful. Passing
real Python functions is a lot more powerful and flexible. Their main use is to allow in-game
builders to
do limited coding/scripting for their prototypes without giving them direct access to raw Python.

## Storing prototypes

A prototype can be defined and stored in two ways, either in the database or as a dict in a module.

### Database prototypes

Stored as [Scripts](./Scripts.md) in the database. These are sometimes referred to as *database-
prototypes* This is the only way for in-game builders to modify and add prototypes. They have the
advantage of being easily modifiable and sharable between builders but you need to work with them
using in-game tools.

### Module-based prototypes

These prototypes are defined as dictionaries assigned to global variables in one of the modules
defined in `settings.PROTOTYPE_MODULES`. They can only be modified from outside the game so they are
are necessarily "read-only" from in-game and cannot be modified (but copies of them could be made
into database-prototypes). These were the only prototypes available before Evennia 0.8. Module based
prototypes can be useful in order for developers to provide read-only "starting" or "base"
prototypes to build from or if they just prefer to work offline in an external code editor.

By default `mygame/world/prototypes.py` is set up for you to add your own prototypes. *All global
dicts* in this module will be considered by Evennia to be a prototype. You could also tell Evennia
to look for prototypes in more modules if you want:

```python
# in mygame/server/conf.py

PROTOTYPE_MODULES = += ["world.myownprototypes", "combat.prototypes"]

```

Here is an example of a prototype defined in a module:

    ```python
    # in a module Evennia looks at for prototypes,
    # (like mygame/world/prototypes.py)

    ORC_SHAMAN = {"key":"Orc shaman",
		  "typeclass": "typeclasses.monsters.Orc",
		  "weapon": "wooden staff",
		  "health": 20}
    ```

> Note that in the example above, `"ORC_SHAMAN"` will become the `prototype_key` of this prototype.
> It's the only case when `prototype_key` can be skipped in a prototype. However, if `prototype_key`
> was given explicitly, that would take precedence. This is a legacy behavior and it's recommended
> that you always add `prototype_key` to be consistent.


## Using @spawn

The spawner can be used from inside the game through the Builder-only `@spawn` command. Assuming the
"goblin" typeclass is available to the system (either as a database-prototype or read from module),
you can spawn a new goblin with

    @spawn goblin

You can also specify the prototype directly as a valid Python dictionary:

    @spawn {"prototype_key": "shaman", \
	    "key":"Orc shaman", \
            "prototype_parent": "goblin", \
            "weapon": "wooden staff", \
            "health": 20}

> Note: The `@spawn` command is more lenient about the prototype dictionary than shown here. So you
can for example skip the `prototype_key` if you are just testing a throw-away prototype. A random
hash will be used to please the validation. You could also skip  `prototype_parent/typeclass` - then
the typeclass given by `settings.BASE_OBJECT_TYPECLASS` will be used.

## Using evennia.prototypes.spawner()

In code you access the spawner mechanism directly via the call

```python
    new_objects = evennia.prototypes.spawner.spawn(*prototypes)
```

All arguments are prototype dictionaries. The function will return a
matching list of created objects. Example:

```python
    obj1, obj2 = evennia.prototypes.spawner.spawn({"key": "Obj1", "desc": "A test"},
                                                  {"key": "Obj2", "desc": "Another test"})
```
> Hint: Same as when using `@spawn`, when spawning from a one-time prototype dict like this, you can
skip otherwise required keys, like `prototype_key` or `typeclass`/`prototype_parent`. Defaults will
be used.

Note that no `location` will be set automatically when using `evennia.prototypes.spawner.spawn()`,
you
have to specify `location` explicitly in the prototype dict.

If the prototypes you supply are using `prototype_parent` keywords, the spawner will read prototypes
from modules
in `settings.PROTOTYPE_MODULES` as well as those saved to the database to determine the body of
available parents. The `spawn` command takes many optional keywords, you can find its definition [in
the api docs](github:evennia.prototypes.spawner#spawn).
