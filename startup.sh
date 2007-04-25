#!/bin/bash
export DJANGO_SETTINGS_MODULE="settings"

## Uncomment whichever python binary you'd like to use to run the game.
## Evennia is developed on 2.5 but should be compatible with 2.4.
# PYTHON_BIN="python"
# PYTHON_BIN="python2.4"
PYTHON_BIN="python2.5"

## The name of your logfile.
LOGNAME="evennia.log"
## Where to put the last log file from the game's last running
## on next startup.
LOGNAME_OLD="evennia.log.old"
mv $LOGNAME $LOGNAME_OLD

## There are several different ways you can run the server, read the
## description for each and uncomment the desired mode.

## Generate profile data for use with cProfile.
# $PYTHON_BIN -m cProfile -o profiler.log -s time server.py
## Interactive mode. Good for development and debugging.
# $PYTHON_BIN server.py
## Stand-alone mode. Good for running games.
nohup $PYTHON_BIN server.py > $LOGNAME &
