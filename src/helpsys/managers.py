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
        
    def find_topicsuggestions(self, pobject, topicstr):
        """
        Do a fuzzy match, preferably within the category of the
        current topic.
        """                
        basetopic = self.filter(topicname__iexact=topicstr)
        if not basetopic:
            # this topic does not exist; just reply partial
            # matches to the string
            topics = self.filter(topicname__icontains=topicstr)                    
            return [topic for topic in topics if topic.can_view(pobject)]

        # we know that the topic exists, try to find similar ones within
        # its category.
        basetopic = basetopic[0]
        category = basetopic.category
        topics = []

        #remove the @
        crop = topicstr.lstrip('@')
        
        # first we filter for matches with the full name 
        topics = self.filter(category__iexact=category).filter(topicname__icontains=crop)
        if len(crop) > 4:
            # next search with a cropped version of the command.
            ttemp = self.filter(category__iexact=category).filter(topicname__icontains=crop[:4])
            ttemp = [topic for topic in ttemp if topic not in topics]
            topics = list(topics) + list(ttemp)
        # we need to clean away the given help entry.
        return [topic for topic in topics if topic.topicname.lower() != topicstr.lower()]
                    
    def find_topics_with_category(self, pobject, category):
        """
        Search topics having a particular category
        """
        t_query = self.filter(category__iexact=category)
        return [topic for topic in t_query if topic.can_view(pobject)]
