from django.contrib import admin
from src.helpsys.models import HelpEntry

class HelpEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'topicname', 'staff_only')
    list_display_links = ('id', 'topicname')
    list_filter = ('staff_only',)
    search_fields = ['topicname', 'entrytext']
admin.site.register(HelpEntry, HelpEntryAdmin)