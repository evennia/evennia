#!/usr/bin/env python

"""

Database migration helper, using South.

Usage: 

 - Install South using the method suitable for your platform
     http://south.aeracode.org/docs/installation.html

 -  You need to have a database setup, either an old one or 
    a fresh one. If the latter, run manage.py syncdb as normal, 
    entering superuser info etc.

 -  Start this tool and use the 'initialize' option. South will
    create a migration scheme for all Evennia components. 

That's all you need to do until Evennia's database scheme changes,
something which is usually announced with the update. To update
your current database automatically, follow these steps: 

 - Run this tool

 - Select the Update option. 

That is all. :) 

For more advanced migrations, there might be further instructions.

"""

import os, sys
from subprocess import call             


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
    database with 'python manage.py syncdb' before continuing."""
    sys.exit()

# Get the settings
from django.conf import settings

# Prepare all valid apps
APPLIST = [app.split('.')[-1] for app in settings.INSTALLED_APPS 
           if app.startswith("src.") or app.startswith("game.")]

def run_south(mode):    
    """
    Simply call manage.py with the appropriate South commands.
    """
    if mode == "init":
        for appname in APPLIST:
            print "Initializing %s ..." % appname
            call([sys.executable, "manage.py", "convert_to_south", appname])
        print "\nInitialization complete. That's all you need to do for now."    
    elif mode == "update":        
        for appname in APPLIST:        
            print "Updating/migrating schema for %s ..." % appname                
            call([sys.executable, "manage.py", "schemamigration", appname, "--auto"])
            call([sys.executable, "manage.py", "migrate", appname])                        
        print "\nUpdate complete."        
    
def south_ui():
    """
    Simple menu for handling migrations.
    """
    
    string = """
    Evennia Database Migration Tool

    You usually don't need to use this tool unless a new version of Evennia
    tells you that the database scheme changed in some way, AND you don't want
    to reset your database.
    
    This tool will help you to migrate an existing database without having to
    manually edit your tables and fields to match the new scheme. For that
    to work you must have run this tool *before* applying the changes however.

    This is a simple wrapper on top of South, a Django database scheme
    migration tool.
    
    If you want more control, you can call manage.py directly using the
    instructions found at http://south.aeracode.org/docs.

    NOTE: Evennia is still in Alpha - there is no guarantee that database
          changes will still not be too advanced to handle with this simple
          tool, and it is too soon to talk of supplying custom migration
          schemes to new versions. 

    Options: 

    i - Initialize an existing/new database with migration mappings (done once)
    u - Update an initialized database to the changed scheme
    q - Quit 
    """ 
    
    while True:
        print string 
        inp = str(raw_input(" Option > "))        
        inp = inp.lower()
        if inp in ["q", "i", "u"]:            
            if inp == 'i':
                run_south("init")
            elif inp == 'u':
                run_south("update")
            sys.exit()
            
if __name__ == "__main__":
    
    if not 'south' in settings.INSTALLED_APPS:
        string = "\n       The 'south' database migration tool does not seem to be installed."
        string += "\n      You can find it here: http://south.aeracide.org.\n"
        print string    
    else:
        south_ui()
        
