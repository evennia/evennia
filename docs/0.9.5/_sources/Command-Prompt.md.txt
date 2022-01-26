# Command Prompt


A *prompt* is quite common in MUDs. The prompt display useful details about your character that you
are likely to want to keep tabs on at all times, such as health, magical power etc. It might also
show things like in-game time, weather and so on. Many modern MUD clients (including Evennia's own
webclient) allows for identifying the prompt and have it appear in a correct location (usually just
above the input line). Usually it will remain like that until it is explicitly updated.

## Sending a prompt

A prompt is sent using the  `prompt` keyword to the `msg()` method on objects. The prompt will be
sent without any line breaks.

```python
    self.msg(prompt="HP: 5, MP: 2, SP: 8")
```
You can combine the sending of normal text with the sending (updating of the prompt):

```python
    self.msg("This is a text", prompt="This is a prompt")
```

You can update the prompt on demand, this is normally done using [OOB](./OOB.md)-tracking of the relevant
Attributes (like the character's health). You could also make sure that attacking commands update
the prompt when they cause a change in health, for example.

Here is a simple example of the prompt sent/updated from a command class:

```python
    from evennia import Command

    class CmdDiagnose(Command):
        """
        see how hurt your are

        Usage:
          diagnose [target]

        This will give an estimate of the target's health. Also
        the target's prompt will be updated.
        """
        key = "diagnose"
        
        def func(self):
            if not self.args:
                target = self.caller
            else:
                target = self.search(self.args)
                if not target:
                    return
            # try to get health, mana and stamina
            hp = target.db.hp
            mp = target.db.mp
            sp = target.db.sp

            if None in (hp, mp, sp):
                # Attributes not defined
                self.caller.msg("Not a valid target!")
                return
             
            text = "You diagnose %s as having " \
                   "%i health, %i mana and %i stamina." \
                   % (hp, mp, sp)
            prompt = "%i HP, %i MP, %i SP" % (hp, mp, sp)
            self.caller.msg(text, prompt=prompt)
```
## A prompt sent with every command

The prompt sent as described above uses a standard telnet instruction (the Evennia web client gets a
special flag). Most MUD telnet clients will understand and allow users to catch this and keep the
prompt in place until it updates. So *in principle* you'd not need to update the prompt every
command.

However, with a varying user base it can be unclear which clients are used and which skill level the
users have. So sending a prompt with every command is a safe catch-all. You don't need to manually
go in and edit every command you have though. Instead you edit the base command class for your
custom commands (like `MuxCommand` in your `mygame/commands/command.py` folder) and overload the
`at_post_cmd()` hook. This hook is always called *after* the main `func()` method of the Command.

```python
from evennia import default_cmds

class MuxCommand(default_cmds.MuxCommand):
    # ...
    def at_post_cmd(self):
        "called after self.func()."
        caller = self.caller
        prompt = "%i HP, %i MP, %i SP" % (caller.db.hp,
                                          caller.db.mp,
                                          caller.db.sp)
        caller.msg(prompt=prompt)

```

### Modifying default commands

If you want to add something small like this to Evennia's default commands without modifying them
directly the easiest way is to just wrap those with a multiple inheritance to your own base class:

```python
# in (for example) mygame/commands/mycommands.py

from evennia import default_cmds
# our custom MuxCommand with at_post_cmd hook
from commands.command import MuxCommand

# overloading the look command
class CmdLook(default_cmds.CmdLook, MuxCommand):
    pass
```

The result of this is that the hooks from your custom `MuxCommand` will be mixed into the default
`CmdLook` through multiple inheritance. Next you just add this to your default command set:

```python
# in mygame/commands/default_cmdsets.py

from evennia import default_cmds
from commands import mycommands

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    # ...
    def at_cmdset_creation(self):
        # ...
        self.add(mycommands.CmdLook())
```

This will automatically replace the default `look` command in your game with your own version.