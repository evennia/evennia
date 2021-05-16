"""
Views to manipulate help entries.

"""

from django.utils.text import slugify
from django.views.generic import ListView
from django.http import HttpResponseBadRequest
from django.db.models.functions import Lower
from evennia.help.models import HelpEntry
from .mixins import TypeclassMixin, EvenniaDetailView


class HelpMixin(TypeclassMixin):
    """
    This is a "mixin", a modifier of sorts.

    Any view class with this in its inheritance list will be modified to work
    with HelpEntry objects instead of generic Objects or otherwise.

    """

    # -- Django constructs --
    model = HelpEntry

    # -- Evennia constructs --
    page_title = "Help"

    def get_queryset(self):
        """
        Django hook; here we want to return a list of only those HelpEntries
        and other documentation that the current user is allowed to see.

        Returns:
            queryset (QuerySet): List of Help entries available to the user.

        """
        account = self.request.user

        # Get list of all HelpEntries
        entries = self.typeclass.objects.all().iterator()

        # Now figure out which ones the current user is allowed to see
        bucket = [entry.id for entry in entries if entry.access(account, "view")]

        # Re-query and set a sorted list
        filtered = (
            self.typeclass.objects.filter(id__in=bucket)
            .order_by(Lower("db_key"))
            .order_by(Lower("db_help_category"))
        )

        return filtered


class HelpListView(HelpMixin, ListView):
    """
    Returns a list of help entries that can be viewed by a user, authenticated
    or not.

    """

    # -- Django constructs --
    paginate_by = 500
    template_name = "website/help_list.html"

    # -- Evennia constructs --
    page_title = "Help Index"


class HelpDetailView(HelpMixin, EvenniaDetailView):
    """
    Returns the detail page for a given help entry.

    """

    # -- Django constructs --
    template_name = "website/help_detail.html"

    def get_context_data(self, **kwargs):
        """
        Adds navigational data to the template to let browsers go to the next
        or previous entry in the help list.

        Returns:
            context (dict): Django context object

        """
        context = super().get_context_data(**kwargs)

        # Get the object in question
        obj = self.get_object()

        # Get queryset and filter out non-related categories
        queryset = (
            self.get_queryset()
            .filter(db_help_category=obj.db_help_category)
            .order_by(Lower("db_key"))
        )
        context["topic_list"] = queryset

        # Find the index position of the given obj in the queryset
        objs = list(queryset)
        for i, x in enumerate(objs):
            if obj is x:
                break

        # Find the previous and next topics, if either exist
        try:
            assert i + 1 <= len(objs) and objs[i + 1] is not obj
            context["topic_next"] = objs[i + 1]
        except:
            context["topic_next"] = None

        try:
            assert i - 1 >= 0 and objs[i - 1] is not obj
            context["topic_previous"] = objs[i - 1]
        except:
            context["topic_previous"] = None

        # Format the help entry using HTML instead of newlines
        text = obj.db_entrytext
        text = text.replace("\r\n\r\n", "\n\n")
        text = text.replace("\r\n", "\n")
        text = text.replace("\n", "<br />")
        context["entry_text"] = text

        return context

    def get_object(self, queryset=None):
        """
        Override of Django hook that retrieves an object by category and topic
        instead of pk and slug.

        Returns:
            entry (HelpEntry): HelpEntry requested in the URL.

        """
        # Get the queryset for the help entries the user can access
        if not queryset:
            queryset = self.get_queryset()

        # Find the object in the queryset
        category = slugify(self.kwargs.get("category", ""))
        topic = slugify(self.kwargs.get("topic", ""))
        obj = next(
            (
                x
                for x in queryset
                if slugify(x.db_help_category) == category and slugify(x.db_key) == topic
            ),
            None,
        )

        # Check if this object was requested in a valid manner
        if not obj:
            return HttpResponseBadRequest(
                "No %(verbose_name)s found matching the query"
                % {"verbose_name": queryset.model._meta.verbose_name}
            )

        return obj
