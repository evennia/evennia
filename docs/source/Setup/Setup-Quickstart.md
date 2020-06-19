# Setup quickstart

The Evennia server is installed, run and maintained from the terminal (console/CMD on Windows). Starting the 
server doesn't make anything visible online. Once you download everything you can in fact develop your game
in complete isolation if you want, without needing any access to the internet. 

## Installation

Evennia requires Python3.7+. As with most Python packages, using a
[virtualenv](../Glossary#virtualenv) is recommended in order to keep your
installation independent from the system libraries. It's _not_ recommended 
to install Evennia as superuser. 

    pip install evennia

Make sure the `evennia` command works. Use `evennia -h` for usage help (or read on).

If you are having trouble, want to install in some other way (like with Docker) or want to contribute to
Evennia itself, check out the [Extended Installation instructions](Extended-Installation). 
It also has a [troubleshooting section](Extended-Installation#Troubleshooting) for different operating
systems.


## Initialize a new game

Use `cd` to enter a folder where you want to do your game development. Here (and in 
the rest of this documentation we call this folder `mygame`, but you should of course 
name your game whatever you like):

    evennia --init mygame

This will create a new folder `mygame` (or whatever you chose) in your current location. This
contains 


## Start the new game

`cd` into your game folder (`mygame` above). Next run 

    evennia migrate

This will create the default database (Sqlite3). The database file ends up as `mygame/server/evennia.db3`. If you
ever want to start from a fresh database, just delete this file and re-run `evennia migrate` again.

    evennia start 

Fill in your user-name and password. This will be the "god user" or "superuser" in-game. The email is optional.

If all went well, the server is now up and running. Point a legacy MUD/telnet client to `localhost:4000` or
a web browser at [http://localhost:4001](http://localhost:4001) to play your new (if empty) game!

> If `localhost` doesn't work on your computer, use `127.0.0.1`, which is the same thing.


## See server logs 

This will echo the server logs to the terminal as they come in

    evennia --log

or 

    evennia -l 


You can also attach `--log` to other `evennia` commands to start the log right away, such as 


    evennia start -l 


## Restarting and stopping 


This will restart the server without disconnecting any connected players:

    evennia restart 

Do a full stop and restart (will disconnect everyone):

    evennia reboot 

Stop the server (will need to use `start` to activate it again):

    evennia stop


## The Next step

Why not head into the [Starting Tutorial](../Howto/Starting/Starting-Overview) to learn how to start making your new game!
