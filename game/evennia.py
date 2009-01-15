#!/usr/bin/env python
"""
EVENNIA SERVER STARTUP SCRIPT

Sets the appropriate environmental variables and launches the server
process. Run the script with the -h flag to see usage information.
"""
import getopt # for parsing command line arguments
from optparse import OptionParser
import os # for OS related fonctions 
import sys # for getting command line arguments
from subprocess import Popen, call

# Set the Python path up so we can get to settings.py from here.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['DJANGO_SETTINGS_MODULE'] = 'game.settings'
from django.conf import settings
SERVER_PY_FILE = os.path.join(settings.SRC_DIR, 'server.py')

# Determine what the twistd binary name is. Eventually may want to have a
# setting in settings.py to specify the path to the containing directory.
if os.name == 'nt':
    TWISTED_BINARY = 'twistd.bat'
else:
    TWISTED_BINARY = 'twistd' 

# Add this to the environmental variable for the 'twistd' command.
os.environ['PYTHONPATH'] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def cycle_logfile():
    """
    Move the old log file to evennia.log (by default).
    """
    if os.path.exists(settings.DEFAULT_LOG_FILE):
        os.rename(settings.DEFAULT_LOG_FILE, 
                  settings.DEFAULT_LOG_FILE+'.old')

def start_daemon(parser, options, args):
    """
    Start the server in daemon mode. This means that all logging output will
    be directed to logs/evennia.log by default, and the process will be
    backgrounded.
    """ 
    if os.path.exists('twistd.pid'):
        print "A twistd.pid file exists in the current directory, which suggests that the server is already running."
        sys.exit()
    
    print 'Starting in daemon mode...'
    
    # Move the old evennia.log file out of the way.
    cycle_logfile()

    # Start it up
    Popen([TWISTED_BINARY, 
           '--logfile=%s' % settings.DEFAULT_LOG_FILE, 
           '--python=%s' % SERVER_PY_FILE])

def start_interactive(parser, options, args):
    """
    Start in interactive mode, which means the process is foregrounded and
    all logging output is directed to stdout.
    """
    print 'Starting in interactive mode...'
    try:
        call([TWISTED_BINARY, 
              '-n', 
              '--python=%s' % SERVER_PY_FILE])
    except KeyboardInterrupt:
        pass

def stop_server(parser, options, args):
    """
    Gracefully stop the server process.
    """
    if os.name == 'posix': 
        if os.path.exists('twistd.pid'):
            print 'Stoping The Server'
            f = open('twistd.pid', 'r')
            pid = f.read()
            Popen(['kill', pid])
        else:
            print "No twistd.pid file exists, the server doesn't appear to be running."
    elif os.name == 'nt':
        print 'TODO not implented'
    else:
        print 'Unknown OS delected, can not kill'

def main():
    """
    Beginning of the program logic.
    """
    parser = OptionParser(usage="%prog [options] <start|stop>",
                          description="")
    parser.add_option('-i', '--interactive', action='store_true', 
                      dest='interactive', default=False,
                      help='Start in interactive mode')
    parser.add_option('-d', '--daemon', action='store_false', 
                      dest='interactive',
                      help='Start in daemon mode (default)')
    (options, args) = parser.parse_args()
    
    if "start" in args:
        if options.interactive:
            start_interactive(parser, options, args)
        else:
            start_daemon(parser, options, args)
    elif "stop" in args:
        stop_server(parser, options, args)
    else:
        parser.print_help()
if __name__ == '__main__':
    main()
