# Using Commands and Building Stuff

In this lesson, we will test out what we can do in-game out-of-the-box. Evennia ships with
[around 90 default commands](../../../Components/Default-Commands.md) and, while you can override those as you please, the defaults can be quite useful.

Connect and login to your new game. You will find yourself in the "Limbo" location. This
is the only room in the game at this point. Let's explore the default commands a little.

The default commands have syntax [similar to MUX](../../../Coding/Default-Command-Syntax.md):

     command[/switch/switch...] [arguments ...]

An example would be:

     create/drop box

A _/switch_ is a special, optional flag to make a command behave differently. A switch is always put directly after the command name, and begins with a forward slash (`/`). The _arguments_ are one or more inputs to the commands. It's common to use an equal sign (`=`) when assigning something to an object.

> Are you used to commands starting with @, like @create? That will work, too. Evennia simply ignores the preceeding @.

## Getting Help

    help

Will give you a list of all commands available to you. Use

    help <commandname>

to see the in-game help for that command.

## Looking Around

The most common command is

    look

This will show you the description of the current location. `l` is an alias for the look command.

When targeting objects in commands, you have two special labels you can use: `here` for the current room, or `me`/`self` to point back to yourself. Thus,

    look me

will give you your own description. `look here` is, in this case, the same as just plain `look`.


## Stepping Down from Godhood

If you just installed Evennia, your very first player account is called user #1 &mdash; also known as the _superuser_ or _god user_. This user is very powerful &mdash; so powerful that it will override many game restrictions (such as locks). This can be useful, but it also hides some functionality that you might want to test.

To step down temporarily from your superuser position, you may use the `quell` command in-game:

    quell

This will make you start using the permission of your current character's level instead of your superuser level. If you didn't change any settings, your initial game Character should have _Developer_ level permission &mdash; as high as can be without bypassing locks like the superuser does. This will work fine for the examples on this page. Use

    unquell

to get superuser status again when you are done.

## Creating an Object

Basic objects can be anything &mdash; swords, flowers, and non-player characters. They are created using the `create` command. For example:

    create box

This creates a new 'box' (of the default object type) in your inventory. Use the command `inventory` (or `i`) to see it. Now, 'box' is a rather short name, so let's rename it and tack on a few aliases:

    name box = very large box;box;very;crate

```{warning} MUD Clients and Semi-Colons: 
Some traditional MUD clients use the semi-colon `;` to separate client inputs. If so, the above line will give an error and you'll need to change your client to use another command-separator or put it in 'verbatim' mode. If you still have trouble, use the Evennia web client instead.
```

We have now renamed the box as _very large box_ &mdash; and this is what we will see when looking at it. However, we will also recognize it by any of the other names we have offered as arguments to the name command above (i.e., _crate_ or simply _box_ as before). We also could have given these aliases directly after the name in the initial `create` object command. This is true for all creation commands &mdash; you can always provide a list of `;`-separated aliases to the name of your new object. In our example, if you had not wanted to change the box object's name itself, but to add aliases only, you could use the `alias` command.

At this point in the building tutorial, our Character is currently carrying the box. Let's drop it:

    drop box

Hey presto, &mdash; there it is on the ground, in all its normality. There is also a shortcut to both create and drop an object in one go by using the `/drop` switch (e.g, `create/drop box`). 

Let us take a closer look at our new box:

    examine box

The examine command will show some technical details about the box object. For now, we will ignore what this
information means.

Try to `look` at the box to see the (default) description:

    > look box
    You see nothing special.

The default description is not very exciting. Let's add some flavor:

    desc box = This is a large and very heavy box.

If you try the `get` command, we will pick up the box. So far so good. But, if we really want this to be a large and heavy box, people should _not_ be able to run off with it so easily. To prevent this, we must lock it down. This is done by assigning a _lock_ to it. TO do so, first make sure the box was dropped in the room, then use the lock command:

    lock box = get:false()

Locks represent a rather [big topic](../../../Components/Locks.md) but, for now, this will do what we want. The above command will lock the box so no one can lift it &mdash; with one exception. Remember that superusers override all locks and will pick it up anyway. Make sure you are quelling your superuser powers, and try to get it again:

    > get box
    You can't get that.

Think this default error message looks dull? The `get` command looks for an [Attribute](../../../Components/Attributes.md) named `get_err_msg` to return as a custom error message. We set attributes using the `set` command:

    set box/get_err_msg = It's way too heavy for you to lift.

Now try to get the box and you should see a more pertinent error message echoed back to you. To see what this message string is in the future, you can use 'examine'.

    examine box/get_err_msg

`Examine` will return the value of attributes, including color codes. For instance, `examine here/desc` would return the raw description of the current room (including color codes), so that you can copy-and-paste to set its description to something else.

You create new Commands &mdash; or modify existing ones &mdash; in Python code outside the game. We explore doing so later in the [Commands tutorial](./Beginner-Tutorial-Adding-Commands.md).

## Get a Personality

[Scripts](../../../Components/Scripts.md) are powerful out-of-character objects useful for many "under the hood" things. One of their optional abilities is to do things on a timer. To try out our first script, let's apply one to ourselves. There is an example script in `evennia/contrib/tutorials/bodyfunctions/bodyfunctions.py` that is called `BodyFunctions`. To add this to our self, we may use the `script` command:

    script self = tutorials.bodyfunctions.BodyFunctions

The above string tells Evennia to dig up the Python code at the place we indicate. It already knows to look in the `contrib/` folder, so we don't have to give the full path.

> Note also how we use `.` instead of `/` (or `\` on Windows). This convention is a so-called "Python-path." In a Python-path, you separate the parts of the path with `.` and skip the `.py` file-ending. Importantly, it also allows you to point to Python code _inside_ files as in our example where the `BodyFunctions` class is inside the `bodyfunctions.py` file. We'll get to classes later. These "Python-paths" are used extensively throughout Evennia.

Wait a while and you will notice yourself starting to make random observations...

    script self =

The above command will show details about scripts on the given object, in this case your self. The `examine` command also includes such details. 

You will see how long it is until it "fires" next. Don't be alarmed if nothing happens when the countdown reaches zero &mdash; this particular script has a randomizer to determine if it will say something or not. So you will not see output every time it fires.

When you are tired of your character's "insights," stop the script with:

    script/stop self = tutorials.bodyfunctions.BodyFunctions

You may create your own scripts in Python, outside the game; the path you give to `script` is literally the Python path to your script file. The [Scripts](../../../Components/Scripts.md) page explains more details.

## Pushing Your Buttons

If we get back to the box we made, there is only so much fun you can have with it at this point. It's just a dumb generic object. If you renamed it to `stone` and changed its description, no one would be the wiser. However, with the combined use of custom [Typeclasses](../../../Components/Typeclasses.md), [Scripts](../../../Components/Scripts.md) and object-based [Commands](../../../Components/Commands.md), you can expand it &mdash; and other items &mdash; to be as unique, complex, and interactive as you want.

So, let's work though just such an example. So far, we have only created objects that use the default object typeclass named simply `Object`. Let's create an object that is a little more interesting. Under
`evennia/contrib/tutorials` there is a module `red_button.py`. It contains the enigmatic `RedButton` class.

Let's make us one of _those_!

    create/drop button:tutorials.red_button.RedButton

Enter the above command with Python-path and there you go &mdash; one red button! Just as in the Script example earlier, we have specified a Python-path to the Python code that we want Evennia to use for creating the object. 

The RedButton is an example object intended to show off a few of Evennia's features. You will find that the [Typeclass](../../../Components/Typeclasses.md) and [Commands](../../../Components/Commands.md) controlling it are inside [evennia/contrib/tutorials/red_button](../../../api/evennia.contrib.tutorials.red_button.md).

If you wait for a while (make sure you dropped it!) the button will blink invitingly.

Why don't you try to push it...?

Surely a big red button is meant to be pushed.

You know you want to.

```{warning} Don't press the invitingly blinking red button.
```

## Making Yourself a House

The main command for shaping your game world is `dig`. For example, if you are standing in Limbo, you can dig a route to your new house location like this:

    dig house = large red door;door;in,to the outside;out

The above command will create a new room named "house." It will also create an exit from your current location named 'large red door' and a corresponding exit named 'to the outside' in the new house room leading back to Limbo. In above, we also define a few aliases to those exits so that players don't need to type the full exit name.

If you wanted to use regular compass directions (north, west, southwest, etc.), you could do that with `dig`, too. However, Evennia also has a specialized version of `dig` that helps with cardinal directions (as well as up/down and in/out). It's called `tunnel`:

    tunnel sw = cliff

This will create a new room named "cliff" with a "southwest" exit leading there, and a "northeast" path leading back from the cliff to your current location.

You can create new exits from where you are standing, using the `open` command:

    open north;n = house

This opens an exit `north` (with an alias `n`) to the previously created room `house`.

If you have many rooms named `house`, you will get a list of matches and must select to which specific one you want to link.

Next, follow the northern exit to your "house" by walking north. You can also `teleport` to it:

    north

or:

    teleport house

To open an exit back to Limbo manually (in case you didn't do so automatically by using the `dig` command):

    open door = limbo

(You can also use the `#dbref` of Limbo, which you can find by using `examine here` when standing in Limbo.)

## Reshuffling the World

Assuming you are back at `Limbo`, let's teleport the _large box_ to our `house`:

    teleport box = house
        very large box is leaving Limbo, heading for house.
        Teleported very large box -> house.

You can find things in the game world, such as our `box`, by using the `find` command:

    find box
        One Match(#1-#8):
        very large box(#8) - src.objects.objects.Object

Knowing the `#dbref` of the box (#8 in this example), you can grab the box and get it back here without actually going to the `house` first:

    teleport #8 = here

As mentioned, `here` is an alias for "your current location." The box should now be back in Limbo with you. 

We are getting tired of the box. Let's destroy it:

    destroy box

Issuing the `destroy`` command will ask you for confirmation. Once you confirm, the box will be gone.

You can `destroy` many objects in one go by providing a comma-separated list of objects (or a range of `#dbrefs`, if they are not in the same location) to the command.

## Adding a Help Entry

Command-related `help` entries are something that you modify in Python code &mdash; we'll cover that when we explain how to add Commands &mdash; but you may also add non-command-related help entries. For example, to explain something about the history of your game world:

    sethelp History = At the dawn of time ...

You will now find your new `History` entry in the `help` list, and can read your help-text with `help History`.

## Adding a World

After this brief introduction to building and using in-game commands, you may be ready to see a more fleshed-out example. Fortunately, Evennia comes with an tutorial world for you to explore &mdash; which we will try in the next lesson.
