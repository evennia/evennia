"""
Events Calendar

Contribution by InspectorCaracal (2023)

A system for viewing and managing community events for your game.

## Installation

The main components of the events system are the `Event` class and the `EventCalendar`
global script. You'll need to create the `EventCalendar` global script for any of the
provided commands to work.

The recommended method is to add it to the `GLOBAL_SCRIPTS` setting in `server/conf/settings.py`

    GLOBAL_SCRIPTS = {
        "event_calendar_script": {
            "typeclass": "base_systems.events_calendar.events.EventCalendar",
            "desc": "Track and manage community events."
        }
    }

The event calendar comes with an optional clean-up mechanism. If you set a repeating interval
on the calendar global script, it will regularly delete any events that have already ended.

You will also need to add the cmdset to your game. It can be added to `CharacterCmdSet`,
`AccountCmdSet`, or both.

Example:

    # ...
    from evennia.contrib.base_systems.events_calendar.commands import EventCmdSet
    
    class AccountCmdSet(default_cmds.AccountCmdSet):
    
        def at_cmdset_creation(self):
            super().at_cmdset_creation()
            # ...
            self.add(EventCmdSet)

"""
from zoneinfo import ZoneInfo
from datetime import datetime
from django.conf import settings
from evennia import DefaultScript, create_script
from evennia.utils import dbserialize, class_from_module, inherits_from, is_iter, make_iter
from evennia.server.sessionhandler import SESSIONS

_BASE_SCRIPT_TYPECLASS = class_from_module(settings.BASE_SCRIPT_TYPECLASS, DefaultScript)

_TIME_ZONE = ZoneInfo(settings.TIME_ZONE) if settings.USE_TZ else None

_DEFAULT_VIEW_TEMPLATE = """\
|c{name}|n{creator}
Starts: {start}|g{active}|n
Ends:   {end}
{desc}
"""
_SHORT_VIEW_TEMPLATE = "|w{name}|n{creator}, starts {start}|g{active}|n"
_DEFAULT_TIME_FORMAT = "%d %b %Y, %H:%M %Z"


class AnnounceEvent(DefaultScript):
    def at_repeat(self):
        if not (event := self.db.event):
            return

        # announce to all if applicable
        if event.announce:
            message = f"|w{event.name}|n has begun!"
            SESSIONS.announce_all(message)

        # notify all RSVP'd
        elif notify_list := event.notify:
            message = f"Your RSVP'd event |w{event.name}|n has started."
            for rsvp in notify_list:
                rsvp.msg(message)

    def at_stop(self):
        self.delete()


class EventError(Exception):
    """
    Error from an Event
    """


class Event:
    """
    A class containing information about a single Event.
    """

    view_perm = None
    script = None
    announce = False

    def __init__(self, name, desc, start_time, end_time, creator=None, **kwargs):
        """
        Initialize the event class.

        Args:
            name (str):  The name of the event.
            desc (str):  The description for the event.
            start_time (datetime):  What time the event will begin.
            end_time (datetime):  What time the event will end.

        Keyword args:
            creator (Object or Account):  An optional event-creator to attach to the event.
        """
        if start_time > end_time:
            # an event can't go backwards in time!
            raise EventError("Start time cannot be later than the end time.")
        self.name = name
        self.desc = desc
        self.start_time = start_time
        self.end_time = end_time
        self.creator = creator
        self.notify = []
        # add optional arbitrary data
        for key, val in kwargs.items():
            # don't override methods
            if not (attr := hasattr(self, key)) or not callable(attr):
                setattr(self, key, val)

    def __str__(self):
        return "{name}{creator} {start}-{end}".format(
            name=self.name,
            creator=f" (by {self.creator})" if self.creator else "",
            start=self.start_time.strftime("%d %b"),
            end=self.end_time.strftime("%d %b"),
        )

    def __lt__(self, other):
        return self.start_time < other.start_time

    def __serialize_dbobjs__(self):
        # serialize all attributes in case there are custom ones with db objects
        for attr, val in vars(self).items():
            if inherits_from(val, "evennia.typeclasses.models.TypedObject"):
                setattr(self, attr, dbserialize.dbserialize(val))

    def __deserialize_dbobjs__(self):
        # deserialize all attributes in case there are custom ones with db objects
        for attr, val in vars(self).items():
            if type(val) is bytes:
                setattr(self, attr, dbserialize.dbunserialize(val))

    @property
    def status(self):
        """
        Returns a string representing the chronological status of the event.
        """
        now = datetime.now(tz=_TIME_ZONE)
        if self.start_time > now:
            return "scheduled"
        elif self.start_time < now < self.end_time:
            return "active"
        else:
            return "completed"

    def can_view(self, viewer):
        # for situations like the website, which checks all your character perms
        if is_iter(viewer):
            return any(self.can_view(v) for v in viewer)

        if not viewer:
            # "no viewer" means get a full list
            return True

        if viewer == self.creator:
            # you can always view your own events
            return True

        if not self.view_perm:
            # if no perm is specified, assume no restrictions
            return True

        if not hasattr(viewer, "check_permstring"):
            # this viewer has no permissions but permissions are required
            return False

        return viewer.check_permstring(self.view_perm)

    def view(self, **kwargs):
        """
        Formats the data for view.
        """
        if not (template_str := kwargs.get("template")):
            template_str = _DEFAULT_VIEW_TEMPLATE
        if not (time_format := kwargs.get("ftime")):
            time_format = _DEFAULT_TIME_FORMAT

        view_str = template_str.format(
            name=self.name,
            desc=self.desc,
            creator=f" (by {self.creator.name})" if self.creator else "",
            start=self.start_time.strftime(time_format).strip(),
            end=self.end_time.strftime(time_format).strip(),
            active=" (happening now!)" if self.status == "active" else "",
        )
        return view_str


class EventCalendar(_BASE_SCRIPT_TYPECLASS):
    """
    A script typeclass intended to be used as a global script, for tracking current and upcoming events.
    """

    key = "event_calendar_script"

    def at_repeat(self):
        # clear out events that have already completed
        self.clean_up()

    def _sort_events(self):
        if not (all_events := self.db.all_events):
            return
        all_events = all_events.deserialize()
        all_events.sort()
        self.db.all_events = all_events

    def current_events(self, as_data=False, **kwargs):
        """
        Returns a list of all currently active events
        """
        return self.list_events(as_data=as_data, status="active", **kwargs)

    def future_events(self, as_data=False, **kwargs):
        """
        Returns a list of all future events
        """
        return self.list_events(as_data=as_data, status="scheduled", **kwargs)

    def list_events(
        self, viewer=None, as_data=False, status=None, include_expired=True, short=False, **kwargs
    ):
        """
        Returns an optionally-filtered list of events
        """
        if not (all_events := self.db.all_events):
            return []
        # optional custom view template
        if short:
            view_template = str(self.db.short_view or _SHORT_VIEW_TEMPLATE)
        else:
            view_template = str(self.db.view_template or _DEFAULT_VIEW_TEMPLATE)
        # optional custom time format
        ftime = str(self.db.ftime or "")
        event_list = []
        for event in all_events:
            if not event:
                continue

            # check optional filters
            if not event.can_view(viewer):
                continue
            if status and event.status != status:
                continue
            if not include_expired and event.status == "completed":
                continue

            # append the right form of the event
            if as_data:
                event_list.append(event)
            else:
                event_list.append(event.view(template=view_template, ftime=ftime, **kwargs))

        if as_data:
            return event_list
        else:
            return "\n".join(event_list) or ""

    def format_events(self, events, short=False, **kwargs):
        """
        Format a list of Event objects using the scripts formatting templates.
        """
        events = make_iter(events)
        # optional custom view template
        if short:
            view_template = str(self.db.short_view or _SHORT_VIEW_TEMPLATE)
        else:
            view_template = str(self.db.view_template or _DEFAULT_VIEW_TEMPLATE)
        # optional custom time format
        ftime = str(self.db.ftime or "")
        event_list = [event.view(template=view_template, ftime=ftime, **kwargs) for event in events]
        return "\n".join(event_list) or ""

    def clean_up(self):
        """
        Remove all past events
        """
        if not (all_events := self.db.all_events):
            return
        all_events = all_events.deserialize()
        to_remove = []
        for event in all_events:
            if event.status == "completed":
                to_remove.append(event)
        for event in to_remove:
            all_events.remove(event)
        self.db.all_events = all_events

    def add_event(self, event):
        """
        Add a new event to the calendar
        """
        if not event.script:
            from evennia.utils import logger

            logger.log_msg(event.start_time.tzinfo)
            tdelta = event.start_time - datetime.now(tz=_TIME_ZONE)
            seconds_until = int(tdelta.total_seconds())
            if seconds_until > 0:
                # only create an announcement script if the event will start in the future
                new_script = create_script(
                    typeclass="evennia.contrib.base_systems.events_calendar.events_calendar.AnnounceEvent",
                    start_delay=True,
                    interval=seconds_until,
                    repeats=1,
                    persistent=True,
                    desc=f"announce start of {event}",
                )
                new_script.db.event = event
                event.script = new_script.key
        if not (events_list := self.db.all_events):
            self.db.all_events = [event]
            return True
        elif event not in events_list:
            events_list.append(event)
            self._sort_events()
            return True

    def delete_event(self, event):
        """
        Delete an existing event from the calendar.
        """
        if event in self.db.all_events:
            if scheduled := getattr(event, "script"):
                if script := DefaultScript.objects.search_script(scheduled):
                    script.delete()
            self.db.all_events.remove(event)
            return True

    def search_event(self, search_data="", viewer=None, creator=None, **kwargs):
        """
        Find matching events.
        """
        search_data = search_data.lower().strip()

        def _check_creator(ecreator):
            # make sure that both account and character creators are identified
            if not creator:
                return True
            if creator == ecreator:
                return True
            elif account := getattr(creator, "account", None):
                return account == ecreator

        return [
            event
            for event in self.attributes.get("all_events", [])
            if search_data in str(event).lower()
            and event.can_view(viewer)
            and _check_creator(event.creator)
            and all(val == getattr(event, key, None) for key, val in kwargs.items())
        ]
