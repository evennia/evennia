Scripts
=======

*Scripts* are the out-of-character siblings to the in-character
`Objects <Objects.html>`_. The name "Script" might suggest that they can
only be used to script the game but this is only part of their
usefulness (in the end we had to pick a single name for them). Scripts
are full Typeclassed database entities, just like Objects - with all the
advantages this entails. Likewise they can also store arbitrary
*Attributes*.

Scripts can be used for many different things in Evennia:

-  They can attach to Objects to influence them in various ways - or
   exist independently of any one in-game entity.
-  They can work as timers and tickers - anything that may change with
   Time. But they can also have no time dependence at all.
-  They can describe State changes.
-  They can act as data stores for storing game data persistently in the
   database.
-  They can be used as OOC stores for sharing data between groups of
   objects.

The most obvious use of Scripts may be to use them as *timers* or
*Events*. Consider a script running on the object ``Grandfather Clock``.
The script has a timer that tells it to fire every hour. This allows the
clock to chime regularly. The script might even regulate how often the
clock must be rewound so it won't stop.

Scripts may act as changeable *States*. Consider for example creating a
'dark' room. It has two scripts assigned on it - one ``DarkState``
script, and one ``BrightState`` script. When characters enter the dark
room, it assigns a custom `Cmdset <Commands.html>`_ to them. This
command set defines the parameters of the state they describe. In this
case it limits their actions because of the darkness. After the
characters have stumbled around for a while, someone brings up a torch.
As a light source is now in the room, ``DarkState`` reacts to this by
shutting down itself and handing over control to the ``BrightState``
script that restores normal commands. Finally, when the character with
the torch leaves the room, the ``BrightState`` script detects this and
obediently hands control back to the ``DarkState``, leaving the
remaining poor characters in darkness once again.

By combining state-changes with timers one can make a room look
different during nighttime than it does during the day. Weather and
seasons might come and go. But one can also achieve more complex things
such as state-AI systems that make mobs move around and possibly pursue
characters between rooms.

Scripts are also excellent places to store game data in an OOC way. A
groupd of objects may share date by use of a Script object they all hold
references to.

In short, Scripts can be used for a lot of things.

How to create and test your own Script types
--------------------------------------------

In-game you can try out scripts using the ``@script`` command. Try the
following:

::

     > @script self = examples.bodyfunctions.BodyFunctions

This should cause some random messages. Add the ``/stop`` switch to the
above command to kill the script again. You can use the ``@scripts``
command to list all active scripts in the game. Evennia creates a few
default ones.

Custom script modules are usually stored in ``game/gamesrc/scripts``. As
a convenience you can inherit sripts from ``ev.Script``.

If you add scripts to `Objects <Objects.html>`_ the script can then
manipulate the object as desired. The script is added to the object's
*script handler*, called simply ``scripts``. The handler takes care of
all initialization and startup of the script for you.

::

     # add script to myobj's scripthandler
     myobj.scripts.add("game.gamesrc.scripts.myscripts.CoolScript")
     # alternative way
     from ev import create_script
     create_script("game.gamesrc.scripts.myscripts.CoolScript", obj=myobj)

A script does not have to be connected to an in-game object. Such
scripts are called *Global scripts*. You can create global scripts by
simply not supplying an object to store it on:

::

     # adding a global script
     from ev import create_script
     create_script("game.gamesrc.scripts.globals.MyGlobalEconomy", key="economy", obj=None)

Assuming the Script ``game.gamesrc.scripts.globals.MyGlobalEconomy``
exists, this will create and start it as a global script.

Properties and functions defined on Scripts
-------------------------------------------

A Script has all the properties of a typeclassed object, such as ``db``
and ``ndb``\ (see `Typeclasses <Typeclasses.html>`_). Setting ``key`` is
useful in order to manage scripts (delete them by name etc). These are
usually set up in the Script's typeclass, but can also be assigned on
the fly as keyword arguments to ``ev.create_script``.

-  ``desc`` - an optional description of the script's function. Seen in
   script listings.
-  ``interval`` - how often the script should run. If ``interval == 0``
   (default), it runs forever, without any repeating (it will not accept
   a negative value).
-  ``start_delay`` - (bool), if we should wait ``interval`` seconds
   before firing for the first time or not.
-  ``repeats`` - How many times we should repeat, assuming
   ``interval > 0``. If repeats is set to ``<= 0``, the script will
   repeat indefinitely.
-  ``persistent``- if this script should survive a server *reset* or
   server *shutdown*. (You don't need to set this for it to survive a
   normal reload - the script will be paused and seamlessly restart
   after the reload is complete).

There is one special property:

-  ``obj`` - the `Object <Objects.html>`_ this script is attached to (if
   any). You should not need to set this manually. If you add the script
   to the Object with ``myobj.scripts.add(myscriptpath)`` or give
   ``myobj`` as an argument to the ``utils.create.create_script``
   function, the ``obj`` property will be set to ``myobj`` for you.

It's also imperative to know the hook functions. Normally, overriding
these are all the customization you'll need to do in Scripts. You can
find longer descriptions of these in ``src/scripts/scripts.py``.

-  ``at_script_creation()`` - this is usually where the script class
   sets things like ``interval`` and ``repeats``; things that control
   how the script runs. It is only called once - when the script is
   first created.
-  ``is_valid()`` - determines if the script should still be running or
   not. This is called when running ``obj.scripts.validate()``, which
   you can run manually, but which also Evennia calls during certain
   situations such as reloads. This is also useful for using scripts as
   state managers. If the method returns ``False``, the script is
   stopped and cleanly removed.
-  ``at_start()`` - this is called when the script first starts. For
   persistent scripts this is at least once ever server startup. Note
   that this will *always* be called right away, also if ``start_delay``
   is ``True``.
-  ``at_repeat()`` - this is called every ``interval`` seconds, or not
   at all. It is called right away at startup, unless ``start_delay`` is
   ``True``, in which case the system will wait ``interval`` seconds
   before calling.
-  ``at_stop()`` - this is called when the script stops for whatever
   reason. It's a good place to do custom cleanup.
-  ``at_server_reload()`` - this is called whenever the server is
   warm-rebooted (e.g. with the ``@reload`` command). It's a good place
   to save non-persistent data you might want to survive a reload.
-  ``at_server_shutdown()`` - this is called when a system reset or
   systems shutdown is invoked.

Running methods (usually called automatically by the engine, but
possible to also invoke manually)

-  ``start()`` - this will start the script. This is called
   automatically whenever you add a new script to a handler.
   ``at_start()`` will be called.
-  ``stop()`` - this will stop the script and delete it. Removing a
   script from a handler will stop it automatically. ``at_stop()`` will
   be called.
-  ``pause()`` - this pauses a running script, rendering it inactive,
   but not deleting it. All properties are saved and timers can be
   resumed. This is called automatically when the server reloads. No
   hooks are called - as far as the script knows, it never stopped -
   this is a suspension of the script, not a change of state.
-  ``unpause()`` - resumes a previously paused script. Timers etc are
   restored to what they were before pause. The server unpauses all
   paused scripts after a server reload. No hooks are called - as far as
   the script is concerned, it never stopped running.
-  ``time_until_next_repeat()`` - for timed scripts, this returns the
   time in seconds until it next fires. Returns ``None`` if
   ``interval==0``.

Example script
--------------

::

    import random
    from ev import Script
    class Weather(Script): 
        "Displays weather info. Meant to be attached to a room."
        def at_script_creation(self):
            "Called once, during initial creation"
            self.key = "weather_script"
            self.desc = "Gives random weather messages."
            self.interval = 60 * 5 # every 5 minutes
            self.persistent = True
        def at_repeat(self):
            "called every self.interval seconds."        
            rand = random.random()
            if rand < 0.5:
                weather = "A faint breeze is felt."
            elif rand < 0.7:
                weather = "Clouds sweep across the sky."                          
            else:
                weather = "There is a light drizzle of rain."
            # send this message to everyone inside the object this
            # script is attached to (likely a room)
            self.obj.msg_contents(weather)

This is a simple weather script that we can put on an object. Every 5
minutes it will tell everyone inside that object how the weather is.

To activate it, just add it to the script handler (``scripts``) on an
`Room <Objects.html>`_. That object becomes ``self.obj`` in the example
above. Here we put it on a room called ``myroom``:

::

    myroom.scripts.add(weather.Weather)

In code you can also use the create function directly if you know how to
locate the room you want:

::

    from ev import create_script
    create_script('game.gamesrc.scripts.weather.Weather', obj=myroom)

Or, from in-game, use the ``@script`` command:

::

     @script here = weather.Weather 

