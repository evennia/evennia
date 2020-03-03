#
# This sets up how models are displayed
# in the web admin interface.
#
from django import forms
from django.conf import settings
from django.contrib import admin
from evennia.typeclasses.admin import AttributeInline, TagInline
from evennia.objects.models import ObjectDB
from evennia.accounts.models import AccountDB
from django.contrib.admin.utils import flatten_fieldsets
from evennia.utils.utils import class_from_module
import inspect


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


class CharacterForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        if 'initial' not in kwargs:
            kwargs['initial'] = {}
        if 'instance' in kwargs:
            kwargs['initial'].update({'superuser': kwargs['instance'].is_superuser})
            kwargs['initial'].update({
                'db_account': AccountDB.objects.get_account_from_uid(kwargs['instance'].db.creator_id)
                }
            )
        super().__init__(*args, **kwargs)

    class Meta(object):
        model = ObjectDB
        fields = "__all__"

    db_account = forms.ModelChoiceField(
        queryset=AccountDB.objects.all(),
        label="Player",
        help_text="Who should puppet this object?",
        required=False,
        )

    superuser = forms.BooleanField(
        label="Superuser?",
        required=False,
        disabled=True,
        help_text="You can't change this setting here; use the Account record."
        )


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

    # Potentially extendable (with some frontend work) to an AutoComplete or Select field
    # choices=[(key.get("typeclass"), key.get("typeclass")) for key in ObjectDB.objects.get_typeclass_totals()],

    db_typeclass_path = forms.CharField(
        label="Typeclass",
        initial=settings.BASE_OBJECT_TYPECLASS,
        widget=forms.TextInput(attrs={"size": "78"}),
        help_text="This defines what 'type' of entity this is. This variable holds a "
        "Python path to a module with a valid Evennia Typeclass. If you are "
        "creating a Character you should use the typeclass defined by "
        "settings.BASE_CHARACTER_TYPECLASS or one derived from that.",
    )

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
    class Meta(object):
        fields = "__all__"

    db_lock_storage = forms.CharField(
        label="Locks",
        required=False,
        widget=forms.Textarea(attrs={"cols": "100", "rows": "2"}),
        help_text="In-game lock definition string. If not given, defaults will be used. "
        "This string should be on the form "
        "<i>type:lockfunction(args);type2:lockfunction2(args);...",
    )


class ObjectDBAdmin(admin.ModelAdmin):
    """
    Describes the admin page for Objects.

    """

    inlines = [ObjectTagInline, ObjectAttributeInline]
    list_display = ("id", "db_key", "db_account", "db_typeclass_path")
    list_display_links = ("id", "db_key")
    ordering = ["db_account", "db_typeclass_path", "id"]
    search_fields = ["=id", "^db_key", "db_typeclass_path", "^db_account__db_key"]
    raw_id_fields = ("db_destination", "db_location", "db_home")

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
                    ("db_lock_storage",),
                    ("db_location", "db_home"),
                    "db_destination",
                    "db_cmdset_storage",
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

    character_form = CharacterForm
    character_fieldsets = (
        (
            None,
            {
                "fields": (
                    "db_key",
                    "db_typeclass_path",
                    ("db_account", "superuser",),
                    ("db_lock_storage",),
                    ("db_location", "db_home",),
                    "db_destination",
                    "db_cmdset_storage",
                )
            },
        ),
    )

    def get_fieldsets(self, request, obj=None):
        """
        Return fieldsets.

        Args:
            request (Request): Incoming request.
            obj (ObjectDB, optional): Database object.
        """
        from evennia.objects.objects import DefaultCharacter

        if not obj:
            return self.add_fieldsets
        elif DefaultCharacter in inspect.getmro(class_from_module(obj.db_typeclass_path)):
            return self.character_fieldsets
        return super().get_fieldsets(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        """
        Use special form during creation.

        Args:
            request (Request): Incoming request.
            obj (Object, optional): Database object.

        """
        defaults = {}
        if obj is None:
            defaults.update(
                {"form": self.add_form, "fields": flatten_fieldsets(self.add_fieldsets)}
            )
            defaults.update(kwargs)
        elif DefaultCharacter in inspect.getmro(class_from_module(obj.db_typeclass_path)):
            defaults.update(
                {"form": self.character_form, "fields": flatten_fieldsets(self.character_fieldsets)}
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
        # Reconnect sessions to new puppets
        # if 'db_account' in form.changed_data:
        # Note that the above fails in the edge case where you're setting the
        # Player to the creator_id because we're manually setting initial
        if obj.account:
            if settings.MULTISESSION_MODE in (0, 1):
                for character in obj.account.characters:
                    if character != obj:
                        character.account = None  # cleanup
                        character.save()
                obj.account.db._last_puppet = obj
                for session in obj.account.sessions.get():
                    obj.account.at_post_login(session=session)
            elif settings.MULTISESSION_MODE in (2,):
                obj.account.db._playable_characters = [
                    x for x in obj.account.db._playable_characters if x != obj
                ]
                obj.account.db._playable_characters.append(obj)
        obj.at_init()

    def response_add(self, request, obj, post_url_continue=None):
        from django.http import HttpResponseRedirect
        from django.urls import reverse

        return HttpResponseRedirect(reverse("admin:objects_objectdb_change", args=[obj.id]))


admin.site.register(ObjectDB, ObjectDBAdmin)
