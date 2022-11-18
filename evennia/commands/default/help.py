"""
The help command. The basic idea is that help texts for commands are best
written by those that write the commands - the developers. So command-help is
all auto-loaded and searched from the current command set. The normal,
database-tied help system is used for collaborative creation of other help
topics such as RP help or game-world aides. Help entries can also be created
outside the game in modules given by ``settings.FILE_HELP_ENTRY_MODULES``.

"""

from collections import defaultdict
from dataclasses import dataclass
from itertools import chain

from django.conf import settings

from evennia.help.filehelp import FILE_HELP_ENTRIES
from evennia.help.models import HelpEntry
from evennia.help.utils import help_search_with_index, parse_entry_for_subcategories
from evennia.utils import create, evmore
from evennia.utils.ansi import ANSIString
from evennia.utils.eveditor import EvEditor
from evennia.utils.utils import (
    class_from_module,
    dedent,
    format_grid,
    inherits_from,
    pad,
)

CMD_IGNORE_PREFIXES = settings.CMD_IGNORE_PREFIXES
COMMAND_DEFAULT_CLASS = class_from_module(settings.COMMAND_DEFAULT_CLASS)
HELP_MORE_ENABLED = settings.HELP_MORE_ENABLED
DEFAULT_HELP_CATEGORY = settings.DEFAULT_HELP_CATEGORY
HELP_CLICKABLE_TOPICS = settings.HELP_CLICKABLE_TOPICS

# limit symbol import for API
__all__ = ("CmdHelp", "CmdSetHelp")


@dataclass
class HelpCategory:
    """
    Mock 'help entry' to search categories with the same code.

    """

    key: str

    @property
    def search_index_entry(self):
        return {
            "key": self.key,
            "aliases": "",
            "category": self.key,
            "no_prefix": "",
            "tags": "",
            "text": "",
        }

    def __hash__(self):
        return hash(id(self))


class CmdHelp(COMMAND_DEFAULT_CLASS):
    """
    Get help.

    Usage:
      help
      help <topic, command or category>
      help <topic>/<subtopic>
      help <topic>/<subtopic>/<subsubtopic> ...

    Use the 'help' command alone to see an index of all help topics, organized
    by category. Some big topics may offer additional sub-topics.

    """

    key = "help"
    aliases = ["?"]
    locks = "cmd:all()"
    arg_regex = r"\s|$"

    # this is a special cmdhandler flag that makes the cmdhandler also pack
    # the current cmdset with the call to self.func().
    return_cmdset = True

    # Help messages are wrapped in an EvMore call (unless using the webclient
    # with separate help popups) If you want to avoid this, simply add
    # 'HELP_MORE_ENABLED = False' in your settings/conf/settings.py
    help_more = HELP_MORE_ENABLED

    # colors for the help index
    index_type_separator_clr = "|w"
    index_category_clr = "|W"
    index_topic_clr = "|G"

    # suggestion cutoff, between 0 and 1 (1 => perfect match)
    suggestion_cutoff = 0.6

    # number of suggestions (set to 0 to remove suggestions from help)
    suggestion_maxnum = 5

    # separator between subtopics:
    subtopic_separator_char = r"/"

    # should topics disply their help entry when clicked
    clickable_topics = HELP_CLICKABLE_TOPICS

    def msg_help(self, text):
        """
        messages text to the caller, adding an extra oob argument to indicate
        that this is a help command result and could be rendered in a separate
        help window
        """
        if type(self).help_more:
            usemore = True

            if self.session and self.session.protocol_key in (
                "websocket",
                "ajax/comet",
            ):
                try:
                    options = self.account.db._saved_webclient_options
                    if options and options["helppopup"]:
                        usemore = False
                except KeyError:
                    pass

            if usemore:
                evmore.msg(self.caller, text, session=self.session)
                return

        self.msg(text=(text, {"type": "help"}))

    def format_help_entry(
        self,
        topic="",
        help_text="",
        aliases=None,
        suggested=None,
        subtopics=None,
        click_topics=True,
    ):
        """This visually formats the help entry.
        This method can be overridden to customize the way a help
        entry is displayed.

        Args:
            title (str, optional): The title of the help entry.
            help_text (str, optional): Text of the help entry.
            aliases (list, optional): List of help-aliases (displayed in header).
            suggested (list, optional): Strings suggested reading (based on title).
            subtopics (list, optional): A list of strings - the subcategories available
                for this entry.
            click_topics (bool, optional): Should help topics be clickable. Default is True.

        Returns:
            help_message (str): Help entry formated for console.

        """
        separator = "|C" + "-" * self.client_width() + "|n"
        start = f"{separator}\n"

        title = f"|CHelp for |w{topic}|n" if topic else "|rNo help found|n"

        if aliases:
            aliases = " |C(aliases: {}|C)|n".format("|C,|n ".join(f"|w{ali}|n" for ali in aliases))
        else:
            aliases = ""

        help_text = "\n" + dedent(help_text.strip("\n")) if help_text else ""

        if subtopics:
            if click_topics:
                subtopics = [
                    f"|lchelp {topic}/{subtop}|lt|w{topic}/{subtop}|n|le" for subtop in subtopics
                ]
            else:
                subtopics = [f"|w{topic}/{subtop}|n" for subtop in subtopics]
            subtopics = "\n|CSubtopics:|n\n  {}".format(
                "\n  ".join(
                    format_grid(
                        subtopics, width=self.client_width(), line_prefix=self.index_topic_clr
                    )
                )
            )
        else:
            subtopics = ""

        if suggested:
            suggested = sorted(suggested)
            if click_topics:
                suggested = [f"|lchelp {sug}|lt|w{sug}|n|le" for sug in suggested]
            else:
                suggested = [f"|w{sug}|n" for sug in suggested]
            suggested = "\n|COther topic suggestions:|n\n{}".format(
                "\n  ".join(
                    format_grid(
                        suggested, width=self.client_width(), line_prefix=self.index_topic_clr
                    )
                )
            )
        else:
            suggested = ""

        end = start

        partorder = (start, title + aliases, help_text, subtopics, suggested, end)

        return "\n".join(part.rstrip() for part in partorder if part)

    def format_help_index(
        self, cmd_help_dict=None, db_help_dict=None, title_lone_category=False, click_topics=True
    ):
        """Output a category-ordered g for displaying the main help, grouped by
        category.

        Args:
            cmd_help_dict (dict): A dict `{"category": [topic, topic, ...]}` for
                command-based help.
            db_help_dict (dict): A dict `{"category": [topic, topic], ...]}` for
                database-based help.
            title_lone_category (bool, optional): If a lone category should
                be titled with the category name or not. While pointless in a
                general index, the title should probably show when explicitly
                listing the category itself.
            click_topics (bool, optional): If help-topics are clickable or not
                (for webclient or telnet clients with MXP support).
        Returns:
            str: The help index organized into a grid.

        Notes:
            The input are the pre-loaded help files for commands and database-helpfiles
            respectively. You can override this method to return a custom display of the list of
            commands and topics.

        """

        def _group_by_category(help_dict):
            grid = []
            verbatim_elements = []

            if len(help_dict) == 1 and not title_lone_category:
                # don't list categories if there is only one
                for category in help_dict:
                    # gather and sort the entries from the help dictionary
                    entries = sorted(set(help_dict.get(category, [])))

                    # make the help topics clickable
                    if click_topics:
                        entries = [f"|lchelp {entry}|lt{entry}|le" for entry in entries]

                    # add the entries to the grid
                    grid.extend(entries)
            else:
                # list the categories
                for category in sorted(set(list(help_dict.keys()))):
                    category_str = f"-- {category.title()} "
                    grid.append(
                        ANSIString(
                            self.index_category_clr
                            + category_str
                            + "-" * (width - len(category_str))
                            + self.index_topic_clr
                        )
                    )
                    verbatim_elements.append(len(grid) - 1)

                    # gather and sort the entries from the help dictionary
                    entries = sorted(set(help_dict.get(category, [])))

                    # make the help topics clickable
                    if click_topics:
                        entries = [f"|lchelp {entry}|lt{entry}|le" for entry in entries]

                    # add the entries to the grid
                    grid.extend(entries)

            return grid, verbatim_elements

        help_index = ""
        width = self.client_width()
        grid = []
        verbatim_elements = []
        cmd_grid, db_grid = "", ""

        if any(cmd_help_dict.values()):
            # get the command-help entries by-category
            sep1 = (
                self.index_type_separator_clr
                + pad("Commands", width=width, fillchar="-")
                + self.index_topic_clr
            )
            grid, verbatim_elements = _group_by_category(cmd_help_dict)
            gridrows = format_grid(
                grid,
                width,
                sep="  ",
                verbatim_elements=verbatim_elements,
                line_prefix=self.index_topic_clr,
            )
            cmd_grid = ANSIString("\n").join(gridrows) if gridrows else ""

        if any(db_help_dict.values()):
            # get db-based help entries by-category
            sep2 = (
                self.index_type_separator_clr
                + pad("Game & World", width=width, fillchar="-")
                + self.index_topic_clr
            )
            grid, verbatim_elements = _group_by_category(db_help_dict)
            gridrows = format_grid(
                grid,
                width,
                sep="  ",
                verbatim_elements=verbatim_elements,
                line_prefix=self.index_topic_clr,
            )
            db_grid = ANSIString("\n").join(gridrows) if gridrows else ""

        # only show the main separators if there are actually both cmd and db-based help
        if cmd_grid and db_grid:
            help_index = f"{sep1}\n{cmd_grid}\n{sep2}\n{db_grid}"
        else:
            help_index = f"{cmd_grid}{db_grid}"

        return help_index

    def can_read_topic(self, cmd_or_topic, caller):
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
            return cmd_or_topic.auto_help and cmd_or_topic.access(caller, "read", default=True)
        else:
            return cmd_or_topic.access(caller, "read", default=True)

    def can_list_topic(self, cmd_or_topic, caller):
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
            The `.auto_help` propery is checked for commands. For all help entries,
            the 'view' lock will be checked, and if no such lock is defined, the 'read'
            lock will be used. If neither lock is defined, the help entry is assumed to be
            accessible to all.

        """
        if hasattr(cmd_or_topic, "auto_help") and not cmd_or_topic.auto_help:
            return False

        has_view = (
            "view:" in cmd_or_topic.locks
            if inherits_from(cmd_or_topic, "evennia.commands.command.Command")
            else cmd_or_topic.locks.get("view")
        )

        if has_view:
            return cmd_or_topic.access(caller, "view", default=True)
        else:
            # no explicit 'view' lock - use the 'read' lock
            return cmd_or_topic.access(caller, "read", default=True)

    def collect_topics(self, caller, mode="list"):
        """
        Collect help topics from all sources (cmd/db/file).

        Args:
            caller (Object or Account): The user of the Command.
            mode (str): One of 'list' or 'query', where the first means we are collecting to view
                the help index and the second because of wanting to search for a specific help
                entry/cmd to read. This determines which access should be checked.

        Returns:
            tuple: A tuple of three dicts containing the different types of help entries
            in the order cmd-help, db-help, file-help:
                `({key: cmd,...}, {key: dbentry,...}, {key: fileentry,...}`

        """
        # start with cmd-help
        cmdset = self.cmdset
        # removing doublets in cmdset, caused by cmdhandler
        # having to allow doublet commands to manage exits etc.
        cmdset.make_unique(caller)
        # retrieve all available commands and database / file-help topics.
        # also check the 'cmd:' lock here
        cmd_help_topics = [cmd for cmd in cmdset if cmd and cmd.access(caller, "cmd")]
        # get all file-based help entries, checking perms
        file_help_topics = {topic.key.lower().strip(): topic for topic in FILE_HELP_ENTRIES.all()}
        # get db-based help entries, checking perms
        db_help_topics = {topic.key.lower().strip(): topic for topic in HelpEntry.objects.all()}
        if mode == "list":
            # check the view lock for all help entries/commands and determine key
            cmd_help_topics = {
                cmd.auto_help_display_key if hasattr(cmd, "auto_help_display_key") else cmd.key: cmd
                for cmd in cmd_help_topics
                if self.can_list_topic(cmd, caller)
            }
            db_help_topics = {
                key: entry
                for key, entry in db_help_topics.items()
                if self.can_list_topic(entry, caller)
            }
            file_help_topics = {
                key: entry
                for key, entry in file_help_topics.items()
                if self.can_list_topic(entry, caller)
            }
        else:
            # query - check the read lock on entries
            cmd_help_topics = {
                cmd.auto_help_display_key if hasattr(cmd, "auto_help_display_key") else cmd.key: cmd
                for cmd in cmd_help_topics
                if self.can_read_topic(cmd, caller)
            }
            db_help_topics = {
                key: entry
                for key, entry in db_help_topics.items()
                if self.can_read_topic(entry, caller)
            }
            file_help_topics = {
                key: entry
                for key, entry in file_help_topics.items()
                if self.can_read_topic(entry, caller)
            }

        return cmd_help_topics, db_help_topics, file_help_topics

    def do_search(self, query, entries, search_fields=None):
        """
        Perform a help-query search, default using Lunr search engine.

        Args:
            query (str): The help entry to search for.
            entries (list): All possibilities. A mix of commands, HelpEntries and FileHelpEntries.
            search_fields (list): A list of dicts defining how Lunr will find the
                search data on the elements. If not given, will use a default.

        Returns:
            tuple: A tuple (match, suggestions).

        """
        if not search_fields:
            # lunr search fields/boosts
            search_fields = [
                {"field_name": "key", "boost": 10},
                {"field_name": "aliases", "boost": 9},
                {"field_name": "no_prefix", "boost": 8},
                {"field_name": "category", "boost": 7},
                {"field_name": "tags", "boost": 1},  # tags are not used by default
            ]
        match, suggestions = None, None
        for match_query in (query, f"{query}*"):
            # We first do an exact word-match followed by a start-by query. The
            # return of this will either be a HelpCategory, a Command or a
            # HelpEntry/FileHelpEntry.
            matches, suggestions = help_search_with_index(
                match_query, entries, suggestion_maxnum=self.suggestion_maxnum, fields=search_fields
            )
            if matches:
                match = matches[0]
                break
        return match, suggestions

    def parse(self):
        """
        input is a string containing the command or topic to match.

        The allowed syntax is
        ::

            help <topic>[/<subtopic>[/<subtopic>[/...]]]

        The database/command query is always for `<topic>`, and any subtopics
        is then parsed from there. If a `<topic>` has spaces in it, it is
        always matched before assuming the space begins a subtopic.

        """
        # parse the query

        if self.args:
            self.subtopics = [
                part.strip().lower() for part in self.args.split(self.subtopic_separator_char)
            ]
            self.topic = self.subtopics.pop(0)
        else:
            self.topic = ""
            self.subtopics = []

    def strip_cmd_prefix(self, key, all_keys):
        """
        Conditional strip of a command prefix, such as @ in @desc. By default
        this will be hidden unless there is a duplicate without the prefix
        in the full command set (such as @open and open).

        Args:
            key (str): Command key to analyze.
            all_cmds (list): All command-keys (and potentially aliases).

        Returns:
            str: Potentially modified key to use in help display.

        """
        if key and key[0] in CMD_IGNORE_PREFIXES and key[1:] not in all_keys:
            # filter out e.g. `@` prefixes from display if there is duplicate
            # with the prefix in the set (such as @open/open)
            return key[1:]
        return key

    def func(self):
        """
        Run the dynamic help entry creator.
        """
        caller = self.caller
        query, subtopics, cmdset = self.topic, self.subtopics, self.cmdset
        clickable_topics = self.clickable_topics

        if not query:
            # list all available help entries, grouped by category. We want to
            # build dictionaries {category: [topic, topic, ...], ...}

            cmd_help_topics, db_help_topics, file_help_topics = self.collect_topics(
                caller, mode="list"
            )

            # db-topics override file-based ones
            file_db_help_topics = {**file_help_topics, **db_help_topics}

            # group by category (cmds are listed separately)
            cmd_help_by_category = defaultdict(list)
            file_db_help_by_category = defaultdict(list)

            # get a collection of all keys + aliases to be able to strip prefixes like @
            key_and_aliases = set(chain(*(cmd._keyaliases for cmd in cmd_help_topics.values())))

            for key, cmd in cmd_help_topics.items():
                key = self.strip_cmd_prefix(key, key_and_aliases)
                cmd_help_by_category[cmd.help_category].append(key)
            for key, entry in file_db_help_topics.items():
                file_db_help_by_category[entry.help_category].append(key)

            # generate the index and display
            output = self.format_help_index(
                cmd_help_by_category, file_db_help_by_category, click_topics=clickable_topics
            )
            self.msg_help(output)

            return

        # search for a specific entry. We need to check for 'read' access here before
        # building the set of possibilities.
        cmd_help_topics, db_help_topics, file_help_topics = self.collect_topics(
            caller, mode="query"
        )

        # get a collection of all keys + aliases to be able to strip prefixes like @
        key_and_aliases = set(chain(*(cmd._keyaliases for cmd in cmd_help_topics.values())))

        # db-help topics takes priority over file-help
        file_db_help_topics = {**file_help_topics, **db_help_topics}

        # commands take priority over the other types
        all_topics = {**file_db_help_topics, **cmd_help_topics}

        # get all categories
        all_categories = list(
            set(HelpCategory(topic.help_category) for topic in all_topics.values())
        )

        # all available help options - will be searched in order. We also check # the
        # read-permission here.
        entries = list(all_topics.values()) + all_categories

        # lunr search fields/boosts
        match, suggestions = self.do_search(query, entries)

        if not match:
            # no topic matches found. Only give suggestions.
            help_text = f"There is no help topic matching '{query}'."

            if not suggestions:
                # we don't even have a good suggestion. Run a second search,
                # doing a full-text search in the actual texts of the help
                # entries

                search_fields = [
                    {"field_name": "text", "boost": 1},
                ]

                for match_query in [query, f"{query}*", f"*{query}"]:
                    _, suggestions = help_search_with_index(
                        match_query,
                        entries,
                        suggestion_maxnum=self.suggestion_maxnum,
                        fields=search_fields,
                    )
                    if suggestions:
                        help_text += (
                            "\n... But matches where found within the help "
                            "texts of the suggestions below."
                        )
                        suggestions = [
                            self.strip_cmd_prefix(sugg, key_and_aliases) for sugg in suggestions
                        ]
                        break

            output = self.format_help_entry(
                topic=None,  # this will give a no-match style title
                help_text=help_text,
                suggested=suggestions,
                click_topics=clickable_topics,
            )

            self.msg_help(output)
            return

        if isinstance(match, HelpCategory):
            # no subtopics for categories - these are just lists of topics
            category = match.key
            category_lower = category.lower()
            cmds_in_category = [
                key for key, cmd in cmd_help_topics.items() if category_lower == cmd.help_category
            ]
            topics_in_category = [
                key
                for key, topic in file_db_help_topics.items()
                if category_lower == topic.help_category
            ]
            output = self.format_help_index(
                {category: cmds_in_category},
                {category: topics_in_category},
                title_lone_category=True,
                click_topics=clickable_topics,
            )
            self.msg_help(output)
            return

        if inherits_from(match, "evennia.commands.command.Command"):
            # a command match
            topic = match.key
            help_text = match.get_help(caller, cmdset)
            aliases = match.aliases
            suggested = suggestions[1:]
        else:
            # a database (or file-help) match
            topic = match.key
            help_text = match.entrytext
            aliases = match.aliases if isinstance(match.aliases, list) else match.aliases.all()
            suggested = suggestions[1:]

        # parse for subtopics. The subtopic_map is a dict with the current topic/subtopic
        # text is stored under a `None` key and all other keys are subtopic titles pointing
        # to nested dicts.

        subtopic_map = parse_entry_for_subcategories(help_text)
        help_text = subtopic_map[None]
        subtopic_index = [subtopic for subtopic in subtopic_map if subtopic is not None]

        if subtopics:
            # if we asked for subtopics, parse the found topic_text to see if any match.
            # the subtopics is a list describing the path through the subtopic_map.

            for subtopic_query in subtopics:

                if subtopic_query not in subtopic_map:
                    # exact match failed. Try startswith-match
                    fuzzy_match = False
                    for key in subtopic_map:
                        if key and key.startswith(subtopic_query):
                            subtopic_query = key
                            fuzzy_match = True
                            break

                    if not fuzzy_match:
                        # startswith failed - try an 'in' match
                        for key in subtopic_map:
                            if key and subtopic_query in key:
                                subtopic_query = key
                                fuzzy_match = True
                                break

                    if not fuzzy_match:
                        # no match found - give up
                        checked_topic = topic + f"/{subtopic_query}"
                        output = self.format_help_entry(
                            topic=topic,
                            help_text=f"No help entry found for '{checked_topic}'",
                            subtopics=subtopic_index,
                            click_topics=clickable_topics,
                        )
                        self.msg_help(output)
                        return

                # if we get here we have an exact or fuzzy match

                subtopic_map = subtopic_map.pop(subtopic_query)
                subtopic_index = [subtopic for subtopic in subtopic_map if subtopic is not None]
                # keep stepping down into the tree, append path to show position
                topic = topic + f"/{subtopic_query}"

            # we reached the bottom of the topic tree
            help_text = subtopic_map[None]

        topic = self.strip_cmd_prefix(topic, key_and_aliases)
        if subtopics:
            aliases = None
        else:
            aliases = [self.strip_cmd_prefix(alias, key_and_aliases) for alias in aliases]
        suggested = [self.strip_cmd_prefix(sugg, key_and_aliases) for sugg in suggested]

        output = self.format_help_entry(
            topic=topic,
            help_text=help_text,
            aliases=aliases,
            subtopics=subtopic_index,
            suggested=suggested,
            click_topics=clickable_topics,
        )

        self.msg_help(output)


def _loadhelp(caller):
    entry = caller.db._editing_help
    if entry:
        return entry.entrytext
    else:
        return ""


def _savehelp(caller, buffer):
    entry = caller.db._editing_help
    caller.msg("Saved help entry.")
    if entry:
        entry.entrytext = buffer


def _quithelp(caller):
    caller.msg("Closing the editor.")
    del caller.db._editing_help


class CmdSetHelp(CmdHelp):
    """
    Edit the help database.

    Usage:
      sethelp[/switches] <topic>[[;alias;alias][,category[,locks]] [= <text>]

    Switches:
      edit - open a line editor to edit the topic's help text.
      replace - overwrite existing help topic.
      append - add text to the end of existing topic with a newline between.
      extend - as append, but don't add a newline.
      delete - remove help topic.

    Examples:
      sethelp lore = In the beginning was ...
      sethelp/append pickpocketing,Thievery = This steals ...
      sethelp/replace pickpocketing, ,attr(is_thief) = This steals ...
      sethelp/edit thievery

    If not assigning a category, the `settings.DEFAULT_HELP_CATEGORY` category
    will be used. If no lockstring is specified, everyone will be able to read
    the help entry.  Sub-topics are embedded in the help text.

    Note that this cannot modify command-help entries - these are modified
    in-code, outside the game.

    # SUBTOPICS

    ## Adding subtopics

    Subtopics helps to break up a long help entry into sub-sections. Users can
    access subtopics with |whelp topic/subtopic/...|n Subtopics are created and
    stored together with the main topic.

    To start adding subtopics, add the text '# SUBTOPICS' on a new line at the
    end of your help text. After this you can now add any number of subtopics,
    each starting with '## <subtopic-name>' on a line, followed by the
    help-text of that subtopic.
    Use '### <subsub-name>' to add a sub-subtopic and so on. Max depth is 5. A
    subtopic's title is case-insensitive and can consist of multiple words -
    the user will be able to enter a partial match to access it.

    For example:

    | Main help text for <topic>
    |
    | # SUBTOPICS
    |
    | ## about
    |
    | Text for the '<topic>/about' subtopic'
    |
    | ### more about-info
    |
    | Text for the '<topic>/about/more about-info sub-subtopic
    |
    | ## extra
    |
    | Text for the '<topic>/extra' subtopic

    """

    key = "sethelp"
    aliases = []
    switch_options = ("edit", "replace", "append", "extend", "delete")
    locks = "cmd:perm(Helper)"
    help_category = "Building"
    arg_regex = None

    def parse(self):
        """We want to use the default parser rather than the CmdHelp.parse"""
        return COMMAND_DEFAULT_CLASS.parse(self)

    def func(self):
        """Implement the function"""

        switches = self.switches
        lhslist = self.lhslist

        if not self.args:
            self.msg(
                "Usage: sethelp[/switches] <topic>[;alias;alias][,category[,locks,..] = <text>"
            )
            return

        nlist = len(lhslist)
        topicstr = lhslist[0] if nlist > 0 else ""
        if not topicstr:
            self.msg("You have to define a topic!")
            return
        topicstrlist = topicstr.split(";")
        topicstr, aliases = (
            topicstrlist[0],
            topicstrlist[1:] if len(topicstr) > 1 else [],
        )
        aliastxt = ("(aliases: %s)" % ", ".join(aliases)) if aliases else ""
        old_entry = None

        # check if we have an old entry with the same name

        cmd_help_topics, db_help_topics, file_help_topics = self.collect_topics(
            self.caller, mode="query"
        )
        # db-help topics takes priority over file-help
        file_db_help_topics = {**file_help_topics, **db_help_topics}
        # commands take priority over the other types
        all_topics = {**file_db_help_topics, **cmd_help_topics}
        # get all categories
        all_categories = list(
            set(HelpCategory(topic.help_category) for topic in all_topics.values())
        )
        # all available help options - will be searched in order. We also check # the
        # read-permission here.
        entries = list(all_topics.values()) + all_categories

        # default setup
        category = lhslist[1] if nlist > 1 else DEFAULT_HELP_CATEGORY
        lockstring = ",".join(lhslist[2:]) if nlist > 2 else "read:all()"

        # search for existing entries of this or other types
        old_entry = None
        for querystr in topicstrlist:
            match, _ = self.do_search(querystr, entries)
            if match:
                warning = None
                if isinstance(match, HelpCategory):
                    warning = (
                        f"'{querystr}' matches (or partially matches) the name of "
                        f"help-category '{match.key}'. If you continue, your help entry will "
                        "take precedence and the category (or part of its name) *may* not "
                        "be usable for grouping help entries anymore."
                    )
                elif inherits_from(match, "evennia.commands.command.Command"):
                    warning = (
                        f"'{querystr}' matches (or partially matches) the key/alias of "
                        f"Command '{match.key}'. Command-help take precedence over other "
                        "help entries so your help *may* be impossible to reach for those "
                        "with access to that command."
                    )
                elif inherits_from(match, "evennia.help.filehelp.FileHelpEntry"):
                    warning = (
                        f"'{querystr}' matches (or partially matches) the name/alias of the "
                        f"file-based help topic '{match.key}'. File-help entries cannot be "
                        "modified from in-game (they are files on-disk). If you continue, "
                        "your help entry may shadow the file-based one's name partly or "
                        "completely."
                    )
                if warning:
                    # show a warning for a clashing help-entry type. Even if user accepts this
                    # we don't break here since we may need to show warnings for other inputs.
                    # We don't count this as an old-entry hit because we can't edit these
                    # types of entries.
                    self.msg(f"|rWarning:\n|r{warning}|n")
                    repl = yield ("|wDo you still want to continue? Y/[N]?|n")
                    if repl.lower() not in ("y", "yes"):
                        self.msg("Aborted.")
                        return
                else:
                    # a db-based help entry - this is OK
                    old_entry = match
                    category = lhslist[1] if nlist > 1 else old_entry.help_category
                    lockstring = ",".join(lhslist[2:]) if nlist > 2 else old_entry.locks.get()
                    break

        category = category.lower()

        if "edit" in switches:
            # open the line editor to edit the helptext. No = is needed.
            if old_entry:
                topicstr = old_entry.key
                if self.rhs:
                    # we assume append here.
                    old_entry.entrytext += "\n%s" % self.rhs
                helpentry = old_entry
            else:
                helpentry = create.create_help_entry(
                    topicstr,
                    self.rhs,
                    category=category,
                    locks=lockstring,
                    aliases=aliases,
                )
            self.caller.db._editing_help = helpentry

            EvEditor(
                self.caller,
                loadfunc=_loadhelp,
                savefunc=_savehelp,
                quitfunc=_quithelp,
                key="topic {}".format(topicstr),
                persistent=True,
            )
            return

        if "append" in switches or "merge" in switches or "extend" in switches:
            # merge/append operations
            if not old_entry:
                self.msg(f"Could not find topic '{topicstr}'. You must give an exact name.")
                return
            if not self.rhs:
                self.msg("You must supply text to append/merge.")
                return
            if "merge" in switches:
                old_entry.entrytext += " " + self.rhs
            else:
                old_entry.entrytext += "\n%s" % self.rhs
            old_entry.aliases.add(aliases)
            self.msg(f"Entry updated:\n{old_entry.entrytext}{aliastxt}")
            return

        if "delete" in switches or "del" in switches:
            # delete the help entry
            if not old_entry:
                self.msg(f"Could not find topic '{topicstr}'{aliastxt}.")
                return
            old_entry.delete()
            self.msg(f"Deleted help entry '{topicstr}'{aliastxt}.")
            return

        # at this point it means we want to add a new help entry.
        if not self.rhs:
            self.msg("You must supply a help text to add.")
            return
        if old_entry:
            if "replace" in switches:
                # overwrite old entry
                old_entry.key = topicstr
                old_entry.entrytext = self.rhs
                old_entry.help_category = category
                old_entry.locks.clear()
                old_entry.locks.add(lockstring)
                old_entry.aliases.add(aliases)
                old_entry.save()
                self.msg(f"Overwrote the old topic '{topicstr}'{aliastxt}.")
            else:
                self.msg(
                    f"Topic '{topicstr}'{aliastxt} already exists. Use /edit to open in editor, or "
                    "/replace, /append and /merge to modify it directly."
                )
        else:
            # no old entry. Create a new one.
            new_entry = create.create_help_entry(
                topicstr, self.rhs, category=category, locks=lockstring, aliases=aliases
            )
            if new_entry:
                self.msg(f"Topic '{topicstr}'{aliastxt} was successfully created.")
                if "edit" in switches:
                    # open the line editor to edit the helptext
                    self.caller.db._editing_help = new_entry
                    EvEditor(
                        self.caller,
                        loadfunc=_loadhelp,
                        savefunc=_savehelp,
                        quitfunc=_quithelp,
                        key="topic {}".format(new_entry.key),
                        persistent=True,
                    )
                    return
            else:
                self.msg(f"Error when creating topic '{topicstr}'{aliastxt}! Contact an admin.")
