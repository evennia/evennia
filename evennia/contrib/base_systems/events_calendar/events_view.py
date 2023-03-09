"""
The main index page, including the game stats

"""

from django.views.generic import ListView

from evennia import GLOBAL_SCRIPTS


class EventListView(ListView):
    # Tell the view what HTML template to use for the page
    template_name = "website/events_template.html"

    paginate_by = 10

    # -- Evennia constructs --
    page_title = "Events List"

    def get_queryset(self):
        if not (calendar := GLOBAL_SCRIPTS.get("event_calendar_script")):
            return []

        viewer = self.request.user
        if not str(viewer) == "AnonymousUser":
            viewer = viewer.db._playable_characters + [viewer]
        return calendar.list_events(as_data=True, viewer=viewer, include_expired=False)
