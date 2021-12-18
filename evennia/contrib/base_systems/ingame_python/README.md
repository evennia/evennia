# Evennia in-game Python system

Vincent Le Goff 2017

This contrib adds the system of in-game Python in Evennia, allowing immortals (or other trusted builders) to
dynamically add features to individual objects.  Using custom Python set in-game, every immortal or privileged users
could have a specific room, exit, character, object or something else behave differently from its
"cousins".  For these familiar with the use of softcode in MU`*`, like SMAUG MudProgs, the ability to
add arbitrary behavior to individual objects is a step toward freedom.  Keep in mind, however, the
warning below, and read it carefully before the rest of the documentation.

## A WARNING REGARDING SECURITY

Evennia's in-game Python system will run arbitrary Python code without much restriction.  Such a system is as
powerful as potentially dangerous, and you will have to keep in mind these points before deciding to
install it:

1. Untrusted people can run Python code on your game server with this system.  Be careful about who
   can use this system (see the permissions below).
2. You can do all of this in Python outside the game.  The in-game Python system is not to replace all your
   game feature.

## Basic structure and vocabulary

- At the basis of the in-game Python system are **events**.  An **event** defines the context in which we
  would like to call some arbitrary code.  For instance, one event is
  defined on exits and will fire every time a character traverses through this exit.  Events are described
  on a [typeclass](https://github.com/evennia/evennia/wiki/Typeclasses) (like
  [exits](https://github.com/evennia/evennia/wiki/Objects#exits) in our example).  All objects inheriting
  from this typeclass will have access to this event.
- **Callbacks** can be set on individual objects, on events defined in code.  These **callbacks**
  can contain arbitrary code and describe a specific behavior for an object.  When the event fires,
  all callbacks connected to this object's event are executed.

To see the system in context, when an object is picked up (using the default `get` command), a
specific event is fired:

1. The event "get" is set on objects (on the `Object` typeclass).
2. When using the "get" command to pick up an object, this object's `at_get` hook is called.
3. A modified hook of DefaultObject is set by the event system.  This hook will execute (or call)
   the "get" event on this object.
4. All callbacks tied to this object's "get" event will be executed in order.  These callbacks act
   as functions containing Python code that you can write in-game, using specific variables that
   will be listed when you edit the callback itself.
5. In individual callbacks, you can add multiple lines of Python code that will be fired at this
   point.  In this example, the `character` variable will contain the character who has picked up
   the object, while `obj` will contain the object that was picked up.

Following this example, if you create a callback "get" on the object "a sword", and put in it:

```python
character.msg("You have picked up {} and have completed this quest!".format(obj.get_display_name(character)))
```

When you pick up this object you should see something like:

    You pick up a sword.
    You have picked up a sword and have completed this quest!

## Installation

Being in a separate contrib, the in-game Python system isn't installed by default.  You need to do it
manually, following these steps:

1. Launch the main script (important!):
   ```@py evennia.create_script("evennia.contrib.ingame_python.scripts.EventHandler")```
2. Set the permissions (optional):
   - `EVENTS_WITH_VALIDATION`: a group that can edit callbacks, but will need approval (default to
     `None`).
   - `EVENTS_WITHOUT_VALIDATION`: a group with permission to edit callbacks without need of
     validation (default to `"immortals"`).
   - `EVENTS_VALIDATING`: a group that can validate callbacks (default to `"immortals"`).
   - `EVENTS_CALENDAR`: type of the calendar to be used (either `None`, `"standard"` or `"custom"`,
     default to `None`).
3. Add the `@call` command.
4. Inherit from the custom typeclasses of the in-game Python system.
   - `evennia.contrib.ingame_python.typeclasses.EventCharacter`: to replace `DefaultCharacter`.
   - `evennia.contrib.ingame_python.typeclasses.EventExit`: to replace `DefaultExit`.
   - `evennia.contrib.ingame_python.typeclasses.EventObject`: to replace `DefaultObject`.
   - `evennia.contrib.ingame_python.typeclasses.EventRoom`: to replace `DefaultRoom`.

The following sections describe in details each step of the installation.

> Note: If you were to start the game without having started the main script (such as when
resetting your database) you will most likely face a traceback when logging in, telling you
that a 'callback' property is not defined. After performing step `1` the error will go away.

### Starting the event script

To start the event script, you only need a single command, using `@py`.

    @py evennia.create_script("evennia.contrib.ingame_python.scripts.EventHandler")

This command will create a global script (that is, a script independent from any object).  This
script will hold basic configuration, individual callbacks and so on.  You may access it directly,
but you will probably use the callback handler.  Creating this script will also create a `callback`
handler on all objects (see below for details).

### Editing permissions

This contrib comes with its own set of permissions.  They define who can edit callbacks without
validation, and who can edit callbacks but needs validation.  Validation is a process in which an
administrator (or somebody trusted as such) will check the callbacks produced by others and will
accept or reject them.  If accepted, the callbacks are connected, otherwise they are never run.

By default, callbacks can only be created by immortals: no one except the immortals can edit
callbacks, and immortals don't need validation.  It can easily be changed, either through settings
or dynamically by changing permissions of users.

The events contrib adds three
[permissions](https://github.com/evennia/evennia/wiki/Locks#permissions) in the settings.  You can
override them by changing the settings into your `server/conf/settings.py` file (see below for an
example).  The settings defined in the events contrib are:

- `EVENTS_WITH_VALIDATION`: this defines a permission that can edit callbacks, but will need
  approval.  If you set this to `"wizards"`, for instance, users with the permission `"wizards"`
will be able to edit callbacks.  These callbacks will not be connected, though, and will need to be
checked and approved by an administrator.  This setting can contain `None`, meaning that no user is
allowed to edit callbacks with validation.
- `EVENTS_WITHOUT_VALIDATION`: this setting defines a permission allowing editing of callbacks
  without needing validation.  By default, this setting is set to `"immortals"`.  It means that
immortals can edit callbacks, and they will be connected when they leave the editor, without needing
approval.
- `EVENTS_VALIDATING`: this last setting defines who can validate callbacks.  By default, this is
  set to `"immortals"`, meaning only immortals can see callbacks needing validation, accept or
reject them.

You can override all these settings in your `server/conf/settings.py` file.  For instance:

```python
# ... other settings ...

# Event settings
EVENTS_WITH_VALIDATION = "wizards"
EVENTS_WITHOUT_VALIDATION = "immortals"
EVENTS_VALIDATING = "immortals"
```

In addition, there is another setting that must be set if you plan on using the time-related events
(events that are scheduled at specific, in-game times).  You would need to specify the type of
calendar you are using.  By default, time-related events are disabled.  You can change the
`EVENTS_CALENDAR` to set it to:

- `"standard"`: the standard calendar, with standard days, months, years and so on.
- `"custom"`: a custom calendar that will use the
  [custom_gametime](https://github.com/evennia/evennia/blob/master/evennia/contrib/custom_gametime.py)
contrib to schedule events.

This contrib defines two additional permissions that can be set on individual users:

- `events_without_validation`: this would give this user the rights to edit callbacks but not
  require validation before they are connected.
- `events_validating`: this permission allows this user to run validation checks on callbacks
  needing to be validated.

For instance, to give the right to edit callbacks without needing approval to the player 'kaldara',
you might do something like:

    @perm *kaldara = events_without_validation

To remove this same permission, just use the `/del` switch:

    @perm/del *kaldara = events_without_validation

The rights to use the `@call` command are directly related to these permissions: by default, only
users who have the `events_without_validation` permission or are in (or above) the group defined in
the `EVENTS_WITH_VALIDATION` setting will be able to call the command (with different switches).

### Adding the `@call` command

You also have to add the `@call` command to your Character CmdSet.  This command allows your users
to add, edit and delete callbacks in-game.  In your `commands/default_cmdsets, it might look like
this:

```python
from evennia import default_cmds
from evennia.contrib.ingame_python.commands import CmdCallback

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    The `CharacterCmdSet` contains general in-game commands like `look`,
    `get`, etc available on in-game Character objects. It is merged with
    the `PlayerCmdSet` when a Player puppets a Character.
    """
    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super(CharacterCmdSet, self).at_cmdset_creation()
        self.add(CmdCallback())
```

### Changing parent classes of typeclasses

Finally, to use the in-game Python system, you need to have your typeclasses inherit from the modified event
classes.  For instance, in your `typeclasses/characters.py` module, you should change inheritance
like this:

```python
from evennia.contrib.ingame_python.typeclasses import EventCharacter

class Character(EventCharacter):

    # ...
```

You should do the same thing for your rooms, exits and objects.  Note that the in-game Python system works by
overriding some hooks.  Some of these features might not be accessible in your game if you don't
call the parent methods when overriding hooks.

## Using the `@call` command

The in-game Python system relies, to a great extent, on its `@call` command.  Who can execute this command,
and who can do what with it, will depend on your set of permissions.

The `@call` command allows to add, edit and delete callbacks on specific objects' events.  The event
system can be used on most Evennia objects, mostly typeclassed objects (excluding players).  The
first argument of the `@call` command is the name of the object you want to edit.  It can also be
used to know what events are available for this specific object.

### Examining callbacks and events

To see the events connected to an object, use the `@call` command and give the name or ID of the
object to examine.  For instance, @call here` to examine the events on your current location.  Or
`@call self` to see the events on yourself.

This command will display a table, containing:

- The name of each event in the first column.
- The number of callbacks of this name, and the number of total lines of these callbacks in the
  second column.
- A short help to tell you when the event is triggered in the third column.

If you execute `@call #1` for instance, you might see a table like this:

```
+------------------+---------+-----------------------------------------------+
| Event name       |  Number | Description                                   |
+~~~~~~~~~~~~~~~~~~+~~~~~~~~~+~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~+
| can_delete       |   0 (0) | Can the character be deleted?                 |
| can_move         |   0 (0) | Can the character move?                       |
| can_part         |   0 (0) | Can the departing character leave this room?  |
| delete           |   0 (0) | Before deleting the character.                |
| greet            |   0 (0) | A new character arrives in the location of    |
|                  |         | this character.                               |
| move             |   0 (0) | After the character has moved into its new    |
|                  |         | room.                                         |
| puppeted         |   0 (0) | When the character has been puppeted by a     |
|                  |         | player.                                       |
| time             |   0 (0) | A repeated event to be called regularly.      |
| unpuppeted       |   0 (0) | When the character is about to be un-         |
|                  |         | puppeted.                                     |
+------------------+---------+-----------------------------------------------+
```

### Creating a new callback

The `/add` switch should be used to add a callback.  It takes two arguments beyond the object's
name/DBREF:

1. After an = sign, the name of the event to be edited (if not supplied, will display the list of
   possible events, like above).
2. The parameters (optional).

We'll see callbacks with parameters later.  For the time being, let's try to prevent a character
from going through the "north" exit of this room:

```
@call north
+------------------+---------+-----------------------------------------------+
| Event name       |  Number | Description                                   |
+~~~~~~~~~~~~~~~~~~+~~~~~~~~~+~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~+
| can_traverse     |   0 (0) | Can the character traverse through this exit? |
| msg_arrive       |   0 (0) | Customize the message when a character        |
|                  |         | arrives through this exit.                    |
| msg_leave        |   0 (0) | Customize the message when a character leaves |
|                  |         | through this exit.                            |
| time             |   0 (0) | A repeated event to be called regularly.      |
| traverse         |   0 (0) | After the character has traversed through     |
|                  |         | this exit.                                    |
+------------------+---------+-----------------------------------------------+
```

If we want to prevent a character from traversing through this exit, the best event for us would be
"can_traverse".

> Why not "traverse"?  If you read the description of both events, you will see "traverse" is called
 **after** the character has traversed through this exit.  It would be too late to prevent it.  On
> the other hand, "can_traverse" is obviously checked before the character traverses.

When we edit the event, we have some more information:

    @call/add north = can_traverse

Can the character traverse through this exit?
This event is called when a character is about to traverse this
exit.  You can use the deny() eventfunc to deny the character from
exiting for this time.

Variables you can use in this event:

    - character: the character that wants to traverse this exit.
    - exit: the exit to be traversed.
    - room: the room in which stands the character before moving.

The section dedicated to [eventfuncs](#the-eventfuncs) will elaborate on the `deny()` function and
other eventfuncs.  Let us say, for the time being, that it can prevent an action (in this case, it
can prevent the character from traversing through this exit).  In the editor that opened when you
used `@call/add`, you can type something like:

```python
if character.id == 1:
    character.msg("You're the superuser, 'course I'll let you pass.")
else:
    character.msg("Hold on, what do you think you're doing?")
    deny()
```

You can now enter `:wq` to leave the editor by saving the callback.

If you enter `@call north`, you should see that "can_traverse" now has an active callback.  You can
use `@call north = can_traverse` to see more details on the connected callbacks:

```
@call north = can_traverse
+--------------+--------------+----------------+--------------+--------------+
|       Number | Author       | Updated        | Param        | Valid        |
+~~~~~~~~~~~~~~+~~~~~~~~~~~~~~+~~~~~~~~~~~~~~~~+~~~~~~~~~~~~~~+~~~~~~~~~~~~~~+
|            1 | XXXXX        | 5 seconds ago  |              | Yes          |
+--------------+--------------+----------------+--------------+--------------+
```

The left column contains callback numbers.  You can use them to have even more information on a
specific event.  Here, for instance:

```
@call north = can_traverse 1
Callback can_traverse 1 of north:
Created by XXXXX on 2017-04-02 17:58:05.
Updated by XXXXX on 2017-04-02 18:02:50
This callback is connected and active.
Callback code:
if character.id == 1:
    character.msg("You're the superuser, 'course I'll let you pass.")
else:
    character.msg("Hold on, what do you think you're doing?")
    deny()
```

Then try to walk through this exit.  Do it with another character if possible, too, to see the
difference.

### Editing and removing a callback

You can use the `/edit` switch to the `@call` command to edit a callback.  You should provide, after
the name of the object to edit and the equal sign:

1. The name of the event (as seen above).
2. A number, if several callbacks are connected at this location.

You can type `@call/edit <object> = <event name>` to see the callbacks that are linked at this
location.  If there is only one callback, it will be opened in the editor; if more are defined, you
will be asked for a number to provide (for instance, `@call/edit north = can_traverse 2`).

The command `@call` also provides a `/del` switch to remove a callback.  It takes the same arguments
as the `/edit` switch.

When removed, callbacks are logged, so an administrator can retrieve its content, assuming the
`/del` was an error.

### The code editor

When adding or editing a callback, the event editor should open in code mode.  The additional
options supported by the editor in this mode are describe in [a dedicated section of the EvEditor's
documentation](https://github.com/evennia/evennia/wiki/EvEditor#the-eveditor-to-edit-code).

## Using events

The following sections describe how to use events for various tasks, from the most simple to the
most complex.

### The eventfuncs

In order to make development a little easier, the in-game Python system provides eventfuncs to be used in
callbacks themselves.  You don't have to use them, they are just shortcuts.  An eventfunc is just a
simple function that can be used inside of your callback code.

Function   | Argument                 | Description                       | Example
-----------|--------------------------|-----------------------------------|--------
deny       | `()`                     | Prevent an action from happening. | `deny()`
get        | `(**kwargs)`             | Get a single object.              | `char = get(id=1)`
call_event | `(obj, name, seconds=0)` | Call another event.               | `call_event(char, "chain_1", 20)`

#### deny

The `deny()` function allows to interrupt the callback and the action that called it.  In the
`can_*` events, it can be used to prevent the action from happening.  For instance, in `can_say` on
rooms, it can prevent the character from saying something in the room.  One could have a `can_eat`
event set on food that would prevent this character from eating this food.

Behind the scenes, the `deny()` function raises an exception that is being intercepted by the
handler of events.  The handler will then report that the action was cancelled.

#### get

The `get` eventfunc is a shortcut to get a single object with a specific identity.  It's often used
to retrieve an object with a given ID.  In the section dedicated to [chained
events](#chained-events), you will see a concrete example of this function in action.

#### call_event

Some callbacks will call other events.  It is particularly useful for [chained
events](#chained-events) that are described in a dedicated section.  This eventfunc is used to call
another event, immediately or in a defined time.

You need to specify as first parameter the object containing the event.  The second parameter is the
name of the event to call.  The third parameter is the number of seconds before calling this event.
By default, this parameter is set to 0 (the event is called immediately).

### Variables in callbacks

In the Python code you will enter in individual callbacks, you will have access to variables in your
locals.  These variables will depend on the event, and will be clearly listed when you add or edit a
callback.  As you've seen in the previous example, when we manipulate characters or character
actions, we often have a `character` variable that holds the character doing the action.

In most cases, when an event is fired, all callbacks from this event are called.  Variables are
created for each event.  Sometimes, however, the callback will execute and then ask for a variable
in your locals: in other words, some callbacks can alter the actions being performed by changing
values of variables.  This is always clearly specified in the help of the event.

One example that will illustrate this system is the "msg_leave" event that can be set on exits.
This event can alter the message that will be sent to other characters when someone leaves through
this exit.

    @call/add down = msg_leave

Which should display:

```
Customize the message when a character leaves through this exit.
This event is called when a character leaves through this exit.
To customize the message that will be sent to the room where the
character came from, change the value of the variable "message"
to give it your custom message.  The character itself will not be
notified.  You can use mapping between braces, like this:
    message = "{character} falls into a hole!"
In your mapping, you can use {character} (the character who is
about to leave), {exit} (the exit), {origin} (the room in which
the character is), and {destination} (the room in which the character
is heading for).  If you need to customize the message with other
information, you can also set "message" to None and send something
else instead.

Variables you can use in this event:
    character: the character who is leaving through this exit.
    exit: the exit being traversed.
    origin: the location of the character.
    destination: the destination of the character.
    message: the message to be displayed in the location.
    mapping: a dictionary containing additional mapping.
```

If you write something like this in your event:

```python
message = "{character} falls into a hole in the ground!"
```

And if the character Wilfred takes this exit, others in the room will see:

    Wildred falls into a hole in the ground!

In this case, the in-game Python system placed the variable "message" in the callback locals, but will read
from it when the event has been executed.

### Callbacks with parameters

Some callbacks are called without parameter.  It has been the case for all examples we have seen
before.  In some cases, you can create callbacks that are triggered under only some conditions.  A
typical example is the room's "say" event.  This event is triggered when somebody says something in
the room.  Individual callbacks set on this event can be configured to fire only when some words are
used in the sentence.

For instance, let's say we want to create a cool voice-operated elevator.  You enter into the
elevator and say the floor number... and the elevator moves in the right direction.  In this case,
we could create an callback with the parameter "one":

    @call/add here = say one

This callback will only fire when the user says a sentence that contains "one".

But what if we want to have a callback that would fire if the user says 1 or one?  We can provide
several parameters, separated by a comma.

    @call/add here = say 1, one

Or, still more keywords:

    @call/add here = say 1, one, ground

This time, the user could say something like "take me to the ground floor" ("ground" is one of our
keywords defined in the above callback).

Not all events can take parameters, and these who do have different ways of handling them.  There
isn't a single meaning to parameters that could apply to all events.  Refer to the event
documentation for details.

> If you get confused between callback variables and parameters, think of parameters as checks
> performed before the callback is run.  Event with parameters will only fire some specific
> callbacks, not all of them.

### Time-related events

Events are usually linked to commands,  as we saw before.  However, this is not always the case.
Events can be triggered by other actions and, as we'll see later, could even be called from inside
other events!

There is a specific event, on all objects, that can trigger at a specific time.  It's an event with
a mandatory parameter, which is the time you expect this event to fire.

For instance, let's add an event on this room that should trigger every day, at precisely 12:00 PM
(the time is given as game time, not real time):

    @call here = time 12:00

```python
# This will be called every MUD day at 12:00 PM
room.msg_contents("It's noon, time to have lunch!")
```

Now, at noon every MUD day, this event will fire and this callback will be executed.  You can use
this event on every kind of typeclassed object, to have a specific action done every MUD day at the
same time.

Time-related events can be much more complex than this.  They can trigger every in-game hour or more
often (it might not be a good idea to have events trigger that often on a lot of objects).  You can
have events that run every in-game week or month or year.  It will greatly vary depending on the
type of calendar used in your game.  The number of time units is described in the game
configuration.

With a standard calendar, for instance, you have the following units: minutes, hours, days, months
and years.  You will specify them as numbers separated by either a colon (:), a space ( ), or a dash
(-).  Pick whatever feels more appropriate (usually, we separate hours and minutes with a colon, the
other units with a dash).

Some examples of syntax:

- `18:30`: every day at 6:30 PM.
- `01 12:00`: every month, the first day, at 12 PM.
- `06-15 09:58`: every year, on the 15th of June (month comes before day), at 9:58 AM.
- `2025-01-01 00:00`: January 1st, 2025 at midnight (obviously, this will trigger only once).

Notice that we specify units in the reverse order (year, month, day, hour and minute) and separate
them with logical separators.  The smallest unit that is not defined is going to set how often the
event should fire.  That's why, if you use `12:00`, the smallest unit that is not defined is "day":
the event will fire every day at the specified time.

> You can use chained events (see below) in conjunction with time-related events to create more
random or frequent actions in events.

### Chained events

Callbacks can call other events, either now or a bit later.  It is potentially very powerful.

To use chained events, just use the `call_event` eventfunc.  It takes 2-3 arguments:

- The object containing the event.
- The name of the event to call.
- Optionally, the number of seconds to wait before calling this event.

All objects have events that are not triggered by commands or game-related operations.  They are
called "chain_X", like "chain_1", "chain_2", "chain_3" and so on.  You can give them more specific
names, as long as it begins by "chain_", like "chain_flood_room".

Rather than a long explanation, let's look at an example: a subway that will go from one place to
the next at regular times.  Connecting exits (opening its doors), waiting a bit, closing them,
rolling around and stopping at a different station.  That's quite a complex set of callbacks, as it
is, but let's only look at the part that opens and closes the doors:

    @call/add here = time 10:00

```python
# At 10:00 AM, the subway arrives in the room of ID 22.
# Notice that exit #23 and #24 are respectively the exit leading
# on the platform and back in the subway.
station = get(id=22)
to_exit = get(id=23)
back_exit = get(id=24)

# Open the door
to_exit.name = "platform"
to_exit.aliases = ["p"]
to_exit.location = room
to_exit.destination = station
back_exit.name = "subway"
back_exit.location = station
back_exit.destination = room

# Display some messages
room.msg_contents("The doors open and wind gushes in the subway")
station.msg_contents("The doors of the subway open with a dull clank.")

# Set the doors to close in 20 seconds
call_event(room, "chain_1", 20)
```

This callback will:

1. Be called at 10:00 AM (specify 22:00 to set it to 10:00 PM).
2. Set an exit between the subway and the station.  Notice that the exits already exist (you will
   not have to create them), but they don't need to have specific location and destination.
3. Display a message both in the subway and on the platform.
4. Call the event "chain_1" to execute in 20 seconds.

And now, what should we have in "chain_1"?

    @call/add here = chain_1

```python
# Close the doors
to_exit.location = None
to_exit.destination = None
back_exit.location = None
back_exit.destination = None
room.msg_content("After a short warning signal, the doors close and the subway begins moving.")
station.msg_content("After a short warning signal, the doors close and the subway begins moving.")
```

Behind the scenes, the `call_event` function freezes all variables ("room", "station", "to_exit",
"back_exit" in our example), so you don't need to define them again.

A word of caution on callbacks that call chained events: it isn't impossible for a callback to call
itself at some recursion level.  If `chain_1` calls `chain_2` that calls `chain_3` that calls
`chain_`, particularly if there's no pause between them, you might run into an infinite loop.

Be also careful when it comes to handling characters or objects that may very well move during your
pause between event calls.  When you use `call_event()`, the MUD doesn't pause and commands can be
entered by players, fortunately.  It also means that, a character could start an event that pauses
for awhile, but be gone when the chained event is called.  You need to check that, even lock the
character into place while you are pausing (some actions should require locking) or at least,
checking that the character is still in the room, for it might create illogical situations if you
don't.

> Chained events are a special case: contrary to standard events, they are created in-game, not
 through code.  They usually contain only one callback, although nothing prevents you from creating
 several chained events in the same object.

## Using events in code

This section describes callbacks and events from code, how to create new events, how to call them in
a command, and how to handle specific cases like parameters.

Along this section, we will see how to implement the following example: we would like to create a
"push" command that could be used to push objects.  Objects could react to this command and have
specific events fired.

### Adding new events

Adding new events should be done in your typeclasses.  Events are contained in the `_events` class
variable, a dictionary of event names as keys, and tuples to describe these events as values.  You
also need to register this class, to tell the in-game Python system that it contains events to be added to
this typeclass.

Here, we want to add a "push" event on objects.  In your `typeclasses/objects.py` file, you should
write something like:

```python
from evennia.contrib.ingame_python.utils import register_events
from evennia.contrib.ingame_python.typeclasses import EventObject

EVENT_PUSH = """
A character push the object.
This event is called when a character uses the "push" command on
an object in the same room.

Variables you can use in this event:
    character: the character that pushes this object.
    obj: the object connected to this event.
"""

@register_events
class Object(EventObject):
    """
    Class representing objects.
    """

    _events = {
        "push": (["character", "obj"], EVENT_PUSH),
    }
```

- Line 1-2: we import several things we will need from the in-game Python system.  Note that we use
  `EventObject` as a parent instead of `DefaultObject`, as explained in the installation.
- Line 4-12: we usually define the help of the event in a separate variable, this is more readable,
  though there's no rule against doing it another way.  Usually, the help should contain a short
explanation on a single line, a longer explanation on several lines, and then the list of variables
with explanations.
- Line 14: we call a decorator on the class to indicate it contains events.  If you're not familiar
  with decorators, you don't really have to worry about it, just remember to put this line just
above the class definition if your class contains events.
- Line 15: we create the class inheriting from `EventObject`.
- Line 20-22: we define the events of our objects in an `_events` class variable.  It is a
  dictionary.  Keys are event names.  Values are a tuple containing:
  - The list of variable names (list of str).  This will determine what variables are needed when
    the event triggers.  These variables will be used in callbacks (as we'll see below).
  - The event help (a str, the one we have defined above).

If you add this code and reload your game, create an object and examine its events with `@call`, you
should see the "push" event with its help.  Of course, right now, the event exists, but it's not
fired.

### Calling an event in code

The in-game Python system is accessible through a handler on all objects.  This handler is named `callbacks`
and can be accessed from any typeclassed object (your character, a room, an exit...).  This handler
offers several methods to examine and call an event or callback on this object.

To call an event, use the `callbacks.call` method in an object.  It takes as argument:

- The name of the event to call.
- All variables that will be accessible in the event as positional arguments.  They should be
  specified in the order chosen when [creating new events](#adding-new-events).

Following the same example, so far, we have created an event on all objects, called "push".  This
event is never fired for the time being.  We could add a "push" command, taking as argument the name
of an object.  If this object is valid, it will call its "push" event.

```python
from commands.command import Command

class CmdPush(Command):

    """
    Push something.

    Usage:
        push <something>

    Push something where you are, like an elevator button.

    """

    key = "push"

    def func(self):
        """Called when pushing something."""
        if not self.args.strip():
            self.msg("Usage: push <something>")
            return

        # Search for this object
        obj = self.caller.search(self.args)
        if not obj:
            return

        self.msg("You push {}.".format(obj.get_display_name(self.caller)))

        # Call the "push" event of this object
        obj.callbacks.call("push", self.caller, obj)
```

Here we use `callbacks.call` with the following arguments:

- `"push"`: the name of the event to be called.
- `self.caller`: the one who pushed the button (this is our first variable, `character`).
- `obj`: the object being pushed (our second variable, `obj`).

In the "push" callbacks of our objects, we then can use the "character" variable (containing the one
who pushed the object), and the "obj" variable (containing the object that was pushed).

### See it all work

To see the effect of the two modifications above (the added event and the "push" command), let us
create a simple object:

    @create/drop rock
    @desc rock = It's a single rock, apparently pretty heavy.  Perhaps you can try to push it though.
    @call/add rock = push

In the callback you could write:

```python
from random import randint
number = randint(1, 6)
character.msg("You push a rock... is... it... going... to... move?")
if number == 6:
    character.msg("The rock topples over to reveal a beautiful ant-hill!")
```

You can now try to "push rock".  You'll try to push the rock, and once out of six times, you will
see a message about a "beautiful ant-hill".

### Adding new eventfuncs

Eventfuncs, like `deny(), are defined in `contrib/events/eventfuncs.py`.  You can add your own
eventfuncs by creating a file named `eventfuncs.py` in your `world` directory.  The functions
defined in this file will be added as helpers.

You can also decide to create your eventfuncs in another location, or even in several locations.  To
do so, edit the `EVENTFUNCS_LOCATION` setting in your `server/conf/settings.py` file, specifying
either a python path or a list of Python paths in which your helper functions are defined.  For
instance:

```python
EVENTFUNCS_LOCATIONS = [
        "world.events.functions",
]
```

### Creating events with parameters

If you want to create events with parameters (if you create a "whisper" or "ask" command, for
instance, and need to have some characters automatically react to words), you can set an additional
argument in the tuple of events in your typeclass' ```_events``` class variable.  This third argument
must contain a callback that will be called to filter through the list of callbacks when the event
fires.  Two types of parameters are commonly used (but you can define more parameter types, although
this is out of the scope of this documentation).

- Keyword parameters: callbacks of this event will be filtered based on specific keywords.  This is
  useful if you want the user to specify a word and compare this word to a list.
- Phrase parameters: callbacks will be filtered using an entire phrase and checking all its words.
  The "say" command uses phrase parameters (you can set a "say" callback to fires if a phrase
contains one specific word).

In both cases, you need to import a function from `evennia.contrib.ingame_python.utils` and use it as third
parameter in your event definition.

- `keyword_event` should be used for keyword parameters.
- `phrase_event` should be used for phrase parameters.

For example, here is the definition of the "say" event:

```python
from evennia.contrib.ingame_python.utils import register_events, phrase_event
# ...
@register_events
class SomeTypeclass:
    _events = {
        "say": (["speaker", "character", "message"], CHARACTER_SAY, phrase_event),
    }
```

When you call an event using the `obj.callbacks.call` method, you should also provide the parameter,
using the `parameters` keyword:

```python
obj.callbacks.call(..., parameters="<put parameters here>")
```

It is necessary to specifically call the event with parameters, otherwise the system will not be
able to know how to filter down the list of callbacks.

## Disabling all events at once

When callbacks are running in an infinite loop, for instance, or sending unwanted information to
players or other sources, you, as the game administrator, have the power to restart without events.
The best way to do this is to use a custom setting, in your setting file
(`server/conf/settings.py`):

```python
# Disable all events
EVENTS_DISABLED = True
```

The in-game Python system will still be accessible (you will have access to the `@call` command, to debug),
but no event will be called automatically.
