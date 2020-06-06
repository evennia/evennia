# Manually Configuring Color


This is a small tutorial for customizing your character objects, using the example of letting users turn on and off ANSI color parsing as an example.  `@options NOCOLOR=True` will now do what this tutorial shows, but the tutorial subject can be applied to other toggles you may want, as well.

In the Building guide's [Colors](TextTags#coloured-text) page you can learn how to add color to your game by using special markup. Colors enhance the gaming experience, but not all users want color. Examples would be users working from clients that don't support color, or people with various seeing disabilities that rely on screen readers to play your game. Also, whereas Evennia normally automatically detects if a client supports color, it may get it wrong. Being able to turn it on manually if you know it **should** work could be a nice feature.

So here's how to allow those users to remove color. It basically means you implementing a simple configuration system for your characters. This is the basic sequence:

1. Define your own default character typeclass, inheriting from Evennia's default.
1. Set an attribute on the character to control markup on/off.
1. Set your custom character class to be the default for new accounts.
1. Overload the `msg()` method on the typeclass and change how it uses markup.
1. Create a custom command to allow users to change their setting.

## Setting up a custom Typeclass

Create a new module in `mygame/typeclasses` named, for example, `mycharacter.py`. Alternatively you can simply add a new class to 'mygamegame/typeclasses/characters.py'.

In your new module(or characters.py), create a new [Typeclass](../typeclasses) inheriting from `evennia.DefaultCharacter`. We will also import `evennia.utils.ansi`, which we will use later.

```python
    from evennia import Character
    from evennia.utils import ansi

    class ColorableCharacter(Character):
        at_object_creation(self):
            # set a color config value
            self.db.config_color = True
```

Above we set a simple config value as an [Attribute](../Attributes).

Let's make sure that new characters are created of this type. Edit your `mygame/server/conf/settings.py` file and add/change `BASE_CHARACTER_TYPECLASS` to point to your new character class. Observe that this will only affect *new* characters, not those already created. You have to convert already created characters to the new typeclass by using the `@typeclass` command (try on a secondary character first though, to test that everything works - you don't want to render your root user unusable!).

     @typeclass/reset/force Bob = mycharacter.ColorableCharacter

`@typeclass` changes Bob's typeclass and runs all its creation hooks all over again. The `/reset` switch clears all attributes and properties back to the default for the new typeclass - this is useful in this case to avoid ending up with an object having a "mixture" of properties from the old typeclass and the new one. `/force` might be needed if you edit the typeclass and want to update the object despite the actual typeclass name not having changed.

## Overload the `msg()` method

Next we need to overload the `msg()` method. What we want is to check the configuration value before calling the main function.  The original `msg` method call is seen in `evennia/objects/objects.py` and is called like this:

```python
    msg(self, text=None, from_obj=None, session=None, options=None, **kwargs):
```

As long as we define a method on our custom object with the same name and keep the same number of arguments/keywords we will overload the original. Here's how it could look:

```python
    class ColorableCharacter(Character):
        # [...]
        msg(self, text=None, from_obj=None, session=None, options=None,
            **kwargs):
            "our custom msg()"
            if self.db.config_color is not None: # this would mean it was not set
                if not self.db.config_color:
                    # remove the ANSI from the text
                    text = ansi.strip_ansi(text)
            super().msg(text=text, from_obj=from_obj,
                                               session=session, **kwargs)
```

Above we create a custom version of the `msg()` method. If the configuration Attribute is set, it strips the ANSI from the text it is about to send, and then calls the parent `msg()` as usual. You need to `@reload` before your changes become visible.

There we go! Just flip the attribute `config_color` to False and your users will not see any color. As superuser (assuming you use the Typeclass `ColorableCharacter`) you can test this with the `@py` command:

     @py self.db.config_color = False

## Custom color config command

For completeness, let's add a custom command so users can turn off their color display themselves if they want.

In `mygame/commands`, create a new file, call it for example `configcmds.py` (it's likely that you'll want to add other commands for configuration down the line). You can also copy/rename the command template.

```python
    from evennia import Command

    class CmdConfigColor(Command):
        """
        Configures your color

        Usage:
          @togglecolor on|off

        This turns ANSI-colors on/off.
        Default is on.
        """

        key = "@togglecolor"
        aliases = ["@setcolor"]

        def func(self):
            "implements the command"
            # first we must remove whitespace from the argument
            self.args = self.args.strip()
            if not self.args or not self.args in ("on", "off"):
                self.caller.msg("Usage: @setcolor on|off")
                return
            if self.args == "on":
                self.caller.db.config_color = True
                # send a message with a tiny bit of formatting, just for fun
                self.caller.msg("Color was turned |won|W.")
            else:
                self.caller.db.config_color = False
                self.caller.msg("Color was turned off.")
```

Lastly, we make this command available to the user by adding it to the default `CharacterCmdSet` in `mygame/commands/default_cmdsets.py` and reloading the server. Make sure you also import the command:

```python
from mygame.commands import configcmds
class CharacterCmdSet(default_cmds.CharacterCmdSet):
    # [...]
    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #

        # here is the only line that we edit
        self.add(configcmds.CmdConfigColor())
```

## More colors

Apart from ANSI colors, Evennia also supports **Xterm256** colors (See [Colors](../TextTags#colored-text)). The `msg()` method supports the `xterm256` keyword for manually activating/deactiving xterm256. It should be easy to expand the above example to allow players to customize xterm256 regardless of if Evennia thinks their client supports it or not.

To get a better understanding of how `msg()` works with keywords, you can try this as superuser:

    @py self.msg("|123Dark blue with xterm256, bright blue with ANSI", xterm256=True)
    @py self.msg("|gThis should be uncolored", nomarkup=True)
