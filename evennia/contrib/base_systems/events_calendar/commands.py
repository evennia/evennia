"""
Events Command

Adds a command for managing events through the EventCalendar script.
"""

from django.conf import settings
from evennia import CmdSet, GLOBAL_SCRIPTS, utils
from evennia.utils import evmenu, iter_to_str
from evennia.commands.default.muxcommand import MuxCommand

_ADD_EVENT_PERMS = getattr(settings, "EVENTS_PERMS_ADD", "Admin")
_DELETE_EVENT_PERMS = getattr(settings, "EVENTS_PERMS_DELETE_ANY", "Admin")


_CREATE_MENU = getattr(
    settings, "EVENTS_CREATE_MENU", "evennia.contrib.base_systems.events_calendar.menus"
)
_DELETE_MENU = getattr(
    settings, "EVENTS_DELETE_MENU", "evennia.contrib.base_systems.events_calendar.menus"
)


class CmdEvents(MuxCommand):
    """
    view and manage community events

    Usage:
        events
        events/[current/future/mine]
        events/[new/delete] [event name]
        events/rsvp event name

    Examples:
        events
        events/mine
        events/new My First Event
        events/view Another Event

    Switches:
        current - List any events currently active
        future  - List upcoming events
        mine    - List all events you've created
        view    - View full details for an event. Can be combined with list switches or
                  used with an event name.
        rsvp    - Sign up to be alerted when the event begins, or again to remove yourself.
        new     - Open the new event menu, optionally providing a name.
        delete  - Open the event deletion menu, optionally providing a name.
    """

    key = "events"
    aliases = ("event",)

    switch_options = (
        "current",
        "future",
        "mine",
        "new",
        "add",
        "create",
        "remove",
        "delete",
        "view",
        "rsvp",
        "del",
    )

    def func(self):
        if not (calendar := GLOBAL_SCRIPTS.get("event_calendar_script")):
            self.msg("No event calendar was found.")
            return

        def _cleanup_info(caller, evmenu):
            del caller.ndb._event_info

        if any(w in self.switches for w in ("new", "create", "add")):
            if not self.caller.check_permstring(_ADD_EVENT_PERMS):
                self.msg("You do not have permission to add new events.")
                return
            if self.args:
                name = self.args.strip()
                self.caller.ndb._event_info = {"name": name}
                startnode = "menunode_add_info"
            else:
                startnode = "menunode_begin_add_menu"
            evmenu.EvMenu(
                self.caller,
                _CREATE_MENU,
                startnode=startnode,
                cmd_on_exit=_cleanup_info,
            )
            return

        if any(w in self.switches for w in ("remove", "delete", "del")):
            search_term = self.args.strip()
            if not self.caller.check_permstring(_DELETE_EVENT_PERMS):
                # can only delete your own events
                if search_results := calendar.search_event(
                    search_term, viewer=self.caller, creator=self.caller
                ):
                    self.caller.ndb._event_info = {"opts": search_results}
                else:
                    self.msg("You have no events to delete.")
                    return
            elif search_term:
                # filter list by search term
                if search_results := calendar.search_event(search_term, viewer=self.caller):
                    self.caller.ndb._event_info = {"opts": search_results}
                else:
                    self.msg(f"No matching events for {search_term} were found.")
                    return
            self.msg(self.caller.ndb._event_info)
            evmenu.EvMenu(
                self.caller,
                _DELETE_MENU,
                startnode="menunode_begin_delete_menu",
                cmd_on_exit=_cleanup_info,
            )
            return

        if not (switches := self.switches):
            switches = ("current", "future")

        if "rsvp" in switches:
            if not self.args:
                self.msg("You must specify which event you want to RSVP")
                return
            search_term = self.args.strip()
            if search_results := calendar.search_event(
                search_term, viewer=self.caller, status="scheduled"
            ):
                if len(search_results) > 1:
                    # do proper multimatch here
                    self.msg("More than one match.")
                    return
                event = search_results[0]
                if self.caller in event.notify:
                    event.notify.remove(self.caller)
                    self.msg(f"You will no longer be notified when |w{event}|n begins.")
                else:
                    event.notify.append(self.caller)
                    self.msg(
                        f"You have RSVPed for |w{event}|n and will be notified when it begins."
                    )
            else:
                self.msg(f"No matching events for {search_term} were found.")
            return

        short_view = "view" not in switches
        if len(switches) == 1:
            if "view" in switches:
                if not self.args:
                    self.msg("View which event?")
                    return
                search_term = self.args.strip()
                if not (search_results := calendar.search_event(search_term, viewer=self.caller)):
                    self.msg("No matching events were found.")
                    return
                self.msg(calendar.format_events(search_results))
                return
            if "mine" in switches:
                if events := calendar.search_event(creator=self.caller):
                    self.msg("|wMy Events|n")
                    self.msg(calendar.format_events(events, short=short_view))
                else:
                    self.msg("You have no events.")
                return

        results = []

        if "current" in switches:
            if events := calendar.current_events(
                viewer=self.caller,
                creator=self.caller if "mine" in switches else None,
                short=short_view,
            ):
                results.append(events)

        if "future" in switches:
            if events := calendar.future_events(
                viewer=self.caller,
                creator=self.caller if "mine" in switches else None,
                short=short_view,
            ):
                results.append(events)

        if not results:
            self.msg(f"There are no matching events.")

        else:
            self.msg("|wEvents|n")
            self.msg("\n".join(results).strip())


class EventsCmdSet(CmdSet):
    key = "Events CmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()

        self.add(CmdEvents)
