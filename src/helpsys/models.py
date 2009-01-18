"""
Models for the help system.
"""
from django.db import models
from django.contrib import admin
from src import ansi
from src.helpsys.managers.helpentry import HelpEntryManager

class HelpEntry(models.Model):
    """
    A generic help entry.
    """
    topicname = models.CharField(max_length=255)
    entrytext = models.TextField(blank=True, null=True)
    staff_only = models.BooleanField(default=0)
    
    objects = HelpEntryManager()
        
    class Meta:
        verbose_name_plural = "Help entries"
        ordering = ['topicname']
        
    def __str__(self):
        return self.topicname
        
    def get_topicname(self):
        """
        Returns the topic's name.
        """
        return self.topicname
    
    def get_entrytext_ingame(self):
        """
        Gets the entry text for in-game viewing.
        """
        return ansi.parse_ansi(self.entrytext)

class HelpEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'topicname', 'staff_only')
    list_display_links = ('id', 'topicname')
    list_filter = ('staff_only',)
    search_fields = ['entrytext']
admin.site.register(HelpEntry, HelpEntryAdmin)