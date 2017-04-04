# Evennia event system

Vincent Le Goff 2017

This contrib adds the system of events in Evennia, allowing immortals (or other trusted builders) to dynamically add features to individual objects.  Using events, every immortal or privileged users could have a specific room, exit, character, object or something else behave differently from its "cousins".  For these familiar with the use of softcode in MU*, like SMAUG MudProgs, the ability to add arbitrary behavior to individual objects is a step toward freedom.  Keep in mind, however, the warning below, and read it carefully before the rest of the documentation.

## A WARNING REGARDING SECURITY

Evennia's event system will run arbitrary Python code without much restriction.  Such a system is as powerful as potentially dangerous, and you will have to keep in mind two important questions, and answer them for yourself, before deciding to use this system in your game:

1. Is it worth it?  This event system isn't some magical feature that would remove the need for the MU*'s development, and empower immortals to create fabulous things without any control.  Everything that immortals would be able to do through the event system could be achieved by modifying the source code.  Immortals might be familiar with Evennia's design, and could contribute by sending pull requests to your code, for instance.  The event system could admittedly earn you time and have immortals adding in special features without the need for complex code.  You have to consider, however, if it's worth adding this system in your game.  A possible risk is that your immortals will try to do everything though this system and your code will not be updated, while there will still be room to enhance it.
2. Who should use this system?  Having arbitrary Python code running cannot be considered a secure feature.  You will have to be extremely careful in deciding who can use this system.  By default, immortals can create and edit events (these users have access to the `@py` command, which is potentially as dangerous).  Builders will not be able to add or edit events, although you can change this setting, to have builders be able to create events, and set their events to require approval by an administrator.  You can change permissions (see below for more details on how to do it).  You are free to trust or mistrust your builders or other users, just remember that the potential for malign code cannot be restricted.

## Basic structure and vocabulary

- At the basis of the event system are **event types**.  An **event type** defines the context in which we would like to call some arbitrary code.  For instance, one event type is defined on exits and will fire every time a character traverses through this exit.  Event types are described on a [typeclass](https://github.com/evennia/evennia/wiki/Typeclasses) (like [exits](https://github.com/evennia/evennia/wiki/Objects#exits) in our example).  All objects inheriting from this typeclass will have access to this event type.
- An event type should specify a **trigger**, a simple name describing the moment when the event type will be fired.  The event type that will be fired every time a character traverses through an exit is called "traverse".  Both "event types" and "trigger" can describe the same thing, although the term **trigger** in the rest of the documentation will be used to describe the moment when the event fires.  Users of the system will be more interested in knowing what triggers are available for such and such objects, while developers will be there to create event types.
- Individual events can be set on individual objects.  They contain the code that will be executed at a specific moment (when a specific action triggers this event type).  More than one event can be connected to an object's event type: for instance, several events can be set on the "traverse" event type of a single exit.  They will all be called in the order they have been defined.

To see the system in context, when an object is picked up (using the default `get` command), a specific event type is fired:

1. The event type "get" is set on objects (on the `DefaultObject` typeclass).
2. When using the "get" command to pick up an object, this object's `at_get` hook is called.
3. A modified hook of DefaultObject is set by the event system.  This hook will execute (or call) the "get" event type on this object.
4. All events tied to this object's "get" trigger will be executed in order.  These events act as functions containing Python code that you can write, using specific variables that will be listed when you edit the event itself.
5. In individual events, you can add multiple lines of Python code that will be fired at this point.  In this example, the `character` variable will contain the character who has picked up the object, while `obj` will contain the object that was picked up.

Following this example, if you create an event "get" on the object "a sword", and put in it:

```python
character.msg("You have picked up {} and have completed this quest!".format(obj.get_display_name(character)))
```

When you pick up this object you should see something like:

    You pick up a sword.
    You have picked up a sword and have completed this quest!

## Installation

Being in a separate contrib, the event system isn't installed by default.  You need to do it manually, following these steps:

1. Launch the main script:
   ```@py ev.create_script("evennia.contrib.events.scripts.EventHandler")```
2. Set the permissions (optional):
   - `EVENTS_WITH_VALIDATION`: a group that can edit events, but will need approval (default to `None`).
   - `EVENTS_WITHOUT_VALIDATION`: a group with permission to edit events without need of validation (default to `"immortals"`).
   - `EVENTS_VALIDATING`: a group that can validate events (default to `"immortals"`).
   - `EVENTS_CALENDAR`: type of the calendar to be used (either `None`, `"standard"`, `"custom"` or a custom callback, default to `None`).
3. Add the `@event` command.
4. Inherit from the custom typeclasses of the event system.
   - `evennia.contrib.events.typeclasses.EventCharacter`: to replace `DefaultCharacter`.
   - `evennia.contrib.events.typeclasses.EventExit`: to replace `DefaultExit`.
   - `evennia.contrib.events.typeclasses.EventObject`: to replace `DefaultObject`.
   - `evennia.contrib.events.typeclasses.EventRoom`: to replace `DefaultRoom`.

The following sections describe in details each step of the installation.

### Starting the event script

To start the event script, you only need a single command, using `@py`.

    @py ev.create_script("evennia.contrib.events.scripts.EventHandler")

This command will create a global script (that is, a script independent from any object).  This script will hold basic configuration, event description and so on.  You may access it directly, but you will probably use the custom helper functions (see the section on extending the event system).  Doing so will also create a `events` handler on all objects (see below for details).

### Editing permissions

This contrib comes with its own set of permissions.  They define who can edit events without validation, and who can edit events but needs validation.  Validation is a process in which an administrator (or somebody trusted as such) will check the events produced by others and will accept or reject them.  If accepted, the events are connected, otherwise they are never run.

By default, events can only be created by immortals: no one except the immortals can edit events, and immortals don't need validation.  It can easily be changed, either through settings or dynamically by changing permissions of users.

#### Permissions in settings

The events contrib adds three [permissions](https://github.com/evennia/evennia/wiki/Locks#permissions) in the settings.  You can override them by changing the settings into your `server/conf/settings.py` file (see below for an example).  The settings defined in the events contrib are:

- `EVENTS_WITH_VALIDATION`: this defines a permission that can edit events, but will need approval.  If you set this to `"wizards"`, for instance, users with the permission `"wizards"` will be able to edit events.  These events will not be connected, though, and will need to be checked and approved by an administrator.  This setting can contain `None`, meaning that no user is allowed to edit events with validation.
- `EVENTS_WITHOUT_VALIDATION`: this setting defines a permission allowing editing of events without needing validation.  By default, this setting is set to `"immortals"`.  It means that immortals can edit events, and they will be connected when they leave the editor, without needing approval.
- `EVENTS_VALIDATING`: this last setting defines who can validate events.  By default, this is set to `"immortals"`, meaning only immortals can see events needing validation, accept or reject them.

You can override all these settings in your `server/conf/settings.py` file.  For instance:

```python
# ... other settings ...

# Event settings
EVENTS_WITH_VALIDATION = "wizards"
EVENTS_WITHOUT_VALIDATION = "immortals"
EVENTS_VALIDATING = "immortals"
```

This set of settings means that:

1. Wizards can edit events, but they will need to be individually approved before they are connected.  Wizards will be able to add whatever they want, but before their code runs, it will have to be checked and approved by an immortal.
2. Immortals can edit events, their work doesn't need to be approved.  It is automatically accepted and connected.
3. Immortals can also see events that need approval (these produced by wizards) and accept or reject them.  Whenever accepted, the event is connected and will fire without constraint whenever it has to.

In addition, there is another setting that must be set if you plan on using the time-related events (events that are scheduled at specific, in-game times).  You would need to specify the type of calendar you are using.  By default, time-related events are disabled.  You can change the `EVENTS_CALENDAR` to set it to:

- `"standard"`: the standard calendar, with standard days, months, years and so on.
- `"custom"`: a custom calendar that will use the [custom_gametime](https://github.com/evennia/evennia/blob/master/evennia/contrib/custom_gametime.py) contrib to schedule events.
- A special callback to schedule time-related events in a way not supported by the `gametime` utility and the `custom_gametime` contrib (see below).

#### Permissions on individual users

This contrib defines two additional permissions that can be set on individual users:

- `events_without_validation`: this would give this user the rights to edit events but not require validation before they are connected.
- `events_validating`: this permission allows this user to run validation checks on events needing to be validated.

For instance, to give the right to edit events without needing approval to the player 'kaldara', you might do something like:

    @perm *kaldara = events_without_validation

To remove this same permission, just use the `/del` switch:

    @perm/del *kaldara = events_without_validation

The rights to use the `@event` command are directly related to these permissions: by default, only users who have the "events_without_validation" permission or are in (or above) the group defined in the `EVENTS_WITH_VALIDATION` setting will be able to call the commands (with different switches).

### Adding the `@event` command

You also have to add the `@event` command to your Character CmdSet.  In your `commands/default_cmdsets`, it might look like this:

```python
from evennia import default_cmds
from evennia.contrib.events.commands import CmdEvent

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
        self.add(CmdEvent())
```

### Changing parent classes of typeclasses

Finally, to use the event system, you need to have your typeclasses inherit from the modified event typeclasses.  For instance, in your `typeclasses/characters.py` module, you should change inheritance like this:

```python
from evennia.contrib.events.typeclasses import EventCharacter

class Character(EventCharacter):

    # ...
```

You should do the same thing for your rooms, exits and objects.  Note that the event system works by overriding some hooks.  Some of these features might not be accessible in your game if you don't call the parent methods when overriding hooks.

## Using the `@event` command

The event system relies, to a great extent, on its `@event` command.  Who can execute this command, and who can do what with it, will depend on your set of permissions.

The event system can be used on most Evennia objects, mostly typeclassed objects (excluding players).  The first argument of the `@event` command is the name of the object you want to edit.  It can also be used to know what event types are available for this specific object.

### Examining events and event types

To see the event types connected to an object, use the `@event` command and give the name or ID of the object to examine.  For instance, @event here` to examine the event types on your current location.  Or `@event self` to see the event types on yourself.

This command will display a table, containing:

- The name of each event type (trigger) in the first column.
- The number of events of this name, and the number of total lines of these events in the second column.
- A short help to tell you when the event is triggered in the third column.

If you execute `@event #1` for instance, you might see a table like this:

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

### Creating a new event

The `/add` switch should be used to add an event.  It takes two arguments beyond the object's name/DBREF:

1. After an = sign, the trigger of the event to be edited (if not supplied, will display the list of possible triggers, like above).
2. The parameters (optional).

We'll see events with parameters later.  For the time being, let's try to prevent a character from going through the "north" exit of this room:

```
@event north
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

If we want to prevent a character from traversing through this exit, the best trigger for us would be "can_traverse".

> Why not "traverse"?  If you read the description of both triggers, you will see "traverse" is called **after** the character has traversed through this exit.  It would be too late to prevent it.  On the other hand, "can_traverse" is obviously checked before the character traverses.

When we edit the event, we have some more information:

    @event/add north = can_traverse

```
Can the character traverse through this exit?
This event is called when a character is about to traverse this
exit.  You can use the deny() function to deny the character from
exiting for this time.

Variables you can use in this event:
    character: the character that wants to traverse this exit.
    exit: the exit to be traversed.
    room: the room in which stands the character before moving.
```

The section dedicated to [helpers](#the-helper-functions) will elaborate on the `deny()` function and other helpers.  Let us say, for the time being, that it can prevent an action (in this case, it can prevent the character from traversing through this exit).  In the editor that opened when you used `@event/add`, you can type something like:

```python
if character.id == 1:
    character.msg("You're the superuser, 'course I'll let you pass.")
else:
    character.msg("Hold on, what do you think you're doing?")
    deny()
```

You can now enter `:wq` to leave the editor by saving the event.

If you enter `@event north`, you should see that "can_traverse" now has an active event.  You can use `@event north = can_traverse` to see more details on the connected events:

```
@event north = can_traverse
+--------------+--------------+----------------+--------------+--------------+
|       Number | Author       | Updated        | Param        | Valid        |
+~~~~~~~~~~~~~~+~~~~~~~~~~~~~~+~~~~~~~~~~~~~~~~+~~~~~~~~~~~~~~+~~~~~~~~~~~~~~+
|            1 | XXXXX        | 5 seconds ago  |              | Yes          |
+--------------+--------------+----------------+--------------+--------------+
```

The left column contains event numbers.  You can use them to have even more information on a specific event.  Here, for instance:

```
@event north = can_traverse 1
Event can_traverse 1 of north:
Created by XXXXX on 2017-04-02 17:58:05.
Updated by XXXXX on 2017-04-02 18:02:50
This event is connected and active.
Event code:
if character.id == 1:
    character.msg("You're the superuser, 'course I'll let you pass.")
else:
    character.msg("Hold on, what do you think you're doing?")
    deny()
```

Then try to walk through this exit.  Do it with another character if possible, too, to see the difference.

### Editing and removing an event

You can use the `/edit` switch to the `@event` command to edit an event.  You should provide, after the name of the object to edit and the equal sign:

1. The name of the event (as seen above).
2. A number, if several events are connected at this location.

You can type `@event/edit <object> = <event_name>` to see the events that are linked at this location.  If there is only one event, it will be opened in the editor; if more are defined, you will be asked for a number to provide (for instance, `@event/edit north = can_traverse 2`).

The command `@event` also provides a `/del` switch to remove an event.  It takes the same arguments as the `/edit` switch.

When removed, events are logged, so an administrator can retrieve its content, assuming the `/del` was an error.

### The code editor

When adding or editing an event, the event editor should open in code mode.  The additional options supported by the editor in this mode are describe in [a dedicated section of the EvEditor's documentation](https://github.com/evennia/evennia/wiki/EvEditor#the-eveditor-to-edit-code).

## Using events

The following sections describe how to use events for various tasks, from the most simple to the most complex.

### The helper functions

In order to make development a little easier, the event system provides helper functions to be used in events themselves.  You don't have to use them, they are just shortcuts.

Function   | Argument                 | Description                       | Example
-----------|--------------------------|-----------------------------------|--------
deny       | `()`                     | Prevent an action from happening. | `deny()`
get        | `(**kwargs)`             | Get a single object.              | `char = get(id=1)`
call_event | `(obj, name, seconds=0)` | Call another event.               | `call_event(char, "chain_1", 20)`

#### deny

The `deny()` function allows to interrupt the event and the action that called it.  In the `can_*` events, it can be used to prevent the action from happening.  For instance, in `can_say` on rooms, it can prevent the character from saying something in the room.  One could have a `can_eat` event set on food that would prevent this character from eating this food.

Behind the scenes, the `deny()` function raises an exception that is being intercepted by the handler of events.  The handler will then report that the action was cancelled.

#### get

The `get` helper is a shortcut to get a single object with a specific identity.  It's often used to retrieve an object with a given ID.  In the section dedicated to [chained events](#chained-events), you will see a concrete example of this helper in action.

#### call_event

Some events will call others.  It is particularly useful for [chained events](#chained-events) that are described in a dedicated section.  This helper is used to call another event, immediately or in a defined time.

You need to specify as first parameter the object containing the event.  The second parameter is the name of the event to call.  The third parameter is the number of seconds before calling this event.  By default, this parameter is set to 0 (the event is called immediately).

### Variables in events

In the Python code you will enter in individual events, you will have access to variable in your locals.  These variables will depend on the event, and will be clearly listed when you add or edit it.  As you've seen in the previous example, when we manipulate characters or character actions, we often have a `character` variable that holds the character doing the action.

In most cases, when an event type is fired, all events from this event type are called.  Variables are created for each event.  Sometimes, however, the event type will execute and then ask for a variable in your event: in other words, some events can alter the actions being performed by changing values of variables.  This is always clearly specified in the help of the event.

One example that will illustrate this system is the event type "msg_leave" that can be set on exits.  This event can alter the message that will be sent to other characters when someone leave through this exit.

    @event/add down = msg_leave

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

In this case, the event system placed the variable "message" in the event, but will read from it when the event has been executed.

### Events with parameters

Some events are called without parameter.  It has been the case for all examples we have seen before.  In some cases, you can create events that are triggered under only some conditions.  A typical example is the room's "say" event.  This event is triggered when somebody says something in the room.  The event can be configured to fire only when some words are used in the sentence.

For instance, let's say we want to create a cool voice-operated elevator.  You enter into the elevator and say the floor number... and the elevator moves in the right direction.  In this case, we could create an event with the parameter "one":

    @event/add here = say one

This event will only fire when the user says a sentence that contains "one".

But what if we want to have an event that would fire if the user says 1 or one?  We can provide several parameters, separated by a comma.

    @event/add here = say 1, one

Or, still more keywords:

    @event/add here = say 1, one, ground

This time, the user could say something like "take me to the ground floor" ("ground" is one of our keywords defined in the above event).

Not all events can take parameters, and these who do have different ways of handling them.  There isn't a single meaning to parameters that could apply to all events.  Refer to the event documentation for details.

### Time-related events

Events are usually linked to commands,  as we saw before.  However, this is not always the case.  Events can be triggered by other actions and, as we'll see later, could even be called from inside other events!

There is a specific event, on all objects, that can trigger at a specific time.  It's an event with a mandatory parameter, which is the time you expect this event to fire.

For instance, let's add an event on this room that should trigger every day, at precisely 12:00 PM (the time is given as game time, not real time):

```
@event here = time 12:00
```

```python
# This will be called every MUD day at 12:00 PM
room.msg_contents("It's noon, time to have lunch!")
```

Now, at noon every MUD day, this event will fire.  You can use this event on every kind of typeclassed object, to have a specific action done every MUD day at the same time.

Time-related events can be much more complex than this.  They can trigger every in-game hour or more often (it might not be a good idea to have events trigger that often on a lot of objects).  You can have events that run every in-game week or month or year.  It will greatly vary depending on the type of calendar used in your game.  The number of time units is described in the game configuration.

With a standard calendar, for instance, you have the following units: minutes, hours, days, months and years.  You will specify them as numbers separated by either a colon (:), a space ( ), or a dash (-).  Pick whatever feels more appropriate (usually, we separate hours and minutes with a colon, the other units with a dash).

Some examples of syntax:

- `18:30`: every day at 6:30 PM.
- `01 12:00`: every month, the first day, at 12 PM.
- `06-15 09:58`: every year, on the 15th of June (month comes before day), at 9:58 AM.
- `2025-01-01 00:00`: January 1st, 2025 at midnight (obviously, this will trigger only once).

Notice that we specify units in the reverse order (year, month, day, hour and minute) and separate them with logical separators.  The smallest unit that is not defined is going to set how often the event should fire.  That's why, if you use `12:00`, the smallest unit that is not defined is "day": the event will fire every day at the specified time.

> You can use chained events (see below) in conjunction with time-related events to create more random or frequent actions in events.

### Chained events

Events can call other events, either now or a bit later.  It is potentially very powerful.

To use chained events, just use the `call_event` helper function.  It takes 2-3 arguments:

- The object containing the event.
- The name of the event to call.
- Optionally, the number of seconds to wait before calling this event.

All objects have events that are not triggered by commands or game-related operations.  They are called "chain_X", like "chain_1", "chain_2", "chain_3" and so on.  You can give them more specific names, as long as it begins by "chain_", like "chain_flood_room".

Rather than a long explanation, let's look at an example: a subway that will go from one place to the next at regular times.  Creating exits (opening its doors), waiting a bit, closing them, rolling around and stopping at a different station.  That's quite a complex set of events, as it is, but let's only look at the part that opens and closes the doors:

    @event/add here = time 10:00

```python
# At 10:00 AM, the subway arrives in the room of ID 22.
# Notice that exit #23 and #24 are respectively the exit leading
# on the platform and back in the subway.
station = get(id=22)
# Open the door
to_exit = get(id=23)
to_exit.name = "platform"
to_exit.aliases = ["p"]
to_exit.location = room
to_exit.destination = station
# Create the return exit
back_exit = get(id=24)
back_exit.name = "subway"
back_exit.location = station
back_exit.destination = room
# Display some messages
room.msg_contents("The doors open and wind gushes in the subway")
station.msg_contents("The doors of the subway open with a dull clank.")
# Set the doors to close in 20 seconds
call_event(room, "chain_1", 20)
```

This event will:

1. Be called at 10:00 AM (specify 22:00 to say 10:00 PM).
2. Set an exit between the subway and the station.  Notice that the exits already exist (you will not have to create them), but they don't need to have specific location and destination.
3. Display a message both in the subway and on the platform.
4. Call the event "chain_1" to execute in 20 seconds.

And now, what should we have in "chain_1"?

    @event/add here = chain_1

```python
# Close the doors
to_exit.location = None
to_exit.destination = None
back_exit.location = None
back_exit.destination = None
room.msg_content("After a short warning signal, the doors close and the subway begins moving.")
station.msg_content("After a short warning signal, the doors close and the subway begins moving.")
```

Behind the scenes, the `call_event` function freezes all variables ("room", "station", "to_exit", "back_exit" in our example), so you don't need to define them again.

A word of caution on events that call chained events: it isn't impossible for an event to call itself at some recursion level.  If `chain_1` calls `chain_2` that calls `chain_3` that calls `chain_`, particularly if there's no pause between them, you might run into an infinite loop.

Be also careful when it comes to handling characters or objects that may very well move during your pause between event calls.  When you use `call_event()`, the MUD doesn't pause and commands can be entered by players, fortunately.  It also means that, a character could start an event that pauses for awhile, but be gone when the chained event is called.  You need to check that, even lock the character into place while you are pausing (some actions should require locking) or at least, checking that the character is still in the room, for it might create illogical situations if you don't.

## Using events in code

This section describes events and event types from code, how to create new event types, how to call them in a command, and how to handle specific cases like parameters.

Along this section, we will see how to implement the following example: we would like to create a "push" command that could be used to push objects.  Objects could react to this and have specific events fired.

### Adding new event types

Adding new event types should be done below your typeclasses.  For instance, if you want to add a new event type on all your rooms, you should probably edit your `typeclasses/rooms.py` module.  We'll see how to add a "push" event type to all objeects.  To add a new event type, you should use the `create_event_type` function defined in `evennia.contrib.events.custom`.  This function takes 4 arguments.

- The class to have these events (defined above).
- The trigger of the event type to add (str).
- The list of variables to be present when calling this events (list of str).
- The help text of this event (str).

The variables define what will be accessible in the namespace of your event.  Here, when we "push" an object, we would like to know what object is pushed, and who has pushed it (we'll limit this command to characters).  You can edit `typeclasses/objects.py` to modify/add the following lines:

```python
from evennia.contrib.events.custom import create_event_type, connect_event_types
from evennia.contrib.events.typeclasses import EventObject

class Object(EventObject):
    # ...


# Object events
create_event_type(Object, "push", ["character", "obj"], """
    A character push the object.
    This event is called when a character uses the "push" command on
    an object in the same room.

    Variables you can use in this event:
        character: the character that pushes this object.
        obj: the object connected to this event.
""")

# Force-update the new event types
connect_event_types()
```

Here we have set:

1. The typeclass (here, `Object`), meaning that this event will be accessible to all instances of `Object` or a child class.
2. `"push"` as the trigger (the name of the event type).
3. Two variables ("character" and "obj") that will be accessible in our event namespace.
4. A longer help text to describe more in details when this event will fire.  It's best to keep this format as much as possible: a single line to briefly describe the event, a longer explanation on several lines, and the list of variables of this event.

> It's best to call `connect_event_types()` after having defined new event types.  It can be kept for the very last line of the file.  The event system doesn't automatically integrate new event types, this function is to force it to do so.

If you save this code and reload your game, you should see the new event type if you enter the `@event` command with an object as argument.

### Calling an event in code

The event system is accessible through a handler on all objects.  This handler is named `events` and can be accessed from any typeclassed object (your character, a room, an exit...).  This handler offers several methods to examine and call an event type on this object.

To call an event, use the `events.call` method in an object.  It takes as argument:

- The name of the event type to call.
- All variables that will be accessible in the event as positional arguments.  They should be specified in the order chosen when [creating new event types](#adding-new-event-types).

Following the same example, so far, we have created an event type on all objects, called "push".  This event type is never fired for the time being.  We could add a "push" command, taking as argument the name of an object.  If this object is valid, it will call its "push" event type.

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

        # Call the "push" event type of this object
        obj.events.call("push", self.caller, obj)
```

Here we use `events.call` with the following arguments:

- `"push"`: the name of the event type to be called.
- `self.caller`: the one who pushed the button (this is our first variable, `character`).
- `obj`: the object being pushed (our second variable, `obj`).

In the "push" event of our objects, we then can use the "character" variable (containing the one who pushed the object), and the "obj" variable (containing the object that was pushed).

### See it all work

To see the effect of the two modifications above (the added event type and the "push" command), let us create a simple object:

    @create/drop rock
    @desc rock = It's a single rock, apparently pretty heavy.  Perhaps you can try to push it though.
    @event/add rock = push

In the event you could write:

```python
from random import randint
number = randint(1, 6)
character.msg("You push a rock... is... it... going... to... move?")
if number == 6:
    character.msg("The rock topples over to reveal a beautiful ant-hill!")
```

You can now try to "push rock".  You'll try to push the rock, and once out of six times, you will see a message about a "beautiful ant-hill".

### Adding new helper functions

Helper functions, like `deny(), are defined in `contrib/events/helpers.py`.  You can add your own helpers by creating a file named `event_helpers.py` in your `world` directory.  The functions defined in this file will be added as helpers.

You can also decide to create your helper functions in another location, or even in several locations.  To do so, edit the `EVENTS_HELPERS_LOCATIONS` setting in your `server/conf/settings.py` file, specifying either a python path or a list of Python paths in which your helper functions are defined.  For instance:

```python
EVENTS_HELPERS_LOCATIONS = [
        "world.events.helpers",
]
```

## Disabling all events at once

When events are running in an infinite loop, for instance, or sending unwanted information to players or other sources, you, as the game administrator, have the power to restart without events.  The best way to do this is to use a custom setting, in your setting file (`server/conf/settings.py`):

```python
# Disable all events
EVENTS_DISABLED = True
```

The event system will still be accessible (you will have access to the `@event` command, to debug), but no event will be called automatically.

