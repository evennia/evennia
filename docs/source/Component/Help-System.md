# Help System


An important part of Evennia is the online help system. This allows the players and staff alike to
learn how to use the game's commands as well as other information pertinent to the game. The help
system has many different aspects, from the normal editing of help entries from inside the game, to
auto-generated help entries during code development using the *auto-help system*.

## Viewing the help database

The main command is `help`: 

     help [searchstring]

This will show a list of help entries, ordered after categories. You will find two sections,
*Command help entries* and *Other help entries* (initially you will only have the first one). You
can use help to get more info about an entry; you can also give partial matches to get suggestions.
If you give category names you will only be shown the topics in that category.


## Command Auto-help system

A common item that requires help entries are in-game commands. Keeping these entries up-to-date with
the actual source code functionality can be a chore. Evennia's commands are therefore auto-
documenting straight from the sources through its *auto-help system*.  Only commands that you and
your character can actually currently use are picked up by the auto-help system. That means an admin
will see a considerably larger amount of help topics than a normal player when using the default
`help` command.

The auto-help system uses the `__doc__` strings of your command classes and formats this to a nice-
looking help entry. This makes for a very easy way to keep the help updated - just document your
commands well and updating the help file is just a `@reload` away.  There is no need to manually
create and maintain help database entries for commands; as long as you keep the docstrings updated
your help will be dynamically updated for you as well.

Example (from a module with command definitions): 

```python
    class CmdMyCmd(Command):
       """
       mycmd - my very own command
    
       Usage: 
         mycmd[/switches] <args>
    
       Switches:
         test - test the command
         run  - do something else
    
       This is my own command that does this and that.
    
       """
       # [...]

       help_category = "General"    # default
       auto_help = True             # default
       
       # [...]
```

The text at the very top of the command class definition is the class' `__doc__`-string and will be
shown to users looking for help. Try to use a consistent format - all default commands are using the
structure shown above.

You should also supply the `help_category` class property if you can; this helps to group help
entries together for people to more easily find them. See the `help` command in-game to see the
default categories. If you don't specify the category, "General" is assumed.

If you don't want your command to be picked up by the auto-help system at all (like if you want to
write its docs manually using the info in the next section or you use a [cmdset](Command-Sets) that
has its own help functionality) you can explicitly set `auto_help` class property to `False` in your
command definition.

Alternatively, you can keep the advantages of *auto-help* in commands, but control the display of
command helps.  You can do so by overriding the command's `get_help()` method.  By default, this
method will return the class docstring.  You could modify it to add custom behavior:  the text
returned by this method will be displayed to the character asking for help in this command.

## Database help entries

These are all help entries not involving commands (this is handled automatically by the [Command
Auto-help system](Help-System#command-auto-help-system)).  Non-automatic help entries describe how
your particular game is played - its rules, world descriptions and so on.

A help entry consists of four parts: 

- The *topic*. This is the name of the help entry. This is what players search for when they are
looking for help. The topic can contain spaces and also partial matches will be found.
- The *help category*. Examples are *Administration*, *Building*, *Comms* or *General*. This is an
overall grouping of similar help topics, used by the engine to give a better overview.
- The *text* - the help text itself, of any length.
- locks - a [lock definition](Locks). This can be used to limit access to this help entry, maybe
because it's staff-only or otherwise meant to be restricted. Help commands check for `access_type`s
`view` and `edit`. An example of a lock string would be `view:perm(Builders)`.

You can create new help entries in code by using `evennia.create_help_entry()`.

```python
from evennia import create_help_entry
entry = create_help_entry("emote", 
                "Emoting is important because ...", 
                category="Roleplaying", locks="view:all()")
```

From inside the game those with the right permissions can use the `@sethelp` command to add and
modify help entries.

    > @sethelp/add emote = The emote command is ...

Using `@sethelp` you can add, delete and append text to existing entries. By default new entries
will go in the *General* help category. You can change this using a different form of the `@sethelp`
command:

    > @sethelp/add emote, Roleplaying = Emoting is important because ...

If the category *Roleplaying* did not already exist, it is created and will appear in the help
index.

You can, finally, define a lock for the help entry by following the category with a [lock
definition](Locks):

    > @sethelp/add emote, Roleplaying, view:all() = Emoting is ... 