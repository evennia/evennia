@echo off
rem ------------------------------------------------------------------------
rem WINDOWS STARTUP SCRIPT
rem NOTE: This _MUST_ be launched with the Twisted environment variables
rem set. It is recommended that you launch Twisted Command Prompt to do so.
rem ------------------------------------------------------------------------

set DJANGO_SETTINGS_MODULE=settings
set PYTHONPATH=.
echo Starting Evennia...

rem ------------------------------------------------------------------------
rem We're only going to run in interactive mode until we've had more time to 
rem make sure things work as expected on Windows.
rem ------------------------------------------------------------------------
twistd -oy --logfile=- --python=src/server.py