# Evennia's event system, user documentation

Evennia's event system allows to add dynamic features in your world without editing the source code.  These features are placed on individual objects, and can offer opportunities to customize a few objects without customizing all of them.  Usages can range from:

- Adding dialogues to some characters (a NPC greeting player-characters).
- Adding some custom actions at specific in-game moments (a shop-keeper going home at 8 PM and coming back to the shop in the morning).
- Build complex quests (a set of actions with conditions required to obtain some reward or advantage).
- Deny a command from executing based on some conditions (prevent a character from going in some room without completing some quest).
- Have some objects react in specific ways when some action occurs (a character enters the room, a character says something).

In short, the event system allows what other engines would implement through soft code or "scripting".  The event system in Evennia doesn't rely on a homemade language, however, but on Python, and therefore allows almost everything possible through modifications to the source code.  It's not necessary to know Evennia to use the event system, although knowing some basis of Evennia (the system of typeclasses and attributes, for instance) will not hurt.

## Some basic examples

Before beginning to use this system, it might be worth understanding its possibilities and basic features.  The event system allows to create events that can be fired at specific moments.  For instance, checking beforehand if a character has some characteristics before allowing him/her to walk through an exit.  You will find some examples here (of course, this is only a list of examples, you could do so much more through this system):

    Edit the event 'can_traverse' of a specific exit:
        if character.db.health < 30:
            character.msg("You are obviously too weak to do that.")
            deny()
        else: # That's really opional here, but why not?
            character.msg("Alrigh, you can go.")

The `deny()` function denies characters from moving and so, after the message has been sent, the action is cancelled (he/she doesn't move).  The `else:` statement and instructions are, as in standard Python, optional here.

    Edit the event 'eat' of a specific object:
        if character.db.race != "goblin":
            character.msg("This is a nice-tasting apple, as juicy as you'd like.")
        else:
            character.msg("You bite into the apple... and spit it out!  Do people really eat that?!")
            character.db.health -= 10

This time, we have an event that behaves differently when a character eats an apple... and is a goblin, or something else.  Notice that the race system will need to be in your game, the event system just provides ways to access your regular Evennia objects and attributes.

    Edit the event 'time' of a specific NPC with the parameter '19:45':
        character.execute_cmd("say Well, it's time to go home, folks!")
        exit = character.location.search("up")

        exit.db.lock = False
        exit.db.closed = False
        move(character, "up")
        exit.db.closed = True
        exit.db.lock = True

For this example, at 19:45 sharp (game time), the NPC leaves.  It can be useful for a shop-keeper to just go in his/her room to sleep, and comeback in the morning.

You will find more examples in this documentation, along with clear indications on how to use this feature in context.

## Basic usage

The event system relies, to a great extent, on its `@event` command.  By default, immortals will be the only ones to have access to this command, for obvious security reasons.

### The `@event` command

The event system can be used on most Evennia objects, mostly typeclassed objects (rooms, exits, characters, objects, and the ones you want to add to your game, players don't use this system however).  The first argument of the `@event` command is the name of the object you want to edit.

#### Examining events

Let's say we are in a room with two exist, north and south.  You could see what events are currently linked with the `north` exit by entering:

    @event north

The object to display or edit is searched in the room, by default, which makes editing rather easy.  However, you can also provide its DBREF (a number) after a `#` sign, like this:

    @event #1

(In most settings, this will show the events linked with the character 1, the superuser.)

This command will display a table, containing:

- The name of each event in the first column.
- The number of events of this name, and the number of total lines of these events in the second column.
- A short help to tell you when the event is triggered in the third column.

Notice that several events can be linked at the same location.  For instance, you can have several events in an exit's "can_traverse" event: each event will be called in the order and each can prevent the character from going elsewhere.

You can see the list of events of each name by using the same command, specifying the name of the event after an equal sign:

    @event south = can_traverse

If you have more than one event of this name, they will be shown in a table with numbers starting from 1.  You can examine a specific event by providing the number after the event's name:

    @event south = can_traverse 1

This command will allow you to examine the event more closely, including seeing its associated code.

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

#### Editing an event

You can use the `/edit` switch to the `@event` command to edit an event.  You should provide, after the name of the object to edit and the equal sign:

1. The name of the event (as seen above).
2. A number, if several events are connected at this location.

You can type `@event/edit <object> = <event_name>` to see the events that are linked at this location.  If there is only one event, it will be opened in the editor; if more are defined, you will be asked for a number to provide (for instance, `@event/edit north = can_traverse 2`).

#### Removing an event

The command `@event` also provides a `/del` switch to remove an event.  It takes the same arguments as the `/edit` switch:

1. The name of the object.
2. The name of the event after an = sign.
3. Optionally a number if more than one event are located there.

When removed, events are logged, so an administrator can retrieve its content, assuming the `/del` was an error and the administrator has access to log files.

### The event editor

When adding or editing an event, the event editor should open.  It is basically the same as [EvEditor](https://github.com/evennia/evennia/wiki/EvEditor), which so ressemble VI, but it adds a couple of options to handle indentation.

Python is a programming language that needs correct indentation.  It is not an aesthetic concern, but a requirement to differentiate between blocks.  The event editor will try to guess the right level of indentation to make your life easier, but it will not be perfect.

- If you enter an instruction beginning by `if`, `elif`, or `else`, the editor will automatically increase the level of indentation of the next line.
- If the instruction is an `elif` or `else`, the editor will look for the opening block of `if` and match indentation.
- Blocks `while`, `for`, `try`, `except`, 'finally' obey the same rules.

There are still some cases when you must tell the editor to reduce or increase indentation.  The usual use cases are:

1. When you close a condition or loop, the editor will not be able to tell.
2. When you want to keep the instruction on several lines, the editor will not bother with indentation.

In both cases, you should use the `:>` command (increase indentation by one level) and `:<` (decrease indentation by one level).  Indentation is always shown when you add a new line in your event.

In all the cases shown above, you don't need to enter your indentation manually.  Just change the indentation whenever needed, don't bother to write spaces or tabulations at the beginning of your line.  For instance, you could enter the following lines in your client:

```
if character.id == 1:
character.msg("You're the big boss.")
else:
character.msg("I don't know who you are.")
:<
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

## Using events

The following sub-sections describe how to use events for various tasks, from the most simple to the most complex.

### Standard Python code in events

This might sound superfluous, considering the previous explanations, but remember you can use standard Python code in your events.  Everything that you could do in the source code itself, like changing attributes or aliases, creating or removing objects, can be done through this system.  What you will see in the following sub-sections doesn't rely on a new syntax of Python: they add functions and some features, at the best.  Events aren't written in softcode, and their syntax might, at first glance, be a bit unfriendly to a user without any programming skills.  However, you will probably grasp the basic concept very quickly, and will be able to move beyond simple events in good time.  Don't overlook examples, in this documentation, or in your game.

### The helper functions

In order to make development a little easier, the event system provides helper functions to be used in events themselves.  You don't have to use them, they are just shortcuts.

The `deny()` function is such a helper.  It allows to interrupt the event and the action that called it.  In the `can_*` events, it can be used to prevent the action from happening.  For instance, in `can_traverse` on exits, it can prevent the user from moving in that direction.  One could have a `can_eat` event set on food that would prevent this character from eating this food.  Or a `can_say` event in a room that would prevent the character from saying something here.

Behind the scene, the `deny()` function raises an exception that is being intercepted by the handler of events.  Calling this function in events that cannot be stopped may result in errors.

You could easily add other helper functions.  This will greatly depend on the objects you have defined in your game, and how often specific features have to be used by event users.

### Variables in events

Most events have variables.  Variables are just Python variables.  As you've seen in the previous example, when we manipulate characters or character actions, we often have a `character` variable that holds the character doing the action.  The list of variables can change between events, and is always available in the help of the event.  When you edit or add a new event, you'll see the help: read it carefully until you're familiar with this event, since it will give you useful information beyond the list of variables.

Sometimes, variables in events can also be set to contain new directions.  One simple example is the exits' "msg_leave" event, that is called when a character leaves a room through this exit.  This event is executed and you can set a custom message when a character walks through this exit, which can sometimes be useful:

    @event/add down = msg_leave
        message = "{character} falls into a hole in the ground!"

Then, if the character Wilfred takes this story, others in the room will see:

    Wildred falls into a hole in the ground!

### Events with parameters

Some events are called without parameter.  For instance, when a character traverses through an exit, the exit's "traverse" event is called with no argument.  In some cases, you can create events that are triggered under only some conditions.  A typical example is the room's "say" event.  This event is triggered when somebody says something in the room.  The event can be configured to fire only when some words are used in the sentence.

For instance, let's say we want to create a cool voice-operated elevator.  You enter into the elevator and say the floor number... and the elevator moves in the right direction.  In this case, we could create an event with the parameter "one":

    @event/add here = say one

This event will only fire when the user says "one" in this room.

But what if we want to have an event that would fire if the user says 1 or one?  We can provide several parameters, separated by a comma.

    @event/add here = say 1, one

Or, still more keywords:

    @event/add here = say 1, one, ground

This time, the user could say "ground" or "one" in the room, and it would fire the event.

Not all events can take parameters, and these who do have a different ways of handling them.  There isn't a single meaning to parameters that could apply to all events.  Refer to the event documentation for details.

### Time-related events

Events are usually linked to commands.  As we saw before, however, this is not always the case.  Events can be triggered by other actions and, as we'll see later, could even be called from inside other events!

There is a specific event, on all objects, that can trigger at a specific time.  It's an event with a mandatory argument, which is the time you expect this event to fire.

For instance, let's add an event on this room that should trigger every day, at precisely 12:00 PM (the time is given as game time, not real time):

```
@event here = time 12:00
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

Notice that we specify units in the reverse order (year, month, day, hour and minute) and separate them with logical separators.  The smallest unit that is not defined is going to set how often the event should fire.  That's why, if you use `12:00`, the smallest unit that is not defined is "day": the event will fire every day at the specific time.

> You can use chained events (see below) in conjunction with time-related events to create more random or frequent actions in events.

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
call(room, "chain_1", 20)
```

This event will:

1. Be called at 10:00 AM (specify 22:00 to say 10:00 PM).
2. Set an exit between the subway and the station.  Notice that the exits already exist (you will have to create them), but they don't need to have specific location and destination.
3. Display a message both in the subway and on the platform.
4. Call the event "chain_1" to execute in 20 seconds.

And now, what should we have in "chain_1"?

```
@event here = chain_1
# Close the doors
to_exit.location = None
to_exit.destination = None
back_exit.location = None
back_exit.destination = None
room.msg_content("After a short warning signal, the doors close and the subway begins moving.")
station.msg_content("After a short warning signal, the doors close and the subway begins moving.")
```

Behind the scene, the `call` function freezes all variables ("room", "station", "to_exit, "back_exit" in our example), so you don't need to define them afterward.

A word of caution on events that call chained events: it isn't impossible for an event to call itself at some recursion level.  If `chain_1` calls `chain_2` that calls `chain_3` that calls `chain_`, particularly if there's no pause between them, you might run into an infinite loop.

Be also careful when it comes to handling characters or objects that may very well move during your pause between event calls.  When you use `call()`, the MUD doesn't pause and commands can be entered by players, fortunately.  It also means that, a character could start an event that pauses for awhile, but be gone when the chained event is called.  You need to check that, even lock the character into place while you are pausing (some actions should require locking) or at least, checking that the character is still in the room, for it might create illogical situations if you don't.

## Errors in events

There are a lot of ways to make mistakes while writing events.  Once you begin, you might encounter syntax errors very often, but leave them behind as you gain in confidence.  However, there are still so many ways to trigger errors:  passing the wrong arguments to a helper function is only one of many possible examples.

When an event encounters an error, it stops abruptly and sends the error on a special channel, named "everror", on which you can connect or disconnect should the amount of information be overwhelming.  These error messages will contain:

- The name and ID of the object that encountered the error.
- The name and number of the event that crashed.
- The line number (and code) that caused the error.
- The short error messages (it might not be that short at times).

The error will also be logged, so an administrator can still access it more completely, seeing the full traceback, which can help to understand the error sometimes.

