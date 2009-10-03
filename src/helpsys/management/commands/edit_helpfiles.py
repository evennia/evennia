"""
Support commands for a more advanced help system.
Allows adding help to the data base from inside the mud as
well as creating auto-docs of commands based on their doc strings. 
The system supports help-markup for multiple help entries as well
as a dynamically updating help index. 
"""
from django.contrib.auth.models import User
from src.helpsys.models import HelpEntry
from src.ansi import ANSITable

#
# Helper functions
#

def _privileged_help_search(topicstr):
    """
    searches the topic data base without needing to know who calls it. Needed
    for autohelp functionality. Will show all help entries, also those set to staff
    only.
    """
    if topicstr.isdigit():
        t_query = HelpEntry.objects.filter(id=topicstr)
    else:
        exact_match = HelpEntry.objects.filter(topicname__iexact=topicstr)
        if exact_match:
            t_query = exact_match
        else:
            t_query = HelpEntry.objects.filter(topicname__istartswith=topicstr)        
    return t_query


def _create_help(topicstr, entrytext, staff_only=False, force_create=False,
             pobject=None, noauth=False):
    """
    Add a help entry to the database, replace an old one if it exists.

    Note - noauth=True will bypass permission checks, so do not use this from
    inside mud, it is needed by the autohelp system only. 
    """

    if noauth:
        #do not check permissions (for autohelp)
        topic = _privileged_help_search(topicstr)
    elif pobject:
        #checks access rights before searching (this should have been
        #done already at the command level)
        if not pobject.has_perm("helpsys.add_help"): return []
        topic = HelpEntry.objects.find_topicmatch(pobject, topicstr)
    else:
        return []

    if len(topic) == 1:
        #replace an old help file
        topic = topic[0]        
        topic.entrytext = entrytext
        topic.staff_only = staff_only
        topic.save()
        return [topic]
    elif len(topic) > 1 and not force_create:
        #a partial match, return it for inspection.
        return topic        
    else:
        #we have a new topic - create a new help object
        new_entry = HelpEntry(topicname=topicstr,
                         entrytext=entrytext,
                         staff_only=staff_only)
        new_entry.save()
        return [new_entry]

def handle_help_markup(topicstr, entrytext, staff_only, identifier="<<TOPIC:"):
    """
    Handle help markup in order to split help into subsections.
    Handles markup of the form <<TOPIC:STAFF:TopicTitle>> and
    <<TOPIC:ALL:TopicTitle>> to override the staff_only flag on a per-subtopic
    basis. 
    """
    topic_list = entrytext.split(identifier)                                
    topic_dict = {}
    staff_dict = {}
    for txt in topic_list:
        txt = txt.rstrip()
        if txt.count('>>'):
            topic, text = txt.split('>>',1)                  
            text = text.rstrip()
            topic = topic.lower()
            
            if topic in topic_dict.keys():
                #do not allow multiple topics of the same name
                return {}, []
            if 'all:' in topic:
                topic = topic[4:]
                staff_dict[topic] = False
            elif 'staff:' in topic:
                topic = topic[6:]
                staff_dict[topic] = True
            else:
                staff_dict[topic] = staff_only
            topic_dict[topic] = text                                                
        else:
            #no markup, just add the entry as-is
            topic = topicstr.lower()
            topic_dict[topic] = txt
            staff_dict[topic] = staff_only
    return topic_dict, staff_dict

def format_footer(top, text, topic_dict, staff_dict):
    """
    Formats the subtopic with a 'Related Topics:' footer. If mixed
    staff-only flags are set, those help entries without the staff-only flag
    will not see staff-only help files recommended in the footer. This allows
    to separate out the staff-only help switches etc into a separate
    help file so as not to confuse normal players.
    """
    if text:
        #only include non-staff related footers to non-staff commands
        if staff_dict[top]:
            other_topics = other_topics = filter(lambda o: o != top, topic_dict.keys())
        else:
            other_topics = other_topics = filter(lambda o: o != top and not staff_dict[o],
                                                 topic_dict.keys())           
        if other_topics:
            footer = ANSITable.ansi['normal'] + "\n\r\n\r    Related Topics: "            
            for t in other_topics:
                footer += t + ', '
            footer = footer[:-2] + '.'
            return text + footer
        else:
            return text            
    else:
        return False

#
# Access functions
#

def add_help(topicstr, entrytext, staff_only=False, force_create=False,
             pobject=None, auto_help=False):
    """
    Add a help topic to the database. This is also usable by autohelp, with auto=True. 

    Allows <<TOPIC:TopicTitle>> markup in the help text, to automatically spawn
    subtopics. For creating mixed staff/ordinary subtopics, the <<TOPIC:STAFF:TopicTitle>> and 
    <<TOPIC:ALL:TopicTitle>> commands can override the overall staff_only setting for
    that entry only. 
    """
    identifier = '<<TOPIC:'
    if identifier in entrytext:        
        #There is markup in the entry, so we should split the doc into separate subtopics        
        topic_dict, staff_dict = handle_help_markup(topicstr, entrytext,
                                                     staff_only, identifier)
        topics = []
        for topic, text in topic_dict.items():            

            #format with nice footer
            entry = format_footer(topic, text, topic_dict, staff_dict)

            if entry:                
                #create the subtopic
                newtopic = _create_help(topic, entry,staff_only=staff_dict[topic],
                        force_create=force_create,pobject=pobject,noauth=auto_help)
                topics.extend(newtopic)
        return topics

    elif entrytext:        
        #if there were no topic sections, just create the help entry as normal
        return _create_help(topicstr.lower(),entrytext,staff_only=staff_only,
                           force_create=force_create,pobject=pobject,noauth=auto_help) 

def del_help(pobject,topicstr):
    """
    Delete a help entry from the data base.

    Note that it makes no sense to delete auto-added help entries this way since
    they will just be re-added on the next @reload. Delete such entries by turning
    off their auto-help functionality first.
    """
    #find topic with permission checks
    if not pobject.is_staff(): return []
    topic = HelpEntry.objects.find_topicmatch(pobject, topicstr)
    if topic:
        if len(topic) == 1:
            #delete topic
            topic.delete()           
            return True
        else:
            return topic
    else:
            return []

def get_help_index(pobject,filter=None):
    """
    Dynamically builds a help index depending on who asks for it, so
    normal players won't see staff-only help files, for example.
    
    The filter parameter allows staff to limit their view of the help index
    no filter (default) - view all help files, staff and non-staff
    filter='staff' - view only staff-specific help files
    filter='player' - view only those files visible to all
    """

    if pobject.has_perm("helpsys.staff_help"):
        if filter == 'staff':
            helpentries = HelpEntry.objects.filter(staff_only=True).order_by('topicname')
        elif filter == 'player':
            helpentries = HelpEntry.objects.filter(staff_only=False).order_by('topicname')
        else:
            helpentries = HelpEntry.objects.all().order_by('topicname')
    else:
        helpentries = HelpEntry.objects.filter(staff_only=False).order_by('topicname')

    if not helpentries:
        pobject.emit_to("No help entries found.")
        return

    topics = [entry.topicname for entry in helpentries]
    #format help entries into suitable alphabetized collumns.
    percollumn = 8
    s = ""
    i = 0
    while True:
        i += 1
        try:
            top = topics.pop(0)
            s+= " %s " % top 
            if i%percollumn == 0: s += '\n\r'
        except IndexError:
            break    
    s += " (%i entries)" % (i-1)
    pobject.emit_to(s)
