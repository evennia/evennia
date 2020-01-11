"""
Module containing the building menu system.

Evennia contributor: vincent-lg 2018

Building menus are in-game menus, not unlike `EvMenu` though using a
different approach.  Building menus have been specifically designed to edit
information as a builder.  Creating a building menu in a command allows
builders quick-editing of a given object, like a room.  If you follow the
steps below to add the contrib, you will have access to an `@edit` command
that will edit any default object offering to change its key and description.

1. Import the `GenericBuildingCmd` class from this contrib in your `mygame/commands/default_cmdset.py` file:

    ```python
    from evennia.contrib.building_menu import GenericBuildingCmd
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

The `@edit` command will allow you to edit any object.  You will need to
specify the object name or ID as an argument.  For instance: `@edit here`
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
from evennia.contrib.building_menu import BuildingMenu

class RoomBuildingMenu(BuildingMenu):
    # ...
```

Next, override the `init` method.  You can add choices (like the title,
description, and exits choices as seen above) by using the `add_choice`
method.

```
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

```
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

This is a very short introduction.  For more details, see the online tutorial
(https://github.com/evennia/evennia/wiki/Building-menus) or read the
heavily-documented code below.

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


# Constants
_MAX_TEXT_WIDTH = settings.CLIENT_DEFAULT_WIDTH
_CMD_NOMATCH = cmdhandler.CMD_NOMATCH
_CMD_NOINPUT = cmdhandler.CMD_NOINPUT


# Private functions
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
    caller.cmdset.add(
        BuildingMenuCmdSet,
        permanent=caller.ndb._building_menu and caller.ndb._building_menu.persistent or False,
    )
    if caller.ndb._building_menu:
        caller.ndb._building_menu.move(back=True)


def _call_or_get(value, menu=None, choice=None, string=None, obj=None, caller=None):
    """
    Call the value, if appropriate, or just return it.

    Args:
        value (any): the value to obtain.  It might be a callable (see note).

    Kwargs:
        menu (BuildingMenu, optional): the building menu to pass to value
                if it is a callable.
        choice (Choice, optional): the choice to pass to value if a callable.
        string (str, optional): the raw string to pass to value if a callback.
        obj (Object): the object to pass to value if a callable.
        caller (Account or Object, optional): the caller to pass to value
                if a callable.

    Returns:
        The value itself.  If the argument is a function, call it with
        specific arguments (see note).

    Note:
        If `value` is a function, call it with varying arguments.  The
        list of arguments will depend on the argument names in your callable.
        - An argument named `menu` will contain the building menu or None.
        - The `choice` argument will contain the choice or None.
        - The `string` argument will contain the raw string or None.
        - The `obj` argument will contain the object or None.
        - The `caller` argument will contain the caller or None.
        - Any other argument will contain the object (`obj`).
        Thus, you could define callbacks like this:
            def on_enter(menu, caller, obj):
            def on_nomatch(string, choice, menu):
            def on_leave(caller, room): # note that room will contain `obj`

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


# Helper functions, to be used in menu choices


def menu_setattr(menu, choice, obj, string):
    """
    Set the value at the specified attribute.

    Args:
        menu (BuildingMenu): the menu object.
        choice (Chocie): the specific choice.
        obj (Object): the object to modify.
        string (str): the string with the new value.

    Note:
        This function is supposed to be used as a default to
        `BuildingMenu.add_choice`, when an attribute name is specified
        (in the `attr` argument) but no function `on_nomatch` is defined.

    """
    attr = getattr(choice, "attr", None) if choice else None
    if choice is None or string is None or attr is None or menu is None:
        log_err(
            dedent(
                """
                The `menu_setattr` function was called to set the attribute {} of object {} to {},
                but the choice {} of menu {} or another information is missing.
            """.format(
                    attr, obj, repr(string), choice, menu
                )
            ).strip("\n")
        ).strip()
        return

    for part in attr.split(".")[:-1]:
        obj = getattr(obj, part)

    setattr(obj, attr.split(".")[-1], string)
    return True


def menu_quit(caller, menu):
    """
    Quit the menu, closing the CmdSet.

    Args:
        caller (Account or Object): the caller.
        menu (BuildingMenu): the building menu to close.

    Note:
        This callback is used by default when using the
        `BuildingMenu.add_choice_quit` method.  This method is called
        automatically if the menu has no parent.

    """
    if caller is None or menu is None:
        log_err(
            "The function `menu_quit` was called with missing "
            "arguments: caller={}, menu={}".format(caller, menu)
        )

    if caller.cmdset.has(BuildingMenuCmdSet):
        menu.close()
        caller.msg("Closing the building menu.")
    else:
        caller.msg("It looks like the building menu has already been closed.")


def menu_edit(caller, choice, obj):
    """
    Open the EvEditor to edit a specified attribute.

    Args:
        caller (Account or Object): the caller.
        choice (Choice): the choice object.
        obj (Object): the object to edit.

    """
    attr = choice.attr
    caller.db._building_menu_to_edit = (obj, attr)
    caller.cmdset.remove(BuildingMenuCmdSet)
    EvEditor(
        caller,
        loadfunc=_menu_loadfunc,
        savefunc=_menu_savefunc,
        quitfunc=_menu_quitfunc,
        key="editor",
        persistent=True,
    )


# Building menu commands and CmdSet


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
        raw_string = self.args.rstrip()
        if self.menu is None:
            log_err("When CMDNOMATCH was called, the building menu couldn't be found")
            self.caller.msg("|rThe building menu couldn't be found, remove the CmdSet.|n")
            self.caller.cmdset.delete(BuildingMenuCmdSet)
            return

        choice = self.menu.current_choice
        if raw_string in self.menu.keys_go_back:
            if self.menu.keys:
                self.menu.move(back=True)
            elif self.menu.parents:
                self.menu.open_parent_menu()
            else:
                self.menu.display()
        elif choice:
            if choice.nomatch(raw_string):
                self.caller.msg(choice.format_text())
        else:
            for choice in self.menu.relevant_choices:
                if choice.key.lower() == raw_string.lower() or any(
                    raw_string.lower() == alias for alias in choice.aliases
                ):
                    self.menu.move(choice.key)
                    return

            self.msg("|rUnknown command: {}|n.".format(raw_string))


class BuildingMenuCmdSet(CmdSet):

    """Building menu CmdSet."""

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
                menu = BuildingMenu.restore(caller)

        cmds = [CmdNoInput, CmdNoMatch]
        for cmd in cmds:
            self.add(cmd(building_menu=menu))


# Menu classes


class Choice(object):

    """A choice object, created by `add_choice`."""

    def __init__(
        self,
        title,
        key=None,
        aliases=None,
        attr=None,
        text=None,
        glance=None,
        on_enter=None,
        on_nomatch=None,
        on_leave=None,
        menu=None,
        caller=None,
        obj=None,
    ):
        """Constructor.

        Args:
            title (str): the choice's title.
            key (str, optional): the key of the letters to type to access
                    the choice.  If not set, try to guess it based on the title.
            aliases (list of str, optional): the allowed aliases for this choice.
            attr (str, optional): the name of the attribute of 'obj' to set.
            text (str or callable, optional): a text to be displayed for this
                    choice.  It can be a callable.
            glance (str or callable, optional): an at-a-glance summary of the
                    sub-menu shown in the main menu.  It can be set to
                    display the current value of the attribute in the
                    main menu itself.
            menu (BuildingMenu, optional): the parent building menu.
            on_enter (callable, optional): a callable to call when the
                    caller enters into the choice.
            on_nomatch (callable, optional): a callable to call when no
                    match is entered in the choice.
            on_leave (callable, optional): a callable to call when the caller
                    leaves the choice.
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

    def format_text(self):
        """Format the choice text and return it, or an empty string."""
        text = ""
        if self.text:
            text = _call_or_get(
                self.text, menu=self.menu, choice=self, string="", caller=self.caller, obj=self.obj
            )
            text = dedent(text.strip("\n"))
            text = text.format(obj=self.obj, caller=self.caller)

        return text

    def enter(self, string):
        """Called when the user opens the choice.

        Args:
            string (str): the entered string.

        """
        if self.on_enter:
            _call_or_get(
                self.on_enter,
                menu=self.menu,
                choice=self,
                string=string,
                caller=self.caller,
                obj=self.obj,
            )

    def nomatch(self, string):
        """Called when the user entered something in the choice.

        Args:
            string (str): the entered string.

        Returns:
            to_display (bool): The return value of `nomatch` if set or
            `True`.  The rule is that if `no_match` returns `True`,
            then the choice or menu is displayed.

        """
        if self.on_nomatch:
            return _call_or_get(
                self.on_nomatch,
                menu=self.menu,
                choice=self,
                string=string,
                caller=self.caller,
                obj=self.obj,
            )

        return True

    def leave(self, string):
        """Called when the user closes the choice.

        Args:
            string (str): the entered string.

        """
        if self.on_leave:
            _call_or_get(
                self.on_leave,
                menu=self.menu,
                choice=self,
                string=string,
                caller=self.caller,
                obj=self.obj,
            )


class BuildingMenu(object):

    """
    Class allowing to create and set building menus to edit specific objects.

    A building menu is somewhat similar to `EvMenu`, but designed to edit
    objects by builders, although it can be used for players in some contexts.
    You could, for instance, create a building menu to edit a room with a
    sub-menu for the room's key, another for the room's description,
    another for the room's exits, and so on.

    To add choices (simple sub-menus), you should call `add_choice` (see the
    full documentation of this method).  With most arguments, you can
    specify either a plain string or a callback.  This callback will be
    called when the operation is to be performed.

    Some methods are provided for frequent needs (see the `add_choice_*`
    methods).  Some helper functions are defined at the top of this
    module in order to be used as arguments to `add_choice`
    in frequent cases.

    """

    keys_go_back = ["@"]  # The keys allowing to go back in the menu tree
    sep_keys = "."  # The key separator for menus with more than 2 levels
    joker_key = "*"  # The special key meaning "anything" in a choice key
    min_shortcut = 1  # The minimum length of shorcuts when `key` is not set

    def __init__(
        self,
        caller=None,
        obj=None,
        title="Building menu: {obj}",
        keys=None,
        parents=None,
        persistent=False,
    ):
        """Constructor, you shouldn't override.  See `init` instead.

        Args:
            caller (Account or Object): the caller.
            obj (Object): the object to be edited, like a room.
            title (str, optional): the menu title.
            keys (list of str, optional): the starting menu keys (None
                    to start from the first level).
            parents (tuple, optional): information for parent menus,
                    automatically supplied.
            persistent (bool, optional): should this building menu
                    survive a reload/restart?

        Note:
            If some of these options have to be changed, it is
            preferable to do so in the `init` method and not to
            override `__init__`.  For instance:
                class RoomBuildingMenu(BuildingMenu):
                    def init(self, room):
                        self.title = "Menu for room: {obj.key}(#{obj.id})"
                        # ...

        """
        self.caller = caller
        self.obj = obj
        self.title = title
        self.keys = keys or []
        self.parents = parents or ()
        self.persistent = persistent
        self.choices = []
        self.cmds = {}
        self.can_quit = False

        if obj:
            self.init(obj)
            if not parents and not self.can_quit:
                # Automatically add the menu to quit
                self.add_choice_quit(key=None)
            self._add_keys_choice()

    @property
    def current_choice(self):
        """Return the current choice or None.

        Returns:
            choice (Choice): the current choice or None.

        Note:
            We use the menu keys to identify the current position of
            the caller in the menu.  The menu `keys` hold a list of
            keys that should match a choice to be usable.

        """
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

                    if not isinstance(menu_key, str) or menu_key != choice_key:
                        common = False
                        break

                if common:
                    return choice

        return None

    @property
    def relevant_choices(self):
        """Only return the relevant choices according to the current meny key.

        Returns:
            relevant (list of Choice object): the relevant choices.

        Note:
            We use the menu keys to identify the current position of
            the caller in the menu.  The menu `keys` hold a list of
            keys that should match a choice to be usable.

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

                    if not isinstance(menu_key, str) or menu_key != choice_key:
                        common = False
                        break

                if common:
                    relevant.append(choice)

        return relevant

    def _save(self):
        """Save the menu in a attributes on the caller.

        If `persistent` is set to `True`, also save in a persistent attribute.

        """
        self.caller.ndb._building_menu = self

        if self.persistent:
            self.caller.db._building_menu = {
                "class": type(self).__module__ + "." + type(self).__name__,
                "obj": self.obj,
                "title": self.title,
                "keys": self.keys,
                "parents": self.parents,
                "persistent": self.persistent,
            }

    def _add_keys_choice(self):
        """Add the choices' keys if some choices don't have valid keys."""
        # If choices have been added without keys, try to guess them
        for choice in self.choices:
            if not choice.key:
                title = strip_ansi(choice.title.strip()).lower()
                length = self.min_shortcut
                while length <= len(title):
                    i = 0
                    while i < len(title) - length + 1:
                        guess = title[i : i + length]
                        if guess not in self.cmds:
                            choice.key = guess
                            break

                        i += 1

                    if choice.key:
                        break

                    length += 1

                if choice.key:
                    self.cmds[choice.key] = choice
                else:
                    raise ValueError("Cannot guess the key for {}".format(choice))

    def init(self, obj):
        """Create the sub-menu to edit the specified object.

        Args:
            obj (Object): the object to edit.

        Note:
            This method is probably to be overridden in your subclasses.
            Use `add_choice` and its variants to create menu choices.

        """
        pass

    def add_choice(
        self,
        title,
        key=None,
        aliases=None,
        attr=None,
        text=None,
        glance=None,
        on_enter=None,
        on_nomatch=None,
        on_leave=None,
    ):
        """
        Add a choice, a valid sub-menu, in the current builder menu.

        Args:
            title (str): the choice's title.
            key (str, optional): the key of the letters to type to access
                    the sub-neu.  If not set, try to guess it based on the
                    choice title.
            aliases (list of str, optional): the aliases for this choice.
            attr (str, optional): the name of the attribute of 'obj' to set.
                    This is really useful if you want to edit an
                    attribute of the object (that's a frequent need).  If
                    you don't want to do so, just use the `on_*` arguments.
            text (str or callable, optional): a text to be displayed when
                    the menu is opened  It can be a callable.
            glance (str or callable, optional): an at-a-glance summary of the
                    sub-menu shown in the main menu.  It can be set to
                    display the current value of the attribute in the
                    main menu itself.
            on_enter (callable, optional): a callable to call when the
                    caller enters into this choice.
            on_nomatch (callable, optional): a callable to call when
                    the caller enters something in this choice.  If you
                    don't set this argument but you have specified
                    `attr`, then `obj`.`attr` will be set with the value
                    entered by the user.
            on_leave (callable, optional): a callable to call when the
                    caller leaves the choice.

        Returns:
            choice (Choice): the newly-created choice.

        Raises:
            ValueError if the choice cannot be added.

        Note:
            Most arguments can be callables, like functions.  This has the
            advantage of allowing great flexibility.  If you specify
            a callable in most of the arguments, the callable should return
            the value expected by the argument (a str more often than
            not).  For instance, you could set a function to be called
            to get the menu text, which allows for some filtering:
                def text_exits(menu):
                    return "Some text to display"
                class RoomBuildingMenu(BuildingMenu):
                    def init(self):
                        self.add_choice("exits", key="x", text=text_exits)

            The allowed arguments in a callable are specific to the
            argument names (they are not sensitive to orders, not all
            arguments have to be present).  For more information, see
            `_call_or_get`.

        """
        key = key or ""
        key = key.lower()
        aliases = aliases or []
        aliases = [a.lower() for a in aliases]
        if attr and on_nomatch is None:
            on_nomatch = menu_setattr

        if key and key in self.cmds:
            raise ValueError(
                "A conflict exists between {} and {}, both use "
                "key or alias {}".format(self.cmds[key], title, repr(key))
            )

        if attr:
            if glance is None:
                glance = "{obj." + attr + "}"
            if text is None:
                text = """
                        -------------------------------------------------------------------------------
                        {attr} for {{obj}}(#{{obj.id}})

                        You can change this value simply by entering it.
                        Use |y{back}|n to go back to the main menu.

                        Current value: |c{{{obj_attr}}}|n
                """.format(
                    attr=attr, obj_attr="obj." + attr, back="|n or |y".join(self.keys_go_back)
                )

        choice = Choice(
            title,
            key=key,
            aliases=aliases,
            attr=attr,
            text=text,
            glance=glance,
            on_enter=on_enter,
            on_nomatch=on_nomatch,
            on_leave=on_leave,
            menu=self,
            caller=self.caller,
            obj=self.obj,
        )
        self.choices.append(choice)
        if key:
            self.cmds[key] = choice

        for alias in aliases:
            self.cmds[alias] = choice

        return choice

    def add_choice_edit(
        self,
        title="description",
        key="d",
        aliases=None,
        attr="db.desc",
        glance="\n   {obj.db.desc}",
        on_enter=None,
    ):
        """
        Add a simple choice to edit a given attribute in the EvEditor.

        Args:
            title (str, optional): the choice's title.
            key (str, optional): the choice's key.
            aliases (list of str, optional): the choice's aliases.
            glance (str or callable, optional): the at-a-glance description.
            on_enter (callable, optional): a different callable to edit
                    the attribute.

        Returns:
            choice (Choice): the newly-created choice.

        Note:
            This is just a shortcut method, calling `add_choice`.
            If `on_enter` is not set, use `menu_edit` which opens
            an EvEditor to edit the specified attribute.
            When the caller closes the editor (with :q), the menu
            will be re-opened.

        """
        on_enter = on_enter or menu_edit
        return self.add_choice(
            title, key=key, aliases=aliases, attr=attr, glance=glance, on_enter=on_enter, text=""
        )

    def add_choice_quit(self, title="quit the menu", key="q", aliases=None, on_enter=None):
        """
        Add a simple choice just to quit the building menu.

        Args:
            title (str, optional): the choice's title.
            key (str, optional): the choice's key.
            aliases (list of str, optional): the choice's aliases.
            on_enter (callable, optional): a different callable
                    to quit the building menu.

        Note:
            This is just a shortcut method, calling `add_choice`.
            If `on_enter` is not set, use `menu_quit` which simply
            closes the menu and displays a message.  It also
            removes the CmdSet from the caller.  If you supply
            another callable instead, make sure to do the same.

        """
        on_enter = on_enter or menu_quit
        self.can_quit = True
        return self.add_choice(title, key=key, aliases=aliases, on_enter=on_enter)

    def open(self):
        """Open the building menu for the caller.

        Note:
            This method should be called once when the building menu
            has been instanciated.  From there, the building menu will
            be re-created automatically when the server
            reloads/restarts, assuming `persistent` is set to `True`.

        """
        caller = self.caller
        self._save()

        # Remove the same-key cmdset if exists
        if caller.cmdset.has(BuildingMenuCmdSet):
            caller.cmdset.remove(BuildingMenuCmdSet)

        self.caller.cmdset.add(BuildingMenuCmdSet, permanent=self.persistent)
        self.display()

    def open_parent_menu(self):
        """Open the parent menu, using `self.parents`.

        Note:
            You probably don't need to call this method directly,
            since the caller can go back to the parent menu using the
            `keys_go_back` automatically.

        """
        parents = list(self.parents)
        if parents:
            parent_class, parent_obj, parent_keys = parents[-1]
            del parents[-1]

            if self.caller.cmdset.has(BuildingMenuCmdSet):
                self.caller.cmdset.remove(BuildingMenuCmdSet)

            try:
                menu_class = class_from_module(parent_class)
            except Exception:
                log_trace(
                    "BuildingMenu: attempting to load class {} failed".format(repr(parent_class))
                )
                return

            # Create the parent menu
            try:
                building_menu = menu_class(
                    self.caller, parent_obj, keys=parent_keys, parents=tuple(parents)
                )
            except Exception:
                log_trace(
                    "An error occurred while creating building menu {}".format(repr(parent_class))
                )
                return
            else:
                return building_menu.open()

    def open_submenu(self, submenu_class, submenu_obj, parent_keys=None):
        """
        Open a sub-menu, closing the current menu and opening the new one.

        Args:
            submenu_class (str): the submenu class as a Python path.
            submenu_obj (Object): the object to give to the submenu.
            parent_keys (list of str, optional): the parent keys when
                    the submenu is closed.

        Note:
            When the user enters `@` in the submenu, she will go back to
            the current menu, with the `parent_keys` set as its keys.
            Therefore, you should set it on the keys of the choice that
            should be opened when the user leaves the submenu.

        Returns:
            new_menu (BuildingMenu): the new building menu or None.

        """
        parent_keys = parent_keys or []
        parents = list(self.parents)
        parents.append((type(self).__module__ + "." + type(self).__name__, self.obj, parent_keys))
        if self.caller.cmdset.has(BuildingMenuCmdSet):
            self.caller.cmdset.remove(BuildingMenuCmdSet)

        # Shift to the new menu
        try:
            menu_class = class_from_module(submenu_class)
        except Exception:
            log_trace(
                "BuildingMenu: attempting to load class {} failed".format(repr(submenu_class))
            )
            return

        # Create the submenu
        try:
            building_menu = menu_class(self.caller, submenu_obj, parents=parents)
        except Exception:
            log_trace(
                "An error occurred while creating building menu {}".format(repr(submenu_class))
            )
            return
        else:
            return building_menu.open()

    def move(self, key=None, back=False, quiet=False, string=""):
        """
        Move inside the menu.

        Args:
            key (any): the portion of the key to add to the current
                    menu keys.  If you wish to go back in the menu
                    tree, don't provide a `key`, just set `back` to `True`.
            back (bool, optional): go back in the menu (`False` by default).
            quiet (bool, optional): should the menu or choice be
                    displayed afterward?
            string (str, optional): the string sent by the caller to move.

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
            choice.leave("")

        if not back:  # Move forward
            if not key:
                raise ValueError("you are asking to move forward, you should specify a key.")

            self.keys.append(key)
        else:  # Move backward
            if not self.keys:
                raise ValueError(
                    "you already are at the top of the tree, you cannot move backward."
                )

            del self.keys[-1]

        self._save()
        choice = self.current_choice
        if choice:
            choice.enter(string)

        if not quiet:
            self.display()

    def close(self):
        """Close the building menu, removing the CmdSet."""
        if self.caller.cmdset.has(BuildingMenuCmdSet):
            self.caller.cmdset.delete(BuildingMenuCmdSet)
        if self.caller.attributes.has("_building_menu"):
            self.caller.attributes.remove("_building_menu")
        if self.caller.nattributes.has("_building_menu"):
            self.caller.nattributes.remove("_building_menu")

    # Display methods.  Override for customization
    def display_title(self):
        """Return the menu title to be displayed."""
        return _call_or_get(self.title, menu=self, obj=self.obj, caller=self.caller).format(
            obj=self.obj
        )

    def display_choice(self, choice):
        """Display the specified choice.

        Args:
            choice (Choice): the menu choice.

        """
        title = _call_or_get(
            choice.title, menu=self, choice=choice, obj=self.obj, caller=self.caller
        )
        clear_title = title.lower()
        pos = clear_title.find(choice.key.lower())
        ret = " "
        if pos >= 0:
            ret += title[:pos] + "[|y" + choice.key.title() + "|n]" + title[pos + len(choice.key) :]
        else:
            ret += "[|y" + choice.key.title() + "|n] " + title

        if choice.glance:
            glance = _call_or_get(
                choice.glance, menu=self, choice=choice, caller=self.caller, string="", obj=self.obj
            )
            glance = glance.format(obj=self.obj, caller=self.caller)

            ret += ": " + glance

        return ret

    def display(self):
        """Display the entire menu or a single choice, depending on the keys."""
        choice = self.current_choice
        if self.keys and choice:
            text = choice.format_text()
        else:
            text = self.display_title() + "\n"
            for choice in self.relevant_choices:
                text += "\n" + self.display_choice(choice)

        self.caller.msg(text)

    @staticmethod
    def restore(caller):
        """Restore the building menu for the caller.

        Args:
            caller (Account or Object): the caller.

        Note:
            This method should be automatically called if a menu is
            saved in the caller, but the object itself cannot be found.

        """
        menu = caller.db._building_menu
        if menu:
            class_name = menu.get("class")
            if not class_name:
                log_err(
                    "BuildingMenu: on caller {}, a persistent attribute holds building menu "
                    "data, but no class could be found to restore the menu".format(caller)
                )
                return

            try:
                menu_class = class_from_module(class_name)
            except Exception:
                log_trace(
                    "BuildingMenu: attempting to load class {} failed".format(repr(class_name))
                )
                return

            # Create the menu
            obj = menu.get("obj")
            keys = menu.get("keys")
            title = menu.get("title", "")
            parents = menu.get("parents")
            persistent = menu.get("persistent", False)
            try:
                building_menu = menu_class(
                    caller, obj, title=title, keys=keys, parents=parents, persistent=persistent
                )
            except Exception:
                log_trace(
                    "An error occurred while creating building menu {}".format(repr(class_name))
                )
                return

            return building_menu


# Generic building menu and command
class GenericBuildingMenu(BuildingMenu):

    """A generic building menu, allowing to edit any object.

    This is more a demonstration menu.  By default, it allows to edit the
    object key and description.  Nevertheless, it will be useful to demonstrate
    how building menus are meant to be used.

    """

    def init(self, obj):
        """Build the meny, adding the 'key' and 'description' choices.

        Args:
            obj (Object): any object to be edited, like a character or room.

        Note:
            The 'quit' choice will be automatically added, though you can
            call `add_choice_quit` to add this choice with different options.

        """
        self.add_choice(
            "key",
            key="k",
            attr="key",
            glance="{obj.key}",
            text="""
                -------------------------------------------------------------------------------
                Editing the key of {{obj.key}}(#{{obj.id}})

                You can change the simply by entering it.
                Use |y{back}|n to go back to the main menu.

                Current key: |c{{obj.key}}|n
        """.format(
                back="|n or |y".join(self.keys_go_back)
            ),
        )
        self.add_choice_edit("description", key="d", attr="db.desc")


class GenericBuildingCmd(Command):

    """
    Generic building command.

    Syntax:
      @edit [object]

    Open a building menu to edit the specified object.  This menu allows to
    change the object's key and description.

    Examples:
      @edit here
      @edit self
      @edit #142

    """

    key = "@edit"

    def func(self):
        if not self.args.strip():
            self.msg("You should provide an argument to this function: the object to edit.")
            return

        obj = self.caller.search(self.args.strip(), global_search=True)
        if not obj:
            return

        menu = GenericBuildingMenu(self.caller, obj)
        menu.open()
