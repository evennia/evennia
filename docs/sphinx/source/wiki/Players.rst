Players
=======

All gamers (real people) that opens a game *Session* on Evennia are
doing so through an object called *Player*. The Player object has no
in-game representation, it represents the account the gamer has on the
game. In order to actually get on the game the Player must *puppet* an
`Object <Objects.html>`_ (normally a Character).

Just how this works depends on the configuration option
``MULTISESSION_MODE``. There are three multisession modes, described in
the diagram below:

|image0|

From left to right, these show ``MULTISESSION_MODE`` 0, 1 and 2. In all
cases the gamer connects to the `Portal <PortalAndServer.html>`_ with
one or more sessions - this could be a telnet connection, webclient, ssh
or some of the other protocols Evennia supports.

-  In mode 0 (leftmost), each Player can only hold one session at a
   time. This is the normal mode for many legacy muds.
-  In mode 1 (middle), each Player can hold any number of sessions but
   they are all treated equal. This means all giving a command in one
   client is doing exactly the same thing as doing so in any other
   connected client. All sessions will see the same output and e.g.
   giving the @quit command will kill all sessions.
-  In mode 2 (right) eeach Player can hold any number of sessions and
   they are kept separate from one another. This allows a single player
   to puppet any number of Characters and Objects.

Apart from storing login information and other account-specific data,
the Player object is what is chatting on
`Channels <Communications.html>`_. It is also a good place to store
`Permissions <Locks.html>`_ to be consistent between different in-game
characters as well as configuration options. Players are
`TypeClassed <Typeclasses.html>`_ entities defaulting to use
``settings.BASE_PLAYER_TYPECLASS``. They also hold a
`CmdSet <Commands.html>`_ defaulting to the set defined by
``settings.CMDSET_PLAYER``.

If you are logged in into default Evennia under any multisession mode,
you can use the ``@ooc`` command to leave your current
`Character <Objects.html>`_ and go into OOC mode. You are quite limited
in this mode, basically it works like a simple chat program. It acts as
a staging area for switching between Characters (if your game supports
that) or as a safety mode if your Character gets deleted. . Use ``@ic``
attempt to puppet a Character.

Note that the Player object can and often do have a different set of
[Locks#Permissions Permissions] from the Character they control.
Normally you should put your permissions on the Player level - only if
your Player does not have a given permission will the permissions on the
Character be checked.

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
            self.db.real_address = None   #       "
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
-  ``obj`` - an alias for ``character``.
-  ``name`` - an alias for ``user.username``
-  ``sessions`` - a list of all connected Sessions (physical
   connections) this object listens to. The so-called session-id (used
   in many places) is found as a property ``sessid`` on each Session
   instance.
-  ``is_superuser`` (bool: True/False) - if this player is a superuser.

Special handlers:

-  ``cmdset`` - This holds all the current `Commands <Commands.html>`_
   of this Player. By default these are the commands found in the cmdset
   defined by ``settings.CMDSET_PLAYER``.
-  ``nicks`` - This stores and handles `Nicks <Nicks.html>`_, in the
   same way as nicks it works on Objects. For Players, nicks are
   primarily used to store custom aliases for [Communications#Channels
   Channels].

Selection of special methods (see ``src.player.models`` for details):

-  ``get_puppet`` - get a currently puppeted object connected to the
   Player and a given given session id, if any.
-  ``puppet_object`` - connect a session to a puppetable Object.
-  ``unpuppet_object`` - disconnect a session from a puppetable Object.
-  ``msg`` - send text to the Player
-  ``execute_cmd`` - runs a command as if this Player did it.
-  ``search`` - search for Players.

.. |image0| image:: https://lh5.googleusercontent.com/-9XuiTr2UAbo/UZDxNLFUobI/AAAAAAAAB3I/1wArg9P-KnQ/w898-h293-no/evennia_player_sessions2.png
