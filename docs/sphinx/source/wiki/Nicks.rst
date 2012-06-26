Nicks
=====

*Nicks*, short for *Nicknames* is a system allowing an object (usually a
`Player Character <Players.html>`_) to assign custom replacement names
for other game entities.

Nicks are not to be confused with *Aliases*. Setting an Alias on a game
entity actually changes an inherent attribute on that entity, and
everyone in the game will be able to use that alias to address the
entity thereafter. A *Nick* on the other hand, is an alternate name *you
alone* can use to refer to that entity. The nicknamed entitity is not
changed in any way. The principle is very simple - Evennia simply scans
your input looking for a defined nick and replaces it with the full,
"real" name before passing it on. In the default system nicks are
controlled with the simple ``nick`` command, but the system can be
expanded for other uses too.

Default Evennia use Nicks in three flavours that determine when Evennia
actually tries to do the substitution.

-  inputline - replacement is attempted whenever you write anything on
   the command line. This is the default.
-  objects - replacement is only attempted when referring an object
-  players - replacement is only attempted when referring a player

Here's how to use it in the default command set (using the ``nick``
command):

::

     nick ls = look

This is a good one for unix/linux users who are accustomed to using the
``ls`` command in their daily life. It is equivalent to
``nick/inputline ls = look``.

::

     nick/object mycar2 = The red sports car

With this example, substitutions will only be done specifically for
commands expecting an object reference, such as

::

     look mycar2 

becomes equivalent to "``look The red sports car``\ ".

::

     nick/players tom = Thomas Johnsson

This is useful for commands searching for players explicitly:

::

     @find *tom 

One can use nicks to speed up input. Below we add ourselves a quicker
way to build red buttons. In the future just writing *rb* will be enough
to execute that whole long string.

::

     nick rb = @create button:examples.red_button.RedButton

Nicks could also be used as the start for building a "recog" system
suitable for an RP mud.

::

     nick/player Arnold = The mysterious hooded man

Coding with nicks
-----------------

Nicks are are stored as the ``Nick`` database model and are referred
from the normal Evennia `object <Objects.html>`_ through the ``nicks``
property. `` nicks`` is a special handler that offers effective error
checking, searches and conversion.

::

    # A command/channel nick:
      object.nicks.add("greetjack", "tell Jack = Hello pal!")

    # An object nick:  
      object.nicks.add("rose", "The red flower", nick_type="object")

    # An player nick:
      object.nicks("tom", "Tommy Hill", nick_type="player")

    # My own custom nick type (handled by my own game code somehow):
      object.nicks.add("hood", "The hooded man", nick_type="my_identsystem")

    # get back the translated nick:
     full_name = object.nicks.get("rose", nick_type="object")

    # delete a previous set nick
      object.nicks.del("rose", nick_type="object")

In a command definition you can reach the nick handler through
``self.caller.nicks``. See the ``nick`` command in
``game/gamesrc/commands/default/general.py`` for more examples.

As a last note, The Evennia `channel <Communications.html>`_ alias
systems are using nicks with the ``nick_type="channel"`` in order to
allow users to create their own custom aliases to channels.
