# OnDemandHandler 

This handler offers help for implementing on-demand state changes. On-demand means that the state won't be computed until the player _actually looks for it_. Until they do, nothing happens. This is the most compute-efficient way to handle your systems and you should consider using this style of system whenever you can. 

Take for example a gardening system. A player goes to a room and plants a seed. After a certain time, that plant will then move through a set of stages; it will move from "seedling" to 'sprout' to 'flowering' and then on to 'wilting' and eventually 'dead'. 

Now, you _could_ use `utils.delay` to track each phase, or use the [TickerHandler](./TickerHandler.md) to tick the flower. You could even use a [Script](./Scripts.md) on the flower. This would work like this:

1. The ticker/task/Script would automatically fire at regular intervals to update the plant through its stages. 
2. Whenever a player comes to the room, the state is already updated on the flower, so they just read the state. 

This will work fine, but if no one comes back to that room, that's a lot of updating that no one will see. While maybe not a big deal for a single player, what if you have flowers in thousands of rooms, all growing indepedently? Or some even more complex system requiring calculation on every state change. You should avoid spending computing on things that bring nothing extra to your player base.

Using the The on-demand style, the flower would instead work like this: 

1. When the player plants the seed, we register _the current timestamp_ - the time the plant starts to grow. We store this with the `OnDemandHandler` (below).
2. When a player enters the room and/or looks at the plant (or a code system needs to know the plant's state), _then_ (and only then) we check _the current time_ to figure out the state the flower must now be in (the `OnDemandHandler` does the book-keeping for us). The key is that _until we check_, the flower object is completely inactive and uses no computing resources.

## A blooming flower using the OnDemandHandler 

This handler is found as `evennia.ON_DEMAND_HANDLER`. It is meant to be integrated into your other code. Here's an example of a flower that goes through its stages of life in 12 hours.

```python
# e.g. in mygame/typeclasses/objects.py

from evennia import ON_DEMAND_HANDLER 

# ... 

class Flower(Object): 

    def at_object_creation(self):

        minute = 60
        hour = minute * 60

        ON_DEMAND_HANDLER.add(
            self,
            category="plantgrowth"
            stages={
                0: "seedling",
                10 * minute: "sprout",
                5 * hour: "flowering",
                10 * hour: "wilting",
                12 * hour: "dead"
            })

    def at_desc(self, looker):
        """
        Called whenever someone looks at this object
        """ 
        stage = ON_DEMAND_HANDLER.get_state(self, category="plantgrowth")

        match stage: 
            case "seedling": 
                return "There's nothing to see. Nothing has grown yet."
            case "sprout": 
                return "A small delicate sprout has emerged!"
            case "flowering": 
                return f"A beautiful {self.name}!"
            case "wilting": 
                return f"This {self.name} has seen better days."
            case "dead": 
                # it's dead and gone. Stop and delete 
                ON_DEMAND_HANDLER.remove(self, category="plantgrowth")
                self.delete()
```


The `get_state(key, category=None, **kwargs)` methoid is used to get the current stage. The `get_dt(key, category=None, **kwargs)` method instead retrieves the currently passed time.

You could now create the rose and it would figure out its state only when you are actually looking at it. It will stay a seedling for 10 minutes (of in-game real time) before it sprouts. Within 12 hours it will be dead again. 

If you had a `harvest` command in your game, you could equally have it check the stage of bloom and give you different results depending on if you pick the rose at the right time or not.

The on-demand handler's tasks survive a reload and will properly account for downtime.

## More usage examples

The [OnDemandHandler API](evennia.scripts.ondemandhandler.OnDemandHandler) describes how to use the handler in detail. While it's available as `evennia.ON_DEMAND_HANDLER`, its code is located in `evennia.scripts.ondemandhandler.py`. 

```python
from evennia import ON_DEMAND_HANDLER 

ON_DEMAND_HANDLER.add("key", category=None, stages=None)
time_passed = ON_DEMAND_HANDLER.get_dt("key", category=None)
current_state = ON_DEMAND_HANDLER.get_stage("key", category=None)

# remove things 
ON_DEMAND_HANDLER.remove("key", category=None)
ON_DEMAND_HANDLER.clear(cateogory="category")  #clear all with category
```

```{sidebar} Not all stages may fire! 
This is important. If no-one checks in on the flower until a time when it's  already wilting, it will simply _skip_ all its previous stages, directly to the 'wilting' stage. So don't write code for a stage that assumes previous stages to have made particular changes to the object - those changes may not have happened because those stages could have been skipped entirely!
```
- The `key` can be a string, but also a typeclassed object (its string representation will be used, which normally includes its `#dbref`). You can also pass a `callable` - this will be called without arguments and is expected to return a string to use for the `key`. Finally, you can also pass [OnDemandTask](evennia.scripts.ondemandhandler.OnDemandTask) entities - these are the objects the handler uses under the hood to represent each task. 
- The `category` allows you to further categorize your demandhandler  tasks to make sure they are unique. Since the handler is global, you need to make sure `key` + `category` is unique. While `category` is optional, if you use it you must also use it to retrieve your state later.
- `stages` is a `dict` `{dt: statename}` or `{dt: (statename, callable)}` that represents how much time (in seconds) from _the start of the task_ it takes for that stage to begin. In the flower example above, it was 10 hours until the `wilting` state began. If a callable is included, it will fire the first time that stage is reached. This callable takes the current `OnDemandTask` and `**kwargs` as arguments; the keywords are passed on from the `get_stages/dt` methods. [See below](#stage-callables) for information about the allowed callables. Having `stages` is optional - sometimes you only want to know how much time has passed.
- `.get_dt()` - get the current time (in seconds) since the task started. This is a `float`.
- `.get_stage()` - get the current state name, such as "flowering" or "seedling". If you didn't specify any `stages`, this will return `None`, and you need to interpret the `dt` yourself to determine which state you are in.

Under the hood, the handler uses  [OnDemandTask](evennia.scripts.ondemandhandler.OnDemandTask) objects. It can sometimes be practical to create tasks directly with these, and pass them to the handler in bulk: 

```python
from evennia import ON_DEMAND_HANDLER, OnDemandTask 

task1 = OnDemandTask("key1", {0: "state1", 100: ("state2", my_callable)})
task2 = OnDemandTask("key2", category="state-category")

# batch-start on-demand tasks
ON_DEMAND_HANDLER.batch_add(task1, task2)

# get the tasks back later 
task1 = ON_DEMAND_HANDLER.get("key1")
task2 = ON_DEMAND_HANDLER.get("key1", category="state-category")

# batch-deactivate tasks you have available
ON_DEMAND_HANDLER.batch_remove(task1, task2)
```

### Stage callables 

If you define one or more of your `stages` dict keys as `{dt: (statename, callable)}`, this callable will be called when that stage is checked for the first time. This 'stage callable' have a few requirements: 

- The stage callable must be [possible to pickle](https://docs.python.org/3/library/pickle.html#pickle-picklable) because it will be saved to the database. This basically means your callable needs to be a stand-alone function or a method decorated with `@staticmethod`. You won't be able to access the object instance as `self` directly from such a method or function - you need to pass it explicitly.
- The callable must always take `task` as its first element. This is the `OnDemandTask` object firing this callable.
- It may optionally take `**kwargs` . This will be passed down from your call of `get_dt` or `get_stages`.

Here's an example: 

```python
from evennia DefaultObject, ON_DEMAND_HANDLER

def mycallable(task, **kwargs)
	# this function is outside the class and is pickleable just fine
    obj = kwargs.get("obj")
    # do something with the object

class SomeObject(DefaultObject):

    def at_object_creation(self):
        ON_DEMAND_HANDLER.add(
	        "key1", 
	        stages={0: "new", 10: ("old", mycallable)}
	    )

	def do_something(self):
	    # pass obj=self into the handler; to be passed into
	    # mycallable if we are in the 'old' stage.
		state = ON_DEMAND_HANDLER.get_state("key1", obj=self)

```

Above, the `obj=self` will passed into `mycallable` once we reach the 'old' state. If we are not in the 'old' stage, the extra kwargs go nowhere. This way a function can be made aware of the object calling it while still being possible to pickle. You can also pass any other information into the callable this way. 

> If you don't want to deal with the complexity of callables you can also just read off the current stage and do all the logic outside of the handler. This can often be easier to read and maintain. 


### Looping repeatedly

Normally, when a sequence of `stages` have been cycled through, the task will just stop at the last stage indefinitely.

`evennia.OnDemandTask.stagefunc_loop` is an included static-method stage callable you can use to make the task loop. Here's an example of how to use it: 

```python
from evennia import ON_DEMAND_HANDLER, OnDemandTask 

ON_DEMAND_HANDLER.add(
    "trap_state", 
    stages={
        0: "harmless",
        50: "solvable",
        100: "primed",
        200: "deadly",
        250: ("_reset", OnDemandTask.stagefunc_loop)
    }
)
```

This is a trap state that loops through its states depending on timing. Note that the looping helper callable will _immediately_ reset the cycle back to the first stage, so the last stage will never be visible to the player/game system. So it's a good (if optional) idea to name it with `_*` to remember this is a 'virtual' stage. In the example above, the "deadly" state will cycle directly to "harmless".

The `OnDemandTask` task instance has a `.iterations` variable that will go up by one for every loop.

If the state is not checked for a long time, the looping function will correctly update the `.iterations` property on the task it would have used so far and figure out where in the cycle it is right now.

### Bouncing back and forth 

`evennia.OnDemandTask.stagefunc_bounce` is an included static-method callable you can use to 'bounce' the sequence of stages. That is, it will cycle to the end of the cycle and then reverse direction and cycle through the sequence in reverse, keeping the same time intervals between each stage. 

To make this repeat indefinitely, you need to put these callables at both ends of the list:

```python 
from evennia import ON_DEMAND_HANDLER, OnDemandTask 

ON_DEMAND_HANDLER.add(
    "cycling reactor",
    "nuclear",
    stages={
        0: ("cold", OnDemandTask.stagefunc_bounce),
        150: "luke warm",
        300: "warm", 
        450: "hot"
        600: ("HOT!", OnDemandTask.stagefunc_bounce)    
    }
)
```

This will cycle 
    
        cold -> luke warm -> warm -> hot -> HOT! 

before reversing and go back (over and over): 

        HOT! -> hot -> warm -> luke warm -> cold 

Unlike the `stagefunc_loop` callable, the bouncing one _will_ visibly stay at the first and last stage until it changes to the next one in the sequence.  The `OnDemandTask` instance has an `.iterations` property that will step up by one every time the sequence reverses. 

If the state is not checked for a long time, the bounce function will correctly update the `.iterations` property to the amount of iterations it would have done in that time, and figure out where in the cycle it is right now.

## When is it not suitable to do things on-demand?

If you put your mind to it, you can probably make of your game on-demand. The player will not be the wiser. 

There is only really one case where on-demand doesn't work, and that is if the player should be informed of something _without first providing any input_. 

If a player has to run `check health` command to see how much health they have, that could happen on demand. Similarly, a prompt could be set to update every time you move. But if you would an idling player to get a message popping up out of nowhere saying "You are feeling hungry" or to have some HP meter visually increasing also when standing still, then some sort of timer/ticker would be necessary to crank the wheels. 

Remember however, that in a text-medium (especially with traditional line-by-line MUD clients), there is only so much spam you can push on the player before they get overwhelmed.