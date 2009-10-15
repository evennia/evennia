"""
Support functions for the help system.
Allows adding help to the data base from inside the mud as
well as creating auto-docs of commands based on their doc strings. 
The system supports help-markup for multiple help entries as well
as a dynamically updating help index. 
"""
import textwrap
from django.conf import settings
from src.helpsys.models import HelpEntry
from src import logger
from src import defines_global

                            
class EditHelp(object):
    """
    This sets up an object able to perform normal editing
    operations on the help database. 
    """
    def __init__(self, indent=4, width=70):
        """
        We check if auto-help is active or not and
        set some formatting options.         
        """
        self.indent = indent # indentation of help text
        self.width = width # width of help text
        
    def format_help_text(self, help_text):
        """
        This formats the help entry text for proper left-side indentation.

        The first line is adjusted to the proper indentation and the
        subsequent lines are then adjusted proportionally to the first;
        so indentation relative this first line remains intact. 
        """
        lines = help_text.expandtabs().splitlines()

        # strip empty lines above and below the text
        while True:
            if lines and not lines[0].strip():
                lines.pop(0)
            else:
                break 
        while True:
            if lines and not lines[-1].strip():
                lines.pop()
            else:
                break 
        if not lines:
            return ""
                
        # produce a list of the indentations of each line initially
        indentlist = [len(line) - len(line.lstrip()) for line in lines]
 
        # use the first line to set the shift
        lineshift = indentlist[0] - self.indent

        # shift everything to the left
        indentlist = [max(self.indent, indent-lineshift) for indent in indentlist]
        trimmed = []
        for il, line in enumerate(lines):
            indentstr = " " * indentlist[il]
            trimmed.append("%s%s" % (indentstr, line.strip()))        
        return "\n".join(trimmed)
    
    def parse_markup_header(self, subtopic_header):
        """
         The possible markup headers for splitting the help into sections are:
         [[TopicTitle]]
         [[TopicTitle,category]]
         [[TopicTitle(perm1,perm2)]]
         [[TopicTitle,category(perm1,perm2)]] 
        """
        subtitle = ""
        subcategory = ""
        subpermissions = ()    
        #identifying the header parts. The header can max have three parts:
        # topicname, category (perm1,perm2,...)            
        try:
            # find the permission tuple
            lindex = subtopic_header.index('(')
            rindex = subtopic_header.index(')')
            if lindex < rindex:
                permtuple = subtopic_header[lindex+1:rindex]
                subpermissions = tuple([p.strip()
                                        for p in permtuple.split(',')])
                subtopic_header = subtopic_header[:lindex]
        except ValueError:
            # no permission tuple found
            pass
        # see if we have a name, category pair.
        try:
            subtitle, subcategory = subtopic_header.split(',')
            subtitle, subcategory = subtitle.strip(), subcategory.strip()
        except ValueError:
            subtitle = subtopic_header.strip()
        # we are done, return a tuple with the results
        return ( subtitle, subcategory, subpermissions )

    def format_help_entry(self, helptopic, category, helptext, permissions=None):
        """
        helptopic (string) - name of the full help entry
        helptext (string) - the help entry (may contain sections)
        permissions (tuple) - tuple with permission/group names
                              defined for the entire help entry.
                              (markup permissions override those)        
        Handles help markup in order to split help into subsections.
       
        These markup markers will be assumed to start a new line, regardless
        of where they are located in the help entry. If no permission string 
        tuple and/or category is given, the overall permission/category of
        the entire help entry is used. 
        """
        # sanitize input
        topics = []
        if '[[' not in helptext:
            formatted_text = self.format_help_text(helptext)
            topics.append((helptopic, category,
                           formatted_text, permissions))     
            return topics 

        subtopics = helptext.split('[[')

        if subtopics[0]:
            # the very first entry (before any markup) is the normal
            # help entry for the helptopic at hand.
            formatted_text = self.format_help_text(subtopics[0])
            topics.append((helptopic, category, formatted_text, permissions))
            
        for subtopic in subtopics[1:]:
            # handle all extra topics designated with markup                    
            try:
                subtopic_header, subtopic_text = subtopic.split(']]', 1)
            except ValueError:
                # if we have no ending, the entry is malformed and
                # we ignore this entry (better than overwriting 
                # something in the database).
                logger.log_errmsg("Malformed help markup in %s: '%s'\n (missing end ']]' )" % \
                                  (helptopic, subtopic))
                continue 
            # parse and format the help entry parts
            subtopic_header = self.parse_markup_header(subtopic_header)
            if not subtopic_header[0]:
                # we require a topic title. 
                logger.log_errmsg("Malformed help markup in '%s': Missing title." % subtopic_header)
                return
            # parse the header and use defaults
            subtopic_name = subtopic_header[0]
            subtopic_category = subtopic_header[1]
            subtopic_text = self.format_help_text(subtopic_text)                              
            subtopic_permissions = subtopic_header[2]
            if not subtopic_category:
                # no category set; inherit from main topic
                subtopic_category = category
            if not subtopic_permissions:
                # no permissions set; inherit from main topic
                subtopic_permissions = permissions
                
            # We have a finished topic, add it to the list as a topic tuple.
            topics.append((subtopic_name, subtopic_category,
                           subtopic_text, subtopic_permissions))
        return topics
                
    def create_help(self, newtopic):
        """
        Add a help entry to the database, replace an old one if it exists.
        topic (tuple) - this is a formatted tuple of data as prepared
        by format_help_entry, on the form (title, category, text, (perm_tuple))               
        """        
        #sanity checks;
        topicname = newtopic[0]
        category = newtopic[1]
        entrytext = newtopic[2]        
        permissions = newtopic[3]

        if not (topicname or entrytext):
            # don't create anything if there we
            # are missing vital parts
            return
        if not category:
            # this will force the default
            category = "General"
        if permissions:
            # the permissions tuple might be mangled;
            # make sure we build a string properly.
            if type(permissions) != type(tuple()):
                permissions = "%s" % permissions
            else:
                permissions = ", ".join(permissions)
        else:
            permissions = ""

        # check if the help topic already exist.
        oldtopic = HelpEntry.objects.filter(topicname__iexact=newtopic[0])
        if oldtopic:
            #replace an old help file
            topic = oldtopic[0]        
            topic.category = category
            topic.entrytext = entrytext
            topic.canview = permissions
            topic.save()
        else:            
            #we have a new topic - create a new help object
            new_entry = HelpEntry(topicname=topicname,
                                  category=category,
                                  entrytext=entrytext,
                                  canview=permissions)
            new_entry.save()

    def add_help_auto(self, topicstr, category, entrytext, permissions=()):
        """
        This is used by the auto_help system to add help one or more
        help entries to the system. 
        """
        # sanity checks
        if permissions and type(permissions) != type(tuple()):
            string  = "Auto-Help: malformed perm_tuple %s: %s -> %s (fixed)" % \
                      (topicstr,permissions, (permissions,))
            logger.log_errmsg(string)            
            permissions = (permissions,)

        # identify markup and do nice formatting as well as eventual
        # related entries to the help entries.
        #logger.log_infomsg("auto-help in: %s %s %s %s" % (topicstr, category, entrytext, permissions))
        topics = self.format_help_entry(topicstr, category,
                                        entrytext, permissions)
        #logger.log_infomsg("auto-help: %s -> %s" % (topicstr,topics))
        # create the help entries:
        if topics: 
            for topic in topics:
                self.create_help(topic)

    def add_help_manual(self, pobject, topicstr, category,
                        entrytext, permissions=(), force=False):
        """
        This is used when a player wants to add a help entry to the database
        manually (most often from inside the game)        

        force - this is given by the player and forces an overwrite also if the
                entry already exists or there are multiple similar matches to
                the entry.
        """
        # permission check:
        if not (pobject.is_superuser() or pobject.has_perm("helpsys.add_help")):
            pobject.emit_to(defines_global.NOPERMS_MSG)
            return None 
        # do a more fuzzy search to warn in case in case we are misspelling. 
        topic = HelpEntry.objects.find_topicmatch(pobject, topicstr)
        if topic and not force:
            return topic                    
        self.add_help_auto(topicstr, category, entrytext, permissions)
        pobject.emit_to("Added/appended help topic '%s'." % topicstr)
        
    def del_help_auto(self, topicstr):
        """
        Delete a help entry from the data base. Automatic version.
        """
        topic = HelpEntry.objects.filter(topicname__iexact=topicstr)
        if topic:
            topic[0].delete()
        
    def del_help_manual(self, pobject, topicstr):
        """
        Deletes an entry from the database. Interactive version. 
        Note that it makes no sense to delete auto-added help entries this way since
        they will be re-added on the next @reload. This is mostly useful for cleaning
        the database from doublet or orphaned entries, or when auto-help is turned off. 
        """
        # find topic with permission checks
        if not (pobject.is_superuser() or pobject.has_perm("helpsys.del_help")):
            pobject.emit_to(defines_global.NOPERMS_MSG)
            return None 
        topic = HelpEntry.objects.find_topicmatch(pobject, topicstr)
        if not topic or len(topic) > 1:
            return topic            
        # we have an exact match. Delete topic.
        topic[0].delete()
        pobject.emit_to("Help entry '%s' deleted." % topicstr)

    def homogenize_database(self, category):
        """
        This sets the entire help database to one category.
        It can be used to mark an initially loaded help database
        in a particular category, for later filtering.

        In evennia dev version, this is done with MUX help database. 
        """
        entries = HelpEntry.objects.all()
        for entry in entries:
            entry.category = category
            entry.save()
        logger.log_infomsg("Help database homogenized to category %s" % category)

    def autoclean_database(self, topiclist):
        """
        This syncs the entire help database against a reference topic
        list, deleting non-used or duplicate help entries that can be
        the result of auto-help misspellings etc. 
        """
        pass

class ViewHelp(object): 
    """
    This class contains ways to view the
    help database in a dynamical fashion.
    """
    def __init__(self, indent=4, width=78, category_cols=4, entry_cols=6):
        """
        indent (int) - number of spaces to indent tables with
        width (int) - width of index tables
        category_cols (int) - number of collumns per row for
                              category tables
        entry_cols (int) - number of collumns per row for help entries
        """
        self.width = width
        self.indent = indent
        self.category_cols = category_cols 
        self.entry_cols = entry_cols
        self.show_related = settings.HELP_SHOW_RELATED
        
    def make_table(self, items, cols):
        """        
        This takes a list of string items and displays them in collumn order,
        (sorted horizontally-first), ie
        A A A A
        A B B B
        B B C C
        C C  
        cols is the number of collumns to format. 
        """
        items.sort()
        if not items or not cols:
            return []
        length = len(items)
        # split the list into sublists of length cols
        rows = [items[i:i+cols] for i in xrange(0, length, cols)]                
        # build the table 
        string = ""
        for row in rows:
            string += self.indent * " " + ",  ".join(row) + "\n"
        return string
            
    def index_full(self, pobject):
        """
        This lists all available topics in the help index,
        ordered after category.

        The MUX category is not shown, it is for development 
        reference only. 
        """
        entries = HelpEntry.objects.all()        

        categories = [e.category for e in entries if e.category != 'MUX']
        categories = list(set(categories)) # make list unique
        categories.sort()
        table = ""
        for category in categories:
            topics = [e.topicname.lower() for e in entries.filter(category__iexact=category)
                      if e.can_view(pobject)]

            # pretty-printing the list
            header = "--- Topics in category %s:" % category
            nl = self.width - len(header)
            if not topics:
                text = self.indent*" " + "[There are no topics relevant to you in this category.]\n\r"
            else:
                text = self.make_table(topics, self.entry_cols)
            table += "\r\n%s%s\n\r\n\r%s" % (header, "-"*nl, text)
        return table 
               
    def index_categories(self):
        """
        This lists all categories defined in the help index.
        """
        entries = HelpEntry.objects.all()        
        categories = [e.category for e in entries]
        categories = list(set(categories)) # make list unique
        return self.make_table(categories, self.category_cols)
    
    def index_category(self, pobject, category):
        """
        List the help entries within a certain category
        """        
        entries = HelpEntry.objects.find_topics_with_category(pobject, category)
        if not entries:
            return []
        # filter out those we can actually view
        helptopics = [e.topicname.lower() for e in entries if e.can_view(pobject)]
        if not helptopics: 
            # we don't have permission to view anything in this category
            return " [There are no topics relevant to you in this category.]\n\r"
        return self.make_table(helptopics, self.entry_cols)

    def suggest_help(self, pobject, topic):
        """
        This goes through the help database, searching for relatively
        close matches to this topic. If those are found, they are
        added as a nice footer to the end of the topic entry. 
        """                
        if not self.show_related:
            return None
        topicname = topic.topicname
        return HelpEntry.objects.find_topicsuggestions(pobject, topicname)

# Object instances 
edithelp = EditHelp(indent=3,
                width=80)
viewhelp = ViewHelp(indent=3,
                width=80,
                category_cols=4,
                entry_cols=4)
