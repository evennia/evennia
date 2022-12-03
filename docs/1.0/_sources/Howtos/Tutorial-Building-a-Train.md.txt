# Building a train that moves

> TODO: This should be updated for latest Evennia use.

Vehicles are things that you can enter and then move around in your game world. Here we'll explain how to create a train, but this can be equally applied to create other kind of vehicles
(cars, planes, boats, spaceships, submarines, ...).

Objects in Evennia have an interesting property: you can put any object inside another object. This is most obvious in rooms: a room in Evennia is just like any other game object (except rooms tend to not themselves be inside anything else).

Our train will be similar: it will be an object that other objects can get inside. We then simply
move the Train, which brings along everyone inside it.

## Creating our train object

The first step we need to do is create our train object, including a new typeclass.  To do this,
create a new file, for instance in `mygame/typeclasses/train.py` with the following content:

```python
# in mygame/typeclasses/train.py

from evennia import DefaultObject

class TrainObject(DefaultObject):

    def at_object_creation(self):
        # We'll add in code here later.
        pass

```

Now we can create our train in our game:

```
create/drop train:train.TrainObject
```

Now this is just an object that doesn't do much yet... but we can already force our way inside it
and back (assuming we created it in limbo).

```
tel train 
tel limbo
```

## Entering and leaving the train

Using the `tel`command like shown above is obviously not what we want. `@tel` is an admin command and normal players will thus never be able to enter the train! 

It is also not really a good idea to use [Exits](../Components/Objects.md#exits) to get in and out of the train - Exits are (at least by default) objects too.  They point to a specific destination. If we put an Exit in this room leading inside the train it would stay here when the train moved away (still leading into the train like a magic portal!). In the same way, if we put an Exit object inside the train, it would always point back to this room, regardless of where the Train has moved. 

Now, one *could* define custom Exit types that move with the train or change their destination in the right way - but this seems to be a pretty cumbersome solution.

What we will do instead is to create some new [commands](../Components/Commands.md): one for entering the train and
another for leaving it again. These will be stored *on the train object* and will thus be made
available to whomever is either inside it or in the same room as the train.

Let's create a new command module as `mygame/commands/train.py`:

```python
# mygame/commands/train.py

from evennia import Command, CmdSet

class CmdEnterTrain(Command):
    """
    entering the train
    
    Usage:
      enter train

    This will be available to players in the same location
    as the train and allows them to embark. 
    """

    key = "enter train"

    def func(self):
        train = self.obj
        self.caller.msg("You board the train.")
        self.caller.move_to(train, move_type="board")


class CmdLeaveTrain(Command):
    """
    leaving the train 
 
    Usage:
      leave train

    This will be available to everyone inside the 
    train. It allows them to exit to the train's
    current location. 
    """

    key = "leave train"

    def func(self):
        train = self.obj
        parent = train.location
        self.caller.move_to(parent, move_type="disembark")


class CmdSetTrain(CmdSet):

    def at_cmdset_creation(self):
        self.add(CmdEnterTrain())
        self.add(CmdLeaveTrain())
```
Note that while this seems like a lot of text, the majority of lines here are taken up by
documentation.

These commands are work in a pretty straightforward way: `CmdEnterTrain` moves the location of the player to inside the train and `CmdLeaveTrain` does the opposite: it moves the player back to the
current location of the train (back outside to its current location). We stacked them in a [cmdset](../Components/Command-Sets.md) `CmdSetTrain` so they can be used.

To make the commands work we need to add this cmdset to our train typeclass:

```python
# file mygame/typeclasses/train.py

from commands.train import CmdSetTrain
from typeclasses.objects import Object

class TrainObject(Object):

    def at_object_creation(self):        
        self.cmdset.add_default(CmdSetTrain)

```

If we now `reload` our game and reset our train, those commands should work and we can now enter and leave the train:

```
reload
typeclass/force/reset train = train.TrainObject
enter train
leave train
```

Note the switches used with the `typeclass` command: The `/force` switch is necessary to assign our object the same typeclass we already have. The `/reset` re-triggers the typeclass' `at_object_creation()` hook (which is otherwise only called the very first an instance is created).
As seen above, when this hook is called on our train, our new cmdset will be loaded.

## Locking down the commands

If you have played around a bit, you've probably figured out that you can use `leave train` when
outside the train and `enter train` when inside. This doesn't make any sense ... so let's go ahead
and fix that.  We need to tell Evennia that you can not enter the train when you're already inside
or leave the train when you're outside. One solution to this is [locks](../Components/Locks.md): we will lock down the commands so that they can only be called if the player is at the correct location. 

Since we didn't set a `lock` property on the Command, it defaults to `cmd:all()`. This means that everyone can use the command as long as they are in the same room _or inside the train_.

First of all we need to create a new lock function. Evennia comes with many lock functions built-in
already, but none that we can use for locking a command in this particular case. Create a new entry in `mygame/server/conf/lockfuncs.py`:

```python

# file mygame/server/conf/lockfuncs.py

def cmdinside(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Usage: cmdinside() 
    Used to lock commands and only allows access if the command
    is defined on an object which accessing_obj is inside of.     
    """
    return accessed_obj.obj == accessing_obj.location

```
If you didn't know, Evennia is by default set up to use all functions in this module as lock
functions (there is a setting variable that points to it).

Our new lock function, `cmdinside`, is to be used by Commands.  The `accessed_obj` is the Command object (in our case this will be `CmdEnterTrain` and `CmdLeaveTrain`) — Every command has an `obj` property: this is the the object on which the command "sits".  Since we added those commands to our train object, the `.obj` property will be set to the train object. Conversely, `accessing_obj` is the object that called the command: in our case it's the Character trying to enter or leave the train.

What this function does is to check that the player's location is the same as the train object. If
it is, it means the player is inside the train. Otherwise it means the player is somewhere else and
the check will fail.

The next step is to actually use this new lock function to create a lock of type `cmd`:

```python
# file commands/train.py
...
class CmdEnterTrain(Command):
    key = "enter train"
    locks = "cmd:not cmdinside()"
    # ...

class CmdLeaveTrain(Command):
    key = "leave train"
    locks = "cmd:cmdinside()"
    # ...
```

Notice how we use the `not` here so that we can use the same `cmdinside` to check if we are inside
and outside, without having to create two separate lock functions. After a `@reload` our commands
should be locked down appropriately and you should only be able to use them at the right places.

> Note: If you're logged in as the super user (user `#1`) then this lock will not work: the super
user ignores lock functions. In order to use this functionality you need to `@quell` first.

## Making our train move

Now that we can enter and leave the train correctly, it's time to make it move.  There are different
things we need to consider for this:

* Who can control your vehicle? The first player to enter it, only players that have a certain "drive" skill, automatically?
* Where should it go? Can the player steer the vehicle to go somewhere else or will it always follow the same route?

For our example train we're going to go with automatic movement through a predefined route (its track). The train will stop for a bit at the start and end of the route to allow players to enter and leave it.

Go ahead and create some rooms for our train. Make a list of the room ids along the route (using the `xe` command).

```
> dig/tel South station
> ex              # note the id of the station
> tunnel/tel n = Following a railroad
> ex              # note the id of the track
> tunnel/tel n = Following a railroad
> ...
> tunnel/tel n = North Station
```

Put the train onto the tracks:

```
tel south station
tel train = here
```

Next we will tell the train how to move and which route to take.

```python
# file typeclasses/train.py

from evennia import DefaultObject, search_object

from commands.train import CmdSetTrain

class TrainObject(DefaultObject):

    def at_object_creation(self):
        self.cmdset.add_default(CmdSetTrain)
        self.db.driving = False
        # The direction our train is driving (1 for forward, -1 for backwards)
        self.db.direction = 1
        # The rooms our train will pass through (change to fit your game)
        self.db.rooms = ["#2", "#47", "#50", "#53", "#56", "#59"]

    def start_driving(self):
        self.db.driving = True

    def stop_driving(self):
        self.db.driving = False

    def goto_next_room(self):
        currentroom = self.location.dbref
        idx = self.db.rooms.index(currentroom) + self.db.direction

        if idx < 0 or idx >= len(self.db.rooms):
            # We reached the end of our path
            self.stop_driving()
            # Reverse the direction of the train
            self.db.direction *= -1
        else:
            roomref = self.db.rooms[idx]
            room = search_object(roomref)[0]
            self.move_to(room)
            self.msg_contents(f"The train is moving forward to {room.name}.")
```

We added a lot of code here. Since we changed the `at_object_creation` to add in variables we will have to reset our train object like earlier (using the `@typeclass/force/reset` command).

We are keeping track of a few different things now: whether the train is moving or standing still,
which direction the train is heading to and what rooms the train will pass through.

We also added some methods: one to start moving the train, another to stop and a third that actually moves the train to the next room in the list. Or makes it stop driving if it reaches the last stop.

Let's try it out, using `py` to call the new train functionality:

```
> reload
> typeclass/force/reset train = train.TrainObject
> enter train
> py here.goto_next_room()
```

You should see the train moving forward one step along the rail road.

## Adding in scripts

If we wanted full control of the train we could now just add a command to step it along the track when desired. We want the train to move on its own though, without us having to force it by manually calling the `goto_next_room` method.

To do this we will create two [scripts](../Components/Scripts.md): one script that runs when the train has stopped at
a station and is responsible for starting the train again after a while. The other script will take
care of the driving.

Let's make a new file in `mygame/typeclasses/trainscript.py`

```python
# file mygame/typeclasses/trainscript.py

from evennia import DefaultScript

class TrainStoppedScript(DefaultScript):

    def at_script_creation(self):
        self.key = "trainstopped"
        self.interval = 30
        self.persistent = True
        self.repeats = 1
        self.start_delay = True

    def at_repeat(self):
        self.obj.start_driving()        

    def at_stop(self):
        self.obj.scripts.add(TrainDrivingScript)


class TrainDrivingScript(DefaultScript):

    def at_script_creation(self):
        self.key = "traindriving"
        self.interval = 1
        self.persistent = True

    def is_valid(self):
        return self.obj.db.driving

    def at_repeat(self):
        if not self.obj.db.driving:
            self.stop()
        else:
            self.obj.goto_next_room()

    def at_stop(self):
        self.obj.scripts.add(TrainStoppedScript)
```

Those scripts work as a state system: when the train is stopped, it waits for 30 seconds and then
starts again. When the train is driving, it moves to the next room every second. The train is always
in one of those two states - both scripts take care of adding the other one once they are done.

As a last step we need to link the stopped-state script to our train, reload the game and reset our
train again., and we're ready to ride it around!

```python
# file typeclasses/train.py

from typeclasses.trainscript import TrainStoppedScript

class TrainObject(DefaultObject):

    def at_object_creation(self):
        # ...
        self.scripts.add(TrainStoppedScript)
```

```
> reload
> typeclass/force/reset train = train.TrainObject
> enter train

# output:
< The train is moving forward to Following a railroad.
< The train is moving forward to Following a railroad.
< The train is moving forward to Following a railroad.
...
< The train is moving forward to Following a railroad.
< The train is moving forward to North station.

leave train
```

Our train will stop 30 seconds at each end station and then turn around to go back to the other end.

## Expanding

This train is very basic and still has some flaws. Some more things to do:

* Make it look like a train.
* Make it impossible to exit and enter the train mid-ride. This could be made by having the enter/exit commands check so the train is not moving before allowing the caller to proceed.
* Have train conductor commands that can override the automatic start/stop.
* Allow for in-between stops between the start- and end station
* Have a rail road track instead of hard-coding the rooms in the train object. This could for example be a custom [Exit](../Components/Objects.md#exits) only traversable by trains. The train will follow the track. Some track segments can split to lead to two different rooms and a player can switch the direction to which room it goes.
* Create another kind of vehicle!