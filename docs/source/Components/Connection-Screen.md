# Connection Screen


When you first connect to your game you are greeted by Evennia's default connection screen.


    ==============================================================
     Welcome to Evennia, version Beta-ra4d24e8a3cab+!

     If you have an existing account, connect to it by typing:
          connect <username> <password>
     If you need to create an account, type (without the <>'s):
          create <username> <password>

     If you have spaces in your username, enclose it in quotes.
     Enter help for more info. look will re-show this screen.
    ==============================================================

Effective, but not very exciting. You will most likely want to change this to be more unique for
your game. This is simple:

1. Edit `mygame/server/conf/connection_screens.py`.
1. [Reload](../Setup/Running-Evennia.md) Evennia.

Evennia will look into this module and locate all *globally defined strings* in it. These strings
are used as the text in your connection screen and are shown to the user at startup. If more than
one such string/screen is defined in the module, a *random* screen will be picked from among those
available.

## Commands available at the Connection Screen

You can also customize the [Commands](./Commands.md) available to use while the connection screen is
shown (`connect`, `create` etc). These commands are a bit special since when the screen is running
the account is not yet logged in. A command is made available at the login screen by adding them to
`UnloggedinCmdSet` in `mygame/commands/default_cmdset.py`.  See [Commands](./Commands.md) and the
tutorial section on how to add new commands to a default command set.
