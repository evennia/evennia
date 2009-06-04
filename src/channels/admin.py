from django.contrib import admin
from src.channels.models import CommChannel, CommChannelMessage, CommChannelMembership

class CommChannelAdmin(admin.ModelAdmin):
    list_display = ('name', 'ansi_name', 'owner', 'description', 'is_joined_by_default')
admin.site.register(CommChannel, CommChannelAdmin)

class CommChannelMembershipAdmin(admin.ModelAdmin):
    list_display = ('channel', 'listener', 'user_alias', 'is_listening')
admin.site.register(CommChannelMembership, CommChannelMembershipAdmin)

class CommChannelMessageAdmin(admin.ModelAdmin):
    list_display = ('channel', 'date_sent', 'message')
admin.site.register(CommChannelMessage, CommChannelMessageAdmin)