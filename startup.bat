@echo off
set DJANGO_SETTINGS_MODULE=settings
set PYTHONPATH=.
echo Starting Evennia...

rem We're only going to run in interactive mode until we've had more time to make sure things work as expected on Windows.
twistd -noy server.py