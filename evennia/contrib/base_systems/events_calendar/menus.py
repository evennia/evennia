from zoneinfo import ZoneInfo
from datetime import datetime
from django.conf import settings
import dateutil.parser as dateparser
from evennia import GLOBAL_SCRIPTS
from evennia.utils import dedent, evmenu

from .events_calendar import Event

_EVENTS_ADMIN_PERM = getattr(settings, "EVENTS_PERMS_STAFF", "Admin")

_TIME_ZONE = ZoneInfo(settings.TIME_ZONE) if settings.USE_TZ else None

_DEFAULT_TIME_FORMAT = "%d %b %Y, %H:%M %Z"
# Add Event menu

_PERM_LIST = settings.PERMISSION_HIERARCHY


def menunode_begin_add_menu(caller):
    caller.ndb._event_info = {}
    text = "What would you like to call this event?"
    options = {"key": "_default", "goto": (_set_event_info, {"to_set": "name"})}

    return text, options


def menunode_add_info(caller, raw_string, **kwargs):
    if not (time_format := GLOBAL_SCRIPTS.event_calendar_script.db.ftime):
        time_format = _DEFAULT_TIME_FORMAT
    event_info = caller.ndb._event_info
    err = ""
    start_time = event_info.get("start_time")
    end_time = event_info.get("end_time")
    if start_time and end_time and start_time > end_time:
        err = "|rYour event cannot end before it starts!|n\n\n"
    text = dedent(
        """\
        You are adding a new event: |w{name}|n
        Start time: {start}
        End time:   {end}
        {desc}
  
        {err}Choose an option to set (or |wq|n to cancel):
    """
    ).format(
        name=caller.ndb._event_info["name"],
        start=start_time.strftime(time_format) if start_time else "N/A",
        end=end_time.strftime(time_format) if end_time else "N/A",
        desc=event_info.get("desc", "(no description)"),
        err=err,
    )

    options = [
        {"desc": "Name", "goto": ("menunode_enter_info", {"to_set": "name"})},
        {"desc": "Description", "goto": ("menunode_enter_info", {"to_set": "desc"})},
        {"desc": "Starting time", "goto": ("menunode_pick_date", {"to_set": "start"})},
        {"desc": "Ending time", "goto": ("menunode_pick_date", {"to_set": "end"})},
    ]
    if caller.check_permstring(_EVENTS_ADMIN_PERM):
        if event_info.get("anonymous"):
            options.append({"desc": "Set to player event", "goto": _toggle_anonymous})
            if event_info.get("announce"):
                options.append({"desc": "Turn off auto-announcement", "goto": _toggle_announce})
            else:
                options.append({"desc": "Auto-announce event starting", "goto": _toggle_announce})
        else:
            options.append({"desc": "Set to anonymous/staff event", "goto": _toggle_anonymous})
    options.append({"desc": "Set view permission", "goto": "menunode_set_permission"})

    if start_time and end_time and not err:
        options.append({"desc": "Confirm and create", "goto": "menunode_confirm_add"})
    return text, options


def menunode_enter_info(caller, raw_string, to_set, **kwargs):
    if to_set == "name":
        word = "name"
    elif to_set == "desc":
        word = "description"

    text = f"Enter your event's {word}:"

    option = {"key": "_default", "goto": (_set_event_info, {"to_set": to_set})}

    return text, option


def menunode_pick_date(caller, raw_string, to_set, **kwargs):
    if not (time_format := GLOBAL_SCRIPTS.event_calendar_script.db.ftime):
        time_format = _DEFAULT_TIME_FORMAT
    event_info = caller.ndb._event_info
    if scheduled := event_info.get(f"{to_set}_time"):
        schedule_str = scheduled.strftime(time_format)
    else:
        schedule_str = "N/A"

    text = dedent(
        f"""
  Your event |w{event_info['name']}|n is scheduled to {to_set} at:
  
  {schedule_str}
  
  Enter a new date, or leave blank to keep this time:
  """
    )
    if err := kwargs.get("error"):
        text = err + "\n\n" + text

    option = {"key": "_default", "goto": (_set_event_date, {"to_set": to_set})}

    return text, option


def menunode_set_permission(caller, raw_string, **kwargs):
    current = caller.ndb._event_info.get("view_perm") or "anyone"

    text = f"Your event is currently restricted to: {current}.\n\nChoose a permission level below to restrict the event to players of that level or higher:"
    options = []

    for perm in _PERM_LIST:
        if caller.permissions.check(perm):
            options.append({"desc": perm, "goto": (_set_permission, {"perm": perm})})

    return text, options


def _set_event_info(caller, raw_string, to_set, **kwargs):
    info = raw_string.strip()
    caller.ndb._event_info[to_set] = info
    return "menunode_add_info"


def _set_event_date(caller, raw_string, to_set, **kwargs):
    try:
        date_obj = dateparser.parse(
            raw_string.strip(),
            default=datetime.now(tz=_TIME_ZONE),
            fuzzy=True,
            ignoretz=not _TIME_ZONE,
        )
    except ValueError:
        return ("menunode_pick_date", {"to_set": to_set, "error": "Invalid date."})

    caller.ndb._event_info[f"{to_set}_time"] = date_obj
    return "menunode_add_info"


def _set_permission(caller, raw_string, perm, **kwargs):
    caller.ndb._event_info["view_perm"] = perm
    return "menunode_add_info"


def _toggle_anonymous(caller, raw_string, **kwargs):
    anon = caller.ndb._event_info.get("anonymous")
    caller.ndb._event_info["anonymous"] = not anon
    if anon:
        # it was anonymous and no longer is; non-anon events can't be announced
        caller.ndb._event_info["announce"] = False

    return "menunode_add_info"


def _toggle_announce(caller, raw_string, **kwargs):
    caller.ndb._event_info["announce"] = not caller.ndb._event_info.get("announce")
    return "menunode_add_info"


def menunode_confirm_add(caller, raw_string, **kwargs):
    event_info = dict(caller.ndb._event_info)
    event_info["desc"] = event_info.get("desc", "(no description)")
    if not event_info.pop("anonymous", None):
        event_info["creator"] = caller
    event = Event(**event_info)

    text = dedent(
        """
  Your event:
  
  {event}{announce}
  """
    ).format(
        event=event.view(),
        announce="\n(Event will be auto-announced when it starts.)" if event.announce else "",
    )

    options = (
        {"key": "Create", "goto": ("menunode_add_end", {"event": event})},
        {"key": ("Back", "b"), "goto": "menunode_add_info"},
    )

    return text, options


def menunode_add_end(caller, raw_string, event, **kwargs):
    GLOBAL_SCRIPTS.event_calendar_script.add_event(event)
    text = "Your event has been added!"
    return text


# Delete Event menu


def _list_events(caller):
    events = caller.ndb._event_info or {}
    if not (options := events.get("opts")):
        options = GLOBAL_SCRIPTS.event_calendar_script.list_events(as_data=True)
    return options


@evmenu.list_node(_list_events, select="menunode_confirm_delete", pagesize=10)
def menunode_begin_delete_menu(caller, raw_string, **kwargs):
    text = "Which event do you want to delete?\n\n(press |wq|n to cancel)"
    return text, []


def menunode_confirm_delete(caller, raw_string, selection, **kwargs):
    text = dedent(
        """
    {event}
    
    Delete this event?
  """
    ).format(event=selection.view())

    options = (
        {"key": "Delete", "goto": ("menunode_delete_event", {"event": selection})},
        {"key": ("Back", "b"), "goto": "menunode_begin_delete_menu"},
    )

    return text, options


def menunode_delete_event(caller, raw_string, event, **kwargs):
    text = f"Event {event} has been deleted."
    GLOBAL_SCRIPTS.event_calendar_script.delete_event(event)
    return text
