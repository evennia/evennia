Players
=======

All users (in the sense of actual people) connecting to Evennia are
doing so through an object called *Player*. The Player object has no
in-game representation; rather it is the out-of-character representation
of the user. The Player object is what is chatting on
`Channels <Communications.html>`_. It is also a good place to store
`Permissions <Locks.html>`_ to be consistent between different in-game
characters, configuration options, account info and other things related
to the user. Players are `TypeClassed <Typeclasses.html>`_ entities and
can store a `CmdSet <Commands.html>`_ of their own for OOC-type
commands.

If you are logged in into default Evennia, you can use the ``@ooc``
command to leave your current `Character <Objects.html>`_ and go into
OOC mode. You are quite limited in this mode, basically it works like a
simple chat program. It acts as a staging area for switching between
Characters (if your game supports that) or as a safety mode if your
Character gets deleted. . Use ``@ic`` to switch back "into" your
character.

Also note that the Player object can have a different set of
[Locks#Permissions Permissions] from the Character they control (in the
first character you create permissions for Player and Character are the
same, however).

How to create your own Player types
-----------------------------------

You will usually not want more than one Player typeclass for all new
players (but you could in principle create a system that changes a
player's typeclass dynamically).

An Evennia Player is, per definition, a Python class that includes
``src.players.player.Player`` among its parents (if you are aware of how
`Typeclasses <Typeclasses.html>`_ work, this is a typeclass linked to
the ``PlayerDB`` database model). You can also inherit from
``ev.Player`` which is a shortcut.

Here's how to define a new Player typeclass in code:

::

    from ev import Player
    class ConfigPlayer(Player):
        """
        This creates a Player with some configuration options
        """        
        at_player_creation(self):
            "this is called only once, when player is first created"
            self.db.real_name = None      # this is set later
            self.db.real_address = None   #        ''
            self.db.config_1 = True       # default config
            self.db.config_2 = False      #       "
            self.db.config_3 = 1          #       "
            # ... whatever else our game needs to know

There is no pre-made folder in ``game/gamesrc`` to store custom player
typeclasses. Make your own folder or store it in ``gamesrc/objects``
(remember that if you make your own folder you need to add an empty
``__init__.py`` file so that you can import the file later). To change
which object becomes the Player object for new players, set the variable
``BASE_PLAYER_TYPECLASS`` in your ``settings.py`` file.

Properties on Players
---------------------

Beyond those properties assigned to all typeclassed objects (see
`Typeclasses <Typeclasses.html>`_), the Player also has the following
custom properties:

-  ``user`` - a unique link to a ``User`` Django object, representing
   the logged-in user.
-  ``character`` - a reference to an associated *Character*-type
   `Object <Objects.html>`_.
-  ``obj`` - an alias for ``character``.
-  ``name`` - an alias for ``user.username``
-  ``sessions`` - a list of all connected Sessions (physical
   connections) this object listens to.
-  ``is_superuser`` (bool: True/False) - if this player is a superuser.

Special handlers:

-  ``cmdset`` - This holds all the current `Commands <Commands.html>`_
   of this Player. By default these are the commands found in the cmdset
   defined by ``settings.CMDSET_OOC``.
-  ``nicks`` - This stores and handles `Nicks <Nicks.html>`_, in the
   same way as nicks it works on Objects. For Players, nicks are
   primarily used to store custom aliases for [Communications#Channels
   Channels].

How it all hangs together
-------------------------

Looking at the above list, it's clear there are more to ``Player``\ s
than what first meets the eye.

What happens when a person connects to Evennia and logs in is that they
log in as a ``User`` object. This is a Django object that knows all
about keeping track of authentication - it stores the login name
(``username``), password, e-mail etc.

We can't change ``User`` very much unless we want to start digging down
into Django source code (and we don't). Django however allows another
model (technically called a *profile*) to reference the User for
customization. This is our ``Player`` object. There is a one-to-one
relationship between ``User`` and Player, so we have tried to completely
hide the ``User`` interface throughout Evennia and left you to only have
to deal with ``Player``.

So for all purposes, ``Player`` represents the OOC existence of a person
logged into Evennia. You e.g. connect to
`Channels <Communications.html>`_ using your Player identity. The Player
object may store configurations and follows you wherever you go. You
will however never see the Player object in-game. This is handled by a
*Character*, a type of `Object <Objects.html>`_ connected to the
``character`` property in the list above.

So why don't we just use ``Player`` to walk around with too? The main
reason for this is flexibility. Your Player object won't change, but
your character *might*. By separating the two you could easily implement
a game where you can ``swap`` between different *Character* objects. All
you'd need to do is change the ``character`` property to point to
another suitable object (and change the values of the ``player``
property on the affected objects).

So the structure looks like ``User - Player - Character``, where the
last two are typeclassed, customizable objects.
