"""
File-based help entries. These complements command-based help and help entries
added in the database using the `sethelp` command in-game.

Control where Evennia reads these entries with `settings.FILE_HELP_ENTRY_MODULES`,
which is a list of python-paths to modules to read.

A module like this should hold a global `HELP_ENTRY_DICTS` list, containing
dicts that each represent a help entry. If no `HELP_ENTRY_DICTS` variable is
given, all top-level variables that are dicts in the module are read as help
entries.

Each dict is on the form
::

    {'key': <str>,
     'category': <str>,   # optional, otherwise settings.FILE_DEFAULT_HELP_CATEGORY
     'aliases': <list>,   # optional
     'text': <str>}``     # the actual help text. Can contain # subtopic sections

"""

HELP_ENTRY_DICTS = [
    {
        "key": "evennia",
        "aliases": ['ev'],
        "category": "General",
        "text": """
            Evennia is a MUD game server in Python.

            # subtopics

            ## Installation

            You'll find installation instructions on https:evennia.com

            ## Community

            There are many ways to get help and communicate with other devs!

            ### IRC

            The irc channel is #evennia on irc.freenode.net

            ### Discord

            There is also a discord channel you can find from the sidebard on evennia.com.

        """
    },
    {
        "key": "building",
        "category": "building",
        "text": """
            Evennia comes with a bunch of default building commands. You can
            find a building tutorial in the evennia documentation.

        """
    }
]
