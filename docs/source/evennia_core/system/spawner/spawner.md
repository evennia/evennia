# Spawner
The *spawner* is a system for defining and creating individual objects from a base template called a
*prototype*. It is only designed for use with in-game [Objects](../objects/Objects), not any other type of
entity.

The normal way to create a custom object in Evennia is to make a [Typeclass](Typeclasses). If you
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

> Note: The `@spawn` command is more lenient about the prototype dictionary than shown here. So you can for example skip the `prototype_key` if you are just testing a throw-away prototype. A random hash will be used to please the validation. You could also skip  `prototype_parent/typeclass` - then the typeclass given by `settings.BASE_OBJECT_TYPECLASS` will be used. 

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
> Hint: Same as when using `@spawn`, when spawning from a one-time prototype dict like this, you can skip otherwise required keys, like `prototype_key` or `typeclass`/`prototype_parent`. Defaults will be used.

Note that no `location` will be set automatically when using `evennia.prototypes.spawner.spawn()`, you
have to specify `location` explicitly in the prototype dict.

If the prototypes you supply are using `prototype_parent` keywords, the spawner will read prototypes from modules 
in `settings.PROTOTYPE_MODULES` as well as those saved to the database to determine the body of available parents. The `spawn` command takes many optional keywords, you can find its definition [in the api docs](https://github.com/evennia/evennia/wiki/evennia.prototypes.spawner#spawn).