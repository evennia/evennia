# Prototype

The prototype dictionary can either be created for you by the OLC (see above), be  written manually in a Python module (and then referenced by the `@spawn` command/OLC), or created on-the-fly and manually loaded into the spawner function or `@spawn` command. 

The dictionary defines all possible database-properties of an Object. It has a fixed set of allowed keys. When preparing to store the prototype in the database (or when using the OLC), some 
of these keys are mandatory. When just passing a one-time prototype-dict to the spawner the system is
more lenient and will use defaults for keys not explicitly provided. 

In dictionary form, a prototype can look something like this: 


    { 
       "prototype_key": "house"
       "key": "Large house"
       "typeclass": "typeclasses.rooms.house.House"
    }

If you wanted to load it into the spawner in-game you could just put all on one line: 

    @spawn {"prototype_key="house", "key": "Large house", ...}

> Note that the prototype dict as given on the command line must be a valid Python structure -
so you need to put quotes around strings etc. For security reasons, a dict inserted from-in game cannot have any 
other advanced Python functionality, such as executable code, `lambda` etc. If builders are supposed
to be able to use such features, you need to offer them through [protfuncs](#protfuncs), embedded runnable functions that you have full control to check and vet before running.

### Prototype keys

All keys starting with `prototype_` are for book keeping.

 - `prototype_key` - the 'name' of the prototype. While this can sometimes be skipped (such as when
    defining a prototype in a module or feeding a prototype-dict manually to the spawner function), it's good 
    practice to try to include this. It is used for book-keeping and storing of the prototype so you  
    can find it later.
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

 - `key` - the main object identifier. Defaults to "Spawned Object *X*", where *X* is a random integer.
 - `typeclass` - A full python-path (from your gamedir) to the typeclass you want to use. If not set, the `prototype_parent` should be 
   defined, with `typeclass` defined somewhere in the parent chain. When creating a one-time prototype
   dict just for spawning, one could omit this - `settings.BASE_OBJECT_TYPECLASS` will be used instead.
 - `location` - this should be a `#dbref`.
 - `home` - a valid `#dbref`. Defaults to `location` or `settings.DEFAULT_HOME` if location does not exist.
 - `destination` - a valid `#dbref`. Only used by exits.
 - `permissions` - list of permission strings, like `["Accounts", "may_use_red_door"]`
 - `locks` - a [lock-string](../locks/Locks) like `"edit:all();control:perm(Builder)"`
 - `aliases` - list of strings for use as aliases
 - `tags` - list [Tags](../tags/Tags). These are given as tuples `(tag, category, data)`.
 - `attrs` - list of [Attributes](../attributes/Attributes). These are given as tuples `(attrname, value, category, lockstring)`
 - Any other keywords are interpreted as non-category [Attributes](../attributes/Attributes) and their values. This is
   convenient for simple Attributes - use `attrs` for full control of Attributes.

Deprecated as of Evennia 0.8:

 - `ndb_<name>` - sets the value of a non-persistent attribute (`"ndb_"` is stripped from the name).
   This is simply not useful in a prototype and is deprecated.
 - `exec` - This accepts a code snippet or a list of code snippets to run. This should not be used -
   use callables or [protfuncs](#protfuncs) instead (see below).

### Prototype values

The prototype supports values of several different types.

It can be a hard-coded value:

```python
    {"key": "An ugly goblin", ...}
```

It can also be a *callable*. This callable is called without arguments whenever the prototype is used to
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

Finally, the value can be a **prototype function**. These look like simple function calls that you embed in strings and that has a $ in front, like 

    {"key": "$choice(Urfgar, Rick the smelly, Blargh the foul)",
     "attrs": {"desc": "This is a large $red(and very red) demon. "
                       "He has $randint(2,5) skulls in a chain around his neck."}

At execution time, the place of the protfunc will be replaced with the result of that protfunc being called (this is always a string). A protfunc works in much the same way as an
[InlineFunc](https://github.com/evennia/evennia/wiki/TextTags#inline-functions) - they are actually
parsed using the same parser - except protfuncs are run every time the prototype is used to spawn a new object (whereas an inlinefunc is called when a text is returned to the user).

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
   return "|r{}|n".format(args[0])
```

> Note that we must make sure to validate input and raise `ValueError` if that fails. Also, it is *not* possible to use keywords in the call to the protfunc (so something like `$echo(text, align=left)` is invalid). The `kwargs` requred is for internal evennia use and not used at all for protfuncs (only by inlinefuncs). 

To make this protfunc available to builders in-game, add it to a new module and add the path to that module to `settings.PROT_FUNC_MODULES`: 

```python
# in mygame/server/conf/settings.py

PROT_FUNC_MODULES += ["world.myprotfuncs"]
```

All **global callables** in your added module will be considered a new protfunc. To avoid this (e.g. to have helper functions that are not protfuncs on their own), name your function something starting with `_`. 

The default protfuncs available out of the box are defined in `evennia/prototypes/profuncs.py`. To override the ones available, just add the same-named function in your own protfunc module.

| Protfunc | Description | 
|----------|-------------|
| `$random()` | Returns random value in range [0, 1) |
| `$randint(start, end)` | Returns random value in range (start, end) |
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
| `$obj(<query>)` | Returns object #dbref searched globally by key, tag or #dbref. Error if more than one found." |
| `$objlist(<query>)` | Like `$obj`, except always returns a list of zero, one or more results. |
| `$dbref(dbref)` | Returns argument if it is formed as a #dbref (e.g. #1234), otherwise error.

For developers with access to Python, using protfuncs in prototypes is generally not useful. Passing real Python functions is a lot more powerful and flexible. Their main use is to allow in-game builders to
do limited coding/scripting for their prototypes without giving them direct access to raw Python.

## Storing prototypes

A prototype can be defined and stored in two ways, either in the database or as a dict in a module. 

### Database prototypes

Stored as [Scripts](../scripts/Scripts) in the database. These are sometimes referred to as *database-prototypes* This is the only way for in-game builders to modify and add prototypes. They have the advantage of being easily modifiable and sharable between builders but you need to work with them using in-game tools.  

### Module-based prototypes

These prototypes are defined as dictionaries assigned to global variables in one of the modules defined in `settings.PROTOTYPE_MODULES`. They can only be modified from outside the game so they are are necessarily "read-only" from in-game and cannot be modified (but copies of them could be made into database-prototypes). These were the only prototypes available before Evennia 0.8. Module based prototypes can be useful in order for developers to provide read-only "starting" or "base" prototypes to build from or if they just prefer to work offline in an external code editor. 

By default `mygame/world/prototypes.py` is set up for you to add your own prototypes. *All global dicts* in this module will be considered by Evennia to be a prototype. You could also tell Evennia to look for prototypes in more modules if you want: 

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

