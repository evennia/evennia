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

#------------------------------------------------------------
# Get Evennia version
#------------------------------------------------------------
try:
    f = open(os.pardir + os.sep + 'VERSION.txt', 'r''')
    VERSION = "%s-r%s" % (f.read().strip(), os.popen("hg id -i").read().strip())
    f.close()
except IOError:
    VERSION = "Unknown version"

#------------------------------------------------------------
# Check so session file exists in the current dir- if not, create it.
#------------------------------------------------------------

_CREATED_SETTINGS = False
if not os.path.exists('settings.py'):
    # If settings.py doesn't already exist, create it and populate it with some
    # basic stuff.

    # make random secret_key.
    import random
    import string
    secret_key = list((string.letters +
        string.digits + string.punctuation).replace("\\", "").replace("'", '"'))
    random.shuffle(secret_key)
    secret_key = "".join(secret_key[:40])

    settings_file = open('settings.py', 'w')
    _CREATED_SETTINGS = True

    string = \
    """
######################################################################
# Evennia MU* server configuration file
#
# You may customize your setup by copy&pasting the variables you want
# to change from the master config file src/settings_default.py to
# this file. Try to *only* copy over things you really need to customize
# and do *not* make any changes to src/settings_default.py directly.
# This way you'll always have a sane default to fall back on
# (also, the master config file may change with server updates).
#
######################################################################

from src.settings_default import *

######################################################################
# Custom settings
######################################################################


######################################################################
# SECRET_KEY was randomly seeded when settings.py was first created.
# Don't share this with anybody. It is used by Evennia to handle
# cryptographic hashing for things like cookies on the web side.
######################################################################
SECRET_KEY = '%s'

""" % secret_key

    settings_file.write(string)
    settings_file.close()

    # obs - this string cannot be under i18n since settings didn't exist yet.
    print """
    Welcome to Evennia!

    This looks like your first startup, so we created a fresh
    game/settings.py file for you. No database has yet been created.
    You may edit the settings file now if you like, but if you just
    want to quickly get started you don't have to touch anything.

    Once you are ready to continue, (re)run
        python manage.py syncdb
    followed by
        python manage.py migrate
    """


#------------------------------------------------------------
# Test the import of the settings file
#------------------------------------------------------------
try:
    from game import settings
except Exception:
    import traceback
    string = "\n" + traceback.format_exc()

    # note - if this fails, ugettext will also fail, so we cannot translate this string.

    string += """\n
    Error: Couldn't import the file 'settings.py' in the directory containing %(file)r.
    There are usually two reasons for this:
    1) The settings module contains errors. Review the traceback above to resolve the
       problem, then try again.
    2) If you get errors on finding DJANGO_SETTINGS_MODULE you might have set up django
       wrong in some way. If you run a virtual machine, it might be worth to restart it
       to see if this resolves the issue. Evennia should not require you to define any
       environment variables manually.
    """ % {'file': __file__}
    print string
    sys.exit(1)

os.environ['DJANGO_SETTINGS_MODULE'] = 'game.settings'

#------------------------------------------------------------
# This is run only if the module is called as a program
#------------------------------------------------------------
if __name__ == "__main__":

    if _CREATED_SETTINGS:
        # if settings were created, info has already been printed.
        sys.exit()

    # run the standard django manager, if dependencies match
    from src.utils.utils import check_evennia_dependencies
    if check_evennia_dependencies():
        if len(sys.argv) > 1 and sys.argv[1] in ('runserver', 'testserver'):
            print """
            WARNING: There is no need to run the Django development
            webserver to test out Evennia web features (the web client
            will in fact not work since the Django test server knows
            nothing about MUDs).  Instead, just start Evennia with the
            webserver component active (this is the default).
            """
        from django.core.management import execute_from_command_line
        execute_from_command_line(sys.argv)
