#
# This sets up how models are displayed
# in the web admin interface.
#
from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.admin.utils import flatten_fieldsets
from django.utils.translation import gettext as _

from evennia.objects.models import ObjectDB
from .attributes import AttributeInline
from .tags import TagInline
from . import utils as adminutils


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
        "as part of Evennia's startup.",
        choices=adminutils.get_and_load_typeclasses(parent=ObjectDB))

    db_cmdset_storage = forms.CharField(
        label="CmdSet",
        initial="",
        required=False,
        widget=forms.TextInput(attrs={"size": "78"}),
        help_text="Most non-character objects don't need a cmdset"
        " and can leave this field blank.",
    )

    raw_id_fields = ("db_destination", "db_location", "db_home")


class ObjectEditForm(ObjectCreateForm):
    """
    Form used for editing. Extends the create one with more fields

    """

    class Meta:
        model = ObjectDB
        fields = "__all__"

    db_lock_storage = forms.CharField( label="Locks",
        required=False,
        widget=forms.Textarea(attrs={"cols": "100", "rows": "2"}),
        help_text="In-game lock definition string. If not given, defaults will be used. "
        "This string should be on the form "
        "<i>type:lockfunction(args);type2:lockfunction2(args);...",
    )

    db_typeclass_path = forms.ChoiceField(
        label="Typeclass",
        help_text="This is the Python-path to the class implementing the actual object functionality. "
        "<BR>If your custom class is not found here, it may not be imported as part of Evennia's startup.",
        choices=adminutils.get_and_load_typeclasses(parent=ObjectDB))


@admin.register(ObjectDB)
class ObjectAdmin(admin.ModelAdmin):
    """
    Describes the admin page for Objects.

    """

    inlines = [ObjectTagInline, ObjectAttributeInline]
    list_display = ("id", "db_key", "db_account", "db_typeclass_path")
    list_display_links = ("id", "db_key")
    ordering = ["db_account", "db_typeclass_path", "id"]
    search_fields = ["=id", "^db_key", "db_typeclass_path", "^db_account__db_key"]
    raw_id_fields = ("db_destination", "db_location", "db_home")
    readonly_fields = ("serialized_string", )

    save_as = True
    save_on_top = True
    list_select_related = True
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
                    "db_cmdset_storage",
                    "db_lock_storage",
                    "serialized_string"
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
                    ("db_location", "db_home"),
                    "db_destination",
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
        "Copy & paste this string into an Attribute's `value` field to store it there. "
        "Note that you cannot (easily) add multiple objects this way - better do that "
        "in code.")

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
            obj.basetype_setup()
            obj.basetype_posthook_setup()
            obj.at_object_creation()
        obj.at_init()

    def response_add(self, request, obj, post_url_continue=None):
        from django.http import HttpResponseRedirect
        from django.urls import reverse

        return HttpResponseRedirect(reverse("admin:objects_objectdb_change", args=[obj.id]))
