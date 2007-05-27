#!/bin/bash
export DJANGO_SETTINGS_MODULE="settings"

mv -f logs/evennia.log logs/evennia.logs.old

## There are several different ways you can run the server, read the
## description for each and uncomment the desired mode.

## TODO: Make this accept a command line argument to use interactive
## mode instead of having to uncomment crap.

## Interactive mode. Good for development and debugging.
#twistd -noy twistd -ny server.py
## Stand-alone mode. Good for running games.
twistd -y server.py
