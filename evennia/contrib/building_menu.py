"""
Module containing the building menu system.

Evennia contributor: vincent-lg 2018

Building menus are similar to `EvMenu`, except that they have been specifically-designed to edit information as a builder.  Creating a building menu in a command allows builders quick-editing of a given object, like a room.  Here is an example of output you could obtain when editing the room:

```
 Editing the room: Limbo

 [T]itle: the limbo room
 [D]escription
    This is the limbo room.  You can easily change this default description,
    either by using the |y@desc/edit|n command, or simply by entering this
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
from textwrap import dedent

from django.conf import settings
from evennia import Command, CmdSet
from evennia.commands import cmdhandler
from evennia.utils.ansi import strip_ansi
from evennia.utils.eveditor import EvEditor
from evennia.utils.logger import log_err, log_trace
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

    def __init__(self, title, key=None, aliases=None, attr=None, text=None, glance=None, on_enter=None, on_nomatch=None, on_leave=None,
            menu=None, caller=None, obj=None):
        """Constructor.

        Args:
            title (str): the choice's title.
            key (str, optional): the key of the letters to type to access
                    the sub-neu.  If not set, try to guess it based on the title.
            aliases (list of str, optional): the allowed aliases for this choice.
            attr (str, optional): the name of the attribute of 'obj' to set.
            text (str or callable, optional): a text to be displayed when
                    the menu is opened  It can be a callable.
            glance (str or callable, optional): an at-a-glance summary of the
                    sub-menu shown in the main menu.  It can be set to
                    display the current value of the attribute in the
                    main menu itself.
            menu (BuildingMenu, optional): the parent building menu.
            on_enter (callable, optional): a callable to call when the choice is entered.
            on_nomatch (callable, optional): a callable to call when no match is entered in the choice.
            on_leave (callable, optional): a callable to call when the caller leaves the choice.
            caller (Account or Object, optional): the caller.
            obj (Object, optional): the object to edit.

        """
        self.title = title
        self.key = key
        self.aliases = aliases
        self.attr = attr
        self.text = text
        self.glance = glance
        self.on_enter = on_enter
        self.on_nomatch = on_nomatch
        self.on_leave = on_leave
        self.menu = menu
        self.caller = caller
        self.obj = obj

    def __repr__(self):
        return "<Choice (title={}, key={})>".format(self.title, self.key)

    @property
    def keys(self):
        """Return a tuple of keys separated by `sep_keys`."""
        return tuple(self.key.split(self.menu.sep_keys))

    def enter(self, string):
        """Called when the user opens the choice."""
        if self.on_enter:
            _call_or_get(self.on_enter, menu=self.menu, choice=self, string=string, caller=self.caller, obj=self.obj)

        # Display the text if there is some
        if self.caller:
            self.caller.msg(self.format_text())

    def nomatch(self, string):
        """Called when the user entered something that wasn't a command in a given choice.

        Args:
            string (str): the entered string.

        """
        if self.on_nomatch:
            _call_or_get(self.on_nomatch, menu=self.menu, choice=self, string=string, caller=self.caller, obj=self.obj)

    def format_text(self):
        """Format the choice text and return it, or an empty string."""
        text = ""
        if self.text:
            text = _call_or_get(self.text, menu=self.menu, choice=self, string="", caller=self.caller, obj=self.obj)
            text = text.format(obj=self.obj, caller=self.caller)

        return text


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

    keys_go_back = ["@"]
    sep_keys = "."
    joker_key = "*"
    min_shortcut = 1

    def __init__(self, caller=None, obj=None, title="Building menu: {obj}", key="", parents=None):
        """Constructor, you shouldn't override.  See `init` instead.

        Args:
            obj (Object): the object to be edited, like a room.

        """
        self.caller = caller
        self.obj = obj
        self.title = title
        self.choices = []
        self.key = key
        self.parents = parents or ()
        self.cmds = {}

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

    @property
    def keys(self):
        """Return a tuple of keys separated by `sep_keys`."""
        if not self.key:
            return ()

        return tuple(self.key.split(self.sep_keys))

    @property
    def current_choice(self):
        """Return the current choice or None."""
        menu_keys = self.keys
        if not menu_keys:
            return None

        for choice in self.choices:
            choice_keys = choice.keys
            if len(menu_keys) == len(choice_keys):
                # Check all the intermediate keys
                common = True
                for menu_key, choice_key in zip(menu_keys, choice_keys):
                    if choice_key == self.joker_key:
                        continue

                    if menu_key != choice_key:
                        common = False
                        break

                if common:
                    return choice

        return None

    @property
    def relevant_choices(self):
        """Only return the relevant choices according to the current meny key.

        The menu key is stored and will be used to determine the
        actual position of the caller in the menu.  Therefore, this
        method compares the menu key (`self.key`) to all the choices'
        keys.  It also handles the joker key.

        """
        menu_keys = self.keys
        relevant = []
        for choice in self.choices:
            choice_keys = choice.keys
            if not menu_keys and len(choice_keys) == 1:
                # First level choice with the menu key empty, that's relevant
                relevant.append(choice)
            elif len(menu_keys) == len(choice_keys) - 1:
                # Check all the intermediate keys
                common = True
                for menu_key, choice_key in zip(menu_keys, choice_keys):
                    if choice_key == self.joker_key:
                        continue

                    if menu_key != choice_key:
                        common = False
                        break

                if common:
                    relevant.append(choice)

        return relevant

    def init(self, obj):
        """Create the sub-menu to edit the specified object.

        Args:
            obj (Object): the object to edit.

        Note:
            This method is probably to be overridden in your subclasses.  Use `add_choice` and its variants to create sub-menus.

        """
        pass

    def add_choice(self, title, key=None, aliases=None, attr=None, text=None, glance=None,
            on_enter=None, on_nomatch=None, on_leave=None):
        """Add a choice, a valid sub-menu, in the current builder menu.

        Args:
            title (str): the choice's title.
            key (str, optional): the key of the letters to type to access
                    the sub-neu.  If not set, try to guess it based on the title.
            aliases (list of str, optional): the allowed aliases for this choice.
            attr (str, optional): the name of the attribute of 'obj' to set.
            text (str or callable, optional): a text to be displayed when
                    the menu is opened  It can be a callable.
            glance (str or callable, optional): an at-a-glance summary of the
                    sub-menu shown in the main menu.  It can be set to
                    display the current value of the attribute in the
                    main menu itself.
            on_enter (callable, optional): a callable to call when the choice is entered.
            on_nomatch (callable, optional): a callable to call when no match is entered in the choice.
                    is set in `attr`.  If `attr` is not set, you should
                    specify a function that both callback and set the value in `obj`.
            on_leave (callable, optional): a callable to call when the caller leaves the choice.

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
        if on_enter is None and on_nomatch is None:
            if attr is None:
                raise ValueError("The choice {} has neither attr nor callback, specify one of these as arguments".format(title))

        if attr and on_nomatch is None:
            on_nomatch = menu_setattr

        if isinstance(text, basestring):
            text = dedent(text.strip("\n"))

        if key and key in self.cmds:
            raise ValueError("A conflict exists between {} and {}, both use key or alias {}".format(self.cmds[key], title, repr(key)))

        choice = Choice(title, key=key, aliases=aliases, attr=attr, text=text, glance=glance, on_enter=on_enter, on_nomatch=on_nomatch, on_leave=on_leave,
                menu=self, caller=self.caller, obj=self.obj)
        self.choices.append(choice)
        if key:
            self.cmds[key] = choice

        for alias in aliases:
            self.cmds[alias] = choice

    def add_choice_edit(self, title="description", key="d", aliases=None, attr="db.desc", glance="\n   {obj.db.desc}", on_enter=None):
        """
        Add a simple choice to edit a given attribute in the EvEditor.

        Args:
            title (str, optional): the choice title.
            key (str, optional): the choice key.
            aliases (list of str, optional): the choice aliases.
            glance (str or callable, optional): the at-a-glance description.
            on_enter (callable, optional): a different callable to edit the attribute.

        Note:
            This is just a shortcut method, calling `add_choice`.
            If `on_enter` is not set, use `menu_edit` which opens
            an EvEditor to edit the specified attribute.

        """
        on_enter = on_enter or menu_edit
        return self.add_choice(title, key=key, aliases=aliases, attr=attr, glance=glance, on_enter=on_enter)

    def add_choice_quit(self, title="quit the menu", key="q", aliases=None, on_enter=None):
        """
        Add a simple choice just to quit the building menu.

        Args:
            title (str, optional): the choice title.
            key (str, optional): the choice key.
            aliases (list of str, optional): the choice aliases.
            on_enter (callable, optional): a different callable to quit the building menu.

        Note:
            This is just a shortcut method, calling `add_choice`.
            If `on_enter` is not set, use `menu_quit` which simply
            closes the menu and displays a message.  It also
            removes the CmdSet from the caller.  If you supply
            another callable instead, make sure to do the same.

        """
        on_enter = on_enter or menu_quit
        return self.add_choice(title, key=key, aliases=aliases, on_enter=on_enter)

    def _save(self):
        """Save the menu in a persistent attribute on the caller."""
        self.caller.ndb._building_menu = self
        self.caller.db._building_menu = {
                "class": type(self).__module__ + "." + type(self).__name__,
                "obj": self.obj,
                "key": self.key,
                "parents": self.parents,
        }

    def open(self):
        """Open the building menu for the caller."""
        caller = self.caller
        self._save()
        self.caller.cmdset.add(BuildingMenuCmdSet, permanent=True)
        self.display()

    def open_parent_menu(self):
        """Open parent menu, using `self.parents`."""
        parents = list(self.parents)
        if parents:
            parent_class, parent_obj, parent_key = parents[-1]
            del parents[-1]

            if self.caller.cmdset.has(BuildingMenuCmdSet):
                self.caller.cmdset.remove(BuildingMenuCmdSet)

            try:
                menu_class = class_from_module(parent_class)
            except Exception:
                log_trace("BuildingMenu: attempting to load class {} failed".format(repr(parent_class)))
                return

            # Create the submenu
            try:
                building_menu = menu_class(self.caller, parent_obj, key=parent_key, parents=tuple(parents))
            except Exception:
                log_trace("An error occurred while creating building menu {}".format(repr(parent_class)))
                return
            else:
                return building_menu.open()

    def open_submenu(self, submenu_class, submenu_obj, parent_key):
        """
        Open a sub-menu, closing the current menu and opening the new one.

        Args:
            submenu_class (str): the submenu class as a Python path.
            submenu_obj (any): the object to give to the submenu.
            parent_key (str, optional): the parent key when the submenu is closed.

        Note:
            When the user enters `@` in the submenu, she will go back to
            the current menu, with the `parent_key` set as its key.
            Therefore, you should set it on the key of the choice that
            should be opened when the user leaves the submenu.

        Returns:
            new_menu (BuildingMenu): the new building menu or None.

        """
        parents = list(self.parents)
        parents.append((type(self).__module__ + "." + type(self).__name__, self.obj, parent_key))
        parents = tuple(parents)
        if self.caller.cmdset.has(BuildingMenuCmdSet):
            self.caller.cmdset.remove(BuildingMenuCmdSet)

        # Shift to the new menu
        try:
            menu_class = class_from_module(submenu_class)
        except Exception:
            log_trace("BuildingMenu: attempting to load class {} failed".format(repr(submenu_class)))
            return

        # Create the submenu
        try:
            building_menu = menu_class(self.caller, submenu_obj, parents=parents)
        except Exception:
            log_trace("An error occurred while creating building menu {}".format(repr(submenu_class)))
            return
        else:
            return building_menu.open()

    def move(self, key=None, back=False, quiet=False, string="" ):
        """
        Move inside the menu.

        Args:
            key (str): the portion of the key to add to the current
                    menu key, after a separator (`sep_keys`).  If
                    you wish to go back in the menu tree, don't
                    provide a `key`, just set `back` to `True`.
            back (bool, optional): go back in the menu (`False` by default).
            quiet (bool, optional): should the menu or choice be displayed afterward?

        Note:
            This method will need to be called directly should you
            use more than two levels in your menu.  For instance,
            in your room menu, if you want to have an "exits"
            option, and then be able to enter "north" in this
            choice to edit an exit.  The specific exit choice
            could be a different menu (with a different class), but
            it could also be an additional level in your original menu.
            If that's the case, you will need to use this method.

        """
        choice = self.current_choice
        if choice:
            #choice.leave()
            pass

        if not back: # Move forward
            if not key:
                raise ValueError("you are asking to move forward, you should specify a key.")

            if self.key:
                self.key += self.sep_keys
            self.key += key
        else: # Move backward
            if not self.keys:
                raise ValueError("you already are at the top of the tree, you cannot move backward.")

            self.key = self.sep_keys.join(self.keys[:-1])

        self._save()
        choice = self.current_choice
        if choice:
            choice.enter(string)

        if not quiet:
            self.display()

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
        if choice.glance:
            glance = _call_or_get(choice.glance, menu=self, choice=choice, caller=self.caller, string="", obj=self.obj)
            glance = glance.format(obj=self.obj, caller=self.caller)
            ret += ": " + glance

        return ret

    def display(self):
        """Display the entire menu or a single choice, depending on the current key.."""
        choice = self.current_choice
        if self.key and choice:
            text = choice.format_text()
        else:
            text = self.display_title() + "\n"
            for choice in self.choices:
                text += "\n" + self.display_choice(choice)

        self.caller.msg(text)

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
        menu = caller.db._building_menu
        if menu:
            class_name = menu.get("class")
            if not class_name:
                log_err("BuildingMenu: on caller {}, a persistent attribute holds building menu data, but no class could be found to restore the menu".format(caller))
                return

            try:
                menu_class = class_from_module(class_name)
            except Exception:
                log_trace("BuildingMenu: attempting to load class {} failed".format(repr(class_name)))
                return

            # Create the menu
            obj = menu.get("obj")
            key = menu.get("key")
            parents = menu.get("parents")
            try:
                building_menu = menu_class(caller, obj, key=key, parents=parents)
            except Exception:
                log_trace("An error occurred while creating building menu {}".format(repr(class_name)))
                return False

            return building_menu


class CmdNoInput(Command):

    """No input has been found."""

    key = _CMD_NOINPUT
    locks = "cmd:all()"

    def __init__(self, **kwargs):
        self.menu = kwargs.pop("building_menu", None)
        super(Command, self).__init__(**kwargs)

    def func(self):
        """Display the menu or choice text."""
        if self.menu:
            self.menu.display()
        else:
            log_err("When CMDNOINPUT was called, the building menu couldn't be found")
            self.caller.msg("|rThe building menu couldn't be found, remove the CmdSet.|n")
            self.caller.cmdset.delete(BuildingMenuCmdSet)


class CmdNoMatch(Command):

    """No input has been found."""

    key = _CMD_NOMATCH
    locks = "cmd:all()"

    def __init__(self, **kwargs):
        self.menu = kwargs.pop("building_menu", None)
        super(Command, self).__init__(**kwargs)

    def func(self):
        """Call the proper menu or redirect to nomatch."""
        raw_string = self.raw_string.rstrip()
        if self.menu is None:
            log_err("When CMDNOMATCH was called, the building menu couldn't be found")
            self.caller.msg("|rThe building menu couldn't be found, remove the CmdSet.|n")
            self.caller.cmdset.delete(BuildingMenuCmdSet)
            return

        choice = self.menu.current_choice
        if raw_string in self.menu.keys_go_back:
            if self.menu.key:
                self.menu.move(back=True)
            elif self.menu.parents:
                self.menu.open_parent_menu()
            else:
                self.menu.display()
        elif choice:
            choice.nomatch(raw_string)
            self.caller.msg(choice.format_text())
        else:
            for choice in self.menu.relevant_choices:
                if choice.key.lower() == raw_string.lower() or any(raw_string.lower() == alias for alias in choice.aliases):
                    self.menu.move(choice.key)
                    return

            self.msg("|rUnknown command: {}|n.".format(raw_string))


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
        if menu is None:
            menu = caller.db._building_menu
            if menu:
                menu = BuildingMenu.restore(caller, self)

        cmds = [CmdNoInput, CmdNoMatch]
        for cmd in cmds:
            self.add(cmd(building_menu=menu))


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
        but no function to call `on_nomatch` the said value.

    """
    attr = getattr(choice, "attr", None)
    if choice is None or string is None or attr is None or menu is None:
        log_err("The `menu_setattr` function was called to set the attribute {} of object {} to {}, but the choice {} of menu {} or another information is missing.".format(attr, obj, repr(string), choice, menu))
        return

    for part in attr.split(".")[:-1]:
        obj = getattr(obj, part)

    setattr(obj, attr.split(".")[-1], string)

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

def menu_edit(caller, choice, obj):
    """
    Open the EvEditor to edit a specified field.

    Args:
        caller (Account or Object): the caller.
        choice (Choice): the choice object.
        obj (any): the object to edit.

    """
    attr = choice.attr
    caller.db._building_menu_to_edit = (obj, attr)
    caller.cmdset.remove(BuildingMenuCmdSet)
    EvEditor(caller, loadfunc=_menu_loadfunc, savefunc=_menu_savefunc, quitfunc=_menu_quitfunc, key="editor", persistent=True)

def open_submenu(caller, menu, choice, obj, parent_key):
    """
    Open a sub-menu, closing the current menu and opening the new one
    with `parent` set.

    Args:
        caller (Account or Object): the caller.
        menu (Building): the selected choice.
        choice (Chocie): the choice.
        obj (any): the object to be edited.
        parent_key (any): the parent menu key.

    Note:
        You can easily call this function from a different callback to customize its
        behavior.

    """
    parent_key = parent_key if isinstance(parent_key, basestring) else None
    menu.open_submenu(choice.attr, obj, parent_key)


# Private functions for EvEditor
def _menu_loadfunc(caller):
    obj, attr = caller.attributes.get("_building_menu_to_edit", [None, None])
    if obj and attr:
        for part in attr.split(".")[:-1]:
            obj = getattr(obj, part)

    return getattr(obj, attr.split(".")[-1]) if obj is not None else ""

def _menu_savefunc(caller, buf):
    obj, attr = caller.attributes.get("_building_menu_to_edit", [None, None])
    if obj and attr:
        for part in attr.split(".")[:-1]:
            obj = getattr(obj, part)

        setattr(obj, attr.split(".")[-1], buf)

    caller.attributes.remove("_building_menu_to_edit")
    return True

def _menu_quitfunc(caller):
    caller.cmdset.add(BuildingMenuCmdSet)
    if caller.ndb._building_menu:
        caller.ndb._building_menu.move(back=True)
