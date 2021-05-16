#
# This sets up how models are displayed
# in the web admin interface.
#
from django.conf import settings

from evennia.typeclasses.admin import AttributeInline, TagInline

from evennia.scripts.models import ScriptDB
from django.contrib import admin


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


class ScriptDBAdmin(admin.ModelAdmin):
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
    )
    list_display_links = ("id", "db_key")
    ordering = ["db_obj", "db_typeclass_path"]
    search_fields = ["^db_key", "db_typeclass_path"]
    save_as = True
    save_on_top = True
    list_select_related = True
    raw_id_fields = ("db_obj",)

    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("db_key", "db_typeclass_path"),
                    "db_interval",
                    "db_repeats",
                    "db_start_delay",
                    "db_persistent",
                    "db_obj",
                )
            },
        ),
    )
    inlines = [ScriptTagInline, ScriptAttributeInline]

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


admin.site.register(ScriptDB, ScriptDBAdmin)
