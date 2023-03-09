# Events Calendar
*Contribution by InspectorCaracal (2023)*

A system for viewing and managing community events for your game.

## Installation

> This contrib requires extra dependencies. Install with `pip install evennia[extra]` or `pip install python-dateutil`

The main components of the events system are the `Event` class and the `EventCalendar` global script. You'll need to create the `EventCalendar` global script for any of the provided commands to work.

The recommended method is to add it to the `GLOBAL_SCRIPTS` setting in `server/conf/settings.py`

```python
GLOBAL_SCRIPTS = {
    "event_calendar_script": {
        "typeclass": "base_systems.events_calendar.events.EventCalendar",
        "desc": "Track and manage community events.",
				# The interval is optional and defines how often old events will be cleaned up.
				"interval": 36000
    }
}
````

The event calendar comes with an optional clean-up mechanism. If you set a repeating interval on the calendar global script, it will regularly delete any events that have already ended. If you would rather keep old events or remove them manually, leave the interval setting out.

You will also need to add the events cmdset to your game. It can be added to `CharacterCmdSet`, `AccountCmdSet`, or both.

Example:
```python
    # add this import line
    from evennia.contrib.base_systems.events_calendar.commands import EventsCmdSet
    
    class AccountCmdSet(default_cmds.AccountCmdSet):
    
        def at_cmdset_creation(self):
            super().at_cmdset_creation()
            # ...
            # add this line to include the cmdset
            self.add(EventsCmdSet)
```

## Website Installation

To add an events listing page to your game's website, you will first need to copy the template file `events_template.html` (e.g. from [github](https://github.com/evennia/evennia/blob/main/evennia/contrib/base_systems/events_calendar/events_template.html) ) from the contrib to your website templates folder: `mygame/web/templates/website/`.

Then, import and add the events view to `mygame/web/website/urls.py` - it should look something like this:

```python
from django.urls import path

from evennia.web.website.urls import urlpatterns as evennia_website_urlpatterns
from evennia.contrib.base_systems.events_calendar.events_view import EventListView

# add patterns here
urlpatterns = [
    # this is the new path for the events page
    path("events/", EventListView.as_view(), name="events")
]

# read by Django
urlpatterns = urlpatterns + evennia_website_urlpatterns
```

That will make a list of your scheduled events available at e.g. `localhost:4001/events`

In order to make the new Events page available from the menu bar, you also need to copy `_menu.html` (e.g. from [github](https://github.com/evennia/evennia/blob/main/evennia/web/templates/website/_menu.html) to your `web/templates/website/` folder, then add a new menu item.

Example:
```html
            <!-- game views -->
            <li><a class="nav-link" href="{% url 'characters' %}">Characters</a></li>
            <li><a class="nav-link" href="{% url 'channels' %}">Channels</a></li>
            <li><a class="nav-link" href="{% url 'help' %}">Help</a></li>
            <!-- the new Events link -->
            <li><a class="nav-link" href="{% url 'events' %}">Events</a></li>
            <!-- end game views -->
```

**This contrib does not provide the ability to add, modify, or delete events from the website.**

## Usage

The primary method for adding, creating and viewing events is the `events` command in-game, but the contrib also has several optional settings to customize its behavior.

### Creating new events.

New events are created through the `events/new` command, which will begin an EvMenu that allows you to define the information for your event.

If you enter the command with arguments, e.g. `events/new My Event`, it will set that as the name of your event. If not, it will prompt you for an event name before continuing with the menu.

The contrib supports setting the name, description, start time, end time, and view permissions of events with the menu, along with anonymous mode and auto-announce for staff. View permissions can only be limited to your own permission level and lower.

### Viewing events

The main way to view events is with the `events` command.

Entering `events` on its own will show a list of all current and upcoming commands. `events/current` will show only currently active events, while `events/future` will show only upcoming events. `events/mine` will show a similar list, but only events that you are set as the creator for.

You can also use the `view` switch to see more detail of an event. `events/view my event` will show the detail view of all events matching that name. `view` can be combined with any of the list switches to show the full detail view instead of the list view. e.g. `events/view/current` or `events/view/mine`.

Additionally, if you have the website view installed, you can view a list of current and upcoming lists at `yourgame.com/events`. This list can't be filtered further, but it does respect view permissions.

### Deleting events

Existing events can be deleted with the `events/delete` command.

Entering the command with arguments, e.g. `events/delete my event`, the events calendar will filter to matching events that you're allowed to delete. Otherwise, it will show a complete list of all events that you can delete.

### Settings

By default, only players with `Admin` permission or above can create or delete any events. You can modify that with the following settings:

```python
# Set the permission required to create new events
EVENTS_PERMS_ADD = "Admin"
# Set the permission required to delete events created by *anyone*
EVENTS_PERMS_DELETE_ANY = "Admin"
# What permission is required to create "staff" events - anonymous events that 
# can be automatically announced to all players when they begin.
EVENTS_PERMS_STAFF = "Admin"
```

> Anyone can always view and delete their own events.

Creating and deleting new events are managed with a custom `EvMenu` - `menus.py` in the contrib. You can replace these menus with your own, allowing you to add, remove, or otherwise modify any of the information that can be added to a single Event.

> When using your own menus, the event creation menu MUST have "menunode_begin_add_menu" and "menunode_add_info" defined, and event deletion menu MUST have "menunode_begin_delete_menu" defined.

```python
# The menu module used when creating a new event
EVENTS_CREATE_MENU = "mygame.world.event_create_menu"
# The menu module used for deleting an event
EVENTS_DELETE_MENU = "mygame.world.event_delete_menu"
```

The `Event` class and `EventCalendar` global script are designed to be flexible and support any extra metadata you might want to add to your events - for example, Category, or Location - without changing their code, so you can pass any additional keyword arguments when creating an Event in your custom menus.
