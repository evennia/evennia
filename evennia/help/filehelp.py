"""
The filehelp-system allows for defining help files outside of the game. These
will be treated as non-command help entries and displayed in the same way as
help entries created using the `sethelp` default command. After changing an
entry on-disk you need to reload the server to have the change show in-game.

An filehelp file is a regular python module with dicts representing each help
entry. If a list `HELP_ENTRY_DICTS` is found in the module, this should be a list of
dicts.  Otherwise *all* top-level dicts in the module will be assumed to be a
help-entry dict.

Each help-entry dict is on the form
::

    {'key': <str>,
     'text': <str>,
     'category': <str>,   # optional, otherwise settings.DEFAULT_HELP_CATEGORY
     'aliases': <list>,   # optional
     'locks': <str>}      # optional, use access-type 'view'. Default is view:all()

The `text`` should be formatted on the same form as other help entry-texts and
can contain ``# subtopics`` as normal.

New help-entry modules are added to the system by providing the python-path to
the module to `settings.FILE_HELP_ENTRY_MODULES`. Note that if same-key entries are
added, entries in latter modules will override that of earlier ones. Use
`settings.DEFAULT_HELP_CATEGORY`` to customize what category is used if
not set explicitly.

An example of the contents of a module:
::

    help_entry1 = {
        "key": "The Gods",   # case-insensitive, also partial-matching ('gods') works
        "aliases": ['pantheon', 'religion'],
        "category": "Lore",
        "locks": "view:all()",   # this is optional unless restricting access
        "text": '''
            The gods formed the world ...

            # Subtopics

            ## Pantheon

            ...

            ### God of love

            ...

            ### God of war

            ...

        '''
    }


    HELP_ENTRY_DICTS = [
        help_entry1,
        ...
    ]

----

"""

from dataclasses import dataclass

from django.conf import settings
from django.urls import reverse
from django.utils.text import slugify

from evennia.locks.lockhandler import LockHandler
from evennia.utils import logger
from evennia.utils.utils import (
    all_from_module,
    lazy_property,
    make_iter,
    variable_from_module,
)

_DEFAULT_HELP_CATEGORY = settings.DEFAULT_HELP_CATEGORY


@dataclass
class FileHelpEntry:
    """
    Represents a help entry read from file. This mimics the api of the
    database-bound HelpEntry so that they can be used interchangeably in the
    help command.

    """

    key: str
    aliases: list
    help_category: str
    entrytext: str
    lock_storage: str

    @property
    def search_index_entry(self):
        """
        Property for easily retaining a search index entry for this object.

        """
        return {
            "key": self.key,
            "aliases": " ".join(self.aliases),
            "category": self.help_category,
            "no_prefix": "",
            "tags": "",
            "locks": "",
            "text": self.entrytext,
        }

    def __str__(self):
        return self.key

    def __repr__(self):
        return f"<FileHelpEntry {self.key}>"

    @lazy_property
    def locks(self):
        return LockHandler(self)

    def web_get_detail_url(self):
        """
        Returns the URI path for a View that allows users to view details for
        this object.

        ex. Oscar (Character) = '/characters/oscar/1/'

        For this to work, the developer must have defined a named view somewhere
        in urls.py that follows the format 'modelname-action', so in this case
        a named view of 'character-detail' would be referenced by this method.

        ex.
        ::
            url(r'characters/(?P<slug>[\w\d\-]+)/(?P<pk>[0-9]+)/$',
                CharDetailView.as_view(), name='character-detail')

        If no View has been created and defined in urls.py, returns an
        HTML anchor.

        This method is naive and simply returns a path. Securing access to
        the actual view and limiting who can view this object is the developer's
        responsibility.

        Returns:
            path (str): URI path to object detail page, if defined.

        """
        try:
            return reverse(
                "help-entry-detail",
                kwargs={"category": slugify(self.help_category), "topic": slugify(self.key)},
            )
        except Exception:
            return "#"

    def web_get_admin_url(self):
        """
        Returns the URI path for the Django Admin page for this object.

        ex. Account#1 = '/admin/accounts/accountdb/1/change/'

        Returns:
            path (str): URI path to Django Admin page for object.

        """
        return False

    def access(self, accessing_obj, access_type="view", default=True):
        """
        Determines if another object has permission to access this help entry.

        Args:
            accessing_obj (Object or Account): Entity trying to access this one.
            access_type (str): type of access sought.
            default (bool): What to return if no lock of `access_type` was found.

        """
        return self.locks.check(accessing_obj, access_type=access_type, default=default)


class FileHelpStorageHandler:
    """
    This reads and stores help entries for quick access. By default
    it reads modules from `settings.FILE_HELP_ENTRY_MODULES`.

    Note that this is not meant to any searching/lookup - that is all handled
    by the help command.

    """

    def __init__(self, help_file_modules=settings.FILE_HELP_ENTRY_MODULES):
        """
        Initialize the storage.
        """
        self.help_file_modules = [str(part).strip() for part in make_iter(help_file_modules)]
        self.help_entries = []
        self.help_entries_dict = {}
        self.load()

    def load(self):
        """
        Load/reload file-based help-entries from file.

        """
        loaded_help_dicts = []

        for module_or_path in self.help_file_modules:
            help_dict_list = variable_from_module(module_or_path, variable="HELP_ENTRY_DICTS")
            if not help_dict_list:
                help_dict_list = [
                    dct for dct in all_from_module(module_or_path).values() if isinstance(dct, dict)
                ]
            if help_dict_list:
                loaded_help_dicts.extend(help_dict_list)
            else:
                logger.log_err(f"Could not find file-help module {module_or_path} (skipping).")

        # validate and parse dicts into FileEntryHelp objects and make sure they are unique-by-key
        # by letting latter added ones override earlier ones.
        unique_help_entries = {}

        for dct in loaded_help_dicts:
            key = dct.get("key").lower().strip()
            category = dct.get("category", _DEFAULT_HELP_CATEGORY).strip()
            aliases = list(dct.get("aliases", []))
            entrytext = dct.get("text", "")
            locks = dct.get("locks", "")

            if not key and entrytext:
                logger.error(f"Cannot load file-help-entry (missing key or text): {dct}")
                continue

            unique_help_entries[key] = FileHelpEntry(
                key=key,
                help_category=category,
                aliases=aliases,
                lock_storage=locks,
                entrytext=entrytext,
            )

        self.help_entries_dict = unique_help_entries
        self.help_entries = list(unique_help_entries.values())

    def all(self, return_dict=False):
        """
        Get all help entries.

        Args:
            return_dict (bool): Return a dict ``{key: FileHelpEntry,...}``. Otherwise,
                return a list of ``FileHelpEntry`.

        Returns:
            dict or list: Depending on the setting of ``return_dict``.

        """
        return self.help_entries_dict if return_dict else self.help_entries


# singleton to hold the loaded help entries
FILE_HELP_ENTRIES = FileHelpStorageHandler()
