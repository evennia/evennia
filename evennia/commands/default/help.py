"""
The help command. The basic idea is that help texts for commands
are best written by those that write the commands - the admins. So
command-help is all auto-loaded and searched from the current command
set. The normal, database-tied help system is used for collaborative
creation of other help topics such as RP help or game-world aides.

"""

import re
from django.conf import settings
from collections import defaultdict
from evennia.utils.utils import fill, dedent
from evennia.commands.command import Command
from evennia.help.models import HelpEntry
from evennia.utils import create, evmore
from evennia.utils.ansi import ANSIString
from evennia.utils.eveditor import EvEditor
from evennia.utils.utils import (
    string_suggestions,
    class_from_module,
    inherits_from,
    format_grid, pad
)

COMMAND_DEFAULT_CLASS = class_from_module(settings.COMMAND_DEFAULT_CLASS)
HELP_MORE = settings.HELP_MORE
CMD_IGNORE_PREFIXES = settings.CMD_IGNORE_PREFIXES

_RE_HELP_SUBTOPICS_START = re.compile(
    r"^\s*?#\s*?subtopics\s*?$", re.I + re.M)
_RE_HELP_SUBTOPIC_SPLIT = re.compile(r"^\s*?(\#{2,6}\s*?\w+?[a-z0-9 \-\?!,\.]*?)$", re.M + re.I)
_RE_HELP_SUBTOPIC_PARSE = re.compile(
    r"^(?P<nesting>\#{2,6})\s*?(?P<name>.*?)$", re.I + re.M)
MAX_SUBTOPIC_NESTING = 5


# limit symbol import for API
__all__ = ("CmdHelp", "CmdSetHelp")
_DEFAULT_WIDTH = settings.CLIENT_DEFAULT_WIDTH
_SEP = "|C" + "-" * _DEFAULT_WIDTH + "|n"

_LUNR = None
_LUNR_EXCEPTION = None


class HelpCategory:
    def __init__(self, key):
        self.key = key

    @property
    def search_index_entry(self):
        return {
            "key": str(self),
            "aliases": "",
            "category": self.key,
            "tags": "",
            "text": "",
        }

    def __str__(self):
        return f"Category: {self.key}"

    def __eq__(self, other):
        return str(self).lower() == str(other).lower()

    def __hash__(self):
        return id(self)


def help_search_with_index(query, candidate_entries, suggestion_maxnum=5):
    """
    Lunr-powered fast index search and suggestion wrapper
    """
    global _LUNR, _LUNR_EXCEPTION
    if not _LUNR:
        # we have to delay-load lunr because it messes with logging if it's imported
        # before twisted's logging has been set up
        from lunr import lunr as _LUNR
        from lunr.exceptions import QueryParseError as _LUNR_EXCEPTION

    indx = [cnd.search_index_entry for cnd in candidate_entries]
    mapping = {indx[ix]["key"]: cand for ix, cand in enumerate(candidate_entries)}

    search_index = _LUNR(
        ref="key",
        fields=[
            {"field_name": "key", "boost": 10},
            {"field_name": "aliases", "boost": 9},
            {"field_name": "category", "boost": 8},
            {"field_name": "tags", "boost": 5},
            {"field_name": "text", "boost": 1},
        ],
        documents=indx,
    )
    try:
        matches = search_index.search(query)[:suggestion_maxnum]
    except _LUNR_EXCEPTION:
        # this is a user-input problem
        matches = []

    # matches (objs), suggestions (strs)
    return (
        [mapping[match["ref"]] for match in matches],
        [str(match["ref"]) for match in matches],  # + f" (score {match['score']})")   # good debug
    )


def parse_entry_for_subcategories(entry):
    """
    Parse a command docstring for special sub-category blocks:

    Args:
        entry (str): A help entry to parse

    Returns:
        dict: The dict is a mapping that splits the entry into subcategories. This
            will always hold a key `None` for the main help entry and
            zero or more keys holding the subcategories. Each is itself
            a dict with a key `None` for the main text of that subcategory
            followed by any sub-sub-categories down to a max-depth of 5.

    Example:
    ::

        '''
        Main topic text

        # SUBTOPICS

        ## foo

        A subcategory of the main entry, accessible as `help topic foo`
        (or using /, like `help topic/foo`)

        ## bar

        Another subcategory, accessed as `help topic bar`
        (or `help topic/bar`)

        ### moo

        A subcategory of bar, accessed as `help bar moo`
        (or `help bar/moo`)

        #### dum

        A subcategory of moo, accessed `help bar moo dum`
        (or `help bar/moo/dum`)

        '''

    This will result in this returned entry structure:
    ::

        {
           None: "Main topic text":
           "foo": {
                None: "main topic/foo text"
           },
           "bar": {
                None: "Main topic/bar text",
                "moo": {
                    None: "topic/bar/moo text"
                    "dum": {
                        None: "topic/bar/moo/dum text"
                    }
                }
           }
        }


    Apart from making
    sub-categories at the bottom of the entry.

    This will be applied both to command docstrings and database-based help
    entries.

    """
    topic, *subtopics = _RE_HELP_SUBTOPICS_START.split(entry, maxsplit=1)
    structure = {None: topic.strip()}

    if subtopics:
        subtopics = subtopics[0]
    else:
        return structure

    keypath = []
    current_nesting = 0
    subtopic = None

    # from evennia import set_trace;set_trace()
    for part in _RE_HELP_SUBTOPIC_SPLIT.split(subtopics.strip()):

        subtopic_match = _RE_HELP_SUBTOPIC_PARSE.match(part.strip())
        if subtopic_match:
            # a new sub(-sub..) category starts.
            mdict = subtopic_match.groupdict()
            subtopic = mdict['name'].lower().strip()
            new_nesting = len(mdict['nesting']) - 1

            if new_nesting > MAX_SUBTOPIC_NESTING:
                raise RuntimeError(
                    f"Can have max {MAX_SUBTOPIC_NESTING} levels of nested help subtopics.")

            nestdiff = new_nesting - current_nesting
            if nestdiff < 0:
                # jumping back up in nesting
                for _ in range(abs(nestdiff) + 1):
                    try:
                        keypath.pop()
                    except IndexError:
                        pass
            elif nestdiff == 0:
                # don't add a deeper nesting but replace the current
                try:
                    keypath.pop()
                except IndexError:
                    pass
            keypath.append(subtopic)
            current_nesting = new_nesting
        else:
            # an entry belonging to a subtopic - find the nested location
            dct = structure
            if not keypath and subtopic is not None:
                structure[subtopic] = dedent(part.strip())
            else:
                for key in keypath:
                    if key in dct:
                        dct = dct[key]
                    else:
                        dct[key] = {
                            None: dedent(part.strip())
                        }
    return structure


class CmdHelp(COMMAND_DEFAULT_CLASS):
    """
    View help or a list of topics

    Usage:
      help
      help <topic, command or category>
      help <topic> / <subtopic>
      help <topic> / <subtopic> / <subsubtopic> ...

    Use the help command alone to see an index of all help topics, organized by
    category. Some long topics may offer additional sub-topics.

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
    # 'HELP_MORE = False' in your settings/conf/settings.py
    help_more = HELP_MORE

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

    def msg_help(self, text):
        """
        messages text to the caller, adding an extra oob argument to indicate
        that this is a help command result and could be rendered in a separate
        help window
        """
        if type(self).help_more:
            usemore = True

            if self.session and self.session.protocol_key in ("websocket", "ajax/comet",):
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

    @staticmethod
    def format_help_entry(topic="", help_text="", aliases=None, suggested=None,
                          subtopics=None):
        """
        This visually formats the help entry.
        This method can be overriden to customize the way a help
        entry is displayed.

        Args:
            title (str): The title of the help entry.
            help_text (str): Text of the help entry.
            aliases (list): List of help-aliases (displayed in header).
            suggested (list): Strings suggested reading (based on title).
            subtopics (list): A list of strings - the subcategories available
                for this entry.

        Returns the formatted string, ready to be sent.

        """
        start = f"{_SEP}\n"

        title = f"|CHelp for |w{topic}|n" if topic else ""

        if aliases:
            aliases = (
                " |C(aliases: {}|C)|n".format("|C,|n ".join(f"|w{ali}|n" for ali in aliases))
            )
        else:
            aliases = ''

        help_text = f"\n\n{dedent('    ' + help_text.strip())}\n" if help_text else ""

        if subtopics:
            subtopics = (
                "\n|CSubtopics:|n\n  {}".format(
                    "\n  ".join(f"|w{topic}/{subtop}|n" for subtop in subtopics))
            )
        else:
            subtopics = ''

        if suggested:
            suggested = (
                "\n\n|CSuggested other topics:|n\n{}".format(
                    fill("|C,|n ".join(f"|w{sug}|n" for sug in suggested), indent=2))
            )
        else:
            suggested = ''

        end = f"\n{_SEP}"

        return "".join((start, title, aliases, help_text, subtopics, suggested, end))

    def format_help_index(self, cmd_help_dict=None, db_help_dict=None):
        """
        Output a category-ordered g for displaying the main help, grouped by
        category.

        Args:
            cmd_help_dict (dict): A dict `{"category": [topic, topic, ...]}` for
                command-based help.
            db_help_dict (dict): A dict `{"category": [topic, topic], ...]}` for
                database-based help.

        Returns:
            str: The help index organized into a grid.

        The input are the
        pre-loaded help files for commands and database-helpfiles
        respectively.  You can override this method to return a
        custom display of the list of commands and topics.

        """
        def _group_by_category(help_dict):
            grid = []
            verbatim_elements = []

            if len(help_dict) == 1:
                # don't list categories if there is only one
                for category in help_dict:
                    entries = sorted(set(help_dict.get(category, [])))
                    grid.extend(entries)
            else:
                # list the categories
                for category in sorted(set(list(help_dict.keys()))):
                    category_str = f"-- {category.title()} "
                    grid.append(
                        ANSIString(
                            self.index_category_clr + category_str
                            + "-" * (width - len(category_str))
                            + self.index_topic_clr
                        )
                    )
                    verbatim_elements.append(len(grid) - 1)

                    entries = sorted(set(help_dict.get(category, [])))
                    grid.extend(entries)

            return grid, verbatim_elements

        help_index = ""
        width = self.client_width()
        grid = []
        verbatim_elements = []

        # get the command-help entries by-category
        sep1 = (self.index_type_separator_clr
                + pad("Commands", width=width, fillchar='-')
                + self.index_topic_clr)
        grid, verbatim_elements = _group_by_category(cmd_help_dict)
        gridrows = format_grid(grid, width, sep="  ", verbatim_elements=verbatim_elements)
        cmd_grid = ANSIString("\n").join(gridrows) if gridrows else ""

        # get db-based help entries by-category
        sep2 = (self.index_type_separator_clr
                + pad("Game & World", width=width, fillchar='-')
                + self.index_topic_clr)
        grid, verbatim_elements = _group_by_category(db_help_dict)
        gridrows = format_grid(grid, width, sep="  ", verbatim_elements=verbatim_elements)
        db_grid = ANSIString("\n").join(gridrows) if gridrows else ""

        # only show the main separators if there are actually both cmd and db-based help
        if cmd_grid and db_grid:
            help_index = f"{sep1}\n{cmd_grid}\n{sep2}\n{db_grid}"
        else:
            help_index = f"{cmd_grid}{db_grid}"

        return help_index

    def check_show_help(self, cmd, caller):
        """
        Helper method. If this return True, the given cmd
        auto-help will be viewable in the help listing.
        Override this to easily select what is shown to
        the account. Note that only commands available
        in the caller's merged cmdset are available.

        Args:
            cmd (Command): Command class from the merged cmdset
            caller (Character, Account or Session): The current caller
                executing the help command.

        """
        # return only those with auto_help set and passing the cmd: lock
        return cmd.auto_help and cmd.access(caller)

    def should_list_cmd(self, cmd, caller):
        """
        Should the specified command appear in the help table?

        This method only checks whether a specified command should
        appear in the table of topics/commands.  The command can be
        used by the caller (see the 'check_show_help' method) and
        the command will still be available, for instance, if a
        character type 'help name of the command'.  However, if
        you return False, the specified command will not appear in
        the table.  This is sometimes useful to "hide" commands in
        the table, but still access them through the help system.

        Args:
            cmd: the command to be tested.
            caller: the caller of the help system.

        Return:
            True: the command should appear in the table.
            False: the command shouldn't appear in the table.

        """
        return True

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
            self.subtopics = [part.strip().lower()
                              for part in self.args.split(self.subtopic_separator_char)]
            self.topic = self.subtopics.pop(0)
        else:
            self.topic = ""
            self.subtopics = []

    def func(self):
        """
        Run the dynamic help entry creator.
        """
        caller = self.caller
        query, subtopics, cmdset = self.topic, self.subtopics, self.cmdset
        suggestion_cutoff = self.suggestion_cutoff
        suggestion_maxnum = self.suggestion_maxnum

        # removing doublets in cmdset, caused by cmdhandler
        # having to allow doublet commands to manage exits etc.
        cmdset.make_unique(caller)

        # retrieve all available commands and database topics
        all_cmds = [cmd for cmd in cmdset if self.check_show_help(cmd, caller)]
        all_db_topics = [
            topic for topic in HelpEntry.objects.all() if topic.access(caller, "view", default=True)
        ]
        all_categories = list(set(
            [HelpCategory(cmd.help_category) for cmd in all_cmds]
                + [HelpCategory(topic.help_category) for topic in all_db_topics]
            )
        )

        if not query:
            # list all available help entries, grouped by category. We want to
            # build dictionaries {category: [topic, topic, ...], ...}
            cmd_help_dict = defaultdict(list)
            db_help_dict = defaultdict(list)

            # Filter commands that should be reached by the help
            # system, but not be displayed in the table, or be displayed differently.
            for cmd in all_cmds:
                if self.should_list_cmd(cmd, caller):
                    key = (cmd.auto_help_display_key
                           if hasattr(cmd, "auto_help_display_key") else cmd.key)
                    cmd_help_dict[cmd.help_category].append(key)

            for db_topic in all_db_topics:
                db_help_dict[db_topic.help_category].append(db_topic.key)

            output = self.format_help_index(cmd_help_dict, db_help_dict)
            self.msg_help(output)

            return

        # We have a query - try to find a specific topic/category using the
        # Lunr search engine

        # all available options
        entries = [cmd for cmd in all_cmds if cmd] + list(HelpEntry.objects.all()) + all_categories
        match, suggestions = None, None

        for match_query in [f"{query}~1", f"{query}*"]:
            # We first do an exact word-match followed by a start-by query
            # the return of this will either be a HelpCategory, a Command or a HelpEntry.
            matches, suggestions = help_search_with_index(
                match_query, entries, suggestion_maxnum=self.suggestion_maxnum
            )
            if matches:
                match = matches[0]
                break

        if not match:
            # no exact matches found. Just give suggestions.
            output = self.format_help_entry(
                topic="",
                help_text=f"No help entry found for '{query}'",
                suggested=suggestions
            )
            self.msg_help(output)
            return

        if isinstance(match, HelpCategory):
            # no subtopics for categories - these are just lists of topics
            output = self.format_help_index(
                {
                    match.key: [
                        cmd.key
                        for cmd in all_cmds
                        if match.key.lower() == cmd.help_category
                    ]
                },
                {
                    match.key: [
                        topic.key
                        for topic in all_db_topics
                        if match.key.lower() == topic.help_category
                    ]
                },
            )
            self.msg_help(output)
            return

        if inherits_from(match, "evennia.commands.command.Command"):
            # a command match
            topic = match.key
            help_text = match.get_help(caller, cmdset)
            aliases = match.aliases
            suggested=suggestions[1:]
        else:
            # a database match
            topic = match.key
            help_text = match.entrytext
            aliases = match.aliases.all()
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
                            subtopics=subtopic_index
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

        output = self.format_help_entry(
            topic=topic,
            help_text=help_text,
            aliases=aliases if not subtopics else None,
            subtopics=subtopic_index
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


class CmdSetHelp(COMMAND_DEFAULT_CLASS):
    """
    Edit the help database.

    Usage:
      help[/switches] <topic>[[;alias;alias][,category[,locks]] [= <text>]

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

    If not assigning a category, the "General" category will be used. If no
    lockstring is specified, everyone will be able to read the help entry.
    Sub-topics are embedded in the help text.

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
    switch_options = ("edit", "replace", "append", "extend", "delete")
    locks = "cmd:perm(Helper)"
    help_category = "Building"

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
        try:
            for querystr in topicstrlist:
                old_entry = HelpEntry.objects.find_topicmatch(querystr)  # also search by alias
                if old_entry:
                    old_entry = list(old_entry)[0]
                    break
            category = lhslist[1] if nlist > 1 else old_entry.help_category
            lockstring = ",".join(lhslist[2:]) if nlist > 2 else old_entry.locks.get()
        except Exception:
            old_entry = None
            category = lhslist[1] if nlist > 1 else "General"
            lockstring = ",".join(lhslist[2:]) if nlist > 2 else "view:all()"
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
                    topicstr, self.rhs, category=category, locks=lockstring, aliases=aliases,
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
                self.msg("Could not find topic '%s'. You must give an exact name." % topicstr)
                return
            if not self.rhs:
                self.msg("You must supply text to append/merge.")
                return
            if "merge" in switches:
                old_entry.entrytext += " " + self.rhs
            else:
                old_entry.entrytext += "\n%s" % self.rhs
            old_entry.aliases.add(aliases)
            self.msg("Entry updated:\n%s%s" % (old_entry.entrytext, aliastxt))
            return
        if "delete" in switches or "del" in switches:
            # delete the help entry
            if not old_entry:
                self.msg("Could not find topic '%s'%s." % (topicstr, aliastxt))
                return
            old_entry.delete()
            self.msg("Deleted help entry '%s'%s." % (topicstr, aliastxt))
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
                self.msg("Overwrote the old topic '%s'%s." % (topicstr, aliastxt))
            else:
                self.msg(
                    "Topic '%s'%s already exists. Use /replace to overwrite "
                    "or /append or /merge to add text to it." % (topicstr, aliastxt)
                )
        else:
            # no old entry. Create a new one.
            new_entry = create.create_help_entry(
                topicstr, self.rhs, category=category, locks=lockstring, aliases=aliases
            )
            if new_entry:
                self.msg("Topic '%s'%s was successfully created." % (topicstr, aliastxt))
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
                self.msg(
                    "Error when creating topic '%s'%s! Contact an admin." % (topicstr, aliastxt)
                )
