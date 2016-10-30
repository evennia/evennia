from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.core.urlresolvers import reverse
from evennia.typeclasses.models import Attribute, Tag


class TagAdmin(admin.ModelAdmin):
    """
    A django Admin wrapper for Tags.

    """
    search_fields = ('db_key', 'db_category', 'db_tagtype')
    list_display = ('db_key', 'db_category', 'db_tagtype', 'db_data')
    fields = ('db_key', 'db_category', 'db_tagtype', 'db_data')
    list_filter = ('db_tagtype',)


class TagInline(admin.TabularInline):
    """
    A handler for inline Tags.

    """
    # Set this to the through model of your desired M2M when subclassing.
    model = None
    fields = ('tag', 'key', 'category', 'data', 'tagtype')
    raw_id_fields = ('tag',)
    readonly_fields = ('key', 'category', 'data', 'tagtype')
    extra = 0
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
