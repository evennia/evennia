The Connection Screen
=====================

When you first connect to your game you are greeted by Evennia's default
connection screen. It welcomes you, gives you the server version and
tells you how to connect.

::


    ==============================================================
     Welcome to Evennia, version Beta-ra4d24e8a3cab+!

     If you have an existing account, connect to it by typing:
          connect <username> <password>
     If you need to create an account, type (without the <>'s):
          create <username> <password>

     If you have spaces in your username, enclose it in quotes.
     Enter help for more info. look will re-show this screen.
    ==============================================================

Effective, but not very exciting. You will most likely want to change
this to be more unique for your game.

You can customize the connection screen easily. If you look in
``game/gamesrc/world`` you will find a module named
``connection_screens.py``. Evennia looks into this module for globally
defined strings (only). These strings are used as connection screens and
shown to the user at startup. If more than one screen is defined in the
module, a random screen will be picked from among those available.

Evennia's default screen is imported as ``DEFAULT_SCREEN`` from
``src.commands.connection_screen``. Remove the import or redefine
``DEFAULT_SCREEN`` to get rid of the default. There is a commented-out
example screen in the module that you can start from. You can define and
import things as normal into the module, but remember that *all* global
strings will be picked up and potentially used as a connection screen.
You can change which module Evennia uses by changing
``settings.CONNECTION_SCREEN_MODULE``.

You can also customize the `commands <Commands.html>`_ available during
the connection screen (``connect``, ``create`` etc). These commands are
a bit special since when the screen is running the player is not yet
identified. A command is made available at the login screen by adding
them to the command set specified by settings.CMDSET\_UNLOGGEDIN. The
default commands are found in ``src/commands/default/unloggedin.py``.
