# Containers
Contribution by InspectorCaracal (2023)

Adds the ability to put objects into other container objects by providing a container typeclass and extending certain base commands.

## Installation

To install, import and add the `ContainerCmdSet` to `CharacterCmdSet` in your `default_cmdsets.py` file:

```python
from evennia.contrib.game_systems.containers import ContainerCmdSet

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    # ...
    
    def at_cmdset_creation(self):
        # ...
        self.add(ContainerCmdSet)
```

This will replace the default `look` and `get` commands with the container-friendly versions provided by the contrib as well as add a new `put` command.

## Usage

The contrib includes a `ContribContainer` typeclass which has all of the set-up necessary to be used as a container. To use, all you need to do is create an object in-game with that typeclass - it will automatically inherit anything you implemented in your base Object typeclass as well.

    create bag:game_systems.containers.ContribContainer

The contrib's `ContribContainer` comes with a capacity limit of a maximum number of items it can hold. This can be changed per individual object.

In code:
```py
obj.capacity = 5
```
In game:

    set box/capacity = 5

You can also make any other objects usable as containers by setting the `get_from` lock type on it.

    lock mysterious box = get_from:true()

## Extending

The `ContribContainer` class is intended to be usable as-is, but you can also inherit from it for your own container classes to extend its functionality. Aside from having the container lock pre-set on object creation, it comes with three main additions:

### `capacity` property

`ContribContainer.capacity` is an `AttributeProperty` - meaning you can access it in code with `obj.capacity` and also set it in game with `set obj/capacity = 5` - which represents the capacity of the container as an integer. You can override this with a more complex representation of capacity on your own container classes.

### `at_pre_get_from` and `at_pre_put_in` methods

These two methods on `ContribContainer` are called as extra checks when attempting to either get an object from, or put an object in, a container. The contrib's `ContribContainer.at_pre_get_from` doesn't do any additional validation by default, while `ContribContainer.at_pre_put_in` does a simple capacity check.

You can override these methods on your own child class to do any additional capacity or access checks.