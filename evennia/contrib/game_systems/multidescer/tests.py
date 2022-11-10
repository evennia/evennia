"""
Test multidescer contrib.

"""

from evennia.commands.default.tests import BaseEvenniaCommandTest

from . import multidescer


class TestMultidescer(BaseEvenniaCommandTest):
    def test_cmdmultidesc(self):
        self.call(multidescer.CmdMultiDesc(), "/list", "Stored descs:\ncaller:")
        self.call(
            multidescer.CmdMultiDesc(), "test = Desc 1", "Stored description 'test': \"Desc 1\""
        )
        self.call(
            multidescer.CmdMultiDesc(), "test2 = Desc 2", "Stored description 'test2': \"Desc 2\""
        )
        self.call(
            multidescer.CmdMultiDesc(), "/swap test-test2", "Swapped descs 'test' and 'test2'."
        )
        self.call(
            multidescer.CmdMultiDesc(),
            "test3 = Desc 3init",
            "Stored description 'test3': \"Desc 3init\"",
        )
        self.call(
            multidescer.CmdMultiDesc(),
            "/list",
            "Stored descs:\ntest3: Desc 3init\ntest: Desc 1\ntest2: Desc 2\ncaller:",
        )
        self.call(
            multidescer.CmdMultiDesc(), "test3 = Desc 3", "Stored description 'test3': \"Desc 3\""
        )
        self.call(
            multidescer.CmdMultiDesc(),
            "/set test1 + test2 + + test3",
            "test1 Desc 2 Desc 3\n\n" "The above was set as the current description.",
        )
        self.assertEqual(self.char1.db.desc, "test1 Desc 2 Desc 3")
