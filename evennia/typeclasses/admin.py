from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.core.urlresolvers import reverse
from evennia.typeclasses.models import Attribute, Tag
from django import forms


class TagAdmin(admin.ModelAdmin):
    """
    A django Admin wrapper for Tags.

    """
    search_fields = ('db_key', 'db_category', 'db_tagtype')
    list_display = ('db_key', 'db_category', 'db_tagtype', 'db_data')
    fields = ('db_key', 'db_category', 'db_tagtype', 'db_data')
    list_filter = ('db_tagtype',)


class TagForm(forms.ModelForm):
    tag_key = forms.CharField(label='Tag Name')
    tag_category = forms.CharField(label="Category", required=False)
    tag_type = forms.CharField(label="Type", required=False)
    tag_data = forms.CharField(label="Data", required=False)

    def __init__(self, *args, **kwargs):
        super(TagForm, self).__init__(*args, **kwargs)
        if hasattr(self.instance, 'tag'):
            self.fields['tag_key'].initial = self.instance.tag.db_key
            self.fields['tag_category'].initial = self.instance.tag.db_category
            self.fields['tag_type'].initial = self.instance.tag.db_tagtype
            self.fields['tag_data'].initial = self.instance.tag.db_data

    def save(self, commit=True):
        # we are spoofing a tag for the Handler that will be called
        #instance = super(TagForm, self).save(commit=False)
        instance = self.instance
        instance.tag_key = self.cleaned_data['tag_key']
        instance.tag_category = self.cleaned_data['tag_category'] or None
        instance.tag_type = self.cleaned_data['tag_type'] or None
        instance.tag_data = self.cleaned_data['tag_data'] or None
        return instance


class TagFormSet(forms.BaseInlineFormSet):
    def save(self, commit=True):
        print "inside TagFormSet"
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
        instances = super(TagFormSet, self).save(commit=False)
        for obj in self.deleted_objects:
            handler = get_handler(obj)
            try:
                tagkey = obj.tag_key
            except AttributeError:
                tagkey = obj.tag.db_key
            handler.remove(tagkey)
        for instance in instances:
            handler = get_handler(instance)
            handler.add(instance.tag_key)


class TagInline(admin.TabularInline):
    """
    A handler for inline Tags.

    """
    # Set this to the through model of your desired M2M when subclassing.
    model = None
    form = TagForm
    formset = TagFormSet
    related_field = None
    #fields = ('tag', 'key', 'category', 'data', 'tagtype')
    raw_id_fields = ('tag',)
    readonly_fields = ('tag',)
    #readonly_fields = ('key', 'category', 'data', 'tagtype')
    extra = 0

    def get_formset(self, request, obj=None, **kwargs):
        """
        get_formset has to return a class, but we need to make the class that we return
        know about the related_field that we'll use. Returning the class itself rather than
        a proxy isn't threadsafe, since it'd be the base class and would change if multiple
        people used the admin at the same time
        """
        formset = super(TagInline, self).get_formset(request, obj, **kwargs)
        class ProxyFormset(formset):
            pass
        ProxyFormset.related_field = self.related_field
        return ProxyFormset

    def key(self, instance):
        if not instance.id:
            return "Not yet set or saved."
        return '<strong><a href="%s">%s</a></strong>' % (
            reverse("admin:typeclasses_tag_change",
                    args=[instance.tag.id]),
            instance.tag.db_key)
    key.allow_tags = True
    
    def category(self, instance):
        if not instance.id:
            return "Not yet set or saved."
        return instance.tag.db_category

    def data(self, instance):
        if not instance.id:
            return "Not yet set or saved."
        return instance.tag.db_data
    
    def tagtype(self, instance):
        if not instance.id:
            return "Not yet set or saved."
        return instance.tag.db_tagtype


class AttributeInline(admin.TabularInline):
    """
    Inline creation of player attributes.j

    """
    # Set this to the through model of your desired M2M when subclassing.
    model = None
    extra = 1
    #form = AttributeForm
    fields = ('attribute', 'key', 'value', 'strvalue')
    raw_id_fields = ('attribute',)
    readonly_fields = ('key', 'value', 'strvalue')

    def key(self, instance):
        if not instance.id:
            return "Not yet set or saved."
        return '<strong><a href="%s">%s</a></strong>' % (
            reverse("admin:typeclasses_attribute_change",
                    args=[instance.attribute.id]),
            instance.attribute.db_key)

    key.allow_tags = True

    def value(self, instance):
        if not instance.id:
            return "Not yet set or saved."
        return instance.attribute.value

    def strvalue(self, instance):
        if not instance.id:
            return "Not yet set or saved."
        return instance.attribute.strvalue


class AttributeAdmin(ModelAdmin):
    """
    Defines how to display the attributes.

    """
    search_fields = ('db_key', 'db_strvalue', 'db_value')
    list_display = ('db_key', 'db_strvalue', 'db_value')
    permitted_types = ('str', 'unicode', 'int', 'float', 'NoneType', 'bool')

    fields = ('db_key', 'db_value', 'db_strvalue', 'db_category',
              'db_lock_storage', 'db_model', 'db_attrtype')

    def get_readonly_fields(self, request, obj=None):
        if obj.db_value.__class__.__name__ not in self.permitted_types:
            return ['db_value']
        return []

admin.site.register(Attribute, AttributeAdmin)
admin.site.register(Tag, TagAdmin)
