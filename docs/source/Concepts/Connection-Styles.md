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

The number of sessions possible to connect to a given account at the same time and how it works is given by the `MULTISESSION_MODE` setting:

* `MULTISESSION_MODE=0`: One session per account. When connecting with a new session the old one is disconnected. This is the default mode and emulates many classic mud code bases.
    ```
    ┌──────┐ │   ┌───────┐    ┌───────┐   ┌─────────┐
    │Client├─┼──►│Session├───►│Account├──►│Character│
    └──────┘ │   └───────┘    └───────┘   └─────────┘
    ```
* `MULTISESSION_MODE=1`: Many sessions per account, input/output from/to each session is treated the same. For the player this means they can connect to the game from multiple clients and see the same output in all of them. The result of a command given in one client (that is, through one Session) will be returned to *all* connected Sessions/clients with no distinction.       
    ```
             │
    ┌──────┐ │   ┌───────┐
    │Client├─┼──►│Session├──┐
    └──────┘ │   └───────┘  └──►┌───────┐   ┌─────────┐
             │                  │Account├──►│Character│
    ┌──────┐ │   ┌───────┐  ┌──►└───────┘   └─────────┘
    │Client├─┼──►│Session├──┘
    └──────┘ │   └───────┘
             │
    ```

* `MULTISESSION_MODE=2`: Many sessions per account, one character per session. In this mode, puppeting an Object/Character will link the puppet back only to the particular Session doing the puppeting. That is, input from that Session will make use of the CmdSet of that Object/Character and outgoing messages (such as the result of a `look`) will be passed back only to that puppeting Session. If another Session tries to puppet the same Character, the old Session will automatically un-puppet it. From the player's perspective, this will mean that they can open separate game clients and play a different Character in each using one game account.
    ```
             │                 ┌───────┐
    ┌──────┐ │   ┌───────┐     │Account│    ┌─────────┐
    │Client├─┼──►│Session├──┐  │       │  ┌►│Character│
    └──────┘ │   └───────┘  └──┼───────┼──┘ └─────────┘
             │                 │       │
    ┌──────┐ │   ┌───────┐  ┌──┼───────┼──┐ ┌─────────┐
    │Client├─┼──►│Session├──┘  │       │  └►│Character│
    └──────┘ │   └───────┘     │       │    └─────────┘
             │                 └───────┘
    ```
* `MULTISESSION_MODE=3`: Many sessions per account *and* character. This is the full multi-puppeting mode, where multiple sessions may not only connect to the player account but multiple sessions may also puppet a single character at the same time. From the user's perspective it means one can open multiple client windows, some for controlling different Characters and some that share a Character's input/output like in mode 1. This mode otherwise works the same as mode 2.
    ```
             │                 ┌───────┐
    ┌──────┐ │   ┌───────┐     │Account│    ┌─────────┐
    │Client├─┼──►│Session├──┐  │       │  ┌►│Character│
    └──────┘ │   └───────┘  └──┼───────┼──┘ └─────────┘
             │                 │       │
    ┌──────┐ │   ┌───────┐  ┌──┼───────┼──┐
    │Client├─┼──►│Session├──┘  │       │  └►┌─────────┐
    └──────┘ │   └───────┘     │       │    │Character│
             │                 │       │  ┌►└─────────┘
    ┌──────┐ │   ┌───────┐  ┌──┼───────┼──┘             ▼
    │Client├─┼──►│Session├──┘  │       │
    └──────┘ │   └───────┘     └───────┘
             │
    ```

> Note that even if multiple Sessions puppet one Character, there is only ever one instance of that Character.

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

