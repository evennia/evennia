#! /usr/bin/python
"""
Windows launcher. This is called by a dynamically created .bat file in
the python bin directory and makes the 'evennia' program available on
the command %path%.
"""

import os, sys

sys.path.insert(0, os.path.abspath(os.getcwd()))

from  evennia.server.evennia_launcher import main
main()
