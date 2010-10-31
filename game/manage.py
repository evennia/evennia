#!/usr/bin/env python
"""
Set up the evennia system. A first startup consists of giving
the command './manage syncdb' to setup the system and create
the database. 
"""

import sys
import os

# Tack on the root evennia directory to the python path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    VERSION = open("%s%s%s" % (os.pardir, os.sep, 'VERSION')).readline().strip()
except IOError:
    VERSION = "Unknown version"

_CREATED_SETTINGS = False    
if not os.path.exists('settings.py'):
    # If settings.py doesn't already exist, create it and populate it with some
    # basic stuff.

    settings_file = open('settings.py', 'w')
    _CREATED_SETTINGS = True

    string = \
    """# 
# Evennia MU* server configuration file
#
# You may customize your setup by copy&pasting the variables you want
# to change from the master config file src/settings_default.py to
# this file. Try to *only* copy over things you really need to customize
# and do *not* make any changes to src/settings_default.py directly.
# This way you'll always have a sane default to fall back on
# (also, the master file may change with server updates).
#

from src.settings_default import * 

###################################################
# Evennia base server config 
###################################################

###################################################
# Evennia Database config 
###################################################

###################################################
# Evennia in-game parsers
###################################################

###################################################
# Default command sets 
###################################################

###################################################
# Default Object typeclasses 
###################################################

###################################################
# Batch processor 
###################################################

###################################################
# Game Time setup
###################################################

###################################################
# Game Permissions
###################################################

###################################################
# In-game Channels created from server start
###################################################

###################################################
# IMC2 Configuration
###################################################

###################################################
# IRC config
###################################################

###################################################
# Config for Django web features
###################################################

###################################################
# Evennia components (django apps)
###################################################"""

    settings_file.write(string)
    settings_file.close()

    print """
    Welcome to Evennia (version %s)! 
    We created a fresh settings.py file for you.""" % VERSION 

try:
    from game import settings
except Exception:
    import traceback
    string = "\n" + traceback.format_exc()
    string += """\n
    Error: Couldn't import the file 'settings.py' in the directory 
    containing %r. There can be two reasons for this: 
    1) You moved your settings.py elsewhere. In that case you need to run
       django-admin.py, passing it the true location of your settings module.
    2) The settings module is where it's supposed to be, but an exception
       was raised when trying to load it. Review the traceback above to
       resolve the problem, then try again. 
    """ % __file__
    print string 
    sys.exit(1)
        
if __name__ == "__main__":
    from django.core.management import execute_manager    
    if _CREATED_SETTINGS: 
        print """
    Edit your new settings.py file as needed, then run
    'python manage syncdb' and follow the prompts to
    create the database and your superuser account.
        """
        sys.exit()
    # run the django setups
    execute_manager(settings)
