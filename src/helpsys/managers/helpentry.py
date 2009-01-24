"""
Custom manager for HelpEntry objects.
"""
from django.db import models

class HelpEntryManager(models.Manager):
    def find_topicmatch(self, pobject, topicstr):
        """
        Searches for matching topics based on player's input.
        """
        is_staff = pobject.is_staff()
        
        if topicstr.isdigit():
            t_query = self.filter(id=topicstr)
        else:
            exact_match = self.filter(topicname__iexact=topicstr)
            if exact_match:
                t_query = exact_match
            else:
                t_query = self.filter(topicname__istartswith=topicstr)
        
        if not is_staff:
            return t_query.exclude(staff_only=1)
            
        return t_query
        
    def find_topicsuggestions(self, pobject, topicstr):
        """
        Do a fuzzier "contains" match.
        """
        is_staff = pobject.is_staff()
        t_query = self.filter(topicname__icontains=topicstr)
        
        if not is_staff:
            return t_query.exclude(staff_only=1)
            
        return t_query

