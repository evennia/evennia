# Dialogues in events


- Next tutorial: [adding a voice-operated elevator with events](./A-voice-operated-elevator-using-events).

This tutorial will walk you through the steps to create several dialogues with characters, using the [in-game Python system](https://github.com/evennia/evennia/blob/master/evennia/contrib/ingame_python/README.md).  This tutorial assumes the in-game Python system is installed in your game.  If it isn't, you can follow the installation steps given in [the documentation on in-game Python](https://github.com/evennia/evennia/blob/master/evennia/contrib/ingame_python/README.md), and come back on this tutorial once the system is installed.  **You do not need to read** the entire documentation, it's a good reference, but not the easiest way to learn about it.  Hence these tutorials.

The in-game Python system allows to run code on individual objects in some situations.  You don't have to modify the source code to add these features, past the installation.  The entire system makes it easy to add specific features to some objects, but not all.  This is why it can be very useful to create a dialogue system taking advantage of the in-game Python system.

> What will we try to do?

In this tutorial, we are going to create a basic dialogue to have several characters automatically respond to specific messages said by others.

## A first example with a first character

Let's create a character to begin with.

    @charcreate a merchant

This will create a merchant in the room where you currently are.  It doesn't have anything, like a description, you can decorate it a bit if you like.

As said above, the in-game Python system consists in linking objects with arbitrary code.  This code will be executed in some circumstances.  Here, the circumstance is "when someone says something in the same room", and might be more specific like "when someone says hello".  We'll decide what code to run (we'll actually type the code in-game).  Using the vocabulary of the in-game Python system, we'll create a callback: a callback is just a set of lines of code that will run under some conditions.

You can have an overview of every "conditions" in which callbacks can be created using the `@call` command (short for `@callback`).  You need to give it an object as argument.  Here for instance, we could do:

    @call a merchant

You should see a table with three columns, showing the list of events existing on our newly-created merchant.  There are quite a lot of them, as it is, althougn no line of code has been set yet.  For our system, you might be more interested by the line describing the `say` event:

    | say              |   0 (0) | After another character has said something in |
    |                  |         | the character's room.                         |

We'll create a callback on the `say` event, called when we say "hello" in the merchant's room:

    @call/add a merchant = say hello

Before seeing what this command displays, let's see the command syntax itself:

- `@call` is the command name, `/add` is a switch.  You can read the help of the command to get the help of available switches and a brief overview of syntax.
- We then enter the object's name, here "a merchant".  You can enter the ID too ("#3" in my case), which is useful to edit the object when you're not in the same room.  You can even enter part of the name, as usual.
- An equal sign, a simple separator.
- The event's name.  Here, it's "say".  The available events are displayed when you use `@call` without switch.
- After a space, we enter the conditions in which this callback should be called.  Here, the conditions represent what the other character should say.  We enter "hello".  Meaning that if someone says something containing "hello" in the room, the callback we are now creating will be called.

When you enter this command, you should see something like this:

```
After another character has said something in the character's room.
This event is called right after another character has said
something in the same location.  The action cannot be prevented
at this moment.  Instead, this event is ideal to create keywords
that would trigger a character (like a NPC) in doing something
if a specific phrase is spoken in the same location.

To use this event, you have to specify a list of keywords as
parameters that should be present, as separate words, in the
spoken phrase.  For instance, you can set a callback that would
fire if the phrase spoken by the character contains "menu" or
"dinner" or "lunch":
    @call/add ... = say menu, dinner, lunch
Then if one of the words is present in what the character says,
this callback will fire.

Variables you can use in this event:
    speaker: the character speaking in this room.
    character: the character connected to this event.
    message: the text having been spoken by the character.
```

That's some list of information.  What's most important to us now is:

- The "say" event is called whenever someone else speaks in the room.
- We can set callbacks to fire when specific keywords are present in the phrase by putting them as additional parameters.  Here we have set this parameter to "hello".  We can have several keywords separated by a comma (we'll see this in more details later).
- We have three default variables we can use in this callback: `speaker` which contains the character who speaks, `character` which contains the character who's modified by the in-game Python system (here, or merchant), and `message` which contains the spoken phrase.

This concept of variables is important.  If it makes things more simple to you, think of them as parameters in a function: they can be used inside of the function body because they have been set when the function was called.

This command has opened an editor where we can type our Python code.

```
----------Line Editor [Callback say of a merchant]--------------------------------
01| 
----------[l:01 w:000 c:0000]------------(:h for help)----------------------------
```

For our first test, let's type something like:

```python
character.location.msg_contents("{character} shrugs and says: 'well, yes, hello to you!'", mapping=dict(character=character))
```

Once you have entered this line, you can type `:wq` to save the editor and quit it.

And now if you use the "say" command with a message containing "hello":

```
You say, "Hello sir merchant!"
a merchant(#3) shrugs and says: 'well, yes, hello to you!'
```

If you say something that doesn't contain "hello", our callback won't execute.

**In summary**:

1. When we say something in the room, using the "say" command, the "say" event of all characters (except us) is called.
2. The in-game Python system looks at what we have said, and checks whether one of our callbacks in the "say" event contains a keyword that we have spoken.
3. If so, call it, defining the event variables as we have seen.
4. The callback is then executed as normal Python code.  Here we have called the `msg_contents` method on the character's location (probably a room) to display a message to the entire room.  We have also used mapping to easily display the character's name.  This is not specific to the in-game Python system.  If you feel overwhelmed by the code we've used, just shorten it and use something more simple, for instance:

```python
speaker.msg("You have said something to me.")
```

## The same callback for several keywords

It's easy to create a callback that will be triggered if the sentence contains one of several keywords.

    @call/add merchant = say trade, trader, goods

And in the editor that opens:

```python
character.location.msg_contents("{character} says: 'Ho well, trade's fine as long as roads are safe.'", mapping=dict(character=character))
```

Then you can say something with either "trade", "trader" or "goods" in your sentence, which should call the callback:

```
You say, "and how is your trade going?"
a merchant(#3) says: 'Ho well, trade's fine as long as roads are safe.'
```

We can set several keywords when adding the callback.  We just need to separate them with commas.

## A longer callback

So far, we have only set one line in our callbacks.  Which is useful, but we often need more.  For an entire dialogue, you might want to do a bit more than that.

    @call/add merchant = say bandit, bandits

And in the editor you can paste the following lines:

```python
character.location.msg_contents("{character} says: 'Bandits he?'", mapping=dict(character=character))
character.location.msg_contents("{character} scratches his head, considering.", mapping=dict(character=character))
character.location.msg_contents("{character} whispers: 'Aye, saw some of them, north from here.  No trouble o' mine, but...'", mapping=dict(character=character))
speaker.msg("{character} looks at you more closely.".format(character=character.get_display_name(speaker)))
speaker.msg("{character} continues in a low voice: 'Ain't my place to say, but if you need to find 'em, they're encamped some distance away from the road, I guess near a cave or something.'.".format(character=character.get_display_name(speaker)))
```

Now try to ask the merchant about bandits:

```
You say, "have you seen bandits?"
a merchant(#3) says: 'Bandits he?'
a merchant(#3) scratches his head, considering.
a merchant(#3) whispers: 'Aye, saw some of them, north from here.  No trouble o' mine, but...'
a merchant(#3) looks at you more closely.
a merchant(#3) continues in a low voice: 'Ain't my place to say, but if you need to find 'em, they're encamped some distance away from the road, I guess near a cave or something.'.
```

Notice here that the first lines of dialogue are spoken to the entire room, but then the merchant is talking directly to the speaker, and only the speaker hears it.  There's no real limit to what you can do with this.

- You can set a mood system, storing attributes in the NPC itself to tell you in what mood he is, which will influence the information he will give... perhaps the accuracy of it as well.
- You can add random phrases spoken in some context.
- You can use other actions (you're not limited to having the merchant say something, you can ask him to move, gives you something, attack if you have a combat system, or whatever else).
- The callbacks are in pure Python, so you can write conditions or loops.
- You can add in "pauses" between some instructions using chained events.  This tutorial won't describe how to do that however.  You already have a lot to play with.

## Tutorial F.A.Q.

- **Q:** can I create several characters who would answer to specific dialogue?
- **A:** of course.  Te in-game Python system is so powerful because you can set unique code for various objects.  You can have several characters answering to different things.  You can even have different characters in the room answering to greetings.  All callbacks will be executed one after another.
- **Q:** can I have two characters answering to the same dialogue in exactly the same way?
- **A:** It's possible but not so easy to do.  Usually, event grouping is set in code, and depends on different games.  However, if it is for some infrequent occurrences, it's easy to do using [chained events](https://github.com/evennia/evennia/blob/master/evennia/contrib/ingame_python/README.md#chained-events).
- **Q:** is it possible to deploy callbacks on all characters sharing the same prototype?
- **A:** not out of the box.  This depends on individual settings in code.  One can imagine that all characters of some type would share some events, but this is game-specific.  Rooms of the same zone could share the same events as well.  It is possible to do but requires modification of the source code.

- Next tutorial: [adding a voice-operated elevator with events](./A-voice-operated-elevator-using-events).
