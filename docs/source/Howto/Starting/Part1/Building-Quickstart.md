# Using the game and building stuff

[prev lesson](../Starting-Part1) | [next lesson](./Tutorial-World-Introduction)

In this lesson we will test out what we can do in-game out-of-the-box. Evennia ships with 
[around 90 default commands](api:evennia.commands.default#modules), and while you can override those as you please, 
they can be quite useful.

Connect and log into your new game and you will end up in the "Limbo" location. This 
is the only room in the game at this point. Let's explore the commands a little.

The default commands has syntax [similar to MUX](../../../Concepts/Using-MUX-as-a-Standard):

     command[/switch/switch...] [arguments ...]

An example would be 

     create/drop box

A _/switch_ is a special, optional flag to the command to make it behave differently. It is always
put directly after the command name, and begins with a forward slash (`/`). The _arguments_ are one
or more inputs to the commands. It's common to use an equal sign (`=`) when assigning something to
an object.

> Are you used to commands starting with @, like @create? That will work too. Evennia simply ignores
> the preceeding @. 

## Getting help

    help 
    
Will give you a list of all commands available to you. Use 

    help <commandname>
    
to see the in-game help for that command. 

## Looking around

The most common comman is 

    look
    
This will show you the description of the current location. `l` is an alias. 

When targeting objects in commands you have two special labels you can use, `here` for the current
room or `me`/`self` to point back to yourself. So 

    look me

will give you your own description. `look here` is, in this case, the same as plain `look`. 


## Stepping Down From Godhood

If you just installed Evennia, your very first player account is called user #1, also known as the
_superuser_ or _god user_. This user is very powerful, so powerful that it will override many game
restrictions such as locks. This can be useful, but it also hides some functionality that you might
want to test.

To temporarily step down from your superuser position you can use the `quell` command in-game:

    quell

This will make you start using the permission of your current character's level instead of your
superuser level. If you didn't change any settings your game Character should have an _Developer_
level permission - high as can be without bypassing locks like the superuser does. This will work
fine for the examples on this page. Use

    unquell

to get superuser status again when you are done.

## Creating an Object

Basic objects can be anything -- swords, flowers and non-player characters. They are created using
the `create` command:

    create box

This created a new 'box' (of the default object type) in your inventory. Use the command `inventory`
(or `i`) to see it. Now, 'box' is a rather short name, let's rename it and tack on a few aliases.

    name box = very large box;box;very;crate

```warning:: MUD clients and semi-colon

    Some traditional MUD clients use the semi-colon `;` to separate client inputs. If so, 
    the above line will give an error. You need to change your client to use another command-separator
    or to put it in 'verbatim' mode. If you still have trouble, use the Evennia web client instead.

```


We now renamed the box to _very large box_ (and this is what we will see when looking at it), but we
will also recognize it by any of the other names we give - like _crate_ or simply _box_ as before.
We could have given these aliases directly after the name in the `create` command, this is true for
all creation commands - you can always tag on a list of `;`-separated aliases to the name of your
new object. If you had wanted to not change the name itself, but to only add aliases, you could have
used the `alias` command.

We are currently carrying the box. Let's drop it (there is also a short cut to create and drop in
one go by using the `/drop` switch, for example `create/drop box`).
 
    drop box 

Hey presto - there it is on the ground, in all its normality.

    examine box

This will show some technical details about the box object. For now we will ignore what this
information means.

Try to `look` at the box to see the (default) description. 

    look box
    You see nothing special.

The description you get is not very exciting. Let's add some flavor.

    describe box = This is a large and very heavy box.

If you try the `get` command we will pick up the box. So far so good, but if we really want this to
be a large and heavy box, people should _not_ be able to run off with it that easily. To prevent
this we need to lock it down. This is done by assigning a _Lock_  to it. Make sure the box was
dropped in the room, then try this:

    lock box = get:false()

Locks represent a rather [big topic](../../../Components/Locks), but for now that will do what we want. This will lock
the box so noone can lift it. The exception is superusers, they override all locks and will pick it
up anyway. Make sure you are quelling your superuser powers and try to get the box now:

    > get box
    You can't get that.

Think thís default error message looks dull? The `get` command looks for an [Attribute](../../../Components/Attributes)
named `get_err_msg` for returning a nicer error message (we just happen to know this, you would need
to peek into the
[code](https://github.com/evennia/evennia/blob/master/evennia/commands/default/general.py#L235) for
the `get` command to find out.). You set attributes using the `set` command:

    set box/get_err_msg = It's way too heavy for you to lift. 

Try to get it now and you should see a nicer error message echoed back to you. To see what this
message string is in the future, you can use 'examine.'

    examine box/get_err_msg

Examine will return the value of attributes, including color codes. `examine here/desc` would return
the raw description of your current room (including color codes), so that you can copy-and-paste to
set its description to something else.

You create new Commands (or modify existing ones) in Python outside the game. We will get to that 
later, in the [Commands tutorial](./Adding-Commands).

## Get a Personality

[Scripts](../../../Components/Scripts) are powerful out-of-character objects useful for many "under the hood" things.
One of their optional abilities is to do things on a timer. To try out a first script, let's put one
on ourselves. There is an example script in `evennia/contrib/tutorial_examples/bodyfunctions.py`
that is called `BodyFunctions`. To add this to us we will use the `script` command:

    script self = tutorial_examples.bodyfunctions.BodyFunctions

This string will tell Evennia to dig up the Python code at the place we indicate. It already knows
to look in the `contrib/` folder, so we don't have to give the full path. 

> Note also how we use `.` instead of `/` (or `\` on Windows). This is a so-called "Python path". In a Python-path, 
> you separate the parts of the path with `.` and skip the `.py` file-ending. Importantly, it also allows you to point to
Python code _inside_ files, like the `BodyFunctions` class inside `bodyfunctions.py` (we'll get to classes later). 
These "Python-paths" are used extensively throughout Evennia. 

Wait a while and you will notice yourself starting making random observations ...

    script self 

This will show details about scripts on yourself (also `examine` works). You will see how long it is
until it "fires" next. Don't be alarmed if nothing happens when the countdown reaches zero - this
particular script has a randomizer to determine if it will say something or not. So you will not see
output every time it fires.

When you are tired of your character's "insights", kill the script with

    script/stop self = tutorial_examples.bodyfunctions.BodyFunctions

You create your own scripts in Python, outside the game; the path you give to `script` is literally
the Python path to your script file. The [Scripts](../../../Components/Scripts) page explains more details.

## Pushing Your Buttons

If we get back to the box we made, there is only so much fun you can have with it at this point. It's
just a dumb generic object. If you renamed it to `stone` and changed its description, noone would be
the wiser. However, with the combined use of custom [Typeclasses](../../../Components/Typeclasses), [Scripts](../../../Components/Scripts)
and object-based [Commands](../../../Components/Commands), you could expand it and other items to be as unique, complex
and interactive as you want.

Let's take an example. So far we have only created objects that use the default object typeclass
named simply `Object`. Let's create an object that is a little more interesting. Under
`evennia/contrib/tutorial_examples` there is a module `red_button.py`.  It contains the enigmatic
`RedButton` class.

Let's make us one of _those_!

    create/drop button:tutorial_examples.red_button.RedButton

The same way we did with the Script Earler, we specify a "Python-path" to the Python code we want Evennia
to use for creating the object. There you go - one red button.

The RedButton is an example object intended to show off a few of Evennia's features. You will find
that the [Typeclass](../../../Components/Typeclasses) and [Commands](../../../Components/Commands) controlling it are 
inside [evennia/contrib/tutorial_examples](api:evennia.contrib.tutorial_examples)

If you wait for a while (make sure you dropped it!) the button will blink invitingly. 

Why don't you try to push it ...? 

Surely a big red button is meant to be pushed. 

You know you want to.

```warning:: Don't press the invitingly blinking red button.
```

## Making Yourself a House

The main command for shaping the game world is `dig`. For example, if you are standing in Limbo you
can dig a route to your new house location like this:

    dig house = large red door;door;in,to the outside;out

This will create a new room named 'house'. Spaces at the start/end of names and aliases are ignored
so you could put more air if you wanted.  This call will directly create an exit from your current
location named 'large red door' and a corresponding exit named 'to the outside' in the house room
leading back to Limbo. We also define a few aliases to those exits, so people don't have to write
the full thing all the time.

If you wanted to use normal compass directions (north, west, southwest etc), you could do that with
`dig` too. But Evennia also has a limited version of `dig` that helps for compass directions (and
also up/down and in/out). It's called `tunnel`:

    tunnel sw = cliff

This will create a new room "cliff" with an exit "southwest" leading there and a path "northeast"
leading back from the cliff to your current location.

You can create new exits from where you are, using the `open` command: 

    open north;n = house

This opens an exit `north` (with an alias `n`) to the previously created room `house`.

If you have many rooms named `house` you will get a list of matches and have to select which one you
want to link to. 

Follow the north exit to your 'house' or `teleport` to it:

    north

or:

    teleport house

To manually open an exit back to Limbo (if you didn't do so with the `dig` command):

    open door = limbo

(You can also us the #dbref of limbo, which you can find by using `examine here` when in limbo).

## Reshuffling the World

You can find things using the `find` command. Assuming you are back at `Limbo`, let's teleport the
_large box_ to our house.

    teleport box = house
        very large box is leaving Limbo, heading for house.
        Teleported very large box -> house.

We can still find the box by using find: 

    find box
        One Match(#1-#8):
        very large box(#8) - src.objects.objects.Object

Knowing the `#dbref` of the box (#8 in this example), you can grab the box and get it back here
without actually yourself going to `house` first:

    teleport #8 = here

As mentioned, `here` is an alias for 'your current location'. The box should now be back in Limbo with you.

We are getting tired of the box. Let's destroy it.

    destroy box

It will ask you for confirmation. Once you give it, the box will be gone. 

You can destroy many objects in one go by giving a comma-separated list of objects (or a range
of #dbrefs, if they are not in the same location) to the command.

## Adding a Help Entry

The Command-help is something you modify in Python code. We'll get to that when we get to how to 
add Commands. But you can also add regular help entries, for example to explain something about 
the history of your game world:

    sethelp/add History = At the dawn of time ...

You will now find your new `History` entry in the `help` list and read your help-text with `help History`.

## Adding a World

After this brief introduction to building and using in-game commands you may be ready to see a more fleshed-out 
example. Evennia comes with a tutorial world for you to explore. We will try that out in the next section.

[prev lesson](../Starting-Part1) | [next lesson](./Tutorial-World-Introduction)
