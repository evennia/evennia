# Non-Player-Characters

```{sidebar} vNPCs
You should usually avoid creating hundreds of NPC objects to populate your 'busy town' - in a text game so many NPCs will just spam the screen and annoy your players. Since this is a text game, you can usually get away with using _vNPcs_ - virtual NPCs. vNPCs are only described in text - a room could be described as a bustling street, farmers can be described shouting to each other. Using room descriptions for this works well, but the tutorial lesson about [EvAdventure Rooms](./Beginner-Tutorial-Rooms.md) has a section called [adding life to a room](./Beginner-Tutorial-Rooms.md#adding-life-to-a-room) that can be used for making vNPCs appear to do things in the background.
```

_Non-Player-Characters_, or NPCs, is the common term for all active agents that are _not_ controlled by players. NPCs could be anything from merchants and quest givers, to monsters and bosses.  They could also be 'flavor' - townsfolk doing their chores, farmers tending their fields - there to make the world feel "more alive". 

In this lesson we will create the base class of _EvAdventure_ NPCs based on the _Knave_ ruleset. According to the _Knave_ rules, NPCs have some simplified stats compared to the [PC characters](./Beginner-Tutorial-Characters.md) we designed earlier. 

<div style="clear: right;"></div>

## The NPC base class

```{sidebar}
See [evennia/contrib/tutorials/evadventure/npcs.py](evennia.contrib.tutorials.evadventure.npcs) for a ready-made example of an npc module.
```
> Create a new module `evadventure/npcs.py`.

```{code-block} python
:linenos: 
:emphasize-lines: 9, 12, 13, 15, 17, 19, 25, 23, 59, 61

# in evadventure/npcs.py 

from evennia import DefaultCharacter, AttributeProperty

from .characters import LivingMixin
from .enums import Ability


class EvAdventureNPC(LivingMixin, DefaultCharacter): 
	"""Base class for NPCs""" 

    is_pc = False
    hit_dice = AttributeProperty(default=1, autocreate=False)
    armor = AttributeProperty(default=1, autocreate=False)  # +10 to get armor defense
    hp_multiplier = AttributeProperty(default=4, autocreate=False)  # 4 default in Knave
    hp = AttributeProperty(default=None, autocreate=False)  # internal tracking, use .hp property
    morale = AttributeProperty(default=9, autocreate=False)
    allegiance = AttributeProperty(default=Ability.ALLEGIANCE_HOSTILE, autocreate=False)

    weapon = AttributeProperty(default=BARE_HANDS, autocreate=False)  # instead of inventory
    coins = AttributeProperty(default=1, autocreate=False)  # coin loot
 
    is_idle = AttributeProperty(default=False, autocreate=False)
    
    @property
    def strength(self):
        return self.hit_dice
        
    @property
    def dexterity(self):
        return self.hit_dice
 
    @property
    def constitution(self):
        return self.hit_dice
 
    @property
    def intelligence(self):
        return self.hit_dice
 
    @property
    def wisdom(self):
        return self.hit_dice
 
    @property
    def charisma(self):
        return self.hit_dice
 
    @property
    def hp_max(self):
        return self.hit_dice * self.hp_multiplier
    
    def at_object_creation(self):
         """
         Start with max health.
  
         """
         self.hp = self.hp_max
         self.tags.add("npcs", category="group")
                                                                                   
     def ai_next_action(self, **kwargs):                     
         """                                                        
		 The system should regularly poll this method to have 
		 the NPC do their next AI action. 
                                                                    
         """                                                        
         pass                           
```

- **Line 9**: By use of _multiple inheritance_ we use the `LinvingMixin` we created in the [Character lesson](./Beginner-Tutorial-Characters.md). This includes a lot of useful methods, such as showing our 'hurt level', methods to use to heal, hooks to call when getting attacked, hurt and so on. We can re-use all of those in upcoming NPC subclasses.
- **Line 12**: The `is_pc` is a quick and convenient way to check if this is, well, a PC or not. We will use it in the upcoming [Combat base lesson](./Beginner-Tutorial-Combat-Base.md).
- **Line 13**: The NPC is simplified in that all stats are just based on the `Hit dice` number (see **Lines 25-51**). We store `armor` and a `weapon` as direct [Attributes](../../../Components/Attributes.md) on the class rather than bother implementing a full equipment system. 
- **Lines 17, 18**: The `morale` and `allegiance` are _Knave_ properties determining how likely the NPC is to flee in a combat situation and if they are hostile or friendly.
- **Line 19**: The `is_idle` Attribute is a useful property. It should be available on all NPCs and will be used to disable AI entirely. 
- **Line 59**: We make sure to tag NPCs. We may want to group different NPCs together later, for example to have all NPCs with the same tag respond if one of them is attacked.
- **Line 61**: The `ai_next_action` is a method we prepare for the system to be able to ask the NPC 'what do you want to do next?'. In it we will add all logic related to the artificial intelligence of the NPC - such as walking around, attacking and performing other actions.


## Testing 

> Create a new module `evadventure/tests/test_npcs.py`

Not so much to test yet, but we will be using the same module to test other aspects of NPCs in the future, so let's create it now. 

```python 
# in evadventure/tests/test_npcs.py

from evennia import create_object                                           
from evennia.utils.test_resources import EvenniaTest                        
                                                                            
from .. import npcs                                                         
                                                                            
class TestNPCBase(EvenniaTest):                                             
	"""Test the NPC base class""" 
	
    def test_npc_base(self):
        npc = create_object(
            npcs.EvAdventureNPC,
            key="TestNPC",
            attributes=[("hit_dice", 4)],  # set hit_dice to 4
        )
        
        self.assertEqual(npc.hp_multiplier, 4)
        self.assertEqual(npc.hp, 16)
        self.assertEqual(npc.strength, 4)
        self.assertEqual(npc.charisma, 4)



```

Nothing special here. Note how the `create_object` helper function takes `attributes` as a keyword. This is a list of tuples we use to set different values than the default ones to Attributes. We then check a few of the properties to make sure they return what we expect.


## Conclusions 

In _Knave_, an NPC is a simplified version of a Player Character. In other games and rule systems, they may be all but identical. 

With the NPC class in place, we have enough to create a 'test dummy'. Since it has no AI yet, it won't fight back, but it will be enough to have something to hit when we test our combat in the upcoming lessons.