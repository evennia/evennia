#!/usr/bin/env python
import sys
import os
from django.core.management import execute_manager

# Tack on the root evennia directory to the python path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from game import settings
except ImportError:
     import sys
     sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
     sys.exit(1)

if __name__ == "__main__":
     execute_manager(settings)
