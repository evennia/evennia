from django.contrib import admin
from src.channels.models import CommChannel, CommChannelMessage

class CommChannelAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner')
admin.site.register(CommChannel, CommChannelAdmin)

class CommChannelMessageAdmin(admin.ModelAdmin):
    list_display = ('channel', 'date_sent', 'message')
admin.site.register(CommChannelMessage, CommChannelMessageAdmin)