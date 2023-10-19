# Cooldowns

Contribution by owllex, 2021

Cooldowns are used to model rate-limited actions, like how often a
character can perform a given action; until a certain time has passed their
command can not be used again. This contrib provides a simple cooldown
handler that can be attached to any typeclass. A cooldown is a lightweight persistent
asynchronous timer that you can query to see if a certain time has yet passed.

Cooldowns are completely asynchronous and must be queried to know their
state. They do not fire callbacks, so are not a good fit for use cases
where something needs to happen on a specific schedule (use delay or
a TickerHandler for that instead).

See also the evennia [howto](../Howtos/Howto-Command-Cooldown.md) for more information
about the concept.

## Installation

To use, simply add the following property to the typeclass definition of any
object type that you want to support cooldowns. It will expose a new `cooldowns`
property that persists data to the object's attribute storage. You can set this
on your base `Object` typeclass to enable cooldown tracking on every kind of
object, or just put it on your `Character` typeclass.

By default the CooldownHandler will use the `cooldowns` property, but you can
customize this if desired by passing a different value for the `db_attribute`
parameter.

```python
from evennia.contrib.game_systems.cooldowns import CooldownHandler
from evennia.utils.utils import lazy_property

@lazy_property
def cooldowns(self):
    return CooldownHandler(self, db_attribute="cooldowns")
```

## Example

Assuming you've installed cooldowns on your Character typeclasses, you can use a
cooldown to limit how often you can perform a command. The following code
snippet will limit the use of a Power Attack command to once every 10 seconds
per character.

```python
class PowerAttack(Command):
    def func(self):
        if self.caller.cooldowns.ready("power attack"):
            self.do_power_attack()
            self.caller.cooldowns.add("power attack", 10)
        else:
            self.caller.msg("That's not ready yet!")

```


----

<small>This document page is generated from `evennia/contrib/game_systems/cooldowns/README.md`. Changes to this
file will be overwritten, so edit that file rather than this one.</small>
