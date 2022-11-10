"""
Test tree select

"""

from evennia.contrib.utils.fieldfill import fieldfill
from evennia.utils.test_resources import BaseEvenniaTest

from . import tree_select

TREE_MENU_TESTSTR = """Foo
Bar
-Baz
--Baz 1
--Baz 2
-Qux"""


class TestTreeSelectFunc(BaseEvenniaTest):
    def test_tree_functions(self):
        # Dash counter
        self.assertTrue(tree_select.dashcount("--test") == 2)
        # Is category
        self.assertTrue(tree_select.is_category(TREE_MENU_TESTSTR, 1) is True)
        # Parse options
        self.assertTrue(
            tree_select.parse_opts(TREE_MENU_TESTSTR, category_index=2)
            == [(3, "Baz 1"), (4, "Baz 2")]
        )
        # Index to selection
        self.assertTrue(tree_select.index_to_selection(TREE_MENU_TESTSTR, 2) == "Baz")
        # Go up one category
        self.assertTrue(tree_select.go_up_one_category(TREE_MENU_TESTSTR, 4) == 2)
        # Option list to menu options
        test_optlist = tree_select.parse_opts(TREE_MENU_TESTSTR, category_index=2)
        optlist_to_menu_expected_result = [
            {"goto": ["menunode_treeselect", {"newindex": 3}], "key": "Baz 1"},
            {"goto": ["menunode_treeselect", {"newindex": 4}], "key": "Baz 2"},
            {
                "goto": ["menunode_treeselect", {"newindex": 1}],
                "key": ["<< Go Back", "go back", "back"],
                "desc": "Return to the previous menu.",
            },
        ]
        self.assertTrue(
            tree_select.optlist_to_menuoptions(TREE_MENU_TESTSTR, test_optlist, 2, True, True)
            == optlist_to_menu_expected_result
        )


FIELD_TEST_TEMPLATE = [
    {"fieldname": "TextTest", "fieldtype": "text"},
    {"fieldname": "NumberTest", "fieldtype": "number", "blankmsg": "Number here!"},
    {"fieldname": "DefaultText", "fieldtype": "text", "default": "Test"},
    {"fieldname": "DefaultNum", "fieldtype": "number", "default": 3},
]

FIELD_TEST_DATA = {"TextTest": None, "NumberTest": None, "DefaultText": "Test", "DefaultNum": 3}


class TestFieldFillFunc(BaseEvenniaTest):
    def test_field_functions(self):
        self.assertTrue(fieldfill.form_template_to_dict(FIELD_TEST_TEMPLATE) == FIELD_TEST_DATA)
