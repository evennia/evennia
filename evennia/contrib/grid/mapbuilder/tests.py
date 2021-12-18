"""
Test map builder.

"""

from evennia.commands.default.tests import CommandTest
from . import mapbuilder


class TestMapBuilder(CommandTest):
    def test_cmdmapbuilder(self):
        self.call(
            mapbuilder.CmdMapBuilder(),
            "evennia.contrib.mapbuilder.EXAMPLE1_MAP evennia.contrib.mapbuilder.EXAMPLE1_LEGEND",
            """Creating Map...|≈≈≈≈≈
≈♣n♣≈
≈∩▲∩≈
≈♠n♠≈
≈≈≈≈≈
|Creating Landmass...|""",
        )
        self.call(
            mapbuilder.CmdMapBuilder(),
            "evennia.contrib.mapbuilder.EXAMPLE2_MAP evennia.contrib.mapbuilder.EXAMPLE2_LEGEND",
            """Creating Map...|≈ ≈ ≈ ≈ ≈

≈ ♣-♣-♣ ≈
    ≈ ♣ ♣ ♣ ≈
  ≈ ♣-♣-♣ ≈

≈ ≈ ≈ ≈ ≈
|Creating Landmass...|""",
        )
