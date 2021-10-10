# Building menus


# The building_menu contrib

This contrib allows you to write custom and easy to use building menus.  As the name implies, these
menus are most useful for building things, that is, your builders might appreciate them, although
you can use them for your players as well.

Building menus are somewhat similar to `EvMenu` although they don't use the same system at all and
are intended to make building easier.  They replicate what other engines refer to as "building
editors", which allow to you to build in a menu instead of having to enter a lot of complex
commands.  Builders might appreciate this simplicity, and if the code that was used to create them
is simple as well, coders could find this contrib useful.

## A simple menu

Before diving in, there are some things to point out:

- Building menus work on an object.  This object will be edited by manipulations in the menu.  So
you can create a menu to add/edit a room, an exit, a character and so on.
- Building menus are arranged in layers of choices.  A choice gives access to an option or to a sub-
menu.  Choices are linked to commands (usually very short).  For instance, in the example shown
below, to edit the room key, after opening the building menu, you can type `k`.  That will lead you
to the key choice where you can enter a new key for the room.  Then you can enter `@` to leave this
choice and go back to the entire menu.  (All of this can be changed).
- To open the menu, you will need something like a command.  This contrib offers a basic command for
demonstration, but we will override it in this example, using the same code with more flexibility.

So let's add a very basic example to begin with.

### A generic editing command

Let's begin by adding a new command.  You could add or edit the following file (there's no trick
here, feel free to organize the code differently):

```python
# file: commands/building.py
from evennia.contrib.building_menu import BuildingMenu
from commands.command import Command

class EditCmd(Command):

    """
    Editing command.

    Usage:
      @edit [object]

    Open a building menu to edit the specified object.  This menu allows to
    specific information about this object.

    Examples:
      @edit here
      @edit self
      @edit #142

    """

    key = "@edit"
    locks = "cmd:id(1) or perm(Builders)"
    help_category = "Building"

    def func(self):
        if not self.args.strip():
            self.msg("|rYou should provide an argument to this function: the object to edit.|n")
            return

        obj = self.caller.search(self.args.strip(), global_search=True)
        if not obj:
            return

        if obj.typename == "Room":
            Menu = RoomBuildingMenu
        else:
            obj_name = obj.get_display_name(self.caller)
            self.msg(f"|rThe object {obj_name} cannot be edited.|n")
            return

        menu = Menu(self.caller, obj)
        menu.open()
```

This command is rather simple in itself:

1. It has a key `@edit` and a lock to only allow builders to use it.
2. In its `func` method, it begins by checking the arguments, returning an error if no argument is
specified.
3. It then searches for the given argument.  We search globally.  The `search` method used in this
way will return the found object or `None`.  It will also send the error message to the caller if
necessary.
4. Assuming we have found an object, we check the object `typename`.  This will be used later when
we want to display several building menus.  For the time being, we only handle `Room`.  If the
caller specified something else, we'll display an error.
5. Assuming this object is a `Room`, we have defined a `Menu` object containing the class of our
building menu.  We build this class (creating an instance), giving it the caller and the object to
edit.
6. We then open the building menu, using the `open` method.

The end might sound a bit surprising at first glance.  But the process is still very simple: we
create an instance of our building menu and call its `open` method.  Nothing more.

> Where is our building menu?

If you go ahead and add this command and test it, you'll get an error.  We haven't defined
`RoomBuildingMenu` yet.

To add this command, edit `commands/default_cmdsets.py`.  Import our command, adding an import line
at the top of the file:

```python
"""
...
"""

from evennia import default_cmds

# The following line is to be added
from commands.building import EditCmd
```

And in the class below (`CharacterCmdSet`), add the last line of this code:

```python
class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    The `CharacterCmdSet` contains general in-game commands like `look`,
    `get`, etc available on in-game Character objects. It is merged with
    the `AccountCmdSet` when an Account puppets a Character.
    """
    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
        self.add(EditCmd())
```

### Our first menu

So far, we can't use our building menu.  Our `@edit` command will throw an error.  We have to define
the `RoomBuildingMenu` class.  Open the `commands/building.py` file and add to the end of the file:

```python
# ... at the end of commands/building.py
# Our building menu

class RoomBuildingMenu(BuildingMenu):

    """
    Building menu to edit a room.

    For the time being, we have only one choice: key, to edit the room key.

    """

    def init(self, room):
        self.add_choice("key", "k", attr="key")
```

Save these changes, reload your game.  You can now use the `@edit` command.  Here's what we get
(notice that the commands we enter into the game are prefixed with `> `, though this prefix will
probably not appear in your MUD client):

```
> look
Limbo(#2)
Welcome to your new Evennia-based game! Visit https://www.evennia.com if you need
help, want to contribute, report issues or just join the community.
As Account #1 you can create a demo/tutorial area with @batchcommand tutorial_world.build.

> @edit here
Building menu: Limbo

 [K]ey: Limbo
 [Q]uit the menu

> q
Closing the building menu.

> @edit here
Building menu: Limbo

 [K]ey: Limbo
 [Q]uit the menu

> k
-------------------------------------------------------------------------------
key for Limbo(#2)

You can change this value simply by entering it.

Use @ to go back to the main menu.

Current value: Limbo

> A beautiful meadow
-------------------------------------------------------------------------------

key for A beautiful meadow(#2)

You can change this value simply by entering it.

Use @ to go back to the main menu.

Current value: A beautiful meadow

> @
Building menu: A beautiful meadow

 [K]ey: A beautiful meadow
 [Q]uit the menu

> q

Closing the building menu.

> look
A beautiful meadow(#2)
Welcome to your new Evennia-based game! Visit https://www.evennia.com if you need
help, want to contribute, report issues or just join the community.
As Account #1 you can create a demo/tutorial area with @batchcommand tutorial_world.build.
```

Before diving into the code, let's examine what we have:

- When we use the `@edit here` command, a building menu for this room appears.
- This menu has two choices:
    - Enter `k` to edit the room key.  You will go into a choice where you can simply type the key
room key (the way we have done here).  You can use `@` to go back to the menu.
    - You can use `q` to quit the menu.

We then check, with the `look` command, that the menu has modified this room key.  So by adding a
class, with a method and a single line of code within, we've added a menu with two choices.

### Code explanation

Let's examine our code again:

```python
class RoomBuildingMenu(BuildingMenu):

    """
    Building menu to edit a room.

    For the time being, we have only one choice: key, to edit the room key.

    """

    def init(self, room):
        self.add_choice("key", "k", attr="key")
```

- We first create a class inheriting from `BuildingMenu`.  This is usually the case when we want to
create a building menu with this contrib.
- In this class, we override the `init` method, which is called when the menu opens.
- In this `init` method, we call `add_choice`.  This takes several arguments, but we've defined only
three here:
    - The choice name.  This is mandatory and will be used by the building menu to know how to
display this choice.
    - The command key to access this choice.  We've given a simple `"k"`.  Menu commands usually are
pretty short (that's part of the reason building menus are appreciated by builders).  You can also
specify additional aliases, but we'll see that later.
    - We've added a keyword argument, `attr`.  This tells the building menu that when we are in this
choice, the text we enter goes into this attribute name.  It's called `attr`, but it could be a room
attribute or a typeclass persistent or non-persistent attribute (we'll see other examples as well).

> We've added the menu choice for `key` here, why is another menu choice defined for `quit`?

Our building menu creates a choice at the end of our choice list if it's a top-level menu (sub-menus
don't have this feature).  You can, however, override it to provide a different "quit" message or to
perform some actions.

I encourage you to play with this code.  As simple as it is, it offers some functionalities already.

## Customizing building menus

This somewhat long section explains how to customize building menus.  There are different ways
depending on what you would like to achieve.  We'll go from specific to more advanced here.

### Generic choices

In the previous example, we've used `add_choice`.  This is one of three methods you can use to add
choices.  The other two are to handle more generic actions:

- `add_choice_edit`: this is called to add a choice which points to the `EvEditor`.  It is used to
edit a description in most cases, although you could edit other things.  We'll see an example
shortly.  `add_choice_edit` uses most of the `add_choice` keyword arguments we'll see, but usually
we specify only two (sometimes three):
    - The choice title as usual.
    - The choice key (command key) as usual.
    - Optionally, the attribute of the object to edit, with the `attr` keyword argument.  By
default, `attr` contains `db.desc`.  It means that this persistent data attribute will be edited by
the `EvEditor`.  You can change that to whatever you want though.
- `add_choice_quit`: this allows to add a choice to quit the editor.  Most advisable!  If you don't
do it, the building menu will do it automatically, except if you really tell it not to.  Again, you
can specify the title and key of this menu.  You can also call a function when this menu closes.

So here's a more complete example (you can replace your `RoomBuildingMenu` class in
`commands/building.py` to see it):

```python
class RoomBuildingMenu(BuildingMenu):

    """
    Building menu to edit a room.
    """

    def init(self, room):
        self.add_choice("key", "k", attr="key")
        self.add_choice_edit("description", "d")
        self.add_choice_quit("quit this editor", "q")
```

So far, our building menu class is still thin... and yet we already have some interesting feature.
See for yourself the following MUD client output (again, the commands are prefixed with `> ` to
distinguish them):

```
> @reload

> @edit here
Building menu: A beautiful meadow

 [K]ey: A beautiful meadow
 [D]escription: 
   Welcome to your new Evennia-based game! Visit https://www.evennia.com if you need
help, want to contribute, report issues or just join the community.
As Account #1 you can create a demo/tutorial area with @batchcommand tutorial_world.build.
 [Q]uit this editor

> d

----------Line Editor [editor]----------------------------------------------------
01| Welcome to your new |wEvennia|n-based game! Visit https://www.evennia.com if you need
02| help, want to contribute, report issues or just join the community.
03| As Account #1 you can create a demo/tutorial area with |w@batchcommand tutorial_world.build|n.

> :DD

----------[l:03 w:034 c:0247]------------(:h for help)----------------------------
Cleared 3 lines from buffer.

> This is a beautiful meadow. But so beautiful I can't describe it.

01| This is a beautiful meadow. But so beautiful I can't describe it.

> :wq
Building menu: A beautiful meadow

 [K]ey: A beautiful meadow
 [D]escription: 
   This is a beautiful meadow.  But so beautiful I can't describe it.
 [Q]uit this editor

> q
Closing the building menu.

> look
A beautiful meadow(#2)
This is a beautiful meadow.  But so beautiful I can't describe it.
```

So by using the `d` shortcut in our building menu, an `EvEditor` opens.  You can use the `EvEditor`
commands (like we did here, `:DD` to remove all, `:wq` to save and quit).  When you quit the editor,
the description is saved (here, in `room.db.desc`) and you go back to the building menu.

Notice that the choice to quit has changed too, which is due to our adding `add_choice_quit`.  In
most cases, you will probably not use this method, since the quit menu is added automatically.

### `add_choice` options

`add_choice` and the two methods `add_choice_edit` and `add_choice_quit` take a lot of optional
arguments to make customization easier.  Some of these options might not apply to `add_choice_edit`
or `add_choice_quit` however.

Below are the options of `add_choice`, specify them as arguments:

- The first positional, mandatory argument is the choice title, as we have seen.  This will
influence how the choice appears in the menu.
- The second positional, mandatory argument is the command key to access to this menu.  It is best
to use keyword arguments for the other arguments.
- The `aliases` keyword argument can contain a list of aliases that can be used to access to this
menu.  For instance: `add_choice(..., aliases=['t'])`
- The `attr` keyword argument contains the attribute to edit when this choice is selected.  It's a
string, it has to be the name, from the object (specified in the menu constructor) to reach this
attribute.  For instance, a `attr` of `"key"` will try to find `obj.key` to read and write the
attribute.  You can specify more complex attribute names, for instance, `attr="db.desc"` to set the
`desc` persistent attribute, or `attr="ndb.something"` so use a non-persistent data attribute on the
object.
- The `text` keyword argument is used to change the text that will be displayed when the menu choice
is selected.  Menu choices provide a default text that you can change.  Since this is a long text,
it's useful to use multi-line strings (see an example below).
- The `glance` keyword argument is used to specify how to display the current information while in
the menu, when the choice hasn't been opened.  If you examine the previous examples, you will see
that the current (`key` or `db.desc`) was shown in the menu, next to the command key.  This is
useful for seeing at a glance the current value (hence the name).  Again, menu choices will provide
a default glance if you don't specify one.
- The `on_enter` keyword argument allows to add a callback to use when the menu choice is opened.
This is more advanced, but sometimes useful.
- The `on_nomatch` keyword argument is called when, once in the menu, the caller enters some text
that doesn't match any command (including the `@` command).  By default, this will edit the
specified `attr`.
- The `on_leave` keyword argument allows to specify a callback used when the caller leaves the menu
choice.  This can be useful for cleanup as well.

These are a lot of possibilities, and most of the time you won't need them all.  Here is a short
example using some of these arguments (again, replace the `RoomBuildingMenu` class in
`commands/building.py` with the following code to see it working):

```python
class RoomBuildingMenu(BuildingMenu):

    """
    Building menu to edit a room.

    For the time being, we have only one choice: key, to edit the room key.

    """

    def init(self, room):
        self.add_choice("title", key="t", attr="key", glance="{obj.key}", text="""
                -------------------------------------------------------------------------------
                Editing the title of {{obj.key}}(#{{obj.id}})

                You can change the title simply by entering it.
                Use |y{back}|n to go back to the main menu.

                Current title: |c{{obj.key}}|n
        """.format(back="|n or |y".join(self.keys_go_back)))
        self.add_choice_edit("description", "d")
```

Reload your game and see it in action:

```
> @edit here
Building menu: A beautiful meadow

 [T]itle: A beautiful meadow
 [D]escription: 
   This is a beautiful meadow.  But so beautiful I can't describe it.
 [Q]uit the menu

> t
-------------------------------------------------------------------------------

Editing the title of A beautiful meadow(#2)

You can change the title simply by entering it.
Use @ to go back to the main menu.

Current title: A beautiful meadow

> @

Building menu: A beautiful meadow

 [T]itle: A beautiful meadow
 [D]escription: 
   This is a beautiful meadow.  But so beautiful I can't describe it.
 [Q]uit the menu

> q
Closing the building menu.
```

The most surprising part is no doubt the text.  We use the multi-line syntax (with `"""`).
Excessive spaces will be removed from the left for each line automatically.  We specify some
information between braces... sometimes using double braces.  What might be a bit odd:

- `{back}` is a direct format argument we'll use (see the `.format` specifiers).
- `{{obj...}}` refers to the object being edited.  We use two braces, because `.format` will remove them.

In `glance`, we also use `{obj.key}` to indicate we want to show the room's key.

### Everything can be a function

The keyword arguments of `add_choice` are often strings (type `str`).  But each of these arguments
can also be a function.  This allows for a lot of customization, since we define the callbacks that
will be executed to achieve such and such an operation.

To demonstrate, we will try to add a new feature.  Our building menu for rooms isn't that bad, but
it would be great to be able to edit exits too.  So we can add a new menu choice below
description... but how to actually edit exits?  Exits are not just an attribute to set: exits are
objects (of type `Exit` by default) which stands between two rooms (object of type `Room`).  So how
can we show that?

First let's add a couple of exits in limbo, so we have something to work with:

```
@tunnel n
@tunnel s
```

This should create two new rooms, exits leading to them from limbo and back to limbo.

```
> look
A beautiful meadow(#2)
This is a beautiful meadow.  But so beautiful I can't describe it.
Exits: north(#4) and south(#7)
```

We can access room exits with the `exits` property:

```
> @py here.exits
[<Exit: north>, <Exit: south>]
```

So what we need is to display this list in our building menu... and to allow to edit it would be
great.  Perhaps even add new exits?

First of all, let's write a function to display the `glance` on existing exits.  Here's the code,
it's explained below:

```python
class RoomBuildingMenu(BuildingMenu):

    """
    Building menu to edit a room.

    """

    def init(self, room):
        self.add_choice("title", key="t", attr="key", glance="{obj.key}", text="""
                -------------------------------------------------------------------------------
                Editing the title of {{obj.key}}(#{{obj.id}})

                You can change the title simply by entering it.
                Use |y{back}|n to go back to the main menu.

                Current title: |c{{obj.key}}|n
        """.format(back="|n or |y".join(self.keys_go_back)))
        self.add_choice_edit("description", "d")
        self.add_choice("exits", "e", glance=glance_exits, attr="exits")


# Menu functions
def glance_exits(room):
    """Show the room exits."""
    if room.exits:
        glance = ""
        for exit in room.exits:
            glance += f"\n  |y{exit.key}|n"

        return glance

    return "\n  |gNo exit yet|n"
```

When the building menu opens, it displays each choice to the caller.  A choice is displayed with its
title (rendered a bit nicely to show the key as well) and the glance.  In the case of the `exits`
choice, the glance is a function, so the building menu calls this function giving it the object
being edited (the room here).  The function should return the text to see.

```
> @edit here
Building menu: A beautiful meadow

 [T]itle: A beautiful meadow
 [D]escription: 
   This is a beautiful meadow.  But so beautiful I can't describe it.
 [E]xits: 
  north
  south
 [Q]uit the menu

> q
Closing the editor.
```

> How do I know the parameters of the function to give?

The function you give can accept a lot of different parameters.  This allows for a flexible approach
but might seem complicated at first.  Basically, your function can accept any parameter, and the
building menu will send only the parameter based on their names.  If your function defines an
argument named `caller` for instance (like `def func(caller):` ), then the building menu knows that
the first argument should contain the caller of the building menu.  Here are the arguments, you
don't have to specify them (if you do, they need to have the same name):

- `menu`: if your function defines an argument named `menu`, it will contain the building menu
itself.
- `choice`: if your function defines an argument named `choice`, it will contain the `Choice` object
representing this menu choice.
- `string`: if your function defines an argument named `string`, it will contain the user input to
reach this menu choice.  This is not very useful, except on `nomatch` callbacks which we'll see
later.
- `obj`: if your function defines an argument named `obj`, it will contain the building menu edited
object.
- `caller`: if your function defines an argument named `caller`, it will contain the caller of the
building menu.
- Anything else: any other argument will contain the object being edited by the building menu.

So in our case:

```python
def glance_exits(room):
```

The only argument we need is `room`.  It's not present in the list of possible arguments, so the
editing object of the building menu (the room, here) is given.

> Why is it useful to get the menu or choice object?

Most of the time, you will not need these arguments.  In very rare cases, you will use them to get
specific data (like the default attribute that was set).  This tutorial will not elaborate on these
possibilities.  Just know that they exist.

We should also define a text callback, so that we can enter our menu to see the room exits.  We'll
see how to edit them in the next section but this is a good opportunity to show a more complete
callback.  To see it in action, as usual, replace the class and functions in `commands/building.py`:

```python
# Our building menu

class RoomBuildingMenu(BuildingMenu):

    """
    Building menu to edit a room.

    """

    def init(self, room):
        self.add_choice("title", key="t", attr="key", glance="{obj.key}", text="""
                -------------------------------------------------------------------------------
                Editing the title of {{obj.key}}(#{{obj.id}})

                You can change the title simply by entering it.
                Use |y{back}|n to go back to the main menu.

                Current title: |c{{obj.key}}|n
        """.format(back="|n or |y".join(self.keys_go_back)))
        self.add_choice_edit("description", "d")
        self.add_choice("exits", "e", glance=glance_exits, attr="exits", text=text_exits)


# Menu functions
def glance_exits(room):
    """Show the room exits."""
    if room.exits:
        glance = ""
        for exit in room.exits:
            glance += f"\n  |y{exit.key}|n"

        return glance

    return "\n  |gNo exit yet|n"

def text_exits(caller, room):
    """Show the room exits in the choice itself."""
    text = "-" * 79
    text += "\n\nRoom exits:"
    text += "\n Use |y@c|n to create a new exit."
    text += "\n\nExisting exits:"
    if room.exits:
        for exit in room.exits:
            text += f"\n  |y@e {exit.key}|n"
            if exit.aliases.all():
                text += " (|y{aliases}|n)".format(aliases="|n, |y".join(
                    alias for alias in exit.aliases.all()
                ))
            if exit.destination:
                text += f" toward {exit.get_display_name(caller)}"
    else:
        text += "\n\n |gNo exit has yet been defined.|n"

    return text
```

Look at the second callback in particular.  It takes an additional argument, the caller (remember,
the argument names are important, their order is not relevant).  This is useful for displaying
destination of exits accurately.  Here is a demonstration of this menu:

```
> @edit here
Building menu: A beautiful meadow

 [T]itle: A beautiful meadow
 [D]escription: 
   This is a beautiful meadow.  But so beautiful I can't describe it.
 [E]xits: 
  north
  south
 [Q]uit the menu

> e
-------------------------------------------------------------------------------

Room exits:
 Use @c to create a new exit.

Existing exits:
  @e north (n) toward north(#4)
  @e south (s) toward south(#7)

> @
Building menu: A beautiful meadow

 [T]itle: A beautiful meadow
 [D]escription: 
   This is a beautiful meadow.  But so beautiful I can't describe it.
 [E]xits: 
  north
  south
 [Q]uit the menu

> q
Closing the building menu.
```

Using callbacks allows a great flexibility.  We'll now see how to handle sub-menus.

### Sub-menus for complex menus

A menu is relatively flat: it has a root (where you see all the menu choices) and individual choices
you can go to using the menu choice keys.  Once in a choice you can type some input or go back to
the root menu by entering the return command (usually `@`).

Why shouldn't individual exits have their own menu though?  Say, you edit an exit and can change its
key, description or aliases... perhaps even destination?  Why ever not?  It would make building much
easier!

The building menu system offers two ways to do that.  The first is nested keys: nested keys allow to
go beyond just one menu/choice, to have menus with more layers.  Using them is quick but might feel
a bit counter-intuitive at first.  Another option is to create a different menu class and redirect
from the first to the second.  This option might require more lines but is more explicit and can be
re-used for multiple menus.  Adopt one of them depending of your taste.

#### Nested menu keys

So far, we've only used menu keys with one letter.  We can add more, of course, but menu keys in
their simple shape are just command keys.  Press "e" to go to the "exits" choice.

But menu keys can be nested.  Nested keys allow to add choices with sub-menus.  For instance, type
"e" to go to the "exits" choice, and then you can type "c" to open a menu to create a new exit, or
"d" to open a menu to delete an exit.  The first menu would have the "e.c" key (first e, then c),
the second menu would have key as "e.d".

That's more advanced and, if the following code doesn't sound very friendly to you, try the next
section which provides a different approach of the same problem.

So we would like to edit exits.  That is, you can type "e" to go into the choice of exits, then
enter `@e` followed by the exit name to edit it... which will open another menu.  In this sub-menu
you could change the exit key or description.

So we have a menu hierarchy similar to that:

```
t                       Change the room title
d                       Change the room description
e                       Access the room exits
  [exit name]           Access the exit name sub-menu
                 [text] Change the exit key
```

Or, if you prefer an example output:

```
> look
A beautiful meadow(#2)
This is a beautiful meadow.  But so beautiful I can't describe it.
Exits: north(#4) and south(#7)

> @edit here
Building menu: A beautiful meadow

 [T]itle: A beautiful meadow
 [D]escription: 
   This is a beautiful meadow.  But so beautiful I can't describe it.
 [E]xits: 
  north
  south
 [Q]uit the menu

> e
-------------------------------------------------------------------------------

Room exits :
 Use @c to create a new exit.

Existing exits:
  @e north (n) toward north(#4)
  @e south (s) toward south(#7)

> @e north
Editing: north
Exit north:
Enter the exit key to change it, or @ to go back.

New exit key:

> door

Exit door:
Enter the exit key to change it, or @ to go back.

New exit key:

> @

-------------------------------------------------------------------------------

Room exits :
 Use @c to create a new exit.

Existing exits:
  @e door (n) toward door(#4)
  @e south (s) toward south(#7)

> @
Building menu: A beautiful meadow

 [T]itle: A beautiful meadow
 [D]escription: 
   This is a beautiful meadow.  But so beautiful I can't describe it.
 [E]xits: 
  door
  south
 [Q]uit the menu

> q
Closing the building menu.
```

This needs a bit of code and a bit of explanation.  So here we go... the code first, the
explanations next!

```python
# ... from commands/building.py
# Our building menu

class RoomBuildingMenu(BuildingMenu):

    """
    Building menu to edit a room.

    For the time being, we have only one choice: key, to edit the room key.

    """

    def init(self, room):
        self.add_choice("title", key="t", attr="key", glance="{obj.key}", text="""
                -------------------------------------------------------------------------------
                Editing the title of {{obj.key}}(#{{obj.id}})

                You can change the title simply by entering it.
                Use |y{back}|n to go back to the main menu.

                Current title: |c{{obj.key}}|n
        """.format(back="|n or |y".join(self.keys_go_back)))
        self.add_choice_edit("description", "d")
        self.add_choice("exits", "e", glance=glance_exits, text=text_exits, on_nomatch=nomatch_exits)

        # Exit sub-menu
        self.add_choice("exit", "e.*", text=text_single_exit, on_nomatch=nomatch_single_exit)


# Menu functions
def glance_exits(room):
    """Show the room exits."""
    if room.exits:
        glance = ""
        for exit in room.exits:
            glance += f"\n  |y{exit.key}|n"

        return glance

    return "\n  |gNo exit yet|n"

def text_exits(caller, room):
    """Show the room exits in the choice itself."""
    text = "-" * 79
    text += "\n\nRoom exits:"
    text += "\n Use |y@c|n to create a new exit."
    text += "\n\nExisting exits:"
    if room.exits:
        for exit in room.exits:
            text += f"\n  |y@e {exit.key}|n"
            if exit.aliases.all():
                text += " (|y{aliases}|n)".format(aliases="|n, |y".join(
                    alias for alias in exit.aliases.all()
                ))
            if exit.destination:
                text += f" toward {exit.get_display_name(caller)}"
    else:
        text += "\n\n |gNo exit has yet been defined.|n"

    return text

def nomatch_exits(menu, caller, room, string):
    """
    The user typed something in the list of exits.  Maybe an exit name?
    """
    string = string[3:]
    exit = caller.search(string, candidates=room.exits)
    if exit is None:
        return

    # Open a sub-menu, using nested keys
    caller.msg(f"Editing: {exit.key}")
    menu.move(exit)
    return False

# Exit sub-menu
def text_single_exit(menu, caller):
    """Show the text to edit single exits."""
    exit = menu.keys[1]
    if exit is None:
        return ""

    return f"""
        Exit {exit.key}:

        Enter the exit key to change it, or |y@|n to go back.

        New exit key:
    """

def nomatch_single_exit(menu, caller, room, string):
    """The user entered something in the exit sub-menu.  Replace the exit key."""
    # exit is the second key element: keys should contain ['e', <Exit object>]
    exit = menu.keys[1]
    if exit is None:
        caller.msg("|rCannot find the exit.|n")
        menu.move(back=True)
        return False

    exit.key = string
    return True
```

> That's a lot of code!  And we only handle editing the exit key!

That's why at some point you might want to write a real sub-menu, instead of using simple nested
keys.  But you might need both to build pretty menus too!

1. The first thing new is in our menu class.  After creating a `on_nomatch` callback for the exits
menu (that shouldn't be a surprised), we need to add a nested key.  We give this menu a key of
`"e.*"`.  That's a bit odd!  "e" is our key to the exits menu, . is the separator to indicate a
nested menu, and * means anything.  So basically, we create a nested menu that is contains within
the exits menu and anything.  We'll see what this "anything" is in practice.
2. The `glance_exits` and `text_exits` are basically the same.
3. The `nomatch_exits` is short but interesting.  It's called when we enter some text in the "exits"
menu (that is, in the list of exits).  We have said that the user should enter `@e` followed by the
exit name to edit it.  So in the `nomatch_exits` callbac, we check for that input.  If the entered
text begins by `@e`, we try to find the exit in the room.  If we do...
4. We call the `menu.move` method.  That's where things get a bit complicated with nested menus: we
need to use `menu.move` to change from layer to layer.  Here, we are in the choice of exits (the
exits menu, of key "e").  We need to go down one layer to edit an exit.  So we call `menu.move` and
give it an exit object.  The menu system remembers what position the user is based on the keys she
has entered: when the user opens the menu, there is no key.  If she selects the exits choice, the
menu key being "e", the position of the user is `["e"]` (a list with the menu keys).  If we call
`menu.move`, whatever we give to this method will be appended to the list of keys, so that the user
position becomes `["e", <Exit object>]`.
5. In the menu class, we have defined the menu "e.*", meaning "the menu contained in the exits
choice plus anything".  The "anything" here is an exit:  we have called `menu.move(exit)`, so the
`"e.*"` menu choice is chosen.
6. In this menu, the text is set to a callback.  There is also a `on_nomatch` callback that is
called whenever the user enters some text.  If so, we change the exit name.

Using `menu.move` like this is a bit confusing at first.  Sometimes it's useful.  In this case, if
we want a more complex menu for exits, it makes sense to use a real sub-menu, not nested keys like
this.  But sometimes, you will find yourself in a situation where you don't need a full menu to
handle a choice.

#### Full sub-menu as separate classes

The best way to handle individual exits is to create two separate classes:

- One for the room menu.
- One for the individual exit menu.

The first one will have to redirect on the second.  This might be more intuitive and flexible,
depending on what you want to achieve.  So let's build two menus:

```python
# Still in commands/building.py, replace the menu class and functions by...
# Our building menus

class RoomBuildingMenu(BuildingMenu):

    """
    Building menu to edit a room.
    """

    def init(self, room):
        self.add_choice("title", key="t", attr="key", glance="{obj.key}", text="""
                -------------------------------------------------------------------------------
                Editing the title of {{obj.key}}(#{{obj.id}})

                You can change the title simply by entering it.
                Use |y{back}|n to go back to the main menu.

                Current title: |c{{obj.key}}|n
        """.format(back="|n or |y".join(self.keys_go_back)))
        self.add_choice_edit("description", "d")
        self.add_choice("exits", "e", glance=glance_exits, text=text_exits,
on_nomatch=nomatch_exits)


# Menu functions
def glance_exits(room):
    """Show the room exits."""
    if room.exits:
        glance = ""
        for exit in room.exits:
            glance += f"\n  |y{exit.key}|n"

        return glance

    return "\n  |gNo exit yet|n"

def text_exits(caller, room):
    """Show the room exits in the choice itself."""
    text = "-" * 79
    text += "\n\nRoom exits:"
    text += "\n Use |y@c|n to create a new exit."
    text += "\n\nExisting exits:"
    if room.exits:
        for exit in room.exits:
            text += f"\n  |y@e {exit.key}|n"
            if exit.aliases.all():
                text += " (|y{aliases}|n)".format(aliases="|n, |y".join(
                    alias for alias in exit.aliases.all()
                ))
            if exit.destination:
                text += f" toward {exit.get_display_name(caller)}"
    else:
        text += "\n\n |gNo exit has yet been defined.|n"

    return text

def nomatch_exits(menu, caller, room, string):
    """
    The user typed something in the list of exits.  Maybe an exit name?
    """
    string = string[3:]
    exit = caller.search(string, candidates=room.exits)
    if exit is None:
        return

    # Open a sub-menu, using nested keys
    caller.msg(f"Editing: {exit.key}")
    menu.open_submenu("commands.building.ExitBuildingMenu", exit, parent_keys=["e"])
    return False

class ExitBuildingMenu(BuildingMenu):

    """
    Building menu to edit an exit.

    """

    def init(self, exit):
        self.add_choice("key", key="k", attr="key", glance="{obj.key}")
        self.add_choice_edit("description", "d")
```

The code might be much easier to read.  But before detailing it, let's see how it behaves in the
game:

```
> @edit here
Building menu: A beautiful meadow

 [T]itle: A beautiful meadow
 [D]escription: 
   This is a beautiful meadow.  But so beautiful I can't describe it.
 [E]xits: 
  door
  south
 [Q]uit the menu

> e
-------------------------------------------------------------------------------

Room exits:
 Use @c to create a new exit.

Existing exits:
  @e door (n) toward door(#4)
  @e south (s) toward south(#7)

Editing: door

> @e door
Building menu: door

 [K]ey: door
 [D]escription: 
   None

> k
-------------------------------------------------------------------------------
key for door(#4)

You can change this value simply by entering it.

Use @ to go back to the main menu.

Current value: door

> north

-------------------------------------------------------------------------------
key for north(#4)

You can change this value simply by entering it.

Use @ to go back to the main menu.

Current value: north

> @
Building menu: north

 [K]ey: north
 [D]escription: 
   None

> d
----------Line Editor [editor]----------------------------------------------------
01| None
----------[l:01 w:001 c:0004]------------(:h for help)----------------------------

> :DD
Cleared 1 lines from buffer.

> This is the northern exit. Cool huh?
01| This is the northern exit. Cool huh?

> :wq
Building menu: north
 [K]ey: north
 [D]escription: 
   This is the northern exit.  Cool huh?

> @
-------------------------------------------------------------------------------
Room exits:
 Use @c to create a new exit.

Existing exits:
  @e north (n) toward north(#4)
  @e south (s) toward south(#7)

> @
Building menu: A beautiful meadow

 [T]itle: A beautiful meadow
 [D]escription: 
   This is a beautiful meadow.  But so beautiful I can't describe it.
 [E]xits: 
  north
  south
 [Q]uit the menu

> q
Closing the building menu.

> look
A beautiful meadow(#2)
This is a beautiful meadow.  But so beautiful I can't describe it.
Exits: north(#4) and south(#7)
> @py here.exits[0]
>>> here.exits[0]
north
> @py here.exits[0].db.desc
>>> here.exits[0].db.desc
This is the northern exit.  Cool huh?
```

Very simply, we created two menus and bridged them together.  This needs much less callbacks.  There
is only one line in the `nomatch_exits` to add:

```python
    menu.open_submenu("commands.building.ExitBuildingMenu", exit, parent_keys=["e"])
```

We have to call `open_submenu` on the menu object (which opens, as its name implies, a sub menu)
with three arguments:

- The path of the menu class to create.  It's the Python class leading to the menu (notice the
dots).
- The object that will be edited by the menu.  Here, it's our exit, so we give it to the sub-menu.
- The keys of the parent to open when the sub-menu closes.  Basically, when we're in the root of the
sub-menu and press `@`, we'll open the parent menu, with the parent keys.  So we specify `["e"]`,
since the parent menus is the "exits" choice.

And that's it.  The new class will be automatically created.  As you can see, we have to create a
`on_nomatch` callback to open the sub-menu, but once opened, it automatically close whenever needed.

### Generic menu options

There are some options that can be set on any menu class.  These options allow for greater
customization.  They are class attributes (see the example below), so just set them in the class
body:

- `keys_go_back` (default to `["@"]`): the keys to use to go back in the menu hierarchy, from choice
to root menu, from sub-menu to parent-menu.  By default, only a `@` is used.  You can change this
key for one menu or all of them.  You can define multiple return commands if you want.
- `sep_keys` (default `"."`): this is the separator for nested keys.  There is no real need to
redefine it except if you really need the dot as a key, and need nested keys in your menu.
- `joker_key` (default to `"*"`): used for nested keys to indicate "any key".  Again, you shouldn't
need to change it unless you want to be able to use the @*@ in a command key, and also need nested
keys in your menu.
- `min_shortcut` (default to `1`): although we didn't see it here, one can create a menu choice
without giving it a key.  If so, the menu system will try to "guess" the key.  This option allows to
change the minimum length of any key for security reasons.

To set one of them just do so in your menu class(es):

```python
class RoomBuildingMenu(BuildingMenu):
    keys_go_back = ["/"]
    min_shortcut = 2
```

## Conclusion

Building menus mean to save you time and create a rich yet simple interface.  But they can be
complicated to learn and require reading the source code to find out how to do such and such a
thing.  This documentation, however long, is an attempt at describing this system, but chances are
you'll still have questions about it after reading it, especially if you try to push this system to
a great extent.  Do not hesitate to read the documentation of this contrib, it's meant to be
exhaustive but user-friendly.
