from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.core.urlresolvers import reverse
from django.forms import Textarea
from src.typeclasses.models import Attribute, Tag


class PickledWidget(Textarea):
    pass


class TagAdmin(admin.ModelAdmin):
    fields = ('db_key', 'db_category', 'db_data')


class TagInline(admin.TabularInline):
    # Set this to the through model of your desired M2M when subclassing.
    model = None
    raw_id_fields = ('tag',)
    extra = 0


class AttributeInline(admin.TabularInline):
    """
    Inline creation of player attributes
    """
    # Set this to the through model of your desired M2M when subclassing.
    model = None
    extra = 3
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
        return instance.attribute.db_value

    def strvalue(self, instance):
        if not instance.id:
            return "Not yet set or saved."
        return instance.attribute.db_strvalue


class AttributeAdmin(ModelAdmin):
    """
    Defines how to display the attributes
    """
    search_fields = ('db_key', 'db_strvalue', 'db_value')
    list_display = ('db_key', 'db_strvalue', 'db_value')

admin.site.register(Attribute, AttributeAdmin)
admin.site.register(Tag, TagAdmin)