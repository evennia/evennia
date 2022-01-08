# Building menu

Contrib by vincent-lg, 2018

Building menus are in-game menus, not unlike `EvMenu` though using a
different approach. Building menus have been specifically designed to edit
information as a builder. Creating a building menu in a command allows
builders quick-editing of a given object, like a room. If you follow the
steps to add the contrib, you will have access to an `edit` command
that will edit any default object, offering to change its key and description.

## Install

1. Import the `GenericBuildingCmd` class from this contrib in your
   `mygame/commands/default_cmdset.py` file:

    ```python
    from evennia.contrib.base_systems.building_menu import GenericBuildingCmd
    ```

2. Below, add the command in the `CharacterCmdSet`:

    ```python
    # ... These lines should exist in the file
    class CharacterCmdSet(default_cmds.CharacterCmdSet):
        key = "DefaultCharacter"

        def at_cmdset_creation(self):
            super(CharacterCmdSet, self).at_cmdset_creation()
            # ... add the line below
            self.add(GenericBuildingCmd())
    ```

## Usage

The `edit` command will allow you to edit any object.  You will need to
specify the object name or ID as an argument.  For instance: `edit here`
will edit the current room.  However, building menus can perform much more
than this very simple example, read on for more details.

Building menus can be set to edit about anything.  Here is an example of
output you could obtain when editing the room:

```
 Editing the room: Limbo(#2)

 [T]itle: the limbo room
 [D]escription
    This is the limbo room.  You can easily change this default description,
    either by using the |y@desc/edit|n command, or simply by entering this
    menu (enter |yd|n).
 [E]xits:
     north to A parking(#4)
 [Q]uit this menu
```

From there, you can open the title choice by pressing t.  You can then
change the room title by simply entering text, and go back to the
main menu entering @ (all this is customizable).  Press q to quit this menu.

The first thing to do is to create a new module and place a class
inheriting from `BuildingMenu` in it.

```python
from evennia.contrib.base_systems.building_menu import BuildingMenu

class RoomBuildingMenu(BuildingMenu):
    # ...

```

Next, override the `init` method (not `__init__`!).  You can add
choices (like the title, description, and exits choices as seen above) by using
the `add_choice` method.

```python
class RoomBuildingMenu(BuildingMenu):
    def init(self, room):
        self.add_choice("title", "t", attr="key")

```

That will create the first choice, the title choice.  If one opens your menu
and enter t, she will be in the title choice.  She can change the title
(it will write in the room's `key` attribute) and then go back to the
main menu using `@`.

`add_choice` has a lot of arguments and offers a great deal of
flexibility.  The most useful ones is probably the usage of callbacks,
as you can set almost any argument in `add_choice` to be a callback, a
function that you have defined above in your module.  This function will be
called when the menu element is triggered.

Notice that in order to edit a description, the best method to call isn't
`add_choice`, but `add_choice_edit`.  This is a convenient shortcut
which is available to quickly open an `EvEditor` when entering this choice
and going back to the menu when the editor closes.

```python
class RoomBuildingMenu(BuildingMenu):
    def init(self, room):
        self.add_choice("title", "t", attr="key")
        self.add_choice_edit("description", key="d", attr="db.desc")

```

When you wish to create a building menu, you just need to import your
class, create it specifying your intended caller and object to edit,
then call `open`:

```python
from <wherever> import RoomBuildingMenu

class CmdEdit(Command):

    key = "redit"

    def func(self):
        menu = RoomBuildingMenu(self.caller, self.caller.location)
        menu.open()

```

This is a very short introduction.  For more details, see the [online
tutorial](https://github.com/evennia/evennia/wiki/Building-menus) or read the
heavily-documented code of the contrib itself.
