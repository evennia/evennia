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

# Globally available help entry temp values
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

def _create_db_entry(replace_duplicates):
    """
    Creates a HelpFile object in the database from the currently stored values.
    """
    global topic_name, entry_text
    
    # See if an existing topic matches the new topic's name
    existing_matches = HelpEntry.objects.filter(topicname__iexact=topic_name)
    
    # If this becomes false, the entry is not saved
    save_entry = True
    
    if existing_matches and not replace_duplicates:
        # Duplicate, ignore this one
        print "IGNORING DUPLICATE:", topic_name
        save_entry = False
    elif existing_matches and replace_duplicates:
        # Replace an existing entry
        print "REPLACING:", topic_name
        help = existing_matches[0]
    else:
        # New blank entry
        print "CREATING:", topic_name
        help = HelpEntry()
    
    if save_entry:
        help.topicname = topic_name
        help.entrytext = entry_text
        if not _is_function_entry(topic_name):
            help.save()
        else:
            print "IGNORING FUNCTION:", topic_name
    
    # Reset for the next help entry
    topic_name = ''
    entry_text = ''
    
def _start_new_helpentry(first_line, replace_duplicates):
    """
    Given a line, start storing stuff in a new help entry.
    """
    global topic_name
    
    # Before starting a new help entry, save the old one that was previously
    # being worked on (if applicable)
    if topic_name.strip() != '' and entry_text.strip() != '':
        _create_db_entry(replace_duplicates)
    
    topic_name = first_line[1:].strip()
    # Handle the default topic
    if topic_name == '' or topic_name.lower() == 'help':
        topic_name = 'Help Index'

def import_helpfiles(file, replace_duplicates=False):
    """
    Given a file-like object, imports the help files within.
    """
    global topic_name, entry_text
    
    # One list entry per line
    line_list = file.readlines()
    
    for line in line_list:
        """
        If the first character of the line is an ampersand, this line is the
        start of a new help entry. Save the previous one we were working on
        and start a new one.
        """
        if line[0] == '&':
            _start_new_helpentry(line, replace_duplicates)
        else:
            # Otherwise, keep cramming the lines into the entry text attrib
            entry_text += line
            
    # End the last topic
    _start_new_helpentry('', replace_duplicates)

def main():
    """
    Beginning of the program logic.
    """
    parser = OptionParser(usage="%prog [options] <helpfile.txt>",
        description="This command imports MUX and MUSH-style help files. By " \
        "default, if a duplicate entry is found, the existing entry is " \
        "preserved. With the -r flag, the existing entry is replaced with " \
        "the imported entry.")
    parser.add_option('-r', '--replace', action='store_true', 
                      dest='replace_duplicates', default=False,
                      help='Replace duplicate entries')
    (options, args) = parser.parse_args()
    
    # A filename must be provided, show help if not
    filename = " ".join(args)
    if filename.strip() == "":
        parser.print_help()
        return
        
    try:
        file = open(filename, 'r')
    except IOError:
        print "Specified file cannot be found."
        return
    
    # Import the help files
    import_helpfiles(file, replace_duplicates=options.replace_duplicates)
        
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print "Import Aborted."