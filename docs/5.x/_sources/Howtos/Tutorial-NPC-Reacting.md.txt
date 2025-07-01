# NPCs reacting to your presence


    > north 
    ------------------------------------
    Meadow
    You are standing in a green meadow. 
    A bandit is here. 
    ------------------------------------
    Bandit gives you a menacing look!

This tutorial shows the implementation of an NPC object that responds to characters entering their
location. 

What we will need is the following:

- An NPC typeclass that can react when someone enters.
- A custom [Room](../Components/Objects.md#rooms) typeclass that can tell the NPC that someone entered.
- We will also tweak our default `Character` typeclass a little.

```python
# in mygame/typeclasses/npcs.py  (for example)

from typeclasses.characters import Character

class NPC(Character):
    """
    A NPC typeclass which extends the character class.
    """
    def at_char_entered(self, character, **kwargs):
        """
        A simple is_aggressive check.
        Can be expanded upon later.
        """
        if self.db.is_aggressive:
            self.execute_cmd(f"say Graaah! Die, {character}!")
        else:
            self.execute_cmd(f"say Greetings, {character}!")
```

```{sidebar} Passing extra information
Note that we don't use the `**kwargs` property here. This can be used to pass extra information into hooks in your game and would be used when you make custom move commands. For example, if you `run` into the room, you could inform all hooks by doing `obj.move_to(..., running=True)`. Maybe your librarian NPC should have a separate reaction for people running into their library!

We make sure to pass the `**kwargs` from the standard `at_object_receive` hook below.
```

Here we make a simple method on the `NPC`˙ called `at_char_entered`. We expect it to be called when a (player-)character enters the room. We don't actually set the `is_aggressive` [Attribute](../Components/Attributes.md) beforehand; we leave this up for the admin to activate in-game. if it's not set, the NPC is simply non-hostile. 

Whenever _something_ enters the `Room`, its [at_object_receive](DefaultObject.at_object_receive) hook will be called. So we should override it.


```python
# in mygame/typeclasses/rooms.py

from evennia import utils

# ... 

class Room(ObjectParent, DefaultRoom):

    # ... 
    
    def at_object_receive(self, arriving_obj, source_location, **kwargs):
        if arriving_obj.account: 
            # this has an active acccount - a player character
            for item in self.contents:
                # get all npcs in the room and inform them
                if utils.inherits_from(item, "typeclasses.npcs.NPC"):
                    item.at_char_entered(arriving_obj, **kwargs)

```

```{sidebar} Universal Object methods
Remember that Rooms are `Objects`, and other Objects have these same hooks. So an `at_object_receive` hook will fire for you when you pick something up (making you 'receive' it). Or for a box when putting something inside it, for example.
```
A currently puppeted Character will have an `.account` attached to it. We use that to know that the thing arriving is a Character. We then use Evennia's [utils.inherits_from](evennia.utils.utils.inherits_from) helper utility to get every NPC in the room can each of their newly created `at_char_entered` method.

Make sure to `reload`.

Let's create an NPC and make it aggressive. For the sake of this example, let's assume your name is "Anna" and that there is a room to the north of your current location.

    > create/drop Orc:typeclasses.npcs.NPC
    > north 
    > south 
    Orc says, Greetings, Anna!

Now let's turn the orc aggressive. 

    > set orc/is_aggressive = True 
    > north 
    > south 
    Orc says, Graah! Die, Anna!

That's one easily aggravated Orc!