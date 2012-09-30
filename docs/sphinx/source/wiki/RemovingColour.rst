Tutorial: Removing colour from your game
========================================

This is a small tutorial for customizing your character objects, using
the example of letting users turn on and off ansii colour parsing.

In the Building guide's `Colours <Colours.html>`_ page you can learn how
to add Colour to your game by using special markup. Colours enhance the
gaming experience, but not all users want colour. Examples would be
users working from clients that don't support colour, or people with
various seeing disabilities that rely on screen readers to play your
game.

So here's how to allow those users to remove colour. It basically means
you implementing a simple configuration system for your characters. This
is the basic sequence:

#. Define your own default character typeclass, inheriting from
   Evennia's default.
#. Set an attribute on the character to control markup on/off.
#. Set your custom character class to be the default for new players.
#. Overload the ``msg()`` method on the typeclass and change how it uses
   markup.
#. Create a custom command to allow users to change their setting.

Setting up a custom Typeclass
-----------------------------

Create a new module in ``game/gamesrc/objects`` named, for example,
``mycharacter.py``.

In your new module, create a new `typeclass <Typeclasses.html>`_
inheriting from ``ev.Character``.

::

    from ev import Character

    class ColourableCharacter(Character):
        at_object_creation(self):              
            # set a colour config value
            self.db.config_colour = True 

Above we set a simple config value as an `attribute <Attributes.html>`_.

Let's make sure that new characters are created of this type. Edit your
``game/settings.py`` file and add/change ``BASE_CHARACTER_TYPECLASS`` to
point to your new character class. Observe that this will only affect
*new* characters, not those already created. You have to convert already
created characters to the new typeclass by using the ``@typeclass``
command (try on a secondary character first though, to test that
everything works - you don't want to render your root user unusable!).

::

     @typeclass/reset/force Bob = mycharacter.ColourableCharacter

``@typeclass`` changes Bob's typeclass and runs all its creation hooks
all over again. The ``/reset`` switch clears all attributes and
properties back to the default for the new typeclass - this is useful in
this case to avoid ending up with an object having a "mixture" of
properties from the old typeclass and the new one. ``/force`` might be
needed if you edit the typeclass and want to update the object despite
the actual typeclass name not having changed.

Overload the \`msg()\` method
-----------------------------

Next we need to overload the ``msg()`` method. What we want is to check
the configuration value before calling the main function. The ``msg``
method call is found in
``src/objects/objects.py' and is called like this:  {{{ msg(message, from_obj=None, data=None) }}} As long as we define a method on our custom object with the same name and keep the same number of arguments/keywords we will overload the original. Here's how it could look: {{{ from ev import ansi  msg(self, message, from_obj=None, data=None):     "our custom msg()"     if not self.db.config_colour:         # if config_colour is False, strip ansi colour         message = ansi.parse_ansi(message, strip_ansi=True)     self.dbobj.msg(message, from_obj, data) }}} Above we create a custom version of the ``\ msg()\ `` method that cleans all ansi characters if the config value is not set to True. Once that's done, we pass it all on to the normal ``\ msg()\ `` on the database object (``\ ObjectDB\ ``) to do its thing. The colour strip is done by the ansi module itself by giving the ``\ strip\_ansi\ `` keyword to ``\ ansi.parse\_ansi\ ``.  Since we put this custom ``\ msg()\ `` in our typeclass ``\ ColourableCharacter\ ``, it will be searched for and called rather than the default method on ``\ ObjectDB\ `` (which we now instead call manually).  There we go! Just flip the attribute ``\ config\_colour\ `` to False and your users will not see any colour. As superuser (assuming you use the Typeclass ``\ ColourableCharacter\ ``) you can test this with the ``\ @py\ `` command:  {{{  @py self.db.config_colour = False }}}   ==Custom colour config command ==  For completeness, let's add a custom command so users can turn off their colour display themselves if they want.  In ``\ game/gamesrc/commands\ ``, reate a new file, call it for example  ``\ configcmds.py\ `` (it's likely that you'll want to add other commands for configuration down the line). You can also copy/rename the command template from ``\ game/gamesrc/commands/examples\ ``.  {{{ from ev import default_cmds class ConfigColourCmd(default_cmds.MuxCommand):     """     Configures your colour      Usage:       @setcolour on|off      This turns ansii-colours on/off.      Default is on.      """      key = "@setcolour"     aliases = ["@setcolor"]      def func(self):         "Implements the command"          if not self.args or not self.args in ("on", "off"):             self.caller.msg("Usage: @setcolour on|off")              return         if self.args == "on":             self.caller.db.config_colour = True         else:             self.caller.db.config_colour = False           self.caller.msg("Colour was turned %s." % self.args) }}} Lastly, we make this command available to the user by adding it to the default command set. Easiest is to add it to copy the template file from ``\ gamesrc/commands/examples\ ``, set ``\ settings.CMDSET\_DEFAULT\ `` to point to, and then add your module to the end of ``\ DefaultCmdSet\ `` in that new module.  {{{ from game.gamesrc.commands import configcmds class DefaultCmdSet(cmdset_default.DefaultCmdSet):         key = "DefaultMUX"          def at_cmdset_creation(self):                super(DefaultCmdSet, self).at_cmdset_creation()                 self.add(configcmds.ConfigColourCmd())              }}} When adding a new command to a cmdset like this you need to run the ``\ @reload\ ````
command (or reboot the server). From here on out, your users should be
able to turn on or off their colour as they please.
