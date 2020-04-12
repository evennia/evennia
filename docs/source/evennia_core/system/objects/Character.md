# Characters

Characters are objects controlled by [Accounts](../accounts/Accounts). When a new Account
logs in to Evennia for the first time, a new `Character` object is created and
the Account object is assigned to the `account` attribute. A `Character` object
must have a [Default Commandset](../commands/Commands#Command_Sets) set on itself at
creation, or the account will not be able to issue any commands! If you just
inherit your own class from `evennia.DefaultCharacter` and make sure to use
`super()` to call the parent methods you should be fine. In
`mygame/typeclasses/characters.py` is an empty `Character` class ready for you
to modify.
