"""
Custom manager for HelpEntry objects.
"""
from django.db import IntegrityError

from evennia.server import signals
from evennia.typeclasses.managers import TypedObjectManager
from evennia.utils import logger, utils
from evennia.utils.utils import make_iter

__all__ = ("HelpEntryManager",)


class HelpEntryManager(TypedObjectManager):
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
        Searches for matching topics or aliases based on player's
        input.

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
        if not topics:
            topics = self.get_by_alias(topicstr)
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
        string = "Help database moved to category {default_category}".format(
            default_category=default_category
        )
        logger.log_info(string)

    def search_help(self, ostring, help_category=None):
        """
        Retrieve a search entry object.

        Args:
            ostring (str): The help topic to look for.
            category (str): Limit the search to a particular help topic

        Returns:
            Queryset: An iterable with 0, 1 or more matches.

        """
        ostring = ostring.strip().lower()
        if help_category:
            return self.filter(db_key__iexact=ostring, db_help_category__iexact=help_category)
        else:
            return self.filter(db_key__iexact=ostring)

    def create_help(self, key, entrytext, category="General", locks=None, aliases=None, tags=None):
        """
        Create a static help entry in the help database. Note that Command
        help entries are dynamic and directly taken from the __doc__
        entries of the command. The database-stored help entries are
        intended for more general help on the game, more extensive info,
        in-game setting information and so on.

        Args:
            key (str): The name of the help entry.
            entrytext (str): The body of te help entry
            category (str, optional): The help category of the entry.
            locks (str, optional): A lockstring to restrict access.
            aliases (list of str, optional): List of alternative (likely shorter) keynames.
            tags (lst, optional): List of tags or tuples `(tag, category)`.

        Returns:
            help (HelpEntry): A newly created help entry.

        """
        try:
            new_help = self.model()
            new_help.key = key
            new_help.entrytext = entrytext
            new_help.help_category = category
            if locks:
                new_help.locks.add(locks)
            if aliases:
                new_help.aliases.add(make_iter(aliases))
            if tags:
                new_help.tags.batch_add(*tags)
            new_help.save()
            return new_help
        except IntegrityError:
            string = "Could not add help entry: key '%s' already exists." % key
            logger.log_err(string)
            return None
        except Exception:
            logger.log_trace()
            return None

        signals.SIGNAL_HELPENTRY_POST_CREATE.send(sender=new_help)
