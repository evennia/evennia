# Menu-based login system

Contribution by Vincent-lg 2016. Reworked for modern EvMenu by Griatch, 2019.

This changes the Evennia login to ask for the account name and password as a series
of questions instead of requiring you to enter both at once. It uses Evennia's 
menu system `EvMenu` under the hood.

## Installation

To install, add this to `mygame/server/conf/settings.py`:

    CMDSET_UNLOGGEDIN = "evennia.contrib.base_systems.menu_login.UnloggedinCmdSet"
    CONNECTION_SCREEN_MODULE = "contrib.base_systems.menu_login.connection_screens"

Reload the server and reconnect to see the changes.

## Notes

If you want to modify the way the connection screen looks, point
`CONNECTION_SCREEN_MODULE` to your own module. Use the default as a
guide (see also Evennia docs).
