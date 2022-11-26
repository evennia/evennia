# Character connection styles

```shell
> login Foobar password123
```

Evennia supports multiple ways for players to connect to the game. This allows Evennia to mimic the behavior of various other servers, or open things up for a custom solution. 

## Changing the login screen

This is done by modifying `mygame/server/conf/connection_screens.py` and reloading. If you don't like the default login, there are two contribs to check out as inspiration.

- [Email login](../Contribs/Contrib-Email-Login.md) - require email during install, use email for login.
- [Menu login](../Contribs/Contrib-Menu-Login.md) - login using several prompts, asking to enter username and password in sequence.

## Customizing the login command

When a player connects to the game, it runs the `CMD_LOGINSTART` [system command](../Components/Commands.md#system-commands). By default, this is the [CmdUnconnectedLook](evennia.commands.default.unloggedin.CmdUnconnectedLook). This shows the welcome screen. The other commands in the [UnloggedinCmdSet](evennia.commands.default.cmdset_unloggedin.UnloggedinCmdSet) are what defines the login experience. So if you want to customise it, you just need to replace/remove those commands. 

```{sidebar}
If you instead had your command inherit from `default_cmds.UnConnectedLook`, you didn't even have to speciy the key (since your class would inherit it)!
```
```python
# in mygame/commands/mylogin_commands.py

from evennia import syscmdkeys, default_cmds, Command


class MyUnloggedinLook(Command):

    # this will now be the first command called when connecting
    key = syscmdkeys.CMD_LOGINSTART 

    def func(self):
        # ... 
```
 
Next, add this to the right place in the `UnloggedinCmdSet`: 

```python
# in mygame/commands/default_cmdsets.py

from commands.mylogin_commands import MyUnloggedinLook
# ... 

class UnloggedinCmdSet(default_cmds.UnloggedinCmdSet):
    # ... 
    def at_cmdset_creation(self):
        super().at_cmdset_creation
        self.add(MyUnloggedinLook())
```

`reload` and your alternate command will be used. Examine the default commands and you'll be able to change everything about the login. 

## Multisession mode and multi-playing

The multisession modes are described in detail in the [Session documentation](../Components/Sessions.md#multisession-mode). In brief, this is controlled by a [setting](../Setup/Settings.md). Here's the default: 

    MULTISESSION_MODE = 0

- `MULTISESSION_MODE=0`: One [Session](../Components/Sessions.md) per [Account](../Components/Accounts.md), routed to one [puppet](../Components/Objects.md). If connecting with a new session/client, it will kick the previous one. 
- `MULTISESSION_MODE=1`: Multiple sessions per Account, all routed to one puppet. Allows you to control one puppet from multiple client windows.
- `MULTISESSION_MODE=2`: Multiple sessions per Account, each routed to a different puppet. This allows for multi-playing.
- `MULTISESSION_MODE=3`: Multiple sessions per account, And multiple sessions per puppet. This is full multi-playing, including being able to control each puppet from multiple clients.

Mode `0` is the default and mimics how many legacy codebases work, especially in the DIKU world. The equivalence of higher modes are often 'hacked' into existing servers to allow for players to have multiple characters. 

    MAX_NR_SIMULTANEOUS_PUPPETS = 1

This setting limits how many _different_ puppets your _Account_ can puppet _simultaneously_. This is used to limit true multiplaying. A value higher than one makes no sense unless `MULTISESSION_MODE` is also set `>1`.  Set to `None` for no limit.

## Character creation and auto-puppeting

When a player first creates an account, Evennia will auto-create a `Character` puppet of the same name. When the player logs in, they will auto-puppet this Character. This default hides the Account-Character separation from the player and puts them immediately in the game. This default behavior is similar to how it works in many legacy MU servers. 

To control this behavior, you need to tweak the settings. These are the defaults: 

    AUTO_CREATE_CHARACTER_WITH_ACCOUNT = True
    AUTO_PUPPET_ON_LOGIN = True 
    MAX_NR_CHARACTERS = 1
    
There is a default `charcreate` command. This heeds the `MAX_NR_CHARACTERS`; and if you make your own character-creation command, you should do the same. It needs to be at least `1`. Set to `None` for no limit. See the [Beginner Tutorial](../Howtos/Beginner-Tutorial/Beginner-Tutorial-Overview.md) for ideas on how to make a more advanced character generation system.

```{sidebar}
Combining these settings with `MAX_NR_SIMULTANEOUS_PUPPETS` could allow for a game where (for example) a player can create a 'stable' of Characters, but only be able to play one at a time. 
```
If you choose to not auto-create a character, you will need to provide a character-generation, and there will be no (initial) Character to puppet. In both of these settings, you will initially end up in  `ooc` mode after you login. This is a good place to put a character generation screen/menu (you can e.g. replace the [CmdOOCLook](evennia.commands.default.account.CmdOOCLook) to trigger something other than the normal ooc-look). 

Once you created a Character, if your auto-puppet is set, you will automatically puppet your latest-puppeted Character whenever you login. If not set, you will always start OOC (and should be able to select which Character to puppet).

