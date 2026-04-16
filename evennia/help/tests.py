"""
Unittests for help code (The default help-command is tested as part of default
command test-suite).

"""

from unittest import mock

from parameterized import parameterized

from evennia.help import filehelp
from evennia.help import utils as help_utils
from evennia.utils.test_resources import TestCase
from evennia.utils.utils import dedent


class TestParseSubtopics(TestCase):
    """
    Test the subtopic parser.

    """

    def test_parse_entry(self):
        """
        Test for subcategories

        """
        self.maxDiff = None

        entry = dedent(
            """
            Main topic text
            # subtopics
            ## foo
            Foo sub-category
            ### moo
            Foo/Moo subsub-category
            #### dum
            Foo/Moo/Dum subsubsub-category
            ## bar
            Bar subcategory
            ### moo
            Bar/Moo subcategory
        """,
            indent=0,
        )
        expected = {
            None: "Main topic text",
            "foo": {
                None: "\nFoo sub-category\n",
                "moo": {
                    None: "\nFoo/Moo subsub-category\n",
                    "dum": {
                        None: "\nFoo/Moo/Dum subsubsub-category\n",
                    },
                },
            },
            "bar": {None: "\nBar subcategory\n", "moo": {None: "\nBar/Moo subcategory"}},
        }

        actual_result = help_utils.parse_entry_for_subcategories(entry)
        self.assertEqual(expected, actual_result)

    def test_parse_single_entry(self):
        """
        Test parsing single subcategory

        """

        entry = dedent(
            """
        Main topic text
        # SUBTOPICS
        ## creating extra stuff
        Help on creating extra stuff.
        """,
            indent=0,
        )
        expected = {
            None: "Main topic text",
            "creating extra stuff": {None: "\nHelp on creating extra stuff."},
        }

        actual_result = help_utils.parse_entry_for_subcategories(entry)
        self.assertEqual(expected, actual_result)


# test filehelp system

HELP_ENTRY_DICTS = [
    {
        "key": "evennia",
        "aliases": ["ev"],
        "category": "General",
        "text": """
            Evennia is a MUD game server in Python.

            # subtopics

            ## Installation

            You'll find installation instructions on https:evennia.com

            ## Community

            There are many ways to get help and communicate with other devs!

            ### Discord

            There is also a discord channel you can find from the sidebard on evennia.com.

        """,
    },
    {
        "key": "building",
        "category": "building",
        "text": """
            Evennia comes with a bunch of default building commands. You can
            find a building tutorial in the evennia documentation.

        """,
    },
]


class TestFileHelp(TestCase):
    """
    Test the File-help system

    """

    @mock.patch("evennia.help.filehelp.variable_from_module")
    def test_file_help(self, mock_variable_from_module):
        mock_variable_from_module.return_value = HELP_ENTRY_DICTS

        # we just need anything here since we mock the load anyway
        storage = filehelp.FileHelpStorageHandler(help_file_modules=["dummypath"])
        result = storage.all()

        for inum, helpentry in enumerate(result):
            self.assertEqual(HELP_ENTRY_DICTS[inum]["key"], helpentry.key)
            self.assertEqual(HELP_ENTRY_DICTS[inum].get("aliases", []), helpentry.aliases)
            self.assertEqual(HELP_ENTRY_DICTS[inum]["category"].lower(), helpentry.help_category)
            self.assertEqual(HELP_ENTRY_DICTS[inum]["text"], helpentry.entrytext)


class HelpUtils(TestCase):

    def setUp(self):
        self.candidate_entries = [
            filehelp.FileHelpEntry(
                key="*examine",
                aliases=["*exam", "*ex", "@examine"],
                help_category="building",
                entrytext="Lorem ipsum examine",
                lock_storage="",
            ),
            filehelp.FileHelpEntry(
                key="inventory",
                aliases=[],
                help_category="general",
                entrytext="A character's inventory",
                lock_storage="",
            ),
            filehelp.FileHelpEntry(
                key="userpassword",
                aliases=[],
                help_category="admin",
                entrytext="change the password of an account",
                lock_storage="",
            ),
        ]

    @parameterized.expand(
        [
            ("*examine", "*examine", "Leading wildcard should return exact matches."),
            ("@examine", "*examine", "Aliases should return an entry."),
            ("inventory", "inventory", "It should return exact matches."),
            ("inv*", "inventory", "Trailing wildcard search should return an entry."),
            ("userpaZZword~2", "userpassword", "Fuzzy matching should return an entry."),
            (
                "*word",
                "userpassword",
                "Leading wildcard should return an entry when no exact match.",
            ),
        ]
    )
    def test_help_search_with_index(self, search_term, expected_entry_key, error_msg):
        """Test search terms return correct entries"""

        expected_entry = [
            entry for entry in self.candidate_entries if entry.key == expected_entry_key
        ]

        entries, _ = help_utils.help_search_with_index(search_term, self.candidate_entries)

        self.assertEqual(entries, expected_entry, error_msg)
