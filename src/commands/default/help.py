"""
The help command. The basic idea is that help texts for commands
are best written by those that write the commands - the admins. So
command-help is all auto-loaded and searched from the current command
set. The normal, database-tied help system is used for collaborative
creation of other help topics such as RP help or game-world aides.
"""
 
from src.utils.utils import fill, dedent
from src.commands.command import Command
from src.help.models import HelpEntry
from src.utils import create 
from src.commands.default.muxcommand import MuxCommand

LIST_ARGS = ("list", "all")
SEP = "{C" + "-"*78 + "{n"
 
def format_help_entry(title, help_text, aliases=None, suggested=None):
    """
    This visually formats the help entry.
    """            
    string = SEP + "\n"
    if title: 
        string += "{CHelp topic for {w%s{n" % (title.capitalize()) 
    if aliases:
        string += " {C(aliases: {w%s{n{C){n" % (", ".join(aliases))
    if help_text:
        string += "\n%s" % dedent(help_text.rstrip())
    if suggested:
        string += "\n\n{CSuggested:{n "
        string += "{w%s{n" % fill(", ".join(suggested))    
    string.strip()
    string += "\n" + SEP    
    return string 

def format_help_list(hdict_cmds, hdict_db):
    """
    Output a category-ordered list. The input are the 
    pre-loaded help files for commands and database-helpfiles 
    resectively.
    """    
    string = ""
    if hdict_cmds and hdict_cmds.values():
        string += "\n" + SEP + "\n   {CCommand help entries{n\n" + SEP
        for category in sorted(hdict_cmds.keys()):
            string += "\n  {w%s{n:\n" % (str(category).capitalize()) 
            string += "{G" + fill(", ".join(sorted(hdict_cmds[category]))) + "{n"
    if hdict_db and hdict_db.values():
        string += "\n\n" + SEP + "\n\r  {COther help entries{n\n" + SEP 
        for category in sorted(hdict_db.keys()):
            string += "\n\r  {w%s{n:\n" % (str(category).capitalize()) 
            string += "{G" + fill(", ".join(sorted([str(topic) for topic in hdict_db[category]]))) + "{n" 
    return string 

class CmdHelp(Command):
    """
    The main help command

    Usage:
      help <topic or command>
      help list
      help all

    This will search for help on commands and other
    topics related to the game. 
    """
    key = "help"
    locks = "cmd:all()"

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

        if not query:
            query = "all"

        # removing doublets in cmdset, caused by cmdhandler
        # having to allow doublet commands to manage exits etc.
        cmdset.make_unique(caller)
        
        # Listing all help entries
        
        if query in LIST_ARGS:
            # we want to list all available help entries, grouped by category.
            hdict_cmd = {}
            for cmd in (cmd for cmd in cmdset if cmd.auto_help and not cmd.is_exit 
                        and not cmd.key.startswith('__') and cmd.access(caller)):
                try:
                    hdict_cmd[cmd.help_category].append(cmd.key)
                except KeyError:
                    hdict_cmd[cmd.help_category] = [cmd.key]                    
            hdict_db = {}
            for topic in (topic for topic in HelpEntry.objects.get_all_topics()
                          if topic.access(caller, 'view', default=True)):
                try:
                    hdict_db[topic.help_category].append(topic.key)                    
                except KeyError:
                    hdict_db[topic.help_category] = [topic.key]
            help_entry = format_help_list(hdict_cmd, hdict_db)
            caller.msg(help_entry)
            return 
            
        # Look for a particular help entry
        
        # Cmd auto-help dynamic entries 
        cmdmatches = [cmd for cmd in cmdset if query in cmd and cmd.auto_help and cmd.access(caller)]
        if len(cmdmatches) > 1:
            # multiple matches. Try to limit it down to exact match
            cmdmatches = [cmd for cmd in cmdmatches if cmd == query] or cmdmatches
                
        # Help-database static entries
        dbmatches = [topic for topic in
                     HelpEntry.objects.find_topicmatch(query, exact=False)
                     if topic.access(caller, 'view', default=True)]
        if len(dbmatches) > 1:
            # try to get unique match
            dbmatches = [topic for topic in HelpEntry.objects.find_topicmatch(query, exact=True)
                         if topic.access(caller, 'view', default=True)] or dbmatches

        # Handle result 
        if (not cmdmatches) and (not dbmatches):
            # no normal match. Check if this is a category match instead
            categ_cmdmatches = [cmd.key for cmd in cmdset if query == cmd.help_category and cmd.access(caller)]
            categ_dbmatches = [topic.key for topic in HelpEntry.objects.find_topics_with_category(query)
                               if topic.access(caller, 'view', default=True)]
            cmddict = None
            dbdict = None
    
            if categ_cmdmatches:
                cmddict = {query:categ_cmdmatches}
            if categ_dbmatches:                
                dbdict = {query:categ_dbmatches}            
            if cmddict or dbdict:
                help_entry = format_help_list(cmddict, dbdict)                                              
            else:
                help_entry = "No help entry found for '%s'" % self.original_args

        elif len(cmdmatches) == 1:
            # we matched against a unique command name or alias. Show its help entry.
            suggested = []
            if dbmatches:
                suggested = [entry.key for entry in dbmatches]
            cmd = cmdmatches[0]
            help_entry = format_help_entry(cmd.key, cmd.__doc__,
                                           aliases=cmd.aliases,
                                           suggested=suggested)
        elif len(dbmatches) == 1:
            # matched against a database entry
            entry = dbmatches[0]
            help_entry = format_help_entry(entry.key, entry.entrytext)
        else:
            # multiple matches of either type
            cmdalts = [cmd.key for cmd in cmdmatches]
            dbalts = [entry.key for entry in dbmatches]
            helptext = "Multiple help entries match your search ..."
            help_entry = format_help_entry("", helptext, None, cmdalts + dbalts)

        # send result to user
        caller.msg(help_entry)

class CmdSetHelp(MuxCommand):
    """
    @help - edit the help database

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
      @sethelp/append pickpocketing,Thievery,is_thief, is_staff) = This steals ...
      @sethelp/append pickpocketing, ,is_thief, is_staff) = This steals ...
      
    """
    key = "@help"
    aliases = "@sethelp"
    locks = "cmd:perm(PlayerHelpers)"
    help_category = "Building"
    
    def func(self):
        "Implement the function"
        
        caller = self.caller        
        switches = self.switches
        lhslist = self.lhslist
        rhs = self.rhs

        if not self.args:
            caller.msg("Usage: @sethelp/[add|del|append|merge] <topic>[,category[,locks,..] = <text>]")
            return     

        topicstr = ""
        category = ""
        lockstring = ""
        try:
            topicstr = lhslist[0]
            category = lhslist[1]
            lockstring = ",".join(lhslist[2:])
        except Exception:
            pass
        if not topicstr:
            caller.msg("You have to define a topic!")
            return         
        string = ""
        #print topicstr, category, lockstring

        if switches and switches[0] in ('append', 'app','merge'):
            # add text to the end of a help topic        
            # find the topic to append to
            old_entry = HelpEntry.objects.filter(db_key__iexact=topicstr)
            if not old_entry:
                string = "Could not find topic '%s'. You must give an exact name." % topicstr
            else:
                old_entry = old_entry[0]
                entrytext = old_entry.entrytext
                if switches[0] == 'merge':
                    old_entry.entrytext = "%s %s" % (entrytext, self.rhs)
                    string = "Added the new text right after the old one (merge)."
                else: 
                    old_entry.entrytext = "%s\n\n%s" % (entrytext, self.rhs)
                    string = "Added the new text as a new paragraph after the old one (append)"
                old_entry.save()

        elif switches and switches[0] in ('delete','del'):
            #delete a help entry
            old_entry = HelpEntry.objects.filter(db_key__iexact=topicstr)           
            if not old_entry:
                string = "Could not find topic '%s'." % topicstr
            else:
                old_entry[0].delete()
                string = "Deleted the help entry '%s'." % topicstr

        else:
            # add a new help entry. 
            force_create = ('for' in switches) or ('force' in switches)
            old_entry = None 
            try:
                old_entry = HelpEntry.objects.get(key=topicstr)
            except Exception:
                pass
            if old_entry: 
                if force_create:
                    old_entry.key = topicstr
                    old_entry.entrytext = self.rhs
                    old_entry.help_category = category
                    old_entry.locks.clear()
                    old_entry.locks.add(lockstring)
                    old_entry.save()
                    string = "Overwrote the old topic '%s' with a new one." % topicstr
                else:
                    string = "Topic '%s' already exists. Use /force to overwrite it." % topicstr
            else:
                # no old entry. Create a new one.
                new_entry = create.create_help_entry(topicstr, 
                                                     rhs, category, lockstring)

                if new_entry:
                    string = "Topic '%s' was successfully created." % topicstr
                else:
                    string = "Error when creating topic '%s'! Maybe it already exists?" % topicstr                

        # give feedback
        caller.msg(string)
