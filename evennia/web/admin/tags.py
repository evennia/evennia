"""
Tag admin

"""


import traceback
from datetime import datetime

from django import forms
from django.contrib import admin

from evennia.typeclasses.tags import Tag
from evennia.utils.dbserialize import _SaverSet, from_pickle
from evennia.utils.picklefield import PickledFormField


class TagForm(forms.ModelForm):
    """
    Form to display fields in the stand-alone Tag display.

    """

    db_key = forms.CharField(label="Key/Name", required=True, help_text="The main key identifier")
    db_category = forms.CharField(
        label="Category",
        help_text="Used for grouping tags. Unset (default) gives a category of None",
        required=False,
    )
    db_tagtype = forms.ChoiceField(
        label="Type",
        choices=[(None, "-"), ("alias", "alias"), ("permission", "permission")],
        help_text="Tags are used for different things. Unset for regular tags.",
        required=False,
    )
    db_model = forms.ChoiceField(
        label="Model",
        required=False,
        help_text="Each Tag can only 'attach' to one type of entity.",
        choices=(
            [
                ("objectdb", "objectdb"),
                ("accountdb", "accountdb"),
                ("scriptdb", "scriptdb"),
                ("channeldb", "channeldb"),
                ("helpentry", "helpentry"),
                ("msg", "msg"),
            ]
        ),
    )
    db_data = forms.CharField(
        label="Data",
        help_text="Usually unused. Intended for info about the tag itself",
        widget=forms.Textarea(attrs={"cols": "100", "rows": "2"}),
        required=False,
    )

    class Meta:
        fields = ("tag_key", "tag_category", "tag_data", "tag_type")


class InlineTagForm(forms.ModelForm):
    """
    Form for displaying tags inline together with other entities.

    This form overrides the base behavior of the ModelForm that would be used for a
    Tag-through-model.  Since the through-models only have access to the foreignkeys of the Tag and
    the Object that they're attached to, we need to spoof the behavior of it being a form that would
    correspond to its tag, or the creation of a tag. Instead of being saved, we'll call to the
    Object's handler, which will handle the creation, change, or deletion of a tag for us, as well
    as updating the handler's cache so that all changes are instantly updated in-game.
    """

    tag_key = forms.CharField(
        label="Tag Name", required=True, help_text="This is the main key identifier"
    )
    tag_category = forms.CharField(
        label="Category",
        help_text="Used for grouping tags. Unset (default) gives a category of None",
        required=False,
    )
    tag_type = forms.ChoiceField(
        label="Type",
        choices=[(None, "-"), ("alias", "alias"), ("permission", "permission")],
        help_text="Tags are used for different things. Unset for regular tags.",
        required=False,
    )
    tag_data = forms.CharField(
        label="Data",
        widget=forms.Textarea(attrs={"cols": "100", "rows": "2"}),
        help_text="Usually unused. Intended for eventual info about the tag itself",
        required=False,
    )

    class Meta:
        fields = ("tag_key", "tag_category", "tag_data", "tag_type")

    def __init__(self, *args, **kwargs):
        """
        If we have a tag, then we'll prepopulate our instance with the fields we'd expect it
        to have based on the tag. tag_key, tag_category, tag_type, and tag_data all refer to
        the corresponding tag fields. The initial data of the form fields will similarly be
        populated.
        """
        super().__init__(*args, **kwargs)
        tagkey = None
        tagcategory = None
        tagtype = None
        tagdata = None
        if hasattr(self.instance, "tag"):
            tagkey = self.instance.tag.db_key
            tagcategory = self.instance.tag.db_category
            tagtype = self.instance.tag.db_tagtype
            tagdata = self.instance.tag.db_data
            self.fields["tag_key"].initial = tagkey
            self.fields["tag_category"].initial = tagcategory
            self.fields["tag_type"].initial = tagtype
            self.fields["tag_data"].initial = tagdata
        self.instance.tag_key = tagkey
        self.instance.tag_category = tagcategory
        self.instance.tag_type = tagtype
        self.instance.tag_data = tagdata

    def save(self, commit=True):
        """
        One thing we want to do here is the or None checks, because forms are saved with an empty
        string rather than null from forms, usually, and the Handlers may handle empty strings
        differently than None objects. So for consistency with how things are handled in game,
        we'll try to make sure that empty form fields will be None, rather than ''.
        """
        # we are spoofing a tag for the Handler that will be called
        # instance = super().save(commit=False)
        instance = self.instance
        instance.tag_key = self.cleaned_data["tag_key"]
        instance.tag_category = self.cleaned_data["tag_category"] or None
        instance.tag_type = self.cleaned_data["tag_type"] or None
        instance.tag_data = self.cleaned_data["tag_data"] or None
        return instance


class TagFormSet(forms.BaseInlineFormSet):
    """
    The Formset handles all the inline forms that are grouped together on the change page of the
    corresponding object. All the tags will appear here, and we'll save them by overriding the
    formset's save method. The forms will similarly spoof their save methods to return an instance
    which hasn't been saved to the database, but have the relevant fields filled out based on the
    contents of the cleaned form. We'll then use that to call to the handler of the corresponding
    Object, where the handler is an AliasHandler, PermissionsHandler, or TagHandler, based on the
    type of tag.
    """

    verbose_name = "Tag"
    verbose_name_plural = "Tags"

    def save(self, commit=True):
        def get_handler(finished_object):
            related = getattr(finished_object, self.related_field)
            try:
                tagtype = finished_object.tag_type
            except AttributeError:
                tagtype = finished_object.tag.db_tagtype
            if tagtype == "alias":
                handler_name = "aliases"
            elif tagtype == "permission":
                handler_name = "permissions"
            else:
                handler_name = "tags"
            return getattr(related, handler_name)

        instances = super().save(commit=False)
        # self.deleted_objects is a list created when super of save is called, we'll remove those
        for obj in self.deleted_objects:
            handler = get_handler(obj)
            handler.remove(obj.tag_key, category=obj.tag_category)
        for instance in instances:
            handler = get_handler(instance)
            handler.add(instance.tag_key, category=instance.tag_category, data=instance.tag_data)


class TagInline(admin.TabularInline):
    """
    A handler for inline Tags. This class should be subclassed in the admin of your models,
    and the 'model' and 'related_field' class attributes must be set. model should be the
    through model (ObjectDB_db_tag', for example), while related field should be the name
    of the field on that through model which points to the model being used: 'objectdb',
    'msg', 'accountdb', etc.
    """

    # Set this to the through model of your desired M2M when subclassing.
    model = None
    verbose_name = "Tag"
    verbose_name_plural = "Tags"
    form = InlineTagForm
    formset = TagFormSet
    related_field = None  # Must be 'objectdb', 'accountdb', 'msg', etc. Set when subclassing
    # raw_id_fields = ('tag',)
    # readonly_fields = ('tag',)
    extra = 0

    def get_formset(self, request, obj=None, **kwargs):
        """
        get_formset has to return a class, but we need to make the class that we return
        know about the related_field that we'll use. Returning the class itself rather than
        a proxy isn't threadsafe, since it'd be the base class and would change if multiple
        people used the admin at the same time
        """
        formset = super().get_formset(request, obj, **kwargs)

        class ProxyFormset(formset):
            pass

        ProxyFormset.related_field = self.related_field
        return ProxyFormset


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """
    A django Admin wrapper for Tags.

    """

    search_fields = ("db_key", "db_category", "db_tagtype")
    list_display = ("db_key", "db_category", "db_tagtype", "db_model", "db_data")
    list_filter = ("db_tagtype", "db_category", "db_model")
    form = TagForm
    view_on_site = False

    fieldsets = (
        (
            None,
            {"fields": (("db_key", "db_category"), ("db_tagtype", "db_model"), "db_data")},
        ),
    )
