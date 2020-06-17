# Coding FAQ

*This FAQ page is for users to share their solutions to coding problems. Keep it brief and link to
the docs if you can rather than too lengthy explanations. Don't forget to check if an answer already
exists before answering - maybe you can clarify that answer rather than to make a new Q&A section.*


## Table of Contents

- [Removing default commands](Coding-FAQ#removing-default-commands)
- [Preventing character from moving based on a condition](Coding-FAQ#preventing-character-from-
moving-based-on-a-condition)
- [Reference initiating object in an EvMenu command](Coding-FAQ#reference-initiating-object-in-an-
evmenu-command)
- [Adding color to default Evennia Channels](Coding-FAQ#adding-color-to-default-evennia-channels)
- [Selectively turn off commands in a room](Coding-FAQ#selectively-turn-off-commands-in-a-room)
- [Select Command based on a condition](Coding-FAQ#select-command-based-on-a-condition)
- [Automatically updating code when reloading](Coding-FAQ#automatically-updating-code-when-
reloading)
- [Changing all exit messages](Coding-FAQ#changing-all-exit-messages)
- [Add parsing with the "to" delimiter](Coding-FAQ#add-parsing-with-the-to-delimiter)
- [Store last used session IP address](Coding-FAQ#store-last-used-session-ip-address)
- [Use wide characters with EvTable](Coding-FAQ#non-latin-characters-in-evtable)

## Removing default commands
**Q:** How does one *remove* (not replace) e.g. the default `get` [Command](Commands) from the
Character [Command Set](Command-Sets)?

**A:** Go to `mygame/commands/default_cmdsets.py`. Find the `CharacterCmdSet` class. It has one
method named `at_cmdset_creation`. At the end of that method, add the following line:
`self.remove(default_cmds.CmdGet())`. See the [Adding Commands Tutorial](Adding-Command-Tutorial)
for more info.

## Preventing character from moving based on a condition
**Q:** How does one keep a character from using any exit, if they meet a certain condition? (I.E. in
combat, immobilized, etc.)

**A:** The `at_before_move` hook is called by Evennia just before performing any move. If it returns
`False`, the move is aborted. Let's say we want to check for an [Attribute](Attributes) `cantmove`.
Add the following code to the `Character` class:

```python
def at_before_move(self, destination):
    "Called just before trying to move"
    if self.db.cantmove: # replace with condition you want to test
        self.msg("Something is preventing you from moving!")
        return False
    return True
```

## Reference initiating object in an EvMenu command.
**Q:** An object has a Command on it starts up an EvMenu instance. How do I capture a reference to
that object for use in the menu?

**A:** When an [EvMenu](EvMenu) is started, the menu object is stored as `caller.ndb._menutree`.
This is a good place to store menu-specific things since it will clean itself up when the menu
closes. When initiating the menu, any additional keywords you give will be available for you as
properties on this menu object:

```python
class MyObjectCommand(Command):
    # A Command stored on an object (the object is always accessible from
    # the Command as self.obj)
    def func(self):
        # add the object as the stored_obj menu property
        EvMenu(caller, ..., stored_obj=self.obj)

```

Inside the menu you can now access the object through `caller.ndb._menutree.stored_obj`.


## Adding color to default Evennia Channels
**Q:** How do I add colors to the names of Evennia channels?

**A:** The Channel typeclass' `channel_prefix` method decides what is shown at the beginning of a
channel send. Edit `mygame/typeclasses/channels.py` (and then `@reload`):

```python
# define our custom color names
CHANNEL_COLORS = {'public': '|015Public|n',
                  'newbie': '|550N|n|551e|n|552w|n|553b|n|554i|n|555e|n',
                  'staff': '|010S|n|020t|n|030a|n|040f|n|050f|n'}

# Add to the Channel class
    # ...
    def channel_prefix(self, msg, emit=False):
        prefix_string = ""
        if self.key in COLORS:
            prefix_string = "[%s] " % CHANNEL_COLORS.get(self.key.lower())
        else:
            prefix_string = "[%s] " % self.key.capitalize()
        return prefix_string
```
Additional hint: To make colors easier to change from one place you could instead put the
`CHANNEL_COLORS` dict in your settings file and import it as `from django.conf.settings import
CHANNEL_COLORS`.


## Selectively turn off commands in a room
**Q:** I want certain commands to turn off in a given room. They should still work normally for
staff.

**A:** This is done using a custom cmdset on a room [locked with the 'call' lock type](Locks). Only
if this lock is passed will the commands on the room be made available to an object inside it. Here
is an example of a room where certain commands are disabled for non-staff:

```python
# in mygame/typeclasses/rooms.py

from evennia import default_commands, CmdSet

class CmdBlocking(default_commands.MuxCommand):
    # block commands give, get, inventory and drop
    key = "give"
    aliases = ["get", "inventory", "drop"]
    def func(self):
        self.caller.msg("You cannot do that in this room.")

class BlockingCmdSet(CmdSet):
    key = "blocking_cmdset"
    # default commands have prio 0
    priority = 1
    def at_cmdset_creation(self):
        self.add(CmdBlocking())

class BlockingRoom(Room):
    def at_object_creation(self):
        self.cmdset.add(BlockingCmdSet, permanent=True)
        # only share commands with players in the room that
        # are NOT Builders or higher
        self.locks.add("call:not perm(Builders)")
```
After `@reload`, make some `BlockingRooms` (or switch a room to it with `@typeclass`). Entering one
will now replace the given commands for anyone that does not have the `Builders` or higher
permission. Note that the 'call' lock is special in that even the superuser will be affected by it
(otherwise superusers would always see other player's cmdsets and a game would be unplayable for
superusers).

## Select Command based on a condition
**Q:** I want a command to be available only based on a condition. For example I want the "werewolf"
command to only be available on a full moon, from midnight to three in-game time.

**A:** This is easiest accomplished by putting the "werewolf" command on the Character as normal,
but to [lock](Locks) it with the "cmd" type lock. Only if the "cmd" lock type is passed will the
command be available.

```python
# in mygame/commands/command.py

from evennia import Command

class CmdWerewolf(Command):
    key = "werewolf"
    # lock full moon, between 00:00 (midnight) and 03:00.
    locks = "cmd:is_full_moon(0, 3)"
    def func(self):
        # ...
```
Add this to the [default cmdset as usual](Adding-Command-Tutorial). The `is_full_moon` [lock
function](Locks#lock-functions) does not yet exist. We must create that:

```python
# in mygame/server/conf/lockfuncs.py

def is_full_moon(accessing_obj, accessed_obj,
                 starthour, endhour, *args, **kwargs):
    # calculate if the moon is full here and
    # if current game time is between starthour and endhour
    # return True or False

```
After a `@reload`, the `werewolf` command will be available only at the right time, that is when the
`is_full_moon` lock function returns True.

## Automatically updating code when reloading
**Q:** I have a development server running Evennia.  Can I have the server update its code-base when
I reload?

**A:** Having a development server that pulls updated code whenever you reload it can be really
useful if you have limited shell access to your server, or want to have it done automatically.  If
you have your project in a configured Git environment, it's a matter of automatically calling `git
pull` when you reload.  And that's pretty straightforward:

In `/server/conf/at_server_startstop.py`:

```python
import subprocess

# ... other hooks ...

def at_server_reload_stop():
    """
    This is called only time the server stops before a reload.
    """
    print("Pulling from the game repository...")
    process = subprocess.call(["git", "pull"], shell=False)
```

That's all.  We call `subprocess` to execute a shell command (that code works on Windows and Linux,
assuming the current directory is your game directory, which is probably the case when you run
Evennia).  `call` waits for the process to complete, because otherwise, Evennia would reload on
partially-modified code, which would be problematic.

Now, when you enter `@reload` on your development server, the game repository is updated from the
configured remote repository (Github, for instance).  Your development cycle could resemble
something like:

1. Coding on the local machine.
2. Testing modifications.
3. Committing once, twice or more (being sure the code is still working, unittests are pretty useful
here).
4. When the time comes, login to the development server and run `@reload`.

The reloading might take one or two additional seconds, since Evennia will pull from your remote Git
repository.  But it will reload on it and you will have your modifications ready, without needing
connecting to your server using SSH or something similar.

## Changing all exit messages
**Q:** How can I change the default exit messages to something like "XXX leaves east" or "XXX
arrives from the west"?

**A:** the default exit messages are stored in two hooks, namely `announce_move_from` and
`announce_move_to`, on the `Character` typeclass (if what you want to change is the message other
characters will see when a character exits).

These two hooks provide some useful features to easily update the message to be displayed.  They
take both the default message and mapping as argument.  You can easily call the parent hook with
these information:

* The message represents the string of characters sent to characters in the room when a character
leaves.
* The mapping is a dictionary containing additional mappings (you will probably not need it for
simple customization).

It is advisable to look in the [code of both
hooks](https://github.com/evennia/evennia/tree/master/evennia/objects/objects.py), and read the
hooks' documentation.  The explanations on how to quickly update the message are shown below:

```python
# In typeclasses/characters.py
"""
Characters

"""
from evennia import DefaultCharacter

class Character(DefaultCharacter):
    """
    The default character class.

    ...
    """

    def announce_move_from(self, destination, msg=None, mapping=None):
        """
        Called if the move is to be announced. This is
        called while we are still standing in the old
        location.

        Args:
            destination (Object): The place we are going to.
            msg (str, optional): a replacement message.
            mapping (dict, optional): additional mapping objects.

        You can override this method and call its parent with a
        message to simply change the default message.  In the string,
        you can use the following as mappings (between braces):
            object: the object which is moving.
            exit: the exit from which the object is moving (if found).
            origin: the location of the object before the move.
            destination: the location of the object after moving.

        """
        super().announce_move_from(destination, msg="{object} leaves {exit}.")

    def announce_move_to(self, source_location, msg=None, mapping=None):
        """
        Called after the move if the move was not quiet. At this point
        we are standing in the new location.

        Args:
            source_location (Object): The place we came from
            msg (str, optional): the replacement message if location.
            mapping (dict, optional): additional mapping objects.

        You can override this method and call its parent with a
        message to simply change the default message.  In the string,
        you can use the following as mappings (between braces):
            object: the object which is moving.
            exit: the exit from which the object is moving (if found).
            origin: the location of the object before the move.
            destination: the location of the object after moving.

        """
        super().announce_move_to(source_location, msg="{object} arrives from the {exit}.")
```

We override both hooks, but call the parent hook to display a different message.  If you read the
provided docstrings, you will better understand why and how we use mappings (information between
braces).  You can provide additional mappings as well, if you want to set a verb to move, for
instance, or other, extra information.

## Add parsing with the "to" delimiter

**Q:** How do I change commands to undestand say `give obj to target` as well as the default `give
obj = target`?

**A:** You can make change the default `MuxCommand` parent with your own class making a small change
in its `parse` method:

```python
    # in mygame/commands/command.py
    from evennia import default_cmds
    class MuxCommand(default_cmds.MuxCommand):
        def parse(self):
            """Implement an additional parsing of 'to'"""
            super().parse()
            if " to " in self.args:
                self.lhs, self.rhs = self.args.split(" to ", 1)
```
Next you change the parent of the default commands in settings:

```python
    COMMAND_DEFAULT_CLASS = "commands.command.MuxCommand"
```

Do a `@reload` and all default commands will now use your new tweaked parent class. A copy of the
MuxCommand class is also found commented-out in the `mygame/commands/command.py` file.

## Store last used session IP address

**Q:** If a user has already logged out of an Evennia account, their IP is no longer visible to
staff that wants to ban-by-ip (instead of the user) with `@ban/ip`?

**A:** One approach is to write the IP from the last session onto the "account" account object.

`typeclasses/accounts.py`
```python
    def at_post_login(self, session=None, **kwargs):
        super().at_post_login(session=session, **kwargs)
        self.db.lastsite = self.sessions.all()[-1].address
```
Adding timestamp for login time and appending to a list to keep the last N login IP addresses and
timestamps is possible, also.  Additionally, if you don't want the list to grow beyond a
`do_not_exceed` length, conditionally pop a value after you've added it, if the length has grown too
long.

**NOTE:** You'll need to add `import time` to generate the login timestamp.
```python
    def at_post_login(self, session=None, **kwargs):
        super().at_post_login(session=session, **kwargs)
        do_not_exceed = 24  # Keep the last two dozen entries
        session = self.sessions.all()[-1]  # Most recent session
        if not self.db.lastsite:
           self.db.lastsite = []
        self.db.lastsite.insert(0, (session.address, int(time.time())))
        if len(self.db.lastsite) > do_not_exceed:
            self.db.lastsite.pop()
```
This only stores the data. You may want to interface the `@ban` command or make a menu-driven viewer
for staff to browse the list and display how long ago the login occurred.

## Non-latin characters in EvTable

**Q:** When using e.g. Chinese characters in EvTable, some lines appear to be too wide, for example
```
+------+------+
|      |      |
|  测试  |  测试  |
|      |      |
+~~~~~~+~~~~~~+
```
**A:** The reason for this is because certain non-latin characters are *visually* much wider than
their len() suggests. There is little Evennia can (reliably) do about this. If you are using such
characters, you need to make sure to use a suitable mono-spaced font where are width are equal. You
can set this in your web client and need to recommend it for telnet-client users. See [this
discussion](https://github.com/evennia/evennia/issues/1522) where some suitable fonts are suggested.