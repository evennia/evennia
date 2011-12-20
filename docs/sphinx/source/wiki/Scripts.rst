Scripts
=======

*Scripts* are the way to implement everything in Evennia that may change
with time.

The most obvious use of Scripts may be to use them as *timers* or
*Events*. Consider a script running on the object ``Grandfather Clock``.
The script has a timer that tells it to fire every hour. This allows the
clock to chime regularly. The script might even regulate how often the
clock must be rewound so it won't stop.

Scripts may act as changeable *States*. Consider for example creating a
'dark' room. It has two scripts assigned on it - one ``DarkState``
script, and one ``BrightState`` script. When characters enters the dark
room, it assigns a custom `Cmdset <Commands.html>`_ to them - this
command set (say) limits their actions because of the darkness. After
the characters have stumbled around for a while, someone brings up a
torch. As a light source is now in the room, ``DarkState`` reacts to
this by shutting down itself and handing over control to the
``BrightState`` script that restores normal commands. Finally, when the
character with the torch leaves the room, the ``BrightState`` script
detects this and obediently hands control back to the ``DarkState``,
leaving the remaining poor characters in darkness once again.

By combining state-changes with timers one can make a room look
different during nighttime than it does during the day. Weather and
seasons might come and go. But one can also achieve more complex things
such as state-AI systems that make mobs move around and possibly pursue
characters between rooms.

... In short, Scripts make the game world *tick*. Scripts are
database-persistent objects and are `TypeClassed <Typeclasses.html>`_
entities, with all the advantages that this entails.

How to create your own Script types
-----------------------------------

An Evennia Script is, per definition, a Python class that includes
``src.scripts.scripts.Script`` among its parents (if you are aware of
how typeclasses work, this is a typeclass linked to the ``ScriptDB``
database model). Scripts have no in-game representation and you cannot
define them with any default commands. They have to be created in python
code modules and imported from there into the game.

The vast majority of scripts are always run 'on'
`Objects <Objects.html>`_ affecting that object and maybe its
surroundings or contents. Scripts unrelated to objects are called
*Global* scripts and could handle things like game-time, weather and
other tickers.

Custom script modules are usually stored in ``game/gamesrc/scripts``. As
a convenience you can inherit all scripts from
``game.gamesrc.scripts.basescript.Script``.

You can try out scripts an add them to objects by use of the ``@script``
command (not to the confused with ``@scripts`` which lists scripts). You
can try it out with an example script:

::

    > @script self = examples.bodyfunctions.BodyFunctions

This should cause some random messages. The ``/stop`` switch will kill
the script again.

In code, you add scripts to `Objects <Objects.html>`_ and the script can
then manipulate the object as desired. The script is added to the
object's *script handler*, called simply ``scripts``. The handler takes
care of all initialization and startup of the script for you.

::

    # adding a script to an existing object 'myobj'
    myobj.scripts.add("game.gamesrc.scripts.myscripts.CoolScript")

The ``myobj.scripts.add()`` method also takes an argument *key* that
allows you to name your script uniquely before adding it. This is not
necessary, but is useful if you add many scripts of the same class and
later plan to use ``myobj.scripts.delete`` to remove individual scripts.

Properties and functions defined on Scripts
-------------------------------------------

It's important to know the variables controlling the script before one
can create one. Beyond those properties assigned to all typeclassed
objects (see `Typeclasses <Typeclasses.html>`_), such as ``key``,
``db``, ``ndb`` etc, all Scripts also has the following properties:

-  ``desc`` - an optional description of the script's function. Seen in
   listings.
-  ``interval`` - how often the script should run. If ``interval == 0``
   (default), it runs forever (it will not accept a negative value).
-  ``start_delay`` - (bool), if we should wait ``interval`` seconds
   before firing for the first time or not.
-  ``repeats`` - How many times we should repeat, assuming
   ``interval > 0``. If repeats is set to ``<= 0``, the script will
   repeat indefinitely.
-  ``persistent``- if this script should survive a server reboot.

There is one special property:

-  ``obj`` - the `Object <Objects.html>`_ this script is attached to (if
   any). You should not need to set this manually. If you add the script
   to the Object with ``myobj.scripts.add(myscriptpath)``, the ``obj``
   property will be set to ``myobj`` for you.

It's also imperative to know the hook functions. Normally, overriding
these are all the customization you'll need to do in Scripts. You can
find longer descriptions of these in ``gamesrc/scripts/basescript.py``.

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

Running methods (usually called automatically by the engine, but
possible to also invoke manually)

-  ``start()`` - this will start the script. This is called
   automatically whenever you add a new script to a handler.
   ``at_start()`` will be called.
-  ``stop()`` - this will stop the script and delete it. Removing a
   script from a handler will stop it auomatically. ``at_stop()`` will
   be called.
-  ``pause()`` - this pauses a running script, rendering it inactive,
   but not deleting it. Timers are saved and can be resumed. This is
   called automatically when the server reloads. No hooks are called -
   this is a suspension of the script, not a change of state.
-  ``unpause()`` - resumes a previously paused script. Timers etc are
   restored to what they were before pause. The server unpauses all
   paused scripts after a server reload. No hooks are called - as far as
   the script is concerned, it never stopped running.
-  ``time_until_next_repeat()`` - for timed scripts, this returns the
   time in seconds until it next fires. Returns None if not a timed
   script.

Example script
--------------

::

    import random
    from game.gamesrc.scripts.basescript import Script
    class Weather(Script): 
        "Displays weather info. Meant to be attached to a room."
        def at_script_creation(self):
            "Called once, during initial creation"
            self.key = "weather_script"
            self.desc = "Gives random weather messages."
            self.interval = 60 * 5 # every 5 minutes
            self.persistent = True
        self.at_repeat(self):
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

    # Assuming Script is found in game/gamesrc/scripts/weather.py
    myroom.scripts.add(weather.Weather)

Or, from in-game, use the ``@script`` command:

::

    @script here = weather.Weather

Global scripts
--------------

You can create scripts that are not attached to a given object -
*Global* scripts. You can create such a script with
``src.utils.create.create_script()`` by refrainnig from supplying an
object to store it on.

::

    from src.utils.create import create_script
      create_script(globals.MyGlobalEconomy, key="economy", obj=None)

Assuming ``game.gamesrc.scripts.global.MyGlobalEconomy`` can be found,
this will create and start it as a global script.
