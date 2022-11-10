"""
Views to manipulate help entries.

Multi entry object type supported added by DaveWithTheNiceHat 2021
    Pull Request #2429
"""
from django.conf import settings
from django.http import HttpResponseBadRequest
from django.utils.text import slugify
from django.views.generic import DetailView, ListView

from evennia.help.filehelp import FILE_HELP_ENTRIES
from evennia.help.models import HelpEntry
from evennia.utils.ansi import strip_ansi
from evennia.utils.utils import inherits_from

DEFAULT_HELP_CATEGORY = settings.DEFAULT_HELP_CATEGORY


def get_help_category(help_entry, slugify_cat=True):
    """Returns help category.

    Args:
        help_entry (HelpEntry, FileHelpEntry or Command): Help entry instance.
        slugify_cat (bool): If true the return string is slugified. Default is True.

    Notes:
        If an entry does not have a `help_category` attribute, DEFAULT_HELP_CATEGORY from the
        settings file is used.
        If the entry does not have attribute 'web_help_entries'. One is created with a slugified
        copy of the attribute help_category. This attribute is used for sorting the entries for the
        help index (ListView) page.

    Returns:
        help_category (str): The category for the help entry.
    """
    help_category = getattr(help_entry, "help_category", None)
    if not help_category:
        help_category = getattr(help_entry, "db_help_category", DEFAULT_HELP_CATEGORY)
    # if one does not exist, create a category for ease of use with web views html templates
    if not hasattr(help_entry, "web_help_category"):
        setattr(help_entry, "web_help_category", slugify(help_category))
    help_category = help_category.lower()
    return slugify(help_category) if slugify_cat else help_category


def get_help_topic(help_entry):
    """Get the topic of the help entry.

    Args:
        help_entry (HelpEntry, FileHelpEntry or Command): Help entry instance.

    Returns:
        help_topic (str): The topic of the help entry. Default is 'unknown_topic'.
    """
    help_topic = getattr(help_entry, "key", None)
    # if object has no key, assume it is a db help entry.
    if not help_topic:
        help_topic = getattr(help_entry, "db_key", "unknown_topic")
    # if one does not exist, create a key for ease of use with web views html templates
    if not hasattr(help_entry, "web_help_key"):
        setattr(help_entry, "web_help_key", slugify(help_topic))
    return help_topic.lower()


def can_read_topic(cmd_or_topic, account):
    """Check if an account or puppet has read access to a help entry.

    Args:
        cmd_or_topic (Command, HelpEntry or FileHelpEntry): The topic/command to test.
        account: the account or puppet checking for access.

    Returns:
        bool: If command can be viewed or not.

    Notes:
        This uses the 'read' lock. If no 'read' lock is defined, the topic is assumed readable
        by all.
        Even if this returns False, the entry will still be visible in the help index unless
        `can_list_topic` is also returning False.
    """
    if inherits_from(cmd_or_topic, "evennia.commands.command.Command"):
        return cmd_or_topic.auto_help and cmd_or_topic.access(account, "read", default=True)
    else:
        return cmd_or_topic.access(account, "read", default=True)


def collect_topics(account):
    """Collect help topics from all sources (cmd/db/file).

    Args:
        account (Character or Account): Account or Character to collect help topics from.

    Returns:
        cmd_help_topics (dict): contains Command instances.
        db_help_topics (dict): contains HelpEntry instances.
        file_help_topics (dict): contains FileHelpEntry instances
    """

    # collect commands of account and all puppets
    # skip a command if an entry is recorded with the same topics, category and help entry
    cmd_help_topics = []
    if not str(account) == "AnonymousUser":
        # create list of account and account's puppets
        puppets = account.db._playable_characters + [account]
        # add the account's and puppets' commands to cmd_help_topics list
        for puppet in puppets:
            for cmdset in puppet.cmdset.get():
                # removing doublets in cmdset, caused by cmdhandler
                # having to allow doublet commands to manage exits etc.
                cmdset.make_unique(puppet)
                # retrieve all available commands and database / file-help topics.
                # also check the 'cmd:' lock here
                for cmd in cmdset:
                    # skip the command if the puppet does not have access
                    if not cmd.access(puppet, "cmd"):
                        continue
                    # skip the command if the puppet does not have read access
                    if not can_read_topic(cmd, puppet):
                        continue
                    # skip the command if it's help entry already exists in the topic list
                    entry_exists = False
                    for verify_cmd in cmd_help_topics:
                        if (
                            verify_cmd.key
                            and cmd.key
                            and verify_cmd.help_category == cmd.help_category
                            and verify_cmd.__doc__ == cmd.__doc__
                        ):
                            entry_exists = True
                            break
                    if entry_exists:
                        continue
                    # add this command to the list
                    cmd_help_topics.append(cmd)

    # Verify account has read access to filehelp entries and gather them into a dictionary
    file_help_topics = {
        topic.key.lower().strip(): topic
        for topic in FILE_HELP_ENTRIES.all()
        if can_read_topic(topic, account)
    }

    # Verify account has read access to database entries and gather them into a dictionary
    db_help_topics = {
        topic.key.lower().strip(): topic
        for topic in HelpEntry.objects.all()
        if can_read_topic(topic, account)
    }

    # Collect commands into a dictionary, read access verified at puppet level
    cmd_help_topics = {
        cmd.auto_help_display_key if hasattr(cmd, "auto_help_display_key") else cmd.key: cmd
        for cmd in cmd_help_topics
    }

    return cmd_help_topics, db_help_topics, file_help_topics


class HelpMixin:
    """
    This is a "mixin", a modifier of sorts.

    Any view class with this in its inheritance list will be modified to work
    with HelpEntry objects instead of generic Objects or otherwise.

    """

    # -- Evennia constructs --
    page_title = "Help"

    def get_queryset(self):
        """
        Django hook; here we want to return a list of only those HelpEntries
        and other documentation that the current user is allowed to see.

        Returns:
            queryset (list): List of Help entries available to the user.

        """
        account = self.request.user

        # collect all help entries
        cmd_help_topics, db_help_topics, file_help_topics = collect_topics(account)

        # merge the entries
        file_db_help_topics = {**file_help_topics, **db_help_topics}
        all_topics = {**file_db_help_topics, **cmd_help_topics}
        all_entries = list(all_topics.values())

        # sort the entries
        all_entries.sort(key=get_help_topic)  # sort alphabetically
        all_entries.sort(key=get_help_category)  # group by categories

        return all_entries


class HelpListView(HelpMixin, ListView):
    """
    Returns a list of help entries that can be viewed by a user, authenticated
    or not.

    """

    # -- Django constructs --
    paginate_by = 500
    template_name = "website/help_list.html"

    # -- Evennia constructs --
    page_title = "Help Index"


class HelpDetailView(HelpMixin, DetailView):
    """
    Returns the detail page for a given help entry.

    """

    # -- Django constructs --
    # the html template to use when contructing the detail page for a help topic
    template_name = "website/help_detail.html"

    @property
    def page_title(self):
        # Makes sure the page has a sensible title.
        obj = self.get_object()
        topic = get_help_topic(obj)
        return f"{topic} detail"

    def get_context_data(self, **kwargs):
        """
        Adds navigational data to the template to let browsers go to the next
        or previous entry in the help list.

        Returns:
            context (dict): Django context object

        """
        context = super().get_context_data(**kwargs)

        # get a full query set
        full_set = self.get_queryset()

        # Get the object in question
        obj = self.get_object(full_set)

        # filter non related categories from the query set
        obj_category = get_help_category(obj)
        category_set = []
        for entry in full_set:
            entry_category = get_help_category(entry)
            if entry_category.lower() == obj_category.lower():
                category_set.append(entry)
        context["topic_list"] = category_set

        # Find the index position of the given obj in the category set
        objs = list(category_set)
        for i, x in enumerate(objs):
            if obj is x:
                break

        # Find the previous and next topics, if either exist
        try:
            assert i + 1 <= len(objs) and objs[i + 1] is not obj
            context["topic_next"] = objs[i + 1]
        except:
            context["topic_next"] = None

        try:
            assert i - 1 >= 0 and objs[i - 1] is not obj
            context["topic_previous"] = objs[i - 1]
        except:
            context["topic_previous"] = None

        # Get the help entry text
        text = "Failed to find entry."
        if inherits_from(obj, "evennia.commands.command.Command"):
            text = obj.__doc__
        elif inherits_from(obj, "evennia.help.models.HelpEntry"):
            text = obj.db_entrytext
        elif inherits_from(obj, "evennia.help.filehelp.FileHelpEntry"):
            text = obj.entrytext
        text = strip_ansi(text)  # remove ansii markups
        context["entry_text"] = text.strip()

        return context

    def get_object(self, queryset=None):
        """
        Override of Django hook that retrieves an object by category and topic
        instead of pk and slug.

        Args:
            queryset (list): A list of help entry objects.

        Returns:
            entry (HelpEntry, FileHelpEntry or Command): HelpEntry requested in the URL.

        """

        if hasattr(self, "obj"):
            return getattr(self, "obj", None)

        # Get the queryset for the help entries the user can access
        if not queryset:
            queryset = self.get_queryset()

        # get the category and topic requested
        category = slugify(self.kwargs.get("category", ""))
        topic = slugify(self.kwargs.get("topic", ""))

        # Find the object in the queryset
        obj = None
        for entry in queryset:
            # continue to next entry if the topics do not match
            entry_topic = get_help_topic(entry)
            if not slugify(entry_topic) == topic:
                continue
            # if the category also matches, object requested is found
            entry_category = get_help_category(entry)
            if slugify(entry_category) == category:
                obj = entry
                break

        # Check if this object was requested in a valid manner
        if not obj:
            return HttpResponseBadRequest(f"No ({category}/{topic})s found matching the query.")
        else:
            # cache the object if one was found
            self.obj = obj

        return obj
