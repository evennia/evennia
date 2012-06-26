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

WWMD - What Would MUX Do?
-------------------------

Our policy for implementing the default commands is as follows - we tend
to look at MUX2's implementation before contriving one of our own. This
comes with a caveat though - there are many cases where this is
impossible without sacrificing the usability and utility of the
codebase. In those cases, differences in implementation as well as
command syntax is to be expected. Evennia is *not* MUX - we handle all
underlying systems very differently and don't use
`SoftCode <SoftCode.html>`_. The WWMD policy is only applied to the
default commands, not to any other programming paradigms in the
codebase.

If you are an Evennia codebase developer, consider activating
``IMPORT_MUX_HELP`` in your ``settings.py`` file. This will import a
copy of the MUX2 help database and might come in handy when it comes to
adding/implementing new default commands. If you must deviate from
MUX2's implementation of something, make sure to document it extensively
in the command's docstring.
