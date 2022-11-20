# Command Cooldown

Some types of games want to limit how often a command can be run. If a
character casts the spell *Firestorm*, you might not want them to spam that
command over and over. Or in an advanced combat system, a massive swing may
offer a chance of lots of damage at the cost of not being able to re-do it for
a while. Such effects are called *cooldowns*.

This page exemplifies a very resource-efficient way to do cooldowns. A more
'active' way is to use asynchronous delays as in the [](Howto-Command-Duration.md#blocking-commands), the two might be useful to
combine if you want to echo some message to the user after the cooldown ends.

## The Cooldown Contrib

The [Cooldown contrib](../Contribs/Contrib-Cooldowns.md) is a ready-made solution for
command cooldowns you can use. It implements a _handler_ on the object to
conveniently manage and store the cooldowns in a similar manner exemplified in
this tutorial.

## Non-persistent cooldown

This little recipe will limit how often a particular command can be run. Since
Commands are class instances, and those are cached in memory, a command
instance will remember things you store on it. So just store the current time
of execution! Next time the command is run, it just needs to check if it has
that time stored, and compare it with the current time to see if a desired
delay has passed.

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
        last_cast = caller.ndb.firestorm_last_cast  # could be None
        if last_cast and (now - last_cast < self.rate_of_fire):
            message = "You cannot cast this spell again yet."
            self.caller.msg(message)
            return

        # [the spell effect is implemented]

        # if the spell was successfully cast, store the casting time
        self.caller.ndb.firestorm_last_cast = now
```

We specify `rate_of_fire` and then just check for a NAtrribute
`firestorm_last_cast` and update it if everything works out.

Simple and very effective since everything is just stored in memory. The
drawback of this simple scheme is that it's non-persistent. If you do
`reload`, the cache is cleaned and all such ongoing cooldowns will be
forgotten.

## Persistent cooldown

To make a cooldown _persistent_ (so it survives a server reload), just
use the same technique, but use [Attributes](../Components/Attributes.md) (that is, `.db` instead
of `.ndb` storage to save the last-cast time.

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

Similarly, when you take that that big sword swing, other types of attacks could
be blocked before you can recover your balance.
