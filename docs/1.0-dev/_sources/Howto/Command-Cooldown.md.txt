# Command Cooldown


Some types of games want to limit how often a command can be run. If a
character casts the spell *Firestorm*, you might not want them to spam that
command over and over. Or in an advanced combat system, a massive swing may
offer a chance of lots of damage at the cost of not being able to re-do it for
a while. Such effects are called *cooldowns*. 

This page exemplifies a very resource-efficient way to do cooldowns. A more
'active' way is to use asynchronous delays as in the [command duration
tutorial](Command-Duration#Blocking-Commands), the two might be useful to
combine if you want to echo some message to the user after the cooldown ends. 

## Non-persistent cooldown

This little recipe will limit how often a particular command can be run. Since
Commands are class instances, and those are cached in memory, a command
instance will remember things you store on it. So just store the current time
of execution! Next time the command is run, it just needs to check if it has
that time stored, and compare it with the current time to see if a desired
delay has passed. 

```python
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
    locks = "cmd:isFireMage()"
        
    def func(self):
        "Implement the spell"
    
        # check cooldown (5 minute cooldown)
        now = time.time()   
        if hasattr(self, "lastcast") and \
                now - self.lastcast < 5 * 60:
            message = "You cannot cast this spell again yet."
            self.caller.msg(message)
            return 
    
        #[the spell effect is implemented]
    
        # if the spell was successfully cast, store the casting time
        self.lastcast = now 
```

We just check the `lastcast` flag, and update it if everything works out.
Simple and very effective since everything is just stored in memory. The
drawback of this simple scheme is that it's non-persistent. If you do
`@reload`, the cache is cleaned and all such ongoing cooldowns will be
forgotten. It is also limited only to this one command, other commands cannot
(easily) check for this value. 

## Persistent cooldown

This is essentially the same mechanism as the simple one above, except we use
the database to store the information which means the cooldown will survive a
server reload/reboot. Since commands themselves have no representation in the
database, you need to use the caster for the storage.

```python
    # inside the func() of CmdSpellFirestorm as above

    # check cooldown (5 minute cooldown)
            
    now = time.time()
    lastcast = self.caller.db.firestorm_lastcast 
            
    if lastcast and now - lastcast < 5 * 60:
        message = "You need to wait before casting this spell again."
        self.caller.msg(message)
        return      
      
    #[the spell effect is implemented]
    
    # if the spell was successfully cast, store the casting time
    self.caller.db.firestorm_lastcast = now
```

Since we are storing as an [Attribute](../Components/Attributes), we need to identify the
variable as `firestorm_lastcast` so we are sure we get the right one (we'll
    likely have other skills with cooldowns after all). But this method of
using cooldowns also has the advantage of working *between* commands - you can
for example let all fire-related spells check the same cooldown to make sure
the casting of *Firestorm* blocks all fire-related spells for a while. Or, in
the case of taking that big swing with the sword, this could now block all
other types of attacks for a while before the warrior can recover. 