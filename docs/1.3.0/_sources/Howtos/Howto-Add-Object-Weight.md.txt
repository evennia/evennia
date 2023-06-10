# Give objects weight

All in-game objets you can touch usually has some weight. What weight does varies from game to game. Commonly it limits how much you can carry. A heavy stone may also hurt you more than a ballon, if it falls on you. If you want to get fancy, a pressure plate may only trigger if the one stepping on it is heavy enough. 

```{code-block} python 
:linenos:
:emphasize-lines: 6,8,10,12

# inside your mygame/typeclasses/objects.py

from evennia import DefaultObject 
from evennia import AttributeProperty 

class ObjectParent: 

    weight = AttributeProperty(default=1, autocreate=False)

    @property 
    def total_weight(self):
        return self.weight + sum(obj.total_weight for obj in self.contents) 


class Object(ObjectParent, DefaultObject):
    # ...
```

```{sidebar} Why not mass? 
Yes, we know weight varies with gravity. 'Mass' is more scientifically correct. But 'mass' is less commonly used in RPGs, so we stick to 'weight' here. Just know if if your sci-fi characters can vacation on the Moon (1/6 gravity of Earth) you should consider using `mass` everywhere and calculate the current weight on the fly.
```

- **Line 6**: We use the `ObjectParent` mixin. Since this mixin is used for `Characters`, `Exits` and `Rooms` as well as for `Object`, it means all of those will automatically _also_ have weight!
- **Line 8**: We use an [AttributeProperty](../Components/Attributes.md#using-attributeproperty) to set up the 'default' weight of 1 (whatever that is). Setting `autocreate=False` means no actual `Attribute` will be created until the weight is actually changed from the default of 1. See the `AttributeProperty` documentation for caveats with this. 
- **Line 10 and 11**: Using the `@property` decorator on `total_weight` means that we will be able to call `obj.total_weight` instead of `obj.total_weight()` later. 
- **Line 12**: We sum up all weights from everything "in" this object, by looping over `self.contents`. Since _all_ objects will have weight now, this should always work! 

Let's check out the weight of some trusty boxes
```
> create/drop box1
> py self.search("box1").weight
1 
> py self.search("box1").total_weight
1 
``` 

Let's  put another box into the first one.

```
> create/drop box2 
> py self.search("box2").total_weight
1 
> py self.search("box2").location = self.search("box1")
> py self.search(box1).total_weight 
2
```


## Limit inventory by weight carried

To limit how much you can carry, you first need to know your own strength

```python
# in mygame/typeclasses/characters.py 

from evennia import AttributeProperty

# ... 

class Character(ObjectParent, DefaultCharacter): 

    carrying_capacity = AttributeProperty(10, autocreate=False)

    @property
    def carried_weight(self):
        return self.total_weight - self.weight

```

Here we make sure to add another `AttributeProperty` telling us how much to carry. In a real game, this may be based on how strong the Character is. When we consider how much weight we already carry, we should not include _our own_ weight, so we subtract that. 

To honor this limit, we'll need to override the default `get` command. 


```{sidebar} Overriding default commands

In this example, we implement the beginning of the `CmdGet` and then call the full `CmdGet()` at the end. This is not very efficient, because the parent `CmdGet` will again have to do the `caller.search()` again. To be more efficient, you will likely want to copy the entirety of the `CmdGet` code into your own version and modify it.
```

```python 
# in mygame/commands/command.py 

# ... 
from evennia import default_cmds 

# ... 

class WeightAwareCmdGet(default_cmds.CmdGet):

    def func(self):
        caller = self.caller 
        if not self.args: 
            caller.msg("Get what?")
            return 

        obj = caller.search(self.args)

        if (obj.weight + caller.carried_weight 
                > caller.carrying_capacity):
            caller.msg("You can't carry that much!")
            return 
        super().func()
```

Here we add an extra check for the weight of the thing we are trying to pick up, then we call the normal `CmdGet` with `super().func()`. 
