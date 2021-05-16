"""
This defines how Comm models are displayed in the web admin interface.

"""

from django.contrib import admin
from evennia.comms.models import ChannelDB
from evennia.typeclasses.admin import AttributeInline, TagInline
from django.conf import settings


class ChannelAttributeInline(AttributeInline):
    """
    Inline display of Channel Attribute - experimental

    """

    model = ChannelDB.db_attributes.through
    related_field = "channeldb"


class ChannelTagInline(TagInline):
    """
    Inline display of Channel Tags - experimental

    """

    model = ChannelDB.db_tags.through
    related_field = "channeldb"


class MsgAdmin(admin.ModelAdmin):
    """
    Defines display for Msg objects

    """

    list_display = (
        "id",
        "db_date_created",
        "db_sender",
        "db_receivers",
        "db_channels",
        "db_message",
        "db_lock_storage",
    )
    list_display_links = ("id",)
    ordering = ["db_date_created", "db_sender", "db_receivers", "db_channels"]
    # readonly_fields = ['db_message', 'db_sender', 'db_receivers', 'db_channels']
    search_fields = ["id", "^db_date_created", "^db_message"]
    save_as = True
    save_on_top = True
    list_select_related = True


# admin.site.register(Msg, MsgAdmin)


class ChannelAdmin(admin.ModelAdmin):
    """
    Defines display for Channel objects

    """

    inlines = [ChannelTagInline, ChannelAttributeInline]
    list_display = ("id", "db_key", "db_lock_storage", "subscriptions")
    list_display_links = ("id", "db_key")
    ordering = ["db_key"]
    search_fields = ["id", "db_key", "db_tags__db_key"]
    save_as = True
    save_on_top = True
    list_select_related = True
    raw_id_fields = ("db_object_subscriptions", "db_account_subscriptions")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("db_key",),
                    "db_lock_storage",
                    "db_account_subscriptions",
                    "db_object_subscriptions",
                )
            },
        ),
    )

    def subscriptions(self, obj):
        """
        Helper method to get subs from a channel.

        Args:
            obj (Channel): The channel to get subs from.

        """
        return ", ".join([str(sub) for sub in obj.subscriptions.all()])

    def save_model(self, request, obj, form, change):
        """
        Model-save hook.

        Args:
            request (Request): Incoming request.
            obj (Object): Database object.
            form (Form): Form instance.
            change (bool): If this is a change or a new object.

        """
        obj.save()
        if not change:
            # adding a new object
            # have to call init with typeclass passed to it
            obj.set_class_from_typeclass(typeclass_path=settings.BASE_CHANNEL_TYPECLASS)
        obj.at_init()

    def response_add(self, request, obj, post_url_continue=None):
        from django.http import HttpResponseRedirect
        from django.urls import reverse

        return HttpResponseRedirect(reverse("admin:comms_channeldb_change", args=[obj.id]))


admin.site.register(ChannelDB, ChannelAdmin)
