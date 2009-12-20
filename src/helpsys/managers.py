"""
Custom manager for HelpEntry objects.
"""
from django.db import models

class HelpEntryManager(models.Manager):
    """
    This implements different ways to search for help entries.
    """
    def find_topicmatch(self, pobject, topicstr, exact=False):
        """
        Searches for matching topics based on player's input.
        """        
        if topicstr.isdigit():
            return self.filter(id=topicstr)
        t_query = self.filter(topicname__iexact=topicstr)
        if not t_query and not exact: 
            t_query = self.filter(topicname__istartswith=topicstr)            
        # check permissions 
        t_query = [topic for topic in t_query if topic.can_view(pobject)]
        return t_query

    def find_apropos(self, pobject, topicstr):
        """
        Do a very loose search, returning all help entries containing
        the search criterion in their titles. 
        """
        topics = self.filter(topicname__icontains=topicstr)
        return [topic for topic in topics if topic.can_view(pobject)]
        
    def find_topicsuggestions(self, pobject, topicstr):
        """
        Do a fuzzy match, preferably within the category of the
        current topic.
        """                
        topics = self.find_apropos(pobject, topicstr)       
        # we need to clean away the given help entry.
        return [topic for topic in topics
                if topic.topicname.lower() != topicstr.lower()]
                    
    def find_topics_with_category(self, pobject, category):
        """
        Search topics having a particular category
        """
        t_query = self.filter(category__iexact=category)
        return [topic for topic in t_query if topic.can_view(pobject)]

