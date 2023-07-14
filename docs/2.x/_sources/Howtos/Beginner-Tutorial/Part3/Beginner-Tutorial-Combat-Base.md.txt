# Combat base framework

Combat is core to many games. Exactly how it works is very game-dependent. In this lesson we will build a framework to implement two common flavors: 

- "Twitch-based" combat ([specific lesson here](./Beginner-Tutorial-Combat-Twitch.md)) means that you perform a combat action by entering a command, and after some delay (which may depend on your skills etc), the action happens. It's called 'twitch' because actions often happen fast enough that changing your strategy may involve some element of quick thinking and a 'twitchy trigger finger'. 
- "Turn-based" combat ([specific lesson here](./Beginner-Tutorial-Combat-Turnbased.md)) means that players input actions in clear turns. Timeout for entering/queuing your actions is often much longer than twitch-based style. Once everyone made their choice (or the timeout is reached), everyone's action happens all at once, after which the next turn starts. This style of combat requires less player reflexes. 

We will design a base combat system that supports both styles. 

- We need a `CombatHandler` to track the progress of combat. This will be a [Script](../../../Components/Scripts.md). Exactly how this works (and where it is stored) will be a bit different between Twitch- and Turnbased combat. We will create its common framework in this lesson.
- Combat are divided into _actions_. We want to be able to easily extend our combat with more possible actions. An action needs Python code to show what actually happens when the action is performed. We will define such code in `Action` classes. 
- We also need a way to describe a _specific instance_ of a given action. That is, when we do an "attack" action, we need at the minimum to know who is being attacked. For this will we use Python `dicts` that we will refer to as `action_dicts`.

## CombatHandler 

> Create a new module `evadventure/combat_base.py`

```{sidebar}
In [evennia/contrib/tutorials/evadventure/combat_base.py](evennia.contrib.tutorials.evadventure.combat_base) you'll find a complete implementation of the base combat module.
```
Our "Combat Handler" will handle the administration around combat. It needs to be _persistent_ (even is we reload the server your combat should keep going). 

Creating the CombatHandler is a little of a catch-22 - how it works depends on how Actions and Action-dicts look. But without having the CombatHandler, it's hard to know how to design Actions and Action-dicts. So we'll start with its general structure and fill out the details later in this lesson. 

Below, methods with `pass` will be filled out this lesson while those raising `NotImplementedError` will be different for Twitch/Turnbased combat and will be implemented in their respective lessons following this one.

```python 
# in evadventure/combat_base.py 

from evennia import DefaultScript


class CombatFailure(RuntimeError):
	"""If some error happens in combat"""
    pass


class EvAdventureCombatBaseHandler(DefaultSCript): 
    """ 
	This should be created when combat starts. It 'ticks' the combat 
	and tracks all sides of it.
	
    """
    # common for all types of combat

    action_classes = {}          # to fill in later 
    fallback_action_dict = {}

    @classmethod 
    def get_or_create_combathandler(cls, obj, **kwargs): 
        """ Get or create combathandler on `obj`.""" 
        pass

    def msg(self, message, combatant=None, broadcast=True, location=True): 
        """ 
        Send a message to all combatants.
		
        """
        pass  # TODO
     
    def get_combat_summary(self, combatant):
        """ 
        Get a nicely formatted 'battle report' of combat, from the 
        perspective of the combatant.
        
    	""" 
        pass  # TODO

	# implemented differently by Twitch- and Turnbased combat

    def get_sides(self, combatant):
        """ 
        Get who's still alive on the two sides of combat, as a 
        tuple `([allies], [enemies])` from the perspective of `combatant` 
	        (who is _not_ included in the `allies` list.
        
        """
        raise NotImplementedError 

    def give_advantage(self, recipient, target): 
        """ 
        Give advantage to recipient against target.
        
        """
        raise NotImplementedError 

    def give_disadvantage(self, recipient, target): 
        """
        Give disadvantage to recipient against target. 

        """
        raise NotImplementedError

    def has_advantage(self, combatant, target): 
        """ 
        Does combatant have advantage against target?
        
        """ 
        raise NotImplementedError 

    def has_disadvantage(self, combatant, target): 
        """ 
        Does combatant have disadvantage against target?
        
        """ 
        raise NotImplementedError

    def queue_action(self, combatant, action_dict):
        """ 
        Queue an action for the combatant by providing 
        action dict.
        
        """ 
        raise NotImplementedError

    def execute_next_action(self, combatant): 
        """ 
        Perform a combatant's next action.
        
        """ 
        raise NotImplementedError

    def start_combat(self): 
        """ 
        Start combat.
        
    	""" 
    	raise NotImplementedError
    
    def check_stop_combat(self): 
        """
        Check if the combat is over and if it should be stopped.
         
        """
        raise NotImplementedError 
        
    def stop_combat(self): 
        """ 
        Stop combat and do cleanup.
        
        """
        raise NotImplementedError


```

The Combat Handler is a [Script](../../../Components/Scripts.md). Scripts are typeclassed entities, which means that they are persistently stored in the database. Scripts can optionally be stored "on" other objects (such as on Characters or Rooms) or be 'global' without any such connection. While Scripts has an optional timer component, it is not active by default and Scripts are commonly used just as plain storage. Since Scripts don't have an in-game existence, they are great for storing data on 'systems' of all kinds, including our combat. 

Let's implement the generic methods we need.

### CombatHandler.get_or_create_combathandler 

A helper method for quickly getting the combathandler for an ongoing combat and combatant. 

We expect to create the script "on" an object (which one we don't know yet, but we expect it to be a typeclassed entity). 

```python
# in evadventure/combat_base.py

from evennia import create_script

# ... 

class EvAdventureCombatBaseHandler(DefaultScript): 

    # ... 

    @classmethod
    def get_or_create_combathandler(cls, obj, **kwargs):
        """
        Get or create a combathandler on `obj`.
    
        Args:
            obj (any): The Typeclassed entity to store this Script on. 
        Keyword Args:
            combathandler_key (str): Identifier for script. 'combathandler' by
                default.
            **kwargs: Extra arguments to the Script, if it is created.
    
        """
        if not obj:
            raise CombatFailure("Cannot start combat without a place to do it!")
    
        combathandler_key = kwargs.pop("key", "combathandler")
        combathandler = obj.ndb.combathandler
        if not combathandler or not combathandler.id:
            combathandler = obj.scripts.get(combathandler_key).first()
            if not combathandler:
                # have to create from scratch
                persistent = kwargs.pop("persistent", True)
                combathandler = create_script(
                    cls,
                    key=combathandler_key,
                    obj=obj,
                    persistent=persistent,
                    **kwargs,
                )
            obj.ndb.combathandler = combathandler
        return combathandler

	# ... 

```

This helper method uses `obj.scripts.get()` to find if the combat script already exists 'on' the provided `obj`. If not, it will create it using Evennia's [create_script](evennia.utils.create.create_script) function. For some extra speed we cache the handler as `obj.ndb.combathandler` The `.ndb.` (non-db) means that handler is cached only in memory. 

```{sidebar} Checking .id (or .pk)
When getting it from cache, we make sure to also check if the combathandler we got has a database `.id` that is not `None` (we could also check `.pk`, stands for "primary key") . If it's `None`, this means the database entity was deleted and we just got its cached python representation from memory - we need to recreate it.
```

`get_or_create_combathandler` is decorated to be a [classmethod](https://docs.python.org/3/library/functions.html#classmethod), meaning it should be used on the handler class directly (rather than on an _instance_ of said class). This makes sense because this method actually should return the new instance. 

As a class method we'll need to call this directly on the class, like this: 

```python
combathandler = EvAdventureCombatBaseHandler.get_or_create_combathandler(combatant)
```

The result will be a new handler _or_ one that was already defined.


### CombatHandler.msg

```python 
# in evadventure/combat_base.py 

# ... 

class EvAdventureCombatBaseHandler(DefaultScript): 
	# ... 

	def msg(self, message, combatant=None, broadcast=True, location=None):
        """
        Central place for sending messages to combatants. This allows
        for adding any combat-specific text-decoration in one place.

        Args:
            message (str): The message to send.
            combatant (Object): The 'You' in the message, if any.
            broadcast (bool): If `False`, `combatant` must be included and
                will be the only one to see the message. If `True`, send to
                everyone in the location.
            location (Object, optional): If given, use this as the location to
                send broadcast messages to. If not, use `self.obj` as that
                location.

        Notes:
            If `combatant` is given, use `$You/you()` markup to create
            a message that looks different depending on who sees it. Use
            `$You(combatant_key)` to refer to other combatants.

        """
        if not location:
            location = self.obj

        location_objs = location.contents

        exclude = []
        if not broadcast and combatant:
            exclude = [obj for obj in location_objs if obj is not combatant]

        location.msg_contents(
            message,
            exclude=exclude,
            from_obj=combatant,
            mapping={locobj.key: locobj for locobj in location_objs},
        )

	# ... 
```

```{sidebar}
The `self.obj` property of a Script is the entity on which the Script 'sits'. If set on a Character, `self.obj` will be that Character. If on a room, it'd be that room. For a global script, `self.obj` is `None`. 
```

We saw the `location.msg_contents()` method before in the [Weapon class of the Objects lesson](./Beginner-Tutorial-Objects.md#weapons). Its purpose is to take a string on the form `"$You() do stuff against $you(key)"` and make sure all sides see a string suitable just to them. Our `msg()` method will by default broadcast the message to everyone in the room. 
<div style="clear: right;"></div>


You'd use it like this:
```python
combathandler.msg(
	f"$You() $conj(throw) {item.key} at $you({target.key}).", 
	combatant=combatant, 
	location=combatant.location
)
```

If combatant is `Trickster`, `item.key` is "a colorful ball" and `target.key` is "Goblin", then 

The combatant would see: 

    You throw a colorful ball at Goblin.

The Goblin sees 

	Trickster throws a colorful ball at you.

Everyone else in the room sees 

	Trickster throws a colorful ball at Goblin.

### Combathandler.get_combat_summary 

We want to be able to show a nice summary of the current combat: 


```shell
                                        Goblin shaman (Perfect)
        Gregor (Hurt)                   Goblin brawler(Hurt)
        Bob (Perfect)         vs        Goblin grunt 1 (Hurt)
                                        Goblin grunt 2 (Perfect)
                                        Goblin grunt 3 (Wounded)
```

```{code-block} python
:linenos:
:emphasize-lines: 15,17,21,22,28,41

# in evadventure/combat_base.py

# ...

from evennia import EvTable

# ... 

class EvAdventureCombatBaseHandler(DefaultScript):

	# ... 

	def get_combat_summary(self, combatant):

        allies, enemies = self.get_sides(combatant)
        nallies, nenemies = len(allies), len(enemies)

        # prepare colors and hurt-levels
        allies = [f"{ally} ({ally.hurt_level})" for ally in allies]
        enemies = [f"{enemy} ({enemy.hurt_level})" for enemy in enemies]

        # the center column with the 'vs'
        vs_column = ["" for _ in range(max(nallies, nenemies))]
        vs_column[len(vs_column) // 2] = "|wvs|n"

        # the two allies / enemies columns should be centered vertically
        diff = abs(nallies - nenemies)
        top_empty = diff // 2
        bot_empty = diff - top_empty
        topfill = ["" for _ in range(top_empty)]
        botfill = ["" for _ in range(bot_empty)]

        if nallies >= nenemies:
            enemies = topfill + enemies + botfill
        else:
            allies = topfill + allies + botfill

        # make a table with three columns
        return evtable.EvTable(
            table=[
                evtable.EvColumn(*allies, align="l"),
                evtable.EvColumn(*vs_column, align="c"),
                evtable.EvColumn(*enemies, align="r"),
            ],
            border=None,
            maxwidth=78,
        )

	# ... 

```

This may look complex, but the complexity is only in figuring out how to organize three columns, especially how to to adjust to the two sides on each side of the `vs` are roughly vertically aligned. 

- **Line 15** : We make use of the `self.get_sides(combatant)` method which we haven't actually implemented yet. This is because turn-based and twitch-based combat will need different ways to find out what the sides are. The `allies` and `enemies` are lists. 
- **Line 17**: The `combatant` is not a part of the `allies` list (this is how we defined `get_sides` to work), so we insert it at the top of the list (so they show first on the left-hand side). 
- **Lines 21, 22**: We make use of the `.hurt_level` values of all living things (see the [LivingMixin of the Character lesson](./Beginner-Tutorial-Characters.md)).
- **Lines 28-39**: We determine how to vertically center the two sides by adding empty lines above and below the content.
- **Line 41**: The [Evtable](../../../Components/EvTable.md) is an Evennia utility for making, well, text tables. Once we are happy with the columns, we feed them to the table and let Evennia do the rest. It's worth to explore `EvTable` since it can help you create all sorts of nice layouts.

## Actions 

In EvAdventure we will only support a few common combat actions, mapping to the equivalent rolls and checks used in _Knave_. We will design our combat framework so that it's easy to expand with other actions later. 

- `hold` - The simplest action. You just lean back and do nothing. 
- `attack` - You attack a given `target` using your currently equipped weapon. This will become a roll of STR or WIS against the targets' ARMOR. 
- `stunt` - You make a 'stunt', which in roleplaying terms would mean you tripping your opponent, taunting or otherwise trying to gain the upper hand without hurting them. You can do this to give yourself (or an ally) _advantage_ against a `target` on the next action. You can also give a `target` _disadvantage_ against you or an ally for their next action.
- `use item` - You make use of a `Consumable` in your inventory. When used on yourself, it'd normally be something like a healing potion. If used on an enemy it could be a firebomb or a bottle of acid. 
- `wield` - You wield an item. Depending on what is being wielded, it will be wielded in different ways: A helmet will be placed on the head, a piece of armor on the chest. A sword will be wielded in one hand, a shield in another. A two-handed axe will use up two hands. Doing so will move whatever was there previously to the backpack. 
- `flee` - You run away/disengage. This action is only applicable in turn-based combat (in twitch-based combat you just move to another room to flee). We will thus wait to define this action until the [Turnbased combat lesson](./Beginner-Tutorial-Combat-Turnbased.md).

## Action dicts 

To pass around the details of an attack (the second point above), we will use a `dict`. A `dict` is simple and also easy to save in an `Attribute`. We'll call this the `action_dict` and here's what we need for each action. 

> You don't need to type these out anywhere, it's listed here for reference. We will use these dicts when calling `combathandler.queue_action(combatant, action_dict)`.

```python 
hold_action_dict = {
	"key": "hold"
}
attack_action_dict = { 
	"key": "attack",
	"target": <Character/NPC> 
}
stunt_action_dict = { 
    "key": "stunt",					
	"recipient": <Character/NPC>, # who gains advantage/disadvantage
	"target": <Character/NPC>,  # who the recipient gainst adv/dis against
	"advantage": bool,  # grant advantage or disadvantage?
	"stunt_type": Ability,   # Ability to use for the challenge
	"defense_type": Ability, # what Ability for recipient to defend with if we
                    	     # are trying to give disadvantage 
}
use_item_action_dict = { 
    "key": "use", 
    "item": <Object>
    "target": <Character/NPC/None> # if using item against someone else			   
}
wield_action_dict = { 
    "key": "wield",
    "item": <Object>					
}

# used only for the turnbased combat, so its Action will be defined there
flee_action_dict = { 
    "key": "flee"                   
}
```

Apart from the `stunt` action, these dicts are all pretty simple. The `key` identifes the action to perform and the other fields identifies the minimum things you need to know in order to resolve each action. 

We have not yet written the code to set these dicts, but we will assume that we know who is performing each of these actions. So if `Beowulf` attacks `Grendel`, Beowulf is not himself included in the attack dict: 

```python
attack_action_dict = { 
    "key": "attack",
    "target": Grendel
}
```

Let's explain the longest action dict, the `Stunt` action dict in more detail as well. In this example, The `Trickster` is performing a _Stunt_ in order to help his friend `Paladin` to gain an INT- _advantage_ against the `Goblin` (maybe the paladin is preparing to cast a spell of something). Since `Trickster` is doing the action, he's not showing up in the dict:

```python 
stunt_action_dict - { 
    "key": "stunt", 
    "recipient": Paladin,
    "target": Goblin,
    "advantage": True,
    "stunt_type": Ability.INT,
    "defense_type": Ability.INT,
}
```
```{sidebar}
In EvAdventure, we'll always set `stunt_type == defense_type` for simplicity. But you could also consider mixing things up so you could use DEX to confuse someone  and give them INT disadvantage, for example.
```
This should result in an INT vs INT based check between the `Trickster` and the `Goblin` (maybe the trickster is trying to confuse the goblin with some clever word play). If the `Trickster` wins, the `Paladin` gains advantage against the Goblin on the `Paladin`'s next action . 


## Action classes 

Once our `action_dict` identifies the particular action we should use, we need something that reads those keys/values and actually _performs_ the action.


```python 
# in evadventure/combat_base.py 

class CombatAction: 

    def __init__(self, combathandler, combatant, action_dict):
        self.combathandler = combathandler
        self.combatant = combatant

        for key, val in action_dict.items(); 
            if key.startswith("_"):
                setattr(self, key, val)
```

We will create a new instance of this class _every time an action is happening_. So we store some key things every action will need - we will need a reference to the common `combathandler` (which we will design in the next section), and to the `combatant` (the one performing this action). The `action_dict` is a dict matching the action we want to perform. 

The `setattr` Python standard function assigns the keys/values of the `action_dict` to be properties "on" this action. This is very convenient to use in other methods. So for the `stunt`  action, other methods could just access `self.key`, `self.recipient`, `self.target` and so on directly. 

```python 
# in evadventure/combat_base.py 

class CombatAction: 

    # ... 

    def msg(self, message, broadcast=True):
        "Send message to others in combat"
        self.combathandler.msg(message, combatant=self.combatant, broadcast=broadcast)

    def can_use(self): 
       """Return False if combatant can's use this action right now""" 
        return True 

    def execute(self): 
        """Does the actional action"""
        pass

    def post_execute(self):
        """Called after `execute`"""
        pass 
```

It's _very_ common to want to send messages to everyone in combat - you need to tell people they are getting attacked, if they get hurt and so on. So having a `msg` helper method on the action is convenient. We offload all the complexity to the combathandler.msg() method.


The `can_use`, `execute` and `post_execute` should all be called in a chain and we should make sure the `combathandler` calls them like this: 

```python
if action.can_use(): 
    action.execute() 
    action.post_execute()
```

### Hold Action 

```python
# in evadventure/combat_base.py 

# ... 

class CombatActionHold(CombatAction): 
    """ 
    Action that does nothing 
    
    action_dict = {
        "key": "hold"
    }
    
    """
```

Holding does nothing but it's cleaner to nevertheless have a separate class for it. We use the docstring to specify how its action-dict should look.

### Attack Action 

```python
# in evadventure/combat_base.py

# ... 

class CombatActionAttack(CombatAction):
     """
     A regular attack, using a wielded weapon.
 
     action-dict = {
             "key": "attack",
             "target": Character/Object
         }
 
     """
 
     def execute(self):
         attacker = self.combatant
         weapon = attacker.weapon
         target = self.target
 
         if weapon.at_pre_use(attacker, target):
             weapon.use(
                 attacker, target, advantage=self.combathandler.has_advantage(attacker, target)
             )
             weapon.at_post_use(attacker, target)
```

Refer to how we [designed Evadventure weapons](./Beginner-Tutorial-Objects.md#weapons) to understand what happens here - most of the work is performed by the weapon class - we just plug in the relevant arguments.

### Stunt Action

```python
# in evadventure/combat_base.py 

# ... 

class CombatActionStunt(CombatAction):
    """
    Perform a stunt the grants a beneficiary (can be self) advantage on their next action against a 
    target. Whenever performing a stunt that would affect another negatively (giving them
    disadvantage against an ally, or granting an advantage against them, we need to make a check
    first. We don't do a check if giving an advantage to an ally or ourselves.

    action_dict = {
           "key": "stunt",
           "recipient": Character/NPC,
           "target": Character/NPC,
           "advantage": bool,  # if False, it's a disadvantage
           "stunt_type": Ability,  # what ability (like STR, DEX etc) to use to perform this stunt. 
           "defense_type": Ability, # what ability to use to defend against (negative) effects of
            this stunt.
        }

    """

    def execute(self):
        combathandler = self.combathandler
        attacker = self.combatant
        recipient = self.recipient  # the one to receive the effect of the stunt
        target = self.target  # the affected by the stunt (can be the same as recipient/combatant)
        txt = ""

        if recipient == target:
            # grant another entity dis/advantage against themselves
            defender = recipient
        else:
            # recipient not same as target; who will defend depends on disadvantage or advantage
            # to give.
            defender = target if self.advantage else recipient

        # trying to give advantage to recipient against target. Target defends against caller
        is_success, _, txt = rules.dice.opposed_saving_throw(
            attacker,
            defender,
            attack_type=self.stunt_type,
            defense_type=self.defense_type,
            advantage=combathandler.has_advantage(attacker, defender),
            disadvantage=combathandler.has_disadvantage(attacker, defender),
        )

        self.msg(f"$You() $conj(attempt) stunt on $You({defender.key}). {txt}")

        # deal with results
        if is_success:
            if self.advantage:
                combathandler.give_advantage(recipient, target)
            else:
                combathandler.give_disadvantage(recipient, target)
            if recipient == self.combatant:
                self.msg(
                    f"$You() $conj(gain) {'advantage' if self.advantage else 'disadvantage'} "
                    f"against $You({target.key})!"
                )
            else:
                self.msg(
                    f"$You() $conj(cause) $You({recipient.key}) "
                    f"to gain {'advantage' if self.advantage else 'disadvantage'} "
                    f"against $You({target.key})!"
                )
            self.msg(
                "|yHaving succeeded, you hold back to plan your next move.|n [hold]",
                broadcast=False,
            )
        else:
            self.msg(f"$You({defender.key}) $conj(resist)! $You() $conj(fail) the stunt.")

```

The main action here is the call to the `rules.dice.opposed_saving_throw` to determine if the stunt succeeds. After that, most lines is about figuring out who should be given advantage/disadvantage and to communicate the result to the affected parties. 

Note that we make heavy use of the helper methods on the `combathandler` here, even those that are not yet implemented. As long as we pass the `action_dict` into the `combathandler`, the action doesn't actually care what happens next.

After we have performed a successful stunt, we queue the `combathandler.fallback_action_dict`. This is because stunts are meant to be one-off things are if we are repeating actions, it would not make sense to repeat the stunt over and over.

### Use Item Action 

```python
# in evadventure/combat_base.py 

# ... 

class CombatActionUseItem(CombatAction):
    """
    Use an item in combat. This is meant for one-off or limited-use items (so things like scrolls and potions, not swords and shields). If this is some sort of weapon or spell rune, we refer to the item to determine what to use for attack/defense rolls.

    action_dict = {
            "key": "use",
            "item": Object
            "target": Character/NPC/Object/None
        }

    """

    def execute(self):
        item = self.item
        user = self.combatant
        target = self.target

        if item.at_pre_use(user, target):
            item.use(
                user,
                target,
                advantage=self.combathandler.has_advantage(user, target),
                disadvantage=self.combathandler.has_disadvantage(user, target),
            )
            item.at_post_use(user, target)
```

See the [Consumable items in the Object lesson](./Beginner-Tutorial-Objects.md) to see how consumables work. Like with weapons, we offload all the logic to the item we use.

### Wield Action 

```python
# in evadventure/combat_base.py 

# ... 

class CombatActionWield(CombatAction):
    """
    Wield a new weapon (or spell) from your inventory. This will 
	    swap out the one you are currently wielding, if any.

    action_dict = {
            "key": "wield",
            "item": Object
        }

    """

    def execute(self):
        self.combatant.equipment.move(self.item)

```

We rely on the [Equipment handler](./Beginner-Tutorial-Equipment.md) we created to handle the swapping of items for us. Since it doesn't make sense to keep swapping over and over, we queue the fallback action after this one.

## Testing 

> Create a module `evadventure/tests/test_combat.py`.

```{sidebar}
See [evennia/contrib/tutorials/evadventure/tests/test_combat.py](evennia.contrib.tutorials.evadventure.tests.test_combat) for ready-made combat unit tests.
```

Unit testing the combat base classes can seem impossible because we have not yet implemented most of it. We can however get very far by the use of [Mocks](https://docs.python.org/3/library/unittest.mock.html). The idea of a Mock is that you _replace_ a piece of code with a dummy object (a 'mock') that can be called to return some specific value. 

For example, consider this following test of the `CombatHandler.get_combat_summary`. We can't just call this because it internally calls `.get_sides` which would raise a `NotImplementedError`. 

```{code-block} python 
:linenos:
:emphasize-lines: 25,32

# in evadventure/tests/test_combat.py 

from unittest.mock import Mock

from evennia.utils.test_resources import EvenniaTestCase
from evennia import create_object
from .. import combat_base
from ..rooms import EvAdventureRoom
from ..characters import EvAdventureCharacter


class TestEvAdventureCombatBaseHandler(EvenniaTestCase):

    def setUp(self): 

		self.location = create_object(EvAdventureRoom, key="testroom")
		self.combatant = create_object(EvAdventureCharacter, key="testchar")
		self.target = create_object(EvAdventureMob, key="testmonster")

        self.combathandler = combat_base.get_combat_summary(self.location)

    def test_get_combat_summary(self):

        # do the test from perspective of combatant
	    self.combathandler.get_sides = Mock(return_value=([], [self.target]))
        result = str(self.combathandler.get_combat_summary(self.combatant))
		self.assertEqual(
		    result, 
		    " testchar (Perfect)  vs  testmonster (Perfect)"
		)
		# test from the perspective of the monster 
		self.combathandler.get_sides = Mock(return_value=([], [self.combatant]))
		result = str(self.combathandler.get_combat_summary(self.target))
		self.assertEqual(
			result,
			" testmonster (Perfect)  vs  testchar (Perfect)"
		)
```

The interesting places are where we apply the mocks: 

- **Line 25** and **Line 32**: While `get_sides` is not implemented yet, we know what it is _supposed_ to return - a tuple of lists. So for the sake of the test, we _replace_ the `get_sides` method with a mock that when called will return something useful. 

With this kind of approach it's possible to fully test a system also when it's not 'complete' yet.

## Conclusions 

We have the core functionality we need for our combat system! In the following two lessons we will make use of these building blocks to create two styles of combat. 