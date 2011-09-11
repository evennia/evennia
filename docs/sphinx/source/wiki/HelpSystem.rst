*How to use Evennia's help system*

Help system
===========

An important part of Evennia is the online help system. This allows the
players and staff alike to learn how to use the game's commands as well
as other information pertinent to the game. The help system has many
different aspects, from the normal editing of help entries from inside
the game, to auto-generated help entries during code development using
the *auto-help* system.

Viewing the help database
-------------------------

The main command is ``help``.

::

    help [searchstring]

This will show a list of help entries, ordered after categories. You
will find two sections, *Command help entries* and *Other help entries*
(initially you will only have the first one). You can use help to get
more info about an entry; you can also give partial matches to get
suggestions. If you give category names you will only be shown the
topics in that category.

Command Auto-help system
------------------------

One important use of the help system is to teach the use of in-game
commands. Evennia offers a dynamically updated help system for all your
commands, new and old, known simply as the *auto-help* system. Only
commands that you can actually use are picked up by the auto-help
system. That means an admin will see a considerably larger mass of help
topics when using the ``help`` command than a normal player.

The auto-help system uses the ``__doc__`` strings of your command
definitions and formats this to a nice-looking help entry. This makes
for a very easy way to keep the help updated - just document your
commands well - updating the help system is just a ``@reload`` away.
There is no need to manually create help database entries for commands;
as long as you keep the docstrings updated your help will be dynamically
updated for you as well.

Example (from a module with command definitions):

::

    class CmdMyCmd(Command):
       """
       mycmd - my very own command   Usage: 
         mycmd[/switches] <args>   Switches:
         test - test the command
         run  - do something else   This is my own command that does things to you when you
       supply it with arguments.    """
       ...
       help_category = "Building"
        ...

So the text at the very top of the command class definition is the
class' ``__doc__``-string and what will be shown to users looking for
help. Try to use a consistent formatting between your help strings (for
example, all default commands have ``__doc__``-strings formatted in the
way seen above). You should also supply the ``help_category`` class
property if you can; this helps to group help entries together for
easier finding (if you don't supply a help\_category, "General" will be
assumed).

Other help entries (entries stored in database)
-----------------------------------------------

The *Other help* section you see when using the ``help`` command shows
all help entries that has been manually added to the database by staff.
Instead of being generated from the code by Evennia, these are stored in
the database using a model called *!HelpEntry*. HelpEntry topics are
intended for world-game-info, tutorials and other types of useful
information not directly tied to a command and covered by auto-help.

A help entry consists of four parts:

-  The *topic*. This is the name of the help entry. This is what players
   search for when they are looking for help. The topic can contain
   spaces.
-  The *help category*. Examples are *Administration*, *Building*,
   *Comms* or *General*. This is an overall grouping of similar help
   topics, used by the engine to give a better overview.
-  The *text* - the help text itself, of any length. This can also
   include *markup*, see below.
-  locks - a `lock definition <Locks.html>`_. Help commands check for
   access\_types ``examine`` and ``edit``.

You can create new help entries in code by using
``src.utils.create.create_help_entry()``:

::

    from src.utils import create 
    entry = create.create_help_entry("emote", 
                                     "Emoting is important because ...", 
                                     category="Roleplaying", locks="view:all()"):

From inside the game those with the right permissions can use the
``@sethelp`` command to add and modify help entries.

::

    > @sethelp/add emote = The emote command is ...

Using ``@sethelp`` you can add, delete and append text to existing
entries. By default new entries will go in the *General* help category.
You can change this using a different form of the ``@sethelp`` command:

::

    > @sethelp/add emote, Roleplaying = Emoting is important because ...

If the category *Roleplaying* did not exist it is created and will
appear in the help index. You can, finally, define a lock for the help
entry by following the category with a `lock definition <Locks.html>`_:

::

    > @sethelp/add emote, Roleplaying, view:all() = The emote command ...

