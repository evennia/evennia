Running Evennia
===============

You control Evennia from ``game/`` using the ``evennia.py`` program.
Below are described the various management options. You can also start
the program without any arguments or use the *menu* option to get a
multiple-choice menu instead.

::

     python evennia.py menu

Starting Evennia
----------------

Evennia consists of two components, the Evennia `Server and
Portal <PortalAndServer.html>`_. Briefly, the *Server* is what is
running the mud. It handles all game-specific things but don't care
exactly how players connect, only that they have. The *Portal* is a
gateway to which players connect. It knows everything about telnet, ssh,
webclient protocols etc but very little about the game. Both are
required for a functioning mud.

::

     python evennia.py start

The above command automatically starts both Portal and Server at the
same time, logging to the log files in ``game/log``.

If you rather see error messages etc directly in the terminal (useful
for quickly debugging your code), you use the -i (interactive) flag:

::

     python evennia.py -i start 

This will start the *Server* in interactive mode. The Portal will
continue to log to its log file. This is normally what you want unless
you are debugging the Portal.

You can also start the two components one at a time.

::

     python evennia.py start server
     python evennia.py start portal

Adding -i to either of these explicit commands will start that component
in interactive mode so it logs to the terminal rather than to log file.

Reloading
---------

The act of *reloading* means the *Server* program is shut down and then
restarted again. In the default cmdset you initiate a reload by using
the ``@reload`` command from inside the game. The game will be briefly
paused for all players as the server comes back up (since they are all
connected to the *Portal*, their connections are not lost).

Reloading is as close to a "warm reboot" you can get. It reinitializes
all code of Evennia, but doesn't kill "persistent" scripts. It also
calls ``at_server_reload()`` hooks on all objects so you can save
eventual temporary properties you want.

You can also reload the server from outside the game (not available in
Windows):

::

     python evennia.py reload

Resetting
---------

*Resetting* is the equivalent of a "cold reboot" of the server - it will
restart but will behave as if it was fully shut down. You initiate a
reset using the ``@reset`` command from inside the game. As with a
reload, no players will be disconnected during a shutdown. It will
however purge all non-persistent scripts and will call
``at_server_shutdown()`` hooks. It can be a good way to clean unsafe
scripts during development, for example.

A reset is equivalent to

::

     python evennia.py stop server
     python evennia.py start server

Shutting down
-------------

A full shutdown closes Evennia completely, both Server and Portal. All
players will be booted and systems saved and turned off cleanly. From
inside the game you initiate a shutdown with the ``@shutdown`` command.

From command line you do

::

     python.py evennia.py stop

You will see messages of both Server and Portal closing down.
