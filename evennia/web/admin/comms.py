"""
This defines how Comm models are displayed in the web admin interface.

"""

from django import forms
from django.conf import settings
from django.contrib import admin

from evennia.comms.models import ChannelDB, Msg

from .attributes import AttributeInline
from .tags import TagInline


class MsgTagInline(TagInline):
    """
    Inline display for Msg-tags.

    """

    model = Msg.db_tags.through
    related_field = "msg"


class MsgForm(forms.ModelForm):
    """
    Custom Msg form.

    """

    class Meta:
        models = Msg
        fields = "__all__"

    db_header = forms.CharField(
        label="Header",
        required=False,
        widget=forms.Textarea(attrs={"cols": "100", "rows": "2"}),
        help_text="Optional header for the message; it could be a title or "
        "metadata depending on msg-use.",
    )

    db_lock_storage = forms.CharField(
        label="Locks",
        required=False,
        widget=forms.Textarea(attrs={"cols": "100", "rows": "2"}),
        help_text="In-game lock definition string. If not given, defaults will be used. "
        "This string should be on the form "
        "<i>type:lockfunction(args);type2:lockfunction2(args);...",
    )


@admin.register(Msg)
class MsgAdmin(admin.ModelAdmin):
    """
    Defines display for Msg objects

    """

    inlines = [MsgTagInline]
    form = MsgForm
    list_display = (
        "id",
        "db_date_created",
        "sender",
        "receiver",
        "start_of_message",
    )
    list_display_links = ("id", "db_date_created", "start_of_message")
    ordering = ["-db_date_created", "-id"]
    search_fields = [
        "=id",
        "^db_date_created",
        "^db_message",
        "^db_sender_accounts__db_key",
        "^db_sender_objects__db_key",
        "^db_sender_scripts__db_key",
        "^db_sender_external",
        "^db_receivers_accounts__db_key",
        "^db_receivers_objects__db_key",
        "^db_receivers_scripts__db_key",
        "^db_receiver_external",
    ]
    readonly_fields = ["db_date_created", "serialized_string"]
    save_as = True
    save_on_top = True
    list_select_related = True
    view_on_site = False

    raw_id_fields = (
        "db_sender_accounts",
        "db_sender_objects",
        "db_sender_scripts",
        "db_receivers_accounts",
        "db_receivers_objects",
        "db_receivers_scripts",
        "db_hide_from_accounts",
        "db_hide_from_objects",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    (
                        "db_sender_accounts",
                        "db_sender_objects",
                        "db_sender_scripts",
                        "db_sender_external",
                    ),
                    (
                        "db_receivers_accounts",
                        "db_receivers_objects",
                        "db_receivers_scripts",
                        "db_receiver_external",
                    ),
                    ("db_hide_from_accounts", "db_hide_from_objects"),
                    "db_header",
                    "db_message",
                    "serialized_string",
                )
            },
        ),
    )

    def sender(self, obj):
        senders = [o for o in obj.senders if o]
        if senders:
            return senders[0]

    sender.help_text = "If multiple, only the first is shown."

    def receiver(self, obj):
        receivers = [o for o in obj.receivers if o]
        if receivers:
            return receivers[0]

    receiver.help_text = "If multiple, only the first is shown."

    def start_of_message(self, obj):
        crop_length = 50
        if obj.db_message:
            msg = obj.db_message
            if len(msg) > (crop_length - 5):
                msg = msg[:50] + "[...]"
            return msg

    def serialized_string(self, obj):
        """
        Get the serialized version of the object.

        """
        from evennia.utils import dbserialize

        return str(dbserialize.pack_dbobj(obj))

    serialized_string.help_text = (
        "Copy & paste this string into an Attribute's `value` field to store "
        "this message-object there."
    )

    def get_form(self, request, obj=None, **kwargs):
        """
        Overrides help texts.

        """
        help_texts = kwargs.get("help_texts", {})
        help_texts["serialized_string"] = self.serialized_string.help_text
        kwargs["help_texts"] = help_texts
        return super().get_form(request, obj, **kwargs)


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


class ChannelForm(forms.ModelForm):
    """
    Form for accessing channels.

    """

    class Meta:
        model = ChannelDB
        fields = "__all__"

    db_lock_storage = forms.CharField(
        label="Locks",
        required=False,
        widget=forms.Textarea(attrs={"cols": "100", "rows": "2"}),
        help_text="In-game lock definition string. If not given, defaults will be used. "
        "This string should be on the form "
        "<i>type:lockfunction(args);type2:lockfunction2(args);...",
    )


@admin.register(ChannelDB)
class ChannelAdmin(admin.ModelAdmin):
    """
    Defines display for Channel objects

    """

    inlines = [ChannelTagInline, ChannelAttributeInline]
    form = ChannelForm
    list_display = (
        "id",
        "db_key",
        "no_of_subscribers",
        "db_lock_storage",
        "db_typeclass_path",
        "db_date_created",
    )
    list_display_links = ("id", "db_key")
    ordering = ["-db_date_created", "-id", "-db_key"]
    search_fields = ["id", "db_key", "db_tags__db_key"]
    readonly_fields = ["serialized_string"]
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
                    "serialized_string",
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

    def no_of_subscribers(self, obj):
        """
        Get number of subs for a a channel .

        Args:
            obj (Channel): The channel to get subs from.

        """
        return sum(1 for sub in obj.subscriptions.all())

    def serialized_string(self, obj):
        """
        Get the serialized version of the object.

        """
        from evennia.utils import dbserialize

        return str(dbserialize.pack_dbobj(obj))

    serialized_string.help_text = (
        "Copy & paste this string into an Attribute's `value` field to store this channel there."
    )

    def get_form(self, request, obj=None, **kwargs):
        """
        Overrides help texts.

        """
        help_texts = kwargs.get("help_texts", {})
        help_texts["serialized_string"] = self.serialized_string.help_text
        kwargs["help_texts"] = help_texts
        return super().get_form(request, obj, **kwargs)

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
