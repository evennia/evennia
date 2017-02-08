# Evennia event system

Vincent Le Goff 2017

This contrib adds the system of events in Evennia, allowing immortals (or other trusted builders) to dynamically add features to individual objects.  Using events, every immortal (or trusted builders) could have a specific room, exit, character, object or something else behaves differently from its "cousins".  For these familiar with the use of softcode in MU*, like SMAUG MudProgs, the ability to add arbitrary behavior to individual objects is a step toward freedom.  Keep in mind, however, the warning below, and read it carefully before the rest of the documentation.

## A WARNING REGARDING SECURITY

Evennia's event system will run arbitrary Python code without much restriction.  Such a system is as powerful as potentially dangerous, and you will have to keep in mind two important questions, and answer them for yourself, before deciding to use this system in your game:

1. Is it worth it?  This event system isn't some magical feature that would remove the need for the MUD's development, and empower immortals to create fabulous things without any control.  Everything that immortals would be able to do through the event system could be achieved by modifying the source code.  Immortals might be familiar with Evennia's design, and could contribute by sending pull requests to your code, for instance.  The event system could admittedly earn you time and have immortals (or trusted builders) adding in special features without the need for complex code.  You have to consider, however, if it's worth adding this system in your game.  A possible risk is that your immortals will try to do everything though this system and your code will not be updated, while there will still be room to enhance it.
2. Is it safe? Having arbitrary Python code running cannot be considered a secure feature.  You will have to be extremely careful in deciding who can use this system.  By default, immortals can create and edit events (these users have access to the `@py` command, which is potentially as dangerous).  Builders will not be able to add or edit events, although you can change this setting, to have builders be able to create events, although their events will require approval by an administrator to be run.  You can change permissions (see below for more details on how to do it).  You are free to trust or mistrust your builders or other users, just remember that the potential for malign code cannot be restricted.

## Some basic examples

Before deciding to install this system, it might be worth understanding its possibilities and basic features.  The event system allows to create events that can be fired at specific moments.  For instance, checking beforehand if a character has some characteristics before allowing him/her to walk through an exit.  You will find some examples here (of course, this is only a set of examples, you could do so much more through this system):

    Edit the event 'can_traverse' of a specific exit:
        if character.db.health < 30:
            character.msg("You are obviously too weak to do that.")
            deny()
        else: # That's really opional here, but why not?
            character.msg("Alrigh, you can go.")

The `deny()` function denies character from moving and so, after the message has been sent, the action is cancelled (he/she doesn't move).  The `else:` statement and instructions are, as in standard Python, optional here.

    Edit the event 'eat' of a specific object:
        if character.db.race != "orc":
            character.msg("This is a nice-tasting apple, as juicy as you'd like.")
        else:
            character.msg("You bite into the apple... and spit it out!  Do people really eat that?!")
            character.db.health -= 10

This time, we have an event that behaves differently when a character eats an apple... and is an orc, or something else.  Notice that the race system will need to be in your game, the event system just provides ways to access your regular Evennia objects and attributes.

    Edit the event 'time' of a specific NPC with the parameter '19:45':
        cmd(character, "say Well, it's time to go home, folks!")
        unlock(room, "up")
        move(character, "up")
        lock(room, "up")

For this example, at 19:45 sharp (MUD time), the NPC leaves.  It can be useful for a shopkeeper to just go in his/her room to sleep, and comeback in the morning.

    Edit the event 'describe' of a specific room with the parameter 'light':
        if time("5:00 6:00"):
            text = "The gray light of dawn slowly spreads over the harbor.")
        elif time("6:00 12:00"):
            text = "The sun shines brightly on the waters of the small harbor.")
        elif time("12:00 18:00"):
            text = "Lengthening shadows fall on the water as the sun continues its course.")
        elif time("18:00 21:00"):
            text = "Sunset shines on the calm waters of this small harbor.")
        else:
            text = "It's pitch dark, you can hardly see your hands and hear the gently sound of waves.")

The description of the room could look something like:

    This is a street made out of wooden planks, running along the
    harbor that spreads south from here.  To the north is a steep
    street that leads deeper into the small city.  $light

When the character looks at this description, the `$light` will be replaced by a specific sentence that will change depending on MUD time.  You can have different parts of the room description that will update regarding different factors, like the health of the character looking at the description, the weather surrounding this room, the fulfillment of a quest, the presence of a NPC, and so on.  This can be used on every object that supports descriptions.

You will find more examples in this documentation, along with clear indications on how to use this feature in context.

## Installation

The event system isn't installed by default.  If you want to use it, you first have to install it.  This is done through editing your code:

In your game settings, you should import the event system.  All it takes to do is a simple:

    import contrib.events

You can do this anywhere in your code, but it's more logical to do it in your settings file (`server/conf/settings.py`).  You might prefer to do it in your startup file (`server/conf/at_server_startstop.py`).

The `@event` command will be added to your character command set.  You can, as usual, decide to customize the command and replace the older version in your command set.

## Basic usage

The event system relies, to a great extent, on its `@event` command.  By default, immortals will be the only ones to have access to this command, for obvious security reasons.  You can customize it to be opened to wizards, with or without validation.  A section of this document explains how to change this setting.

### The `@event` command

The event system can be used on most Evennia objects, mostly typeclassed objects (rooms, exits, characters, objects, and the ones you want to add to your game, players don't use this system however).  The first argument of the `@event` command is the name of the object you want to edit.

#### Examining events

Let's say we are in a room with two exist, north and south.  You could see what events are currently linked with the `north` exit by entering:

    @event north

The object to display or edit is searched in the room, by default, which makes editing rather easy.  However, you can also provide its DBREF (a number) after a `#` sign, like this:

    @event #1

(In most settings, this will show the events linked with the character 1, the superuser.)

The `#DBREF` syntax allows you to edit objects from a distance, without having to move into the rom where these objects are present.

By default, if you try this command on an object that doesn't have any event, it should display something like:

    No event has been defined in TYPE DISPLAY_NAME.

If there are events linked to this object, you will see them in a table (with the event and the number of line).

#### Creating a new event

The `/add` switch should be used to add an event.  It takes two arguments beyond the object's name/DBREF:

1. After an = sign, the event to be edited (if not supplied, will display the list of possible events).
2. The parameters (optional).

We'll see events with parameters later.  For now, let's create an event 'can_traverse' connected to the exit 'north' in this room:

    @event/add north = can_traverse

This will create a new event connected to this exit.  It will be fired before a character traverses this exit.  It is possible to prevent the character from moving at this point.

This command should open a line-editor.  This editor is described in greater details in another section.  For now, you can write instructions as normal:

    if character.id == 1:
        character.msg("You're the superuser, 'course I'll let you pass.")
    else:
        character.msg("Hold on, what do you think you're doing?")
        deny()

You can now enter `:wq` to leave the editor by saving the event.

Then try to walk through this exit.  Do it with another character if possible, too, to see the difference.

If you are immortal, by default, this command should automatically connect the event, and activate it.  You can set some wizards/builders to be allowed to add events, but to validate individual events each time, to make sure they are using the system with no harmful intents.  These events will be created, but they will not be connected before you validate them.

#### Editing an event

You can use the `/edit` switch to the `@event` command to edit an event.  You should provide, after the name of the object to edit and the equal sign:

1. The name of the event (as seen above).
2. A number, if several events are connected at this location.

You can type `@event/edit <object> = <event_name>` to see the events that are linked at this location.  If there is only one event, it will be opened in the editor; if more are defined, you will be asked for a number to provide (for instance, `@event/edit north can_traverse 2`).

Users under validation will be able to edit their own events, but not the events of others.  Editing an event that went into validation will disconnect it and have it sent to validation again.

#### Removing an event

The command `@event` also provides a `/del` switch to remove an event.  It takes the same arguments as the `/edit` switch:

1. The name of the object.
2. The name of the event after an = sign.
3. Optionally a number if more than one event are located there.

When removed, events are logged, so an administrator can retrieve its content, assuming the `/del` was an error and the administrator has access to log files (which is often the case).

### The event editor

When adding or editing an event, the event editor should open.  It is basically the same as [EvEditor](https://github.com/evennia/evennia/wiki/EvEditor), which so ressemble VI, but it adds a couple of options to handle indentation.

Python is a programming language that needs correct indentation.  It is not an aesthetic concern, but a requirement to differentiate between blocks.  The event editor will try to guess the right level of indentation to make your life easier, but it will not be perfect.

- If you enter an instruction beginning by `if`, `elif`, or `else`, the editor will automatically increase the level of indentation of the next line.
- If the instruction is an `elif` or `else`, the editor will look for the opening block of `if` and match indentation.
- Blocks `while`, `for`, `try`, `except`, 'finally' obey the same rules.

There are still some cases when you must tell the editor to reduce or increase indentation.  The usual use cases are:

1. When you close a condition or loop, the editor will not be able to tell.
2. When you want to keep the instruction on several lines, the editor will not bother with indentation.

In both cases, you should use the `:+` command (increase indentation by one level) and `:-` (decrease indentation by one level).  Indentation is always shown when you add a new line in your event.

In all the cases shown above, you don't need to enter your indentation manually.  Just change the indentation whenever needed, don't bother to write spaces or tabulations at the beginning of your line.  For instance, you could enter the following lines in your client:

```
if character.id == 1:
character.msg("You're the big boss.")
else:
character.msg("I don't know who you are.")
:-
character.msg("This is not inside of the condition.")
```

This will produce the following code:

```
if character.id == 1:
    character.msg("You're the big boss.")
else:
    character.msg("I don't know who you are.")

character.msg("This is not inside of the condition.")
```

You can also disable the automatic-indentation mode.  Just enter the command `:=`.  In this mode, you will have to manually type in the spaces or tabulations, the editor will not indent anything without you asking to do it.  This mode can be useful if you copy/paste some code and want to keep the original indentation.

### Editing permissions

This contrib is installed with default permissions.  They define who can edit events without validation, and who can edit events but needs validation.  Validation is a process in which an administrator (or somebody trusted as such) will check the events produced by others and will accept or reject them.  If accepted, the events are connected, otherwise they are never run.

By default, events can only be created by immortals.  They don't need to be validated by anyone, after all, immortals also have access to the `@py` command, so they are probably trusted to use it wisely and not to run dangerous code on your server.

That's the default configuration: no one except the immortals can edit events, and immortals don't need validation.  It can easily be changed, either through settings or dynamically by changing permissions of users.

#### Permissions in settings

The events contrib adds three permissions in the settings.  You can override them by importing the settings into your `server/conf/settings.py` file (see below for an example).  The settings defined in the events contrib are:

- `EVENTS_WITH_VALIDATION`: this defines a group that can edit events, but will need approval.  If you set this to "wizards", for instance, users with the permission "wizards" will be able to edit events.  These events will not be connected, though, and will need to be checked and approved by an administrator.  This setting can contain `None`, meaning that no group is allowed to edit events with validation.
- `EVENTS_WITHOUT_VALIDATION`: this setting defines a permission allowing editing of events without needing validation.  By default, this setting is set to "immortals".  It means that immortals can edit events, and they will be connected when they leave the editor, without needing approval.
- `EVENTS_VALIDATING`: this last setting defines who can validate events.  By default, this is set to "immortals", meaning only immortals can see events needing validation, accept or reject them.

You can override all these settings in your `server/conf/settings.py` file.  For instance:

```
from evennia.contrib.events import *

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

#### Permissions on individual users

Sometimes, you have learned to know a contributor and wish to give him or her more privilege without upgrading him/her to a new group.  For instance, there's a wizard that you have known for years: you don't know him/her well enough to promote him/her as an immortal, but you are sure he/she won't use the event system with harmful intents.  You can give permissions to individual players through the `@perm` command, not altering their group (and then, not giving them extra commands), but allowing them to create events without validation.  There are two permissions you can give to individual users:

- `events_without_validation`: this would give this user the rights to edit events but not require validation before they are connected.  If you do this on an individual basis, keep in mind the power granted to this user and carefully consider the potential impacts on your game or machine.
- `events_validating`: this permission allows this user to run validation checks on events needing to be validated.  In practice, you shouldn't have to use this last permission, if you trust a user enough to run that path, perhaps he/she could be trusted with immortal permissions.

For instance, to give the right to edit events without needing approval to the player 'kaldara', you might do something like:

    @perm *kaldara = events_without_validation

To remove this same permission, just use the `/del` switch:

    @perm/del *kaldara = events_without_validation

The rights to use the `@event` command are directly related to these permissions: by default, only users who have the "events_without_validation" permission or are in (or above) the group defined in the `EVENTS_WITH_VALIDATION` setting will be able to call the commands (with different switches).

## Using events

The following sub-sections describe how to use events for various tasks, from the most simple to the most complex.

### Standard Python code in events

This might sound superfluous, considering the previous explanations, but remember you can use standard Python code in your events.  Everything that you could do in the source code itself, like changing attributes or aliases, creating or removing objects, can be done through this system.  What you will see in the following sub-sections doesn't rely on a new syntax of Python: they add functions and some features, at the best.  Events aren't written in softcode, and their syntax might, at first glance, be a bit unfriendly to a user without any programming skills.  However, he or she will probably grasp the basic concept very quickly, and will be able to move beyond simple events in his or her own time.

### The helper functions

In order to make development a little easier, the event system provides helper functions to be used in events themselves.  You don't have to use them, they are just shortcuts.

The `deny()` function is such a helper.  It allows to interrupt the event and the action that called it.  In the `can_*` events, it can be used to prevent the action from happening.  For instance, in `can_traverse` on exits, it can prevent the user from moving in that direction.  One could have a `can_eat` event set on food that would prevent this player to eat this food.  Or a `can_say` event in a room that would prevent the player from saying something here.

Behind the scene, the `deny()` function raises an exception that is being intercepted by the handler of events.  Calling this function in events that cannot be stopped may result in errors.

You could easily add other helper functions.  This will greatly depend on the objects you have defined in your game, and how often specific features have to be used by event users.  You will find a list of helper functions, their syntax and examples, in the documentation on events.

### Events with parameters

Some events are called without parameter.  For instance, when a character traverses through an exit, the exit's "traverse" event is called with no argument.  In some cases, you can create events that are triggered in only some conditions.  A typical example is the room's "say" event.  This event is triggered when somebody says something in the room.  The event can be configured to fire only when some words are used in the sentence.

For instance, let's say we want to create a cool voice-operated elevator.  You enter into the elevator and say the floor number... and the elevator moves in the right direction.  In this case, we could create an event with the parameter "one":

    @event/add here = say one

This event will only fire when the user says "one" in this room.

But what if we want to have an event that would fire if the user says 1 or one?  We can provide several parameters, separated by a comma.

    @event/add here = say 1, one

Or, still more keywords:

    @event/add here = say 1, one, ground

This time, the user could say "ground" or "one" in the room, and it would fire the event.

Not all events can take parameters, and these who do have a different ways of handling them.  There isn't a single meaning to parameters that could apply to all events.  Refer to the event documentation for details.

### Memory handling

One frequent question when dealing with events would be in storing information for a latter use.  We could, of course, write in the object's attributes themselves, but it might be messy and conflict with code-related features.  Memories are here to store information, temporarily or permanently.  Since memory is a feature of the event system, when some information changes, adequate events are also triggered, which allows very advanced information handling.

Memories use a set of helper function that will be described in more details here:

- `add_memory`: add an information on an object.
- `del_memory`: remove this memory (now or later).
- `memory`: retrieve the value of the memory stored here.
- `has_memory`: has this object stored this memory?

#### The basics of memories

Memories are just pieces of information that will be stored in a dedicated field.  Just like attributes, these memories contain a key and a value.  The key must be a unique string to identify the place where this memory is stored.

Memories can be stored on every typeclassed object.  A character, a room, an object, even an exit can all have memories.

Let's take a room for a first example.  You have an event, `enter`, that is called when a character enters the room.  You could decide to store this character, and retrieve it later.  Having rooms know the last character who entered can be useful in specific features.  So let's see how to do it:

```
@event/add here = enter
add_memory(room, "last_character", character)
```

This very short event will store the character who enters the room, in a memory called "last_character".

So far, you might not see the point of memories.  Why not use attributes directly?  Here are some answers:

- Memories are tracked down by their own monitors.  It means, whenever a memory is added, updated or deleted, events are fired.  You can have specific code that will run in these cases, we'll see why it can be interesting later.
- Memories can have a limited lifetime: a memory can expire at some point (you're going to set that using `del_memory`, we'll see how in the following section).  You don't have to do anything at this point.

These two features make memories pretty powerful.  And keep in mind that they won't conflict with attributes, since they aren't stored in the same place.

#### Expiring memories

One reason why they are called memories is that they can expire.  You can set a memory to be permanently-stored (that's the default), or to expire in some time.  For instance, a NPC could remember the characters that have attacked and fled it... but only for awhile.  A shopkeeper could remember who has attempted to kill hi/her, but given some days, he/she will forget.

To create an expiring memory, use the `del_memory` function.  By default, it just takes the object and the key of the memory.  Using the previous example, we could delete the memory in our room like this:

```
del_memory(room, "last_character")
```

But it can also take a third parameter: the number of seconds before the memory is deleted.

```
del_memory(room, "last_character", 300)
```

This time, the memory will not be destroyed before 300 seconds (5 minutes).

#### Reactive memories

When memories are modified, specific events are called on the object.  They are:

- `add_memory`: a memory has just been added.
- `change_memory`: the value of the memory has been changed.
- `del_memory`: a memory has just been deleted.

How useful is it?  Consider, for example, an object that we will create, a cup of hot tea.  We could so easily make it become colder as time passes.

```
@event cup of tea = create
# This event will be called when the cup of tea is created
add_memory(object, "temperature", 100)
# We'll say the cup is 100°F when it's created
del_memory(object, "temperature", 20)
# The memory will be erased in 20 seconds
:wq

@event cup of tea = del_memory temperature
# Note that this event will only be called when the "temperature"
# memory is deleted. 'value' contains the value of the memory
# being deleted.
value -= 5
# Remove 5 degrees
add_memory(object, "temperature", value)
# Add the memory again
if value > 5:
    # If the temperature is above 5, continues to decrease.
    del_memory(object, "temperature", 20)

# Why not change the name according to the temperature?
if value > 70:
    object.key = "a hot cup of tea"
elif value > 60:
    object.key = "a reasonably-warm cup of tea"
elif value > 40:
    object.key = "a cup of tea a bit too cool"
else:
    object.key = "a cup of tea positevely cold"
:wq
```

Let's take these two events in the order they fire:

1. First, you create a cup of tea.  The memory "temperature" is set to 100.
2. 20 seconds later, the memory is deleted automatically, and the `del_memory` event is called.  In this event, we remove 5 degrees from the value and write the memory "temperature" again.  So 20 seconds after the cup has been created, the memory "temperature" will be 95.  20 seconds later, 90.  20 seconds later, 85... and so on.
3. The name of the object will vary depending on temperature.
4. When the temperature reaches 5, it stops dropping.  It's already rather cold, isn't it?

One more time, events like this one can be very powerful and come in very useful.  You will have to decide, however, if you don't want to create drinks with a "dropping temperature" automatically.  Events are great for creating individual features, but code is better to create features used by many.

### Time-related events

Events are usually linked to commands.  As we saw before with the `del_memory` event, however, this is not always the case.  Events can be triggered by other actions and, as we'll see later, could even be called from inside of other events!

There is a specific event, on all objects, that can trigger at a specific time.  It's an event with a mandatory argument, which is the time you expect this event to fire.

For instance, let's add an event on this room that should trigger every day, at precisely 12:00 PM (the time is given as game time, not real time):

```
@event here = time 12:00
# This will be called every MUD day at 12:00 PM
room.msg_content("It's noon, time to have lunch!")
```

When you save the event, assuming it is auto-validated, at noon every MUD day, this event will fire.  You can use this event on every kind of typeclassed object, to have a specific action done every MUD day at the same time.

### Chained events

Events can call other events, either now or a bit later.  It is potentially very powerful.

To use chained events, just use the `call` helper function.  It takes 2-3 arguments:

- The object containing the event.
- The name of the event to call.
- Optionally, the number of seconds to wait before calling this event.

All objects have events that are not triggered by commands or game-related operations.  They are called "chain_X", like "chain_1", "chain_2", "chain_3" and so on.  You can give them more specific names, as long as it begins by "chain_", like "chain_flood_room".

Rather than a long explanation, let's look at an example: a subway that will go from one place to the next at regular times.  Creating exits (opening its doors), waiting a bit, closing them, rolling around and stopping at a different station.  That's quite a complex set of events, as it is, but let's only look at the part that opens and closes the doors:

```
@event here = time 10:00
# At 10:00 AM, the subway arrives in the room of ID 22
station = room(id=22)
# Open the door
create_exit("east", room, station)
# Rename the exits
rename_exit(room, "east", "doors", aliases="platform")
rename_exit(station, "west", "doors", aliases="subway")
room.msg_content("The doors open and wind gushes in the subway")
station.msg_content("The doors of the subway open with a dull clank.")
# Set the doors to close in 20 seconds
call(room, "chain_1", 20)
```

This event will:

1. Be called at 10:00 AM (specify 22:00 to say 10:00 PM).
2. Create an exit between the subway (room) and the station (room of ID 22).
3. Renames the exits (it's prettier, let's admit it).
4. Display a message both in the subway and on the platform.
5. Call the event "chain_1" to execute in 20 seconds.

And now, what should we have in "chain_1"?

```
@event here = chain_1
# Close the doors
del_exit(room, "doors")
room.msg_content("After a short warning signal, the doors close and the subway begins moving.")
station.msg_content("After a short warning signal, the doors close and the subway begins moving.")
```

Behind the scene, the `call` function freezes all variables ("room" and "station" in our example), so you don't need to define them afterward.

A word of caution on events that call chained events: it isn't impossible for an event to call itself at some recursion level.  If `chain_1` calls `chain_2` that calls `chain_3` that calls `chain_`, particularly if there's no pause between them, you might run into an infinite loop.

Be also careful when it comes to handling characters or objects that may very well move during your pause between event calls.  When you use `call()`, the MUD doesn't pause and commands can be entered by players, fortunately.  It also means that, a character could start an event that pauses for awhile, but be gone when the chained event is called.  You need to check that, even lock the character into place while you are pausing (some actions should require locking) or at least, checking that the character is still in the room, for it might create illogical situations if you don't.

### Events in descriptions

Events can also be used to add dynamic elements into descriptions.  The way to use them is to have a single word in the description preceded by a $ sign.  The event system will attempt to retrieve the event called "describe" with the mandatory argument of the word that follows the $ sign.

For instance, if you have the description:

    This is a plain that looks $color.

The $color indicates to the event system that this is a dynamic portion of the description.  The event system will look for this object's "describe" event that has the parameter "color".  It will call it and expect it to create a "text" variable that will replace the $color:

```
@event here = describe color
if time("22:00 5:00"):
    text = "quite indistinct in the dark"
else:
    text = "a bit sinister, even in broad daylight"
```

When you'll look at this description, if it's between 10 PM and 5 AM, you should see:

    This is a plain that looks quite indistinct in the dark.

If not, it should display:

    This is a plain that looks a bit sinister, even in broad daylight.

You can have several dynamic indicators in your description, as long as you have the matching event that defines the "text" variable.

#### Hooks in description

To alter descriptions, the event system relies on some hooks that can be overridden.  In practice, it is not unlikely that you would have already overriden these hooks and wonder why your descriptions are still static.  You can use the method `get_description` in your object to retrieve the `db.desc` attribute with dynamic parts being replaced by the event system.

In your overridden hooks, instead of using something like:

    desc = self.db.desc

Use:

    desc = self.get_description()

That should effectively and effortlessly resolve the issue.

## Extending events

This section is dedicated to game developers more than users of the event system.  It will explain how to add new helper functions and events.  You can skip this section if these topics don't interest you, and see how you can debug your events in the next section.

### Adding new helper functions

Helper functions, like `deny()` or `create_exit`, are defined in `contrib/events/helpers.py`.  You can add your own helpers by creating a file named `helpers.py` in your `world` directory.  The functions defined in this file will be added as helpers.  Note that the docstring of each function will be used to generate automatic help.

You can also decide to create your helper functions in another location, or even in several locations.  To do so, edit the `EVENTS_HELPERS_LOCATIONS` setting in your `server/conf/settings.py` file, specifying either a python path or a list of Python paths in which your helper functions are defined.  For instance:

```
EVENTS_HELPERS_LOCATIONS = [
        "word/events/helpers",
]
```

A helper function is really a Python function.  Its docstring should be sufficiently elaborate, so the automatically-generated help of your helpers would prove as usable as the default helpers.

### Adding new typeclasses

This section will need to be described more in details, on how to add new typeclasses and, most importantly, how to define their events and how to call them.

## Debugging events

In a perfect world, there wouldn't be any bug, any need for debugging.  Such, as you know, isn't the case.  Sometimes, we need to debug events, in order to understand why it doesn't act as we thought.

### Examining an event's execution

Describe the debug mode of individual objects.

### Errors in events

There are a lot of ways to make mistakes while writing events.  Once you begin, you might encounter syntax errors very often, but leave them behind as you gain in confidence.  However, there are still so many ways to trigger errors:  passing the wrong arguments to a helper function is only one of many possible examples.

When an event encounters an error, it stops abruptly and sends the error on a special channel, named "everror", on which you can connect or disconnect should the amount of information be overhwelming.  These error messages will contain:

- The name and ID of the object that encountered the error.
- The name of the event, with possible parameters, that crashed.
- The short error messages (it might not be that short at times).

The error will also be logged, so an administrator can still access it more completely, seeing the full traceback, which can help to understand the error sometimes.

### Disabling all events at once

Last resort, when events are running in an infinite loop, for instance, or sending unwanted information to players or other sources, you, as the game administrator, have the power to restart without events.  One way to do this will be to uninstall the event system, and you can simply comment the line that imports it in your settings.  However, if you have imported the system in different files, that might be a bit annoying.  You can disable the event system in your `server/conf/at_server_startstop.py` file, in your `at_server_start()` function.

```
from contrib.events.controls import disable_events

def at_server_start():
    """
    This is called every time the server starts up, regardless of
    how it was shut down.
    """
    disable_events()
```

One advantage of this solution is that you will still have access to the `@event` command.  Actually, all features of the event system will be available... except no event will fire.  This includes description events, time-related events, chained events and normal events.  You can then look at the list of events that were modified recently, it might give you an idea of which one is causing all this fuss.
