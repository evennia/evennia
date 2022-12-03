# Accounts

```
┌──────┐ │   ┌───────┐    ┌───────┐   ┌──────┐
│Client├─┼──►│Session├───►│Account├──►│Object│  
└──────┘ │   └───────┘    └───────┘   └──────┘
                              ^
```

An _Account_ represents a unique game account - one player playing the game. Whereas a player can potentially connect to the game from several Clients/Sessions, they will normally have only one Account. 

The Account object has no in-game representation. In order to actually get on the game the Account must *puppet* an [Object](./Objects.md) (normally a [Character](./Objects.md#characters)).

Exactly how many Sessions can interact with an Account and its Puppets at once is determined by
Evennia's [MULTISESSION_MODE](../Concepts/Connection-Styles.md#multisession-mode-and-multiplaying)

Apart from storing login information and other account-specific data, the Account object is what is chatting on Evennia's default [Channels](./Channels.md).  It is also a good place to store [Permissions](./Locks.md) to be consistent between different in-game characters. It can also hold player-level configuration options. 

The Account object has its own default [CmdSet](./Command-Sets.md), the `AccountCmdSet`. The commands in this set are available to the player no matter which character they are puppeting. Most notably the default game's `exit`, `who` and chat-channel commands are in the Account cmdset.

    > ooc 

The default  `ooc` command causes you to leave your current puppet and go into OOC mode. In this mode you have no location and have only the Account-cmdset available. It acts a staging area for switching characters (if your game supports that) as well as a safety fallback if your character gets accidentally deleted. 

    > ic 

This re-puppets the latest character.

Note that the Account object can have, and often does have, a different set of [Permissions](./Permissions.md) from the Character they control.  Normally you should put your permissions on the Account level - this will overrule permissions set on the Character level. For the permissions of the Character to come into play the default `quell` command can be used. This allows for exploring the game using a different permission set (but you can't escalate your permissions this way - for hierarchical permissions like `Builder`, `Admin` etc, the *lower* of the permissions on the Character/Account will always be used). 


## Working with Accounts

You will usually not want more than one Account typeclass for all new accounts.

An Evennia Account is, per definition, a Python class that includes `evennia.DefaultAccount` among its parents. In `mygame/typeclasses/accounts.py` there is an empty class ready for you to modify. Evennia defaults to using this (it inherits directly from `DefaultAccount`).

Here's an example of modifying the default Account class in code:

```python
    # in mygame/typeclasses/accounts.py

    from evennia import DefaultAccount

    class Account(DefaultAccount): 
        # [...]
    	def at_account_creation(self): 
        	"this is called only once, when account is first created"
    	    self.db.real_name = None      # this is set later 
    	    self.db.real_address = None   #       "
    	    self.db.config_1 = True       # default config 
    	    self.db.config_2 = False      #       "
    	    self.db.config_3 = 1          #       "
    
    	    # ... whatever else our game needs to know 
``` 

Reload the server with `reload`.

... However, if you use `examine *self` (the asterisk makes you examine your Account object rather than your Character), you won't see your new Attributes yet. This is because `at_account_creation` is only called the very *first* time the Account is called and your Account object already exists (any new Accounts that connect will see them though). To update yourself you need to make sure to re-fire the hook on all the Accounts you have already created. Here is an example of how to do this using `py`:

``` py [account.at_account_creation() for account in evennia.managers.accounts.all()] ```

You should now see the Attributes on yourself.

> If you wanted Evennia to default to a completely *different* Account class located elsewhere, you > must point Evennia to it. Add `BASE_ACCOUNT_TYPECLASS` to your settings file, and give the python path to your custom class as its value. By default this points to `typeclasses.accounts.Account`, the empty template we used above.


### Properties on Accounts

Beyond those properties assigned to all typeclassed objects (see [Typeclasses](./Typeclasses.md)), the Account also has the following custom properties:

- `user` - a unique link to a `User` Django object, representing the logged-in user.
- `obj` - an alias for `character`.
- `name` - an alias for `user.username`
- `sessions` - an instance of [ObjectSessionHandler](github:evennia.objects.objects#objectsessionhandler) managing all connected Sessions (physical connections) this object listens to (Note: In older versions of Evennia, this was a list). The so-called `session-id` (used in many places) is found as a property `sessid` on each Session instance.
- `is_superuser` (bool: True/False) - if this account is a superuser.

Special handlers:
- `cmdset` - This holds all the current [Commands](./Commands.md) of this Account. By default these are
  the commands found in the cmdset defined by `settings.CMDSET_ACCOUNT`.
- `nicks` - This stores and handles [Nicks](./Nicks.md), in the same way as nicks it works on Objects. For Accounts, nicks are primarily used to store custom aliases for [Channels](./Channels.md).

Selection of special methods (see `evennia.DefaultAccount` for details):
- `get_puppet` - get a currently puppeted object connected to the Account and a given session id, if any.
- `puppet_object` - connect a session to a puppetable Object.
- `unpuppet_object` - disconnect a session from a puppetable Object.
- `msg` - send text to the Account
- `execute_cmd` - runs a command as if this Account did it.
- `search` - search for Accounts.