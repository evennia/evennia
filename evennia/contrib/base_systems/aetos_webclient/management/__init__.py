"""
Django management commands shipped by the Aetos Web Client contrib.

Django discovers commands at `<app>/management/commands/<name>.py`, and Evennia's
launcher passes any operation it does not handle itself to Django's dispatch --
so a command here is reachable as `evennia <name>`. That is the whole mechanism
behind `evennia aetos discover`; see `commands/aetos.py`.

"""
