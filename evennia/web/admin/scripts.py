#
# This sets up how models are displayed
# in the web admin interface.
#
from django import forms
from django.conf import settings
from django.contrib import admin

from evennia.scripts.models import ScriptDB

from . import utils as adminutils
from .attributes import AttributeInline
from .tags import TagInline


class ScriptForm(forms.ModelForm):

    db_key = forms.CharField(
        label="Name/Key", help_text="Script identifier, shown in listings etc."
    )

    db_typeclass_path = forms.ChoiceField(
        label="Typeclass",
        help_text="This is the Python-path to the class implementing the actual script functionality. "
        "<BR>If your custom class is not found here, it may not be imported into Evennia yet.",
        choices=lambda: adminutils.get_and_load_typeclasses(
            parent=ScriptDB, excluded_parents=["evennia.prototypes.prototypes.DbPrototype"]
        ),
    )

    db_lock_storage = forms.CharField(
        label="Locks",
        required=False,
        widget=forms.Textarea(attrs={"cols": "100", "rows": "2"}),
        help_text="In-game lock definition string. If not given, defaults will be used. "
        "This string should be on the form "
        "<i>type:lockfunction(args);type2:lockfunction2(args);...",
    )

    db_interval = forms.IntegerField(
        label="Repeat Interval",
        help_text="Optional timer component.<BR>How often to call the Script's<BR>`at_repeat` hook, in seconds."
        "<BR>Set to 0 to disable.",
    )
    db_repeats = forms.IntegerField(
        help_text="Only repeat this many times." "<BR>Set to 0 to run indefinitely."
    )
    db_start_delay = forms.BooleanField(help_text="Wait <B>Interval</B> seconds before first call.")
    db_persistent = forms.BooleanField(
        label="Survives reboot", help_text="If unset, a server reboot will remove the timer."
    )


class ScriptTagInline(TagInline):
    """
    Inline script tags.

    """

    model = ScriptDB.db_tags.through
    related_field = "scriptdb"


class ScriptAttributeInline(AttributeInline):
    """
    Inline attribute tags.

    """

    model = ScriptDB.db_attributes.through
    related_field = "scriptdb"


@admin.register(ScriptDB)
class ScriptAdmin(admin.ModelAdmin):
    """
    Displaying the main Script page.

    """

    list_display = (
        "id",
        "db_key",
        "db_typeclass_path",
        "db_obj",
        "db_interval",
        "db_repeats",
        "db_persistent",
        "db_date_created",
    )
    list_display_links = ("id", "db_key")
    ordering = ["-db_date_created", "-id"]
    search_fields = ["=id", "^db_key", "db_typeclass_path"]
    readonly_fields = ["serialized_string"]
    form = ScriptForm
    save_as = True
    save_on_top = True
    list_select_related = True
    view_on_site = False
    raw_id_fields = ("db_obj",)

    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("db_key", "db_typeclass_path"),
                    ("db_interval", "db_repeats", "db_start_delay", "db_persistent"),
                    "db_obj",
                    "db_lock_storage",
                    "serialized_string",
                )
            },
        ),
    )
    inlines = [ScriptTagInline, ScriptAttributeInline]

    def serialized_string(self, obj):
        """
        Get the serialized version of the object.

        """
        from evennia.utils import dbserialize

        return str(dbserialize.pack_dbobj(obj))

    serialized_string.help_text = (
        "Copy & paste this string into an Attribute's `value` field to store this script there."
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
            obj.set_class_from_typeclass(typeclass_path=obj.db_typeclass_path)
