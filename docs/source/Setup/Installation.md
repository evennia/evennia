# Installation

The fastest way to install Evennia is to use the `pip` installer that comes with Python (read on). You can also  [clone Evennia from github](./Installation-Git.md)  or use [docker](./Installation-Docker.md).  Some users have also experimented with [installing Evennia on Android](./Installation-Android.md).

If you are converting an existing game, please follow the [upgrade instructions](./Installation-Upgrade.md).

## Requirements

```{sidebar} Develop in isolation
Installing Evennia doesn't make anything visible online. Apart from installation and updating, you can develop your game without any internet connection if you want to.
```
- Evennia requires [Python](https://www.python.org/downloads/) 3.11, 3.12 or 3.13 (recommended). Any OS that supports Python should work.
	- _Windows_: In the installer, make sure to select `add python to path`. If you have multiple versions of Python installed, use `py` command instead of `python` to have Windows automatically use the latest.
- Don't install Evennia as administrator or superuser.
- If you run into trouble, see [installation troubleshooting](./Installation-Troubleshooting.md).

## Install with `pip`

```{important}
You are recommended to setup a light-weight Python virtualenv to install Evennia in. Using a virtualenv is standard practice in Python and allows you to install what you want in isolation from other programs. The virtualenv system is a part of Python and will make your life easier!
```

You re recommended to [setup a light-weight Python virtualenv](./Installation-Git.md#virtualenv) first.

Evennia is managed from the terminal (console/Command Prompt on Windows). Once you have Python installed&mdash;and after activating your virtualenv if you are using one&mdash;install Evennia with:

	pip install evennia

Optional: If you use a [contrib](../Contribs/Contribs-Overview.md) that warns you that it needs additional packages, you can  install all extra dependencies with:

	pip install evennia[extra]

To update Evennia later, do the following:

	pip install --upgrade evennia

```{note} **Windows users only -**
You now must run `python -m evennia` once. This should permanently make the `evennia` command available in your environment.
```

Once installed, make sure the `evennia` command works. Use `evennia -h` for usage help. If you are using a virtualenv, make sure it is active whenever you need to use the `evennia` command later.

## Initialize a New Game

We will create a new "game dir" in which to create your game. Here, and in the rest of the Evennia documentation, we refer to this game dir as  `mygame`, but you should, of course, name your game whatever you like. To create the new `mygame` folder&mdash;or whatever you choose&mdash;in your current location:

```{sidebar} Game Dir vs Game Name
The game dir you create doesn't have to match the name of your game. You can change the name of your game later by editing `mygame/server/conf/settings.py`.
```

	evennia --init mygame

The resultant folder contains all the empty templates and default settings needed to start the Evennia server.

## Start the New Game

First, create the default database (Sqlite3):

	cd mygame
	evennia migrate

The resulting database file is created in `mygame/server/evennia.db3`. If you ever want to start from a fresh database, just delete this file and re-run the `evennia migrate` command.

Next, start the Evennia server with:

	evennia start

When prompted, enter a username and password for the in-game "god" or "superuser." Providing an email address is optional.

> You can also [automate](./Installation-Non-Interactive.md) creation of the superuser.

If all went well, your new Evennia server is now up and running! To play your new&mdash;albeit empty&mdash;game, point a legacy MUD/telnet client to `localhost:4000` or a web browser to [http://localhost:4001](http://localhost:4001). You may log in as a new account or use the superuser account you created above.

## Restarting and Stopping


You can restart the server (without disconnecting players) by issuing:

	evennia restart

And, to do a full stop and restart (with disconnecting players) use:

	evennia reboot

A full stop of the server (use `evennia start` to restart) is achieved with:

	evennia stop

See the [Server start-stop-reload](./Running-Evennia.md) documentation page for details.

## View Server Logs

Log files are located in `mygame/server/logs`. You can tail the logging in real-time with:

	evennia --log

or just:

	evennia -l

Press `Ctrl-C` (`Cmd-C` for Mac) to stop viewing the live log.

You may also begin viewing the real-time log immediately by adding `-l/--log` to `evennia` commands, such as when starting the server:

    evennia start -l

## Server Configuration

Your server's configuration file is `mygame/server/conf/settings.py`. It's empty by default. Copy and paste **only** the settings you want/need from the [default settings file](./Settings-Default.md) to your server's `settings.py`. See the [Settings](./Settings.md) documentation for more information before configuring your server at this time.

## Register with the Evennia Game Index (optional)

To let the world know that you are working on a new Evennia-based game, you may register your server with the _Evennia game index_ by issuing:

    evennia connections

Then, just follow the prompts. You don't have to be open for players to do this &mdash; simply mark your game as closed and "pre-alpha."

See [here](./Evennia-Game-Index.md) for more instructions and please [check out the index](http:games.evennia.com)  beforehand to make sure you don't pick a game name that is already taken &mdash; be nice!

## Next Steps

You are good to go!

Next, why not head over to the [Starting Tutorial](../Howtos/Beginner-Tutorial/Beginner-Tutorial-Overview.md) to learn how to begin making your new game!
