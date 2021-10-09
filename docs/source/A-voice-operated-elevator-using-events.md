# A voice operated elevator using events


- Previous tutorial: [Adding dialogues in events](./Dialogues-in-events)

This tutorial will walk you through the steps to create a voice-operated elevator, using the [in-
game Python
system](https://github.com/evennia/evennia/blob/master/evennia/contrib/ingame_python/README.md).
This tutorial assumes the in-game Python system is installed in your game.  If it isn't, you can
follow the installation steps given in [the documentation on in-game
Python](https://github.com/evennia/evennia/blob/master/evennia/contrib/ingame_python/README.md), and
come back on this tutorial once the system is installed.  **You do not need to read** the entire
documentation, it's a good reference, but not the easiest way to learn about it.  Hence these
tutorials.

The in-game Python system allows to run code on individual objects in some situations.  You don't
have to modify the source code to add these features, past the installation.  The entire system
makes it easy to add specific features to some objects, but not all.

> What will we try to do?

In this tutorial, we are going to create a simple voice-operated elevator.  In terms of features, we
will:

- Explore events with parameters.
- Work on more interesting callbacks.
- Learn about chained events.
- Play with variable modification in callbacks.

## Our study case

Let's summarize what we want to achieve first.  We would like to create a room that will represent
the inside of our elevator.  In this room, a character could just say "1", "2" or "3", and the
elevator will start moving.  The doors will close and open on the new floor (the exits leading in
and out of the elevator will be modified).

We will work on basic features first, and then will adjust some, showing you how easy and powerfully
independent actions can be configured through the in-game Python system.

## Creating the rooms and exits we need

We'll create an elevator right in our room (generally called "Limbo", of ID 2).  You could easily
adapt the following instructions if you already have some rooms and exits, of course, just remember
to check the IDs.

> Note: the in-game Python system uses IDs for a lot of things.  While it is not mandatory, it is
good practice to know the IDs you have for your callbacks, because it will make manipulation much
quicker.  There are other ways to identify objects, but as they depend on many factors, IDs are
usually the safest path in our callbacks.

Let's go into limbo (`#2`) to add our elevator.  We'll add it to the north.  To create this room,
in-game you could type:

    tunnel n = Inside of an elevator

The game should respond by telling you:

    Created room Inside of an elevator(#3) of type typeclasses.rooms.Room.
    Created Exit from Limbo to Inside of an elevator: north(#4) (n).
    Created Exit back from Inside of an elevator to Limbo: south(#5) (s).

Note the given IDs:

- `#2` is limbo, the first room the system created.
- `#3` is our room inside of an elevator.
- `#4` is the north exit from Limbo to our elevator.
- `#5` is the south exit from an elevator to Limbo.

Keep these IDs somewhere for the demonstration.  You will shortly see why they are important.

> Why have we created exits to our elevator and back to Limbo?  Isn't the elevator supposed to move?

It is.  But we need to have exits that will represent the way inside the elevator and out.  What we
will do, at every floor, will be to change these exits so they become connected to the right room.
You'll see this process a bit later.

We have two more rooms to create: our floor 2 and 3.  This time, we'll use `dig`, because we don't
need exits leading there, not yet anyway.

    dig The second floor
    dig The third floor

Evennia should answer with:

    Created room The second floor(#6) of type typeclasses.rooms.Room.
    Created room The third floor(#7) of type typeclasses.rooms.Room.

Add these IDs to your list, we will use them too.

## Our first callback in the elevator

Let's go to the elevator (you could use `tel #3` if you have the same IDs I have).

This is our elevator room.  It looks a bit empty, feel free to add a prettier description or other
things to decorate it a bit.

But what we want now is to be able to say "1", "2" or "3" and have the elevator move in that
direction.

If you have read [the previous tutorial about adding dialogues in events](./Dialogues-in-events), you
may remember what we need to do.  If not, here's a summary: we need to run some code when somebody
speaks in the room.  So we need to create a callback (the callback will contain our lines of code).
We just need to know on which event this should be set.  You can enter `call here` to see the
possible events in this room.

In the table, you should see the "say" event, which is called when somebody says something in the
room.  So we'll need to add a callback to this event.  Don't worry if you're a bit lost, just follow
the following steps, the way they connect together will become more obvious.

    call/add here = say 1, 2, 3

1. We need to add a callback.  A callback contains the code that will be executed at a given time.
So we use the `call/add` command and switch.
2. `here` is our object, the room in which we are.
3. An equal sign.
4. The name of the event to which the callback should be connected.  Here, the event is "say".
Meaning this callback will be executed every time somebody says something in the room.
5. But we add an event parameter to indicate the keywords said in the room that should execute our
callback.  Otherwise, our callback would be called every time somebody speaks, no matter what.  Here
we limit, indicating our callback should be executed only if the spoken message contains "1", "2" or
"3".

An editor should open, inviting you to enter the Python code that should be executed.  The first
thing to remember is to read the text provided (it can contain important information) and, most of
all, the list of variables that are available in this callback:

```
Variables you can use in this event:

    character: the character having spoken in this room.
    room: the room connected to this event.
    message: the text having been spoken by the character.

----------Line Editor [Callback say of Inside of an elevator]---------------------
01|
----------[l:01 w:000 c:0000]------------(:h for help)----------------------------
```

This is important, in order to know what variables we can use in our callback out-of-the-box.  Let's
write a single line to be sure our callback is called when we expect it to:

```python
character.msg(f"You just said {message}.")
```

You can paste this line in-game, then type the `:wq` command to exit the editor and save your
modifications.

Let's check.  Try to say "hello" in the room.  You should see the standard message, but nothing
more.  Now try to say "1".  Below the standard message, you should see:

    You just said 1.

You can try it.  Our callback is only called when we say "1", "2" or "3".  Which is just what we
want.

Let's go back in our code editor and add something more useful.

    call/edit here = say

> Notice that we used the "edit" switch this time, since the callback exists, we just want to edit
it.

The editor opens again.  Let's empty it first:

    :DD

And turn off automatic indentation, which will help us:

    :=

> Auto-indentation is an interesting feature of the code editor, but we'd better not use it at this
point, it will make copy/pasting more complicated.

## Our entire callback in the elevator

So here's the time to truly code our callback in-game.  Here's a little reminder:

1. We have all the IDs of our three rooms and two exits.
2. When we say "1", "2" or "3", the elevator should move to the right room, that is change the
exits.  Remember, we already have the exits, we just need to change their location and destination.

It's a good idea to try to write this callback yourself, but don't feel bad about checking the
solution right now.  Here's a possible code that you could paste in the code editor:

```python
# First let's have some constants
ELEVATOR = get(id=3)
FLOORS = {
    "1": get(id=2),
    "2": get(id=6),
    "3": get(id=7),
}
TO_EXIT = get(id=4)
BACK_EXIT = get(id=5)

# Now we check that the elevator isn't already at this floor
floor = FLOORS.get(message)
if floor is None:
    character.msg("Which floor do you want?")
elif TO_EXIT.location is floor:
    character.msg("The elevator already is at this floor.")
else:
    # 'floor' contains the new room where the elevator should be
    room.msg_contents("The doors of the elevator close with a clank.")
    TO_EXIT.location = floor
    BACK_EXIT.destination = floor
    room.msg_contents("The doors of the elevator open to {floor}.",
            mapping=dict(floor=floor))
```

Let's review this longer callback:

1. We first obtain the objects of both exits and our three floors.  We use the `get()` eventfunc,
which is a shortcut to obtaining objects.  We usually use it to retrieve specific objects with an
ID.  We put the floors in a dictionary.  The keys of the dictionary are the floor number (as str),
the values are room objects.
2. Remember, the `message` variable contains the message spoken in the room.  So either "1", "2", or
"3".  We still need to check it, however, because if the character says something like "1 2" in the
room, our callback will be executed.  Let's be sure what she says is a floor number.
3. We then check if the elevator is already at this floor.  Notice that we use `TO_EXIT.location`.
`TO_EXIT` contains our "north" exit, leading inside of our elevator.  Therefore, its `location` will
be the room where the elevator currently is.
4. If the floor is a different one, have the elevator "move", changing just the location and
destination of both exits.
   - The `BACK_EXIT` (that is "north") should change its location.  The elevator shouldn't be
accessible through our old floor.
   - The `TO_EXIT` (that is "south", the exit leading out of the elevator) should have a different
destination.  When we go out of the elevator, we should find ourselves in the new floor, not the old
one.

Feel free to expand on this example, changing messages, making further checks.  Usage and practice
are keys.

You can quit the editor as usual with `:wq` and test it out.

## Adding a pause in our callback

Let's improve our callback.  One thing that's worth adding would be a pause: for the time being,
when we say the floor number in the elevator, the doors close and open right away.  It would be
better to have a pause of several seconds.  More logical.

This is a great opportunity to learn about chained events.  Chained events are very useful to create
pauses.  Contrary to the events we have seen so far, chained events aren't called automatically.
They must be called by you, and can be called after some time.

- Chained events always have the name "chain_X".  Usually, X is a number, but you can give the
chained event a more explicit name.
- In our original callback, we will call our chained events in, say, 15 seconds.
- We'll also have to make sure the elevator isn't already moving.

Other than that, a chained event can be connected to a callback as usual.  We'll create a chained
event in our elevator, that will only contain the code necessary to open the doors to the new floor.

    call/add here = chain_1

The callback is added to the "chain_1" event, an event that will not be automatically called by the
system when something happens.  Inside this event, you can paste the code to open the doors at the
new floor.  You can notice a few differences:

```python
TO_EXIT.location = floor
TO_EXIT.destination = ELEVATOR
BACK_EXIT.location = ELEVATOR
BACK_EXIT.destination = floor
room.msg_contents("The doors of the elevator open to {floor}.",
        mapping=dict(floor=floor))
```

Paste this code into the editor, then use `:wq` to save and quit the editor.

Now let's edit our callback in the "say" event.  We'll have to change it a bit:

- The callback will have to check the elevator isn't already moving.
- It must change the exits when the elevator move.
- It has to call the "chain_1" event we have defined.  It should call it 15 seconds later.

Let's see the code in our callback.

    call/edit here = say

Remove the current code and disable auto-indentation again:

    :DD
    :=

And you can paste instead the following code.  Notice the differences with our first attempt:

```python
# First let's have some constants
ELEVATOR = get(id=3)
FLOORS = {
    "1": get(id=2),
    "2": get(id=6),
    "3": get(id=7),
}
TO_EXIT = get(id=4)
BACK_EXIT = get(id=5)

# Now we check that the elevator isn't already at this floor
floor = FLOORS.get(message)
if floor is None:
    character.msg("Which floor do you want?")
elif BACK_EXIT.location is None:
    character.msg("The elevator is between floors.")
elif TO_EXIT.location is floor:
    character.msg("The elevator already is at this floor.")
else:
    # 'floor' contains the new room where the elevator should be
    room.msg_contents("The doors of the elevator close with a clank.")
    TO_EXIT.location = None
    BACK_EXIT.location = None
    call_event(room, "chain_1", 15)
```

What changed?

1. We added a little test to make sure the elevator wasn't already moving.  If it is, the
`BACK_EXIT.location` (the "south" exit leading out of the elevator) should be `None`.  We'll remove
the exit while the elevator is moving.
2. When the doors close, we set both exits' `location` to `None`.  Which "removes" them from their
room but doesn't destroy them.  The exits still exist but they don't connect anything.  If you say
"2" in the elevator and look around while the elevator is moving, you won't see any exits.
3. Instead of opening the doors immediately, we call `call_event`.  We give it the object containing
the event to be called (here, our elevator), the name of the event to be called (here, "chain_1")
and the number of seconds from now when the event should be called (here, `15`).
4. The `chain_1` callback we have created contains the code to "re-open" the elevator doors.  That
is, besides displaying a message, it reset the exits' `location` and `destination`.

If you try to say "3" in the elevator, you should see the doors closing.  Look around you and you
won't see any exit.  Then, 15 seconds later, the doors should open, and you can leave the elevator
to go to the third floor.  While the elevator is moving, the exit leading to it will be
inaccessible.

> Note: we don't define the variables again in our chained event, we just call them.  When we
execute `call_event`, a copy of our current variables is placed in the database.  These variables
will be restored and accessible again when the chained event is called.

You can use the `call/tasks` command to see the tasks waiting to be executed.  For instance, say "2"
in the room, notice the doors closing, and then type the `call/tasks` command.  You will see a task
in the elevator, waiting to call the `chain_1` event.

## Changing exit messages

Here's another nice little feature of events: you can modify the message of a single exit without
altering the others.  In this case, when someone goes north into our elevator, we'd like to see
something like: "someone walks into the elevator." Something similar for the back exit would be
great too.

Inside of the elevator, you can look at the available events on the exit leading outside (south).

    call south

You should see two interesting rows in this table:

```
| msg_arrive       |   0 (0) | Customize the message when a character        |
|                  |         | arrives through this exit.                    |
| msg_leave        |   0 (0) | Customize the message when a character leaves |
|                  |         | through this exit.                            |
```

So we can change the message others see when a character leaves, by editing the "msg_leave" event.
Let's do that:

    call/add south = msg_leave

Take the time to read the help.  It gives you all the information you should need.  We'll need to
change the "message" variable, and use custom mapping (between braces) to alter the message.  We're
given an example, let's use it.  In the code editor, you can paste the following line:

```python
message = "{character} walks out of the elevator."
```

Again, save and quit the editor by entering `:wq`.  You can create a new character to see it leave.

    charcreate A beggar
    tel #8 = here

(Obviously, adapt the ID if necessary.)

    py self.search("beggar").move_to(self.search("south"))

This is a crude way to force our beggar out of the elevator, but it allows us to test.  You should
see:

    A beggar(#8) walks out of the elevator.

Great!  Let's do the same thing for the exit leading inside of the elevator.  Follow the beggar,
then edit "msg_leave" of "north":

    call/add north = msg_leave

```python
message = "{character} walks into the elevator."
```

Again, you can force our beggar to move and see the message we have just set.  This modification
applies to these two exits, obviously: the custom message won't be used for other exits.  Since we
use the same exits for every floor, this will be available no matter at what floor the elevator is,
which is pretty neat!

## Tutorial F.A.Q.

- **Q:** what happens if the game reloads or shuts down while a task is waiting to happen?
- **A:** if your game reloads while a task is in pause (like our elevator between floors), when the
game is accessible again, the task will be called (if necessary, with a new time difference to take
into account the reload).  If the server shuts down, obviously, the task will not be called, but
will be stored and executed when the server is up again.
- **Q:** can I use all kinds of variables in my callback?  Whether chained or not?
- **A:** you can use every variable type you like in your original callback.  However, if you
execute `call_event`, since your variables are stored in the database, they will need to respect the
constraints on persistent attributes.  A callback will not be stored in this way, for instance.
This variable will not be available in your chained event.
- **Q:** when you say I can call my chained events something else than "chain_1", "chain_2" and
such, what is the naming convention?
- **A:** chained events have names beginning by "chain_".  This is useful for you and for the
system.  But after the underscore, you can give a more useful name, like "chain_open_doors" in our
case.
- **Q:** do I have to pause several seconds to call a chained event?
- **A:** no, you can call it right away.  Just leave the third parameter of `call_event` out (it
will default to 0, meaning the chained event will be called right away).  This will not create a
task.
- **Q:** can I have chained events calling themselves?
- **A:** you can.  There's no limitation.  Just be careful, a callback that calls itself,
particularly without delay, might be a good recipe for an infinite loop.  However, in some cases, it
is useful to have chained events calling themselves, to do the same repeated action every X seconds
for instance.
- **Q:** what if I need several elevators, do I need to copy/paste these callbacks each time?
- **A:** not advisable.  There are definitely better ways to handle this situation.  One of them is
to consider adding the code in the source itself.  Another possibility is to call chained events
with the expected behavior, which makes porting code very easy.  This side of chained events will be
shown in the next tutorial.

- Previous tutorial: [Adding dialogues in events](./Dialogues-in-events)
