#
# This sets up how models are displayed
# in the web admin interface.
#
from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin.utils import flatten_fieldsets
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext as _

from evennia.accounts.models import AccountDB
from evennia.objects.models import ObjectDB

from . import utils as adminutils
from .attributes import AttributeInline
from .tags import TagInline


class ObjectAttributeInline(AttributeInline):
    """
    Defines inline descriptions of Attributes (experimental)

    """

    model = ObjectDB.db_attributes.through
    related_field = "objectdb"


class ObjectTagInline(TagInline):
    """
    Defines inline descriptions of Tags (experimental)

    """

    model = ObjectDB.db_tags.through
    related_field = "objectdb"


class ObjectCreateForm(forms.ModelForm):
    """
    This form details the look of the fields.

    """

    class Meta(object):
        model = ObjectDB
        fields = "__all__"

    db_key = forms.CharField(
        label="Name/Key",
        widget=forms.TextInput(attrs={"size": "78"}),
        help_text="Main identifier, like 'apple', 'strong guy', 'Elizabeth' etc. "
        "If creating a Character, check so the name is unique among characters!",
    )
    db_typeclass_path = forms.ChoiceField(
        label="Typeclass",
        initial={settings.BASE_OBJECT_TYPECLASS: settings.BASE_OBJECT_TYPECLASS},
        help_text="This is the Python-path to the class implementing the actual functionality. "
        f"<BR>If you are creating a Character you usually need <B>{settings.BASE_CHARACTER_TYPECLASS}</B> "
        "or a subclass of that. <BR>If your custom class is not found in the list, it may not be imported "
        "into Evennia yet.",
        choices=lambda: adminutils.get_and_load_typeclasses(parent=ObjectDB),
    )

    db_lock_storage = forms.CharField(
        label="Locks",
        required=False,
        widget=forms.Textarea(attrs={"cols": "100", "rows": "2"}),
        help_text="In-game lock definition string. If not given, defaults will be used. "
        "This string should be on the form "
        "<i>type:lockfunction(args);type2:lockfunction2(args);...",
    )
    db_cmdset_storage = forms.CharField(
        label="CmdSet",
        initial="",
        required=False,
        widget=forms.TextInput(attrs={"size": "78"}),
    )

    # This is not working well because it will not properly allow an empty choice, and will
    # also not work well for comma-separated storage without more work. Notably, it's also
    # a bit hard to visualize.
    # db_cmdset_storage = forms.MultipleChoiceField(
    #     label="CmdSet",
    #     required=False,
    #     choices=adminutils.get_and_load_typeclasses(parent=ObjectDB))

    db_location = forms.ModelChoiceField(
        ObjectDB.objects.all(),
        label="Location",
        required=False,
        widget=ForeignKeyRawIdWidget(
            ObjectDB._meta.get_field("db_location").remote_field, admin.site
        ),
        help_text="The (current) in-game location.<BR>"
        "Usually a Room but can be<BR>"
        "empty for un-puppeted Characters.",
    )
    db_home = forms.ModelChoiceField(
        ObjectDB.objects.all(),
        label="Home",
        required=False,
        widget=ForeignKeyRawIdWidget(
            ObjectDB._meta.get_field("db_location").remote_field, admin.site
        ),
        help_text="Fallback in-game location.<BR>"
        "All objects should usually have<BR>"
        "a home location.",
    )
    db_destination = forms.ModelChoiceField(
        ObjectDB.objects.all(),
        label="Destination",
        required=False,
        widget=ForeignKeyRawIdWidget(
            ObjectDB._meta.get_field("db_destination").remote_field, admin.site
        ),
        help_text="Only used by Exits.",
    )

    def __init__(self, *args, **kwargs):
        """
        Tweak some fields dynamically.

        """
        super().__init__(*args, **kwargs)

        # set default home
        home_id = str(settings.DEFAULT_HOME)
        home_id = home_id[1:] if home_id.startswith("#") else home_id
        default_home = ObjectDB.objects.filter(id=home_id)
        if default_home:
            default_home = default_home[0]
        self.fields["db_home"].initial = default_home
        self.fields["db_location"].initial = default_home

        # better help text for cmdset_storage
        char_cmdset = settings.CMDSET_CHARACTER
        account_cmdset = settings.CMDSET_ACCOUNT
        self.fields["db_cmdset_storage"].help_text = (
            "Path to Command-set path. Most non-character objects don't need a cmdset"
            " and can leave this field blank. Default cmdset-path<BR> for Characters "
            f"is <strong>{char_cmdset}</strong> ."
        )


class ObjectEditForm(ObjectCreateForm):
    """
    Form used for editing. Extends the create one with more fields

    """

    class Meta:
        model = ObjectDB
        fields = "__all__"

    db_account = forms.ModelChoiceField(
        AccountDB.objects.all(),
        label="Puppeting Account",
        required=False,
        widget=ForeignKeyRawIdWidget(
            ObjectDB._meta.get_field("db_account").remote_field, admin.site
        ),
        help_text="An Account puppeting this Object (if any).<BR>Note that when a user logs "
        "off/unpuppets, this<BR>field will be empty again. This is normal.",
    )


@admin.register(ObjectDB)
class ObjectAdmin(admin.ModelAdmin):
    """
    Describes the admin page for Objects.

    """

    inlines = [ObjectTagInline, ObjectAttributeInline]
    list_display = (
        "id",
        "db_key",
        "db_typeclass_path",
        "db_location",
        "db_destination",
        "db_account",
        "db_date_created",
    )
    list_display_links = ("id", "db_key")
    ordering = ["-db_date_created", "-id"]
    search_fields = [
        "=id",
        "^db_key",
        "db_typeclass_path",
        "^db_account__db_key",
        "^db_location__db_key",
    ]
    raw_id_fields = ("db_destination", "db_location", "db_home", "db_account")
    readonly_fields = ("serialized_string", "link_button")

    save_as = True
    save_on_top = True
    list_select_related = True
    view_on_site = False
    list_filter = ("db_typeclass_path",)

    # editing fields setup

    form = ObjectEditForm
    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("db_key", "db_typeclass_path"),
                    ("db_location", "db_home", "db_destination"),
                    ("db_account", "link_button"),
                    "db_cmdset_storage",
                    "db_lock_storage",
                    "serialized_string",
                )
            },
        ),
    )

    add_form = ObjectCreateForm
    add_fieldsets = (
        (
            None,
            {
                "fields": (
                    ("db_key", "db_typeclass_path"),
                    ("db_location", "db_home", "db_destination"),
                    "db_cmdset_storage",
                )
            },
        ),
    )

    def serialized_string(self, obj):
        """
        Get the serialized version of the object.

        """
        from evennia.utils import dbserialize

        return str(dbserialize.pack_dbobj(obj))

    serialized_string.help_text = (
        "Copy & paste this string into an Attribute's `value` field to store this object there."
    )

    def get_fieldsets(self, request, obj=None):
        """
        Return fieldsets.

        Args:
            request (Request): Incoming request.
            obj (Object, optional): Database object.
        """
        if not obj:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        """
        Use special form during creation.

        Args:
            request (Request): Incoming request.
            obj (Object, optional): Database object.

        """
        help_texts = kwargs.get("help_texts", {})
        help_texts["serialized_string"] = self.serialized_string.help_text
        kwargs["help_texts"] = help_texts

        defaults = {}
        if obj is None:
            defaults.update(
                {"form": self.add_form, "fields": flatten_fieldsets(self.add_fieldsets)}
            )
        defaults.update(kwargs)
        return super().get_form(request, obj, **defaults)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "account-object-link/<int:pk>",
                self.admin_site.admin_view(self.link_object_to_account),
                name="object-account-link",
            )
        ]
        return custom_urls + urls

    def link_button(self, obj):
        return format_html(
            '<a class="button" href="{}">Link to Account</a>&nbsp;',
            reverse("admin:object-account-link", args=[obj.pk]),
        )

    link_button.short_description = "Create attrs/locks for puppeting"
    link_button.allow_tags = True

    def link_object_to_account(self, request, object_id):
        """
        Link object and account when pressing the button.

        This will:

        - Set account.db._last_puppet to this object
        - Add object to account.db._playable_characters
        - Change object locks to allow puppeting by account

        """
        obj = self.get_object(request, object_id)
        account = obj.db_account

        if account:
            account.db._last_puppet = obj
            if not account.db._playable_characters:
                account.db._playable_characters = []
            if obj not in account.db._playable_characters:
                account.db._playable_characters.append(obj)
            if not obj.access(account, "puppet"):
                lock = obj.locks.get("puppet")
                lock += f" or pid({account.id})"
                obj.locks.add(lock)
            self.message_user(
                request,
                "Did the following (where possible): "
                f"Set Account.db._last_puppet = {obj}, "
                f"Added {obj} to Account.db._playable_characters list, "
                f"Added 'puppet:pid({account.id})' lock to {obj}.",
            )
        else:
            self.message_user(
                request,
                "Account must be connected for this action "
                "(set Puppeting Account and save this page first).",
                level=messages.ERROR,
            )

        # stay on the same page
        return HttpResponseRedirect(reverse("admin:objects_objectdb_change", args=[obj.pk]))

    def save_model(self, request, obj, form, change):
        """
        Model-save hook.

        Args:
            request (Request): Incoming request.
            obj (Object): Database object.
            form (Form): Form instance.
            change (bool): If this is a change or a new object.

        """
        if not change:
            # adding a new object
            # have to call init with typeclass passed to it
            obj.set_class_from_typeclass(typeclass_path=obj.db_typeclass_path)
            obj.save()
            obj.basetype_setup()
            obj.basetype_posthook_setup()
            obj.at_object_creation()
        else:
            obj.save()
            obj.at_init()

    def response_add(self, request, obj, post_url_continue=None):
        from django.http import HttpResponseRedirect
        from django.urls import reverse

        return HttpResponseRedirect(reverse("admin:objects_objectdb_change", args=[obj.id]))
