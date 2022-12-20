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
        Adding a lot of rows with `.add_row`.

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

    def test_direct_evcolumn_adds(self):
        """
        Testing https://github.com/evennia/evennia/issues/2762

        Extra spaces getting added to cell content

        Also testing out adding EvColumns directly to the table kwarg.

        """
        # direct table add
        table = evtable.EvTable(table=[["another"]], fill_char=".", pad_char="#", width=8)

        expected = """
+------+
|#anot#|
|#her.#|
+------+
        """
        self._validate(expected, str(table))

        # add with .add_column
        table = evtable.EvTable(fill_char=".", pad_char="#")
        table.add_column("another", width=8)

        self._validate(expected, str(table))

        # add by passing a column to constructor directly

        colB = evtable.EvColumn("another", width=8)

        table = evtable.EvTable(table=[colB], fill_char=".", pad_char="#")

        self._validate(expected, str(table))

        # more complex table

        colA = evtable.EvColumn("this", "is", "a", "column")  # no width
        colB = evtable.EvColumn("and", "another", "one", "here", width=8)

        table = evtable.EvTable(table=[colA, colB], fill_char=".", pad_char="#")

        expected = """
+--------+-------+
|#this..#|#and..#|
|#is....#|#anoth#|
|#......#|#er...#|
|#a.....#|#one..#|
|#column#|#here.#|
+--------+-------+
        """

        self._validate(expected, str(table))

    def test_width_enforcement(self):
        """
        Testing https://github.com/evennia/evennia/issues/2761

        EvTable enforces width kwarg, expanding the wrong column

        """
        # simple crop
        table = evtable.EvTable(table=[["column"]], width=7, enforce_size=True)
        expected = """
+-----+
| col |
+-----+
        """

        # more advanced table with crop
        self._validate(expected, str(table))

        colA = evtable.EvColumn("it", "is", "a", "column", width=6, enforce_size=True)
        colB = evtable.EvColumn("and", "another", "column", "here")
        table = evtable.EvTable(table=[colA, colB], width=40)

        expected = """
+----+---------------------------------+
| it | and                             |
| is | another                         |
| a  | column                          |
| co | here                            |
+----+---------------------------------+
        """

        self._validate(expected, str(table))

    def test_styling_overrides(self):
        """
        Testing https://github.com/evennia/evennia/issues/2760

        Not being able to override table settings.

        """
        column = evtable.EvColumn("this", "is", "a", "column", fill_char=".")
        table = evtable.EvTable(table=[column])

        expected = """
+--------+
| this.. |
| is.... |
| a..... |
| column |
+--------+
        """

        self._validate(expected, str(table))

    def test_color_transfer(self):
        """
        Testing https://github.com/evennia/evennia/issues/2986

        EvTable swallowing color tags.

        """
        from evennia.utils.ansi import ANSI_CYAN, ANSI_RED

        row1 = "|cAn entire colored row|n"
        row2 = "A single |rred|n word"

        table = evtable.EvTable(table=[[row1, row2]])

        self.assertIn(ANSI_RED, str(table))
        self.assertIn(ANSI_CYAN, str(table))
