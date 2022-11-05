# coding=utf-8
"""
EvForm - a way to create advanced ASCII forms

This is intended for creating advanced ASCII game forms, such as a
large pretty character sheet or info document.

The system works on the basis of a readin template that is given in a
separate Python file imported into the handler. This file contains
some optional settings and a string mapping out the form. The template
has markers in it to denounce fields to fill. The markers map the
absolute size of the field and will be filled with an `evtable.EvCell`
object when displaying the form.

Example of input file `testform.py`:

```python
FORMCHAR = "x"
TABLECHAR = "c"

FORM = '''
.------------------------------------------------.
|                                                |
|  Name: xxxxx1xxxxx    Player: xxxxxxx2xxxxxxx  |
|        xxxxxxxxxxx                             |
|                                                |
 >----------------------------------------------<
|                                                |
| Desc:  xxxxxxxxxxx    STR: x4x    DEX: x5x     |
|        xxxxx3xxxxx    INT: x6x    STA: x7x     |
|        xxxxxxxxxxx    LUC: x8x    MAG: x9x     |
|                                                |
 >----------------------------------------------<
|          |                                     |
| cccccccc | ccccccccccccccccccccccccccccccccccc |
| cccccccc | ccccccccccccccccccccccccccccccccccc |
| cccAcccc | ccccccccccccccccccccccccccccccccccc |
| cccccccc | ccccccccccccccccccccccccccccccccccc |
| cccccccc | cccccccccccccccccBccccccccccccccccc |
|          |                                     |
-------------------------------------------------
'''
```

The first line of the `FORM` string is ignored. The forms and table
markers must mark out complete, unbroken rectangles, each containing
one embedded single-character identifier (so the smallest element
possible is a 3-character wide form). The identifier can be any
character except for the `FORM_CHAR` and `TABLE_CHAR` and some of the
common ASCII-art elements, like space, `_` `|` `*` etc (see
`INVALID_FORMCHARS` in this module). Form Rectangles can have any size,
but must be separated from each other by at least one other
character's width.


Use as follows:

```python
    from evennia import EvForm, EvTable

    # create a new form from the template
    form = EvForm("path/to/testform.py")

    # EvForm can also take a dictionary instead of a filepath, as long
    # as the dict contains the keys FORMCHAR, TABLECHAR and FORM
    # form = EvForm(form=form_dict)

    # add data to each tagged form cell
    form.map(cells={1: "Tom the Bouncer",
                    2: "Griatch",
                    3: "A sturdy fellow",
                    4: 12,
                    5: 10,
                    6:  5,
                    7: 18,
                    8: 10,
                    9:  3})
    # create the EvTables
    tableA = EvTable("HP","MV","MP",
                               table=[["**"], ["*****"], ["***"]],
                               border="incols")
    tableB = EvTable("Skill", "Value", "Exp",
                               table=[["Shooting", "Herbalism", "Smithing"],
                                      [12,14,9],["550/1200", "990/1400", "205/900"]],
                               border="incols")
    # add the tables to the proper ids in the form
    form.map(tables={"A": tableA,
                     "B": tableB})

    print(form)
```

This produces the following result:

::

    .------------------------------------------------.
    |                                                |
    |  Name: Tom the        Player: Griatch          |
    |        Bouncer                                 |
    |                                                |
     >----------------------------------------------<
    |                                                |
    | Desc:  A sturdy       STR: 12     DEX: 10      |
    |        fellow         INT: 5      STA: 18      |
    |                       LUC: 10     MAG: 3       |
    |                                                |
     >----------------------------------------------<
    |          |                                     |
    | HP|MV|MP | Skill      |Value      |Exp         |
    | ~~+~~+~~ | ~~~~~~~~~~~+~~~~~~~~~~~+~~~~~~~~~~~ |
    | **|**|** | Shooting   |12         |550/1200    |
    |   |**|*  | Herbalism  |14         |990/1400    |
    |   |* |   | Smithing   |9          |205/900     |
    |          |                                     |
     ------------------------------------------------

The marked forms have been replaced with EvCells of text and with
EvTables. The form can be updated by simply re-applying `form.map()`
with the updated data.

When working with the template ASCII file, you can use `form.reload()`
to re-read the template and re-apply all existing mappings.

Each component is restrained to the width and height specified by the
template, so it will resize to fit (or crop text if the area is too
small for it). If you try to fit a table into an area it cannot fit
into (when including its borders and at least one line of text), the
form will raise an error.

----

"""

import copy
import re

from evennia.utils.ansi import ANSIString
from evennia.utils.evtable import EvCell, EvTable
from evennia.utils.utils import all_from_module, is_iter, to_str

# non-valid form-identifying characters (which can thus be
# used as separators between forms without being detected
# as an identifier). These should be listed in regex form.

INVALID_FORMCHARS = r"\s\/\|\\\*\_\-\#\<\>\~\^\:\;\.\,"
# if there is an ansi-escape (||) we have to replace this with ||| to make sure
# to properly escape down the line
_ANSI_ESCAPE = re.compile(r"\|\|")


class EvForm:
    """
    This object is instantiated with a text file and parses
    it for rectangular form fields. It can then be fed a
    mapping so as to populate the fields with fixed-width
    EvCell or Tables.

    """

    # cell option defaults
    cell_options = {
        "pad_left": 0,
        "pad_right": 0,
        "pad_top": 0,
        "pad_bottom": 0,
        "align": "l",
        "valign": "t",
        "enforce_size": True,
    }

    # table option defaults
    table_options = {
        "pad_left": 0,
        "pad_right": 0,
        "pad_top": 0,
        "pad_bottom": 0,
        "align": "l",
        "valign": "t",
        "enforce_size": True,
    }

    def __init__(self, data=None, cells=None, tables=None, **kwargs):
        """
        Initiate the form

        Keyword Args:
            data (str or dict): Path to template file or a dict with
                "formchar", "tablechar" and "form" keys (not case sensitive, so FORM etc
                also works, to stay compatible with the in-file names). While "form/FORM"
                is required, if FORMCHAR/TABLECHAR are not given, they will default to
                'x' and 'c' respectively.
            cells (dict): A dictionary mapping  `{id: text}`
            tables (dict): A dictionary mapping  `{id: EvTable}`.

        Notes:
            Other kwargs are fed as options to the EvCells and EvTables
            (see `evtable.EvCell` and `evtable.EvTable` for more info).

        """
        self.indata = data  # storing here so we can reload later in case of a filename
        self.options = self._parse_inkwargs(**kwargs)

        self.cells_mapping = (
            dict((to_str(key), value) for key, value in cells.items()) if cells else {}
        )
        self.tables_mapping = (
            dict((to_str(key), value) for key, value in tables.items()) if tables else {}
        )

        # work arrays
        self.mapping = {}
        self.raw_form = []
        self.form = []

        # will parse and build the form
        self.reload()

    def _parse_indata(self):
        """
        Parse and validate the `self.indata` property. We do this in order to be able to
        re-load the evform module if indata is a filename and catch any on-file changes.

        Returns:
            dict: The data dict parsed/generated from the in-data.

        """
        data = self.indata

        default_formchar = "x"
        default_tablechar = "c"

        if isinstance(data, str):
            # a module path - read all variables from it
            data = all_from_module(data)

        if isinstance(data, dict):
            data = {
                "form": str(data.get("form", data.get("FORM", None))),
                "formchar": str(data.get("formchar", data.get("FORMCHAR", default_formchar))),
                "tablechar": str(data.get("tablechar", data.get("TABLECHAR", default_tablechar))),
            }
        else:
            raise RuntimeError(f"EvForm invalid input: {data}.")

        if not data or data["form"] is None:
            raise RuntimeError("Evform data must specify a valid 'form' or 'FORM'.")

        # handle empty or multi-character form/tablechars (not supported)
        data["formchar"] = data["formchar"][0] if data["formchar"] else default_formchar
        data["tablechar"] = data["tablechar"][0] if data["tablechar"] else default_tablechar
        if re.match(rf"[{INVALID_FORMCHARS}]", data["formchar"]):
            raise RuntimeError(f"Invalid formchar: {data['formchar']}")
        if re.match(rf"[{INVALID_FORMCHARS}]", data["tablechar"]):
            raise RuntimeError(f"Invalid tablechar: {data['tablechar']}")

        return data

    def _parse_inkwargs(self, **kwargs):
        """
        Validate incoming kwargs that will be passed on to become cell/table options.

        Keyword Args:
            any: Kwargs to process.

        Returns:
            dict: A validated/cleaned kwarg to use for options.

        """
        if "filename" in kwargs:
            raise DeprecationWarning(
                "EvForm's 'filename' kwarg was renamed to 'data' and can now accept both "
                "a python path and a dict with 'FORMCHAR', 'TABLECHAR' and 'FORM' keys."
            )
        if "form" in kwargs:
            raise DeprecationWarning(
                "EvForms's 'form' kwarg was renamed to 'data' and can now accept both "
                "a ptyhon path and a dict detailing the form."
            )

        # clean cell kwarg options (these cannot be overridden on the cell but must be controlled
        # by the evform itself)
        kwargs.pop("enforce_size", None)
        kwargs.pop("width", None)
        kwargs.pop("height", None)

        return kwargs

    def _parse_to_raw_form(self):
        """
        Forces all lines to be as long as the longest line, filling with whitespace.

        Args:
            lines (list): list of `ANSIString`s

        Returns:
            (list): list of `ANSIString`s of
            same length as the longest input line

        """
        raw_form = EvForm._to_ansi(self.data["form"].split("\n"))
        maxl = max(len(line) for line in raw_form)
        raw_form = [line + " " * (maxl - len(line)) for line in raw_form]
        if raw_form and not raw_form[0].strip():
            # the first line is normally empty, we strip it.
            raw_form = raw_form[1:]
        return raw_form

    @staticmethod
    def _to_ansi(obj, regexable=False):
        "convert anything to ANSIString"

        if isinstance(obj, ANSIString):
            return obj
        elif isinstance(obj, str):
            # since ansi will be parsed twice (here and in the normal ansi send), we have to
            # escape the |-structure twice. TODO: This is tied to the default color-tag syntax
            # which is not ideal for those wanting to replace/extend it ...
            obj = _ANSI_ESCAPE.sub(r"||||", obj)

        if isinstance(obj, dict):
            return dict(
                (key, EvForm._to_ansi(value, regexable=regexable)) for key, value in obj.items()
            )
        # regular _to_ansi (from EvTable)
        elif is_iter(obj):
            return [EvForm._to_ansi(o) for o in obj]
        else:
            return ANSIString(obj, regexable=regexable)

    def _rectangles_to_mapping(self):
        """
        Parse a form for rectangular formfields identified by formchar/tablechar enclosing an
        identifier.

        """
        formchar = self.data["formchar"]
        tablechar = self.data["tablechar"]
        form = self.raw_form

        cell_options = copy.copy(self.cell_options)
        cell_options.update(self.options)

        table_options = copy.copy(self.table_options)
        table_options.update(self.options)

        nform = len(form)

        mapping = {}

        def _get_rectangles(char):
            """Find all identified rectangles marked with given char"""
            rects = []
            coords = {}
            regex = re.compile(rf"{char}+([^{INVALID_FORMCHARS}{char}]+){char}+")

            # find the start/width of rectangles for each line
            for iy, line in enumerate(EvForm._to_ansi(form, regexable=True)):
                ix0 = 0
                while True:
                    match = regex.search(line, ix0)
                    if match:
                        # get the width of the rectangle directly from the match
                        coords[match.group(1)] = [iy, match.start(), match.end()]
                        ix0 = match.end()
                    else:
                        break

            for key, (iy, leftix, rightix) in coords.items():
                # scan up to find top of rectangle
                dy_up = 0
                if iy > 0:
                    for i in range(1, iy):
                        if all(form[iy - i][ix] == char for ix in range(leftix, rightix)):
                            dy_up += 1
                        else:
                            break
                # find bottom edge of rectangle
                dy_down = 0
                if iy < nform - 1:
                    for i in range(1, nform - iy - 1):
                        if all(form[iy + i][ix] == char for ix in range(leftix, rightix)):
                            dy_down += 1
                        else:
                            break

                #  we have our rectangle. Calculate size
                iyup = iy - dy_up
                iydown = iy + dy_down
                width = rightix - leftix
                height = abs(iyup - iydown) + 1

                # store (key, y, x, width, height) of triangle
                rects.append((key, iyup, leftix, width, height))

            return rects

        # Map EvCells into form rectangles
        for (key, y, x, width, height) in _get_rectangles(formchar):

            # get data to populate cell
            data = self.cells_mapping.get(key, "")
            # generate Cell on the fly
            cell = EvCell(data, width=width, height=height, **cell_options)

            mapping[key] = (y, x, width, height, cell)

        # Map EvTables into form rectangles
        for (key, y, x, width, height) in _get_rectangles(tablechar):

            # get EvTable from mapping
            table = self.tables_mapping.get(key, None)

            if table:
                table.reformat(width=width, height=height, **table_options)
            else:
                table = EvTable(width=width, height=height, **table_options)

            mapping[key] = (y, x, width, height, table)

        return mapping

    def _build_form(self):
        """
        Insert cell/table contents into form at given locations to create
        the final result.

        """
        form = copy.copy(self.raw_form)
        mapping = self.mapping

        for key, (y, x, width, height, cell_or_table) in mapping.items():

            # rect is a list of <height> lines, each <width> wide
            rect = cell_or_table.get()
            for il, rectline in enumerate(rect):
                formline = form[y + il]
                # insert new content, replacing old
                form[y + il] = formline[:x] + rectline + formline[x + width :]

        return form

    def reload(self):
        """
        Creates the form from a filename or data structure.

        Args:
            data (str or dict): Can be used to update an existing form using
                the same cells/tables provided on initialization or using `.map()`.

        Notes:
            Kwargs are passed through to Cel creation.

        """
        self.data = self._parse_indata()

        # Create raw form matrix, indexable with (y, x) coords
        self.raw_form = self._parse_to_raw_form()
        # parse and identify all rectangles in the form
        self.mapping = self._rectangles_to_mapping()
        # combine mapping with form template into a final result
        self.form = self._build_form()

    def map(self, cells=None, tables=None, data=None, **kwargs):
        """
        Add mapping for form. This allows for updating an existing
        evform.

        Args:
            cells (dict): A dictionary of {identifier:celltext}. These
                will be appended to the existing mappings.
            tables (dict): A dictionary of {identifier:table}. Will
                be appended to the existing mapping.
            data (str or dict): A path to a evform module or a dict with
                the needed "FORM", "TABLE/FORMCHAR" keys. Will replace
                the originally initialized form.

        Keyword Args:
            These will be appended to the existing cell/table options.

        Notes:
            kwargs will be forwarded to tables/cells. See
            `evtable.EvCell` and `evtable.EvTable` for info.

        """
        if data:
            # storing so ._parse_indata will find it during reload
            self.indata = data

        new_cells = dict((to_str(key), value) for key, value in cells.items()) if cells else {}
        new_tables = dict((to_str(key), value) for key, value in tables.items()) if tables else {}
        self.cells_mapping.update(new_cells)
        self.tables_mapping.update(new_tables)

        self.options.update(self._parse_inkwargs(**kwargs))

        # parse and build the form
        self.reload()

    def __str__(self):
        "Prints the form"
        return str(ANSIString("\n").join([line for line in self.form]))
