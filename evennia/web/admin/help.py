"""
This defines how to edit help entries in Admin.
"""
from django import forms
from django.contrib import admin

from evennia.help.models import HelpEntry

from .tags import TagInline


class HelpTagInline(TagInline):
    model = HelpEntry.db_tags.through
    related_field = "helpentry"


class HelpEntryForm(forms.ModelForm):
    "Defines how to display the help entry"

    class Meta:
        model = HelpEntry
        fields = "__all__"

    db_help_category = forms.CharField(
        label="Help category", initial="General", help_text="organizes help entries in lists"
    )
    db_lock_storage = forms.CharField(
        label="Locks",
        initial="view:all()",
        required=False,
        widget=forms.Textarea(attrs={"cols": "100", "rows": "2"}),
        help_text="Set lock to view:all() unless you want it to only show to certain users."
        "<BR>Use the `edit:` limit if wanting to limit who can edit from in-game. By default it's "
        "only limited to who can use the `sethelp` command (Builders).",
    )


@admin.register(HelpEntry)
class HelpEntryAdmin(admin.ModelAdmin):
    "Sets up the admin manaager for help entries"
    inlines = [HelpTagInline]
    list_display = ("id", "db_key", "db_help_category", "db_lock_storage", "db_date_created")
    list_display_links = ("id", "db_key")
    search_fields = ["^db_key", "db_entrytext"]
    ordering = ["db_help_category", "db_key"]
    list_filter = ["db_help_category"]
    save_as = True
    save_on_top = True
    list_select_related = True
    view_on_site = False

    form = HelpEntryForm
    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("db_key", "db_help_category"),
                    "db_entrytext",
                    "db_lock_storage",
                    # "db_date_created",
                ),
            },
        ),
    )
