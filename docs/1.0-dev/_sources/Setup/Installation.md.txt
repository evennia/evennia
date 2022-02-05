# Installation

The Evennia server is installed, run and maintained from the terminal (console/CMD on Windows). Starting the server
doesn't make anything visible online. Once you download everything you can in fact develop your game in complete
isolation if you want, without needing any access to the internet.

Evennia requires [Python](https://www.python.org/downloads/) 3.9 or 3.10.
Using a [Python virtualenv](../Glossary.md#virtualenv) is highly recommended in order to keep your
Evennia installation independent from the system libraries. Don't install Evennia as 
administrator or superuser. 

```{warning}
pip install evennia is not yet available in develop branch. Use the [git installation](./Installation-Git.md).
```
```{warning}
If you are converting an existing game from a previous version, [see here](./Installation-Upgrade.md).
```

    pip install evennia

Once installed, make sure the `evennia` command works. Use `evennia -h` for usage help. If you are using a 
virtualenv, make sure it's active whenever you need to use the `evennia` command.

Alternatively, you can [install Evennia from github](./Installation-Git.md) or use [docker](./Installation-Docker.md).
Check out [installation troubleshooting](./Installation-Troubleshootin.md) if you run into problems. Some 
users have also experimented with [installing Evennia on Android](./Installation-Android.md).

## Initialize a new game

Use `cd` to enter a folder where you want to do your game development. Here (and in
the rest of the Evennia documentation) we call this folder `mygame`, but you should of course
name your game whatever you like.

    evennia --init mygame

This will create a new folder `mygame` (or whatever you chose) in your current location. This
contains empty templates and all the default settings needed to start the server.


## Start the new game

    cd mygame 
    evennia migrate

This will create the default database (Sqlite3). The database file ends up as `mygame/server/evennia.db3`. If you
ever want to start from a fresh database, just delete this file and re-run `evennia migrate` again.

    evennia start

Set your user-name and password when prompted. This will be the "god user" or "superuser" in-game. 
The email is optional.

> You can also [automate](./Installation-Non-Interactive.md) the creation of the super user.

If all went well, the server is now up and running. Point a legacy MUD/telnet client to `localhost:4000` or
a web browser at [http://localhost:4001](http://localhost:4001) to play your new (if empty) game! 

Log in as a new account or use the superuser you just created.


## Restarting and stopping


You can restart the server without disconnecting players:

    evennia restart

To do a full stop and restart (will disconnect players):

    evennia reboot

Full stop of the server (use `evennia start` to restart):

    evennia stop

## See server logs

Log files are in `mygame/server/logs`. You can tail them live with

    evennia --log

or

    evennia -l


You can start viewing the log immediately when running `evennia` commands, such as


    evennia start -l

To exit the log tailing, enter `Ctrl-C` (`Cmd-C` for Mac). This will not affect the server.

## Server configuration 

The server configuration file is `mygame/server/settings.py`. It's empty by default. Copy and change 
only the settings you want from the [default settings file](./Settings-Default.md).


## The Next steps

You are good to go! 

Evennia comes with a small [Tutorial World](../Howto/Starting/Part1/Tutorial-World.md) to experiment and learn from. After logging 
in, you can create it by running 

    batchcommand tutorial_world.build

Next, why not head into the [Starting Tutorial](../Howto/Starting/Part1/Starting-Part1.md) 
to learn how to start making your new game!