Adding a new command - a step by step guide
===========================================

This is a quick first-time tutorial expanding on the
`Commands <Commands.html>`_ documentation.

Let's assume you have just downloaded Evennia and want to try to add a
new command. This is the fastest way to do it.

Tell Evennia where to look for custom commands/cmdsets
------------------------------------------------------

We will tell Evennia that you want to override the default cmdset with
new additional commands of your own.

#. Go to ``game/gamesrc/commands``.
#. There is a subfolder here named ``examples``. *Copy* the files
   ``examples/command.py`` and ``examples/cmdset.py`` to your current
   directory (game/gamesrc/commands). You can rename them as you please,
   but in this example we assume you don't.
#. Edit ``game/settings.py``, adding the following line:

    ``CMDSET_CHARACTER="game.gamesrc.commands.cmdset.CharacterCmdSet"``

Evennia will now look for default commands in the ``CharacterCmdSet``
class of your newly copied module. You only need to do this once.

Creating a custom command
-------------------------

#. Edit your newly copied ``game/gamesrc/commands/command.py``. This
   template already imports everything you need.
#. Create a new class in ``command.py`` that inherits from
   ``MuxCommand``. Let's call it ``CmdEcho`` in this example.
#. Set the class variable ``key`` to a good command name, like ``echo``.
#. Set the ``locks`` property on the command to a suitable
   [Locks#Defining\_locks lockstring]. If you are unsure, use
   ``"cmd:all()"``.
#. Give your class a useful *\_doc\_* string, this acts as the help
   entry for the command.
#. Define a class method ``func()`` that does stuff. Below is an example
   how it all could look.

::

    # file game/gamesrc/commands/command.py
    #[...]
    from ev import default_cmds
    class CmdEcho(default_cmds.MuxCommand):
        """
        Simple command example

        Usage: 
          echo <text>

        This command simply echoes text back to the caller.
        """

        key = "echo"
        locks = "cmd:all()"

        def func(self):
            "This actually does things" 
            if not self.args:
                self.caller.msg("You didn't enter anything!")           
            else:
                self.caller.msg("You gave the string: '%s'" % self.args)        

Adding the Command to a default Cmdset
--------------------------------------

The command is not available to use until it is part of a Command Set.
In this example we will go the easiest route and add it to the default
Character command set we already prepared.

#. Edit your recently copied ``game/gamesrc/commands/cmdset.py``
#. In this copied module you will find the ``DefaultCmdSet`` class
   already imported and prepared for you. Import your new command module
   here with ``from game.gamesrc.commands.command import CmdEcho``.
#. Add a line ``self.add(CmdEcho())`` to ``CharacterCmdSet``, in the
   ``at_cmdset_creation`` method (the template tells you where). This is
   approximately how it should look at this point:

::

    # file gamesrc/commands/cmdset.py
    #[...]
    from game.gamesrc.commands.command import CmdEcho
    #[...]
    class CharacterCmdSet(default_cmds.CharacterCmdSet):
        
        key = DefaultCharacter

        def at_cmdset_creation(self):

            # this first adds all default commands
            super(DefaultSet, self).at_cmdset_creation()

            # all commands added after this point will extend or 
            # overwrite the default commands.       
            self.add(CmdEcho())

#. Reboot/restart Evennia (``@reload`` from inside the game). You should
   now be able to use your new ``echo`` command from inside the game.
   Use ``help echo`` to see the documentation for the command.

If you have trouble, make sure to check the log for error messages
(probably due to syntax errors in your command definition).

Adding new commands to the default cmdset in the future now only
involves creating the function class and adding it to the cmdset in the
same place. If you want to overload existing default commands (such as
``look`` or ``get``), just add your new command with the same key as the
old one - it will overload the default one. Just remember that you must
``@reload`` the server before you see any changes.

See `Commands <Commands.html>`_ for many more details and possibilities
when defining Commands and using Cmdsets in various ways.

Adding the command to specific object types
-------------------------------------------

You do not *have* to expand the ``CharacterCmdSet``, it's just the
easiest example. The cmdset system is very generic. You can create your
own cmdsets and add them to objects as you please (just how to control
how they merge with the existing set is described in detail in the
[Commands#Command\_Sets Command Set documentation]).

::

    # file gamesrc/commands/cmdset.py
    #[...]
    from game.gamesrc.commands.command import CmdEcho
    #[...]
    class MyCmdSet(default_cmds.CmdSet):
        
        key = MyCmdSet

        def at_cmdset_creation(self):     
            self.add(CmdEcho())

Now you just need to add this to an object. To test things (as
superuser) you can do

::

     @py self.cmdset.add("cmdset.MyCmdSet")

This will add the cmdset (and the echo command) to yourself so you can
test it. This is not permanent though, if you do a ``@reload`` the
merger will be gone. You *can* add the ``permanent=True`` keyword to the
``cmdset.add`` call. This will however only make the new merged cmdset
permanent on that single object, not on other objects of that type,
which is usually what you want.

To make sure all new created objects get your new merged set, put the
``cmdset.add`` call in your custom `Typeclass <Typeclasses.html>`_'
``at_object_creation`` method:

::

    from ev import Object
    class MyObject(Object):
        
        def at_object_creation(self):
            "called when the object is first created"
            self.cmdset.add("cmdset.MyCmdSet")
           

All new objects of this typeclass will now start with this cmdset.

*Note:* An important caveat with this is that ``at_object_creation`` is
only called *once*, when the object is first created. This means that if
you already have existing objects in your databases using that
typeclass, they will not have been initiated the same way. There are
many ways to update them; since it's a one-time update you can usually
just simply loop through them. As superuser, try the following:

::

     @py [obj.cmdset.add("cmdset.MyCmdSet") for obj in 
          ev.managers.typeclass_search("game.gamesrc.objects.objects.mytypeclass.MyTypeClass"]

This goes through all objects in your database having the right
typeclass, adding the new cmdset to each. The good news is that you only
have to do this if you want to post-add cmdsets. If you just want to add
a new command, you can just add that command to the cmdset's
``at_cmdset_creation`` and @reload.
