#!/usr/bin/env python
"""
MUX HELP FILE IMPORTER

Imports MUX/MUSH-style help files.
"""
from optparse import OptionParser
from subprocess import Popen, call
import os  
import sys
import signal

# Set the Python path up so we can get to settings.py from here.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['DJANGO_SETTINGS_MODULE'] = 'game.settings'
from django.conf import settings
from src.helpsys.models import HelpEntry

# If true, when found, duplicate entries are replaced.
replace_duplicates = False

topic_name = ''
entry_text = ''

def _is_function_entry(topic_name):
    """
    Returns True if this appears to be a MUX/MUSH function entry. We are not
    generally interested in these.
    """
    try:
        # If the topic name ends in '()', it's a function
        if topic_name[-2:] == "()":
            return True
    except IndexError:
        # Let the following return handle this
        pass
    return False

def _create_db_entry():
    """
    Creates a HelpFile object in the database from the currently stored values.
    """
    global topic_name, entry_text
    
    existing_matches = HelpEntry.objects.filter(topicname__iexact=topic_name)
    save_entry = True
    
    if existing_matches and not replace_duplicates:
        print "IGNORING DUPLICATE:", topic_name
        save_entry = False
    elif existing_matches and replace_duplicates:
        print "REPLACING:", topic_name
        help = existing_matches[0]
    else:
        print "CREATING:", topic_name
        help = HelpEntry()
    
    if save_entry:
        help.topicname = topic_name
        help.entrytext = entry_text
        if not _is_function_entry(topic_name):
            help.save()
        else:
            print "IGNORING FUNCTION:", topic_name
    
    topic_name = ''
    entry_text = ''
    
def _start_new_helpentry(first_line):
    """
    Given a line, start storing stuff in a new help entry.
    """
    global topic_name
    
    if topic_name.strip() != '' and entry_text.strip() != '':
        _create_db_entry()
    
    topic_name = first_line[1:].strip()
    if topic_name == '' or topic_name.lower() == 'help':
        topic_name = 'Help Index'

def import_helpfiles(file):
    """
    Given a file-like object, imports the help files within.
    """
    global topic_name, entry_text
    
    line_list = file.readlines()
    
    for line in line_list:
        if line[0] == '&':
            _start_new_helpentry(line)
        else:
            #print "+%s" % line
            entry_text += line

def main():
    """
    Beginning of the program logic.
    """
    global replace_duplicates
    
    parser = OptionParser(usage="%prog [options] <helpfile.txt>",
        description="This command imports MUX and MUSH-style help files. By " \
        "default, if a duplicate entry is found, the existing entry is " \
        "preserved. With the -r flag, the existing entry is replaced with " \
        "the imported entry.")
    parser.add_option('-r', '--replace', action='store_true', 
                      dest='replace_duplicates', default=False,
                      help='Replace duplicate entries')
    (options, args) = parser.parse_args()
    
    # A filename must be provided
    filename = " ".join(args)
    if filename.strip() == "":
        parser.print_help()
        return
        
    try:
        file = open(filename, 'r')
    except IOError:
        print "Specified file cannot be found."
        return
    
    # Make this globally available for lazyness
    replace_duplicates = options.replace_duplicates
    
    # Import the help files
    import_helpfiles(file)
        
if __name__ == '__main__':
    main()