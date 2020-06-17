# Turn based Combat System


This tutorial gives an example of a full, if simplified, combat system for Evennia. It was inspired
by the discussions held on the [mailing
list](https://groups.google.com/forum/#!msg/evennia/wnJNM2sXSfs/-dbLRrgWnYMJ).

## Overview of combat system concepts

Most MUDs will use some sort of combat system. There are several main variations:

- _Freeform_ - the simplest form of combat to implement, common to MUSH-style roleplaying games.
This means the system only supplies dice rollers or maybe commands to compare skills and spit out
the result. Dice rolls are done to resolve combat according to the rules of the game and to direct
the scene. A game master may be required to resolve rule disputes.
- _Twitch_ - This is the traditional MUD hack&slash style combat. In a twitch system there is often
no difference between your normal "move-around-and-explore mode" and the "combat mode". You enter an
attack command and the system will calculate if the attack hits and how much damage was caused.
Normally attack commands have some sort of timeout or notion of recovery/balance to reduce the
advantage of spamming or client scripting. Whereas the simplest systems just means entering `kill
<target>` over and over, more sophisticated twitch systems include anything from defensive stances
to tactical positioning.
- _Turn-based_ - a turn based system means that the system pauses to make sure all combatants can
choose their actions before continuing. In some systems, such entered actions happen immediately
(like twitch-based) whereas in others the resolution happens simultaneously at the end of the turn.
The disadvantage of a turn-based system is that the game must switch to a "combat mode" and one also
needs to take special care of how to handle new combatants and the passage of time. The advantage is
that success is not dependent on typing speed or of setting up quick client macros. This potentially
allows for emoting as part of combat which is an advantage for roleplay-heavy games.

To implement a freeform combat system all you need is a dice roller and a roleplaying rulebook. See
[contrib/dice.py](https://github.com/evennia/evennia/blob/master/evennia/contrib/dice.py) for an
example dice roller. To implement at twitch-based system you basically need a few combat
[commands](Commands), possibly ones with a [cooldown](Command-Cooldown). You also need a [game rule
module](Implementing-a-game-rule-system) that makes use of it. We will focus on the turn-based
variety here.

## Tutorial overview

This tutorial will implement the slightly more complex turn-based combat system. Our example has the
following properties:

- Combat is initiated with `attack <target>`, this initiates the combat mode.
- Characters may join an ongoing battle using `attack <target>` against a character already in
combat.
- Each turn every combating character will get to enter two commands, their internal order matters
and they are compared one-to-one in the order given by each combatant.  Use of `say` and `pose` is
free.
- The commands are (in our example) simple; they can either `hit <target>`, `feint <target>` or
`parry <target>`. They can also `defend`, a generic passive defense. Finally they may choose to
`disengage/flee`.
- When attacking we use a classic [rock-paper-scissors](https://en.wikipedia.org/wiki/Rock-paper-
scissors) mechanic to determine success: `hit` defeats `feint`, which defeats `parry` which defeats
`hit`. `defend` is a general passive action that has a percentage chance to win against `hit`
(only).
- `disengage/flee` must be entered two times in a row and will only succeed if there is no `hit`
against them in that time. If so they will leave combat mode.
- Once every player has entered two commands, all commands are resolved in order and the result is
reported. A new turn then begins.
- If players are too slow the turn will time out and any unset commands will be set to `defend`. 

For creating the combat system we will need the following components:

- A combat handler. This is the main mechanic of the system. This is a [Script](Scripts) object
created for each combat.  It is not assigned to a specific object but is shared by the combating
characters and handles all the combat information. Since Scripts are database entities it also means
that the combat will not be affected by a server reload.
- A combat [command set](Command-Sets) with the relevant commands needed for combat, such as the
various attack/defend options and the `flee/disengage` command to leave the combat mode.
- A rule resolution system. The basics of making such a module is described in the [rule system
tutorial](Implementing-a-game-rule-system). We will only sketch such a module here for our end-turn
combat resolution.
- An `attack` [command](Commands) for initiating the combat mode. This is added to the default
command set. It will create the combat handler and add the character(s) to it. It will also assign
the combat command set to the characters.

## The combat handler

The _combat handler_ is implemented as a stand-alone [Script](Scripts).  This Script is created when
the first Character decides to attack another and is deleted when no one is fighting any more. Each
handler represents one instance of combat and one combat only. Each instance of combat can hold any
number of characters but each character can only be part of one combat at a time (a player would
need to disengage from the first combat before they could join another).

The reason we don't store this Script "on" any specific character is because any character may leave
the combat at any time. Instead the script holds references to all characters involved in the
combat.  Vice-versa, all characters holds a back-reference to the current combat handler. While we
don't use this very much here this might allow the combat commands on the characters to access and
update the combat handler state directly.

_Note: Another way to implement a combat handler would be to use a normal Python object and handle
time-keeping with the [TickerHandler](TickerHandler). This would require either adding custom hook
methods on the character or to implement a custom child of the TickerHandler class to track turns.
Whereas the TickerHandler is easy to use, a Script offers more power in this case._

Here is a basic combat handler. Assuming our game folder is named `mygame`, we store it in
`mygame/typeclasses/combat_handler.py`:

```python
# mygame/typeclasses/combat_handler.py

import random
from evennia import DefaultScript
from world.rules import resolve_combat

class CombatHandler(DefaultScript):
    """
    This implements the combat handler.
    """

    # standard Script hooks 

    def at_script_creation(self):
        "Called when script is first created"

        self.key = "combat_handler_%i" % random.randint(1, 1000)
        self.desc = "handles combat"
        self.interval = 60 * 2  # two minute timeout
        self.start_delay = True
        self.persistent = True   

        # store all combatants
        self.db.characters = {}
        # store all actions for each turn
        self.db.turn_actions = {}
        # number of actions entered per combatant
        self.db.action_count = {}

    def _init_character(self, character):
        """
        This initializes handler back-reference 
        and combat cmdset on a character
        """
        character.ndb.combat_handler = self
        character.cmdset.add("commands.combat.CombatCmdSet")

    def _cleanup_character(self, character):
        """
        Remove character from handler and clean 
        it of the back-reference and cmdset
        """
        dbref = character.id 
        del self.db.characters[dbref]
        del self.db.turn_actions[dbref]
        del self.db.action_count[dbref]        
        del character.ndb.combat_handler
        character.cmdset.delete("commands.combat.CombatCmdSet")

    def at_start(self):
        """
        This is called on first start but also when the script is restarted
        after a server reboot. We need to re-assign this combat handler to 
        all characters as well as re-assign the cmdset.
        """
        for character in self.db.characters.values():
            self._init_character(character)

    def at_stop(self):
        "Called just before the script is stopped/destroyed."
        for character in list(self.db.characters.values()):
            # note: the list() call above disconnects list from database
            self._cleanup_character(character)

    def at_repeat(self):
        """
        This is called every self.interval seconds (turn timeout) or 
        when force_repeat is called (because everyone has entered their 
        commands). We know this by checking the existence of the
        `normal_turn_end` NAttribute, set just before calling 
        force_repeat.
        
        """
        if self.ndb.normal_turn_end:
            # we get here because the turn ended normally
            # (force_repeat was called) - no msg output
            del self.ndb.normal_turn_end
        else:        
            # turn timeout
            self.msg_all("Turn timer timed out. Continuing.")
        self.end_turn()

    # Combat-handler methods

    def add_character(self, character):
        "Add combatant to handler"
        dbref = character.id
        self.db.characters[dbref] = character        
        self.db.action_count[dbref] = 0
        self.db.turn_actions[dbref] = [("defend", character, None),
                                       ("defend", character, None)]
        # set up back-reference
        self._init_character(character)
       
    def remove_character(self, character):
        "Remove combatant from handler"
        if character.id in self.db.characters:
            self._cleanup_character(character)
        if not self.db.characters:
            # if no more characters in battle, kill this handler
            self.stop()

    def msg_all(self, message):
        "Send message to all combatants"
        for character in self.db.characters.values():
            character.msg(message)

    def add_action(self, action, character, target):
        """
        Called by combat commands to register an action with the handler.

         action - string identifying the action, like "hit" or "parry"
         character - the character performing the action
         target - the target character or None

        actions are stored in a dictionary keyed to each character, each
        of which holds a list of max 2 actions. An action is stored as
        a tuple (character, action, target). 
        """
        dbref = character.id
        count = self.db.action_count[dbref]
        if 0 <= count <= 1: # only allow 2 actions            
            self.db.turn_actions[dbref][count] = (action, character, target)
        else:        
            # report if we already used too many actions
            return False
        self.db.action_count[dbref] += 1
        return True

    def check_end_turn(self):
        """
        Called by the command to eventually trigger 
        the resolution of the turn. We check if everyone
        has added all their actions; if so we call force the
        script to repeat immediately (which will call
        `self.at_repeat()` while resetting all timers). 
        """
        if all(count > 1 for count in self.db.action_count.values()):
            self.ndb.normal_turn_end = True
            self.force_repeat() 

    def end_turn(self):
        """
        This resolves all actions by calling the rules module. 
        It then resets everything and starts the next turn. It
        is called by at_repeat().
        """        
        resolve_combat(self, self.db.turn_actions)

        if len(self.db.characters) < 2:
            # less than 2 characters in battle, kill this handler
            self.msg_all("Combat has ended")
            self.stop()
        else:
            # reset counters before next turn
            for character in self.db.characters.values():
                self.db.characters[character.id] = character
                self.db.action_count[character.id] = 0
                self.db.turn_actions[character.id] = [("defend", character, None),
                                                  ("defend", character, None)]
            self.msg_all("Next turn begins ...")
```

This implements all the useful properties of our combat handler. This Script will survive a reboot
and will automatically re-assert itself when it comes back online. Even the current state of the
combat should be unaffected since it is saved in Attributes at every turn. An important part to note
is the use of the Script's standard `at_repeat` hook and the `force_repeat` method to end each turn.
This allows for everything to go through the same mechanisms with minimal repetition of code.

What is not present in this handler is a way for players to view the actions they set or to change
their actions once they have been added (but before the last one has added theirs). We leave this as
an exercise.

## Combat commands

Our combat commands - the commands that are to be available to us during the combat - are (in our
example) very simple. In a full implementation the commands available might be determined by the
weapon(s) held by the player or by which skills they know.

We create them in `mygame/commands/combat.py`.

```python
# mygame/commands/combat.py

from evennia import Command

class CmdHit(Command):
    """
    hit an enemy

    Usage:
      hit <target>

    Strikes the given enemy with your current weapon.
    """
    key = "hit"
    aliases = ["strike", "slash"]
    help_category = "combat"

    def func(self):
        "Implements the command"
        if not self.args:
            self.caller.msg("Usage: hit <target>")
            return 
        target = self.caller.search(self.args)
        if not target:
            return
        ok = self.caller.ndb.combat_handler.add_action("hit", 
                                                       self.caller, 
                                                       target) 
        if ok:
            self.caller.msg("You add 'hit' to the combat queue")
        else:
            self.caller.msg("You can only queue two actions per turn!")
 
        # tell the handler to check if turn is over
        self.caller.ndb.combat_handler.check_end_turn()
```

The other commands `CmdParry`, `CmdFeint`, `CmdDefend` and `CmdDisengage` look basically the same.
We should also add a custom `help` command to list all the available combat commands and what they
do.

We just need to put them all in a cmdset. We do this at the end of the same module:

```python
# mygame/commands/combat.py

from evennia import CmdSet
from evennia import default_cmds

class CombatCmdSet(CmdSet):
    key = "combat_cmdset"
    mergetype = "Replace"
    priority = 10 
    no_exits = True

    def at_cmdset_creation(self):
        self.add(CmdHit())
        self.add(CmdParry())
        self.add(CmdFeint())
        self.add(CmdDefend())
        self.add(CmdDisengage())    
        self.add(CmdHelp())
        self.add(default_cmds.CmdPose())
        self.add(default_cmds.CmdSay())
```

## Rules module

A general way to implement a rule module is found in the [rule system tutorial](Implementing-a-game-
rule-system). Proper resolution would likely require us to change our Characters to store things
like strength, weapon skills and so on. So for this example we will settle for a very simplistic
rock-paper-scissors kind of setup with some randomness thrown in. We will not deal with damage here
but just announce the results of each turn. In a real system the Character objects would hold stats
to affect their skills, their chosen weapon affect the choices, they would be able to lose health
etc.

Within each turn, there are "sub-turns", each consisting of one action per character. The actions
within each sub-turn happens simultaneously and only once they have all been resolved we move on to
the next sub-turn (or end the full turn).

*Note: In our simple example the sub-turns don't affect each other (except for `disengage/flee`),
nor do any effects carry over between turns. The real power of a turn-based system would be to add
real tactical possibilities here though; For example if your hit got parried you could be out of
balance and your next action would be at a disadvantage. A successful feint would open up for a
subsequent attack and so on ...*

Our rock-paper-scissor setup works like this: 

- `hit` beats `feint` and `flee/disengage`. It has a random chance to fail against `defend`. 
- `parry` beats `hit`.
- `feint` beats `parry` and is then counted as a `hit`.
- `defend` does nothing but has a chance to beat `hit`.
- `flee/disengage` must succeed two times in a row (i.e. not beaten by a `hit` once during the
turn). If so the character leaves combat.


```python
# mygame/world/rules.py

import random

# messages 

def resolve_combat(combat_handler, actiondict):
    """
    This is called by the combat handler
    actiondict is a dictionary with a list of two actions
    for each character:
    {char.id:[(action1, char, target), (action2, char, target)], ...}
    """
    flee = {} # track number of flee commands per character
    for isub in range(2):
        # loop over sub-turns
        messages = []
        for subturn in (sub[isub] for sub in actiondict.values()):
            # for each character, resolve the sub-turn
            action, char, target = subturn
            if target:
                taction, tchar, ttarget = actiondict[target.id][isub]
            if action == "hit":
                if taction == "parry" and ttarget == char:
                    msg = "%s tries to hit %s, but %s parries the attack!"
                    messages.append(msg % (char, tchar, tchar))
                elif taction == "defend" and random.random() < 0.5:
                    msg = "%s defends against the attack by %s."
                    messages.append(msg % (tchar, char))
                elif taction == "flee":
                    msg = "%s stops %s from disengaging, with a hit!"
                    flee[tchar] = -2
                    messages.append(msg % (char, tchar))
                else:
                    msg = "%s hits %s, bypassing their %s!"
                    messages.append(msg % (char, tchar, taction))
            elif action == "parry":
                if taction == "hit":
                    msg = "%s parries the attack by %s."
                    messages.append(msg % (char, tchar))
                elif taction == "feint":
                    msg = "%s tries to parry, but %s feints and hits!"
                    messages.append(msg % (char, tchar))
                else:
                    msg = "%s parries to no avail."
                    messages.append(msg % char)
            elif action == "feint":
                if taction == "parry":
                    msg = "%s feints past %s's parry, landing a hit!"
                    messages.append(msg % (char, tchar))
                elif taction == "hit":
                    msg = "%s feints but is defeated by %s hit!"
                    messages.append(msg % (char, tchar))
                else:
                    msg = "%s feints to no avail."
                    messages.append(msg % char)
            elif action == "defend":
                msg = "%s defends."
                messages.append(msg % char)
            elif action == "flee":
                if char in flee:
                    flee[char] += 1
                else:
                    flee[char] = 1
                    msg = "%s tries to disengage (two subsequent turns needed)"
                    messages.append(msg % char)

        # echo results of each subturn
        combat_handler.msg_all("\n".join(messages))

    # at the end of both sub-turns, test if anyone fled
    msg = "%s withdraws from combat."
    for (char, fleevalue) in flee.items():
        if fleevalue == 2:
            combat_handler.msg_all(msg % char)
            combat_handler.remove_character(char)
```

To make it simple (and to save space), this example rule module actually resolves each interchange
twice - first when it gets to each character and then again when handling the target. Also, since we
use the combat handler's `msg_all` method here, the system will get pretty spammy. To clean it up,
one could imagine tracking all the possible interactions to make sure each pair is only handled and
reported once.

## Combat initiator command

This is the last component we need, a command to initiate combat. This will tie everything together.
We store this with the other combat commands.

```python
# mygame/commands/combat.py

from evennia import create_script

class CmdAttack(Command):
    """
    initiates combat

    Usage:
      attack <target>

    This will initiate combat with <target>. If <target is
    already in combat, you will join the combat. 
    """
    key = "attack"
    help_category = "General"

    def func(self):
        "Handle command"
        if not self.args:
            self.caller.msg("Usage: attack <target>")            
            return
        target = self.caller.search(self.args)
        if not target:
            return
        # set up combat
        if target.ndb.combat_handler:
            # target is already in combat - join it            
            target.ndb.combat_handler.add_character(self.caller)
            target.ndb.combat_handler.msg_all("%s joins combat!" % self.caller)
        else:
            # create a new combat handler
            chandler = create_script("combat_handler.CombatHandler")
            chandler.add_character(self.caller)
            chandler.add_character(target)
            self.caller.msg("You attack %s! You are in combat." % target)
            target.msg("%s attacks you! You are in combat." % self.caller)       
```

The `attack` command will not go into the combat cmdset but rather into the default cmdset. See e.g.
the [Adding Command Tutorial](Adding-Command-Tutorial) if you are unsure about how to do this.

## Expanding the example

At this point you should have a simple but flexible turn-based combat system. We have taken several
shortcuts and simplifications in this example. The output to the players is likely too verbose
during combat and too limited when it comes to informing about things surrounding it. Methods for
changing your commands or list them, view who is in combat etc is likely needed - this will require
play testing for each game and style. There is also currently no information displayed for other
people happening to be in the same room as the combat - some less detailed information should
probably be echoed to the room to
show others what's going on.