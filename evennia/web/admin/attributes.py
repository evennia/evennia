"""
Attribute admin.

Note that we don't present a separate admin for these, since they are only
relevant together with a specific object.

"""

import traceback
from datetime import datetime

from django import forms
from django.contrib import admin

from evennia.typeclasses.attributes import Attribute
from evennia.utils.dbserialize import _SaverSet, from_pickle
from evennia.utils.picklefield import PickledFormField


class AttributeForm(forms.ModelForm):
    """
    This form overrides the base behavior of the ModelForm that would be used for a Attribute-through-model.
    Since the through-models only have access to the foreignkeys of the Attribute and the Object that they're
    attached to, we need to spoof the behavior of it being a form that would correspond to its Attribute,
    or the creation of an Attribute. Instead of being saved, we'll call to the Object's handler, which will handle
    the creation, change, or deletion of an Attribute for us, as well as updating the handler's cache so that all
    changes are instantly updated in-game.
    """

    attr_key = forms.CharField(
        label="Attribute Name",
        required=False,
        help_text="The main identifier of the Attribute. For Nicks, this is the pattern-matching string.",
    )
    attr_category = forms.CharField(
        label="Category",
        help_text="Categorization. Unset (default) gives a category of `None`, which is "
        "is what is searched with e.g. `obj.db.attrname`. For 'nick'-type attributes, this is usually "
        "'inputline' or 'channel'.",
        required=False,
        max_length=128,
    )
    attr_value = PickledFormField(
        label="Value",
        help_text="Value to pickle/save. Db-objects are serialized as a list "
        "containing `__packed_dbobj__` (they can't easily be added from here). Nicks "
        "store their pattern-replacement here.",
        required=False,
    )
    attr_type = forms.ChoiceField(
        label="Type",
        choices=[(None, "-"), ("nick", "nick")],
        help_text="Unset for regular Attributes, 'nick' for Nick-replacement usage.",
        required=False,
    )
    attr_lockstring = forms.CharField(
        label="Locks",
        required=False,
        help_text="Lock string on the form locktype:lockdef;lockfunc:lockdef;...",
        widget=forms.Textarea(attrs={"rows": 1, "cols": 8}),
    )

    class Meta:
        fields = ("attr_key", "attr_value", "attr_category", "attr_lockstring", "attr_type")

    def __init__(self, *args, **kwargs):
        """
        If we have an Attribute, then we'll prepopulate our instance with the fields we'd expect it
        to have based on the Attribute. attr_key, attr_category, attr_value, attr_type,
        and attr_lockstring all refer to the corresponding Attribute fields. The initial data of the form fields will
        similarly be populated.

        """
        super().__init__(*args, **kwargs)
        attr_key = None
        attr_category = None
        attr_value = None
        attr_type = None
        attr_lockstring = None
        if hasattr(self.instance, "attribute"):
            attr_key = self.instance.attribute.db_key
            attr_category = self.instance.attribute.db_category
            attr_value = self.instance.attribute.db_value
            attr_type = self.instance.attribute.db_attrtype
            attr_lockstring = self.instance.attribute.db_lock_storage
            self.fields["attr_key"].initial = attr_key
            self.fields["attr_category"].initial = attr_category
            self.fields["attr_type"].initial = attr_type
            self.fields["attr_value"].initial = attr_value
            self.fields["attr_lockstring"].initial = attr_lockstring
        self.instance.attr_key = attr_key
        self.instance.attr_category = attr_category
        self.instance.attr_value = attr_value

        # prevent from being transformed to str
        if isinstance(attr_value, (set, _SaverSet)):
            self.fields["attr_value"].disabled = True

        self.instance.deserialized_value = from_pickle(attr_value)
        self.instance.attr_type = attr_type
        self.instance.attr_lockstring = attr_lockstring

    def save(self, commit=True):
        """
        One thing we want to do here is the or None checks, because forms are saved with an empty
        string rather than null from forms, usually, and the Handlers may handle empty strings
        differently than None objects. So for consistency with how things are handled in game,
        we'll try to make sure that empty form fields will be None, rather than ''.
        """
        # we are spoofing an Attribute for the Handler that will be called
        instance = self.instance
        instance.attr_key = self.cleaned_data["attr_key"] or "no_name_entered_for_attribute"
        instance.attr_category = self.cleaned_data["attr_category"] or None
        instance.attr_value = self.cleaned_data["attr_value"]
        # convert the serialized string value into an object, if necessary, for AttributeHandler
        instance.attr_value = from_pickle(instance.attr_value)
        instance.attr_type = self.cleaned_data["attr_type"] or None
        instance.attr_lockstring = self.cleaned_data["attr_lockstring"]
        return instance

    def clean_attr_value(self):
        """
        Prevent certain data-types from being cleaned due to literal_eval
        failing on them. Otherwise they will be turned into str.

        """
        data = self.cleaned_data["attr_value"]
        initial = self.instance.attr_value
        if isinstance(initial, (set, _SaverSet, datetime)):
            return initial
        return data


class AttributeFormSet(forms.BaseInlineFormSet):
    """
    Attribute version of TagFormSet, as above.
    """

    def save(self, commit=True):
        def get_handler(finished_object):
            related = getattr(finished_object, self.related_field)
            try:
                attrtype = finished_object.attr_type
            except AttributeError:
                attrtype = finished_object.attribute.db_attrtype
            if attrtype == "nick":
                handler_name = "nicks"
            else:
                handler_name = "attributes"
            return getattr(related, handler_name)

        instances = super().save(commit=False)
        for obj in self.deleted_objects:
            # self.deleted_objects is a list created when super of save is called, we'll remove those
            handler = get_handler(obj)
            handler.remove(obj.attr_key, category=obj.attr_category)

        for instance in instances:
            handler = get_handler(instance)

            value = instance.attr_value

            try:
                handler.add(
                    instance.attr_key,
                    value,
                    category=instance.attr_category,
                    strattr=False,
                    lockstring=instance.attr_lockstring,
                )
            except (TypeError, ValueError):
                # catch errors in nick templates and continue
                traceback.print_exc()
                continue


class AttributeInline(admin.TabularInline):
    """
    A handler for inline Attributes. This class should be subclassed in the admin of your models,
    and the 'model' and 'related_field' class attributes must be set. model should be the
    through model (ObjectDB_db_tag', for example), while related field should be the name
    of the field on that through model which points to the model being used: 'objectdb',
    'msg', 'accountdb', etc.
    """

    # Set this to the through model of your desired M2M when subclassing.
    model = None
    verbose_name = "Attribute"
    verbose_name_plural = "Attributes"
    form = AttributeForm
    formset = AttributeFormSet
    related_field = None  # Must be 'objectdb', 'accountdb', 'msg', etc. Set when subclassing
    # raw_id_fields = ('attribute',)
    # readonly_fields = ('attribute',)
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
