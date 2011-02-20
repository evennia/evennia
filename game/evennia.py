#!/usr/bin/env python
"""
EVENNIA SERVER STARTUP SCRIPT

Sets the appropriate environmental variables and launches the server
process. Run the script with the -h flag to see usage information.
"""
import os  
import sys
import signal
from optparse import OptionParser
from subprocess import Popen, call

# Set the Python path up so we can get to settings.py from here.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['DJANGO_SETTINGS_MODULE'] = 'game.settings'

if not os.path.exists('settings.py'):
    # make sure we have a settings.py file. 
    print "    No settings.py file found. Launching manage.py ..."

    import game.manage 

    print """
    Now configure Evennia by editing your new settings.py file.
    If you haven't already, you should also create/configure the 
    database with 'python manage.py syncdb' before continuing.

    When you are ready, run this program again to start the server."""
    sys.exit()
                     
# Get the settings
from django.conf import settings

# Setup the launch of twisted depending on which operating system we use
if os.name == 'nt':

    try:
        # Test for for win32api
        import win32api
    except ImportError:
        print """
    ERROR: Unable to import win32api, which Twisted requires to run. 
    You may download it from:
         
    http://sourceforge.net/projects/pywin32 
      or 
    http://starship.python.net/crew/mhammond/win32/Downloads.html"""
        sys.exit()

    if not os.path.exists('twistd.bat'):
        # Test for executable twisted batch file. This calls the twistd.py 
        # executable that is usually not found on the path in Windows.
        # It's not enough to locate scripts.twistd, what we want is the 
        # executable script C:\PythonXX/Scripts/twistd.py. Alas we cannot 
        # hardcode this location since we don't know if user has Python 
        # in a non-standard location, so we try to figure it out. 
        from twisted.scripts import twistd
        twistd_path = os.path.abspath(
            os.path.join(os.path.dirname(twistd.__file__), 
                         os.pardir, os.pardir, os.pardir, os.pardir, 
                         'scripts', 'twistd.py'))        
        bat_file = open('twistd.bat','w')
        bat_file.write("@\"%s\" \"%s\" %%*" % (sys.executable, twistd_path))
        bat_file.close()
        print """
    INFO: Since you are running Windows, a file 'twistd.bat' was
    created for you. This is a simple batch file that tries to call
    the twisted executable. Evennia determined this to be:
      
       %s

    If you run into errors at startup you might need to edit
    twistd.bat to point to the actual location of the Twisted
    executable (usually called twistd.py) on your machine.

    This procedure is only done once. Run evennia.py again when you 
    are ready to start the server.
    """ % twistd_path       
        sys.exit()

    TWISTED_BINARY = 'twistd.bat'
else:
    TWISTED_BINARY = 'twistd' 

# Setup access of the evennia server itself
SERVER_PY_FILE = os.path.join(settings.SRC_DIR, 'server/server.py')

# Add this to the environmental variable for the 'twistd' command.
thispath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if 'PYTHONPATH' in os.environ:
    os.environ['PYTHONPATH'] += (":%s" % thispath)
else:
    os.environ['PYTHONPATH'] = thispath

def cycle_logfile():
    """
    Move the old log file to evennia.log.old (by default).

    """    
    logfile = settings.DEFAULT_LOG_FILE.strip()
    logfile_old = logfile + '.old'
    if os.path.exists(logfile):
        # Cycle the old logfiles to *.old
        if os.path.exists(logfile_old):
            # E.g. Windows don't support rename-replace
            os.remove(logfile_old)
        os.rename(logfile, logfile_old)

    logfile = settings.HTTP_LOG_FILE.strip()
    logfile_old = logfile + '.old'
    if os.path.exists(logfile):
        # Cycle the old logfiles to *.old
        if os.path.exists(logfile_old):
            # E.g. Windows don't support rename-replace
            os.remove(logfile_old)
        os.rename(logfile, logfile_old)    

def start_daemon(parser, options, args):
    """
    Start the server in daemon mode. This means that all logging output will
    be directed to logs/evennia.log by default, and the process will be
    backgrounded.
    """ 
    if os.path.exists('twistd.pid'):
        print "A twistd.pid file exists in the current directory, which suggests that the server is already running."
        sys.exit()
    
    print '\nStarting Evennia server in daemon mode ...'
    print 'Logging to: %s.' % settings.DEFAULT_LOG_FILE
    
    # Move the old evennia.log file out of the way.
    cycle_logfile()

    # Start it up
    # Popen([TWISTED_BINARY, 
    #        '--logfile=%s' % settings.DEFAULT_LOG_FILE, 
    #        '--python=%s' % SERVER_PY_FILE])
    call([TWISTED_BINARY, 
          '--logfile=%s' % settings.DEFAULT_LOG_FILE, 
          '--python=%s' % SERVER_PY_FILE])


def start_interactive(parser, options, args):
    """
    Start in interactive mode, which means the process is foregrounded and
    all logging output is directed to stdout.
    """
    print '\nStarting Evennia server in interactive mode (stop with keyboard interrupt) ...'
    print 'Logging to: Standard output.'

    # we cycle logfiles (this will at most put all files to *.old)
    # to handle html request logging files. 
    cycle_logfile()
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
            print 'Stopping the Evennia server...'
            f = open('twistd.pid', 'r')
            pid = f.read()
            os.kill(int(pid), signal.SIGINT)
            print 'Server stopped.'
        else:
            print "No twistd.pid file exists, the server doesn't appear to be running."
    elif os.name == 'nt':
        print '\n\rStopping cannot be done safely under this operating system.' 
        print 'Kill server using the task manager or shut it down from inside the game.'
    else:
        print '\n\rUnknown OS detected, can not stop. '
        
def main():
    """
    Beginning of the program logic.
    """
    parser = OptionParser(usage="%prog [options] <start|stop>",
                          description="This command starts or stops the Evennia game server. Note that you have to setup the database by running  'manage.py syncdb' before starting the server for the first time.")
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
    from src.utils.utils import check_evennia_dependencies
    if check_evennia_dependencies():
        main()
