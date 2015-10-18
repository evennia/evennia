"""
The help command. The basic idea is that help texts for commands
are best written by those that write the commands - the admins. So
command-help is all auto-loaded and searched from the current command
set. The normal, database-tied help system is used for collaborative
creation of other help topics such as RP help or game-world aides.
"""

from django.conf import settings
from collections import defaultdict
from evennia.utils.utils import fill, dedent
from evennia.commands.command import Command
from evennia.help.models import HelpEntry
from evennia.utils import create
from evennia.utils.utils import string_suggestions
from evennia.commands.default.muxcommand import MuxCommand

# limit symbol import for API
__all__ = ("CmdHelp", "CmdSetHelp")
_DEFAULT_WIDTH = settings.CLIENT_DEFAULT_WIDTH
_SEP = "{C" + "-" * _DEFAULT_WIDTH + "{n"


def format_help_entry(title, help_text, aliases=None, suggested=None):
    """
    This visually formats the help entry.
    """
    string = _SEP + "\n"
    if title:
        string += "{CHelp for {w%s{n" % title
    if aliases:
        string += " {C(aliases: %s{C){n" % ("{C,{n ".join("{w%s{n" % ali for ali in aliases))
    if help_text:
        string += "\n%s" % dedent(help_text.rstrip())
    if suggested:
        string += "\n\n{CSuggested:{n "
        string += "%s" % fill("{C,{n ".join("{w%s{n" % sug for sug in suggested))
    string.strip()
    string += "\n" + _SEP
    return string


def format_help_list(hdict_cmds, hdict_db):
    """
    Output a category-ordered list. The input are the
    pre-loaded help files for commands and database-helpfiles
    resectively.
    """
    string = ""
    if hdict_cmds and any(hdict_cmds.values()):
        string += "\n" + _SEP + "\n   {CCommand help entries{n\n" + _SEP
        for category in sorted(hdict_cmds.keys()):
            string += "\n  {w%s{n:\n" % (str(category).title())
            string += "{G" + fill(", ".join(sorted(hdict_cmds[category]))) + "{n"
    if hdict_db and any(hdict_db.values()):
        string += "\n\n" + _SEP + "\n\r  {COther help entries{n\n" + _SEP
        for category in sorted(hdict_db.keys()):
            string += "\n\r  {w%s{n:\n" % (str(category).title())
            string += "{G" + fill(", ".join(sorted([str(topic) for topic in hdict_db[category]]))) + "{n"
    return string


class CmdHelp(Command):
    """
    view help or a list of topics

    Usage:
      help <topic or command>
      help list
      help all

    This will search for help on commands and other
    topics related to the game.
    """
    key = "help"
    locks = "cmd:all()"
    arg_regex = r"\s|$"

    # this is a special cmdhandler flag that makes the cmdhandler also pack
    # the current cmdset with the call to self.func().
    return_cmdset = True

    def parse(self):
        """
        input is a string containing the command or topic to match.
        """
        self.original_args = self.args.strip()
        self.args = self.args.strip().lower()

    def func(self):
        """
        Run the dynamic help entry creator.
        """
        query, cmdset = self.args, self.cmdset
        caller = self.caller

        suggestion_cutoff = 0.6
        suggestion_maxnum = 5

        if not query:
            query = "all"

        # removing doublets in cmdset, caused by cmdhandler
        # having to allow doublet commands to manage exits etc.
        cmdset.make_unique(caller)

        # retrieve all available commands and database topics
        all_cmds = [cmd for cmd in cmdset if cmd.auto_help and cmd.access(caller)]
        all_topics = [topic for topic in HelpEntry.objects.all() if topic.access(caller, 'view', default=True)]
        all_categories = list(set([cmd.help_category.lower() for cmd in all_cmds] + [topic.help_category.lower() for topic in all_topics]))

        if query in ("list", "all"):
            # we want to list all available help entries, grouped by category
            hdict_cmd = defaultdict(list)
            hdict_topic = defaultdict(list)
            # create the dictionaries {category:[topic, topic ...]} required by format_help_list
            [hdict_cmd[cmd.help_category].append(cmd.key) for cmd in all_cmds]
            [hdict_topic[topic.help_category].append(topic.key) for topic in all_topics]
            # report back
            self.msg(format_help_list(hdict_cmd, hdict_topic))
            return

        # Try to access a particular command

        # build vocabulary of suggestions and rate them by string similarity.
        vocabulary = [cmd.key for cmd in all_cmds if cmd] + [topic.key for topic in all_topics] + all_categories
        [vocabulary.extend(cmd.aliases) for cmd in all_cmds]
        suggestions = [sugg for sugg in string_suggestions(query, set(vocabulary), cutoff=suggestion_cutoff, maxnum=suggestion_maxnum)
                       if sugg != query]
        if not suggestions:
            suggestions = [sugg for sugg in vocabulary if sugg != query and sugg.startswith(query)]

        # try an exact command auto-help match
        match = [cmd for cmd in all_cmds if cmd == query]
        if len(match) == 1:
            self.msg(format_help_entry(match[0].key,
                     match[0].__doc__,
                     aliases=match[0].aliases,
                     suggested=suggestions))
            return

        # try an exact database help entry match
        match = list(HelpEntry.objects.find_topicmatch(query, exact=True))
        if len(match) == 1:
            self.msg(format_help_entry(match[0].key,
                     match[0].entrytext,
                     suggested=suggestions))
            return

        # try to see if a category name was entered
        if query in all_categories:
            self.msg(format_help_list({query:[cmd.key for cmd in all_cmds if cmd.help_category==query]},
                                        {query:[topic.key for topic in all_topics if topic.help_category==query]}))
            return

        # no exact matches found. Just give suggestions.
        self.msg(format_help_entry("", "No help entry found for '%s'" % query, None, suggested=suggestions))


class CmdSetHelp(MuxCommand):
    """
    edit the help database

    Usage:
      @help[/switches] <topic>[,category[,locks]] = <text>

    Switches:
      add    - add or replace a new topic with text.
      append - add text to the end of topic with a newline between.
      merge  - As append, but don't add a newline between the old
               text and the appended text.
      delete - remove help topic.
      force  - (used with add) create help topic also if the topic
               already exists.

    Examples:
      @sethelp/add throw = This throws something at ...
      @sethelp/append pickpocketing,Thievery = This steals ...
      @sethelp/append pickpocketing, ,attr(is_thief) = This steals ...

    This command manipulates the help database. A help entry can be created,
    appended/merged to and deleted. If you don't assign a category, the
    "General" category will be used. If no lockstring is specified, default
    is to let everyone read the help file.

    """
    key = "@help"
    aliases = "@sethelp"
    locks = "cmd:perm(PlayerHelpers)"
    help_category = "Building"

    def func(self):
        "Implement the function"

        switches = self.switches
        lhslist = self.lhslist

        if not self.args:
            self.msg("Usage: @sethelp/[add|del|append|merge] <topic>[,category[,locks,..] = <text>")
            return

        topicstr = ""
        category = "General"
        lockstring = "view:all()"
        try:
            topicstr = lhslist[0]
            category = lhslist[1]
            lockstring = ",".join(lhslist[2:])
        except Exception:
            pass

        if not topicstr:
            self.msg("You have to define a topic!")
            return
        # check if we have an old entry with the same name
        try:
            old_entry = HelpEntry.objects.get(db_key__iexact=topicstr)
        except Exception:
            old_entry = None

        if 'append' in switches or "merge" in switches:
            # merge/append operations
            if not old_entry:
                self.msg("Could not find topic '%s'. You must give an exact name." % topicstr)
                return
            if not self.rhs:
                self.msg("You must supply text to append/merge.")
                return
            if 'merge' in switches:
                old_entry.entrytext += " " + self.rhs
            else:
                old_entry.entrytext += "\n%s" % self.rhs
            self.msg("Entry updated:\n%s" % old_entry.entrytext)
            return
        if 'delete' in switches or 'del' in switches:
            # delete the help entry
            if not old_entry:
                self.msg("Could not find topic '%s'" % topicstr)
                return
            old_entry.delete()
            self.msg("Deleted help entry '%s'." % topicstr)
            return

        # at this point it means we want to add a new help entry.
        if not self.rhs:
            self.msg("You must supply a help text to add.")
            return
        if old_entry:
            if 'for' in switches or 'force' in switches:
                # overwrite old entry
                old_entry.key = topicstr
                old_entry.entrytext = self.rhs
                old_entry.help_category = category
                old_entry.locks.clear()
                old_entry.locks.add(lockstring)
                old_entry.save()
                self.msg("Overwrote the old topic '%s' with a new one." % topicstr)
            else:
                self.msg("Topic '%s' already exists. Use /force to overwrite or /append or /merge to add text to it." % topicstr)
        else:
            # no old entry. Create a new one.
            new_entry = create.create_help_entry(topicstr,
                                                 self.rhs, category, lockstring)
            if new_entry:
                self.msg("Topic '%s' was successfully created." % topicstr)
            else:
                self.msg("Error when creating topic '%s'! Contact an admin." % topicstr)
