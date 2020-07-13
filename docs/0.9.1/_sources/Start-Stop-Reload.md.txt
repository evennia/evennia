# Start Stop Reload


You control Evennia from your game folder (we refer to it as `mygame/` here), using the `evennia`
program. If the `evennia` program is not available on the command line you must first install
Evennia as described in the [Getting Started](./Getting-Started) page.

> Hint: If you ever try the `evennia` command and get an error complaining that the command is not available, make sure your [virtualenv](./Glossary#virtualenv) is active. 

Below are described the various management options. Run

    evennia -h

to give you a brief help and

    evennia menu

to give you a menu with options.

## Starting Evennia

Evennia consists of two components, the Evennia [Server and Portal](./Portal-And-Server).  Briefly,
the  *Server* is what is running the mud. It handles all game-specific things but doesn't care
exactly how players connect, only that they have. The *Portal* is a gateway to which players
connect. It knows everything about telnet, ssh, webclient protocols etc but very little about the
game. Both are required for a functioning mud.

     evennia start

The above command will start the Portal, which in turn will boot up the Server. The command will
print a summary of the process and unless there is an error you will see no further output. Both
components will instead log to log files in `mygame/server/logs/`. For convenience you can follow
those logs directly in your terminal by attaching `-l` to commands:

     evennia -l

Will start following the logs of an already running server. When starting Evennia you can also do

     evennia start -l

> To stop viewing the log files, press `Ctrl-C`.

## Foreground mode

Normally, Evennia runs as a 'daemon', in the background. If you want you can start either of the
processes (but not both) as foreground processes in *interactive* mode. This means they will log
directly to the terminal (rather than to log files that we then echo to the terminal) and you can
kill the process (not just the log-file view) with `Ctrl-C`.

    evennia istart

will start/restart the *Server* in interactive mode. This is required if you want to run a
*debugger*. Next time you reload the server, it will return to normal mode.

    evennia ipstart

will start the *Portal* in interactive mode. This is usually only necessary if you want to run
Evennia under the control of some other type of process.

## Reloading

The act of *reloading* means the Portal will tell the Server to shut down and then boot it back up
again. Everyone will get a message and the game will be briefly paused for all accounts as the server
reboots. Since they are connected to the *Portal*, their connections are not lost.


Reloading is as close to a "warm reboot" you can get. It reinitializes all code of Evennia, but
doesn't kill "persistent" [Scripts](./Scripts). It also calls `at_server_reload()` hooks on all objects so you
can save eventual temporary properties you want.

From in-game the `@reload` command is used. You can also reload the server from outside the game:

     evennia reload

Sometimes reloading from "the outside" is necessary in case you have added some sort of bug that
blocks in-game input.

## Resetting

*Resetting* is the equivalent of a "cold reboot" - the Server will shut down and then restarted
again, but will behave as if it was fully shut down. As opposed to a "real" shutdown, no accounts will be disconnected during a
reset. A reset will however purge all non-persistent scripts and will call `at_server_shutdown()`
hooks. It can be a good way to clean unsafe scripts during development, for example.

From in-game the `@reset` command is used. From the terminal:

    evennia reset


## Rebooting

This will shut down *both* Server and Portal, which means all connected players will lose their
connection. It can only be initiated from the terminal:

    evennia reboot

This is identical to doing these two commands:

     evennia stop
     evennia start


## Shutting down

A full shutdown closes Evennia completely, both Server and Portal. All accounts will be booted and
systems saved and turned off cleanly.

From inside the game you initiate a shutdown with the `@shutdown` command.  From command line you do

     evennia stop

You will see messages of both Server and Portal closing down. All accounts will see the shutdown
message and then be disconnected. The same effect happens if you press `Ctrl+C` while the server
runs in interactive mode.

## Status and info

To check basic Evennia settings, such as which ports and services are active, this will repeat the
initial return given when starting the server:

    evennia info

You can also get a briefer run-status from both components with this command

    evennia status

This can be useful for automating checks to make sure the game is running and is responding.


## Killing (Linux/Mac only)

In the extreme case that neither of the server processes locks up and does not respond to commands,
you can send them kill-signals to force them to shut down. To kill only the Server:

    evennia skill

To kill both Server and Portal:

    evennia kill

Note that this functionality is not supported on Windows.


## Django options

The `evennia` program will also pass-through options used by the `django-admin`. These operate on the database in various ways.

```bash

 evennia migrate # migrate the database
 evennia shell   # launch an interactive, django-aware python shell
 evennia dbshell # launch database shell

```

For (many) more options, see [the django-admin docs](https://docs.djangoproject.com/en/1.7/ref/django-admin/#usage).

## Advanced handling of Evennia processes

If you should need to manually manage Evennia's processors (or view them in a task manager program
such as Linux' `top` or the more advanced `htop`), you will find the following processes to be
related to Evennia:

* 1 x `twistd ... evennia/server/portal/portal.py` - this is the Portal process.
* 3 x `twistd ... server.py` - One of these processes manages Evennia's Server component, the main
  game. The other processes (with the same name but different process id) handle's Evennia's
  internal web server threads. You can look at `mygame/server/server.pid` to determine which is the
  main process.

### Syntax errors during live development

During development, you will usually modify code and then reload the server to see your changes.
This is done by Evennia re-importing your custom modules from disk. Usually bugs in a module will
just have you see a traceback in the game, in the log or on the command line.  For some really
serious syntax errors though, your module might not even be recognized as valid Python. Evennia may
then fail to restart correctly.

From inside the game you see a text about the Server restarting followed by an ever growing list of
"...". Usually this only lasts a very short time (up to a few seconds). If it seems to go on, it
means the Portal is still running (you are still connected to the game) but the Server-component of
Evennia failed to restart (that is, it remains in a shut-down state). Look at your log files or
terminal to see what the problem is - you will usually see a clear traceback showing what went
wrong.

Fix your bug then run

    evennia start

Assuming the bug was fixed, this will start the Server manually (while not restarting the Portal).
In-game you should now get the message that the Server has successfully restarted.
