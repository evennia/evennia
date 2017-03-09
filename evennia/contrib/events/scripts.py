"""
Scripts for the event system.
"""

from evennia import DefaultScript

class EventHandler(DefaultScript):

    """Event handler that contains all events in a global script."""

    def at_script_creation(self):
        self.key = "event_handler"
        self.desc = "Global event handler"
        self.persistent = True

        # Permanent data to be stored
        self.db.event_types = {}
        self.db.events = {}
