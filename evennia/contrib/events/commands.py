"""
Module containing the commands of the event system.
"""

from django.conf import settings
from evennia import Command
from evennia.contrib.events.extend import get_event_handler
from evennia.utils.evtable import EvTable
from evennia.utils.utils import class_from_module

COMMAND_DEFAULT_CLASS = class_from_module(settings.COMMAND_DEFAULT_CLASS)

# Permissions
WITH_VALIDATION = getattr(settings, "EVENTS_WITH_VALIDATION", None)
WITHOUT_VALIDATION = getattr(settings, "EVENTS_WITHOUT_VALIDATION",
        "immortals")
VALIDATING = getattr(settings, "EVENTS_VALIDATING", "immortals")

# Split help file
BASIC_HELP = "Add, edit or delete events."

BASIC_USAGES = [
        "@event object name [= event name]",
        "@event/add object name = event name [parameters]",
        "@event/edit object name = event name [event number]",
        "@event/del object name = event name [event number]",
]

BASIC_SWITCHES = [
    "add - add and edit a new event",
    "edit - edit an existing event",
    "del - delete an existing event",
]

VALIDATOR_USAGES = [
        "@event/accept [object name = event name [event number]]",
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
You can also add, edit or remove events using the add, edit or del switches.
"""

VALIDATOR_TEXT = """
You can also use this command to validate events.  Depending on your game
setting, some users might be allowed to add new events, but these events
will not be fired until you accept them.  To see the events needing
validation, enter the /accept switch without argument:
    @event/accept
A table will show you the events that are not validated yet, who created
it and when.  You can then accept a specific event:
    @event here = enter
Or, if more than one events are connected here, specify the number:
    @event here = enter 3
Use the /del switch to remove events that should not be connected.
"""

class CmdEvent(COMMAND_DEFAULT_CLASS):

    """Command to edit events."""

    key = "@event"
    locks = "cmd:perm({})".format(VALIDATING)
    aliases = ["@events", "@ev"]
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
        text = "\n" + BASIC_HELP + "\n\nUsages:\n    "

        # Usages
        text += "\n    ".join(BASIC_USAGES)
        if validator:
            text += "\n    " + "\n    ".join(VALIDATOR_USAGES)

        # Switches
        text += "\n\nSwitches:\n    "
        text += "\n    ".join(BASIC_SWITCHES)
        if validator:
            text += "\n    " + "\n".join(VALIDATOR_SWITCHES)

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

        # First and foremost, get the event handler
        self.handler = get_event_handler()
        if self.handler is None:
            caller.msg("The event handler is not running, can't " \
                    "access the event system.")
            return

        # Before the equal sign is always an object name
        obj = None
        if self.args.strip():
            obj = caller.search(self.lhs)
            if not obj:
                return

        # Switches are mutually exclusive
        switch = self.switches and self.switches[0] or ""
        if switch == "":
            if not obj:
                caller.msg("Specify an object's name or #ID.")
                return

            self.list_events(obj)
        elif switch == "add":
            if not obj:
                caller.msg("Specify an object's name or #ID.")
                return

            self.add_event(obj)
        elif switch == "edit":
            if not obj:
                caller.msg("Specify an object's name or #ID.")
                return

            self.edit_event(obj)
        elif switch == "del":
            if not obj:
                caller.msg("Specify an object's name or #ID.")
                return

            self.del_event(obj)
        elif switch == "accept" and validator:
            self.accept_event(obj)
        else:
            caller.msg("Mutually exclusive or invalid switches were " \
                    "used, cannot proceed.")

    def list_events(self, obj):
        """Display the list of events connected to the object."""
        events = self.handler.get_events(obj)
        types = self.handler.get_event_types(obj)
        table = EvTable("Event name", "Number", "Lines", "Description",
                width=78)
        for name, infos in sorted(types.items()):
            number = len(events.get(name, []))
            lines = sum(len(e["code"].splitlines()) for e in \
                    events.get(name, []))
            description = infos[1].splitlines()[0]
            table.add_row(name, number, lines, description)

        table.reformat_column(1, align="r")
        table.reformat_column(2, align="r")
        self.msg(table)

    def add_event(self, obj):
        """Add an event."""
        self.msg("Calling add.")

    def edit_event(self, obj):
        """Add an event."""
        self.msg("Calling edit.")

    def del_event(self, obj):
        """Add an event."""
        self.msg("Calling del.")

    def accept_event(self, obj):
        """Add an event."""
        self.msg("Calling accept.")
