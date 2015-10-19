"""
Custom manager for HelpEntry objects.
"""
from django.db import models
from evennia.utils import logger, utils
__all__ = ("HelpEntryManager",)


class HelpEntryManager(models.Manager):
    """
    This HelpEntryManager implements methods for searching
    and manipulating HelpEntries directly from the database.

    These methods will all return database objects
    (or QuerySets) directly.

    Evennia-specific:
    find_topicmatch
    find_apropos
    find_topicsuggestions
    find_topics_with_category
    all_to_category
    search_help (equivalent to evennia.search_helpentry)

    """
    def find_topicmatch(self, topicstr, exact=False):
        """
        Searches for matching topics based on player's input.

        Args:
            topcistr (str): Help topic to search for.
            exact (bool, optional): Require exact match
                (non-case-sensitive).  If `False` (default), match
                sub-parts of the string.

        Returns:
            matches (HelpEntries): Query results.

        """
        dbref = utils.dbref(topicstr)
        if dbref:
            return self.filter(id=dbref)
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

        Args:
            topicstr (str): Search criterion.

        Returns:
            matches (HelpEntries): Query results.

        """
        return self.filter(db_key__icontains=topicstr)

    def find_topicsuggestions(self, topicstr):
        """
        Do a fuzzy match, preferably within the category of the
        current topic.

        Args:
            topicstr (str): Search criterion.

        Returns:
            matches (Helpentries): Query results.

        """
        return self.filter(db_key__icontains=topicstr).exclude(db_key__iexact=topicstr)

    def find_topics_with_category(self, help_category):
        """
        Search topics having a particular category.

        Args:
            help_category (str): Category query criterion.

        Returns:
            matches (HelpEntries): Query results.

        """
        return self.filter(db_help_category__iexact=help_category)

    def get_all_topics(self):
        """
        Get all topics.

        Returns:
            all (HelpEntries): All topics.

        """
        return self.all()

    def get_all_categories(self):
        """
        Return all defined category names with at least one topic in
        them.

        Returns:
            matches (list): Unique list of category names across all
                topics.

        """
        return list(set(topic.help_category for topic in self.all()))

    def all_to_category(self, default_category):
        """
        Shifts all help entries in database to default_category.  This
        action cannot be reverted. It is used primarily by the engine
        when importing a default help database, making sure this ends
        up in one easily separated category.

        Args:
            default_category (str): Category to move entries to.

        """
        topics = self.all()
        for topic in topics:
            topic.help_category = default_category
            topic.save()
        string = "Help database moved to category %s" % default_category
        logger.log_info(string)

    def search_help(self, ostring, help_category=None):
        """
        Retrieve a search entry object.

        Args:
            ostring (str): The help topic to look for.
            category (str): Limit the search to a particular help topic

        """
        ostring = ostring.strip().lower()
        if help_category:
            return self.filter(db_key__iexact=ostring,
                               db_help_category__iexact=help_category)
        else:
            return self.filter(db_key__iexact=ostring)
