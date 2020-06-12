# Tutorial Aggressive NPCs


This tutorial shows the implementation of an NPC object that responds to characters entering their location. In this example the NPC has the option to respond aggressively or not, but any actions could be triggered this way.

One could imagine using a [Script](Scripts) that is constantly checking for newcomers. This would be highly inefficient (most of the time its check would fail). Instead we handle this on-demand by using a couple of existing object hooks to inform the NPC that a Character has entered.

It is assumed that you already know how to create custom room and character typeclasses, please see the [Basic Game tutorial](Tutorial-for-basic-MUSH-like-game) if you haven't already done this.

What we will need is the following: 

- An NPC typeclass that can react when someone enters.
- A custom [Room](Objects#rooms) typeclass that can tell the NPC that someone entered.
- We will also tweak our default `Character` typeclass a little. 

To begin with, we need to create an NPC typeclass. Create a new file inside of your typeclasses folder and name it `npcs.py` and then add the following code:

```python
from typeclasses.characters import Character 

class NPC(Character):
    """
    A NPC typeclass which extends the character class.
    """
    def at_char_entered(self, character):
        """
         A simple is_aggressive check. 
         Can be expanded upon later.
        """       
        if self.db.is_aggressive:
            self.execute_cmd(f"say Graaah, die {character}!")
        else:
            self.execute_cmd(f"say Greetings, {character}!")
```

We will define our custom `Character` typeclass below. As for the new `at_char_entered` method we've just defined, we'll ensure that it will be called by the room where the NPC is located, when a player enters that room.  You'll notice that right now, the NPC merely speaks.  You can expand this part as you like and trigger all sorts of effects here (like combat code, fleeing, bartering or quest-giving) as your game design dictates.

Now your `typeclasses.rooms` module needs to have the following added:

```python
# Add this import to the top of your file.
from evennia import utils

    # Add this hook in any empty area within your Room class.
    def at_object_receive(self, obj, source_location):
        if utils.inherits_from(obj, 'typeclasses.npcs.NPC'): # An NPC has entered
            return
        elif utils.inherits_from(obj, 'typeclasses.characters.Character'): 
            # A PC has entered.
            # Cause the player's character to look around.
            obj.execute_cmd('look')
            for item in self.contents:
                if utils.inherits_from(item, 'typeclasses.npcs.NPC'): 
                    # An NPC is in the room
                    item.at_char_entered(obj)
```

`inherits_from` must be given the full path of the class. If the object inherited a class from your `world.races` module, then you would check inheritance with `world.races.Human`, for example. There is no need to import these prior, as we are passing in the full path. As a matter of a fact, `inherits_from` does not properly work if you import the class and only pass in the name of the class.

> Note:  [at_object_receive](https://github.com/evennia/evennia/blob/master/evennia/objects/objects.py#L1529) is a default hook of the `DefaultObject` typeclass (and its children). Here we are overriding this hook in our customized room typeclass to suit our needs. 

This room checks the typeclass of objects entering it (using `utils.inherits_from` and responds to `Characters`, ignoring other NPCs or objects.  When triggered the room will look through its contents and inform any `NPCs inside by calling their `at_char_entered` method.

You'll also see that we have added a 'look' into this code. This is because, by default, the `at_object_receive` is carried out *before* the character's `at_after_move` which, we will now overload.  This means that a character entering would see the NPC perform its actions before the 'look' command. Deactivate the look command in the default `Character` class within the `typeclasses.characters` module: 

```python
    # Add this hook in any blank area within your Character class.
    def at_after_move(self, source_location):
        """
        Default is to look around after a move 
        Note:  This has been moved to Room.at_object_receive
        """
        #self.execute_cmd('look')
        pass
```

Now let's create an NPC and make it aggressive. Type the following commands into your MUD client:
```
reload
create/drop Orc:npcs.NPC
```

> Note: You could also give the path as `typeclasses.npcs.NPC`, but Evennia will look into the `typeclasses` folder automatically, so this is a little shorter.

When you enter the aggressive NPC's location, it will default to using its peaceful action (say your name is Anna):

```
Orc says, "Greetings, Anna!"
```

Now we turn on the aggressive mode (we do it manually but it could also be triggered by some sort of AI code). 

```
set orc/is_aggressive = True
```

Now it will perform its aggressive action whenever a character enters.

```
Orc says, "Graaah, die, Anna!"
```
