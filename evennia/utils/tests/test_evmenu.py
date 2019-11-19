"""
Unit tests for the EvMenu system

This sets up a testing parent for testing EvMenu trees. It is configured by subclassing the
`TestEvMenu` class from this module and setting the class variables to point to the menu that should
be tested and how it should be called.

Without adding any further test methods, the tester will process all nodes of the menu, depth first,
by stepping through all options for every node. Optionally, it can check that all nodes are visited.
It will create a hierarchical list of node names that describes the tree structure. This can then be
compared against a template to make sure the menu structure is sound. Easiest way to use this is to
run the test once to see how the structure looks.

The system also allows for testing the returns of each node as part of the parsing.

To help debug the menu, turn on `debug_output`, which will print the traversal process in detail.

"""

import copy
from django.test import TestCase
from evennia.utils import evmenu
from evennia.utils import ansi
from mock import MagicMock


class TestEvMenu(TestCase):
    "Run the EvMenu testing."
    menutree = {}  # can also be the path to the menu tree
    startnode = "start"
    cmdset_mergetype = "Replace"
    cmdset_priority = 1
    auto_quit = True
    auto_look = True
    auto_help = True
    cmd_on_exit = "look"
    persistent = False
    startnode_input = ""
    kwargs = {}

    # if all nodes must be visited for the test to pass. This is not on
    # by default since there may be exec-nodes that are made to not be
    # visited.
    expect_all_nodes = False

    # this is compared against the full tree structure generated
    expected_tree = []
    # this allows for verifying that a given node returns a given text. The
    # text is compared with .startswith, so the entire text need not be matched.
    expected_node_texts = {}
    # just check the number of options from each node
    expected_node_options_count = {}
    # check the actual options
    expected_node_options = {}

    # set this to print the traversal as it happens (debugging)
    debug_output = False

    def _debug_output(self, indent, msg):
        if self.debug_output:
            print(" " * indent + ansi.strip_ansi(msg))

    def _test_menutree(self, menu):
        """
        This is a automatic tester of the menu tree by recursively progressing through the
        structure.
        """

        def _depth_first(menu, tree, visited, indent):

            # we are in a given node here
            nodename = menu.nodename
            options = menu.test_options
            if isinstance(options, dict):
                options = (options,)

            # run validation tests for this node
            compare_text = self.expected_node_texts.get(nodename, None)
            if compare_text is not None:
                compare_text = ansi.strip_ansi(compare_text.strip())
                node_text = menu.test_nodetext
                self.assertIsNotNone(
                    bool(node_text),
                    "node: {}: node-text is None, which was not expected.".format(nodename),
                )
                if isinstance(node_text, tuple):
                    node_text, helptext = node_text
                node_text = ansi.strip_ansi(node_text.strip())
                self.assertTrue(
                    node_text.startswith(compare_text),
                    "\nnode \"{}':\nOutput:\n{}\n\nExpected (startswith):\n{}".format(
                        nodename, node_text, compare_text
                    ),
                )
            compare_options_count = self.expected_node_options_count.get(nodename, None)
            if compare_options_count is not None:
                self.assertEqual(
                    len(options),
                    compare_options_count,
                    "Not the right number of options returned from node {}.".format(nodename),
                )
            compare_options = self.expected_node_options.get(nodename, None)
            if compare_options:
                self.assertEqual(
                    options,
                    compare_options,
                    "Options returned from node {} does not match.".format(nodename),
                )

            self._debug_output(indent, "*{}".format(nodename))
            subtree = []

            if not options:
                # an end node
                if nodename not in visited:
                    visited.append(nodename)
                subtree = nodename
            else:
                for inum, optdict in enumerate(options):

                    key, desc, execute, goto = (
                        optdict.get("key", ""),
                        optdict.get("desc", None),
                        optdict.get("exec", None),
                        optdict.get("goto", None),
                    )

                    # prepare the key to pass to the menu
                    if isinstance(key, (tuple, list)) and len(key) > 1:
                        key = key[0]
                    if key == "_default":
                        key = "test raw input"
                    if not key:
                        key = str(inum + 1)

                    backup_menu = copy.copy(menu)

                    # step the menu
                    menu.parse_input(key)

                    # from here on we are likely in a different node
                    nodename = menu.nodename

                    if menu.close_menu.called:
                        # this was an end node
                        self._debug_output(indent, "    .. menu exited! Back to previous node.")
                        menu = backup_menu
                        menu.close_menu = MagicMock()
                        visited.append(nodename)
                        subtree.append(nodename)
                    elif nodename not in visited:
                        visited.append(nodename)
                        subtree.append(nodename)
                        _depth_first(menu, subtree, visited, indent + 2)
                        # self._debug_output(indent, "    -> arrived at {}".format(nodename))
                    else:
                        subtree.append(nodename)
                        # self._debug_output( indent, "    -> arrived at {} (circular call)".format(nodename))
                    self._debug_output(indent, "-- {} ({}) -> {}".format(key, desc, goto))

            if subtree:
                tree.append(subtree)

        # the start node has already fired at this point
        visited_nodes = [menu.nodename]
        traversal_tree = [menu.nodename]
        _depth_first(menu, traversal_tree, visited_nodes, 1)

        if self.expect_all_nodes:
            self.assertGreaterEqual(len(menu._menutree), len(visited_nodes))
        self.assertEqual(traversal_tree, self.expected_tree)

    def setUp(self):
        self.menu = None
        if self.menutree:
            self.caller = MagicMock()
            self.caller.key = "Test"
            self.caller2 = MagicMock()
            self.caller2.key = "Test"
            self.caller.msg = MagicMock()
            self.caller2.msg = MagicMock()
            self.session = MagicMock()
            self.session.protocol_flags = {}
            self.session2 = MagicMock()
            self.session2.protocol_flags = {}
            self.caller.session = self.session
            self.caller2.session = self.session2

            self.menu = evmenu.EvMenu(
                self.caller,
                self.menutree,
                startnode=self.startnode,
                cmdset_mergetype=self.cmdset_mergetype,
                cmdset_priority=self.cmdset_priority,
                auto_quit=self.auto_quit,
                auto_look=self.auto_look,
                auto_help=self.auto_help,
                cmd_on_exit=self.cmd_on_exit,
                persistent=False,
                startnode_input=self.startnode_input,
                session=self.session,
                **self.kwargs,
            )
            # persistent version
            self.pmenu = evmenu.EvMenu(
                self.caller2,
                self.menutree,
                startnode=self.startnode,
                cmdset_mergetype=self.cmdset_mergetype,
                cmdset_priority=self.cmdset_priority,
                auto_quit=self.auto_quit,
                auto_look=self.auto_look,
                auto_help=self.auto_help,
                cmd_on_exit=self.cmd_on_exit,
                persistent=True,
                startnode_input=self.startnode_input,
                session=self.session2,
                **self.kwargs,
            )

            self.menu.close_menu = MagicMock()
            self.pmenu.close_menu = MagicMock()

    def test_menu_structure(self):
        if self.menu:
            self._test_menutree(self.menu)
            self._test_menutree(self.pmenu)


class TestEvMenuExample(TestEvMenu):

    menutree = "evennia.utils.evmenu"
    startnode = "test_start_node"
    kwargs = {"testval": "val", "testval2": "val2"}
    debug_output = False

    expected_node_texts = {"test_view_node": "Your name is"}

    expected_tree = [
        "test_start_node",
        [
            "test_set_node",
            ["test_start_node"],
            "test_look_node",
            ["test_start_node"],
            "test_view_node",
            ["test_start_node"],
            "test_dynamic_node",
            [
                "test_dynamic_node",
                "test_dynamic_node",
                "test_dynamic_node",
                "test_dynamic_node",
                "test_start_node",
            ],
            "test_end_node",
            "test_displayinput_node",
            ["test_start_node"],
        ],
    ]

    def test_kwargsave(self):
        self.assertTrue(hasattr(self.menu, "testval"))
        self.assertTrue(hasattr(self.menu, "testval2"))
