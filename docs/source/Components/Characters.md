# Characters 
**Inheritance Tree:
```
┌─────────────┐
│DefaultObject│
└─────▲───────┘
      │
┌─────┴──────────┐
│DefaultCharacter│
└─────▲──────────┘
      │           ┌────────────┐
      │ ┌─────────►ObjectParent│
      │ │         └────────────┘
  ┌───┴─┴───┐
  │Character│
  └─────────┘
```

_Characters_ is an in-game [Object](./Objects.md) commonly used to represent the player's in-game avatar. The empty `Character` class is found in `mygame/typeclasses/characters.py`. It inherits from [DefaultCharacter](evennia.objects.objects.DefaultCharacter) and the (by default empty) `ObjectParent` class (used if wanting to add share properties between all in-game Objects). 

When a new [Account](./Accounts.md) logs in to Evennia for the first time, a new `Character` object is created and the [Account](./Accounts.md) will be set to _puppet_ it. By default this first Character will get the same name as the Account (but Evennia supports [alternative connection-styles](../Concepts/Connection-Styles.md) if so desired). 

A `Character` object will usually have a [Default Commandset](./Command-Sets.md) set on itself at creation, or the account will not be able to issue any in-game commands! 

If you want to change the default character created by the default commands, you can change it in settings: 

    BASE_CHARACTER_TYPECLASS = "typeclasses.characters.Character"
    
This deafult points at the empty class in  `mygame/typeclasses/characters.py` , ready for you to modify as you please.