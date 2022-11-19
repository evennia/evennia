# Installation

```{important}
If you are converting an existing game from a previous Evennia version, [see here](./Installation-Upgrade.md).
```

Installing Evennia doesn't make anything visible online. Apart from installation and updating, you can develop your game without any internet connection.

- Evennia requires [Python](https://www.python.org/downloads/) 3.9, 3.10 or 3.11 (recommended)
	- Windows: In the installer, make sure you select `add python to path`.  If you have multiple versions of Python installed, use `py` command instead of `python` to have Windows automatically use the latest.
- Using a light-weight  [Python virtual environment](Installation-Git#virtualenv) _ is optional, but _highly recommended_ in order to keep your Evennia installation independent from the system libraries. This comes with Python.
- Don't install Evennia as administrator or superuser. 
- If you run into trouble, see [installation troubleshooting](Installation-Troubleshooting).

Evennia  is managed from the terminal (console/Command Prompt on Windows). Once you have Python, you install Evennia with

    pip install evennia

Optional: If you use a [contrib](Contribs) that warns you that it needs additional packages, you can 
install all extra dependencies with 

	pip install evennia[extra]

To update Evennia later, do 

    pip install --upgrade evennia

Once installed, make sure the `evennia` command works. Use `evennia -h` for usage help.

> Windows users: You need to first run `python -m evennia` once. This should permanently add the evennia launcher to your environment, making the `evennia` command available.

If you are using a  virtualenv, make sure it's active whenever you need to use the `evennia` command.

> You can also  [clone Evennia from github](./Installation-Git.md)  or use [docker](./Installation-Docker.md).  Some users have also experimented with [installing Evennia on Android](./Installation-Android.md).

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

This will create the default database (Sqlite3). The database file ends up as `mygame/server/evennia.db3`. If you ever want to start from a fresh database, just delete this file and re-run `evennia migrate` again.

    evennia start

Set your user-name and password when prompted. This will be the "god user" or "superuser" in-game.  The email is optional.

> You can also [automate](./Installation-Non-Interactive.md) the creation of the super user.

If all went well, the server is now up and running. Point a legacy MUD/telnet client to `localhost:4000` or a web browser at [http://localhost:4001](http://localhost:4001) to play your new (if empty) game! 

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

Stop viewing the log by pressing `Ctrl-C` (`Cmd-C` for Mac). 

You can start viewing the log immediately by adding `-l/--log` to `evennia` commands, such as

    evennia start -l


## Server configuration 

The server configuration file is `mygame/server/settings.py`. It's empty by default. Copy and change  only the settings you want from the [default settings file](./Settings-Default.md).

## Register with the Evennia Game Index (optional)

You can let the world know that you are working on a new Evennia-based game by 
registering your server with the _Evennia game index_. You don't have to be 
open for players to do this - you just mark your game as closed and "pre-alpha".

    evennia connections 

See [here](./Evennia-Game-Index.md) for more instructions and please [check out the index](http:games.evennia.com) 
beforehand to make sure you don't pick a game name that is already taken - be nice!

## The Next steps

You are good to go! 

Next, why not head into the [Starting Tutorial](../Howtos/Beginner-Tutorial/Part1/Beginner-Tutorial-Part1-Intro.md)  to learn how to start making your new game!
