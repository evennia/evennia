# Evennia event system

Vincent Le Goff 2017

This contrib adds the system of events in Evennia, allowing immortals (or other trusted builders) to dynamically add features to individual objects.  Using events, every immortal (or trusted builders) could have a specific room, exit, character, object or something else behaves differently from its "cousins".  For these familiar with the use of softcode in MU*, like SMAUG MudProgs, the ability to add arbitrary behavior to individual objects is a step toward freedom.  Keep in mind, however, the warning below, and read it carefully before the rest of the documentation.

## A WARNING REGARDING SECURITY

Evennia's event system will run arbitrary Python code without much restriction.  Such a system is as powerful as potentially dangerous, and you will have to keep in mind two important questions, and answer them for yourself, before deciding to use this system in your game:

1. Is it worth it?  This event system isn't some magical feature that would remove the need for the MU*'s development, and empower immortals to create fabulous things without any control.  Everything that immortals would be able to do through the event system could be achieved by modifying the source code.  Immortals might be familiar with Evennia's design, and could contribute by sending pull requests to your code, for instance.  The event system could admittedly earn you time and have immortals (or trusted builders) adding in special features without the need for complex code.  You have to consider, however, if it's worth adding this system in your game.  A possible risk is that your immortals will try to do everything though this system and your code will not be updated, while there will still be room to enhance it.
2. Is it safe?  Having arbitrary Python code running cannot be considered a secure feature.  You will have to be extremely careful in deciding who can use this system.  By default, immortals can create and edit events (these users have access to the `@py` command, which is potentially as dangerous).  Builders will not be able to add or edit events, although you can change this setting, to have builders be able to create events, and set their events to require approval by an administrator.  You can change permissions (see below for more details on how to do it).  You are free to trust or mistrust your builders or other users, just remember that the potential for malign code cannot be restricted.

## Installation

Being in a separate contrib, the event system isn't installed by default.  You need to do it manually, following three steps:

1. Launch the main script: the event system is contained in a general script that holds all data.  It has the advantage of saving nothing in your objects, and you can decide to turn it on and off fairly easily.  In order to turn events on, you need to activate the script.  Once executed, the script will remain, including after server reset or reload:
   ```@py ev.create_script("evennia.contrib.events.scripts.EventHandler")```
2. Set the permissions: the event system uses some custom permissions that you can set to define who is allowed to do what, and to what extent (see below for details).  Most of these settings will be stored in your setting file (`server/conf/settings.py`):
   - `EVENTS_WITH_VALIDATION`: a group that can edit events, but will need approval (default to `None`).
   - `EVENTS_WITHOUT_VALIDATION`: a group with permission to edit events without need of validation (default to `"immortals"`).
   - `EVENTS_VALIDATING`: a group that can validate events (default to `"immortals"`).
   - `EVENTS_CALENDAR`: type of the calendar to be used (either `None`, `"standard"`, `"custom"` or a custom callback, default to `None`).
3. Adding the `@event` command: finally, you will need to add the `@event` command to your Character CmdSet.  As with the two previous steps, this is to be done only once: you can disable the event system without removing the `@event` command (a section will describe how useful it can be in case of errors).

### Starting the event script

To start the event script, you only need a single command, using `@py`.

    @py ev.create_script("evennia.contrib.events.scripts.EventHandler")

This command will create a global script (that is, a script independent from any object).  This script will hold basic configuration, event description and so on.  You may access it directly, but you will probably use the custom helper functions (see the section on extending the event system).

### Editing permissions

This contrib is installed with default permissions.  They define who can edit events without validation, and who can edit events but needs validation.  Validation is a process in which an administrator (or somebody trusted as such) will check the events produced by others and will accept or reject them.  If accepted, the events are connected, otherwise they are never run.

By default, events can only be created by immortals.  They don't need to be validated by anyone, after all, immortals also have access to the `@py` command, so they are probably trusted to use it wisely and not to run dangerous code on your server.

That's the default configuration: no one except the immortals can edit events, and immortals don't need validation.  It can easily be changed, either through settings or dynamically by changing permissions of users.

#### Permissions in settings

The events contrib adds three permissions in the settings.  You can override them by changing the settings into your `server/conf/settings.py` file (see below for an example).  The settings defined in the events contrib are:

- `EVENTS_WITH_VALIDATION`: this defines a group that can edit events, but will need approval.  If you set this to "wizards", for instance, users with the permission "wizards" will be able to edit events.  These events will not be connected, though, and will need to be checked and approved by an administrator.  This setting can contain `None`, meaning that no group is allowed to edit events with validation.
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

If you have an active staff of immortals, or are yourself sufficiently active on your project and have some contributors, you might decide to grant the privilege to write events **with** validation to builders, for instance (wizards, as the above permission, will automatically be included).  It is recommended not to give contributors the right to edit events without validation unless you know, for a fact, that you can trust them.  Remember, events have the potential to do many things... including freeze or crash your server... and potentially worse.

In addition, there is another setting that must be set if you plan on using the time-related events (events that are scheduled at specific, in-game times).  You would need to specify the type of calendar you are using.  By default, time-related events are disabled.  You can change the `EVENTS_CALENDAR` to set it to:

- `"standard"`: the standard calendar, with standard days, months, years and so on.
- `"custom"`: a custom calendar that will use the `custom_gametime` contrib to schedule events.
- A special callback to schedule time-related events in a way not supported by the `gametime` utility and the `custom_gametime` contrib (see below).

#### Permissions on individual users

Sometimes, you have learned to know a contributor and wish to give him or her more privilege without upgrading him/her to a new group.  For instance, there's a wizard that you have known for years: you don't know him/her well enough to promote him/her as an immortal, but you are sure he/she won't use the event system with harmful intents.  You can give permissions to individual players through the `@perm` command, not altering their group (and then, not giving them extra commands), but allowing them to create events without validation.  There are two permissions you can give to individual users:

- `events_without_validation`: this would give this user the rights to edit events but not require validation before they are connected.  If you do this on an individual basis, keep in mind the power granted to this user and carefully consider the potential impacts on your game or machine.
- `events_validating`: this permission allows this user to run validation checks on events needing to be validated.  In practice, you shouldn't have to use this last permission, if you trust a user enough to run that path, perhaps he/she could be trusted with immortal permissions.

For instance, to give the right to edit events without needing approval to the player 'kaldara', you might do something like:

    @perm *kaldara = events_without_validation

To remove this same permission, just use the `/del` switch:

    @perm/del *kaldara = events_without_validation

The rights to use the `@event` command are directly related to these permissions: by default, only users who have the "events_without_validation" permission or are in (or above) the group defined in the `EVENTS_WITH_VALIDATION` setting will be able to call the commands (with different switches).

### Adding the `@event` command

You also have to add the `@event` command to your Character CmdSet.  In your `commands/default_cmdsets`, you might have something like:

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

## Extending events

This section will explain how to add new helper functions and events.

### Adding new event types

Default events are great but you may need more events to fit with your purposes.  For instance, if you have a `yell` command and would like a `can_yell` event in all your rooms.

The way to do this is to add, below your class definition, lines to add these events.  The `create_event_type` function should be called.  It takes the following arguments:

- The class to have these events (defined above).
- The name of the event to add (str).
- The list of variables to be present when calling this events (list of str).
- The help text of this event (str).

Here's an example of adding the `can_yell` event to all your rooms:

```python
# In typeclasses/rooms.py
from evennia import DefaultRoom
from evennia.contrib.events.custom import create_event_type

class Room(DefaultRoom):
    """
    Rooms are like any Object, except their location is None
    (which is default). They also use basetype_setup() to
    add locks so they cannot be puppeted or picked up.
    (to change that, use at_object_creation instead)

    See examples/object.py for a list of
    properties and methods available on all Objects.
    """
    pass

# Room events
create_event_type(Room, "can_yell", ["character", "room", "message"], """
        Can the character yell in this room?
        This event is called when a character uses the 'yell' command
        to yell in this room.  This event is called BEFORE the character
        yells, and the room can prevent the command by executing
        'deny()'.  The 'character' variable contains the character
        who wants to yell, the 'room' variable contains the room
        in which the character wants to yell, and the 'message'
        variable contains the message about to be yelled by the character.
""")
```

After this code has been executed, when you type `@event here` to see the events in this room, you will see the `can_yell` event.  The first line of the help text is displayed as a short explanation, so you should always try to format your help files that way.

At this point, the event has been added, but is not being called yet.  To call it, you need to edit your `yell` command, and use the `call` function.  You will probably end up with something like:

```python
from evennia import Command
from evennia.contrib.events.helpers import call

class CmdYell(Command):

    """
    Yell in this room.

    Usage:
        yell <message>

    """

    def func(self):
        """Execute the command."""
        character = self.caller
        location = character.location
        message = self.args

        # Check that the character can yell in this room
        if not call(location, "can_yell", character, location, message):
            # It has been denied, so stop the command here
            return

        # Yell in this room
        location.msg_contents("{char} yells: {msg}.",
                mapping=dict(char=character, msg=message))
```

Note that the `call` function takes as argument:

- The object with the event (here, `location`).
- The name of the event to be called (here, `can_yell`).
- The variables as positional arguments, in the same order they were specified in `create_event`.

The `call` function will return `False` if the event has been interrupted by a `deny()` call.

### Adding new helper functions

Helper functions, like `deny(), are defined in `contrib/events/helpers.py`.  You can add your own helpers by creating a file named `helpers.py` in your `world` directory.  The functions defined in this file will be added as helpers.  Note that the docstring of each function will be used to generate automatic help.

You can also decide to create your helper functions in another location, or even in several locations.  To do so, edit the `EVENTS_HELPERS_LOCATIONS` setting in your `server/conf/settings.py` file, specifying either a python path or a list of Python paths in which your helper functions are defined.  For instance:

```python
EVENTS_HELPERS_LOCATIONS = [
        "world.events.helpers",
]
```

A helper function is really a Python function.  Its docstring should be sufficiently elaborate, so the automatically-generated help of your helpers would prove as usable as the default helpers.

### Adding new typeclasses

Adding a new typeclass is not different from ing one, and will obey to the same rules: define the class as you have been accustomed to doing, and create the events with `create_event` under the class definition.

Note: events obey the inheritance hierarchy: if you define events on the `Room` class, then create a typeclass inheriting from `Room`, the objects of this latter typeclass will have events of both typeclasses.

## Disabling all events at once

When events are running in an infinite loop, for instance, or sending unwanted information to players or other sources, you, as the game administrator, have the power to restart without events.  The best way to do this is to use a custom setting, in your setting file (`server/conf/settings.py`):

```python
# Disable all events
EVENTS_DISABLED = True
```

The event system will still be accessible (you will have access to the `@event` command, to debug), but no event will be called automatically.

