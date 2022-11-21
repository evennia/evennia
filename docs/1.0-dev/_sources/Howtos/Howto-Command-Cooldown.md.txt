# Adding Command Cooldowns

    > hit goblin with sword 
    You strike goblin with the sword. It dodges! 
    > hit goblin with sword 
    You are off-balance and can't attack again yet.

Some types of games want to limit how often a command can be run. If a
character casts the spell *Firestorm*, you might not want them to spam that
command over and over. In an advanced combat system, a massive swing may
offer a chance of lots of damage at the cost of not being able to re-do it for
a while. 

Such effects are called *command cooldowns*.

```{sidebar}
The [Cooldown contrib](../Contribs/Contrib-Cooldowns.md) is a ready-made solution for command cooldowns. It is based on this howto and implements a [handler](Tutorial-Peristent-Handler) on the object to conveniently manage and store the cooldowns.
```
This howto exemplifies a very resource-efficient way to do cooldowns. A more
'active' way is to use asynchronous delays as in the [Command-Duration howto](./Howto-Command-Duration.md#blocking-commands) suggests.  The two howto's might be useful to combine if you want to echo some message to the user after the cooldown ends.

## An efficient cooldown

The idea is that when a [Command](../Components/Commands.md) runs, we store the time it runs. When it next runs, we check again the current time. The command is only allowed to run if enough time passed since now and the previous run. This is a _very_ efficient implementation that only checks on-demand.

```python
# in, say, mygame/commands/spells.py

import time
from evennia import default_cmds

class CmdSpellFirestorm(default_cmds.MuxCommand):
    """
    Spell - Firestorm

    Usage:
      cast firestorm <target>

    This will unleash a storm of flame. You can only release one
    firestorm every five minutes (assuming you have the mana).
    """
    key = "cast firestorm"
    rate_of_fire = 60 * 2  # 2 minutes

    def func(self):
        "Implement the spell"

        now = time.time()
        last_cast = caller.db.firestorm_last_cast  # could be None
        if last_cast and (now - last_cast < self.rate_of_fire):
            message = "You cannot cast this spell again yet."
            self.caller.msg(message)
            return

        # [the spell effect is implemented]

        # if the spell was successfully cast, store the casting time
        self.caller.db.firestorm_last_cast = now
```

We specify `rate_of_fire` and then just check for an [Attribute](../Components/Attributes.md) `firestorm_last_cast` on the `caller.` It is either `None` (because the spell was never cast before) or an timestamp representing the last time the spell was cast. 

### Non-Persistent cooldown

The above implementation will survive a reload. If you don't want that, you can just switch to let `firestorm_last_cast` be a [NAtrribute](../Components/Attributes.md#in-memory-attributes-nattributes) instead. For example: 

```python
        last_cast = caller.ndb.firestorm_last_cast
        # ... 
        self.caller.ndb.firestorm_last_cast = now 
```
That is, use `.ndb` instead of `.db`. Since a `NAttribute`s are purely in-memory, they can be faster to read and write to than an `Attribute`. So this can be more optimal if your intervals are short and need to change often. The drawback is that they'll reset if the server reloads. 

## Make a cooldown-aware command parent

If you have many different spells or other commands with cooldowns, you don't
want to have to add this code every time. Instead you can make a "cooldown
command mixin" class. A _mixin_ is a class that you can 'add' to another class
(via multiple inheritance) to give it some special ability. Here's an example
with persistent storage:

```python
# in, for example, mygame/commands/mixins.py

import time

class CooldownCommandMixin:

    rate_of_fire = 60
    cooldown_storage_key = "last_used"
    cooldown_storage_category = "cmd_cooldowns"

    def check_cooldown(self):
        last_time = self.caller.attributes.get(
            key=self.cooldown_storage_key,
            category=self.cooldown_storage_category)
        )
        return (time.time() - last_time) < self.rate_of_fire

    def update_cooldown(self):
        self.caller.attribute.add(
            key=self.cooldown_storage_key,
            value=time.time(),
            category=self.cooldown_storage_category

        )
```

This is meant to be mixed into a Command, so we assume `self.caller` exists.
We allow for setting what Attribute key/category to use to store the cooldown.

It also uses an Attribute-category to make sure what it stores is not mixed up
with other Attributes on the caller.

Here's how it's used:

```python
# in, say, mygame/commands/spells.py

from evennia import default_cmds
from .mixins import CooldownCommandMixin


class CmdSpellFirestorm(
        CooldownCommandMixin, default_cmds.MuxCommand):
    key = "cast firestorm"

    cooldown_storage_key = "firestorm_last_cast"
    rate_of_fire = 60 * 2

    def func(self):

        if not self.check_cooldown():
            self.caller.msg("You cannot cast this spell again yet.")
            return

        # [the spell effect happens]

        self.update_cooldown()

```

So the same as before, we have just hidden away the cooldown checks and you can
reuse this mixin for all your cooldowns.

### Command crossover

This example of cooldown-checking also works *between* commands. For example,
you can have all fire-related spells store the cooldown with the same
`cooldown_storage_key` (like `fire_spell_last_used`). That would mean casting
of *Firestorm* would block all other fire-related spells for a while.

Similarly, when you take that big sword swing, other types of attacks could
be blocked before you can recover your balance.
