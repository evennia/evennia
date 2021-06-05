"""
Views to manipulate help entries.

Multi entry object type supported added by DaveWithTheNiceHat 2021
    Pull Request #2429
"""
from django.utils.text import slugify
from django.conf import settings
from evennia.utils.utils import inherits_from
from django.views.generic import ListView, DetailView
from django.http import HttpResponseBadRequest
from evennia.help.models import HelpEntry
from evennia.help.filehelp import FILE_HELP_ENTRIES
from .mixins import TypeclassMixin
from evennia.utils.logger import log_info
from evennia.utils.ansi import strip_ansi

DEFAULT_HELP_CATEGORY = settings.DEFAULT_HELP_CATEGORY


def get_help_category(help_entry, slugify_cat=True):
    """Returns help category.

    Args:
        help_entry (HelpEntry, FileHelpEntry or Command): Help entry instance.
        slugify_cat (bool): If true the return string is slugified. Default is True.

    Notes:
        If the entry does not have attribute 'web_help_entries'. One is created with
        a slugified copy of the attribute help_category.
        This attribute is used for sorting the entries for the help index (ListView) page.

    Returns:
        help_category (str): The category for the help entry.
    """
    if not hasattr(help_entry, 'web_help_category'):
        setattr(help_entry, 'web_help_category', slugify(help_entry.help_category))
    return slugify(help_entry.help_category) if slugify_cat else help_entry.help_category


def get_help_topic(help_entry):
    topic = getattr(help_entry, 'key', False)
    if not topic:
        getattr(help_entry, 'db_key', False)
    # log_info(f'get_help_topic returning: {topic}')
    return topic


def can_read_topic(cmd_or_topic, caller):
        """
        Helper method. If this return True, the given help topic
        be viewable in the help listing. Note that even if this returns False,
        the entry will still be visible in the help index unless `should_list_topic`
        is also returning False.
        Args:
            cmd_or_topic (Command, HelpEntry or FileHelpEntry): The topic/command to test.
            caller: the caller checking for access.
        Returns:
            bool: If command can be viewed or not.
        Notes:
            This uses the 'read' lock. If no 'read' lock is defined, the topic is assumed readable
            by all.
        """
        if inherits_from(cmd_or_topic, "evennia.commands.command.Command"):
            return cmd_or_topic.auto_help and cmd_or_topic.access(caller, 'read', default=True)
        else:
            return cmd_or_topic.access(caller, 'read', default=True)


def can_list_topic(cmd_or_topic, caller):
    """
    Should the specified command appear in the help table?
    This method only checks whether a specified command should appear in the table of
    topics/commands.  The command can be used by the caller (see the 'should_show_help' method)
    and the command will still be available, for instance, if a character type 'help name of the
    command'.  However, if you return False, the specified command will not appear in the table.
    This is sometimes useful to "hide" commands in the table, but still access them through the
    help system.
    Args:
        cmd_or_topic (Command, HelpEntry or FileHelpEntry): The topic/command to test.
        caller: the caller checking for access.
    Returns:
        bool: If command should be listed or not.
    Notes:
        By default, the 'view' lock will be checked, and if no such lock is defined, the 'read'
        lock will be used. If neither lock is defined, the help entry is assumed to be
        accessible to all.
    """
    has_view = (
        "view:" in cmd_or_topic.locks
        if inherits_from(cmd_or_topic, "evennia.commands.command.Command")
        else cmd_or_topic.locks.get("view")
    )

    if has_view:
        return cmd_or_topic.access(caller, 'view', default=True)
    else:
        # no explicit 'view' lock - use the 'read' lock
        return cmd_or_topic.access(caller, 'read', default=True)


def collect_topics(account, mode='list'):
        """
        Collect help topics from all sources (cmd/db/file).
        Args:
            account (Object or Account): The user of the Command.
            mode (str): One of 'list' or 'query', where the first means we are collecting to view
                the help index and the second because of wanting to search for a specific help
                entry/cmd to read. This determines which access should be checked.
        Returns:
            tuple: A tuple of three dicts containing the different types of help entries
            in the order cmd-help, db-help, file-help:
                `({key: cmd,...}, {key: dbentry,...}, {key: fileentry,...}`
        """
        # start with cmd-help
        cmd_help_topics = []
        if not str(account) == 'AnonymousUser':
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
                        if not cmd.access(puppet, 'cmd'):
                            continue
                        # skip the command if it's help entry already exists in the topic list
                        entry_exists = False
                        for verify_cmd in cmd_help_topics:
                            if verify_cmd.key and cmd.key and \
                               verify_cmd.help_category == cmd.help_category and \
                               verify_cmd.__doc__ == cmd.__doc__:
                                entry_exists = True
                                break
                        if entry_exists:
                            continue
                        # add this command to the list
                        cmd_help_topics.append(cmd)
        # get all file-based help entries, checking perms
        file_help_topics = {
            topic.key.lower().strip(): topic
            for topic in FILE_HELP_ENTRIES.all()
        }
        # get db-based help entries, checking perms
        db_help_topics = {
            topic.key.lower().strip(): topic
            for topic in HelpEntry.objects.all()
        }
        if mode == 'list':
            # check the view lock for all help entries/commands and determine key
            cmd_help_topics = {
                cmd.auto_help_display_key
                if hasattr(cmd, "auto_help_display_key") else cmd.key: cmd
                for cmd in cmd_help_topics if can_list_topic(cmd, account)}
            db_help_topics = {
                key: entry for key, entry in db_help_topics.items()
                if can_list_topic(entry, account)
            }
            file_help_topics = {
                key: entry for key, entry in file_help_topics.items()
                if can_list_topic(entry, account)}
        else:
            # query
            cmd_help_topics = {
                cmd.auto_help_display_key
                if hasattr(cmd, "auto_help_display_key") else cmd.key: cmd
                for cmd in cmd_help_topics if can_read_topic(cmd, account)}
            db_help_topics = {
                key: entry for key, entry in db_help_topics.items()
                if can_read_topic(entry, account)
            }
            file_help_topics = {
                key: entry for key, entry in file_help_topics.items()
                if can_read_topic(entry, account)}

        return cmd_help_topics, db_help_topics, file_help_topics


class HelpMixin(TypeclassMixin):
    """
    This is a "mixin", a modifier of sorts.

    Any view class with this in its inheritance list will be modified to work
    with HelpEntry objects instead of generic Objects or otherwise.

    """

    # -- Django constructs --
    model = HelpEntry

    # -- Evennia constructs --
    page_title = "Help"

    def get_queryset(self):
        """
        Django hook; here we want to return a list of only those HelpEntries
        and other documentation that the current user is allowed to see.

        Returns:
            queryset (QuerySet): List of Help entries available to the user.

        """
        log_info('get_queryset')
        account = self.request.user
        # collect all help entries
        cmd_help_topics, db_help_topics, file_help_topics = collect_topics(account, mode='query')
        # merge the entries
        file_db_help_topics = {**file_help_topics, **db_help_topics}
        all_topics = {**file_db_help_topics, **cmd_help_topics}
        all_entries = list(all_topics.values())
        # sort the entries
        all_entries = sorted(all_entries, key=get_help_topic)  # sort alphabetically
        all_entries.sort(key=get_help_category)  # group by categories
        log_info('get_queryset success')
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
    template_name = "website/help_detail.html"

    @property
    def page_title(self):
        # Makes sure the page has a sensible title.
        # return "%s Detail" % self.typeclass._meta.verbose_name.title()
        obj = self.get_object()
        topic = get_help_topic(obj)
        return f'{topic} detail'

    def get_context_data(self, **kwargs):
        """
        Adds navigational data to the template to let browsers go to the next
        or previous entry in the help list.

        Returns:
            context (dict): Django context object

        """
        log_info('get_context_data')
        context = super().get_context_data(**kwargs)

        # Get the object in question
        obj = self.get_object()

        # Get queryset and filter out non-related categories
        full_set = self.get_queryset()
        obj_category = get_help_category(obj)
        category_set = []
        for entry in full_set:
            entry_category = get_help_category(entry)
            if entry_category.lower() == obj_category.lower():
                category_set.append(entry)
        context["topic_list"] = category_set

        # log_info(f'category_set: {category_set}')

        # Find the index position of the given obj in the queryset
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

        # Format the help entry using HTML instead of newlines
        text = 'Failed to find entry.'
        if inherits_from(obj, "evennia.commands.command.Command"):
            text = obj.__doc__
        elif inherits_from(obj, "evennia.help.models.HelpEntry"):
            text = obj.db_entrytext
        elif inherits_from(obj, "evennia.help.filehelp.FileHelpEntry"):
            text = obj.entrytext
        text = strip_ansi(text)  # remove ansii markups
        context["entry_text"] = text.strip()
        log_info('get_context_data success')
        return context

    def get_object(self, queryset=None):
        """
        Override of Django hook that retrieves an object by category and topic
        instead of pk and slug.

        Returns:
            entry (HelpEntry): HelpEntry requested in the URL.

        """
        log_info('get_object start')
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
            if not entry_topic.lower() == topic.replace('-', ' '):
                continue
            # if the category also matches, object requested is found
            entry_category = get_help_category(entry)
            if entry_category.lower() == category.replace('-', ' '):
                obj = entry
                break

        # Check if this object was requested in a valid manner
        if not obj:
            return HttpResponseBadRequest(
                f"No ({category}/{topic})s found matching the query"
            )

        log_info(f'get_obj returning {obj}')
        return obj
