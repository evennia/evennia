#! /usr/bin/python2.7
"""
Linux launcher
"""

import os, sys

sys.path.insert(0, os.path.abspath(os.getcwd()))

from  evennia.server.evennia_launcher import main
main()
