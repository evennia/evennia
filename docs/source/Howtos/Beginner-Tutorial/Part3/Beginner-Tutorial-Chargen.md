# Character Generation

In previous lessons we have established how a character looks. Now we need to give the player a 
chance to create one. 

## How it will work

A fresh Evennia install will automatically create a new Character with the same name as your 
Account when you log in. This is quick and simple and mimics older MUD styles. You could picture 
doing this, and then customizing the Character in-place. 

We will be a little more sophisticated though. We want the user to be able to create a character 
using a menu when they log in. 

We do this by editing `mygame/server/conf/settings.py` and adding the line

    AUTO_CREATE_CHARACTER_WITH_ACCOUNT = False 

When doing this, connecting with the game with a new account will land you in "OOC" mode. The 
ooc-version of `look` (sitting in the Account cmdset) will show a list of available characters 
if you have any. You can also enter `charcreate` to make a new character. The `charcreate` is a 
simple command coming with Evennia that just lets you make a new character with a given name and 
description. We will later modify that to kick off our chargen. For now we'll just keep in mind 
that's how we'll start off the menu.

In _Knave_, most of the character-generation is random. This means this tutorial can be pretty
compact while still showing the basic idea. What we will create is a menu looking like this:


```
Silas 

STR +1
DEX +2
CON +1
INT +3
WIS +1
CHA +2

You are lanky with a sunken face and filthy hair, breathy speech, and foreign clothing.
You were a herbalist, but you were pursued and ended up a knave. You are honest but also 
suspicious. You are of the neutral alignment. 

Your belongings: 
Brigandine armor, ration, ration, sword, torch, torch, torch, torch, torch, 
tinderbox, chisel, whistle

----------------------------------------------------------------------------------------
1. Change your name 
2. Swap two of your ability scores (once)
3. Accept and create character
```

If you select 1, you get a new menu node: 

``` 
Your current name is Silas. Enter a new name or leave empty to abort.
-----------------------------------------------------------------------------------------
```
You can now enter a new name. When pressing return you'll get back to the first menu node
showing your character, now with the new name. 

If you select 2, you go to another menu node: 

```
Your current abilities: 

STR +1
DEX +2
CON +1
INT +3
WIS +1
CHA +2

You can swap the values of two abilities around.
You can only do this once, so choose carefully!

To swap the values of e.g. STR and INT, write 'STR INT'. Empty to abort.
------------------------------------------------------------------------------------------
```
If you enter `WIS CHA` here,  WIS will become `+2` and `CHA` `+1`. You will then again go back 
to the main node to see your new character, but this time the option to swap will no longer be 
available (you can only do it once).

If you finally select the `Accept and create character` option, the character will be created 
and you'll leave the menu; 

    Character was created! 

## Random tables

```{sidebar}
Full Knave random tables are found in 
[evennia/contrib/tutorials/evadventure/random_tables.py](evennia.contrib.tutorials.evadventure.random_tables). 
```

> Make a new module `mygame/evadventure/random_tables.py`.

Since most of _Knave_'s character generation is random we will need to roll on random tables 
from the _Knave_ rulebook. While we added the ability to roll on a random table back in the 
[Rules Tutorial](./Beginner-Tutorial-Rules.md), we haven't added the relevant tables yet.

``` 
# in mygame/evadventure/random_tables.py 

character_generation = {
    "physique": [
        "athletic", "brawny", "corpulent", "delicate", "gaunt", "hulking", "lanky",
        "ripped", "rugged", "scrawny", "short", "sinewy", "slender", "flabby",
        "statuesque", "stout", "tiny", "towering", "willowy", "wiry",
    ],
    "face": [
        "bloated", "blunt", "bony", # ... 
    ], # ... 
}

```

The tables are just copied from the _Knave_ rules. We group the aspects in a dict 
`character_generation` to separate chargen-only tables from other random tables we'll also 
keep in here. 

## Storing state of the menu 

```{sidebar}
There is a full implementation of the chargen in [evennia/contrib/tutorials/evadventure/chargen.
py](evennia.contrib.tutorials.evadventure.chargen).
```
> create a new module `mygame/evadventure/chargen.py`.

During character generation we will need an entity to store/retain the changes, like a 
'temporary character sheet'.


```python 
# in mygame/evadventure/chargen.py 

from .random_tables import chargen_table 
from .rules import dice 

class TemporaryCharacterSheet:
    
    def __init__(self):
        self.ability_changes = 0  # how many times we tried swap abilities
    
    def _random_ability(self):
        return min(dice.roll("1d6"), dice.roll("1d6"), dice.roll("1d6"))

    def generate(self):
        # name will likely be modified later
        self.name = dice.roll_random_table("1d282", chargen_table["name"])

        # base attribute values
        self.strength = self._random_ability()
        self.dexterity = self._random_ability()
        self.constitution = self._random_ability()
        self.intelligence = self._random_ability()
        self.wisdom = self._random_ability()
        self.charisma = self._random_ability()

        # physical attributes (only for rp purposes)
        physique = dice.roll_random_table("1d20", chargen_table["physique"])
        face = dice.roll_random_table("1d20", chargen_table["face"])
        skin = dice.roll_random_table("1d20", chargen_table["skin"])
        hair = dice.roll_random_table("1d20", chargen_table["hair"])
        clothing = dice.roll_random_table("1d20", chargen_table["clothing"])
        speech = dice.roll_random_table("1d20", chargen_table["speech"])
        virtue = dice.roll_random_table("1d20", chargen_table["virtue"])
        vice = dice.roll_random_table("1d20", chargen_table["vice"])
        background = dice.roll_random_table("1d20", chargen_table["background"])
        misfortune = dice.roll_random_table("1d20", chargen_table["misfortune"])
        alignment = dice.roll_random_table("1d20", chargen_table["alignment"])

        self.desc = (
            f"You are {physique} with a {face} face, {skin} skin, {hair} hair, {speech} speech,"
            f" and {clothing} clothing. You were a {background.title()}, but you were"
            f" {misfortune} and ended up a knave. You are {virtue} but also {vice}. You are of the"
            f" {alignment} alignment."
        )

        # 
        self.hp_max = max(5, dice.roll("1d8"))
        self.hp = self.hp_max
        self.xp = 0
        self.level = 1

        # random equipment
        self.armor = dice.roll_random_table("1d20", chargen_table["armor"])

        _helmet_and_shield = dice.roll_random_table("1d20", chargen_table["helmets and shields"])
        self.helmet = "helmet" if "helmet" in _helmet_and_shield else "none"
        self.shield = "shield" if "shield" in _helmet_and_shield else "none"

        self.weapon = dice.roll_random_table("1d20", chargen_table["starting weapon"])

        self.backpack = [
            "ration",
            "ration",
            dice.roll_random_table("1d20", chargen_table["dungeoning gear"]),
            dice.roll_random_table("1d20", chargen_table["dungeoning gear"]),
            dice.roll_random_table("1d20", chargen_table["general gear 1"]),
            dice.roll_random_table("1d20", chargen_table["general gear 2"]),
        ]
```

Here we have followed the _Knave_ rulebook to randomize abilities, description and equipment. 
The `dice.roll()` and `dice.roll_random_table` methods now become very useful! Everything here 
should be easy to follow. 

The main difference from baseline _Knave_ is that we make a table of "starting weapon" (in Knave 
you can pick whatever you like). 

We also initialize `.ability_changes = 0`. Knave only allows us to swap the values of two 
Abilities _once_. We will use this to know if it has been done or not.

### Showing the sheet
        
Now that we have our temporary character sheet, we should make it easy to visualize it. 
        
```python
# in mygame/evadventure/chargen.py 

_TEMP_SHEET = """
{name}

STR +{strength}
DEX +{dexterity}
CON +{constitution}
INT +{intelligence}
WIS +{wisdom}
CHA +{charisma}

{description}
    
Your belongings:
{equipment}
"""

class TemporaryCharacterSheet: 
    
    # ... 
    
    def show_sheet(self):
        equipment = (
            str(item)
            for item in [self.armor, self.helmet, self.shield, self.weapon] + self.backpack
            if item
        )

        return _TEMP_SHEET.format(
            name=self.name,
            strength=self.strength,
            dexterity=self.dexterity,
            constitution=self.constitution,
            intelligence=self.intelligence,
            wisdom=self.wisdom,
            charisma=self.charisma,
            description=self.desc,
            equipment=", ".join(equipment),
        )

```

The new `show_sheet` method collect the data from the temporary sheet and return it in a pretty 
form. Making a 'template' string like `_TEMP_SHEET` makes it easier to change things later if you want 
to change how things look.

### Apply character

Once we are happy with our character, we need to actually create it with the stats we chose. 
This is a bit more involved. 

```python
# in mygame/evadventure/chargen.py 

# ... 

from .characters import EvAdventureCharacter
from evennia import create_object
from evennia.prototypes.spawner import spawn 


class TemporaryCharacterSheet:
     
    # ...  

    def apply(self):
        # create character object with given abilities
        new_character = create_object(
            EvAdventureCharacter,
            key=self.name,
            attrs=(
                ("strength", self.strength),
                ("dexterity", self.dexterity),
                ("constitution", self.constitution),
                ("intelligence", self.intelligence),
                ("wisdom", self.wisdom),
                ("charisma", self.wisdom),
                ("hp", self.hp),
                ("hp_max", self.hp_max),
                ("desc", self.desc),     
            ),                           
        )                                
        # spawn equipment (will require prototypes created before it works)
        if self.weapon:                  
            weapon = spawn(self.weapon)  
            new_character.equipment.move(weapon)
        if self.shield:                  
            shield = spawn(self.shield)  
            new_character.equipment.move(shield)
        if self.armor:                   
            armor = spawn(self.armor)    
            new_character.equipment.move(armor)
        if self.helmet:                  
            helmet = spawn(self.helmet)  
            new_character.equipment.move(helmet)
            
        for item in self.backpack:
            item = spawn(item)
            new_character.equipment.store(item)
                                        
        return new_character  
```

We use `create_object` to create a new `EvAdventureCharacter`. We feed it with all relevant data 
from the temporary character sheet. This is when these become an actual character. 

```{sidebar}
A prototype is basically a `dict` describing how the object should be created. Since 
it's just a piece of code, it can stored in a Python module and used to quickly _spawn_ (create) 
things from those prototypes.
```

Each piece of equipment is an object in in its own right. We will here assume that all game 
items are defined as [Prototypes](../../../Components/Prototypes.md) keyed to its name, such as "sword", "brigandine 
armor" etc. 

We haven't actually created those prototypes yet, so for now we'll need to assume they are there.
Once a piece of equipment has been spawned, we make sure to move it into the `EquipmentHandler` we 
created in the [Equipment lesson](./Beginner-Tutorial-Equipment.md).


## Initializing EvMenu 

Evennia comes with a full menu-generation system based on [Command sets](../../../Components/Command-Sets.md), called 
[EvMenu](../../../Components/EvMenu.md). 

```python 
# in mygame/evadventure/chargen.py

from evennia import EvMenu 

# ...

# chargen menu 


# this goes to the bottom of the module

def start_chargen(caller, session=None):
    """
    This is a start point for spinning up the chargen from a command later.

    """

    menutree = {}  # TODO!

    # this generates all random components of the character
    tmp_character = TemporaryCharacterSheet()
    tmp_character.generate()

    EvMenu(caller, menutree, session=session, tmp_character=tmp_character)

```

This first function is what we will call from elsewhere (for example from a custom `charcreate` 
command) to kick the menu into gear.

It takes the `caller` (the one to want to start the menu) and a `session` argument. The latter will help 
track just which client-connection we are using (depending on Evennia settings, you could be 
connecting with multiple clients).

We create a `TemporaryCharacterSheet` and call `.generate()` to make a random character. We then 
feed all this into `EvMenu`. 

The moment this happens, the user will be in the menu, there are no further steps needed. 

The `menutree` is what we'll create next. It describes which menu 'nodes' are available to jump
between. 

## Main Node: Choosing what to do

This is the first menu node. It will act as a central hub, from which one can choose different 
actions.

```python
# in mygame/evadventure/chargen.py 

# ...

# at the end of the module, but before the `start_chargen` function

def node_chargen(caller, raw_string, **kwargs): 

    tmp_character = kwargs["tmp_character"]

    text = tmp_character.show_sheet()

    options = [
        {
           "desc": "Change your name", 
           "goto": ("node_change_name", kwargs)
        }
    ]
    if tmp_character.ability_changes <= 0:
        options.append( 
            { 
                "desc": "Swap two of your ability scores (once)",
                "goto": ("node_swap_abilities", kwargs),
            }
        )
    options.append(
        {
            "desc": "Accept and create character", 
            "goto": ("node_apply_character", kwargs)
        },
    )

    return text, options

# ...
```

A lot to unpack here! In Evennia, it's convention to name your node-functions `node_*`. While 
not required, it helps you track what is a node and not. 

Every menu-node, should accept `caller, raw_string, **kwargs` as arguments. Here `caller` is the 
`caller` you passed into the `EvMenu` call. `raw_string` is the input given by the user in order 
to _get to this node_, so currently empty. The `**kwargs` are all extra keyword arguments passed 
into `EvMenu`. They can also be passed between nodes. In this case, we passed the 
keyword `tmp_character` to `EvMenu`. We now have the temporary character sheet available in the 
node! 

An `EvMenu` node must always return two things - `text` and `options`. The `text` is what will 
show to the user when looking at this node. The `options` are, well, what options should be 
presented to move on from here to some other place. 

For the text, we simply get a pretty-print of the temporary character sheet. A single option is 
defined as a `dict` like this: 

```python
{ 
    "key": ("name". "alias1", "alias2", ...),  # if skipped, auto-show a number
    "desc": "text to describe what happens when selecting option",.
    "goto": ("name of node or a callable", kwargs_to_pass_into_next_node_or_callable)
}
```

Multiple option-dicts are returned in a list or tuple. The `goto` option-key is important to 
understand. The job of this is to either point directly to another node (by giving its name), or 
by pointing to a Python callable (like a function) _that then returns that name_. You can also 
pass kwargs (as a dict). This will be made available as `**kwargs` in the callable or next node.

While an option can have a `key`, you can also skip it to just get a running number.

In our `node_chargen` node, we point to three nodes by name: `node_change_name`, 
`node_swap_abilities`, and `node_apply_character`. We also make sure to pass along `kwargs`
to each node, since that contains our temporary character sheet.

The middle of these options only appear if we haven't already switched two abilities around - to 
know this, we check the `.ability_changes` property to make sure it's still 0.


## Node: Changing your name 

This is where you end up if you opted to change your name in `node_chargen`.

```python
# in mygame/evadventure/chargen.py

# ...

# after previous node 

def _update_name(caller, raw_string, **kwargs):
    """
    Used by node_change_name below to check what user 
    entered and update the name if appropriate.

    """
    if raw_string:
        tmp_character = kwargs["tmp_character"]
        tmp_character.name = raw_string.lower().capitalize()

    return "node_chargen", kwargs


def node_change_name(caller, raw_string, **kwargs):
    """
    Change the random name of the character.

    """
    tmp_character = kwargs["tmp_character"]

    text = (
        f"Your current name is |w{tmp_character.name}|n. "
        "Enter a new name or leave empty to abort." 
    )

    options = {
                   "key": "_default", 
                   "goto": (_update_name, kwargs)
              }

    return text, options
```

There are two functions here - the menu node itself (`node_change_name`) and a 
helper _goto_function_ (`_update_name`) to handle the user's input. 

For the (single) option, we use a special `key` named `_default`. This makes this option 
a catch-all: If the user enters something that does not match any other option, this is 
the option that will be used.
Since we have no other options here, we will always use this option no matter what the user enters.

Also note that the `goto` part of the option points to the `_update_name` callable rather than to 
the name of a node. It's important we keep passing `kwargs` along to it! 

When a user writes anything at this node, the `_update_name` callable will be called. This has 
the same arguments as a node, but it is _not_ a node - we will only use it to _figure out_ which 
node to go to next. 

In `_update_name` we now have a use for the `raw_string` argument - this is what was written by 
the user on the previous node, remember? This is now either an empty string (meaning to ignore 
it) or the new name of the character. 

A goto-function like `_update_name` must return the name of the next node to use. It can also 
optionally return the `kwargs` to pass into that node - we want to always do this, so we don't 
loose our temporary character sheet. Here we will always go back to the `node_chargen`.

> Hint: If returning `None` from a goto-callable, you will always return to the last node you 
> were at.

## Node: Swapping Abilities around

You get here by selecting the second option from the `node_chargen` node.

```python
# in mygame/evadventure/chargen.py 

# ...

# after previous node 

_ABILITIES = {
    "STR": "strength",
    "DEX": "dexterity",
    "CON": "constitution",
    "INT": "intelligence",
    "WIS": "wisdom",
    "CHA": "charisma",
}


def _swap_abilities(caller, raw_string, **kwargs):
    """
    Used by node_swap_abilities to parse the user's input and swap ability
    values.

    """
    if raw_string:
        abi1, *abi2 = raw_string.split(" ", 1)
        if not abi2:
            caller.msg("That doesn't look right.")
            return None, kwargs
        abi2 = abi2[0]
        abi1, abi2 = abi1.upper().strip(), abi2.upper().strip()
        if abi1 not in _ABILITIES or abi2 not in _ABILITIES:
            caller.msg("Not a familiar set of abilites.")
            return None, kwargs
        
        # looks okay = swap values. We need to convert STR to strength etc
        tmp_character = kwargs["tmp_character"]
        abi1 = _ABILITIES[abi1]
        abi2 = _ABILITIES[abi2]
        abival1 = getattr(tmp_character, abi1)
        abival2 = getattr(tmp_character, abi2)
            
        setattr(tmp_character, abi1, abival2)
        setattr(tmp_character, abi2, abival1)
        
        tmp_character.ability_changes += 1
        
    return "node_chargen", kwargs

            
def node_swap_abilities(caller, raw_string, **kwargs):
    """ 
    One is allowed to swap the values of two abilities around, once.

    """
    tmp_character = kwargs["tmp_character"]

    text = f"""
Your current abilities:

STR +{tmp_character.strength}
DEX +{tmp_character.dexterity}
CON +{tmp_character.constitution}
INT +{tmp_character.intelligence}
WIS +{tmp_character.wisdom}
CHA +{tmp_character.charisma}

You can swap the values of two abilities around.
You can only do this once, so choose carefully!

To swap the values of e.g.  STR and INT, write |wSTR INT|n. Empty to abort.
"""

    options = {"key": "_default", "goto": (_swap_abilities, kwargs)}
    
        return text, options
```

This is more code, but the logic is the same - we have a node (`node_swap_abilities`) and
and a goto-callable helper (`_swap_abilities`). We catch everything the user writes on the 
node (such as `WIS CON`) and feed it into the helper. 

In `_swap_abilities`, we need to analyze the `raw_string` from the user to see what they 
want to do.

Most code in the helper is validating the user didn't enter nonsense. If they did, 
we use `caller.msg()` to tell them and then return `None, kwargs`, which re-runs the same node (the 
name-selection) all over again. 

Since we want users to be able to write "CON" instead of the longer "constitution", we need a 
mapping `_ABILITIES` to easily convert between the two (it's stored as `consitution` on the 
temporary character sheet). Once we know which abilities they want to swap, we do so and tick up 
the `.ability_changes` counter. This means this option will no longer be available from the main 
node. 

Finally, we return to `node_chargen` again.

## Node: Creating the Character 

We get here from the main node by opting to finish chargen. 

```python 
node_apply_character(caller, raw_string, **kwargs):
    """                              
    End chargen and create the character. We will also puppet it.
                                     
    """                              
    tmp_character = kwargs["tmp_character"]
    new_character = tmp_character.apply(caller)      
    
    caller.account.db._playable_characters = [new_character] 
    
    text = "Character created!"
    
    return text, None 
```
When entering the node, we will take the Temporary character sheet and use its `.appy` method to
create a new Character with all equipment. 

This is what is called an _end node_, because it returns `None` instead of options. After this, 
the menu will exit. We will be back to the default character selection screen. The characters 
found on that screen are the ones listed in the `_playable_characters` Attribute, so we need to 
also the new character to it.


## Tying the nodes together 

```python
def start_chargen(caller, session=None):
"""
This is a start point for spinning up the chargen from a command later.

    """
    menutree = {  # <----- can now add this!
       "node_chargen": node_chargen, 
       "node_change_name": node_change_name, 
       "node_swap_abilities": node_swap_abilities,
       "node_apply_character": node_apply_character
    }
        
    # this generates all random components of the character
    tmp_character = TemporaryCharacterSheet()
    tmp_character.generate()

    EvMenu(caller, menutree, session=session, 
           startnode="node_chargen",   # <----- 
           tmp_character=tmp_character)
          
```

Now that we have all the nodes, we add them to the `menutree` we left empty before. We only add 
the nodes, _not_ the goto-helpers! The keys we set in the `menutree` dictionary are the names we 
should use to point to nodes from inside the menu (and we did). 

We also add a keyword argument `startnode` pointing to the `node_chargen` node. This tells EvMenu 
to first jump into that node when the menu is starting up.

## Conclusions 

This lesson taught us how to use `EvMenu` to make an interactive character generator. In an RPG 
more complex than _Knave_, the menu would be bigger and more intricate, but the same principles 
apply. 

Together with the previous lessons we have now fished most of the basics around player 
characters - how they store their stats, handle their equipment and how to create them. 

In the next lesson we'll address how EvAdventure _Rooms_ work.