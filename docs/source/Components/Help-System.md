# Help System

Evennia has an extensive help system covering both command-help and regular
free-form help documentation. It supports subtopics and if failing to find a
match it will provide suggestsions, first from alternative topics and then by
finding mentions of the search term in help entries.


    help theatre

```
------------------------------------------------------------------------------
Help for The theatre (aliases: the hub, curtains)

The theatre is at the centre of the city, both literally and figuratively ...
(A lot more text about it follows ...)

Subtopics:
  theatre/lore
  theatre/layout
  theatre/dramatis personae
------------------------------------------------------------------------------
```

    help evennia

```
------------------------------------------------------------------------------
No help found

There is no help topic matching 'evennia'.
... But matches where found within the help texts of the suggestions below.

Suggestions:
  grapevine2chan, about, irc2chan
-----------------------------------------------------------------------------
```

## Using the help system from in-game

The help system is accessed in-game by use of the `help` command:

    help <topic>

Sub-topics are accessed as `help <topic>/<subtopic>/...`.

Creating a new help entry from in-game is done with

    sethelp <topic>[;aliases] [,category] [,lockstring] = <text>

For example

    sethelp The Gods;pantheon, Lore = In the beginning all was dark ...

Use the `/edit` switch to open the EvEditor for more convenient in-game writing
(but note that devs can also create help entries outside the game using their
regular code editor, see below).

> You can also create help entries as Python modules, outside of the game. These
> can not be modified from in-game.

## Sources of help entries

Evennia collects help entries from three sources:

- _Auto-generated command help_ - this is literally the doc-strings of
  the [Command classes](./Commands). The idea is that the command docs are
  easier to maintain and keep up-to-date if the developer can change them at the
  same time as they do the code.
- _Database-stored help entries_ - These are created in-game (using the
  default `sethelp` command as exemplified in the previous section).
- _File-stored help entries_ - These are created outside the game, as dicts in
  normal Python modules. They allows developers to write and maintain their help
  files using a proper text editor.

### The Help Entry

All help entries (no matter the source) have the following properties:

- `key` - This is the main topic-name. For Commands, this is literally the
  command's `key`.
- `aliases` - Alternate names for the help entry. This can be useful if the main
  name is hard to remember.
- `help_category` - The general grouping of the entry. This is optional. If not
  given it will use the default category given by
  `settings.COMMAND_DEFAULT_HELP_CATEGORY` for Commands and
  `settings.DEFAULT_HELP_CATEGORY` for file+db help entries.
- `locks` - Lock string (for commands) or LockHandler (all help entries).
   This defines who may read this entry. See the next section.
- `tags` - This is not used by default, but could be used to further organize
  help entries.
- `text` - The actual help entry text. This will be dedented and stripped of
  extra space at beginning and end.

A `text` that scrolls off the screen will automatically be paginated by
the [EvMore](./EvMore) pager (you can control this with
`settings.HELP_MORE_ENABLED=False`). If you use EvMore and want to control
exactly where the pager should break the page, mark the break with the control
character `\f`.

#### Subtopics

```versionadded:: 1.0
```

Rather than making a very long help entry, the `text` may also be broken up
into _subtopics_. A list of the next level of subtopics are shown below the
main help text and allows the user to read more about some particular detail
that wouldn't fit in the main text.

Subtopics use a markup slightly similar to markdown headings. The top level
heading must be named `# subtopics` (non case-sensitive) and the following
headers must be sub-headings to this (so `## subtopic name` etc). All headings
are non-case sensitive (the help command will format them). The topics can be
nested at most to a depth of 5 (which is probably too many levels already). The
parser uses fuzzy matching to find the subtopic, so one does not have to type
it all out exactly.

Below is an example of a `text` with sub topics.

```
The theatre is the heart of the city, here you can find ...
(This is the main help text, what you get with `help theatre`)

# subtopics

## lore

The theatre holds many mysterious things...
(`help theatre/lore`)

### the grand opening

The grand opening is the name for a mysterious event where ghosts appeared ...
(`this is a subsub-topic to lore, accessible as `help theatre/lore/grand` or
any other partial match).

### the Phantom

Deep under the theatre, rumors has it a monster hides ...
(another subsubtopic, accessible as `help theatre/lore/phantom`)

## layout

The theatre is a two-story building situated at ...
(`help theatre/layout`)

## dramatis personae

There are many interesting people prowling the halls of the theatre ...
(`help theatre/dramatis` or `help theathre/drama` or `help theatre/personae` would work)

### Primadonna Ada

Everyone knows the primadonna! She is ...
(A subtopic under dramatis personae, accessible as `help theatre/drama/ada` etc)

### The gatekeeper

He always keeps an eye on the door and ...
(`help theatre/drama/gate`)

```
### Command Auto-help system

The auto-help system uses the `__doc__` strings of your command classes and
formats this to a nice- looking help entry. This makes for a very easy way to
keep the help updated - just document your commands well and updating the help
file is just a `reload` away.

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

       locks = "cmd:all();read:all()"  # default
       help_category = "General"       # default
       auto_help = True                # default

       # [...]
```

The text at the very top of the command class definition is the class'
`__doc__`-string and will be shown to users looking for help. Try to use a
consistent format - all default commands are using the structure shown above.

You can limit access to the help entry by the `view` and/or `read` locks on the
Command. See [the section below](#Locking-help-entries) for details.

You should also supply the `help_category` class property if you can; this helps
to group help entries together for people to more easily find them. See the
`help` command in-game to see the default categories. If you don't specify the
category, `settings.COMMAND_DEFAULT_HELP_CATEGORY` (default is "General") is
used.

If you don't want your command to be picked up by the auto-help system at all
(like if you want to write its docs manually using the info in the next section
or you use a [cmdset](./Command-Sets) that has its own help functionality) you
can explicitly set `auto_help` class property to `False` in your command
definition.

Alternatively, you can keep the advantages of *auto-help* in commands, but
control the display of command helps.  You can do so by overriding the command's
`get_help(caller, cmdset)` method.  By default, this method will return the
class docstring.  You could modify it to add custom behavior:  the text returned
by this method will be displayed to the character asking for help in this
command.

### Database-help entries

These are most commonly created in-game using the `sethelp` command. If you need to create one
manually, you can do so with `evennia.create_help_entry()`:

```python

from evennia import create_help_entry
entry = create_help_entry("emote",
                "Emoting is important because ...",
                category="Roleplaying", locks="view:all()")
```

The entity being created is a [evennia.help.models.HelpEntry](api:evennia.help.models.HelpEntry)
object. This is _not_ a [Typeclassed](./Typeclasses) entity and is not meant to
be modified to any great degree. It holds the properties listed earlier. The
text is stored in a field `entrytext`. It does not provide a `get_help` method
like commands, stores and returns the `entrytext` directly.

You can search for (db-)-`HelpEntry` objects using `evennia.search_help` but note that
this will not return the two other types of help entries.

### File-help entries

```versionadded:: 1.0
```

File-help entries are created by the game development team outside of the game. The
help entries are defined in normal Python modules (`.py` file ending) containing
a `dict` to represent each entry. They require a server `reload` before any changes
apply.

- Evennia will look through all modules given by
  `settings.FILE_HELP_ENTRY_MODULES`. This should be a list of python-paths for
  Evennia to import.
- If this module contains a top-level variable `HELP_ENTRY_DICTS`, this will be
  imported and must be a `list` of help-entry dicts.
- If no `HELP_ENTRY_DICTS` list is found, _every_ top-level variable in the
  module that is a `dict` will be read as a help entry. The variable-names will
  be ignored in this case.

If you add multiple modules to be read, same-keyed help entries added later in
the list will override coming before.

Each entry dict must define keys to match that needed by all help entries.
Here's an example of a help module:

```python

# in a module pointed to by settings.FILE_HELP_ENTRY_MODULES

HELP_ENTRY_DICTS = [
  {
    "key": "The Gods",   # case-insensitive, can be searched by 'gods' too
    "aliases": ['pantheon', 'religion']
    "category": "Lore",
    "locks": "read:all()",  # optional
    "text": '''
        The gods formed the world ...

        # Subtopics

        ## Pantheon

        The pantheon consists of 40 gods that ...

        ### God of love

        The most prominent god is ...

        ### God of war

        Also known as 'the angry god', this god is known to ...

    '''
  },
  {
    "key": "The mortals",

  }
]

```

The help entry text will be dedented and will retain paragraphs. You should try
to keep your strings a reasonable width (it will look better). Just reload the
server and the file-based help entries will be available to view.

## Locking help entries

The default `help` command gather all available commands and help entries
together so they can be searched or listed. By setting locks on the command/help
entry one can limit who can read help about it.

- Commands failing the normal `cmd`-lock will be removed before even getting
  to the help command. In this case the other two lock types below are ignored.
- The `view` access type determines if the command/help entry should be visible in
  the main help index. If not given, it is assumed everyone can view.
- The `read` access type determines if the command/help entry can be actually read.
  If a `read` lock is given and `view` is not, the `read`-lock is assumed to
  apply to `view`-access as well (so if you can't read the help entry it will
  also not show up in the index). If `read`-lock is not given, it's assume
  everyone can read the help entry.

For Commands you set the help-related locks the same way you would any lock:

```python
class MyCommand(Command):
    """
    <docstring for command>
    """
    key = "mycommand"
    # everyone can use the command, builders can view it in the help index
    # but only devs can actually read the help (a weird setup for sure!)
    locks = "cmd:all();view:perm(Builders);read:perm(Developers)

```

Db-help entries and File-Help entries work the same way (except the `cmd`-type
lock is not used. A file-help example:

```python
help_entry = {
    # ...
    locks = "read:perm(Developer)",
    # ...
}

```

## Customizing the look of the help system

This is done almost exclusively by overriding the `help` command
[evennia.commands.default.help.CmdHelp](api:evennia.commands.default.help#CmdHelp).

Since the available commands may vary from moment to moment, `help` is
responsible for collating the three sources of help-entries (commands/db/file)
together and search through them on the fly. It also does all the formatting of
the output.

To make it easier to tweak the look, the parts of the code that changes the
visual presentation has been broken out into separate methods
`format_help_entry` and `format_help_index` - override these in your version of
`help` to change the display as you please. See the api link above for details.

## Technical notes

Since it needs to search so different types of data, the help system has to
collect all possibilities in memory before searching through the entire set. It
uses the [Lunr](https://github.com/yeraydiazdiaz/lunr.py) search engine to
search through the main bulk of help entries. Lunr is a mature engine used for
web-pages and produces much more sensible results than previous solutions.

Once the main entry has been found, subtopics are then searched with
simple `==`, `startswith` and `in` matching (there are so relatively few of them
at that point).

```versionchanged:: 1.0
  Replaced the bag-of-words algorithm with lunr.

```
