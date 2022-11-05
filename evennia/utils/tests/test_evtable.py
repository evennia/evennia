"""
Tests for EvTable component.

"""

from evennia.utils import ansi, evtable
from evennia.utils.test_resources import EvenniaTestCase


class TestEvTable(EvenniaTestCase):
    def _validate(self, expected, result):
        """easier debug"""
        expected = ansi.strip_ansi(expected).strip()
        result = ansi.strip_ansi(result).strip()

        err = f"\n{'expected':-^60}\n{expected}\n{'result':-^60}\n{result}\n{'':-^60}"
        self.assertEqual(expected, result, err)

    def test_base(self):
        """
        Create plain table.

        """
        table = evtable.EvTable(
            "|yHeading1|n",
            "|gHeading2|n",
            "|rHeading3|n",
            table=[[1, 2, 3], [4, 5, 6], [7, 8, 9]],
            border="cells",
            align="l",
        )

        expected = """
+----------+----------+----------+
| Heading1 | Heading2 | Heading3 |
+~~~~~~~~~~+~~~~~~~~~~+~~~~~~~~~~+
| 1        | 4        | 7        |
+----------+----------+----------+
| 2        | 5        | 8        |
+----------+----------+----------+
| 3        | 6        | 9        |
+----------+----------+----------+
"""

        self._validate(expected, str(table))

    def test_table_with_short_header(self):
        """
        Don't provide header3

        """
        table = evtable.EvTable(
            "|yHeading1|n",
            "|gHeading2|n",
            table=[[1, 2, 3], [4, 5, 6], [7, 8, 9]],
            border="cells",
            align="l",
        )
        expected = """
+----------+----------+---+
| Heading1 | Heading2 |   |
+~~~~~~~~~~+~~~~~~~~~~+~~~+
| 1        | 4        | 7 |
+----------+----------+---+
| 2        | 5        | 8 |
+----------+----------+---+
| 3        | 6        | 9 |
+----------+----------+---+
"""

        self._validate(expected, str(table))

    def test_add_column(self):

        table = evtable.EvTable(
            "|yHeading1|n",
            "|gHeading2|n",
            "|rHeading3|n",
            table=[[1, 2, 3], [4, 5, 6], [7, 8, 9]],
            border="cells",
            align="l",
        )
        table.add_column("|rThis is long data|n", "|bThis is even longer data|n")

        expected = """
+----------+----------+----------+--------------------------+
| Heading1 | Heading2 | Heading3 |                          |
+~~~~~~~~~~+~~~~~~~~~~+~~~~~~~~~~+~~~~~~~~~~~~~~~~~~~~~~~~~~+
| 1        | 4        | 7        | This is long data        |
+----------+----------+----------+--------------------------+
| 2        | 5        | 8        | This is even longer data |
+----------+----------+----------+--------------------------+
| 3        | 6        | 9        |                          |
+----------+----------+----------+--------------------------+
"""
        self._validate(expected, str(table))

    def test_add_row(self):
        table = evtable.EvTable(
            "|yHeading1|n",
            "|gHeading2|n",
            "|rHeading3|n",
            table=[[1, 2, 3], [4, 5, 6], [7, 8, 9]],
            border="cells",
            align="l",
        )
        table.add_row("This is a single row")

        expected = """
+----------------------+----------+----------+
| Heading1             | Heading2 | Heading3 |
+~~~~~~~~~~~~~~~~~~~~~~+~~~~~~~~~~+~~~~~~~~~~+
| 1                    | 4        | 7        |
+----------------------+----------+----------+
| 2                    | 5        | 8        |
+----------------------+----------+----------+
| 3                    | 6        | 9        |
+----------------------+----------+----------+
| This is a single row |          |          |
+----------------------+----------+----------+
"""
        self._validate(expected, str(table))

    def test_add_row_and_column(self):

        table = evtable.EvTable(
            "|yHeading1|n",
            "|gHeading2|n",
            "|rHeading3|n",
            table=[[1, 2, 3], [4, 5, 6], [7, 8, 9]],
            border="cells",
            align="l",
        )
        table.add_row("This is a single row")
        table.add_column("|rThis is long data|n", "|bThis is even longer data|n")

        expected = """
+----------------------+----------+----------+--------------------------+
| Heading1             | Heading2 | Heading3 |                          |
+~~~~~~~~~~~~~~~~~~~~~~+~~~~~~~~~~+~~~~~~~~~~+~~~~~~~~~~~~~~~~~~~~~~~~~~+
| 1                    | 4        | 7        | This is long data        |
+----------------------+----------+----------+--------------------------+
| 2                    | 5        | 8        | This is even longer data |
+----------------------+----------+----------+--------------------------+
| 3                    | 6        | 9        |                          |
+----------------------+----------+----------+--------------------------+
| This is a single row |          |          |                          |
+----------------------+----------+----------+--------------------------+
"""
        self._validate(expected, str(table))

    def test_reformat(self):

        table = evtable.EvTable(
            "|yHeading1|n",
            "|gHeading2|n",
            "|rHeading3|n",
            table=[[1, 2, 3], [4, 5, 6], [7, 8, 9]],
            border="cells",
            align="l",
        )

        # width
        table.reformat(width=50)

        expected = """
+----------------+---------------+---------------+
| Heading1       | Heading2      | Heading3      |
+~~~~~~~~~~~~~~~~+~~~~~~~~~~~~~~~+~~~~~~~~~~~~~~~+
| 1              | 4             | 7             |
+----------------+---------------+---------------+
| 2              | 5             | 8             |
+----------------+---------------+---------------+
| 3              | 6             | 9             |
+----------------+---------------+---------------+
        """
        self._validate(expected, str(table))

        # right-aligned

        table.reformat_column(2, width=30, align="r")

        expected = """
+---------+--------+-----------------------------+
| Heading | Headin |                    Heading3 |
| 1       | g2     |                             |
+~~~~~~~~~+~~~~~~~~+~~~~~~~~~~~~~~~~~~~~~~~~~~~~~+
| 1       | 4      |                           7 |
+---------+--------+-----------------------------+
| 2       | 5      |                           8 |
+---------+--------+-----------------------------+
| 3       | 6      |                           9 |
+---------+--------+-----------------------------+
        """
        self._validate(expected, str(table))

    def test_multiple_rows(self):
        """
        adding a lot of rows with `.add_row`.
        """
        table = evtable.EvTable("|yHeading1|n", "|B|[GHeading2|n", "Heading3")
        nlines = 12

        for i in range(nlines):
            table.add_row(
                f"This is col 0, row {i}",
                f"|gThis is col 1, row |w{i}|n|g|n",
                f"This is col 2, row {i}",
            )

        expected = [
            "+-----------------------+-----------------------+-----------------------+",
            "| Heading1              | Heading2              | Heading3              |",
            "+~~~~~~~~~~~~~~~~~~~~~~~+~~~~~~~~~~~~~~~~~~~~~~~+~~~~~~~~~~~~~~~~~~~~~~~+",
        ]
        for i in range(nlines):
            expected.append(
                f"| This is col 0, row {i:<2} | This is col 1, row {i:<2} | This is col 2, row"
                f" {i:<2} |"
            )
        expected.append(expected[0])
        expected = "\n".join(expected)

        self._validate(expected, str(table))
