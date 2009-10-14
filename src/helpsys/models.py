"""
Models for the help system.
"""
from django.db import models
from django.conf import settings
from src import ansi
from src.helpsys.managers import HelpEntryManager

class HelpEntry(models.Model):
    """
    A generic help entry.
    """
    topicname = models.CharField(max_length=255, unique=True)
    category = models.CharField(max_length=255, default="General")
    canview = models.CharField(max_length=255, blank=True)
    entrytext = models.TextField(blank=True)
    
    #deprecated, only here to allow MUX helpfile load.
    staff_only = models.BooleanField(default=False) 
    
    objects = HelpEntryManager()
        
    class Meta:
        """
        Permissions here defines access to modifying help
        entries etc, not which entries can be viewed (that
        is controlled by the canview field). 
        """
        verbose_name_plural = "Help entries"
        ordering = ['topicname']
        permissions = settings.PERM_HELPSYS
        
    def __str__(self):
        return self.topicname
        
    def get_topicname(self):
        """
        Returns the topic's name.
        """
        return self.topicname

    def get_category(self):
        """
        Returns the category of this help entry.
        """
        return self.category
    
    def can_view(self, pobject):
        """
        Check if the pobject has the necessary permission/group
        to view this help entry. 
        """
        perm = self.canview.split(',')
        if not perm or (len(perm) == 1 and not perm[0]) or \
               pobject.has_perm("helpsys.admin_help"):
            return True
        return pobject.has_perm_list(perm)
                        
    def get_entrytext_ingame(self):
        """
        Gets the entry text for in-game viewing.
        """
        return ansi.parse_ansi(self.entrytext)
