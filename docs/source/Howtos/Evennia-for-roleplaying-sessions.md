# Evennia for roleplaying sessions

This tutorial will explain how to set up a realtime or play-by-post tabletop style game using a
fresh Evennia server.

The scenario is thus: You and a bunch of friends want to play a tabletop role playing game online.
One of you will be the game master and you are all okay with playing using written text. You want
both the ability to role play in real-time (when people happen to be online at the same time) as
well as the ability for people to post when they can and catch up on what happened since they were
last online.

This is the functionality we will be needing and using:

* The ability to make one of you the *GM* (game master), with special abilities.
* A *Character sheet* that players can create, view and fill in. It can also be locked so only the
GM can modify it.
* A *dice roller* mechanism, for whatever type of dice the RPG rules require.
* *Rooms*, to give a sense of location and to compartmentalize play going on- This means both
Character movements from location to location and GM explicitly moving them around.
* *Channels*, for easily sending text to all subscribing accounts, regardless of location.
* Account-to-Account *messaging* capability, including sending to multiple recipients
simultaneously, regardless of location.

We will find most of these things are already part of vanilla Evennia, but that we can expand on the
defaults for our particular use-case. Below we will flesh out these components from start to finish.

## Starting out

We will assume you start from scratch. You need Evennia installed, as per the [Setup Quickstart](../Setup/Installation.md) 
instructions. Initialize a new game directory with `evennia init
<gamedirname>`. In this tutorial we assume your game dir is simply named `mygame`. You can use the
default database and keep all other settings to default for now. Familiarize yourself with the
`mygame` folder before continuing. You might want to browse the 
[First Steps Coding](Beginner-Tutorial/Part1/Beginner-Tutorial-Part1-Intro.md) tutorial, just to see roughly where things are modified.

## The Game Master role

In brief: 

* Simplest way: Being an admin, just give one account `Admins` permission using the standard `@perm`
command.
* Better but more work: Make a custom command to set/unset the above, while tweaking the Character
to show your renewed GM status to the other accounts.

### The permission hierarchy

Evennia has the following [permission hierarchy](../Concepts/Building-Permissions.md#assigning-permissions) out of
the box: *Players, Helpers, Builders, Admins* and finally *Developers*. We could change these but
then we'd need to update our Default commands to use the changes. We want to keep this simple, so
instead we map our different roles on top of this permission ladder.

1. `Players` is the permission set on normal players. This is the default for anyone creating a new
account on the server.
2. `Helpers` are like `Players` except they also have the ability to create/edit new help entries.
This could be granted to players who are willing to help with writing lore or custom logs for
everyone.
3. `Builders` is not used in our case since the GM should be the only world-builder.
4. `Admins` is the permission level the GM should have. Admins can do everything builders can
(create/describe rooms etc) but also kick accounts, rename them and things like that.
5. `Developers`-level permission are the server administrators, the ones with the ability to
restart/shutdown the server as well as changing the permission levels.

> The [superuser](../Concepts/Building-Permissions.md#the-super-user) is not part of the hierarchy and actually
completely bypasses it. We'll assume server admin(s) will "just" be Developers.

### How to grant permissions

Only `Developers` can (by default) change permission level. Only they have access to the `@perm`
command:

```
> @perm Yvonne
Permissions on Yvonne: accounts

> @perm Yvonne = Admins
> @perm Yvonne
Permissions on Yvonne: accounts, admins

> @perm/del Yvonne = Admins
> @perm Yvonne
Permissions on Yvonne: accounts
```

There is no need to remove the basic `Players` permission when adding the higher permission: the
highest will be used. Permission level names are *not* case sensitive. You can also use both plural
and singular, so "Admins" gives the same powers as "Admin".


### Optional: Making a GM-granting command

Use of `@perm` works out of the box, but it's really the bare minimum. Would it not be nice if other
accounts could tell at a glance who the GM is? Also, we shouldn't really need to remember that the
permission level is called "Admins". It would be easier if we could just do `@gm <account>` and
`@notgm <account>` and at the same time change something make the new GM status apparent.

So let's make this possible. This is what we'll do:

1. We'll customize the default Character class. If an object of this class has a particular flag,
its name will have the string`(GM)` added to the end.
2. We'll add a new command, for the server admin to assign the GM-flag properly.

#### Character modification

Let's first start by customizing the Character. We recommend you browse the beginning of the
[Account](../Components/Accounts.md) page to make sure you know how Evennia differentiates between the OOC "Account
objects" (not to be confused with the `Accounts` permission, which is just a string specifying your
access) and the IC "Character objects".

Open `mygame/typeclasses/characters.py` and modify the default `Character` class:

```python
# in mygame/typeclasses/characters.py

# [...]

class Character(DefaultCharacter):
    # [...]
    def get_display_name(self, looker, **kwargs):
        """
        This method customizes how character names are displayed. We assume
        only permissions of types "Developers" and "Admins" require
        special attention.
        """
        name = self.key
        selfaccount = self.account     # will be None if we are not puppeted
        lookaccount = looker.account   #              - " -

        if selfaccount and selfaccount.db.is_gm:
           # A GM. Show name as name(GM)
           name = f"{name}(GM)"

        if lookaccount and \
          (lookaccount.permissions.get("Developers") or lookaccount.db.is_gm):
            # Developers/GMs see name(#dbref) or name(GM)(#dbref)
            name = f"{name}(#{self.id})"

        return name
```

Above, we change how the Character's name is displayed: If the account controlling this Character is
a GM, we attach the string `(GM)` to the Character's name so everyone can tell who's the boss. If we
ourselves are Developers or GM's we will see database ids attached to Characters names, which can
help if doing database searches against Characters of exactly the same name. We base the "gm-
ingness" on having an flag (an [Attribute](../Components/Attributes.md)) named `is_gm`. We'll make sure new GM's
actually get this flag below.

> **Extra exercise:** This will only show the `(GM)` text on *Characters* puppeted by a GM account,
that is, it will show only to those in the same location. If we wanted it to also pop up in, say,
`who` listings and channels, we'd need to make a similar change to the `Account` typeclass in
`mygame/typeclasses/accounts.py`. We leave this as an exercise to the reader.

#### New @gm/@ungm command

We will describe in some detail how to create and add an Evennia [command](../Components/Commands.md) here with the
hope that we don't need to be as detailed when adding commands in the future. We will build on
Evennia's default "mux-like" commands here.

Open `mygame/commands/command.py` and add a new Command class at the bottom:

```python
# in mygame/commands/command.py

from evennia import default_cmds

# [...]

import evennia

class CmdMakeGM(default_cmds.MuxCommand):
    """
    Change an account's GM status

    Usage:
      @gm <account>
      @ungm <account>

    """
    # note using the key without @ means both @gm !gm etc will work
    key = "gm"
    aliases = "ungm"
    locks = "cmd:perm(Developers)"
    help_category = "RP"

    def func(self):
        "Implement the command"
        caller = self.caller

        if not self.args:
            caller.msg("Usage: @gm account or @ungm account")
            return

        accountlist = evennia.search_account(self.args) # returns a list
        if not accountlist:
            caller.msg(f"Could not find account '{self.args}'")
            return
        elif len(accountlist) > 1:
            caller.msg(f"Multiple matches for '{self.args}': {accountlist}")
            return
        else:
            account = accountlist[0]

        if self.cmdstring == "gm":
            # turn someone into a GM
            if account.permissions.get("Admins"):
                caller.msg(f"Account {account} is already a GM.")
            else:
                account.permissions.add("Admins")
                caller.msg(f"Account {account} is now a GM.")
                account.msg(f"You are now a GM (changed by {caller}).")
                account.character.db.is_gm = True
        else:
            # @ungm was entered - revoke GM status from someone
            if not account.permissions.get("Admins"):
                caller.msg(f"Account {account} is not a GM.")
            else:
                account.permissions.remove("Admins")
                caller.msg(f"Account {account} is no longer a GM.")
                account.msg(f"You are no longer a GM (changed by {caller}).")
                del account.character.db.is_gm

```

All the command does is to locate the account target and assign it the `Admins` permission if we
used `@gm` or revoke it if using the `@ungm` alias. We also set/unset the `is_gm` Attribute that is
expected by our new `Character.get_display_name` method from earlier.

> We could have made this into two separate commands or opted for a syntax like `@gm/revoke
<accountname>`. Instead we examine how this command was called (stored in `self.cmdstring`) in order
to act accordingly. Either way works, practicality and coding style decides which to go with.

To actually make this command available (only to Developers, due to the lock on it), we add it to
the default Account command set. Open the file `mygame/commands/default_cmdsets.py` and find the
`AccountCmdSet` class:

```python
# mygame/commands/default_cmdsets.py

# [...]
from commands.command import CmdMakeGM

class AccountCmdSet(default_cmds.AccountCmdSet):
    # [...]
    def at_cmdset_creation(self):
        # [...]
        self.add(CmdMakeGM())

```

Finally, issue the `@reload` command to update the server to your changes. Developer-level players
(or the superuser) should now have the `@gm/@ungm` command available.

## Character sheet

In brief: 

* Use Evennia's EvTable/EvForm to build a Character sheet
* Tie individual sheets to a given Character.
* Add new commands to modify the Character sheet, both by Accounts and GMs.
* Make the Character sheet lockable by a GM, so the Player can no longer modify it.

### Building a Character sheet

There are many ways to build a Character sheet in text, from manually pasting strings together to
more automated ways. Exactly what is the best/easiest way depends on the sheet one tries to create.
We will here show two examples using the *EvTable* and *EvForm* utilities.Later we will create
Commands to edit and display the output from those utilities.

> Note that due to the limitations of the wiki, no color is used in any of the examples. See 
> [the text tag documentation](../Concepts/TextTags.md) for how to add color to the tables and forms.

#### Making a sheet with EvTable

[EvTable](github:evennia.utils.evtable) is a text-table generator. It helps with displaying text in
ordered rows and columns. This is an example of using it in code:

````python
# this can be tried out in a Python shell like iPython

from evennia.utils import evtable

# we hardcode these for now, we'll get them as input later
STR, CON, DEX, INT, WIS, CHA = 12, 13, 8, 10, 9, 13

table = evtable.EvTable("Attr", "Value",
                        table = [
                           ["STR", "CON", "DEX", "INT", "WIS", "CHA"],
                           [STR, CON, DEX, INT, WIS, CHA]
                        ], align='r', border="incols")
````

Above, we create a two-column table by supplying the two columns directly. We also tell the table to
be right-aligned and to use the "incols" border type (borders drawns only in between columns). The
`EvTable` class takes a lot of arguments for customizing its look, you can see [some of the possible
keyword arguments here](github:evennia.utils.evtable#evtable__init__). Once you have the `table` you
could also retroactively add new columns and rows to it with `table.add_row()` and
`table.add_column()`: if necessary the table will expand with empty rows/columns to always remain
rectangular.

The result from printing the above table will be

```python
table_string = str(table)

print(table_string)

 Attr | Value
~~~~~~+~~~~~~~
  STR |    12
  CON |    13
  DEX |     8
  INT |    10
  WIS |     9
  CHA |    13
```

This is a minimalistic but effective Character sheet. By combining the `table_string` with other
strings one could build up a reasonably full graphical representation of a Character. For more
advanced layouts we'll look into EvForm next.

#### Making a sheet with EvForm

[EvForm](github:evennia.utils.evform) allows the creation of a two-dimensional "graphic" made by
text characters. On this surface, one marks and tags rectangular regions ("cells") to be filled with
content. This content can be either normal strings or `EvTable` instances (see the previous section,
one such instance would be the `table` variable in that example).

In the case of a Character sheet, these cells would be comparable to a line or box where you could
enter the name of your character or their strength score. EvMenu also easily allows to update the
content of those fields in code (it use EvTables so you rebuild the table first before re-sending it
to EvForm).

The drawback of EvForm is that its shape is static; if you try to put more text in a region than it
was sized for, the text will be cropped. Similarly, if you try to put an EvTable instance in a field
too small for it, the EvTable will do its best to try to resize to fit, but will eventually resort
to cropping its data or even give an error if too small to fit any data.

An EvForm is defined in a Python module. Create a new file `mygame/world/charsheetform.py` and
modify it thus:

````python
#coding=utf-8

# in mygame/world/charsheetform.py

FORMCHAR = "x"
TABLECHAR = "c"

FORM = """
.--------------------------------------.
|                                      |
| Name: xxxxxxxxxxxxxx1xxxxxxxxxxxxxxx |
|       xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx |
|                                      |
 >------------------------------------<
|                                      |
| ccccccccccc  Advantages:             |
| ccccccccccc   xxxxxxxxxxxxxxxxxxxxxx |
| ccccccccccc   xxxxxxxxxx3xxxxxxxxxxx |
| ccccccccccc   xxxxxxxxxxxxxxxxxxxxxx |
| ccccc2ccccc  Disadvantages:          |
| ccccccccccc   xxxxxxxxxxxxxxxxxxxxxx |
| ccccccccccc   xxxxxxxxxx4xxxxxxxxxxx |
| ccccccccccc   xxxxxxxxxxxxxxxxxxxxxx |
|                                      |
+--------------------------------------+
"""
````
The `#coding` statement (which must be put on the very first line to work) tells Python to use the
utf-8 encoding for the file. Using the `FORMCHAR` and `TABLECHAR` we define what single-character we
want to use to "mark" the regions of the character sheet holding cells and tables respectively.
Within each block (which must be separated from one another by at least one non-marking character)
we embed identifiers 1-4 to identify each block. The identifier could be any single character except
for the `FORMCHAR` and `TABLECHAR`

> You can still use `FORMCHAR` and `TABLECHAR` elsewhere in your sheet, but not in a way that it
would identify a cell/table. The smallest identifiable cell/table area is 3 characters wide
including the identifier (for example `x2x`).

Now we will map content to this form.

````python
# again, this can be tested in a Python shell

# hard-code this info here, later we'll ask the
# account for this info. We will re-use the 'table'
# variable from the EvTable example.

NAME = "John, the wise old admin with a chip on his shoulder"
ADVANTAGES = "Language-wiz, Intimidation, Firebreathing"
DISADVANTAGES = "Bad body odor, Poor eyesight, Troubled history"

from evennia.utils import evform

# load the form from the module
form = evform.EvForm("world/charsheetform.py")

# map the data to the form
form.map(cells={"1":NAME, "3": ADVANTAGES, "4": DISADVANTAGES},
         tables={"2":table})
````

We create some RP-sounding input and re-use the `table` variable from the previous `EvTable`
example.

> Note, that if you didn't want to create the form in a separate module you *could* also load it
directly into the `EvForm` call like this: `EvForm(form={"FORMCHAR":"x", "TABLECHAR":"c", "FORM":
formstring})` where `FORM` specifies the form as a string in the same way as listed in the module
above. Note however that the very first line of the `FORM` string is ignored, so start with a `\n`.

We then map those to the cells of the form:

````python
print(form)
````
````
.--------------------------------------.
|                                      |
| Name: John, the wise old admin with |
|        a chip on his shoulder        |
|                                      |
 >------------------------------------<
|                                      |
|  Attr|Value  Advantages:             |
| ~~~~~+~~~~~   Language-wiz,          |
|   STR|   12   Intimidation,          |
|   CON|   13   Firebreathing          |
|   DEX|    8  Disadvantages:          |
|   INT|   10   Bad body odor, Poor    |
|   WIS|    9   eyesight, Troubled     |
|   CHA|   13   history                |
|                                      |
+--------------------------------------+
````

As seen, the texts and tables have been slotted into the text areas and line breaks have been added
where needed. We chose to just enter the Advantages/Disadvantages as plain strings here, meaning
long names ended up split between rows. If we wanted more control over the display we could have
inserted `\n` line breaks after each line or used a borderless `EvTable` to display those as well.

### Tie a Character sheet to a Character

We will assume we go with the `EvForm` example above. We now need to attach this to a Character so
it can be modified. For this we will modify our `Character` class a little more:

```python
# mygame/typeclasses/character.py

from evennia.utils import evform, evtable

[...]

class Character(DefaultCharacter):
    [...]
    def at_object_creation(self):
        "called only once, when object is first created"
        # we will use this to stop account from changing sheet
        self.db.sheet_locked = False
        # we store these so we can build these on demand
        self.db.chardata  = {"str": 0,
                             "con": 0,
                             "dex": 0,
                             "int": 0,
                             "wis": 0,
                             "cha": 0,
                             "advantages": "",
                             "disadvantages": ""}
        self.db.charsheet = evform.EvForm("world/charsheetform.py")
        self.update_charsheet()

    def update_charsheet(self):
        """
        Call this to update the sheet after any of the ingoing data
        has changed.
        """
        data = self.db.chardata
        table = evtable.EvTable("Attr", "Value",
                        table = [
                           ["STR", "CON", "DEX", "INT", "WIS", "CHA"],
                           [data["str"], data["con"], data["dex"],
                            data["int"], data["wis"], data["cha"]]],
                           align='r', border="incols")
        self.db.charsheet.map(tables={"2": table},
                              cells={"1":self.key,
                                     "3":data["advantages"],
                                     "4":data["disadvantages"]})

```

Use `@reload` to make this change available to all *newly created* Characters. *Already existing*
Characters will *not* have the charsheet defined, since `at_object_creation` is only called once.
The easiest to force an existing Character to re-fire its `at_object_creation` is to use the
`@typeclass` command in-game:

```
@typeclass/force <Character Name>
```

### Command for Account to change Character sheet

We will add a command to edit the sections of our Character sheet. Open
`mygame/commands/command.py`.

```python
# at the end of mygame/commands/command.py

ALLOWED_ATTRS = ("str", "con", "dex", "int", "wis", "cha")
ALLOWED_FIELDNAMES = ALLOWED_ATTRS + \
                     ("name", "advantages", "disadvantages")

def _validate_fieldname(caller, fieldname):
    "Helper function to validate field names."
    if fieldname not in ALLOWED_FIELDNAMES:
        list_of_fieldnames = ", ".join(ALLOWED_FIELDNAMES)
        err = f"Allowed field names: {list_of_fieldnames}"
        caller.msg(err)
        return False
    if fieldname in ALLOWED_ATTRS and not value.isdigit():
        caller.msg(f"{fieldname} must receive a number.")
        return False
    return True

class CmdSheet(MuxCommand):
    """
    Edit a field on the character sheet

    Usage:
      @sheet field value

    Examples:
      @sheet name Ulrik the Warrior
      @sheet dex 12
      @sheet advantages Super strength, Night vision

    If given without arguments, will view the current character sheet.

    Allowed field names are:
       name,
       str, con, dex, int, wis, cha,
       advantages, disadvantages

    """

    key = "sheet"
    aliases = "editsheet"
    locks = "cmd: perm(Players)"
    help_category = "RP"

    def func(self):
        caller = self.caller
        if not self.args or len(self.args) < 2:
            # not enough arguments. Display the sheet
            if sheet:
                caller.msg(caller.db.charsheet)
            else:
                caller.msg("You have no character sheet.")
            return

        # if caller.db.sheet_locked:
            caller.msg("Your character sheet is locked.")
            return

        # split input by whitespace, once
        fieldname, value = self.args.split(None, 1)
        fieldname = fieldname.lower() # ignore case

        if not _validate_fieldnames(caller, fieldname):
            return
        if fieldname == "name":
            self.key = value
        else:
            caller.chardata[fieldname] = value
        caller.update_charsheet()
        caller.msg(f"{fieldname} was set to {value}.")

```

Most of this command is error-checking to make sure the right type of data was input. Note how the
`sheet_locked` Attribute is checked and will return if not set.

This command you import into `mygame/commands/default_cmdsets.py` and add to the `CharacterCmdSet`,
in the same way the `@gm` command was added to the `AccountCmdSet` earlier.

### Commands for GM to change Character sheet

Game masters use basically the same input as Players do to edit a character sheet, except they can
do it on other players than themselves. They are also not stopped by any `sheet_locked` flags.

```python
# continuing in mygame/commands/command.py

class CmdGMsheet(MuxCommand):
    """
    GM-modification of char sheets

    Usage:
      @gmsheet character [= fieldname value]

    Switches:
      lock - lock the character sheet so the account
             can no longer edit it (GM's still can)
      unlock - unlock character sheet for Account
             editing.

    Examples:
      @gmsheet Tom
      @gmsheet Anna = str 12
      @gmsheet/lock Tom

    """
    key = "gmsheet"
    locks = "cmd: perm(Admins)"
    help_category = "RP"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("Usage: @gmsheet character [= fieldname value]")

        if self.rhs:
            # rhs (right-hand-side) is set only if a '='
            # was given.
            if len(self.rhs) < 2:
                caller.msg("You must specify both a fieldname and value.")
                return
            fieldname, value = self.rhs.split(None, 1)
            fieldname = fieldname.lower()
            if not _validate_fieldname(caller, fieldname):
                return
            charname = self.lhs
        else:
            # no '=', so we must be aiming to look at a charsheet
            fieldname, value = None, None
            charname = self.args.strip()

        character = caller.search(charname, global_search=True)
        if not character:
            return

        if "lock" in self.switches:
            if character.db.sheet_locked:
                caller.msg("The character sheet is already locked.")
            else:
                character.db.sheet_locked = True
                caller.msg(f"{character.key} can no longer edit their character sheet.")
        elif "unlock" in self.switches:
            if not character.db.sheet_locked:
                caller.msg("The character sheet is already unlocked.")
            else:
                character.db.sheet_locked = False
                caller.msg(f"{character.key} can now edit their character sheet.")

        if fieldname:
            if fieldname == "name":
                character.key = value
            else:
                character.db.chardata[fieldname] = value
            character.update_charsheet()
            caller.msg(f"You set {character.key}'s {fieldname} to {value}.")
        else:
            # just display
            caller.msg(character.db.charsheet)
```

The `@gmsheet` command takes an additional argument to specify which Character's character sheet to
edit. It also takes `/lock` and `/unlock` switches to block the Player from tweaking their sheet.

Before this can be used, it should be added to the default `CharacterCmdSet` in the same way as the
normal `@sheet`. Due to the lock set on it, this command will only be available to `Admins` (i.e.
GMs) or higher permission levels.

## Dice roller

Evennia's *contrib* folder already comes with a full dice roller. To add it to the game, simply
import `contrib.dice.CmdDice` into `mygame/commands/default_cmdsets.py` and add `CmdDice` to the
`CharacterCmdset` as done with other commands in this tutorial. After a `@reload` you will be able
to roll dice using normal RPG-style format:

```
roll 2d6 + 3
7
```

Use `help dice` to see what syntax is supported or look at `evennia/contrib/dice.py` to see how it's
implemented.

## Rooms

Evennia comes with rooms out of the box, so no extra work needed. A GM will automatically have all
needed building commands available. A fuller go-through is found in the [Building tutorial](Beginner-Tutorial/Part1/Beginner-Tutorial-Building-Quickstart.md).
Here are some useful highlights:

* `@dig roomname;alias = exit_there;alias, exit_back;alias` - this is the basic command for digging
a new room. You can specify any exit-names and just enter the name of that exit to go there.
* `@tunnel direction = roomname` - this is a specialized command that only accepts directions in the
cardinal directions (n,ne,e,se,s,sw,w,nw) as well as in/out and up/down. It also automatically
builds "matching" exits back in the opposite direction.
* `@create/drop objectname` - this creates and drops a new simple object in the current location.
* `@desc obj` - change the look-description of the object.
* `@tel object = location` - teleport an object to a named location.
* `@search objectname` - locate an object in the database.

> TODO: Describe how to add a logging room, that logs says and poses to a log file that people can
access after the fact.

## Channels

Evennia comes with [Channels](../Components/Channels.md) in-built and they are described fully in the
documentation. For brevity, here are the relevant commands for normal use:

* `@ccreate new_channel;alias;alias = short description` - Creates a new channel.
* `addcom channel` - join an existing channel. Use `addcom alias = channel` to add a new alias you
can use to talk to the channel, as many as desired.
* `delcom alias or channel` - remove an alias from a channel or, if the real channel name is given,
unsubscribe completely.
* `@channels` lists all available channels, including your subscriptions and any aliases you have
set up for them.

You can read channel history: if you for example are chatting on the `public` channel you can do
`public/history` to see the 20 last posts to that channel or `public/history 32` to view twenty
posts backwards, starting with the 32nd from the end.

## PMs

To send PMs to one another, players can use the `@page` (or `tell`) command:

```
page recipient = message
page recipient, recipient, ... = message
```

Players can use `page` alone to see the latest messages. This also works if they were not online
when the message was sent.