"""
Views for managing channels.

"""

from django.conf import settings
from django.db.models.functions import Lower
from django.http import HttpResponseBadRequest
from django.utils.text import slugify
from django.views.generic import ListView

from evennia.utils import class_from_module
from evennia.utils.logger import tail_log_file

from .mixins import TypeclassMixin
from .objects import ObjectDetailView


class ChannelMixin(TypeclassMixin):
    """
    This is a "mixin", a modifier of sorts.

    Any view class with this in its inheritance list will be modified to work
    with HelpEntry objects instead of generic Objects or otherwise.

    """

    # -- Django constructs --
    model = class_from_module(
        settings.BASE_CHANNEL_TYPECLASS, fallback=settings.FALLBACK_CHANNEL_TYPECLASS
    )

    # -- Evennia constructs --
    page_title = "Channels"

    # What lock type to check for the requesting user, authenticated or not.
    # https://github.com/evennia/evennia/wiki/Locks#valid-access_types
    access_type = "listen"

    def get_queryset(self):
        """
        Django hook; here we want to return a list of only those Channels
        and other documentation that the current user is allowed to see.

        Returns:
            queryset (QuerySet): List of Channels available to the user.

        """
        account = self.request.user

        # Get list of all Channels
        channels = self.typeclass.objects.all().iterator()

        # Now figure out which ones the current user is allowed to see
        bucket = [channel.id for channel in channels if channel.access(account, "listen")]

        # Re-query and set a sorted list
        filtered = self.typeclass.objects.filter(id__in=bucket).order_by(Lower("db_key"))

        return filtered


class ChannelListView(ChannelMixin, ListView):
    """
    Returns a list of channels that can be viewed by a user, authenticated
    or not.

    """

    # -- Django constructs --
    paginate_by = 100
    template_name = "website/channel_list.html"

    # -- Evennia constructs --
    page_title = "Channel Index"

    max_popular = 10

    def get_context_data(self, **kwargs):
        """
        Django hook; we override it to calculate the most popular channels.

        Returns:
            context (dict): Django context object

        """
        context = super().get_context_data(**kwargs)

        # Calculate which channels are most popular
        context["most_popular"] = sorted(
            list(self.get_queryset()),
            key=lambda channel: len(channel.subscriptions.all()),
            reverse=True,
        )[: self.max_popular]

        return context


class ChannelDetailView(ChannelMixin, ObjectDetailView):
    """
    Returns the log entries for a given channel.

    """

    # -- Django constructs --
    template_name = "website/channel_detail.html"

    # -- Evennia constructs --
    # What attributes of the object you wish to display on the page. Model-level
    # attributes will take precedence over identically-named db.attributes!
    # The order you specify here will be followed.
    attributes = ["name"]

    # How many log entries to read and display.
    max_num_lines = 10000

    def get_context_data(self, **kwargs):
        """
        Django hook; before we can display the channel logs, we need to recall
        the logfile and read its lines.

        Returns:
            context (dict): Django context object

        """
        # Get the parent context object, necessary first step
        context = super().get_context_data(**kwargs)
        channel = self.object

        # Get the filename this Channel is recording to
        filename = channel.get_log_filename()

        # Split log entries so we can filter by time
        bucket = []
        for log in (x.strip() for x in tail_log_file(filename, 0, self.max_num_lines)):
            if not log:
                continue
            try:
                time, msg = log.split(" [-] ")
                time_key = time.split(":")[0]
            except ValueError:
                # malformed log line. Skip.
                continue

            bucket.append({"key": time_key, "timestamp": time, "message": msg})

        # Add the processed entries to the context
        context["object_list"] = bucket

        # Get a list of unique timestamps by hour and sort them
        context["object_filters"] = sorted(set([x["key"] for x in bucket]))

        return context

    def get_object(self, queryset=None):
        """
        Override of Django hook that retrieves an object by slugified channel
        name.

        Returns:
            channel (Channel): Channel requested in the URL.

        """
        # Get the queryset for the help entries the user can access
        if not queryset:
            queryset = self.get_queryset()

        # Find the object in the queryset
        channel = slugify(self.kwargs.get("slug", ""))
        obj = next((x for x in queryset if slugify(x.db_key) == channel), None)

        # Check if this object was requested in a valid manner
        if not obj:
            raise HttpResponseBadRequest(
                "No %(verbose_name)s found matching the query"
                % {"verbose_name": queryset.model._meta.verbose_name}
            )

        return obj
