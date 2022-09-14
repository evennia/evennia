# Character Generation

In previous lessons we have established how a character looks. Now we need to give the player a 
chance to create one. 

In _Knave_, most of the character-generation is random. This means this tutorial can be pretty 
compact while still showing the basic idea. What we will create is a menu looking like this: 

## How it will work

We want to have chargen appear when we log in.

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

If you finally select the `Accept and create character` option, you will leave character 
generation and start the game as this character. 

 
