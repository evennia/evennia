# coding=utf-8
"""
Evform - a way to create advanced ascii forms


This is intended for creating advanced ascii game forms, such as a
large pretty character sheet or info document.

The system works on the basis of a readin template that is given in a
separate python file imported into the handler. This file contains
some optional settings and a string mapping out the form. The template
has markers in it to denounce fields to fill. The markers map the
absolute size of the field and will be filled with an evtable.Cell
object when displaying the form.

Example of input file testform.py:


CELLCHAR = "x"
TABLECHAR = "c"
FORM = '''
 .-------------------------------------.
/                                       \
| Name: xxx1xxxx   Player: xxxxx2xxxxx  |
|                                       |
>~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~<
| Desc: xxxxxxxxxxx   Str:x4x  Dex:x5x  |
|       xxxxx3xxxxx   Int:x6x  Sta:x7x  |
|       xxxxxxxxxxx   Luc:x8x  Mag:x9x  |
|                                       |
>~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~<
|                                       |
| Skills:                               |
| ccccccccccccccccccccccccccccccccccccc |
| ccccccccccccccccccccccccccccccccccccc |
| ccccccccccccccccccccccccccccccccccccc |
|                                       |
`--------------------------------------´
'''

The first line of the FORM string is ignored.

Use as follows:

    MudForm("path/to/testform.py")


By marking out rectangles, this area gets reserved for the Cell.
Embedded inside each area must be a one-character identifier to tag
the area (so the smallest form size is 3 characters including the
marker). This marker is any character except the designated formchar
("x" in this case). Rectangles can have any size, but must be
separated from each other by at least one other character's width.

Parsing this file will result in a CharMap object. This is
primed with a dictionary of {<tag>:function} where the function
is responsible for producing a string for each form location. The
Cell in each location will enforce the size given by the template
and will crop too-long text.

"""

import re
import copy
from src.utils.mudtable import Cell, MudTable
from src.utils.utils import all_from_module

# non-valid form-identifying characters (which can thus be
# used as separators between forms without being detected
# as an identifier). These should be listed in regex form.

INVALID_FORMCHARS = r"\s\-\|\*\#\<\>\~\^"


class MudForm(object):
    """
    This object is instantiated with a text file and parses
    it for rectangular form fields. It can then be fed a
    mapping so as to populate the fields with fixed-width
    Cell objects for displaying
    """
    def __init__(self, filename, cells=None, tables=None, **kwargs):
        """
        Read the template file and parse it for formfields

        kwargs:
            <identifier> - text for fill into form
        """
        self.filename = filename

        self.cells_mapping =  dict((str(key), value) for key, value in cells.items()) if cells  else {}
        self.tables_mapping = dict((str(key), value) for key, value in tables.items()) if tables else {}

        self.cellchar = "x"
        self.tablechar = "c"

        self.raw_form = []
        self.form = []

        # clean kwargs (these cannot be overridden)
        kwargs.pop("enforce_size", None)
        kwargs.pop("width", None)
        kwargs.pop("height", None)
        # table/cell options
        self.options = kwargs

        self.reload()

    def _parse_rectangles(self, cellchar, tablechar, form, **kwargs):
        """
        Parse a form for rectangular formfields identified by
        formchar enclosing an identifier.
        """

        # update options given at creation with new input - this
        # allows e.g. self.map() to add custom settings for individual
        # cells/tables
        custom_options = copy.copy(self.options)
        custom_options.update(kwargs)

        nform = len(form)

        mapping = {}
        cell_coords = {}
        table_coords = {}

        # Locate the identifier tags and the horizontal end coords for all forms
        re_cellchar =  re.compile(r"%s+([^%s%s])%s+" % (cellchar, INVALID_FORMCHARS, cellchar, cellchar))
        re_tablechar = re.compile(r"%s+([^%s%s|])%s+" % (tablechar, INVALID_FORMCHARS, tablechar, tablechar))
        for iy, line in enumerate(form):
            # find cells
            ix0 = 0
            while True:
                match = re_cellchar.search(line, ix0)
                if match:
                    # get the width of the rectangle directly from the match
                    cell_coords[match.group(1)] = [iy, match.start(), match.end()]
                    ix0 = match.end()
                else:
                    break
            # find tables
            ix0 = 0
            while True:
                match = re_tablechar.search(line, ix0)
                if match:
                    # get the width of the rectangle directly from the match
                    print "table.match:", match.group(), match.group(1)
                    table_coords[match.group(1)] = [iy, match.start(), match.end()]
                    ix0 = match.end()
                else:
                    break
        print "table_coords:", table_coords

        # get rectangles and assign Cells
        for key, (iy, leftix, rightix) in cell_coords.items():

            # scan up to find top of rectangle
            dy_up = 0
            if iy > 0:
                for i in range(1,iy):
                    #print "dy_up:", [form[iy-i][ix] for ix in range(leftix, rightix)]
                    if all(form[iy-i][ix] == cellchar for ix in range(leftix, rightix)):
                        dy_up += 1
                    else:
                        break
            # find bottom edge of rectangle
            dy_down = 0
            if iy < nform-1:
                for i in range(1,nform-iy-1):
                    #print "dy_down:", [form[iy+i][ix]for ix in range(leftix, rightix)]
                    if all(form[iy+i][ix] == cellchar for ix in range(leftix, rightix)):
                        dy_down += 1
                    else:
                        break

            #  we have our rectangle. Calculate size of Cell.
            iyup = iy - dy_up
            iydown = iy + dy_down
            width = rightix - leftix
            height = abs(iyup - iydown) + 1

            # we have all the coordinates we need. Create Cell.
            data = self.cells_mapping.get(key, "")
            #if key == "1":
            #print "creating cell '%s' (%s):" % (key, data)
            #print "iy=%s, iyup=%s, iydown=%s, leftix=%s, rightix=%s, width=%s, height=%s" % (iy, iyup, iydown, leftix, rightix, width, height)

            options = { "pad_left":0, "pad_right":0, "pad_top":0, "pad_bottom":0, "align":"l", "valign":"t", "enforce_size":True}
            options.update(custom_options)
            #if key=="4":
            #print "options:", options

            mapping[key] = (iyup, leftix, width, height, Cell(data, width=width, height=height,**options))

        # get rectangles and assign Tables
        for key, (iy, leftix, rightix) in table_coords.items():

            # scan up to find top of rectangle
            dy_up = 0
            if iy > 0:
                for i in range(1,iy):
                    #print "dy_up:", [form[iy-i][ix] for ix in range(leftix, rightix)]
                    if all(form[iy-i][ix] == tablechar for ix in range(leftix, rightix)):
                        dy_up += 1
                    else:
                        break
            # find bottom edge of rectangle
            dy_down = 0
            if iy < nform-1:
                for i in range(1,nform-iy-1):
                    #print "dy_down:", [form[iy+i][ix]for ix in range(leftix, rightix)]
                    if all(form[iy+i][ix] == tablechar for ix in range(leftix, rightix)):
                        dy_down += 1
                    else:
                        break

            #  we have our rectangle. Calculate size of Table.
            iyup = iy - dy_up
            iydown = iy + dy_down
            width = rightix - leftix
            height = abs(iyup - iydown) + 1

            # we have all the coordinates we need. Create Table.
            table = self.tables_mapping.get(key, None)
            #if key == "1":
            print "creating table '%s' (%s):" % (key, data)
            print "iy=%s, iyup=%s, iydown=%s, leftix=%s, rightix=%s, width=%s, height=%s" % (iy, iyup, iydown, leftix, rightix, width, height)

            options = { "pad_left":0, "pad_right":0, "pad_top":0, "pad_bottom":0,
                        "align":"l", "valign":"t", "enforce_size":True}
            options.update(custom_options)
            #if key=="4":
            print "options:", options

            if table:
                table.reformat(width=width, height=height, **options)
            else:
                table = MudTable(width=width, height=height, **options)
            mapping[key] = (iyup, leftix, width, height, table)

        return mapping

    def _populate_form(self, raw_form, mapping):
        """
        Insert cell contents into form at given locations
        """
        form = copy.copy(raw_form)
        for key, (iy0, ix0, width, height, cell_or_table) in mapping.items():
            # rect is a list of <height> lines, each <width> wide
            rect = cell_or_table.get()
            for il, rectline in enumerate(rect):
                formline = form[iy0+il]
                # insert new content, replacing old
                form[iy0+il] = formline = formline[:ix0] + rectline + formline[ix0+width:]
        return form

    def map(self, cells=None, tables=None, **kwargs):
        """
        Add mapping for form.

        keywords:
            <identifier> - text
        """
        # clean kwargs (these cannot be overridden)
        kwargs.pop("enforce_size", None)
        kwargs.pop("width", None)
        kwargs.pop("height", None)

        new_cells =  dict((str(key), value) for key, value in cells.items()) if cells  else {}
        new_tables = dict((str(key), value) for key, value in tables.items()) if tables else {}

        self.cells_mapping.update(new_cells)
        self.tables_mapping.update(new_tables)
        self.reload()

    def reload(self, filename=None, **kwargs):
        """
        Creates the form from a stored file name
        """
        # clean kwargs (these cannot be overridden)
        kwargs.pop("enforce_size", None)
        kwargs.pop("width", None)
        kwargs.pop("height", None)

        if filename:
            self.filename = filename
        filename = self.filename

        datadict = all_from_module(filename)

        cellchar = datadict.get("CELLCHAR", "x")
        self.cellchar = cellchar[0] if len(cellchar) > 1 else cellchar
        tablechar = datadict.get("TABLECHAR", "c")
        self.tablechar = tablechar[0] if len(tablechar) > 1 else tablechar

        # split into a list of list of lines. Form can be indexed with form[iy][ix]
        self.raw_form = datadict.get("FORM", "").split("\n")
        # strip first line
        self.raw_form = self.raw_form[1:] if self.raw_form else self.raw_form

        self.options.update(kwargs)

        # parse and replace
        self.mapping = self._parse_rectangles(self.cellchar, self.tablechar, self.raw_form, **kwargs)
        self.form = self._populate_form(self.raw_form, self.mapping)

    def __str__(self):
        "Prints the form"
        return "\n".join(self.form)


