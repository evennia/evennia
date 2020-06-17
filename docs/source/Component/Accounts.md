# Accounts


All *users* (real people) that starts a game [Session](Sessions) on Evennia are doing so through an
object called *Account*. The Account object has no in-game representation, it represents a unique
game account.  In order to actually get on the game the Account must *puppet* an [Object](Objects)
(normally a [Character](Objects#Character)). 

Exactly how many Sessions can interact with an Account and its Puppets at once is determined by
Evennia's [MULTISESSION_MODE](Sessions#Multisession-mode) setting.

Apart from storing login information and other account-specific data, the Account object is what is
chatting on [Channels](Communications).  It is also a good place to store [Permissions](Locks) to be
consistent between different in-game characters as well as configuration options.  The Account
object also has its own [CmdSet](Command-Sets), the `AccountCmdSet`. 

Logged into default evennia, you can use the `ooc` command to leave your current
[character](Objects) and go into OOC mode. You are quite limited in this mode, basically it works
like a simple chat program.  It acts as a staging area for switching between Characters (if your
game supports that) or as a safety mode if your Character gets deleted. Use `ic` to attempt to
(re)puppet a Character. 

Note that the Account object can have, and often does have, a different set of
[Permissions](Locks#Permissions) from the Character they control.  Normally you should put your
permissions on the Account level - this will overrule permissions set on the Character level. For
the permissions of the Character to come into play the default `quell` command can be used. This
allows for exploring the game using a different permission set (but you can't escalate your
permissions this way - for hierarchical permissions like `Builder`, `Admin` etc, the *lower* of the
permissions on the Character/Account will always be used). 

## How to create your own Account types

You will usually not want more than one Account typeclass for all new accounts (but you could in
principle create a system that changes an account's typeclass dynamically). 

An Evennia Account is, per definition, a Python class that includes `evennia.DefaultAccount` among
its parents. In `mygame/typeclasses/accounts.py` there is an empty class ready for you to modify.
Evennia defaults to using this (it inherits directly from `DefaultAccount`). 

Here's an example of modifying the default Account class in code: 

```python 
    # in mygame/typeclasses/accounts.py

    from evennia import DefaultAccount

    class Account(DefaultAccount): # [...]

	at_account_creation(self): "this is called only once, when account is first created"
	    self.db.real_name = None      # this is set later self.db.real_address = None   #       "
	    self.db.config_1 = True       # default config self.db.config_2 = False      #       "
	    self.db.config_3 = 1          #       "

	    # ... whatever else our game needs to know ``` Reload the server with `reload`. 

```

... However, if you use `examine *self` (the asterisk makes you examine your Account object rather
than your Character), you won't see your new Attributes yet. This is because `at_account_creation`
is only called the very *first* time the Account is called and your Account object already exists
(any new Accounts that connect will see them though). To update yourself you need to make sure to
re-fire the hook on all the Accounts you have already created. Here is an example of how to do this
using `py`:


``` py [account.at_account_creation() for account in evennia.managers.accounts.all()] ```

You should now see the Attributes on yourself. 


> If you wanted Evennia to default to a completely *different* Account class located elsewhere, you
> must point Evennia to it. Add `BASE_ACCOUNT_TYPECLASS` to your settings file, and give the python
> path to your custom class as its value. By default this points to `typeclasses.accounts.Account`,
> the empty template we used above.


## Properties on Accounts

Beyond those properties assigned to all typeclassed objects (see [Typeclasses](Typeclasses)), the
Account also has the following custom properties: 

- `user` - a unique link to a `User` Django object, representing the logged-in user.
- `obj` - an alias for `character`.
- `name` - an alias for `user.username`
- `sessions` - an instance of
  [ObjectSessionHandler](github:evennia.objects.objects#objectsessionhandler)
  managing all connected Sessions (physical connections) this object listens to (Note: In older
  versions of Evennia, this was a list). The so-called `session-id` (used in many places) is found
as
  a property `sessid` on each Session instance.
- `is_superuser` (bool: True/False) - if this account is a superuser.

Special handlers:
- `cmdset` - This holds all the current [Commands](Commands) of this Account. By default these are
  the commands found in the cmdset defined by `settings.CMDSET_ACCOUNT`.
- `nicks` - This stores and handles [Nicks](Nicks), in the same way as nicks it works on Objects.
  For Accounts, nicks are primarily used to store custom aliases for
[Channels](Communications#Channels).
 
Selection of special methods (see `evennia.DefaultAccount` for details):
- `get_puppet` - get a currently puppeted object connected to the Account and a given session id, if
  any.
- `puppet_object` - connect a session to a puppetable Object.
- `unpuppet_object` - disconnect a session from a puppetable Object.
- `msg` - send text to the Account
- `execute_cmd` - runs a command as if this Account did it.
- `search` - search for Accounts.