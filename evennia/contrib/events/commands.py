"""
Module containing the commands of the event system.
"""

from datetime import datetime

from django.conf import settings
from evennia import Command
from evennia.utils.ansi import raw
from evennia.utils.eveditor import EvEditor
from evennia.utils.evtable import EvTable
from evennia.utils.utils import class_from_module, time_format
from evennia.contrib.events.custom import get_event_handler

COMMAND_DEFAULT_CLASS = class_from_module(settings.COMMAND_DEFAULT_CLASS)

# Permissions
WITH_VALIDATION = getattr(settings, "EVENTS_WITH_VALIDATION", None)
WITHOUT_VALIDATION = getattr(settings, "EVENTS_WITHOUT_VALIDATION",
        "immortals")
VALIDATING = getattr(settings, "EVENTS_VALIDATING", "immortals")

# Split help text
BASIC_HELP = "Add, edit or delete events."

BASIC_USAGES = [
        "@event <object name> [= <event name>]",
        "@event/add <object name> = <event name> [parameters]",
        "@event/edit <object name> = <event name> [event number]",
        "@event/del <object name> = <event name> [event number]",
        "@event/tasks [object name [= <event name>]]",
]

BASIC_SWITCHES = [
    "add    - add and edit a new event",
    "edit   - edit an existing event",
    "del    - delete an existing event",
    "tasks  - show the list of differed tasks",
]

VALIDATOR_USAGES = [
        "@event/accept [object name = <event name> [event number]]",
]

VALIDATOR_SWITCHES = [
    "accept - show events to be validated or accept one",
]

BASIC_TEXT = """
This command is used to manipulate events.  An event can be linked to
an object, to fire at a specific moment.  You can use the command without
switches to see what event are active on an object:
  @event self
You can also specify an event name if you want the list of events associated
with this object of this name:
  @event north = can_traverse
You can also add a number after the event name to see details on one event:
  @event here = say 2
You can also add, edit or remove events using the add, edit or del switches.
Additionally, you can see the list of differed tasks created by events
(chained events to be called) using the /tasks switch.
"""

VALIDATOR_TEXT = """
You can also use this command to validate events.  Depending on your game
setting, some users might be allowed to add new events, but these events
will not be fired until you accept them.  To see the events needing
validation, enter the /accept switch without argument:
  @event/accept
A table will show you the events that are not validated yet, who created
them and when.  You can then accept a specific event:
  @event here = enter 1
Use the /del switch to remove events that should not be connected.
"""

class CmdEvent(COMMAND_DEFAULT_CLASS):

    """
    Command to edit events.
    """

    key = "@event"
    aliases = ["@events", "@ev"]
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
            caller (Object or Player): the caller asking for help on the command.
            cmdset (CmdSet): the command set (if you need additional commands).

        Returns:
            docstring (str): the help text to provide the caller for this command.

        """
        lock = "perm({}) or perm(events_validating)".format(VALIDATING)
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
        lock = "perm({}) or perm(events_without_validation)".format(
            WITHOUT_VALIDATION)
        autovalid = caller.locks.check_lockstring(caller, lock)

        # First and foremost, get the event handler and set other variables
        self.handler = get_event_handler()
        self.obj = None
        rhs = self.rhs or ""
        self.event_name, sep, self.parameters = rhs.partition(" ")
        self.event_name = self.event_name.lower()
        self.is_validator = validator
        self.autovalid = autovalid
        if self.handler is None:
            caller.msg("The event handler is not running, can't " \
                    "access the event system.")
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
            self.list_events()
        elif switch == "add":
            self.add_event()
        elif switch == "edit":
            self.edit_event()
        elif switch == "del":
            self.del_event()
        elif switch == "accept" and validator:
            self.accept_event()
        elif switch in ["tasks", "task"]:
            self.list_tasks()
        else:
            caller.msg("Mutually exclusive or invalid switches were " \
                    "used, cannot proceed.")

    def list_events(self):
        """Display the list of events connected to the object."""
        obj = self.obj
        event_name = self.event_name
        parameters = self.parameters
        events = self.handler.get_events(obj)
        types = self.handler.get_event_types(obj)

        if event_name:
            # Check that the event name can be found in this object
            created = events.get(event_name)
            if created is None:
                self.msg("No event {} has been set on {}.".format(event_name,
                        obj))
                return

            if parameters:
                # Check that the parameter points to an existing event
                try:
                    number = int(parameters) - 1
                    assert number >= 0
                    event = events[event_name][number]
                except (ValueError, AssertionError, IndexError):
                    self.msg("The event {} {} cannot be found in {}.".format(
                            event_name, parameters, obj))
                    return

                # Display the events' details
                author = event.get("author")
                author = author.key if author else "|gUnknown|n"
                updated_by = event.get("updated_by")
                updated_by = updated_by.key if updated_by else "|gUnknown|n"
                created_on = event.get("created_on")
                created_on = created_on.strftime("%Y-%m-%d %H:%M:%S") \
                        if created_on else "|gUnknown|n"
                updated_on = event.get("updated_on")
                updated_on = updated_on.strftime("%Y-%m-%d %H:%M:%S") \
                        if updated_on else "|gUnknown|n"
                msg = "Event {} {} of {}:".format(event_name, parameters, obj)
                msg += "\nCreated by {} on {}.".format(author, created_on)
                msg += "\nUpdated by {} on {}".format(updated_by, updated_on)

                if self.is_validator:
                    if event.get("valid"):
                        msg += "\nThis event is |rconnected|n and active."
                    else:
                        msg += "\nThis event |rhasn't been|n accepted yet."

                msg += "\nEvent code:\n"
                msg += raw(event["code"])
                self.msg(msg)
                return

            # No parameter has been specified, display the table of events
            cols = ["Number", "Author", "Updated", "Param"]
            if self.is_validator:
                cols.append("Valid")

            table = EvTable(*cols, width=78)
            table.reformat_column(0, align="r")
            now = datetime.now()
            for i, event in enumerate(created):
                author = event.get("author")
                author = author.key if author else "|gUnknown|n"
                updated_on = event.get("updated_on")
                if updated_on is None:
                    updated_on = event.get("created_on")

                if updated_on:
                    updated_on = "{} ago".format(time_format(
                            (now - updated_on).total_seconds(),
                            4).capitalize())
                else:
                    updated_on = "|gUnknown|n"
                parameters = event.get("parameters", "")

                row = [str(i + 1), author, updated_on, parameters]
                if self.is_validator:
                    row.append("Yes" if event.get("valid") else "No")
                table.add_row(*row)

            self.msg(unicode(table))
        else:
            names = list(set(list(types.keys()) + list(events.keys())))
            table = EvTable("Event name", "Number", "Description",
                    valign="t", width=78)
            table.reformat_column(0, width=20)
            table.reformat_column(1, width=10, align="r")
            table.reformat_column(2, width=48)
            for name in sorted(names):
                number = len(events.get(name, []))
                lines = sum(len(e["code"].splitlines()) for e in \
                        events.get(name, []))
                no = "{} ({})".format(number, lines)
                description = types.get(name, (None, "Chained event."))[1]
                description = description.splitlines()[0]
                table.add_row(name, no, description)

            self.msg(unicode(table))

    def add_event(self):
        """Add an event."""
        obj = self.obj
        event_name = self.event_name
        types = self.handler.get_event_types(obj)

        # Check that the event exists
        if not event_name.startswith("chain_") and not event_name in types:
            self.msg("The event name {} can't be found in {} of " \
                    "typeclass {}.".format(event_name, obj, type(obj)))
            return

        definition = types.get(event_name, (None, "Chain event"))
        description = definition[1]
        self.msg(description)

        # Open the editor
        event = self.handler.add_event(obj, event_name, "",
                self.caller, False, parameters=self.parameters)

        # Lock this event right away
        self.handler.db.locked.append((obj, event_name, event["number"]))

        # Open the editor for this event
        self.caller.db._event = event
        EvEditor(self.caller, loadfunc=_ev_load, savefunc=_ev_save,
                quitfunc=_ev_quit, key="Event {} of {}".format(
                event_name, obj), persistent=True, codefunc=_ev_save)

    def edit_event(self):
        """Edit an event."""
        obj = self.obj
        event_name = self.event_name
        parameters = self.parameters
        events = self.handler.get_events(obj)
        types = self.handler.get_event_types(obj)

        # If no event name is specified, display the list of events
        if not event_name:
            self.list_events()
            return

        # Check that the event exists
        if not event_name in events:
            self.msg("The event name {} can't be found in {}.".format(
                    event_name, obj))
            return

        # If there's only one event, just edit it
        if len(events[event_name]) == 1:
            number = 0
            event = events[event_name][0]
        else:
            if not parameters:
                self.msg("Which event do you wish to edit?  Specify a number.")
                self.list_events()
                return

            # Check that the parameter points to an existing event
            try:
                number = int(parameters) - 1
                assert number >= 0
                event = events[event_name][number]
            except (ValueError, AssertionError, IndexError):
                self.msg("The event {} {} cannot be found in {}.".format(
                        event_name, parameters, obj))
                return

        # If caller can't edit without validation, forbid editing
        # others' works
        if not self.autovalid and event["author"] is not self.caller:
            self.msg("You cannot edit this event created by someone else.")
            return

        # If the event is locked (edited by someone else)
        if (obj, event_name, number) in self.handler.db.locked:
            self.msg("This event is locked, you cannot edit it.")
            return
        self.handler.db.locked.append((obj, event_name, number))

        # Check the definition of the event
        definition = types.get(event_name, (None, "Chained event"))
        description = definition[1]
        self.msg(description)

        # Open the editor
        event = dict(event)
        event["obj"] = obj
        event["name"] = event_name
        event["number"] = number
        self.caller.db._event = event
        EvEditor(self.caller, loadfunc=_ev_load, savefunc=_ev_save,
                quitfunc=_ev_quit, key="Event {} of {}".format(
                event_name, obj), persistent=True, codefunc=_ev_save)

    def del_event(self):
        """Delete an event."""
        obj = self.obj
        event_name = self.event_name
        parameters = self.parameters
        events = self.handler.get_events(obj)
        types = self.handler.get_event_types(obj)

        # If no event name is specified, display the list of events
        if not event_name:
            self.list_events()
            return

        # Check that the event exists
        if not event_name in events:
            self.msg("The event name {} can't be found in {}.".format(
                    event_name, obj))
            return

        # If there's only one event, just delete it
        if len(events[event_name]) == 1:
            number = 0
            event = events[event_name][0]
        else:
            if not parameters:
                self.msg("Which event do you wish to delete?  Specify " \
                        "a number.")
                self.list_events()
                return

            # Check that the parameter points to an existing event
            try:
                number = int(parameters) - 1
                assert number >= 0
                event = events[event_name][number]
            except (ValueError, AssertionError, IndexError):
                self.msg("The event {} {} cannot be found in {}.".format(
                        event_name, parameters, obj))
                return

        # If caller can't edit without validation, forbid deleting
        # others' works
        if not self.autovalid and event["author"] is not self.caller:
            self.msg("You cannot delete this event created by someone else.")
            return

        # If the event is locked (edited by someone else)
        if (obj, event_name, number) in self.handler.db.locked:
            self.msg("This event is locked, you cannot delete it.")
            return

        # Delete the event
        self.handler.del_event(obj, event_name, number)
        self.msg("The event {} {} of {} was deleted.".format(
                obj, event_name, parameters))

    def accept_event(self):
        """Accept an event."""
        obj = self.obj
        event_name = self.event_name
        parameters = self.parameters

        # If no object, display the list of events to be checked
        if obj is None:
            table = EvTable("ID", "Type", "Object", "Name", "Updated by",
                    "On", width=78)
            table.reformat_column(0, align="r")
            now = datetime.now()
            for obj, name, number in self.handler.db.to_valid:
                events = self.handler.db.events.get(obj, {}).get(name)
                if events is None:
                    continue

                try:
                    event = events[number]
                except IndexError:
                    continue

                type_name = obj.typeclass_path.split(".")[-1]
                by = event.get("updated_by")
                by = by.key if by else "|gUnknown|n"
                updated_on = event.get("updated_on")
                if updated_on is None:
                    updated_on = event.get("created_on")

                if updated_on:
                    updated_on = "{} ago".format(time_format(
                            (now - updated_on).total_seconds(),
                            4).capitalize())
                else:
                    updated_on = "|gUnknown|n"

                table.add_row(obj.id, type_name, obj, name, by, updated_on)
            self.msg(unicode(table))
            return

        # An object was specified
        events = self.handler.get_events(obj)
        types = self.handler.get_event_types(obj)

        # If no event name is specified, display the list of events
        if not event_name:
            self.list_events()
            return

        # Check that the event exists
        if not event_name in events:
            self.msg("The event name {} can't be found in {}.".format(
                    event_name, obj))
            return

        if not parameters:
            self.msg("Which event do you wish to accept?  Specify a number.")
            self.list_events()
            return

        # Check that the parameter points to an existing event
        try:
            number = int(parameters) - 1
            assert number >= 0
            event = events[event_name][number]
        except (ValueError, AssertionError, IndexError):
            self.msg("The event {} {} cannot be found in {}.".format(
                    event_name, parameters, obj))
            return

        # Accept the event
        if event["valid"]:
            self.msg("This event has already been accepted.")
        else:
            self.handler.accept_event(obj, event_name, number)
            self.msg("The event {} {} of {} has been accepted.".format(
                    event_name, parameters, obj))

    def list_tasks(self):
        """List the active tasks."""
        obj = self.obj
        event_name = self.event_name
        handler = self.handler
        tasks = [(k, v[0], v[1], v[2]) for k, v in handler.db.tasks.items()]
        if obj:
            tasks = [task for task in tasks if task[2] is obj]
        if event_name:
            tasks = [task for task in tasks if task[3] == event_name]

        tasks.sort()
        table = EvTable("ID", "Object", "Event", "In", width=78)
        table.reformat_column(0, align="r")
        now = datetime.now()
        for task_id, future, obj, event_name in tasks:
            key = obj.get_display_name(self.caller)
            delta = time_format((future - now).total_seconds(), 1)
            table.add_row(task_id, key, event_name, delta)

        self.msg(unicode(table))

# Private functions to handle editing
def _ev_load(caller):
    return caller.db._event and caller.db._event.get("code", "") or ""

def _ev_save(caller, buf):
    """Save and add the event."""
    lock = "perm({}) or perm(events_without_validation)".format(
            WITHOUT_VALIDATION)
    autovalid = caller.locks.check_lockstring(caller, lock)
    event = caller.db._event
    handler = get_event_handler()
    if not handler or not event or not all(key in event for key in \
            ("obj", "name", "number", "valid")):
        caller.msg("Couldn't save this event.")
        return False

    if (event["obj"], event["name"], event["number"]) in handler.db.locked:
        handler.db.locked.remove((event["obj"], event["name"],
                event["number"]))

    handler.edit_event(event["obj"], event["name"], event["number"], buf,
            caller, valid=autovalid)
    return True

def _ev_quit(caller):
    del caller.db._event
    caller.msg("Exited the code editor.")
