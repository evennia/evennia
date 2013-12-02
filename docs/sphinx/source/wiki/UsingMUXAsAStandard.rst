The 'MUX-like' default of Evennia
=================================

Evennia is a highly customizable codebase. Among many things, its
command structure and indeed the very way that commands look can all be
changed by you. If you like the way, say, DikuMUDs handle things, you
could emulate that with Evennia. Or LPMuds, or MOOs. Or if you are
ambitious you could design a whole new style, perfectly fitting your own
dreams of the ideal MUD.

We do offer a default however. The default Evennia setup tend to
resemble `MUX2 <http://www.tinymux.org/>`_, and its cousins
`PennMUSH <http://www.pennmush.org>`_,
`TinyMUSH <http://tinymush.sourceforge.net/>`_, and
`RhostMUSH <http://www.rhostmush.org/>`_. By default we emulate these
Tiny derivatives (MUX2, Penn, etc) in the user interface and building
commands. We believe these codebases have found a good way to do things
in terms of building and administration. We hope this will also make it
more familiar for new users coming from those communities to start using
Evennia.

However, Evennia has taken a completely different stance on how admins
extend and improve their games. Instead of implementing a special
in-game language (SoftCode), all game extension is done through Python
modules, like the rest of Evennia. This gives the admin practically
unlimited power to extend the game leveraging the full power of a mature
high level programming language. You can find a more elaborate
discussion about our take on MUX SoftCode `here <SoftCode.html>`_.

Documentation policy
--------------------

All the commands in the default command sets have their doc-strings
formatted on a similar form:

::

      """
      Short header

      Usage:
        key[/switches, if any] <mandatory args> [<optional args or types>]

      Switches:
        switch1    - description
        switch2    - description

      Examples:
        usage example and output

      Longer documentation detailing the command.

      """

The ``Switches`` and ``Examples`` headers can be skipped if not needed.
Here is the ``nick`` command as an example:

::

      """
      Define a personal alias/nick

        Usage:
          nick[/switches] <nickname> = [<string>]
          alias             ''

        Switches:
          object   - alias an object
          player   - alias a player
          clearall - clear all your aliases
          list     - show all defined aliases (also "nicks" works)

        Examples:
          nick hi = say Hello, I'm Sarah!
          nick/object tom = the tall man

        A 'nick' is a personal shortcut you create for your own use [...]

        """

For commands that *require arguments*, the policy is for it to return a
``Usage`` string if the command is entered without any arguments. So for
such commands, the Command body should contain something to the effect
of

::

      if not self.args:
          self.caller.msg("Usage: nick[/switches] <nickname> = [<string>]")
          return

WWMD - What Would MUX Do?
-------------------------

Our original policy for implementing the default commands was to look at
MUX2's implementation and base our command syntax on that. This means
that many default commands have roughly similar syntax and switches as
MUX commands. There are however many differences between the systems and
readability and usability has taken priority (frankly, the MUX syntax is
outright arcane in places). So the default command sets can be
considered to implement a "MUX-like" dialect - whereas the overall feel
is familiar, the details may differ considerably.
