# Default Command Help


> *This page is auto-generated. Do not modify - your changes will be lost. Report problems to the
[issue tracker](https://github.com/evennia/evennia/issues).*

The full set of default Evennia commands currently contains 92 commands in 9 source
files.  Our policy for adding default commands is outlined [here](Using-MUX-as-a-Standard). More
information about how commands work can be found in the documentation for [Commands](Commands).



## A-Z

- [`__unloggedin_look_command`](https://github.com/evennia/evennia/wiki/Default-Command-
Help#wiki-`--unloggedin-look-command`-cmdunconnectedlook) - look when in unlogged-in state
- [about](Default-Command-Help#wiki-about-cmdabout) - show Evennia info
- [access](Default-Command-Help#wiki-access-cmdaccess) - show your current game access
- [addcom](Default-Command-Help#wiki-addcom-cmdaddcom) - add a channel alias and/or subscribe to a
channel
- [alias](Default-Command-Help#wiki-alias-cmdsetobjalias) - adding permanent aliases for object
- [allcom](Default-Command-Help#wiki-allcom-cmdallcom) - perform admin operations on all channels
- [ban](Default-Command-Help#wiki-ban-cmdban) - ban an account from the server
- [batchcode](Default-Command-Help#wiki-batchcode-cmdbatchcode) - build from batch-code file
- [batchcommands](Default-Command-Help#wiki-batchcommands-cmdbatchcommands) - build from batch-
command file
- [boot](Default-Command-Help#wiki-boot-cmdboot) - kick an account from the server.
- [cboot](Default-Command-Help#wiki-cboot-cmdcboot) - kick an account from a channel you control
- [ccreate](Default-Command-Help#wiki-ccreate-cmdchannelcreate) - create a new channel
- [cdesc](Default-Command-Help#wiki-cdesc-cmdcdesc) - describe a channel you control
- [cdestroy](Default-Command-Help#wiki-cdestroy-cmdcdestroy) - destroy a channel you created
- [cemit](Default-Command-Help#wiki-cemit-cmdcemit) - send an admin message to a channel you control
- [channels](Default-Command-Help#wiki-channels-cmdchannels) - list all channels available to you
- [charcreate](Default-Command-Help#wiki-charcreate-cmdcharcreate) - create a new character
- [chardelete](Default-Command-Help#wiki-chardelete-cmdchardelete) - delete a character - this
cannot be undone!
- [clock](Default-Command-Help#wiki-clock-cmdclock) - change channel locks of a channel you control
- [cmdsets](Default-Command-Help#wiki-cmdsets-cmdlistcmdsets) - list command sets defined on an
object
- [color](Default-Command-Help#wiki-color-cmdcolortest) - testing which colors your client support
- [command](Default-Command-Help#wiki-command-objmanipcommand) - This is a parent class for some of
the defining objmanip commands
- [connect](Default-Command-Help#wiki-connect-cmdunconnectedconnect) - connect to the game
- [copy](Default-Command-Help#wiki-copy-cmdcopy) - copy an object and its properties
- [cpattr](Default-Command-Help#wiki-cpattr-cmdcpattr) - copy attributes between objects
- [create](Default-Command-Help#wiki-create-cmdunconnectedcreate) - create a new account account
- [create](Default-Command-Help#wiki-create-cmdcreate) - create new objects
- [cwho](Default-Command-Help#wiki-cwho-cmdcwho) - show who is listening to a channel
- [delcom](Default-Command-Help#wiki-delcom-cmddelcom) - remove a channel alias and/or unsubscribe
from channel
- [desc](Default-Command-Help#wiki-desc-cmddesc) - describe an object or the current room.
- [destroy](Default-Command-Help#wiki-destroy-cmddestroy) - permanently delete objects
- [dig](Default-Command-Help#wiki-dig-cmddig) - build new rooms and connect them to the current
location
- [drop](Default-Command-Help#wiki-drop-cmddrop) - drop something
- [emit](Default-Command-Help#wiki-emit-cmdemit) - admin command for emitting message to multiple
objects
- [examine](Default-Command-Help#wiki-examine-cmdexamine) - get detailed information about an object
- [find](Default-Command-Help#wiki-find-cmdfind) - search the database for objects
- [force](Default-Command-Help#wiki-force-cmdforce) - forces an object to execute a command
- [get](Default-Command-Help#wiki-get-cmdget) - pick up something
- [give](Default-Command-Help#wiki-give-cmdgive) - give away something to someone
- [help](Default-Command-Help#wiki-help-cmdunconnectedhelp) - get help when in unconnected-in state
- [help](Default-Command-Help#wiki-help-cmdhelp) - View help or a list of topics
- [home](Default-Command-Help#wiki-home-cmdhome) - move to your character's home location
- [ic](Default-Command-Help#wiki-ic-cmdic) - control an object you have permission to puppet
- [inventory](Default-Command-Help#wiki-inventory-cmdinventory) - view inventory
- [irc2chan](Default-Command-Help#wiki-irc2chan-cmdirc2chan) - Link an evennia channel to an
external IRC channel
- [link](Default-Command-Help#wiki-link-cmdlink) - link existing rooms together with exits
- [lock](Default-Command-Help#wiki-lock-cmdlock) - assign a lock definition to an object
- [look](Default-Command-Help#wiki-look-cmdlook) - look at location or object
- [look](Default-Command-Help#wiki-look-cmdooclook) - look while out-of-character
- [mvattr](Default-Command-Help#wiki-mvattr-cmdmvattr) - move attributes between objects
- [name](Default-Command-Help#wiki-name-cmdname) - change the name and/or aliases of an object
- [nick](Default-Command-Help#wiki-nick-cmdnick) - define a personal alias/nick by defining a string
to
- [objects](Default-Command-Help#wiki-objects-cmdobjects) - statistics on objects in the database
- [ooc](Default-Command-Help#wiki-ooc-cmdooc) - stop puppeting and go ooc
- [open](Default-Command-Help#wiki-open-cmdopen) - open a new exit from the current room
- [option](Default-Command-Help#wiki-option-cmdoption) - Set an account option
- [page](Default-Command-Help#wiki-page-cmdpage) - send a private message to another account
- [password](Default-Command-Help#wiki-password-cmdpassword) - change your password
- [perm](Default-Command-Help#wiki-perm-cmdperm) - set the permissions of an account/object
- [pose](Default-Command-Help#wiki-pose-cmdpose) - strike a pose
- [py](Default-Command-Help#wiki-py-cmdpy) - execute a snippet of python code
- [quell](Default-Command-Help#wiki-quell-cmdquell) - use character's permissions instead of
account's
- [quit](Default-Command-Help#wiki-quit-cmdunconnectedquit) - quit when in unlogged-in state
- [quit](Default-Command-Help#wiki-quit-cmdquit) - quit the game
- [reload](Default-Command-Help#wiki-reload-cmdreload) - reload the server
- [reset](Default-Command-Help#wiki-reset-cmdreset) - reset and reboot the server
- [rss2chan](Default-Command-Help#wiki-rss2chan-cmdrss2chan) - link an evennia channel to an
external RSS feed
- [say](Default-Command-Help#wiki-say-cmdsay) - speak as your character
- [script](Default-Command-Help#wiki-script-cmdscript) - attach a script to an object
- [scripts](Default-Command-Help#wiki-scripts-cmdscripts) - list and manage all running scripts
- [server](Default-Command-Help#wiki-server-cmdserverload) - show server load and memory statistics
- [service](Default-Command-Help#wiki-service-cmdservice) - manage system services
- [sessions](Default-Command-Help#wiki-sessions-cmdsessions) - check your connected session(s)
- [set](Default-Command-Help#wiki-set-cmdsetattribute) - set attribute on an object or account
- [setdesc](Default-Command-Help#wiki-setdesc-cmdsetdesc) - describe yourself
- [sethelp](Default-Command-Help#wiki-sethelp-cmdsethelp) - Edit the help database.
- [sethome](Default-Command-Help#wiki-sethome-cmdsethome) - set an object's home location
- [shutdown](Default-Command-Help#wiki-shutdown-cmdshutdown) - stop the server completely
- [spawn](Default-Command-Help#wiki-spawn-cmdspawn) - spawn objects from prototype
- [style](Default-Command-Help#wiki-style-cmdstyle) - In-game style options
- [tag](Default-Command-Help#wiki-tag-cmdtag) - handles the tags of an object
- [tel](Default-Command-Help#wiki-tel-cmdteleport) - teleport object to another location
- [time](Default-Command-Help#wiki-time-cmdtime) - show server time statistics
- [tunnel](Default-Command-Help#wiki-tunnel-cmdtunnel) - create new rooms in cardinal directions
only
- [typeclass](Default-Command-Help#wiki-typeclass-cmdtypeclass) - set or change an object's
typeclass
- [unban](Default-Command-Help#wiki-unban-cmdunban) - remove a ban from an account
- [unlink](Default-Command-Help#wiki-unlink-cmdunlink) - remove exit-connections between rooms
- [userpassword](Default-Command-Help#wiki-userpassword-cmdnewpassword) - change the password of an
account
- [wall](Default-Command-Help#wiki-wall-cmdwall) - make an announcement to all
- [whisper](Default-Command-Help#wiki-whisper-cmdwhisper) - Speak privately as your character to
another
- [who](Default-Command-Help#wiki-who-cmdwho) - list who is currently online
- [wipe](Default-Command-Help#wiki-wipe-cmdwipe) - clear all attributes from an object

## A-Z by source file

- [account.py](Default-Command-Help#accountpy)
- [admin.py](Default-Command-Help#adminpy)
- [batchprocess.py](Default-Command-Help#batchprocesspy)
- [building.py](Default-Command-Help#buildingpy)
- [comms.py](Default-Command-Help#commspy)
- [general.py](Default-Command-Help#generalpy)
- [help.py](Default-Command-Help#helppy)
- [system.py](Default-Command-Help#systempy)
- [unloggedin.py](Default-Command-Help#unloggedinpy)

## Command details

These are generated from the auto-documentation and are ordered by their source file location in
[evennia/commands/default/](https://github.com/evennia/evennia/tree/master/evennia/commands/default/)


### `account.py`

[View account.py
source](https://github.com/evennia/evennia/tree/master/evennia/commands/default/account.py)


#### charcreate (CmdCharCreate)
```
    create a new character

    Usage:
      charcreate <charname> [= desc]

    Create a new character, optionally giving it a description. You
    may use upper-case letters in the name - you will nevertheless
    always be able to access your character using lower-case letters
    if you want.
```
- **key:** *charcreate*
- **aliases:** 
- **[locks](Locks):** *"cmd:pperm(Player)"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdCharCreate` in
[account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/account.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### chardelete (CmdCharDelete)
```
    delete a character - this cannot be undone!

    Usage:
        chardelete <charname>

    Permanently deletes one of your characters.
```
- **key:** *chardelete*
- **aliases:** 
- **[locks](Locks):** *"cmd:pperm(Player)"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdCharDelete` in
[account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/account.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### color (CmdColorTest)
```
    testing which colors your client support

    Usage:
      color ansi||xterm256

    Prints a color map along with in-mud color codes to use to produce
    them.  It also tests what is supported in your client. Choices are
    16-color ansi (supported in most muds) or the 256-color xterm256
    standard. No checking is done to determine your client supports
    color - if not you will see rubbish appear.
```
- **key:** *color*
- **aliases:** 
- **[locks](Locks):** *"cmd:all()"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdColorTest` in
[account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/account.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### ic (CmdIC)
```
    control an object you have permission to puppet

    Usage:
      ic <character>

    Go in-character (IC) as a given Character.

    This will attempt to "become" a different object assuming you have
    the right to do so. Note that it's the ACCOUNT character that puppets
    characters/objects and which needs to have the correct permission!

    You cannot become an object that is already controlled by another
    account. In principle <character> can be any in-game object as long
    as you the account have access right to puppet it.
```
- **key:** *ic*
- **aliases:** *puppet*
- **[locks](Locks):** *"cmd:all()"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdIC` in
[account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/account.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### look (CmdOOCLook)
```
    look while out-of-character

    Usage:
      look

    Look in the ooc state.
```
- **key:** *look*
- **aliases:** *l*, *ls*
- **[locks](Locks):** *"cmd:all()"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdOOCLook` in
[account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/account.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### ooc (CmdOOC)
```
    stop puppeting and go ooc

    Usage:
      ooc

    Go out-of-character (OOC).

    This will leave your current character and put you in a incorporeal OOC state.
```
- **key:** *ooc*
- **aliases:** *unpuppet*
- **[locks](Locks):** *"cmd:pperm(Player)"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdOOC` in
[account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/account.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### option (CmdOption)
```
    Set an account option

    Usage:
      option[/save] [name = value]

    Switches:
      save - Save the current option settings for future logins.
      clear - Clear the saved options.

    This command allows for viewing and setting client interface
    settings. Note that saved options may not be able to be used if
    later connecting with a client with different capabilities.
```
- **key:** *option*
- **aliases:** *options*
- **[locks](Locks):** *"cmd:all()"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdOption` in
[account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/account.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### password (CmdPassword)
```
    change your password

    Usage:
      password <old password> = <new password>

    Changes your password. Make sure to pick a safe one.
```
- **key:** *password*
- **aliases:** 
- **[locks](Locks):** *"cmd:pperm(Player)"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdPassword` in
[account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/account.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### quell (CmdQuell)
```
    use character's permissions instead of account's

    Usage:
      quell
      unquell

    Normally the permission level of the Account is used when puppeting a
    Character/Object to determine access. This command will switch the lock
    system to make use of the puppeted Object's permissions instead. This is
    useful mainly for testing.
    Hierarchical permission quelling only work downwards, thus an Account cannot
    use a higher-permission Character to escalate their permission level.
    Use the unquell command to revert back to normal operation.
```
- **key:** *quell*
- **aliases:** *unquell*
- **[locks](Locks):** *"cmd:pperm(Player)"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdQuell` in
[account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/account.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### quit (CmdQuit)
```
    quit the game

    Usage:
      quit

    Switch:
      all - disconnect all connected sessions

    Gracefully disconnect your current session from the
    game. Use the /all switch to disconnect from all sessions.
```
- **key:** *quit*
- **aliases:** 
- **[locks](Locks):** *"cmd:all()"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdQuit` in
[account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/account.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### sessions (CmdSessions)
```
    check your connected session(s)

    Usage:
      sessions

    Lists the sessions currently connected to your account.
```
- **key:** *sessions*
- **aliases:** 
- **[locks](Locks):** *"cmd:all()"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdSessions` in
[account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/account.py).
Belongs to command set *'DefaultSession'* of class `SessionCmdSet` in
[cmdset_session.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_session.py).


#### style (CmdStyle)
```
    In-game style options

    Usage:
      style
      style <option> = <value>

    Configure stylings for in-game display elements like table borders, help
    entriest etc. Use without arguments to see all available options.
```
- **key:** *style*
- **aliases:** 
- **[locks](Locks):** *"cmd:all()"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdStyle` in
[account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/account.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### who (CmdWho)
```
    list who is currently online

    Usage:
      who
      doing

    Shows who is currently online. Doing is an alias that limits info
    also for those with all permissions.
```
- **key:** *who*
- **aliases:** *doing*
- **[locks](Locks):** *"cmd:all()"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdWho` in
[account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/account.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


### `admin.py`

[View admin.py
source](https://github.com/evennia/evennia/tree/master/evennia/commands/default/admin.py)


#### ban (CmdBan)
```
    ban an account from the server

    Usage:
      ban [<name or ip> [: reason]]

    Without any arguments, shows numbered list of active bans.

    This command bans a user from accessing the game. Supply an optional
    reason to be able to later remember why the ban was put in place.

    It is often preferable to ban an account from the server than to
    delete an account with accounts/delete. If banned by name, that account
    account can no longer be logged into.

    IP (Internet Protocol) address banning allows blocking all access
    from a specific address or subnet. Use an asterisk (*) as a
    wildcard.

    Examples:
      ban thomas             - ban account 'thomas'
      ban/ip 134.233.2.111   - ban specific ip address
      ban/ip 134.233.2.*     - ban all in a subnet
      ban/ip 134.233.*.*     - even wider ban

    A single IP filter can be easy to circumvent by changing computers
    or requesting a new IP address. Setting a wide IP block filter with
    wildcards might be tempting, but remember that it may also
    accidentally block innocent users connecting from the same country
    or region.
```
- **key:** *ban*
- **aliases:** *bans*
- **[locks](Locks):** *"cmd:perm(ban) or perm(Developer)"*
- **[`help_category`](Help-System):** *"Admin"*
- **Source:** class `CmdBan` in
[admin.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/admin.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### boot (CmdBoot)
```
    kick an account from the server.

    Usage
      boot[/switches] <account obj> [: reason]

    Switches:
      quiet - Silently boot without informing account
      sid - boot by session id instead of name or dbref

    Boot an account object from the server. If a reason is
    supplied it will be echoed to the user unless /quiet is set.
```
- **key:** *boot*
- **aliases:** 
- **[locks](Locks):** *"cmd:perm(boot) or perm(Admin)"*
- **[`help_category`](Help-System):** *"Admin"*
- **Source:** class `CmdBoot` in
[admin.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/admin.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### emit (CmdEmit)
```
    admin command for emitting message to multiple objects

    Usage:
      emit[/switches] [<obj>, <obj>, ... =] <message>
      remit           [<obj>, <obj>, ... =] <message>
      pemit           [<obj>, <obj>, ... =] <message>

    Switches:
      room     -  limit emits to rooms only (default)
      accounts -  limit emits to accounts only
      contents -  send to the contents of matched objects too

    Emits a message to the selected objects or to
    your immediate surroundings. If the object is a room,
    send to its contents. remit and pemit are just
    limited forms of emit, for sending to rooms and
    to accounts respectively.
```
- **key:** *emit*
- **aliases:** *remit*, *pemit*
- **[locks](Locks):** *"cmd:perm(emit) or perm(Builder)"*
- **[`help_category`](Help-System):** *"Admin"*
- **Source:** class `CmdEmit` in
[admin.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/admin.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### force (CmdForce)
```
    forces an object to execute a command

    Usage:
        force <object>=<command string>

    Example:
        force bob=get stick
```
- **key:** *force*
- **aliases:** 
- **[locks](Locks):** *"cmd:perm(spawn) or perm(Builder)"*
- **[`help_category`](Help-System):** *"Building"*
- **Source:** class `CmdForce` in
[admin.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/admin.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### perm (CmdPerm)
```
    set the permissions of an account/object

    Usage:
      perm[/switch] <object> [= <permission>[,<permission>,...]]
      perm[/switch] *<account> [= <permission>[,<permission>,...]]

    Switches:
      del     -  delete the given permission from <object> or <account>.
      account -  set permission on an account (same as adding * to name)

    This command sets/clears individual permission strings on an object
    or account. If no permission is given, list all permissions on <object>.
```
- **key:** *perm*
- **aliases:** *setperm*
- **[locks](Locks):** *"cmd:perm(perm) or perm(Developer)"*
- **[`help_category`](Help-System):** *"Admin"*
- **Source:** class `CmdPerm` in
[admin.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/admin.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### unban (CmdUnban)
```
    remove a ban from an account

    Usage:
      unban <banid>

    This will clear an account name/ip ban previously set with the ban
    command.  Use this command without an argument to view a numbered
    list of bans. Use the numbers in this list to select which one to
    unban.
```
- **key:** *unban*
- **aliases:** 
- **[locks](Locks):** *"cmd:perm(unban) or perm(Developer)"*
- **[`help_category`](Help-System):** *"Admin"*
- **Source:** class `CmdUnban` in
[admin.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/admin.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### userpassword (CmdNewPassword)
```
    change the password of an account

    Usage:
      userpassword <user obj> = <new password>

    Set an account's password.
```
- **key:** *userpassword*
- **aliases:** 
- **[locks](Locks):** *"cmd:perm(newpassword) or perm(Admin)"*
- **[`help_category`](Help-System):** *"Admin"*
- **Source:** class `CmdNewPassword` in
[admin.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/admin.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### wall (CmdWall)
```
    make an announcement to all

    Usage:
      wall <message>

    Announces a message to all connected sessions
    including all currently unlogged in.
```
- **key:** *wall*
- **aliases:** 
- **[locks](Locks):** *"cmd:perm(wall) or perm(Admin)"*
- **[`help_category`](Help-System):** *"Admin"*
- **Source:** class `CmdWall` in
[admin.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/admin.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


### `batchprocess.py`

[View batchprocess.py
source](https://github.com/evennia/evennia/tree/master/evennia/commands/default/batchprocess.py)


#### batchcode (CmdBatchCode)
```
    build from batch-code file

    Usage:
     batchcode[/interactive] <python path to file>

    Switch:
       interactive - this mode will offer more control when
                     executing the batch file, like stepping,
                     skipping, reloading etc.
       debug - auto-delete all objects that has been marked as
               deletable in the script file (see example files for
               syntax). This is useful so as to to not leave multiple
               object copies behind when testing out the script.

    Runs batches of commands from a batch-code text file (*.py).
```
- **key:** *batchcode*
- **aliases:** *batchcodes*
- **[locks](Locks):** *"cmd:superuser()"*
- **[`help_category`](Help-System):** *"Building"*
- **Source:** class `CmdBatchCode` in
[batchprocess.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/batchprocess.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### batchcommands (CmdBatchCommands)
```
    build from batch-command file

    Usage:
     batchcommands[/interactive] <python.path.to.file>

    Switch:
       interactive - this mode will offer more control when
                     executing the batch file, like stepping,
                     skipping, reloading etc.

    Runs batches of commands from a batch-cmd text file (*.ev).
```
- **key:** *batchcommands*
- **aliases:** *batchcmd*, *batchcommand*
- **[locks](Locks):** *"cmd:perm(batchcommands) or perm(Developer)"*
- **[`help_category`](Help-System):** *"Building"*
- **Source:** class `CmdBatchCommands` in
[batchprocess.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/batchprocess.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


### `building.py`

[View building.py
source](https://github.com/evennia/evennia/tree/master/evennia/commands/default/building.py)


#### alias (CmdSetObjAlias)
```
    adding permanent aliases for object

    Usage:
      alias <obj> [= [alias[,alias,alias,...]]]
      alias <obj> =
      alias/category <obj> = [alias[,alias,...]:<category>

    Switches:
      category - requires ending input with :category, to store the
        given aliases with the given category.

    Assigns aliases to an object so it can be referenced by more
    than one name. Assign empty to remove all aliases from object. If
    assigning a category, all aliases given will be using this category.

    Observe that this is not the same thing as personal aliases
    created with the 'nick' command! Aliases set with alias are
    changing the object in question, making those aliases usable
    by everyone.
```
- **key:** *alias*
- **aliases:** *setobjalias*
- **[locks](Locks):** *"cmd:perm(setobjalias) or perm(Builder)"*
- **[`help_category`](Help-System):** *"Building"*
- **Source:** class `CmdSetObjAlias` in
[building.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/building.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### cmdsets (CmdListCmdSets)
```
    list command sets defined on an object

    Usage:
      cmdsets <obj>

    This displays all cmdsets assigned
    to a user. Defaults to yourself.
```
- **key:** *cmdsets*
- **aliases:** *listcmsets*
- **[locks](Locks):** *"cmd:perm(listcmdsets) or perm(Builder)"*
- **[`help_category`](Help-System):** *"Building"*
- **Source:** class `CmdListCmdSets` in
[building.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/building.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### command (ObjManipCommand)
```
    This is a parent class for some of the defining objmanip commands
    since they tend to have some more variables to define new objects.

    Each object definition can have several components. First is
    always a name, followed by an optional alias list and finally an
    some optional data, such as a typeclass or a location. A comma ','
    separates different objects. Like this:

        name1;alias;alias;alias:option, name2;alias;alias ...

    Spaces between all components are stripped.

    A second situation is attribute manipulation. Such commands
    are simpler and offer combinations

        objname/attr/attr/attr, objname/attr, ...
```
- **key:** *command*
- **aliases:** 
- **[locks](Locks):** *"cmd:all()"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `ObjManipCommand` in
[building.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/building.py).
Belongs to command set *'<Unknown>'* of class `<Unknown>` in
[](https://github.com/evennia/evennia/tree/master/evennia/commands/default/).


#### copy (CmdCopy)
```
    copy an object and its properties

    Usage:
      copy[/reset] <original obj> [= <new_name>][;alias;alias..]
      [:<new_location>] [,<new_name2> ...]

    switch:
      reset - make a 'clean' copy off the object, thus
              removing any changes that might have been made to the original
              since it was first created.

    Create one or more copies of an object. If you don't supply any targets,
    one exact copy of the original object will be created with the name *_copy.
```
- **key:** *copy*
- **aliases:** 
- **[locks](Locks):** *"cmd:perm(copy) or perm(Builder)"*
- **[`help_category`](Help-System):** *"Building"*
- **Source:** class `CmdCopy` in
[building.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/building.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### cpattr (CmdCpAttr)
```
    copy attributes between objects

    Usage:
      cpattr[/switch] <obj>/<attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
      cpattr[/switch] <obj>/<attr> = <obj1> [,<obj2>,<obj3>,...]
      cpattr[/switch] <attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
      cpattr[/switch] <attr> = <obj1>[,<obj2>,<obj3>,...]

    Switches:
      move - delete the attribute from the source object after copying.

    Example:
      cpattr coolness = Anna/chillout, Anna/nicety, Tom/nicety
      ->
      copies the coolness attribute (defined on yourself), to attributes
      on Anna and Tom.

    Copy the attribute one object to one or more attributes on another object.
    If you don't supply a source object, yourself is used.
```
- **key:** *cpattr*
- **aliases:** 
- **[locks](Locks):** *"cmd:perm(cpattr) or perm(Builder)"*
- **[`help_category`](Help-System):** *"Building"*
- **Source:** class `CmdCpAttr` in
[building.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/building.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### create (CmdCreate)
```
    create new objects

    Usage:
      create[/drop] <objname>[;alias;alias...][:typeclass], <objname>...

    switch:
       drop - automatically drop the new object into your current
              location (this is not echoed). This also sets the new
              object's home to the current location rather than to you.

    Creates one or more new objects. If typeclass is given, the object
    is created as a child of this typeclass. The typeclass script is
    assumed to be located under types/ and any further
    directory structure is given in Python notation. So if you have a
    correct typeclass 'RedButton' defined in
    types/examples/red_button.py, you could create a new
    object of this type like this:

       create/drop button;red : examples.red_button.RedButton
```
- **key:** *create*
- **aliases:** 
- **[locks](Locks):** *"cmd:perm(create) or perm(Builder)"*
- **[`help_category`](Help-System):** *"Building"*
- **Source:** class `CmdCreate` in
[building.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/building.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### desc (CmdDesc)
```
    describe an object or the current room.

    Usage:
      desc [<obj> =] <description>

    Switches:
      edit - Open up a line editor for more advanced editing.

    Sets the "desc" attribute on an object. If an object is not given,
    describe the current room.
```
- **key:** *desc*
- **aliases:** *describe*
- **[locks](Locks):** *"cmd:perm(desc) or perm(Builder)"*
- **[`help_category`](Help-System):** *"Building"*
- **Source:** class `CmdDesc` in
[building.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/building.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### destroy (CmdDestroy)
```
    permanently delete objects

    Usage:
       destroy[/switches] [obj, obj2, obj3, [dbref-dbref], ...]

    Switches:
       override - The destroy command will usually avoid accidentally
                  destroying account objects. This switch overrides this safety.
       force - destroy without confirmation.
    Examples:
       destroy house, roof, door, 44-78
       destroy 5-10, flower, 45
       destroy/force north

    Destroys one or many objects. If dbrefs are used, a range to delete can be
    given, e.g. 4-10. Also the end points will be deleted. This command
    displays a confirmation before destroying, to make sure of your choice.
    You can specify the /force switch to bypass this confirmation.
```
- **key:** *destroy*
- **aliases:** *del*, *delete*
- **[locks](Locks):** *"cmd:perm(destroy) or perm(Builder)"*
- **[`help_category`](Help-System):** *"Building"*
- **Source:** class `CmdDestroy` in
[building.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/building.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### dig (CmdDig)
```
    build new rooms and connect them to the current location

    Usage:
      dig[/switches] <roomname>[;alias;alias...][:typeclass]
            [= <exit_to_there>[;alias][:typeclass]]
               [, <exit_to_here>[;alias][:typeclass]]

    Switches:
       tel or teleport - move yourself to the new room

    Examples:
       dig kitchen = north;n, south;s
       dig house:myrooms.MyHouseTypeclass
       dig sheer cliff;cliff;sheer = climb up, climb down

    This command is a convenient way to build rooms quickly; it creates the
    new room and you can optionally set up exits back and forth between your
    current room and the new one. You can add as many aliases as you
    like to the name of the room and the exits in question; an example
    would be 'north;no;n'.
```
- **key:** *dig*
- **aliases:** 
- **[locks](Locks):** *"cmd:perm(dig) or perm(Builder)"*
- **[`help_category`](Help-System):** *"Building"*
- **Source:** class `CmdDig` in
[building.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/building.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### examine (CmdExamine)
```
    get detailed information about an object

    Usage:
      examine [<object>[/attrname]]
      examine [*<account>[/attrname]]

    Switch:
      account - examine an Account (same as adding *)
      object - examine an Object (useful when OOC)

    The examine command shows detailed game info about an
    object and optionally a specific attribute on it.
    If object is not specified, the current location is examined.

    Append a * before the search string to examine an account.
```
- **key:** *examine*
- **aliases:** *exam*, *ex*
- **[locks](Locks):** *"cmd:perm(examine) or perm(Builder)"*
- **[`help_category`](Help-System):** *"Building"*
- **Source:** class `CmdExamine` in
[building.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/building.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### find (CmdFind)
```
    search the database for objects

    Usage:
      find[/switches] <name or dbref or *account> [= dbrefmin[-dbrefmax]]
      locate - this is a shorthand for using the /loc switch.

    Switches:
      room       - only look for rooms (location=None)
      exit       - only look for exits (destination!=None)
      char       - only look for characters (BASE_CHARACTER_TYPECLASS)
      exact      - only exact matches are returned.
      loc        - display object location if exists and match has one result
      startswith - search for names starting with the string, rather than containing

    Searches the database for an object of a particular name or exact #dbref.
    Use *accountname to search for an account. The switches allows for
    limiting object matches to certain game entities. Dbrefmin and dbrefmax
    limits matches to within the given dbrefs range, or above/below if only
    one is given.
```
- **key:** *find*
- **aliases:** *locate*, *search*
- **[locks](Locks):** *"cmd:perm(find) or perm(Builder)"*
- **[`help_category`](Help-System):** *"Building"*
- **Source:** class `CmdFind` in
[building.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/building.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### link (CmdLink)
```
    link existing rooms together with exits

    Usage:
      link[/switches] <object> = <target>
      link[/switches] <object> =
      link[/switches] <object>

    Switch:
      twoway - connect two exits. For this to work, BOTH <object>
               and <target> must be exit objects.

    If <object> is an exit, set its destination to <target>. Two-way operation
    instead sets the destination to the *locations* of the respective given
    arguments.
    The second form (a lone =) sets the destination to None (same as
    the unlink command) and the third form (without =) just shows the
    currently set destination.
```
- **key:** *link*
- **aliases:** 
- **[locks](Locks):** *"cmd:perm(link) or perm(Builder)"*
- **[`help_category`](Help-System):** *"Building"*
- **Source:** class `CmdLink` in
[building.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/building.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### lock (CmdLock)
```
    assign a lock definition to an object

    Usage:
      lock <object or *account>[ = <lockstring>]
      or
      lock[/switch] <object or *account>/<access_type>

    Switch:
      del - delete given access type
      view - view lock associated with given access type (default)

    If no lockstring is given, shows all locks on
    object.

    Lockstring is of the form
       access_type:[NOT] func1(args)[ AND|OR][ NOT] func2(args) ...]
    Where func1, func2 ... valid lockfuncs with or without arguments.
    Separator expressions need not be capitalized.

    For example:
       'get: id(25) or perm(Admin)'
    The 'get' lock access_type is checked e.g. by the 'get' command.
    An object locked with this example lock will only be possible to pick up
    by Admins or by an object with id=25.

    You can add several access_types after one another by separating
    them by ';', i.e:
       'get:id(25); delete:perm(Builder)'
```
- **key:** *lock*
- **aliases:** *locks*
- **[locks](Locks):** *"cmd: perm(locks) or perm(Builder)"*
- **[`help_category`](Help-System):** *"Building"*
- **Source:** class `CmdLock` in
[building.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/building.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### mvattr (CmdMvAttr)
```
    move attributes between objects

    Usage:
      mvattr[/switch] <obj>/<attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
      mvattr[/switch] <obj>/<attr> = <obj1> [,<obj2>,<obj3>,...]
      mvattr[/switch] <attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
      mvattr[/switch] <attr> = <obj1>[,<obj2>,<obj3>,...]

    Switches:
      copy - Don't delete the original after moving.

    Move an attribute from one object to one or more attributes on another
    object. If you don't supply a source object, yourself is used.
```
- **key:** *mvattr*
- **aliases:** 
- **[locks](Locks):** *"cmd:perm(mvattr) or perm(Builder)"*
- **[`help_category`](Help-System):** *"Building"*
- **Source:** class `CmdMvAttr` in
[building.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/building.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### name (CmdName)
```
    change the name and/or aliases of an object

    Usage:
      name <obj> = <newname>;alias1;alias2

    Rename an object to something new. Use *obj to
    rename an account.
```
- **key:** *name*
- **aliases:** *rename*
- **[locks](Locks):** *"cmd:perm(rename) or perm(Builder)"*
- **[`help_category`](Help-System):** *"Building"*
- **Source:** class `CmdName` in
[building.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/building.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### open (CmdOpen)
```
    open a new exit from the current room

    Usage:
      open <new exit>[;alias;alias..][:typeclass] [,<return exit>[;alias;..][:typeclass]]] =
<destination>

    Handles the creation of exits. If a destination is given, the exit
    will point there. The <return exit> argument sets up an exit at the
    destination leading back to the current room. Destination name
    can be given both as a #dbref and a name, if that name is globally
    unique.
```
- **key:** *open*
- **aliases:** 
- **[locks](Locks):** *"cmd:perm(open) or perm(Builder)"*
- **[`help_category`](Help-System):** *"Building"*
- **Source:** class `CmdOpen` in
[building.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/building.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### script (CmdScript)
```
    attach a script to an object

    Usage:
      script[/switch] <obj> [= script_path or <scriptkey>]

    Switches:
      start - start all non-running scripts on object, or a given script only
      stop - stop all scripts on objects, or a given script only

    If no script path/key is given, lists all scripts active on the given
    object.
    Script path can be given from the base location for scripts as given in
    settings. If adding a new script, it will be started automatically
    (no /start switch is needed). Using the /start or /stop switches on an
    object without specifying a script key/path will start/stop ALL scripts on
    the object.
```
- **key:** *script*
- **aliases:** *addscript*
- **[locks](Locks):** *"cmd:perm(script) or perm(Builder)"*
- **[`help_category`](Help-System):** *"Building"*
- **Source:** class `CmdScript` in
[building.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/building.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### set (CmdSetAttribute)
```
    set attribute on an object or account

    Usage:
      set <obj>/<attr> = <value>
      set <obj>/<attr> =
      set <obj>/<attr>
      set *<account>/<attr> = <value>

    Switch:
        edit: Open the line editor (string values only)
        script: If we're trying to set an attribute on a script
        channel: If we're trying to set an attribute on a channel
        account: If we're trying to set an attribute on an account
        room: Setting an attribute on a room (global search)
        exit: Setting an attribute on an exit (global search)
        char: Setting an attribute on a character (global search)
        character: Alias for char, as above.

    Sets attributes on objects. The second example form above clears a
    previously set attribute while the third form inspects the current value of
    the attribute (if any). The last one (with the star) is a shortcut for
    operating on a player Account rather than an Object.

    The most common data to save with this command are strings and
    numbers. You can however also set Python primitives such as lists,
    dictionaries and tuples on objects (this might be important for
    the functionality of certain custom objects).  This is indicated
    by you starting your value with one of |c'|n, |c"|n, |c(|n, |c[|n
    or |c{ |n.

    Once you have stored a Python primitive as noted above, you can include
    |c[<key>]|n in <attr> to reference nested values in e.g. a list or dict.

    Remember that if you use Python primitives like this, you must
    write proper Python syntax too - notably you must include quotes
    around your strings or you will get an error.
```
- **key:** *set*
- **aliases:** 
- **[locks](Locks):** *"cmd:perm(set) or perm(Builder)"*
- **[`help_category`](Help-System):** *"Building"*
- **Source:** class `CmdSetAttribute` in
[building.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/building.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### sethome (CmdSetHome)
```
    set an object's home location

    Usage:
      sethome <obj> [= <home_location>]
      sethom <obj>

    The "home" location is a "safety" location for objects; they
    will be moved there if their current location ceases to exist. All
    objects should always have a home location for this reason.
    It is also a convenient target of the "home" command.

    If no location is given, just view the object's home location.
```
- **key:** *sethome*
- **aliases:** 
- **[locks](Locks):** *"cmd:perm(sethome) or perm(Builder)"*
- **[`help_category`](Help-System):** *"Building"*
- **Source:** class `CmdSetHome` in
[building.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/building.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### spawn (CmdSpawn)
```
    spawn objects from prototype

    Usage:
      spawn[/noloc] <prototype_key>
      spawn[/noloc] <prototype_dict>

      spawn/search [prototype_keykey][;tag[,tag]]
      spawn/list [tag, tag, ...]
      spawn/show [<prototype_key>]
      spawn/update <prototype_key>

      spawn/save <prototype_dict>
      spawn/edit [<prototype_key>]
      olc     - equivalent to spawn/edit

    Switches:
      noloc - allow location to be None if not specified explicitly. Otherwise,
              location will default to caller's current location.
      search - search prototype by name or tags.
      list - list available prototypes, optionally limit by tags.
      show, examine - inspect prototype by key. If not given, acts like list.
      save - save a prototype to the database. It will be listable by /list.
      delete - remove a prototype from database, if allowed to.
      update - find existing objects with the same prototype_key and update
               them with latest version of given prototype. If given with /save,
               will auto-update all objects with the old version of the prototype
               without asking first.
      edit, olc - create/manipulate prototype in a menu interface.

    Example:
      spawn GOBLIN
      spawn {"key":"goblin", "typeclass":"monster.Monster", "location":"#2"}
      spawn/save {"key": "grunt", prototype: "goblin"};;mobs;edit:all()
    
    Dictionary keys:
      |wprototype_parent  |n - name of parent prototype to use. Required if typeclass is
                        not set. Can be a path or a list for multiple inheritance (inherits
                        left to right). If set one of the parents must have a typeclass.
      |wtypeclass  |n - string. Required if prototype_parent is not set.
      |wkey        |n - string, the main object identifier
      |wlocation   |n - this should be a valid object or #dbref
      |whome       |n - valid object or #dbref
      |wdestination|n - only valid for exits (object or dbref)
      |wpermissions|n - string or list of permission strings
      |wlocks      |n - a lock-string
      |waliases    |n - string or list of strings.
      |wndb_|n<name>  - value of a nattribute (ndb_ is stripped)

      |wprototype_key|n   - name of this prototype. Unique. Used to store/retrieve from db
                            and update existing prototyped objects if desired.
      |wprototype_desc|n  - desc of this prototype. Used in listings
      |wprototype_locks|n - locks of this prototype. Limits who may use prototype
      |wprototype_tags|n  - tags of this prototype. Used to find prototype

      any other keywords are interpreted as Attributes and their values.

    The available prototypes are defined globally in modules set in
    settings.PROTOTYPE_MODULES. If spawn is used without arguments it
    displays a list of available prototypes.
```
- **key:** *spawn*
- **aliases:** *olc*
- **[locks](Locks):** *"cmd:perm(spawn) or perm(Builder)"*
- **[`help_category`](Help-System):** *"Building"*
- **Source:** class `CmdSpawn` in
[building.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/building.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### tag (CmdTag)
```
    handles the tags of an object

    Usage:
      tag[/del] <obj> [= <tag>[:<category>]]
      tag/search <tag>[:<category]

    Switches:
      search - return all objects with a given Tag
      del - remove the given tag. If no tag is specified,
            clear all tags on object.

    Manipulates and lists tags on objects. Tags allow for quick
    grouping of and searching for objects.  If only <obj> is given,
    list all tags on the object.  If /search is used, list objects
    with the given tag.
    The category can be used for grouping tags themselves, but it
    should be used with restrain - tags on their own are usually
    enough to for most grouping schemes.
```
- **key:** *tag*
- **aliases:** *tags*
- **[locks](Locks):** *"cmd:perm(tag) or perm(Builder)"*
- **[`help_category`](Help-System):** *"Building"*
- **Source:** class `CmdTag` in
[building.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/building.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### tel (CmdTeleport)
```
    teleport object to another location

    Usage:
      tel/switch [<object> to||=] <target location>

    Examples:
      tel Limbo
      tel/quiet box = Limbo
      tel/tonone box

    Switches:
      quiet  - don't echo leave/arrive messages to the source/target
               locations for the move.
      intoexit - if target is an exit, teleport INTO
                 the exit object instead of to its destination
      tonone - if set, teleport the object to a None-location. If this
               switch is set, <target location> is ignored.
               Note that the only way to retrieve
               an object from a None location is by direct #dbref
               reference. A puppeted object cannot be moved to None.
      loc - teleport object to the target's location instead of its contents

    Teleports an object somewhere. If no object is given, you yourself are
    teleported to the target location.
```
- **key:** *tel*
- **aliases:** *teleport*
- **[locks](Locks):** *"cmd:perm(teleport) or perm(Builder)"*
- **[`help_category`](Help-System):** *"Building"*
- **Source:** class `CmdTeleport` in
[building.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/building.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### tunnel (CmdTunnel)
```
    create new rooms in cardinal directions only

    Usage:
      tunnel[/switch] <direction>[:typeclass] [= <roomname>[;alias;alias;...][:typeclass]]

    Switches:
      oneway - do not create an exit back to the current location
      tel - teleport to the newly created room

    Example:
      tunnel n
      tunnel n = house;mike's place;green building

    This is a simple way to build using pre-defined directions:
     |wn,ne,e,se,s,sw,w,nw|n (north, northeast etc)
     |wu,d|n (up and down)
     |wi,o|n (in and out)
    The full names (north, in, southwest, etc) will always be put as
    main name for the exit, using the abbreviation as an alias (so an
    exit will always be able to be used with both "north" as well as
    "n" for example). Opposite directions will automatically be
    created back from the new room unless the /oneway switch is given.
    For more flexibility and power in creating rooms, use dig.
```
- **key:** *tunnel*
- **aliases:** *tun*
- **[locks](Locks):** *"cmd: perm(tunnel) or perm(Builder)"*
- **[`help_category`](Help-System):** *"Building"*
- **Source:** class `CmdTunnel` in
[building.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/building.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### typeclass (CmdTypeclass)
```
    set or change an object's typeclass

    Usage:
      typeclass[/switch] <object> [= typeclass.path]
      typeclass/prototype <object> = prototype_key

      typeclass/list/show [typeclass.path]
      swap - this is a shorthand for using /force/reset flags.
      update - this is a shorthand for using the /force/reload flag.

    Switch:
      show, examine - display the current typeclass of object (default) or, if
            given a typeclass path, show the docstring of that typeclass.
      update - *only* re-run at_object_creation on this object
              meaning locks or other properties set later may remain.
      reset - clean out *all* the attributes and properties on the
              object - basically making this a new clean object.
      force - change to the typeclass also if the object
              already has a typeclass of the same name.
      list - show available typeclasses. Only typeclasses in modules actually
             imported or used from somewhere in the code will show up here
             (those typeclasses are still available if you know the path)
      prototype - clean and overwrite the object with the specified
               prototype key - effectively making a whole new object.

    Example:
      type button = examples.red_button.RedButton
      type/prototype button=a red button

    If the typeclass_path is not given, the current object's typeclass is
    assumed.

    View or set an object's typeclass. If setting, the creation hooks of the
    new typeclass will be run on the object. If you have clashing properties on
    the old class, use /reset. By default you are protected from changing to a
    typeclass of the same name as the one you already have - use /force to
    override this protection.

    The given typeclass must be identified by its location using python
    dot-notation pointing to the correct module and class. If no typeclass is
    given (or a wrong typeclass is given). Errors in the path or new typeclass
    will lead to the old typeclass being kept. The location of the typeclass
    module is searched from the default typeclass directory, as defined in the
    server settings.
```
- **key:** *typeclass*
- **aliases:** *swap*, *parent*, *type*, *update*
- **[locks](Locks):** *"cmd:perm(typeclass) or perm(Builder)"*
- **[`help_category`](Help-System):** *"Building"*
- **Source:** class `CmdTypeclass` in
[building.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/building.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### unlink (CmdUnLink)
```
    remove exit-connections between rooms

    Usage:
      unlink <Object>

    Unlinks an object, for example an exit, disconnecting
    it from whatever it was connected to.
```
- **key:** *unlink*
- **aliases:** 
- **[locks](Locks):** *"cmd:perm(unlink) or perm(Builder)"*
- **[`help_category`](Help-System):** *"Building"*
- **Source:** class `CmdUnLink` in
[building.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/building.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### wipe (CmdWipe)
```
    clear all attributes from an object

    Usage:
      wipe <object>[/<attr>[/<attr>...]]

    Example:
      wipe box
      wipe box/colour

    Wipes all of an object's attributes, or optionally only those
    matching the given attribute-wildcard search string.
```
- **key:** *wipe*
- **aliases:** 
- **[locks](Locks):** *"cmd:perm(wipe) or perm(Builder)"*
- **[`help_category`](Help-System):** *"Building"*
- **Source:** class `CmdWipe` in
[building.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/building.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


### `comms.py`

[View comms.py
source](https://github.com/evennia/evennia/tree/master/evennia/commands/default/comms.py)


#### addcom (CmdAddCom)
```
    add a channel alias and/or subscribe to a channel

    Usage:
       addcom [alias=] <channel>

    Joins a given channel. If alias is given, this will allow you to
    refer to the channel by this alias rather than the full channel
    name. Subsequent calls of this command can be used to add multiple
    aliases to an already joined channel.
```
- **key:** *addcom*
- **aliases:** *aliaschan*, *chanalias*
- **[locks](Locks):** *"cmd:not pperm(channel_banned)"*
- **[`help_category`](Help-System):** *"Comms"*
- **Source:** class `CmdAddCom` in
[comms.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/comms.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### allcom (CmdAllCom)
```
    perform admin operations on all channels

    Usage:
      allcom [on | off | who | destroy]

    Allows the user to universally turn off or on all channels they are on, as
    well as perform a 'who' for all channels they are on. Destroy deletes all
    channels that you control.

    Without argument, works like comlist.
```
- **key:** *allcom*
- **aliases:** 
- **[locks](Locks):** *"cmd: not pperm(channel_banned)"*
- **[`help_category`](Help-System):** *"Comms"*
- **Source:** class `CmdAllCom` in
[comms.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/comms.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### cboot (CmdCBoot)
```
    kick an account from a channel you control

    Usage:
       cboot[/quiet] <channel> = <account> [:reason]

    Switch:
       quiet - don't notify the channel

    Kicks an account or object from a channel you control.
```
- **key:** *cboot*
- **aliases:** 
- **[locks](Locks):** *"cmd: not pperm(channel_banned)"*
- **[`help_category`](Help-System):** *"Comms"*
- **Source:** class `CmdCBoot` in
[comms.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/comms.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### ccreate (CmdChannelCreate)
```
    create a new channel

    Usage:
     ccreate <new channel>[;alias;alias...] = description

    Creates a new channel owned by you.
```
- **key:** *ccreate*
- **aliases:** *channelcreate*
- **[locks](Locks):** *"cmd:not pperm(channel_banned) and pperm(Player)"*
- **[`help_category`](Help-System):** *"Comms"*
- **Source:** class `CmdChannelCreate` in
[comms.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/comms.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### cdesc (CmdCdesc)
```
    describe a channel you control

    Usage:
      cdesc <channel> = <description>

    Changes the description of the channel as shown in
    channel lists.
```
- **key:** *cdesc*
- **aliases:** 
- **[locks](Locks):** *"cmd:not pperm(channel_banned)"*
- **[`help_category`](Help-System):** *"Comms"*
- **Source:** class `CmdCdesc` in
[comms.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/comms.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### cdestroy (CmdCdestroy)
```
    destroy a channel you created

    Usage:
      cdestroy <channel>

    Destroys a channel that you control.
```
- **key:** *cdestroy*
- **aliases:** 
- **[locks](Locks):** *"cmd: not pperm(channel_banned)"*
- **[`help_category`](Help-System):** *"Comms"*
- **Source:** class `CmdCdestroy` in
[comms.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/comms.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### cemit (CmdCemit)
```
    send an admin message to a channel you control

    Usage:
      cemit[/switches] <channel> = <message>

    Switches:
      sendername - attach the sender's name before the message
      quiet - don't echo the message back to sender

    Allows the user to broadcast a message over a channel as long as
    they control it. It does not show the user's name unless they
    provide the /sendername switch.
```
- **key:** *cemit*
- **aliases:** *cmsg*
- **[locks](Locks):** *"cmd: not pperm(channel_banned) and pperm(Player)"*
- **[`help_category`](Help-System):** *"Comms"*
- **Source:** class `CmdCemit` in
[comms.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/comms.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### channels (CmdChannels)
```
    list all channels available to you

    Usage:
      channels
      clist
      comlist

    Lists all channels available to you, whether you listen to them or not.
    Use 'comlist' to only view your current channel subscriptions.
    Use addcom/delcom to join and leave channels
```
- **key:** *channels*
- **aliases:** *chanlist*, *channellist*, *clist*, *comlist*, *all channels*
- **[locks](Locks):** *"cmd: not pperm(channel_banned)"*
- **[`help_category`](Help-System):** *"Comms"*
- **Source:** class `CmdChannels` in
[comms.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/comms.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### clock (CmdClock)
```
    change channel locks of a channel you control

    Usage:
      clock <channel> [= <lockstring>]

    Changes the lock access restrictions of a channel. If no
    lockstring was given, view the current lock definitions.
```
- **key:** *clock*
- **aliases:** 
- **[locks](Locks):** *"cmd:not pperm(channel_banned)"*
- **[`help_category`](Help-System):** *"Comms"*
- **Source:** class `CmdClock` in
[comms.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/comms.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### cwho (CmdCWho)
```
    show who is listening to a channel

    Usage:
      cwho <channel>

    List who is connected to a given channel you have access to.
```
- **key:** *cwho*
- **aliases:** 
- **[locks](Locks):** *"cmd: not pperm(channel_banned)"*
- **[`help_category`](Help-System):** *"Comms"*
- **Source:** class `CmdCWho` in
[comms.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/comms.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### delcom (CmdDelCom)
```
    remove a channel alias and/or unsubscribe from channel

    Usage:
       delcom <alias or channel>
       delcom/all <channel>

    If the full channel name is given, unsubscribe from the
    channel. If an alias is given, remove the alias but don't
    unsubscribe. If the 'all' switch is used, remove all aliases
    for that channel.
```
- **key:** *delcom*
- **aliases:** *delaliaschan*, *delchanalias*
- **[locks](Locks):** *"cmd:not perm(channel_banned)"*
- **[`help_category`](Help-System):** *"Comms"*
- **Source:** class `CmdDelCom` in
[comms.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/comms.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### irc2chan (CmdIRC2Chan)
```
    Link an evennia channel to an external IRC channel

    Usage:
      irc2chan[/switches] <evennia_channel> = <ircnetwork> <port> <#irchannel> <botname>[:typeclass]
      irc2chan/delete botname|#dbid

    Switches:
      /delete     - this will delete the bot and remove the irc connection
                    to the channel. Requires the botname or #dbid as input.
      /remove     - alias to /delete
      /disconnect - alias to /delete
      /list       - show all irc<->evennia mappings
      /ssl        - use an SSL-encrypted connection

    Example:
      irc2chan myircchan = irc.dalnet.net 6667 #mychannel evennia-bot
      irc2chan public = irc.freenode.net 6667 #evgaming #evbot:accounts.mybot.MyBot

    This creates an IRC bot that connects to a given IRC network and
    channel. If a custom typeclass path is given, this will be used
    instead of the default bot class.
    The bot will relay everything said in the evennia channel to the
    IRC channel and vice versa. The bot will automatically connect at
    server start, so this command need only be given once. The
    /disconnect switch will permanently delete the bot. To only
    temporarily deactivate it, use the  |wservices|n command instead.
    Provide an optional bot class path to use a custom bot.
```
- **key:** *irc2chan*
- **aliases:** 
- **[locks](Locks):** *"cmd:serversetting(IRC_ENABLED) and pperm(Developer)"*
- **[`help_category`](Help-System):** *"Comms"*
- **Source:** class `CmdIRC2Chan` in
[comms.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/comms.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### page (CmdPage)
```
    send a private message to another account

    Usage:
      page[/switches] [<account>,<account>,... = <message>]
      tell        ''
      page <number>

    Switch:
      last - shows who you last messaged
      list - show your last <number> of tells/pages (default)

    Send a message to target user (if online). If no
    argument is given, you will get a list of your latest messages.
```
- **key:** *page*
- **aliases:** *tell*
- **[locks](Locks):** *"cmd:not pperm(page_banned)"*
- **[`help_category`](Help-System):** *"Comms"*
- **Source:** class `CmdPage` in
[comms.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/comms.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### rss2chan (CmdRSS2Chan)
```
    link an evennia channel to an external RSS feed

    Usage:
      rss2chan[/switches] <evennia_channel> = <rss_url>

    Switches:
      /disconnect - this will stop the feed and remove the connection to the
                    channel.
      /remove     -                                 "
      /list       - show all rss->evennia mappings

    Example:
      rss2chan rsschan = http://code.google.com/feeds/p/evennia/updates/basic

    This creates an RSS reader  that connects to a given RSS feed url. Updates
    will be echoed as a title and news link to the given channel. The rate of
    updating is set with the RSS_UPDATE_INTERVAL variable in settings (default
    is every 10 minutes).

    When disconnecting you need to supply both the channel and url again so as
    to identify the connection uniquely.
```
- **key:** *rss2chan*
- **aliases:** 
- **[locks](Locks):** *"cmd:serversetting(RSS_ENABLED) and pperm(Developer)"*
- **[`help_category`](Help-System):** *"Comms"*
- **Source:** class `CmdRSS2Chan` in
[comms.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/comms.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


### `general.py`

[View general.py
source](https://github.com/evennia/evennia/tree/master/evennia/commands/default/general.py)


#### access (CmdAccess)
```
    show your current game access

    Usage:
      access

    This command shows you the permission hierarchy and
    which permission groups you are a member of.
```
- **key:** *access*
- **aliases:** *groups*, *hierarchy*
- **[locks](Locks):** *"cmd:all()"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdAccess` in
[general.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/general.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### drop (CmdDrop)
```
    drop something

    Usage:
      drop <obj>

    Lets you drop an object from your inventory into the
    location you are currently in.
```
- **key:** *drop*
- **aliases:** 
- **[locks](Locks):** *"cmd:all()"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdDrop` in
[general.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/general.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### get (CmdGet)
```
    pick up something

    Usage:
      get <obj>

    Picks up an object from your location and puts it in
    your inventory.
```
- **key:** *get*
- **aliases:** *grab*
- **[locks](Locks):** *"cmd:all()"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdGet` in
[general.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/general.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### give (CmdGive)
```
    give away something to someone

    Usage:
      give <inventory obj> <to||=> <target>

    Gives an items from your inventory to another character,
    placing it in their inventory.
```
- **key:** *give*
- **aliases:** 
- **[locks](Locks):** *"cmd:all()"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdGive` in
[general.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/general.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### home (CmdHome)
```
    move to your character's home location

    Usage:
      home

    Teleports you to your home location.
```
- **key:** *home*
- **aliases:** 
- **[locks](Locks):** *"cmd:perm(home) or perm(Builder)"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdHome` in
[general.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/general.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### inventory (CmdInventory)
```
    view inventory

    Usage:
      inventory
      inv

    Shows your inventory.
```
- **key:** *inventory*
- **aliases:** *i*, *inv*
- **[locks](Locks):** *"cmd:all()"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdInventory` in
[general.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/general.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### look (CmdLook)
```
    look at location or object

    Usage:
      look
      look <obj>
      look *<account>

    Observes your location or objects in your vicinity.
```
- **key:** *look*
- **aliases:** *l*, *ls*
- **[locks](Locks):** *"cmd:all()"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdLook` in
[general.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/general.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### nick (CmdNick)
```
    define a personal alias/nick by defining a string to
    match and replace it with another on the fly

    Usage:
      nick[/switches] <string> [= [replacement_string]]
      nick[/switches] <template> = <replacement_template>
      nick/delete <string> or number
      nicks

    Switches:
      inputline - replace on the inputline (default)
      object    - replace on object-lookup
      account   - replace on account-lookup
      list      - show all defined aliases (also "nicks" works)
      delete    - remove nick by index in /list
      clearall  - clear all nicks

    Examples:
      nick hi = say Hello, I'm Sarah!
      nick/object tom = the tall man
      nick build $1 $2 = create/drop $1;$2
      nick tell $1 $2=page $1=$2
      nick tm?$1=page tallman=$1
      nick tm\=$1=page tallman=$1

    A 'nick' is a personal string replacement. Use $1, $2, ... to catch arguments.
    Put the last $-marker without an ending space to catch all remaining text. You
    can also use unix-glob matching for the left-hand side <string>:

        * - matches everything
        ? - matches 0 or 1 single characters
        [abcd] - matches these chars in any order
        [!abcd] - matches everything not among these chars
        \= - escape literal '=' you want in your <string>

    Note that no objects are actually renamed or changed by this command - your nicks
    are only available to you. If you want to permanently add keywords to an object
    for everyone to use, you need build privileges and the alias command.
```
- **key:** *nick*
- **aliases:** *nicks*, *nickname*
- **[locks](Locks):** *"cmd:all()"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdNick` in
[general.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/general.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### pose (CmdPose)
```
    strike a pose

    Usage:
      pose <pose text>
      pose's <pose text>

    Example:
      pose is standing by the wall, smiling.
       -> others will see:
      Tom is standing by the wall, smiling.

    Describe an action being taken. The pose text will
    automatically begin with your name.
```
- **key:** *pose*
- **aliases:** *:*, *emote*
- **[locks](Locks):** *"cmd:all()"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdPose` in
[general.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/general.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### say (CmdSay)
```
    speak as your character

    Usage:
      say <message>

    Talk to those in your current location.
```
- **key:** *say*
- **aliases:** *'*, *"*
- **[locks](Locks):** *"cmd:all()"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdSay` in
[general.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/general.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### setdesc (CmdSetDesc)
```
    describe yourself

    Usage:
      setdesc <description>

    Add a description to yourself. This
    will be visible to people when they
    look at you.
```
- **key:** *setdesc*
- **aliases:** 
- **[locks](Locks):** *"cmd:all()"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdSetDesc` in
[general.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/general.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### whisper (CmdWhisper)
```
    Speak privately as your character to another

    Usage:
      whisper <character> = <message>
      whisper <char1>, <char2> = <message>

    Talk privately to one or more characters in your current location, without
    others in the room being informed.
```
- **key:** *whisper*
- **aliases:** 
- **[locks](Locks):** *"cmd:all()"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdWhisper` in
[general.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/general.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


### `help.py`

[View help.py
source](https://github.com/evennia/evennia/tree/master/evennia/commands/default/help.py)


#### help (CmdHelp)
```
    View help or a list of topics

    Usage:
      help <topic or command>
      help list
      help all

    This will search for help on commands and other
    topics related to the game.
```
- **key:** *help*
- **aliases:** *?*
- **[locks](Locks):** *"cmd:all()"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdHelp` in
[help.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/help.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### sethelp (CmdSetHelp)
```
    Edit the help database.

    Usage:
      help[/switches] <topic>[[;alias;alias][,category[,locks]] [= <text>]

    Switches:
      edit - open a line editor to edit the topic's help text.
      replace - overwrite existing help topic.
      append - add text to the end of existing topic with a newline between.
      extend - as append, but don't add a newline.
      delete - remove help topic.

    Examples:
      sethelp throw = This throws something at ...
      sethelp/append pickpocketing,Thievery = This steals ...
      sethelp/replace pickpocketing, ,attr(is_thief) = This steals ...
      sethelp/edit thievery

    This command manipulates the help database. A help entry can be created,
    appended/merged to and deleted. If you don't assign a category, the
    "General" category will be used. If no lockstring is specified, default
    is to let everyone read the help file.
```
- **key:** *sethelp*
- **aliases:** 
- **[locks](Locks):** *"cmd:perm(Helper)"*
- **[`help_category`](Help-System):** *"Building"*
- **Source:** class `CmdSetHelp` in
[help.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/help.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


### `system.py`

[View system.py
source](https://github.com/evennia/evennia/tree/master/evennia/commands/default/system.py)


#### about (CmdAbout)
```
    show Evennia info

    Usage:
      about

    Display info about the game engine.
```
- **key:** *about*
- **aliases:** *version*
- **[locks](Locks):** *"cmd:all()"*
- **[`help_category`](Help-System):** *"System"*
- **Source:** class `CmdAbout` in
[system.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/system.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### objects (CmdObjects)
```
    statistics on objects in the database

    Usage:
      objects [<nr>]

    Gives statictics on objects in database as well as
    a list of <nr> latest objects in database. If not
    given, <nr> defaults to 10.
```
- **key:** *objects*
- **aliases:** *db*, *listobjs*, *stats*, *listobjects*
- **[locks](Locks):** *"cmd:perm(listobjects) or perm(Builder)"*
- **[`help_category`](Help-System):** *"System"*
- **Source:** class `CmdObjects` in
[system.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/system.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### py (CmdPy)
```
    execute a snippet of python code

    Usage:
      py [cmd]
      py/edit
      py/time <cmd>
      py/clientraw <cmd>
      py/noecho

    Switches:
      time - output an approximate execution time for <cmd>
      edit - open a code editor for multi-line code experimentation
      clientraw - turn off all client-specific escaping. Note that this may
        lead to different output depending on prototocol (such as angular brackets
        being parsed as HTML in the webclient but not in telnet clients)
      noecho - in Python console mode, turn off the input echo (e.g. if your client
        does this for you already)

    Without argument, open a Python console in-game. This is a full console,
    accepting multi-line Python code for testing and debugging. Type `exit()` to
    return to the game. If Evennia is reloaded, the console will be closed.

    Enter a line of instruction after the 'py' command to execute it
    immediately.  Separate multiple commands by ';' or open the code editor
    using the /edit switch (all lines added in editor will be executed
    immediately when closing or using the execute command in the editor).

    A few variables are made available for convenience in order to offer access
    to the system (you can import more at execution time).

    Available variables in py environment:
      self, me                   : caller
      here                       : caller.location
      evennia                    : the evennia API
      inherits_from(obj, parent) : check object inheritance

    You can explore The evennia API from inside the game by calling
    the `__doc__` property on entities:
        py evennia.__doc__
        py evennia.managers.__doc__

    |rNote: In the wrong hands this command is a severe security risk.  It
    should only be accessible by trusted server admins/superusers.|n
```
- **key:** *py*
- **aliases:** *!*
- **[locks](Locks):** *"cmd:perm(py) or perm(Developer)"*
- **[`help_category`](Help-System):** *"System"*
- **Source:** class `CmdPy` in
[system.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/system.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### reload (CmdReload)
```
    reload the server

    Usage:
      reload [reason]

    This restarts the server. The Portal is not
    affected. Non-persistent scripts will survive a reload (use
    reset to purge) and at_reload() hooks will be called.
```
- **key:** *reload*
- **aliases:** *restart*
- **[locks](Locks):** *"cmd:perm(reload) or perm(Developer)"*
- **[`help_category`](Help-System):** *"System"*
- **Source:** class `CmdReload` in
[system.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/system.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### reset (CmdReset)
```
    reset and reboot the server

    Usage:
      reset

    Notes:
      For normal updating you are recommended to use reload rather
      than this command. Use shutdown for a complete stop of
      everything.

    This emulates a cold reboot of the Server component of Evennia.
    The difference to shutdown is that the Server will auto-reboot
    and that it does not affect the Portal, so no users will be
    disconnected. Contrary to reload however, all shutdown hooks will
    be called and any non-database saved scripts, ndb-attributes,
    cmdsets etc will be wiped.
```
- **key:** *reset*
- **aliases:** *reboot*
- **[locks](Locks):** *"cmd:perm(reload) or perm(Developer)"*
- **[`help_category`](Help-System):** *"System"*
- **Source:** class `CmdReset` in
[system.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/system.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### scripts (CmdScripts)
```
    list and manage all running scripts

    Usage:
      scripts[/switches] [#dbref, key, script.path or <obj>]

    Switches:
      start - start a script (must supply a script path)
      stop - stops an existing script
      kill - kills a script - without running its cleanup hooks
      validate - run a validation on the script(s)

    If no switches are given, this command just views all active
    scripts. The argument can be either an object, at which point it
    will be searched for all scripts defined on it, or a script name
    or #dbref. For using the /stop switch, a unique script #dbref is
    required since whole classes of scripts often have the same name.

    Use script for managing commands on objects.
```
- **key:** *scripts*
- **aliases:** *globalscript*, *listscripts*
- **[locks](Locks):** *"cmd:perm(listscripts) or perm(Admin)"*
- **[`help_category`](Help-System):** *"System"*
- **Source:** class `CmdScripts` in
[system.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/system.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### server (CmdServerLoad)
```
    show server load and memory statistics

    Usage:
       server[/mem]

    Switches:
        mem - return only a string of the current memory usage
        flushmem - flush the idmapper cache

    This command shows server load statistics and dynamic memory
    usage. It also allows to flush the cache of accessed database
    objects.

    Some Important statistics in the table:

    |wServer load|n is an average of processor usage. It's usually
    between 0 (no usage) and 1 (100% usage), but may also be
    temporarily higher if your computer has multiple CPU cores.

    The |wResident/Virtual memory|n displays the total memory used by
    the server process.

    Evennia |wcaches|n all retrieved database entities when they are
    loaded by use of the idmapper functionality. This allows Evennia
    to maintain the same instances of an entity and allowing
    non-persistent storage schemes. The total amount of cached objects
    are displayed plus a breakdown of database object types.

    The |wflushmem|n switch allows to flush the object cache. Please
    note that due to how Python's memory management works, releasing
    caches may not show you a lower Residual/Virtual memory footprint,
    the released memory will instead be re-used by the program.
```
- **key:** *server*
- **aliases:** *serverprocess*, *serverload*
- **[locks](Locks):** *"cmd:perm(list) or perm(Developer)"*
- **[`help_category`](Help-System):** *"System"*
- **Source:** class `CmdServerLoad` in
[system.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/system.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### service (CmdService)
```
    manage system services

    Usage:
      service[/switch] <service>

    Switches:
      list   - shows all available services (default)
      start  - activates or reactivate a service
      stop   - stops/inactivate a service (can often be restarted)
      delete - tries to permanently remove a service

    Service management system. Allows for the listing,
    starting, and stopping of services. If no switches
    are given, services will be listed. Note that to operate on the
    service you have to supply the full (green or red) name as given
    in the list.
```
- **key:** *service*
- **aliases:** *services*
- **[locks](Locks):** *"cmd:perm(service) or perm(Developer)"*
- **[`help_category`](Help-System):** *"System"*
- **Source:** class `CmdService` in
[system.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/system.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


#### shutdown (CmdShutdown)
```
    stop the server completely

    Usage:
      shutdown [announcement]

    Gracefully shut down both Server and Portal.
```
- **key:** *shutdown*
- **aliases:** 
- **[locks](Locks):** *"cmd:perm(shutdown) or perm(Developer)"*
- **[`help_category`](Help-System):** *"System"*
- **Source:** class `CmdShutdown` in
[system.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/system.py).
Belongs to command set *'DefaultAccount'* of class `AccountCmdSet` in
[cmdset_account.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_account.py).


#### time (CmdTime)
```
    show server time statistics

    Usage:
      time

    List Server time statistics such as uptime
    and the current time stamp.
```
- **key:** *time*
- **aliases:** *uptime*
- **[locks](Locks):** *"cmd:perm(time) or perm(Player)"*
- **[`help_category`](Help-System):** *"System"*
- **Source:** class `CmdTime` in
[system.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/system.py).
Belongs to command set *'DefaultCharacter'* of class `CharacterCmdSet` in
[cmdset_character.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_character.py).


### `unloggedin.py`

[View unloggedin.py
source](https://github.com/evennia/evennia/tree/master/evennia/commands/default/unloggedin.py)


#### __unloggedin_look_command (CmdUnconnectedLook)
```
    look when in unlogged-in state

    Usage:
      look

    This is an unconnected version of the look command for simplicity.

    This is called by the server and kicks everything in gear.
    All it does is display the connect screen.
```
- **key:** *__unloggedin_look_command*
- **aliases:** *l*, *look*
- **[locks](Locks):** *"cmd:all()"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdUnconnectedLook` in
[unloggedin.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/unloggedin.py).
Belongs to command set *'DefaultUnloggedin'* of class `UnloggedinCmdSet` in
[cmdset_unloggedin.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_unloggedin.py).

*OBS: This is a [[System Command|Commands]]. System commands have fixed keys and are called by the
server in specific situations.*

#### connect (CmdUnconnectedConnect)
```
    connect to the game

    Usage (at login screen):
      connect accountname password
      connect "account name" "pass word"

    Use the create command to first create an account before logging in.

    If you have spaces in your name, enclose it in double quotes.
```
- **key:** *connect*
- **aliases:** *con*, *conn*, *co*
- **[locks](Locks):** *"cmd:all()"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdUnconnectedConnect` in
[unloggedin.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/unloggedin.py).
Belongs to command set *'DefaultUnloggedin'* of class `UnloggedinCmdSet` in
[cmdset_unloggedin.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_unloggedin.py).


#### create (CmdUnconnectedCreate)
```
    create a new account account

    Usage (at login screen):
      create <accountname> <password>
      create "account name" "pass word"

    This creates a new account account.

    If you have spaces in your name, enclose it in double quotes.
```
- **key:** *create*
- **aliases:** *cre*, *cr*
- **[locks](Locks):** *"cmd:all()"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdUnconnectedCreate` in
[unloggedin.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/unloggedin.py).
Belongs to command set *'DefaultUnloggedin'* of class `UnloggedinCmdSet` in
[cmdset_unloggedin.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_unloggedin.py).


#### help (CmdUnconnectedHelp)
```
    get help when in unconnected-in state

    Usage:
      help

    This is an unconnected version of the help command,
    for simplicity. It shows a pane of info.
```
- **key:** *help*
- **aliases:** *?*, *h*
- **[locks](Locks):** *"cmd:all()"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdUnconnectedHelp` in
[unloggedin.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/unloggedin.py).
Belongs to command set *'DefaultUnloggedin'* of class `UnloggedinCmdSet` in
[cmdset_unloggedin.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_unloggedin.py).


#### quit (CmdUnconnectedQuit)
```
    quit when in unlogged-in state

    Usage:
      quit

    We maintain a different version of the quit command
    here for unconnected accounts for the sake of simplicity. The logged in
    version is a bit more complicated.
```
- **key:** *quit*
- **aliases:** *qu*, *q*
- **[locks](Locks):** *"cmd:all()"*
- **[`help_category`](Help-System):** *"General"*
- **Source:** class `CmdUnconnectedQuit` in
[unloggedin.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/unloggedin.py).
Belongs to command set *'DefaultUnloggedin'* of class `UnloggedinCmdSet` in
[cmdset_unloggedin.py](https://github.com/evennia/evennia/tree/master/evennia/commands/default/cmdset_unloggedin.py).
