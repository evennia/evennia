#!/bin/bash
export DJANGO_SETTINGS_MODULE="settings"
#python2.5 -m cProfile -o profiler.log -s time server.py
python2.5 server.py
