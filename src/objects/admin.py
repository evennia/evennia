from src.objects.models import Attribute, Object, CommChannel, CommChannelMessage
from django.contrib import admin

class AttributeAdmin(admin.ModelAdmin):
    list_display = ('attr_object', 'attr_name', 'attr_value',)
    search_fields = ['attr_name']
admin.site.register(Attribute, AttributeAdmin)

class ObjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'type', 'date_created')
    list_filter = ('type',)
    search_fields = ['name']
    save_on_top = True
admin.site.register(Object, ObjectAdmin)

class CommChannelAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner')
admin.site.register(CommChannel, CommChannelAdmin)

class CommChannelMessageAdmin(admin.ModelAdmin):
    list_display = ('channel', 'message')
admin.site.register(CommChannelMessage, CommChannelMessageAdmin)