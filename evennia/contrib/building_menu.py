"""
Module containing the building menu system.

Evennia contributor: vincent-lg 2018

Building menus are similar to `EvMenu`, except that they have been specifically-designed to edit information as a builder.  Creating a building menu in a command allows builders quick-editing of a given object, like a room.  Here is an example of output you could obtain when editing the room:

```
 Editing the room: Limbo

 [T]itle: the limbo room
 [D]escription
    This is the limbo room.  You can easily change this default description,
    either by using the |y@desc/edit|n command, or simply by selecting this
    menu (enter |yd|n).
 [E]xits:
     north to A parking(#4)
 [Q]uit this menu
```

From there, you can open the title sub-menu by pressing t.  You can then change the room title by simply entering text, and go back to the main menu entering @ (all this is customizable).  Press q to quit this menu.

The first thing to do is to create a new module and place a class inheriting from `BuildingMenu` in it.

```python
from evennia.contrib.building_menu import BuildingMenu

class RoomMenu(BuildingMenu):
    # ... to be ocmpleted ...
```

Next, override the `init` method.  You can add choices (like the title, description, and exits sub-menus as seen above) by using the `add_choice` method.

```
class RoomMenu(BuildingMenu):
    def init(self, room):
        self.add_choice("Title", "t", attr="key")
```

That will create the first choice, the title sub-menu.  If one opens your menu and enter t, she will be in the title sub-menu.  She can change the title (it will write in the room's `key` attribute) and then go back to the main menu using `@`.

`add_choice` has a lot of arguments and offer a great deal of flexibility.  The most useful ones is probably the usage of callback, as you can set any argument in `add_choice` to be a callback, a function that you have defined above in your module.  Here is a very short example of this:

```
def show_exits(menu
```

"""

from inspect import getargspec

from django.conf import settings
from evennia import Command, CmdSet
from evennia.commands import cmdhandler
from evennia.utils.logger import log_err, log_trace
from evennia.utils.ansi import strip_ansi
from evennia.utils.utils import class_from_module

_MAX_TEXT_WIDTH = settings.CLIENT_DEFAULT_WIDTH
_CMD_NOMATCH = cmdhandler.CMD_NOMATCH
_CMD_NOINPUT = cmdhandler.CMD_NOINPUT

def _call_or_get(value, menu=None, choice=None, string=None, obj=None, caller=None):
    """
    Call the value, if appropriate, or just return it.

    Args:
        value (any): the value to obtain.

    Kwargs:
        menu (BuildingMenu, optional): the building menu to pass to value
        choice (Choice, optional): the choice to pass to value if a callback.
        string (str, optional): the raw string to pass to value if a callback.        if a callback.
        obj (any): the object to pass to value if a callback.
        caller (Account or Character, optional): the caller.

    Returns:
        The value itself.  If the argument is a function, call it with specific
        arguments, passing it the menu, choice, string, and object if supported.

    Note:
        If `value` is a function, call it with varying arguments.  The
        list of arguments will depend on the argument names.
        - An argument named `menu` will contain the building menu or None.
        - The `choice` argument will contain the choice or None.
        - The `string` argument will contain the raw string or None.
        - The `obj` argument will contain the object or None.
        - The `caller` argument will contain the caller or None.
        - Any other argument will contain the object (`obj`).

    """
    if callable(value):
        # Check the function arguments
        kwargs = {}
        spec = getargspec(value)
        args = spec.args
        if spec.keywords:
            kwargs.update(dict(menu=menu, choice=choice, string=string, obj=obj, caller=caller))
        else:
            if "menu" in args:
                kwargs["menu"] = menu
            if "choice" in args:
                kwargs["choice"] = choice
            if "string" in args:
                kwargs["string"] = string
            if "obj" in args:
                kwargs["obj"] = obj
            if "caller" in args:
                kwargs["caller"] = caller

        # Fill missing arguments
        for arg in args:
            if arg not in kwargs:
                kwargs[arg] = obj

        # Call the function and return its return value
        return value(**kwargs)

    return value


class Choice(object):

    """A choice object, created by `add_choice`."""

    def __init__(self, title, key=None, aliases=None, attr=None, callback=None, text=None, brief=None, menu=None, caller=None, obj=None):
        """Constructor.

        Args:
            title (str): the choice's title.
            key (str, optional): the key of the letters to type to access
                    the sub-neu.  If not set, try to guess it based on the title.
            aliases (list of str, optional): the allowed aliases for this choice.
            attr (str, optional): the name of the attribute of 'obj' to set.
            callback (callable, optional): the function to call before the input
                    is set in `attr`.  If `attr` is not set, you should
                    specify a function that both callback and set the value in `obj`.
            text (str or callable, optional): a text to be displayed when
                    the menu is opened  It can be a callable.
            brief (str or callable, optional): a brief summary of the
                    sub-menu shown in the main menu.  It can be set to
                    display the current value of the attribute in the
                    main menu itself.
            menu (BuildingMenu, optional): the parent building menu.
            caller (Account or Object, optional): the caller.
            obj (Object, optional): the object to edit.

        """
        self.title = title
        self.key = key
        self.aliases = aliases
        self.attr = attr
        self.callback = callback
        self.text = text
        self.brief = brief
        self.menu = menu
        self.caller = caller
        self.obj = obj

    def __repr__(self):
        return "<Choice (title={}, key={})>".format(self.title, self.key)

    def trigger(self, string):
        """Call the trigger callback, is specified."""
        if self.callback:
            _call_or_get(self.callback, menu=self.menu, choice=self, string=string, caller=self.caller, obj=self.obj)


class BuildingMenu(object):

    """
    Class allowing to create and set builder menus.

    A builder menu is a kind of `EvMenu` designed to edit objects by
    builders, although it can be used for players in some contexts.  You
    could, for instance, create a builder menu to edit a room with a
    sub-menu for the room's key, another for the room's description,
    another for the room's exits, and so on.

    To add choices (sub-menus), you should call `add_choice` (see the
    full documentation of this method).  With most arguments, you can
    specify either a plain string or a callback.  This callback will be
    called when the operation is to be performed.

    """

    def __init__(self, caller=None, obj=None, title="Building menu: {obj}", key=None):
        """Constructor, you shouldn't override.  See `init` instead.

        Args:
            obj (Object): the object to be edited, like a room.

        """
        self.caller = caller
        self.obj = obj
        self.title = title
        self.choices = []
        self.key = key
        self.cmds = {}

        # Options (can be overridden in init)
        self.min_shortcut = 1

        if obj:
            self.init(obj)

            # If choices have been added without keys, try to guess them
            for choice in self.choices:
                if choice.key is None:
                    title = strip_ansi(choice.title.strip()).lower()
                    length = self.min_shortcut
                    i = 0
                    while length <= len(title):
                        while i < len(title) - length + 1:
                            guess = title[i:i + length]
                            if guess not in self.cmds:
                                choice.key = guess
                                break

                            i += 1

                        if choice.key is not None:
                            break

                        length += 1

                    if choice.key is None:
                        raise ValueError("Cannot guess the key for {}".format(choice))
                    else:
                        self.cmds[chocie.key] = choice

    def init(self, obj):
        """Create the sub-menu to edit the specified object.

        Args:
            obj (Object): the object to edit.

        Note:
            This method is probably to be overridden in your subclasses.  Use `add_choice` and its variants to create sub-menus.

        """
        pass

    def add_choice(self, title, key=None, aliases=None, attr=None, callback=None, text=None, brief=None):
        """Add a choice, a valid sub-menu, in the current builder menu.

        Args:
            title (str): the choice's title.
            key (str, optional): the key of the letters to type to access
                    the sub-neu.  If not set, try to guess it based on the title.
            aliases (list of str, optional): the allowed aliases for this choice.
            attr (str, optional): the name of the attribute of 'obj' to set.
            callback (callable, optional): the function to call before the input
                    is set in `attr`.  If `attr` is not set, you should
                    specify a function that both callback and set the value in `obj`.
            text (str or callable, optional): a text to be displayed when
                    the menu is opened  It can be a callable.
            brief (str or callable, optional): a brief summary of the
                    sub-menu shown in the main menu.  It can be set to
                    display the current value of the attribute in the
                    main menu itself.

        Note:
            All arguments can be a callable, like a function.  This has the
            advantage of allowing persistent building menus.  If you specify
            a callable in any of the arguments, the callable should return
            the value expected by the argument (a str more often than
            not) and can have the following arguments:
                callable(menu)
                callable(menu, user)
                callable(menu, user, input)

        """
        key = key or ""
        key = key.lower()
        aliases = aliases or []
        aliases = [a.lower() for a in aliases]
        if callback is None:
            if attr is None:
                raise ValueError("The choice {} has neither attr nor callback, specify one of these as arguments".format(title))

            callback = menu_setattr

        if key and key in self.cmds:
            raise ValueError("A conflict exists between {} and {}, both use key or alias {}".format(self.cmds[key], title, repr(key)))

        choice = Choice(title, key, aliases, attr, callback, text, brief, menu=self, caller=self.caller, obj=self.obj)
        self.choices.append(choice)
        if key:
            self.cmds[key] = choice

        for alias in aliases:
            self.cmds[alias] = choice

    def add_choice_quit(self, title="quit the menu", key="q", aliases=None):
        """
        Add a simple choice just to quit the building menu.

        Args:
            title (str, optional): the choice title.
            key (str, optional): the choice key.
            aliases (list of str, optional): the choice aliases.

        Note:
            This is just a shortcut method, calling `add_choice`.

        """
        return self.add_choice(title, key=key, aliases=aliases, callback=menu_quit)

    def _generate_commands(self, cmdset):
        """
        Generate commands for the menu, if any is needed.

        Args:
            cmdset (CmdSet): the cmdset.

        """
        if self.key is None:
            for choice in self.choices:
                cmd = MenuCommand(key=choice.key, aliases=choice.aliases, building_menu=self, choice=choice)
                cmd.get_help = lambda cmd, caller: _call_or_get(choice.text, menu=self, choice=choice, obj=self.obj, caller=self.caller)
                cmdset.add(cmd)

    def _save(self):
        """Save the menu in a persistent attribute on the caller."""
        self.caller.ndb._building_menu = self
        self.caller.db._building_menu = {
                "class": type(self).__module__ + "." + type(self).__name__,
                "obj": self.obj,
                "key": self.key,
        }

    def open(self):
        """Open the building menu for the caller."""
        caller = self.caller
        self._save()
        self.caller.cmdset.add(BuildingMenuCmdSet, permanent=True)

        # Try to find the newly added cmdset (a shortcut would be nice)
        for cmdset in self.caller.cmdset.get():
            if isinstance(cmdset, BuildingMenuCmdSet):
                self._generate_commands(cmdset)
                self.display()
                return

    # Display methods.  Override for customization
    def display_title(self):
        """Return the menu title to be displayed."""
        return _call_or_get(self.title, menu=self, obj=self.obj, caller=self.caller).format(obj=self.obj)

    def display_choice(self, choice):
        """Display the specified choice.

        Args:
            choice (Choice): the menu choice.

        """
        title = _call_or_get(choice.title, menu=self, choice=choice, obj=self.obj, caller=self.caller)
        clear_title = title.lower()
        pos = clear_title.find(choice.key.lower())
        ret = " "
        if pos >= 0:
            ret += title[:pos] + "[|y" + choice.key.title() + "|n]" + title[pos + len(choice.key):]
        else:
            ret += "[|y" + choice.key.title() + "|n] " + title

        return ret

    def display(self):
        """Display the entire menu."""
        menu = self.display_title() + "\n"
        for choice in self.choices:
            menu += "\n" + self.display_choice(choice)

        self.caller.msg(menu)

    @staticmethod
    def restore(caller, cmdset):
        """Restore the building menu for the caller.

        Args:
            caller (Account or Character): the caller.
            cmdset (CmdSet): the cmdset.

        Note:
            This method should be automatically called if a menu is
            saved in the caller, but the object itself cannot be found.

        """
        menu = caller.db._buildingmenu
        if menu:
            class_name = menu.get("class")
            if not class_name:
                log_err("BuildingMenu: on caller {}, a persistent attribute holds building menu data, but no class could be found to restore the menu".format(caller))
                return

            try:
                menu_class = class_from_module(class_name)
            except Exception:
                log_trace("BuildingMenu: attempting to load class {} failed".format(repr(class_name)))
                return False

            # Create the menu
            obj = menu.get("obj")
            try:
                building_menu = menu_class(caller, obj)
            except Exception:
                log_trace("An error occurred while creating building menu {}".format(repr(class_name)))
                return False

            # If there's no saved key, add the menu commands
            building_menu._generate_commands(cmdset)

            return building_menu


class MenuCommand(Command):

    """An applicaiton-specific command."""

    help_category = "Application-specific"

    def __init__(self, **kwargs):
        self.menu = kwargs.pop("building_menu", None)
        self.choice = kwargs.pop("choice", None)
        super(MenuCommand, self).__init__(**kwargs)

    def func(self):
        """Function body."""
        if self.choice is None:
            log_err("Command: {}, no choice has been specified".format(self.key))
            self.msg("An unexpected error occurred.  Closing the menu.")
            self.caller.cmdset.delete(BuildingMenuCmdSet)
            return

        self.choice.trigger(self.args)


class CmdNoInput(MenuCommand):

    """No input has been found."""

    key = _CMD_NOINPUT
    locks = "cmd:all()"

    def func(self):
        """Redisplay the screen, if any."""
        if self.menu:
            self.menu.display()
        else:
            log_err("When CMDNOMATCH was called, the building menu couldn't be found")
            self.caller.msg("The building menu couldn't be found, remove the CmdSet")
            self.caller.cmdset.delete(BuildingMenuCmdSet)


class CmdNoMatch(Command):

    """No input has been found."""

    key = _CMD_NOMATCH
    locks = "cmd:all()"

    def func(self):
        """Redirect most inputs to the screen, if found."""
        raw_string = self.raw_string.rstrip()
        self.msg("No match")


class BuildingMenuCmdSet(CmdSet):

    """
    Building menu CmdSet, adding commands specific to the menu.
    """

    key = "building_menu"
    priority = 5

    def at_cmdset_creation(self):
        """Populates the cmdset with commands."""
        caller = self.cmdsetobj

        # The caller could recall the menu
        menu = caller.ndb._building_menu
        if menu:
            menu._generate_commands(self)
        else:
            menu = caller.db._building_menu
            if menu:
                menu = BuildingMenu.restore(caller, self)

        cmds = [CmdNoInput, CmdNoMatch]
        for cmd in cmds:
            self.add(cmd(building_menu=menu, choice=None))


# Helper functions
def menu_setattr(menu, choice, obj, string):
    """
    Set the value at the specified attribute.

    Args:
        menu (BuildingMenu): the menu object.
        choice (Chocie): the specific choice.
        obj (any): the object to modify.
        string (str): the string with the new value.

    Note:
        This function is supposed to be used as a default to
        `BuildingMenu.add_choice`, when an attribute name is specified
        but no function to callback the said value.

    """
    attr = getattr(choice, "attr", None)
    if choice is None or string is None or attr is None or menu is None:
        log_err("The `menu_setattr` function was called to set the attribute {} of object {} to {}, but the choice {} of menu {} or another information is missing.".format(attr, obj, repr(string), choice, menu))
        return

    for part in attr.split(".")[:-1]:
        obj = getattr(obj, part)

    setattr(obj, attr.split(".")[-1], string)
    menu.display()

def menu_quit(caller):
    """
    Quit the menu, closing the CmdSet.

    Args:
        caller (Account or Object): the caller.

    """
    if caller is None:
        log_err("The function `menu_quit` was called from a building menu without a caller")

    if caller.cmdset.has(BuildingMenuCmdSet):
        caller.msg("Closing the building menu.")
        caller.cmdset.remove(BuildingMenuCmdSet)
    else:
        caller.msg("It looks like the building menu has already been closed.")
