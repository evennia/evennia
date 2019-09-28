"""
Module containing the commands of the in-game Python system.
"""

from datetime import datetime

from django.conf import settings
from evennia import Command
from evennia.utils.ansi import raw
from evennia.utils.eveditor import EvEditor
from evennia.utils.evtable import EvTable
from evennia.utils.utils import class_from_module, time_format
from evennia.contrib.ingame_python.utils import get_event_handler

COMMAND_DEFAULT_CLASS = class_from_module(settings.COMMAND_DEFAULT_CLASS)

# Permissions
WITH_VALIDATION = getattr(settings, "callbackS_WITH_VALIDATION", None)
WITHOUT_VALIDATION = getattr(settings, "callbackS_WITHOUT_VALIDATION", "developer")
VALIDATING = getattr(settings, "callbackS_VALIDATING", "developer")

# Split help text
BASIC_HELP = "Add, edit or delete callbacks."

BASIC_USAGES = [
    "@call <object name> [= <callback name>]",
    "@call/add <object name> = <callback name> [parameters]",
    "@call/edit <object name> = <callback name> [callback number]",
    "@call/del <object name> = <callback name> [callback number]",
    "@call/tasks [object name [= <callback name>]]",
]

BASIC_SWITCHES = [
    "add    - add and edit a new callback",
    "edit   - edit an existing callback",
    "del    - delete an existing callback",
    "tasks  - show the list of differed tasks",
]

VALIDATOR_USAGES = ["@call/accept [object name = <callback name> [callback number]]"]

VALIDATOR_SWITCHES = ["accept - show callbacks to be validated or accept one"]

BASIC_TEXT = """
This command is used to manipulate callbacks.  A callback can be linked to
an object, to fire at a specific moment.  You can use the command without
switches to see what callbacks are active on an object:
  @call self
You can also specify a callback name if you want the list of callbacks
associated with this object of this name:
  @call north = can_traverse
You can also add a number after the callback name to see details on one callback:
  @call here = say 2
You can also add, edit or remove callbacks using the add, edit or del switches.
Additionally, you can see the list of differed tasks created by callbacks
(chained events to be called) using the /tasks switch.
"""

VALIDATOR_TEXT = """
You can also use this command to validate callbacks.  Depending on your game
setting, some users might be allowed to add new callbacks, but these callbacks
will not be fired until you accept them.  To see the callbacks needing
validation, enter the /accept switch without argument:
  @call/accept
A table will show you the callbacks that are not validated yet, who created
them and when.  You can then accept a specific callback:
  @call here = enter 1
Use the /del switch to remove callbacks that should not be connected.
"""


class CmdCallback(COMMAND_DEFAULT_CLASS):

    """
    Command to edit callbacks.
    """

    key = "@call"
    aliases = ["@callback", "@callbacks", "@calls"]
    locks = "cmd:perm({})".format(VALIDATING)
    if WITH_VALIDATION:
        locks += " or perm({})".format(WITH_VALIDATION)
    help_category = "Building"

    def get_help(self, caller, cmdset):
        """
        Return the help message for this command and this caller.

        The help text of this specific command will vary depending
        on user permission.

        Args:
            caller (Object or Account): the caller asking for help on the command.
            cmdset (CmdSet): the command set (if you need additional commands).

        Returns:
            docstring (str): the help text to provide the caller for this command.

        """
        lock = "perm({}) or perm(callbacks_validating)".format(VALIDATING)
        validator = caller.locks.check_lockstring(caller, lock)
        text = "\n" + BASIC_HELP + "\n\nUsages:\n  "

        # Usages
        text += "\n  ".join(BASIC_USAGES)
        if validator:
            text += "\n  " + "\n  ".join(VALIDATOR_USAGES)

        # Switches
        text += "\n\nSwitches:\n  "
        text += "\n  ".join(BASIC_SWITCHES)
        if validator:
            text += "\n  " + "\n  ".join(VALIDATOR_SWITCHES)

        # Text
        text += "\n" + BASIC_TEXT
        if validator:
            text += "\n" + VALIDATOR_TEXT

        return text

    def func(self):
        """Command body."""
        caller = self.caller
        lock = "perm({}) or perm(events_validating)".format(VALIDATING)
        validator = caller.locks.check_lockstring(caller, lock)
        lock = "perm({}) or perm(events_without_validation)".format(WITHOUT_VALIDATION)
        autovalid = caller.locks.check_lockstring(caller, lock)

        # First and foremost, get the callback handler and set other variables
        self.handler = get_event_handler()
        self.obj = None
        rhs = self.rhs or ""
        self.callback_name, sep, self.parameters = rhs.partition(" ")
        self.callback_name = self.callback_name.lower()
        self.is_validator = validator
        self.autovalid = autovalid
        if self.handler is None:
            caller.msg("The event handler is not running, can't " "access the event system.")
            return

        # Before the equal sign, there is an object name or nothing
        if self.lhs:
            self.obj = caller.search(self.lhs)
            if not self.obj:
                return

        # Switches are mutually exclusive
        switch = self.switches and self.switches[0] or ""
        if switch in ("", "add", "edit", "del") and self.obj is None:
            caller.msg("Specify an object's name or #ID.")
            return

        if switch == "":
            self.list_callbacks()
        elif switch == "add":
            self.add_callback()
        elif switch == "edit":
            self.edit_callback()
        elif switch == "del":
            self.del_callback()
        elif switch == "accept" and validator:
            self.accept_callback()
        elif switch in ["tasks", "task"]:
            self.list_tasks()
        else:
            caller.msg("Mutually exclusive or invalid switches were " "used, cannot proceed.")

    def list_callbacks(self):
        """Display the list of callbacks connected to the object."""
        obj = self.obj
        callback_name = self.callback_name
        parameters = self.parameters
        callbacks = self.handler.get_callbacks(obj)
        types = self.handler.get_events(obj)

        if callback_name:
            # Check that the callback name can be found in this object
            created = callbacks.get(callback_name)
            if created is None:
                self.msg("No callback {} has been set on {}.".format(callback_name, obj))
                return

            if parameters:
                # Check that the parameter points to an existing callback
                try:
                    number = int(parameters) - 1
                    assert number >= 0
                    callback = callbacks[callback_name][number]
                except (ValueError, AssertionError, IndexError):
                    self.msg(
                        "The callback {} {} cannot be found in {}.".format(
                            callback_name, parameters, obj
                        )
                    )
                    return

                # Display the callback's details
                author = callback.get("author")
                author = author.key if author else "|gUnknown|n"
                updated_by = callback.get("updated_by")
                updated_by = updated_by.key if updated_by else "|gUnknown|n"
                created_on = callback.get("created_on")
                created_on = (
                    created_on.strftime("%Y-%m-%d %H:%M:%S") if created_on else "|gUnknown|n"
                )
                updated_on = callback.get("updated_on")
                updated_on = (
                    updated_on.strftime("%Y-%m-%d %H:%M:%S") if updated_on else "|gUnknown|n"
                )
                msg = "Callback {} {} of {}:".format(callback_name, parameters, obj)
                msg += "\nCreated by {} on {}.".format(author, created_on)
                msg += "\nUpdated by {} on {}".format(updated_by, updated_on)

                if self.is_validator:
                    if callback.get("valid"):
                        msg += "\nThis callback is |rconnected|n and active."
                    else:
                        msg += "\nThis callback |rhasn't been|n accepted yet."

                msg += "\nCallback code:\n"
                msg += raw(callback["code"])
                self.msg(msg)
                return

            # No parameter has been specified, display the table of callbacks
            cols = ["Number", "Author", "Updated", "Param"]
            if self.is_validator:
                cols.append("Valid")

            table = EvTable(*cols, width=78)
            table.reformat_column(0, align="r")
            now = datetime.now()
            for i, callback in enumerate(created):
                author = callback.get("author")
                author = author.key if author else "|gUnknown|n"
                updated_on = callback.get("updated_on")
                if updated_on is None:
                    updated_on = callback.get("created_on")

                if updated_on:
                    updated_on = "{} ago".format(
                        time_format((now - updated_on).total_seconds(), 4).capitalize()
                    )
                else:
                    updated_on = "|gUnknown|n"
                parameters = callback.get("parameters", "")

                row = [str(i + 1), author, updated_on, parameters]
                if self.is_validator:
                    row.append("Yes" if callback.get("valid") else "No")
                table.add_row(*row)

            self.msg(str(table))
        else:
            names = list(set(list(types.keys()) + list(callbacks.keys())))
            table = EvTable("Callback name", "Number", "Description", valign="t", width=78)
            table.reformat_column(0, width=20)
            table.reformat_column(1, width=10, align="r")
            table.reformat_column(2, width=48)
            for name in sorted(names):
                number = len(callbacks.get(name, []))
                lines = sum(len(e["code"].splitlines()) for e in callbacks.get(name, []))
                no = "{} ({})".format(number, lines)
                description = types.get(name, (None, "Chained event."))[1]
                description = description.strip("\n").splitlines()[0]
                table.add_row(name, no, description)

            self.msg(str(table))

    def add_callback(self):
        """Add a callback."""
        obj = self.obj
        callback_name = self.callback_name
        types = self.handler.get_events(obj)

        # Check that the callback exists
        if not callback_name.startswith("chain_") and callback_name not in types:
            self.msg(
                "The callback name {} can't be found in {} of "
                "typeclass {}.".format(callback_name, obj, type(obj))
            )
            return

        definition = types.get(callback_name, (None, "Chained event."))
        description = definition[1]
        self.msg(raw(description.strip("\n")))

        # Open the editor
        callback = self.handler.add_callback(
            obj, callback_name, "", self.caller, False, parameters=self.parameters
        )

        # Lock this callback right away
        self.handler.db.locked.append((obj, callback_name, callback["number"]))

        # Open the editor for this callback
        self.caller.db._callback = callback
        EvEditor(
            self.caller,
            loadfunc=_ev_load,
            savefunc=_ev_save,
            quitfunc=_ev_quit,
            key="Callback {} of {}".format(callback_name, obj),
            persistent=True,
            codefunc=_ev_save,
        )

    def edit_callback(self):
        """Edit a callback."""
        obj = self.obj
        callback_name = self.callback_name
        parameters = self.parameters
        callbacks = self.handler.get_callbacks(obj)
        types = self.handler.get_events(obj)

        # If no callback name is specified, display the list of callbacks
        if not callback_name:
            self.list_callbacks()
            return

        # Check that the callback exists
        if callback_name not in callbacks:
            self.msg("The callback name {} can't be found in {}.".format(callback_name, obj))
            return

        # If there's only one callback, just edit it
        if len(callbacks[callback_name]) == 1:
            number = 0
            callback = callbacks[callback_name][0]
        else:
            if not parameters:
                self.msg("Which callback do you wish to edit?  Specify a number.")
                self.list_callbacks()
                return

            # Check that the parameter points to an existing callback
            try:
                number = int(parameters) - 1
                assert number >= 0
                callback = callbacks[callback_name][number]
            except (ValueError, AssertionError, IndexError):
                self.msg(
                    "The callback {} {} cannot be found in {}.".format(
                        callback_name, parameters, obj
                    )
                )
                return

        # If caller can't edit without validation, forbid editing
        # others' works
        if not self.autovalid and callback["author"] is not self.caller:
            self.msg("You cannot edit this callback created by someone else.")
            return

        # If the callback is locked (edited by someone else)
        if (obj, callback_name, number) in self.handler.db.locked:
            self.msg("This callback is locked, you cannot edit it.")
            return

        self.handler.db.locked.append((obj, callback_name, number))

        # Check the definition of the callback
        definition = types.get(callback_name, (None, "Chained event."))
        description = definition[1]
        self.msg(raw(description.strip("\n")))

        # Open the editor
        callback = dict(callback)
        self.caller.db._callback = callback
        EvEditor(
            self.caller,
            loadfunc=_ev_load,
            savefunc=_ev_save,
            quitfunc=_ev_quit,
            key="Callback {} of {}".format(callback_name, obj),
            persistent=True,
            codefunc=_ev_save,
        )

    def del_callback(self):
        """Delete a callback."""
        obj = self.obj
        callback_name = self.callback_name
        parameters = self.parameters
        callbacks = self.handler.get_callbacks(obj)
        types = self.handler.get_events(obj)

        # If no callback name is specified, display the list of callbacks
        if not callback_name:
            self.list_callbacks()
            return

        # Check that the callback exists
        if callback_name not in callbacks:
            self.msg("The callback name {} can't be found in {}.".format(callback_name, obj))
            return

        # If there's only one callback, just delete it
        if len(callbacks[callback_name]) == 1:
            number = 0
            callback = callbacks[callback_name][0]
        else:
            if not parameters:
                self.msg("Which callback do you wish to delete?  Specify " "a number.")
                self.list_callbacks()
                return

            # Check that the parameter points to an existing callback
            try:
                number = int(parameters) - 1
                assert number >= 0
                callback = callbacks[callback_name][number]
            except (ValueError, AssertionError, IndexError):
                self.msg(
                    "The callback {} {} cannot be found in {}.".format(
                        callback_name, parameters, obj
                    )
                )
                return

        # If caller can't edit without validation, forbid deleting
        # others' works
        if not self.autovalid and callback["author"] is not self.caller:
            self.msg("You cannot delete this callback created by someone else.")
            return

        # If the callback is locked (edited by someone else)
        if (obj, callback_name, number) in self.handler.db.locked:
            self.msg("This callback is locked, you cannot delete it.")
            return

        # Delete the callback
        self.handler.del_callback(obj, callback_name, number)
        self.msg("The callback {}[{}] of {} was deleted.".format(callback_name, number + 1, obj))

    def accept_callback(self):
        """Accept a callback."""
        obj = self.obj
        callback_name = self.callback_name
        parameters = self.parameters

        # If no object, display the list of callbacks to be checked
        if obj is None:
            table = EvTable("ID", "Type", "Object", "Name", "Updated by", "On", width=78)
            table.reformat_column(0, align="r")
            now = datetime.now()
            for obj, name, number in self.handler.db.to_valid:
                callbacks = self.handler.get_callbacks(obj).get(name)
                if callbacks is None:
                    continue

                try:
                    callback = callbacks[number]
                except IndexError:
                    continue

                type_name = obj.typeclass_path.split(".")[-1]
                by = callback.get("updated_by")
                by = by.key if by else "|gUnknown|n"
                updated_on = callback.get("updated_on")
                if updated_on is None:
                    updated_on = callback.get("created_on")

                if updated_on:
                    updated_on = "{} ago".format(
                        time_format((now - updated_on).total_seconds(), 4).capitalize()
                    )
                else:
                    updated_on = "|gUnknown|n"

                table.add_row(obj.id, type_name, obj, name, by, updated_on)
            self.msg(str(table))
            return

        # An object was specified
        callbacks = self.handler.get_callbacks(obj)
        types = self.handler.get_events(obj)

        # If no callback name is specified, display the list of callbacks
        if not callback_name:
            self.list_callbacks()
            return

        # Check that the callback exists
        if callback_name not in callbacks:
            self.msg("The callback name {} can't be found in {}.".format(callback_name, obj))
            return

        if not parameters:
            self.msg("Which callback do you wish to accept?  Specify a number.")
            self.list_callbacks()
            return

        # Check that the parameter points to an existing callback
        try:
            number = int(parameters) - 1
            assert number >= 0
            callback = callbacks[callback_name][number]
        except (ValueError, AssertionError, IndexError):
            self.msg(
                "The callback {} {} cannot be found in {}.".format(callback_name, parameters, obj)
            )
            return

        # Accept the callback
        if callback["valid"]:
            self.msg("This callback has already been accepted.")
        else:
            self.handler.accept_callback(obj, callback_name, number)
            self.msg(
                "The callback {} {} of {} has been accepted.".format(callback_name, parameters, obj)
            )

    def list_tasks(self):
        """List the active tasks."""
        obj = self.obj
        callback_name = self.callback_name
        handler = self.handler
        tasks = [(k, v[0], v[1], v[2]) for k, v in handler.db.tasks.items()]
        if obj:
            tasks = [task for task in tasks if task[2] is obj]
        if callback_name:
            tasks = [task for task in tasks if task[3] == callback_name]

        tasks.sort()
        table = EvTable("ID", "Object", "Callback", "In", width=78)
        table.reformat_column(0, align="r")
        now = datetime.now()
        for task_id, future, obj, callback_name in tasks:
            key = obj.get_display_name(self.caller)
            delta = time_format((future - now).total_seconds(), 1)
            table.add_row(task_id, key, callback_name, delta)

        self.msg(str(table))


# Private functions to handle editing


def _ev_load(caller):
    return caller.db._callback and caller.db._callback.get("code", "") or ""


def _ev_save(caller, buf):
    """Save and add the callback."""
    lock = "perm({}) or perm(events_without_validation)".format(WITHOUT_VALIDATION)
    autovalid = caller.locks.check_lockstring(caller, lock)
    callback = caller.db._callback
    handler = get_event_handler()
    if (
        not handler
        or not callback
        or not all(key in callback for key in ("obj", "name", "number", "valid"))
    ):
        caller.msg("Couldn't save this callback.")
        return False

    if (callback["obj"], callback["name"], callback["number"]) in handler.db.locked:
        handler.db.locked.remove((callback["obj"], callback["name"], callback["number"]))

    handler.edit_callback(
        callback["obj"], callback["name"], callback["number"], buf, caller, valid=autovalid
    )
    return True


def _ev_quit(caller):
    callback = caller.db._callback
    handler = get_event_handler()
    if (
        not handler
        or not callback
        or not all(key in callback for key in ("obj", "name", "number", "valid"))
    ):
        caller.msg("Couldn't save this callback.")
        return False

    if (callback["obj"], callback["name"], callback["number"]) in handler.db.locked:
        handler.db.locked.remove((callback["obj"], callback["name"], callback["number"]))

    del caller.db._callback
    caller.msg("Exited the code editor.")
