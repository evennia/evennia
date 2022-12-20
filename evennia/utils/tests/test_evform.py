"""
Unit tests for the EvForm text form generator

"""
from unittest import skip

from django.test import TestCase

from evennia.utils import ansi, evform, evtable


class TestEvForm(TestCase):

    maxDiff = None

    def _parse_form(self):
        "test evform. This is used by the unittest system."
        form = evform.EvForm("evennia.utils.tests.data.evform_example")

        # add data to each tagged form cell
        form.map(
            cells={
                "AA": "|gTom the Bouncer",
                2: "|yGriatch",
                3: "A sturdy fellow",
                4: 12,
                5: 10,
                6: 5,
                7: 18,
                8: 10,
                9: 3,
                "F": "rev 1",
            }
        )
        # create the EvTables
        tableA = evtable.EvTable(
            "HP", "MV", "MP", table=[["**"], ["*****"], ["***"]], border="incols"
        )
        tableB = evtable.EvTable(
            "Skill",
            "Value",
            "Exp",
            table=[
                ["Shooting", "Herbalism", "Smithing"],
                [12, 14, 9],
                ["550/1200", "990/1400", "205/900"],
            ],
            border="incols",
        )
        # add the tables to the proper ids in the form
        form.map(tables={"A": tableA, "B": tableB})
        return str(form)

    def _simple_form(self, form, literals=None):
        cellsdict = {1: "Apple", 2: "Banana", 3: "Citrus", 4: "Durian"}
        formdict = {"FORMCHAR": "x", "TABLECHAR": "c", "FORM": form}
        form = evform.EvForm(formdict, literals=literals)
        form.map(cells=cellsdict)
        form = ansi.strip_ansi(str(form))
        # this is necessary since editors/black tend to strip lines spaces
        # from the end of lines for the comparison strings.
        form = "\n".join(line.rstrip() for line in form.split("\n"))
        return form

    def test_form_consistency(self):
        """
        Make sure form looks the same every time.

        """
        form1 = self._parse_form()
        form2 = self._parse_form()

        self.assertEqual(form1, form2)

    def test_form_output(self):
        """
        Check the result of the form. We strip ansi for readability.

        """

        form = self._parse_form()
        form_noansi = ansi.strip_ansi(form)
        # we must strip extra space at the end of output simply
        # because editors tend to strip it when creating
        # the comparison string ...
        form_noansi = "\n".join(line.rstrip() for line in form_noansi.split("\n"))

        self.assertNotEqual(form, form_noansi)
        expected = """
.------------------------------------------------.
|                                                |
|  Name: Tom the        Account: Griatch         |
|        Bouncer                                 |
|                                                |
 >----------------------------------------------<
|                                                |
| Desc:  A sturdy       STR: 12     DEX: 10      |
|        fellow         INT: 5      STA: 18      |
|                       LUC: 10     MAG: 3       |
|                                                |
 >----------.-----------------------------------<
|           |                                    |
| HP|MV |MP | Skill      |Value     |Exp         |
| ~~+~~~+~~ | ~~~~~~~~~~~+~~~~~~~~~~+~~~~~~~~~~~ |
| **|***|** | Shooting   |12        |550/1200    |
|   |** |*  | Herbalism  |14        |990/1400    |
|   |   |   | Smithing   |9         |205/900     |
|           |                                    |
 -----------`-------------------------------------
 Footer: rev 1
 info
""".lstrip()
        self.assertEqual(expected, form_noansi)

    def test_ansi_escape(self):
        # note that in a msg() call, the result would be the  correct |-----,
        # in a print, ansi only gets called once, so ||----- is the result
        self.assertEqual(str(evform.EvForm({"FORM": "\n||-----"})), "||-----")

    def test_stacked_form(self):
        """
        Test simple stacked form.

        """
        form = """
xxxx1xxxx
xxxx2xxxx
xxxx3xxxx
xxxx4xxxx
        """
        expected = """
Apple
Banana
Citrus
Durian
""".lstrip()
        result = self._simple_form(form)
        self.assertEqual(expected, result)

    def test_side_by_side_two_column(self):
        """
        Side-by-side 2-column form (bug #2205)

        """
        form = """
xxxx1xxxx  xxxx2xxxx
xxxx3xxxx  xxxx4xxxx
        """
        expected = """
Apple      Banana
Citrus     Durian
""".lstrip()
        result = self._simple_form(form)
        self.assertEqual(expected, result)

    def test_side_by_side_three_column(self):
        """
        Side-by-side 3-column form (bug #2205)

        """
        form = """
xxxx1xxxx  xxxx2xxxx  xxxx3xxxx
xxxx4xxxx
        """
        expected = """
Apple      Banana     Citrus
Durian
""".lstrip()
        result = self._simple_form(form)
        self.assertEqual(expected, result)

    def test_literal_replacement(self):
        form = """
xxxx1xxxx  xxxx2xxxx  xxxx3xxxx
xxxx4xxxx  v&
        """
        expected = """
Apple      Banana     Citrus
Durian     v2
""".lstrip()
        result = self._simple_form(form, literals={"v&": "v2"})
        self.assertEqual(expected, result)


# test of issue #2308

_SHEET = """
.----------------------------------------------.
| Sheet                                        |
| xxxxxxxxxxxxxxxxxxxxxxxxxx1xxxxxxxxxxxx      |
>----------------------------------------------<
| Ability scores  |     Skills                 |
| ccccccccccccccc |   ccccccccccccccccccc      |
| cccccc2cccccccc |   ccccccccccccccccccc      |
| ccccccccccccccc |   ccccccccccccccccccc      |
| ccccccccccccccc |   ccccccccccccccccccc      |
| ccccccccccccccc |   ccccccccccccccccccc      |
| ccccccccccccccc |   ccccccccccccccccccc      |
| ccccccccccccccc |   ccccccccccccccccccc      |
| ccccccccccccccc |   ccccccccccccccccccc      |
| ccccccccccccccc |   ccccccccccccccccccc      |
|                 |   ccccccccc3ccccccccc      |
|                 |   ccccccccccccccccccc      |
|                 |   ccccccccccccccccccc      |
|                 |   ccccccccccccccccccc      |
|                 |                            |
+----------------------------------------------+
"""
_EXPECTED = """
.----------------------------------------------.
| Sheet                                        |
| Test text                                    |
>----------------------------------------------<
| Ability scores  |     Skills                 |
| +------+------+ |   +--------+--------+      |
| |Ab    |Sc    | |   |Skill   |Level   |      |
| +~~~~~~+~~~~~~+ |   +~~~~~~~~+~~~~~~~~+      |
| |STR   |10    | |   |Acro    |10      |      |
| |CON   |10    | |   |Anim    |10      |      |
| |DEX   |10    | |   |Arca    |10      |      |
| |      |      | |   |Ath     |10      |      |
| |      |      | |   |Dec     |10      |      |
| +------+------+ |   |His     |10      |      |
|                 |   |        |        |      |
|                 |   |        |        |      |
|                 |   |        |        |      |
|                 |   +--------+--------+      |
|                 |                            |
+----------------------------------------------+
"""


class TestEvFormParallelTables(TestCase):
    """
    Test of issue #2308
    https://github.com/evennia/evennia/issues/2308
    where parallel tables cause strange overlaps
    in output

    """

    def setUp(self):
        self.text1 = "Test text"
        self.table2 = evtable.EvTable("Ab", "Sc", table=[["|ySTR", "|yCON", "|yDEX"], [10, 10, 10]])
        self.table3 = evtable.EvTable(
            "|RSkill",
            "|RLevel",
            table=[
                ["|yAcro", "|yAnim", "|yArca", "|yAth", "|yDec", "|yHis"],
                [10, 10, 10, 10, 10, 10],
            ],
        )
        self.formdict = {"FORM": _SHEET, "FORMCHAR": "x", "TABLECHAR": "c"}

    def test_parallel_tables(self):
        """
        Build form to check for error.
        """
        form = evform.EvForm(self.formdict)
        form.map(
            cells={
                "1": self.text1,
            },
            tables={"2": self.table2, "3": self.table3},
        )
        self.assertEqual(ansi.strip_ansi(str(form).strip()), _EXPECTED.strip())


class TestEvFormErrors(TestCase):
    """
    Tests of EvForm errors found for v1.0-dev

    """

    maxDiff = None

    def _form(self, form, **kwargs):

        formdict = {
            "form": form,
            "formchar": "x",
            "tablechar": "c",
        }
        form = evform.EvForm(formdict, **kwargs)
        # this is necessary since editors/black tend to strip lines spaces
        # from the end of lines for the comparison strings.
        form = ansi.strip_ansi(str(form))
        form = "\n".join(line.rstrip() for line in form.split("\n"))

        return form

    def _validate(self, expected, result):
        """easier debug"""
        err = f"\n{'expected':-^60}\n{expected}\n{'result':-^60}\n{result}\n{'':-^60}"
        self.assertEqual(expected.lstrip(), result.lstrip(), err)

    @skip("Pending rebuild of markup")
    def test_2757(self):
        """
        Testing https://github.com/evennia/evennia/issues/2757

        Using || ansi escaping messes with rectangle width

        This should be delayed until refactor of markup.

        """
        form = """
       xxxxxx
||---|  xx1xxx
       xxxxxx
        """
        cell_mapping = {1: "Monty"}

        expected = """

|---|  Monty

        """
        self._validate(expected, self._form(form, cells=cell_mapping))

    def test_2759(self):
        """
        Testing https://github.com/evennia/evennia/issues/2759

        Leading space in EvCell is stripped

        """
        # testing the underlying problem

        cell = evtable.EvCell(" Hi", align="l")
        self.assertEqual(cell._align(cell.data), [ansi.ANSIString("Hi ")])

        cell = evtable.EvCell("  Hi", align="l")
        self.assertEqual(cell._align(cell.data), [ansi.ANSIString("Hi  ")])

        cell = evtable.EvCell("  Hi", align="a")
        self.assertEqual(cell._align(cell.data), [ansi.ANSIString("  Hi")])

        form = """
.-----------------------.
|       Test Form       |
|                       |
|.xxxxx  .xxxxxxxxxxxxx |
|.xx1xx  .xxxxxx2xxxxxx |
|.xxxxx  .xxxxxxxxxxxxx |
|        .xxxxxxxxxxxxx |
|                       |
 -----------------------
"""

        cell1 = " Hi."
        cell2 = " Single space\n  Double\n Single again"

        cell_mapping = {1: cell1, 2: cell2}

        # default is left-aligned cells
        expected = """
.-----------------------.
|       Test Form       |
|                       |
|.Hi.    .Single space  |
|.       .Double        |
|.       .Single again  |
|        .              |
|                       |
 -----------------------
"""
        self._validate(expected, self._form(form, cells=cell_mapping))

        # test with absolute alignment (pass cells directly)
        cell_mapping = {
            1: evtable.EvCell(cell1, align="a", valign="t"),
            2: evtable.EvCell(cell2, align="a", valign="t"),
        }

        expected = """
.-----------------------.
|       Test Form       |
|                       |
|. Hi.   . Single space |
|.       .  Double      |
|.       . Single again |
|        .              |
|                       |
 -----------------------
"""
        self._validate(expected, self._form(form, cells=cell_mapping))

    @skip("Awaiting rework of markup")
    def test_2763(self):
        """
        Testing https://github.com/evennia/evennia/issues/2763

        Duplication of ANSI sequences in evform

        TODO: In the future, this test should work, using |n. Today, EvTable
        replaces with raw ANSI sequences already before getting to EvForm.
        """

        formdict = {"form": "|R A |n _ x1xx"}
        cell_mapping = {1: "test"}
        expected = "|R A |n _ |ntest|n"
        form = evform.EvForm(formdict, cells=cell_mapping)
        self._validate(expected, str(form))
