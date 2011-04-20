"""
Custom manager for HelpEntry objects.
"""
from django.db import models
from src.utils import logger, utils

class HelpEntryManager(models.Manager):
    """
    This implements different ways to search for help entries.
    """
    def find_topicmatch(self, topicstr, exact=False):
        """
        Searches for matching topics based on player's input.
        """        
        if utils.dbref(topicstr):
            return self.filter(id=utils.dbref(topicstr))
        topics = self.filter(db_key__iexact=topicstr)
        if not topics and not exact: 
            topics = self.filter(db_key__istartswith=topicstr)            
            if not topics:
                topics = self.filter(db_key__icontains=topicstr)            
        return topics

    def find_apropos(self, topicstr):
        """
        Do a very loose search, returning all help entries containing
        the search criterion in their titles. 
        """
        return self.filter(db_key__icontains=topicstr)
        
    def find_topicsuggestions(self, topicstr):
        """
        Do a fuzzy match, preferably within the category of the
        current topic.
        """                
        topics = self.find_apropos(topicstr)       
        # we need to clean away the given help entry.
        return [topic for topic in topics
                if topic.key.lower() != topicstr.lower()]
                    
    def find_topics_with_category(self, help_category):
        """
        Search topics having a particular category
        """
        topics = self.filter(db_help_category__iexact=help_category)
        return topics

    def get_all_topics(self):
        """
        Return all topics.
        """
        return self.all()

    def get_all_categories(self, pobject):
        """
        Return all defined category names with at least one
        topic in them.
        """
        return list(set(topic.help_category for topic in self.all()))

    def all_to_category(self, default_category):
        """
        Shifts all help entries in database to default_category.
        This action cannot be reverted. It is used primarily by
        the engine when importing a default help database, making
        sure this ends up in one easily separated category. 
        """
        topics = self.all()
        for topic in topics:
            topic.help_category = default_category
            topic.save()
        string = "Help database moved to category %s" % default_category
        logger.log_infomsg(string)

    def search_help(self, ostring, help_category=None):
        """
        Retrieve a search entry object.

        ostring - the help topic to look for
        category - limit the search to a particular help topic
        """
        ostring = ostring.strip().lower() 
        help_entries = self.filter(db_topicstr=ostring)
        if help_category:
            help_entries.filter(db_help_category=help_category)
        return help_entries
