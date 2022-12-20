"""
This is an advanced ASCII table creator. It was inspired by Prettytable
(https://code.google.com/p/prettytable/) but shares no code and is considerably
more advanced, supporting auto-balancing of incomplete tables and ANSI colors among
other things.

Example usage:

```python
  from evennia.utils import evtable

  table = evtable.EvTable("Heading1", "Heading2",
                  table=[[1,2,3],[4,5,6],[7,8,9]], border="cells")
  table.add_column("This is long data", "This is even longer data")
  table.add_row("This is a single row")
  print table
```

Result:

::

    +----------------------+----------+---+--------------------------+
    |       Heading1       | Heading2 |   |                          |
    +~~~~~~~~~~~~~~~~~~~~~~+~~~~~~~~~~+~~~+~~~~~~~~~~~~~~~~~~~~~~~~~~+
    |           1          |     4    | 7 |     This is long data    |
    +----------------------+----------+---+--------------------------+
    |           2          |     5    | 8 | This is even longer data |
    +----------------------+----------+---+--------------------------+
    |           3          |     6    | 9 |                          |
    +----------------------+----------+---+--------------------------+
    | This is a single row |          |   |                          |
    +----------------------+----------+---+--------------------------+

As seen, the table will automatically expand with empty cells to make
the table symmetric. Tables can be restricted to a given width:

```python
  table.reformat(width=50, align="l")
```

(We could just have added these keywords to the table creation call)

This yields the following result:

::

    +-----------+------------+-----------+-----------+
    | Heading1  | Heading2   |           |           |
    +~~~~~~~~~~~+~~~~~~~~~~~~+~~~~~~~~~~~+~~~~~~~~~~~+
    | 1         | 4          | 7         | This is   |
    |           |            |           | long data |
    +-----------+------------+-----------+-----------+
    |           |            |           | This is   |
    | 2         | 5          | 8         | even      |
    |           |            |           | longer    |
    |           |            |           | data      |
    +-----------+------------+-----------+-----------+
    | 3         | 6          | 9         |           |
    +-----------+------------+-----------+-----------+
    | This is a |            |           |           |
    |  single   |            |           |           |
    | row       |            |           |           |
    +-----------+------------+-----------+-----------+


Table-columns can be individually formatted. Note that if an
individual column is set with a specific width, table auto-balancing
will not affect this column (this may lead to the full table being too
wide, so be careful mixing fixed-width columns with auto- balancing).
Here we change the width and alignment of the column at index 3
(Python starts from 0):

```python

table.reformat_column(3, width=30, align="r")
print table
```

::

    +-----------+-------+-----+-----------------------------+---------+
    | Heading1  | Headi |     |                             |         |
    |           | ng2   |     |                             |         |
    +~~~~~~~~~~~+~~~~~~~+~~~~~+~~~~~~~~~~~~~~~~~~~~~~~~~~~~~+~~~~~~~~~+
    | 1         | 4     | 7   |           This is long data | Test1   |
    +-----------+-------+-----+-----------------------------+---------+
    | 2         | 5     | 8   |    This is even longer data | Test3   |
    +-----------+-------+-----+-----------------------------+---------+
    | 3         | 6     | 9   |                             | Test4   |
    +-----------+-------+-----+-----------------------------+---------+
    | This is a |       |     |                             |         |
    |  single   |       |     |                             |         |
    | row       |       |     |                             |         |
    +-----------+-------+-----+-----------------------------+---------+

When adding new rows/columns their data can have its own alignments
(left/center/right, top/center/bottom).

If the height is restricted, cells will be restricted from expanding
vertically. This will lead to text contents being cropped. Each cell
can only shrink to a minimum width and height of 1.

`EvTable` is intended to be used with `ANSIString` for supporting ANSI-coloured
string types.

When a cell is auto-wrapped across multiple lines, ANSI-reset sequences will be
put at the end of each wrapped line. This means that the colour of a wrapped
cell will not "bleed", but it also means that eventual colour outside the table
will not transfer "across" a table, you need to re-set the color to have it
appear on both sides of the table string.

----

"""

from copy import copy, deepcopy
from textwrap import TextWrapper

from django.conf import settings

from evennia.utils.ansi import ANSIString
from evennia.utils.utils import display_len as d_len
from evennia.utils.utils import is_iter, justify

_DEFAULT_WIDTH = settings.CLIENT_DEFAULT_WIDTH


def _to_ansi(obj):
    """
    convert to ANSIString.

    Args:
        obj (str): Convert incoming text to
            be ANSI aware ANSIStrings.
    """
    if is_iter(obj):
        return [_to_ansi(o) for o in obj]
    else:
        return ANSIString(obj)


_whitespace = "\t\n\x0b\x0c\r "


class ANSITextWrapper(TextWrapper):
    """
    This is a wrapper work class for handling strings with ANSI tags
    in it.  It overloads the standard library `TextWrapper` class and
    is used internally in `EvTable` and has no public methods.

    """

    def _munge_whitespace(self, text):
        """_munge_whitespace(text : string) -> string

        Munge whitespace in text: expand tabs and convert all other
        whitespace characters to spaces.  Eg. " foo\tbar\n\nbaz"
        becomes " foo    bar  baz".
        """
        return text

    # TODO: Ignore expand_tabs/replace_whitespace until ANSIString handles them.
    # - don't remove this code. /Griatch
    #        if self.expand_tabs:
    #            text = text.expandtabs()
    #        if self.replace_whitespace:
    #            if isinstance(text, str):
    #                text = text.translate(self.whitespace_trans)
    #        return text

    def _split(self, text):
        """_split(text : string) -> [string]

        Split the text to wrap into indivisible chunks.  Chunks are
        not quite the same as words; see _wrap_chunks() for full
        details.  As an example, the text
          Look, goof-ball -- use the -b option!
        breaks into the following chunks:
          'Look,', ' ', 'goof-', 'ball', ' ', '--', ' ',
          'use', ' ', 'the', ' ', '-b', ' ', 'option!'
        if break_on_hyphens is True, or in:
          'Look,', ' ', 'goof-ball', ' ', '--', ' ',
          'use', ' ', 'the', ' ', '-b', ' ', option!'
        otherwise.
        """
        # NOTE-PYTHON3: The following code only roughly approximates what this
        #               function used to do. Regex splitting on ANSIStrings is
        #               dropping ANSI codes, so we're using ANSIString.split
        #               for the time being.
        #
        #               A less hackier solution would be appreciated.
        chunks = _to_ansi(text).split()

        chunks = [chunk + " " for chunk in chunks if chunk]  # remove empty chunks

        if len(chunks) > 1:
            chunks[-1] = chunks[-1][0:-1]

        return chunks

    def _wrap_chunks(self, chunks):
        """_wrap_chunks(chunks : [string]) -> [string]

        Wrap a sequence of text chunks and return a list of lines of
        length 'self.width' or less.  (If 'break_long_words' is false,
        some lines may be longer than this.)  Chunks correspond roughly
        to words and the whitespace between them: each chunk is
        indivisible (modulo 'break_long_words'), but a line break can
        come between any two chunks.  Chunks should not have internal
        whitespace; ie. a chunk is either all whitespace or a "word".
        Whitespace chunks will be removed from the beginning and end of
        lines, but apart from that whitespace is preserved.
        """
        lines = []
        if self.width <= 0:
            raise ValueError("invalid width %r (must be > 0)" % self.width)

        # Arrange in reverse order so items can be efficiently popped
        # from a stack of chucks.
        chunks.reverse()

        while chunks:

            # Start the list of chunks that will make up the current line.
            # cur_len is just the length of all the chunks in cur_line.
            cur_line = []
            cur_len = 0

            # Figure out which static string will prefix this line.
            if lines:
                indent = self.subsequent_indent
            else:
                indent = self.initial_indent

            # Maximum width for this line.
            width = self.width - d_len(indent)

            # First chunk on line is whitespace -- drop it, unless this
            # is the very beginning of the text (ie. no lines started yet).
            if self.drop_whitespace and chunks[-1].strip() == "" and lines:
                del chunks[-1]

            while chunks:
                ln = d_len(chunks[-1])

                # Can at least squeeze this chunk onto the current line.
                if cur_len + ln <= width:
                    cur_line.append(chunks.pop())
                    cur_len += ln

                # Nope, this line is full.
                else:
                    break

            # The current line is full, and the next chunk is too big to
            # fit on *any* line (not just this one).
            if chunks and d_len(chunks[-1]) > width:
                self._handle_long_word(chunks, cur_line, cur_len, width)

            # If the last chunk on this line is all whitespace, drop it.
            if self.drop_whitespace and cur_line and cur_line[-1].strip() == "":
                del cur_line[-1]

            # Convert current line back to a string and store it in list
            # of all lines (return value).
            if cur_line:
                ln = ""
                for w in cur_line:  # ANSI fix
                    ln += w  #
                lines.append(indent + ln)
        return lines


# -- Convenience interface ---------------------------------------------


def wrap(text, width=_DEFAULT_WIDTH, **kwargs):
    """
    Wrap a single paragraph of text, returning a list of wrapped lines.

    Reformat the single paragraph in 'text' so it fits in lines of no
    more than 'width' columns, and return a list of wrapped lines.  By
    default, tabs in 'text' are expanded with string.expandtabs(), and
    all other whitespace characters (including newline) are converted to

    Args:
        text (str): Text to wrap.
        width (int, optional): Width to wrap `text` to.

    Keyword Args:
        See TextWrapper class for available keyword args to customize
        wrapping behaviour.

    """
    w = ANSITextWrapper(width=width, **kwargs)
    return w.wrap(text)


def fill(text, width=_DEFAULT_WIDTH, **kwargs):
    """Fill a single paragraph of text, returning a new string.

    Reformat the single paragraph in 'text' to fit in lines of no more
    than 'width' columns, and return a new string containing the entire
    wrapped paragraph.  As with wrap(), tabs are expanded and other
    whitespace characters converted to space.

    Args:
        text (str): Text to fill.
        width (int, optional): Width of fill area.

    Keyword Args:
        See TextWrapper class for available keyword args to customize
        filling behaviour.

    """
    w = ANSITextWrapper(width=width, **kwargs)
    return w.fill(text)


# EvCell class (see further down for the EvTable itself)


class EvCell:
    """
    Holds a single data cell for the table. A cell has a certain width
    and height and contains one or more lines of data. It can shrink
    and resize as needed.

    """

    def __init__(self, data, **kwargs):
        """
        Args:
            data (str): The un-padded data of the entry.

        Keyword Args:
            width (int): Desired width of cell. It will pad
                to this size.
            height (int): Desired height of cell. it will pad
                to this size.
            pad_width (int): General padding width. This can be overruled
                by individual settings below.
            pad_left (int): Number of extra pad characters on the left.
            pad_right (int): Number of extra pad characters on the right.
            pad_top (int):  Number of extra pad lines top (will pad with `vpad_char`).
            pad_bottom (int): Number of extra pad lines bottom (will pad with `vpad_char`).
            pad_char (str)- pad character to use for padding. This is overruled
                by individual settings below (default `" "`).
            hpad_char (str): Pad character to use both for extra horizontal
                padding (default `" "`).
            vpad_char (str): Pad character to use for extra vertical padding
                and for vertical fill (default `" "`).
            fill_char (str): Character used to filling (expanding cells to
                desired size). This can be overruled by individual settings below.
            hfill_char (str): Character used for horizontal fill (default `" "`).
            vfill_char (str): Character used for vertical fill (default `" "`).
            align (str): Should be one of "l", "r", "c", "f" or "a" for left-, right-, center-,
                full-justified (with space between words) or absolute (keep as much original
                whitespace as possible). Default is left-aligned.
            valign (str): Should be one of "t", "b" or "c" for top-, bottom and center
                vertical alignment respectively. Default is centered.
            border_width (int): General border width. This is overruled
                by individual settings below.
            border_left (int): Left border width.
            border_right (int): Right border width.
            border_top (int): Top border width.
            border_bottom (int): Bottom border width.
            border_char (str): This will use a single border char for all borders.
                  overruled by individual settings below.
            border_left_char (str): Char used for left border.
            border_right_char (str): Char used for right border.
            border_top_char (str): Char used for top border.
            border_bottom_char (str): Char user for bottom border.
            corner_char (str): Character used when two borders cross.  (default is "").
                This is overruled by individual settings below.
            corner_top_left_char (str): Char used for "nw" corner.
            corner_top_right_char (str):  Char used for "ne" corner.
            corner_bottom_left_char (str): Char used for "sw" corner.
            corner_bottom_right_char (str): Char used for "se" corner.
            crop_string (str): String to use when cropping sideways, default is `'[...]'`.
            crop (bool): Crop contentof cell rather than expand vertically, default=`False`.
            enforce_size (bool): If true, the width/height of the cell is
                strictly enforced and extra text will be cropped rather than the
                cell growing vertically.

        Raises:
            Exception: for impossible cell size requirements where the
                border width or height cannot fit, or the content is too
                small.

        """
        self.formatted = None
        padwidth = kwargs.get("pad_width", None)
        padwidth = int(padwidth) if padwidth is not None else None
        self.pad_left = int(kwargs.get("pad_left", padwidth if padwidth is not None else 1))
        self.pad_right = int(kwargs.get("pad_right", padwidth if padwidth is not None else 1))
        self.pad_top = int(kwargs.get("pad_top", padwidth if padwidth is not None else 0))
        self.pad_bottom = int(kwargs.get("pad_bottom", padwidth if padwidth is not None else 0))

        self.enforce_size = kwargs.get("enforce_size", False)

        # avoid multi-char pad_chars messing up counting
        pad_char = kwargs.get("pad_char", " ")
        pad_char = pad_char[0] if pad_char else " "
        hpad_char = kwargs.get("hpad_char", pad_char)
        self.hpad_char = hpad_char[0] if hpad_char else pad_char
        vpad_char = kwargs.get("vpad_char", pad_char)
        self.vpad_char = vpad_char[0] if vpad_char else pad_char

        fill_char = kwargs.get("fill_char", " ")
        fill_char = fill_char[0] if fill_char else " "
        hfill_char = kwargs.get("hfill_char", fill_char)
        self.hfill_char = hfill_char[0] if hfill_char else " "
        vfill_char = kwargs.get("vfill_char", fill_char)
        self.vfill_char = vfill_char[0] if vfill_char else " "

        self.crop_string = kwargs.get("crop_string", "[...]")

        # borders and corners
        borderwidth = kwargs.get("border_width", 0)
        self.border_left = kwargs.get("border_left", borderwidth)
        self.border_right = kwargs.get("border_right", borderwidth)
        self.border_top = kwargs.get("border_top", borderwidth)
        self.border_bottom = kwargs.get("border_bottom", borderwidth)

        borderchar = kwargs.get("border_char", None)
        self.border_left_char = kwargs.get("border_left_char", borderchar if borderchar else "|")
        self.border_right_char = kwargs.get(
            "border_right_char", borderchar if borderchar else self.border_left_char
        )
        self.border_top_char = kwargs.get("border_top_char", borderchar if borderchar else "-")
        self.border_bottom_char = kwargs.get(
            "border_bottom_char", borderchar if borderchar else self.border_top_char
        )

        corner_char = kwargs.get("corner_char", "+")
        self.corner_top_left_char = kwargs.get("corner_top_left_char", corner_char)
        self.corner_top_right_char = kwargs.get("corner_top_right_char", corner_char)
        self.corner_bottom_left_char = kwargs.get("corner_bottom_left_char", corner_char)
        self.corner_bottom_right_char = kwargs.get("corner_bottom_right_char", corner_char)

        # alignments
        self.align = kwargs.get("align", "l")
        self.valign = kwargs.get("valign", "c")

        self.data = self._split_lines(_to_ansi(data))
        self.raw_width = max(d_len(line) for line in self.data)
        self.raw_height = len(self.data)

        # this is extra trimming required for cels in the middle of a table only
        self.trim_horizontal = 0
        self.trim_vertical = 0

        # width/height is given without left/right or top/bottom padding
        if "width" in kwargs:
            width = kwargs.pop("width")
            self.width = (
                width - self.pad_left - self.pad_right - self.border_left - self.border_right
            )
            if self.width <= 0 < self.raw_width:
                raise Exception("Cell width too small - no space for data.")
        else:
            self.width = self.raw_width
        if "height" in kwargs:
            height = kwargs.pop("height")
            self.height = (
                height - self.pad_top - self.pad_bottom - self.border_top - self.border_bottom
            )
            if self.height <= 0 < self.raw_height:
                raise Exception("Cell height too small - no space for data.")
        else:
            self.height = self.raw_height

    def _reformat(self):
        """
        Apply all EvCells' formatting operations.

        """
        data = self._border(self._pad(self._valign(self._align(self._fit_width(self.data)))))
        return data

    def _split_lines(self, text):
        """
        Simply split by linebreaks

        Args:
            text (str): text to split.

        Returns:
            split (list): split text.
        """
        return text.split("\n")

    def _fit_width(self, data):
        """
        Split too-long lines to fit the desired width of the Cell.

        Args:
            data (str): Text to adjust to the cell's width.

        Returns:
            adjusted data (str): The adjusted text.

        Notes:
            This also updates `raw_width`.


        """
        width = self.width
        adjusted_data = []
        for line in data:
            if 0 < width < d_len(line):
                # replace_whitespace=False, expand_tabs=False is a
                # fix for ANSIString not supporting expand_tabs/translate
                adjusted_data.extend(
                    [
                        ANSIString(part + ANSIString("|n"))
                        for part in wrap(line, width=width, drop_whitespace=False)
                    ]
                )
            else:
                adjusted_data.append(line)
        if self.enforce_size:
            # don't allow too high cells
            excess = len(adjusted_data) - self.height
            if excess > 0:
                # too many lines. Crop and mark last line with crop_string
                crop_string = self.crop_string
                adjusted_data = adjusted_data[:-excess]
                adjusted_data_length = len(adjusted_data[-1])
                crop_string_length = len(crop_string)
                if adjusted_data_length >= crop_string_length:
                    # replace with data[...]
                    # (note that if adjusted data is shorter than the crop-string,
                    # we skip the crop-string and just pass the cropped data.)
                    adjusted_data[-1] = adjusted_data[-1][:-crop_string_length] + crop_string

            elif excess < 0:
                # too few lines. Fill to height.
                adjusted_data.extend(["" for _ in range(excess)])

        return adjusted_data

    def _align(self, data):
        """
        Align list of rows of cell. Whitespace characters will be stripped
        if there is only one whitespace character - otherwise, it's assumed
        the caller may be trying some manual formatting in the text.

        Args:
            data (str): Text to align.

        Returns:
            text (str): Aligned result.

        """
        align = self.align
        hfill_char = self.hfill_char
        width = self.width
        return [justify(line, width, align=align, fillchar=hfill_char) for line in data]

    def _valign(self, data):
        """
        Align cell vertically

        Args:
            data (str): Text to align.

        Returns:
            text (str): Vertically aligned text.

        """
        valign = self.valign
        height = self.height
        cheight = len(data)
        excess = height - cheight
        padline = self.vfill_char * self.width

        if excess <= 0:
            return data
        # only care if we need to add new lines
        if valign == "t":
            return data + [padline for _ in range(excess)]
        elif valign == "b":
            return [padline for _ in range(excess)] + data
        else:  # center
            narrowside = [padline for _ in range(excess // 2)]
            widerside = narrowside + [padline]
            if excess % 2:
                # uneven padding
                if height % 2:
                    return widerside + data + narrowside
                else:
                    return narrowside + data + widerside
            else:
                # even padding, same on both sides
                return narrowside + data + narrowside

    def _pad(self, data):
        """
        Pad data with extra characters on all sides.

        Args:
            data (str): Text to pad.

        Returns:
            text (str): Padded text.

        """
        left = self.hpad_char * self.pad_left
        right = self.hpad_char * self.pad_right
        vfill = (self.width + self.pad_left + self.pad_right) * self.vpad_char
        top = [vfill for _ in range(self.pad_top)]
        bottom = [vfill for _ in range(self.pad_bottom)]
        return top + [left + line + right for line in data] + bottom

    def _border(self, data):
        """
        Add borders to the cell.

        Args:
            data (str): Text to surround with borders.

        Return:
            text (str): Text with borders.

        """

        left = self.border_left_char * self.border_left + ANSIString("|n")
        right = ANSIString("|n") + self.border_right_char * self.border_right

        cwidth = (
            self.width
            + self.pad_left
            + self.pad_right
            + max(0, self.border_left - 1)
            + max(0, self.border_right - 1)
        )

        vfill = self.corner_top_left_char if left else ""
        vfill += cwidth * self.border_top_char
        vfill += self.corner_top_right_char if right else ""
        top = [vfill for _ in range(self.border_top)]

        vfill = self.corner_bottom_left_char if left else ""
        vfill += cwidth * self.border_bottom_char
        vfill += self.corner_bottom_right_char if right else ""
        bottom = [vfill for _ in range(self.border_bottom)]

        return top + [left + line + right for line in data] + bottom

    def get_min_height(self):
        """
        Get the minimum possible height of cell, including at least
        one line for data.

        Returns:
            min_height (int): The mininum height of cell.

        """
        return self.pad_top + self.pad_bottom + self.border_bottom + self.border_top + 1

    def get_min_width(self):
        """
        Get the minimum possible width of cell, including at least one
        character-width for data.

        Returns:
            min_width (int): The minimum width of cell.

        """
        return self.pad_left + self.pad_right + self.border_left + self.border_right + 1

    def get_height(self):
        """
        Get natural height of cell, including padding.

        Returns:
            natural_height (int): Height of cell.

        """
        return len(self.formatted)  # if self.formatted else 0

    def get_width(self):
        """
        Get natural width of cell, including padding.

        Returns:
            natural_width (int): Width of cell.

        """
        return d_len(self.formatted[0])  # if self.formatted else 0

    def replace_data(self, data, **kwargs):
        """
        Replace cell data. This causes a full reformat of the cell.

        Args:
            data (str): Cell data.

        Notes:
            The available keyword arguments are the same as for
            `EvCell.__init__`.

        """
        self.data = self._split_lines(_to_ansi(data))
        self.raw_width = max(d_len(line) for line in self.data)
        self.raw_height = len(self.data)
        self.reformat(**kwargs)

    def reformat(self, **kwargs):
        """
        Reformat the EvCell with new options

        Keyword Args:
            The available keyword arguments are the same as for `EvCell.__init__`.

        Raises:
            Exception: If the cells cannot shrink enough to accomodate
                the options or the data given.

        """
        # keywords that require manipulation
        padwidth = kwargs.get("pad_width", None)
        padwidth = int(padwidth) if padwidth is not None else None
        self.pad_left = int(
            kwargs.pop("pad_left", padwidth if padwidth is not None else self.pad_left)
        )
        self.pad_right = int(
            kwargs.pop("pad_right", padwidth if padwidth is not None else self.pad_right)
        )
        self.pad_top = int(
            kwargs.pop("pad_top", padwidth if padwidth is not None else self.pad_top)
        )
        self.pad_bottom = int(
            kwargs.pop("pad_bottom", padwidth if padwidth is not None else self.pad_bottom)
        )

        self.enforce_size = kwargs.get("enforce_size", False)

        pad_char = kwargs.pop("pad_char", None)
        hpad_char = kwargs.pop("hpad_char", pad_char)
        self.hpad_char = hpad_char[0] if hpad_char else self.hpad_char
        vpad_char = kwargs.pop("vpad_char", pad_char)
        self.vpad_char = vpad_char[0] if vpad_char else self.vpad_char

        fillchar = kwargs.pop("fill_char", None)
        hfill_char = kwargs.pop("hfill_char", fillchar)
        self.hfill_char = hfill_char[0] if hfill_char else self.hfill_char
        vfill_char = kwargs.pop("vfill_char", fillchar)
        self.vfill_char = vfill_char[0] if vfill_char else self.vfill_char

        borderwidth = kwargs.get("border_width", None)
        self.border_left = kwargs.pop(
            "border_left", borderwidth if borderwidth is not None else self.border_left
        )
        self.border_right = kwargs.pop(
            "border_right", borderwidth if borderwidth is not None else self.border_right
        )
        self.border_top = kwargs.pop(
            "border_top", borderwidth if borderwidth is not None else self.border_top
        )
        self.border_bottom = kwargs.pop(
            "border_bottom", borderwidth if borderwidth is not None else self.border_bottom
        )

        borderchar = kwargs.get("border_char", None)
        self.border_left_char = kwargs.pop(
            "border_left_char", borderchar if borderchar else self.border_left_char
        )
        self.border_right_char = kwargs.pop(
            "border_right_char", borderchar if borderchar else self.border_right_char
        )
        self.border_top_char = kwargs.pop(
            "border_topchar", borderchar if borderchar else self.border_top_char
        )
        self.border_bottom_char = kwargs.pop(
            "border_bottom_char", borderchar if borderchar else self.border_bottom_char
        )

        corner_char = kwargs.get("corner_char", None)
        self.corner_top_left_char = kwargs.pop(
            "corner_top_left", corner_char if corner_char is not None else self.corner_top_left_char
        )
        self.corner_top_right_char = kwargs.pop(
            "corner_top_right",
            corner_char if corner_char is not None else self.corner_top_right_char,
        )
        self.corner_bottom_left_char = kwargs.pop(
            "corner_bottom_left",
            corner_char if corner_char is not None else self.corner_bottom_left_char,
        )
        self.corner_bottom_right_char = kwargs.pop(
            "corner_bottom_right",
            corner_char if corner_char is not None else self.corner_bottom_right_char,
        )

        # this is used by the table to adjust size of cells with borders in the middle
        # of the table
        self.trim_horizontal = kwargs.pop("trim_horizontal", self.trim_horizontal)
        self.trim_vertical = kwargs.pop("trim_vertical", self.trim_vertical)

        # fill all other properties
        for key, value in kwargs.items():
            setattr(self, key, value)

        # Handle sizes
        if "width" in kwargs:
            width = kwargs.pop("width")
            self.width = (
                width
                - self.pad_left
                - self.pad_right
                - self.border_left
                - self.border_right
                + self.trim_horizontal
            )
            # if self.width <= 0 and self.raw_width > 0:
            if self.width <= 0 < self.raw_width:
                raise Exception("Cell width too small, no room for data.")
        if "height" in kwargs:
            height = kwargs.pop("height")
            self.height = (
                height
                - self.pad_top
                - self.pad_bottom
                - self.border_top
                - self.border_bottom
                + self.trim_vertical
            )
            if self.height <= 0 < self.raw_height:
                raise Exception("Cell height too small, no room for data.")

        # reformat (to new sizes, padding, header and borders)
        self.formatted = self._reformat()

    def get(self):
        """
        Get data, padded and aligned in the form of a list of lines.

        """
        if not self.formatted:
            self.formatted = self._reformat()
        return self.formatted

    def __repr__(self):
        if not self.formatted:
            self.formatted = self._reformat()
        return str(ANSIString("<EvCel %s>" % self.formatted))

    def __str__(self):
        "returns cell contents on string form"
        if not self.formatted:
            self.formatted = self._reformat()
        return str(ANSIString("\n").join(self.formatted))


# EvColumn class


class EvColumn:
    """
    This class holds a list of Cells to represent a column of a table.
    It holds operations and settings that affect *all* cells in the
    column.

    Columns are not intended to be used stand-alone; they should be
    incorporated into an EvTable (like EvCells)

    """

    def __init__(self, *args, **kwargs):
        """
        Args:
            Text for each row in the column

        Keyword Args:
            All `EvCell.__init_` keywords are available, these
            settings will be persistently applied to every Cell in the
            column.

        """
        self.options = kwargs  # column-specific options
        self.column = [EvCell(data, **kwargs) for data in args]

    def _balance(self, **kwargs):
        """
        Make sure to adjust the width of all cells so we form a
        coherent and lined-up column. Will enforce column-specific
        options to cells.

        Keyword Args:
            Extra keywords to modify the column setting. Same keywords
            as in `EvCell.__init__`.

        """
        col = self.column
        # fixed options for the column will override those requested in the call!
        # this is particularly relevant to things like width/height, to avoid
        # fixed-widths columns from being auto-balanced
        kwargs.update(self.options)
        # use fixed width or adjust to the largest cell
        if "width" not in kwargs:
            [
                cell.reformat() for cell in col
            ]  # this is necessary to get initial widths of all cells
            kwargs["width"] = max(cell.get_width() for cell in col) if col else 0
        [cell.reformat(**kwargs) for cell in col]

    def add_rows(self, *args, **kwargs):
        """
        Add new cells to column. They will be inserted as
        a series of rows. It will inherit the options
        of the rest of the column's cells (use update to change
        options).

        Args:
            Texts for the new cells
            ypos (int, optional): Index position in table before which to insert the
                new column. Uses Python indexing, so to insert at the top,
                use `ypos=0`. If not given, data will be inserted at the end
                of the column.

        Keyword Args:
            Available keywods as per `EvCell.__init__`.

        """
        # column-level options override those in kwargs
        options = {**kwargs, **self.options}

        ypos = kwargs.get("ypos", None)
        if ypos is None or ypos > len(self.column):
            # add to the end
            self.column.extend([EvCell(data, **options) for data in args])
        else:
            # insert cells before given index
            ypos = min(len(self.column) - 1, max(0, int(ypos)))
            new_cells = [EvCell(data, **options) for data in args]
            self.column = self.column[:ypos] + new_cells + self.column[ypos:]
        # self._balance(**kwargs)

    def reformat(self, **kwargs):
        """
        Change the options for the column.

        Keyword Args:
            Keywords as per `EvCell.__init__`.

        """
        self._balance(**kwargs)

    def reformat_cell(self, index, **kwargs):
        """
        reformat cell at given index, keeping column options if
        necessary.

        Args:
            index (int): Index location of the cell in the column,
                starting from 0 for the first row to Nrows-1.

        Keyword Args:
            Keywords as per `EvCell.__init__`.

        """
        # column-level options take precedence here
        kwargs.update(self.options)
        self.column[index].reformat(**kwargs)

    def __repr__(self):
        return "<EvColumn\n  %s>" % "\n  ".join([repr(cell) for cell in self.column])

    def __len__(self):
        return len(self.column)

    def __iter__(self):
        return iter(self.column)

    def __getitem__(self, index):
        return self.column[index]

    def __setitem__(self, index, value):
        self.column[index] = value

    def __delitem__(self, index):
        del self.column[index]


# Main Evtable class


class EvTable:
    """
    The table class holds a list of EvColumns, each consisting of EvCells so
    that the result is a 2D matrix.
    """

    def __init__(self, *args, **kwargs):
        """
        Args:
            Header texts for the table.

        Keyword Args:
            table (list of lists or list of `EvColumns`, optional):
                This is used to build the table in a quick way.  If not
                given, the table will start out empty and `add_` methods
                need to be used to add rows/columns.
            header (bool, optional): `True`/`False` - turn off the
                header texts (`*args`) being treated as a header (such as
                not adding extra underlining)
            pad_width (int, optional): How much empty space to pad your cells with
                (default is 1)
            border (str, optional)): The border style to use. This is one of
                    - `None` - No border drawing at all.
                    - "table" - only a border around the whole table.
                    - "tablecols" - table and column borders. (default)
                    - "header" - only border under header.
                    - "cols" - only vertical borders.
                    - "incols" - vertical borders, no outer edges.
                    - "rows" - only borders between rows.
                    - "cells" - border around all cells.
            border_width (int, optional): Width of table borders, if border is active.
                Note that widths wider than 1 may give artifacts in the corners. Default is 1.
            corner_char (str, optional): Character to use in corners when border is active.
                Default is `+`.
            corner_top_left_char (str, optional): Character used for "nw" corner of table.
                Defaults to `corner_char`.
            corner_top_right_char (str, optional): Character used for "ne" corner of table.
                Defaults to `corner_char`.
            corner_bottom_left_char (str, optional): Character used for "sw" corner of table.
                Defaults to `corner_char`.
            corner_bottom_right_char (str, optional): Character used for "se" corner of table.
                Defaults to `corner_char`.
            pretty_corners (bool, optional): Use custom characters to
                make the table corners look "rounded". Uses UTF-8
                characters. Defaults to `False` for maximum compatibility with various displays
                that may occationally have issues with UTF-8 characters.
            header_line_char (str, optional): Character to use for underlining
                the header row (default is '~'). Requires `border` to not be `None`.
            width (int, optional): Fixed width of table. If not set,
                width is set by the total width of each column.  This will
                resize individual columns in the vertical direction to fit.
            height (int, optional): Fixed height of table. Defaults to being unset. Width is
                still given precedence. If given, table cells will crop text rather
                than expand vertically.
            evenwidth (bool, optional): Used with the `width` keyword. Adjusts columns to have as
                even width as possible. This often looks best also for mixed-length tables. Default
                is `False`.
            maxwidth (int, optional):  This will set a maximum width
                of the table while allowing it to be smaller. Only if it grows wider than this
                size will it be resized by expanding horizontally (or crop `height` is given).
                This keyword has no meaning if `width` is set.

        Raises:
            Exception: If given erroneous input or width settings for the data.

        Notes:
            Beyond those table-specific keywords, the non-overlapping keywords
            of `EvCell.__init__` are also available. These will be passed down
            to every cell in the table.

        """
        # at this point table is a 2D grid - a list of columns
        # x is the column position, y the row
        table = kwargs.pop("table", [])

        # header is a list of texts. We merge it to the table's top
        header = [_to_ansi(head) for head in args]
        self.header = header != []
        if self.header:
            if table:
                excess = len(header) - len(table)
                if excess > 0:
                    # header bigger than table
                    table.extend([] for _ in range(excess))
                elif excess < 0:
                    # too short header
                    header.extend(_to_ansi(["" for _ in range(abs(excess))]))
                for ix, heading in enumerate(header):
                    table[ix].insert(0, heading)
            else:
                table = [[heading] for heading in header]
        # even though we inserted the header, we can still turn off
        # header border underling etc. We only allow this if a header
        # was actually set
        self.header = kwargs.pop("header", self.header) if self.header else False
        hchar = kwargs.pop("header_line_char", "~")
        self.header_line_char = hchar[0] if hchar else "~"

        border = kwargs.pop("border", "tablecols")
        if border is None:
            border = "none"
        if border not in (
            "none",
            "table",
            "tablecols",
            "header",
            "incols",
            "cols",
            "rows",
            "cells",
        ):
            raise Exception("Unsupported border type: '%s'" % border)
        self.border = border

        # border settings are passed into Cell as well (so kwargs.get and not pop)
        self.border_width = kwargs.get("border_width", 1)
        self.corner_char = kwargs.get("corner_char", "+")
        pcorners = kwargs.pop("pretty_corners", False)
        self.corner_top_left_char = _to_ansi(
            kwargs.pop("corner_top_left_char", "." if pcorners else self.corner_char)
        )
        self.corner_top_right_char = _to_ansi(
            kwargs.pop("corner_top_right_char", "." if pcorners else self.corner_char)
        )
        self.corner_bottom_left_char = _to_ansi(
            kwargs.pop("corner_bottom_left_char", " " if pcorners else self.corner_char)
        )
        self.corner_bottom_right_char = _to_ansi(
            kwargs.pop("corner_bottom_right_char", " " if pcorners else self.corner_char)
        )

        self.width = kwargs.pop("width", None)
        self.height = kwargs.pop("height", None)
        self.evenwidth = kwargs.pop("evenwidth", False)
        self.maxwidth = kwargs.pop("maxwidth", None)
        if self.maxwidth and self.width and self.maxwidth < self.width:
            raise Exception("table maxwidth < table width!")
        # size in cell cols/rows
        self.ncols = len(table)
        self.nrows = max(len(col) for col in table) if table else 0
        # size in characters (gets set when _balance is called)
        self.nwidth = 0
        self.nheight = 0
        # save options
        self.options = kwargs

        # use the temporary table to generate the table on the fly, as a list of EvColumns
        self.table = []
        for col in table:
            if isinstance(col, EvColumn):
                self.add_column(col, **kwargs)
            elif isinstance(col, (list, tuple)):
                self.table.append(EvColumn(*col, **kwargs))
            else:
                raise RuntimeError(
                    "EvTable 'table' kwarg must be a list of EvColumns or a list-of-lists of"
                    f" strings. Found {type(col)}."
                )

        # self.table = [EvColumn(*col, **kwargs) for col in table]

        # this is the actual working table
        self.worktable = None

        # balance the table
        # self._balance()

    def _cellborders(self, ix, iy, nx, ny, **kwargs):
        """
        Adds borders to the table by adjusting the input kwarg to
        instruct cells to build a border in the right positions.

        Args:
            ix (int): x index positions in table.
            iy (int): y index positions in table.
            nx (int): x size of table.
            ny (int): y size of table.

        Keyword Args:
            Keywords as per `EvTable.__init__`.

        Returns:
            table (str): string with the correct borders.

        Notes:
            A copy of the kwarg is returned to the cell. This is method
            is called by self._borders.

        """

        ret = kwargs.copy()

        # handle the various border modes
        border = self.border
        header = self.header

        bwidth = self.border_width
        headchar = self.header_line_char

        def corners(ret):
            """Handle corners of table"""
            if ix == 0 and iy == 0:
                ret["corner_top_left_char"] = self.corner_top_left_char
            if ix == nx and iy == 0:
                ret["corner_top_right_char"] = self.corner_top_right_char
            if ix == 0 and iy == ny:
                ret["corner_bottom_left_char"] = self.corner_bottom_left_char
            if ix == nx and iy == ny:
                ret["corner_bottom_right_char"] = self.corner_bottom_right_char
            return ret

        def left_edge(ret):
            """add vertical border along left table edge"""
            if ix == 0:
                ret["border_left"] = bwidth
                # ret["trim_horizontal"] = bwidth
            return ret

        def top_edge(ret):
            """add border along top table edge"""
            if iy == 0:
                ret["border_top"] = bwidth
                # ret["trim_vertical"] = bwidth
            return ret

        def right_edge(ret):
            """add vertical border along right table edge"""
            if ix == nx:  # and 0 < iy < ny:
                ret["border_right"] = bwidth
                # ret["trim_horizontal"] = 0
            return ret

        def bottom_edge(ret):
            """add border along bottom table edge"""
            if iy == ny:
                ret["border_bottom"] = bwidth
                # ret["trim_vertical"] = bwidth
            return ret

        def cols(ret):
            """Adding vertical borders inside the table"""
            if 0 <= ix < nx:
                ret["border_right"] = bwidth
            return ret

        def rows(ret):
            """Adding horizontal borders inside the table"""
            if 0 <= iy < ny:
                ret["border_bottom"] = bwidth
            return ret

        def head(ret):
            """Add header underline"""
            if iy == 0:
                # put different bottom line for header
                ret["border_bottom"] = bwidth
                ret["border_bottom_char"] = headchar
            return ret

        # use the helper functions to define various
        # table "styles"

        if border in ("table", "tablecols", "cells"):
            ret = bottom_edge(right_edge(top_edge(left_edge(corners(ret)))))
        if border in ("cols", "tablecols", "cells"):
            ret = cols(right_edge(left_edge(ret)))
        if border in "incols":
            ret = cols(ret)
        if border in ("rows", "cells"):
            ret = rows(bottom_edge(top_edge(ret)))
        if header and border not in ("none", None):
            ret = head(ret)

        return ret

    def _borders(self):
        """
        Add borders to table. This is called from self._balance.
        """
        nx, ny = self.ncols - 1, self.nrows - 1
        options = self.options
        for ix, col in enumerate(self.worktable):
            for iy, cell in enumerate(col):
                col.reformat_cell(iy, **self._cellborders(ix, iy, nx, ny, **options))

    def _balance(self):
        """
        Balance the table. This means to make sure
        all cells on the same row have the same height,
        that all columns have the same number of rows
        and that the table fits within the given width.
        """

        # we make all modifications on a working copy of the
        # actual table. This allows us to add columns/rows
        # and re-balance over and over without issue.
        self.worktable = deepcopy(self.table)
        #        self._borders()
        #        return
        options = copy(self.options)

        # balance number of rows to make a rectangular table
        # column by column
        ncols = len(self.worktable)
        nrows = [len(col) for col in self.worktable]
        nrowmax = max(nrows) if nrows else 0
        for icol, nrow in enumerate(nrows):
            self.worktable[icol].reformat(**options)
            if nrow < nrowmax:
                # add more rows to too-short columns
                empty_rows = ["" for _ in range(nrowmax - nrow)]
                self.worktable[icol].add_rows(*empty_rows)
        self.ncols = ncols
        self.nrows = nrowmax

        # add borders - these add to the width/height, so we must do this before calculating
        # width/height
        self._borders()

        # equalize widths within each column
        cwidths = [max(cell.get_width() for cell in col) for col in self.worktable]

        if self.width or self.maxwidth and self.maxwidth < sum(cwidths):
            # we set a table width. Horizontal cells will be evenly distributed and
            # expand vertically as needed (unless self.height is set, see below)

            # use fixed width, or set to maxwidth
            width = self.width if self.width else self.maxwidth

            if ncols:
                # get minimum possible cell widths for each row
                cwidths_min = [max(cell.get_min_width() for cell in col) for col in self.worktable]
                cwmin = sum(cwidths_min)

                # get which cols have separately set widths - these should be locked
                # note that we need to remove cwidths_min for each lock to avoid counting
                # it twice (in cwmin and in locked_cols)
                locked_cols = {
                    icol: col.options["width"] - cwidths_min[icol]
                    for icol, col in enumerate(self.worktable)
                    if "width" in col.options
                }
                locked_width = sum(locked_cols.values())

                excess = width - cwmin - locked_width

                if len(locked_cols) >= ncols and excess:
                    # we can't adjust the width at all - all columns are locked
                    raise Exception(
                        "Cannot balance table to width %s - "
                        "all columns have a set, fixed width summing to %s!"
                        % (self.width, sum(cwidths))
                    )

                if excess < 0:
                    # the locked cols makes it impossible
                    raise Exception(
                        "Cannot shrink table width to %s. "
                        "Minimum size (and/or fixed-width columns) "
                        "sets minimum at %s." % (self.width, cwmin + locked_width)
                    )

                if self.evenwidth:
                    # make each column of equal width
                    # use cwidths as a work-array to track weights
                    cwidths = copy(cwidths_min)
                    correction = 0
                    while correction < excess:
                        # flood-fill the minimum table starting with the smallest columns
                        ci = cwidths.index(min(cwidths))
                        if ci in locked_cols:
                            # locked column, make sure it's not picked again
                            cwidths[ci] += 9999
                            cwidths_min[ci] = locked_cols[ci]
                        else:
                            cwidths_min[ci] += 1
                            correction += 1
                    cwidths = cwidths_min
                else:
                    # make each column expand more proportional to their data size
                    # we use cwidth as a work-array to track weights
                    correction = 0
                    while correction < excess:
                        # fill wider columns first
                        ci = cwidths.index(max(cwidths))
                        if ci in locked_cols:
                            # locked column, make sure it's not picked again
                            cwidths[ci] -= 9999
                            cwidths_min[ci] = locked_cols[ci]
                        else:
                            cwidths_min[ci] += 1
                            correction += 1
                            # give a just changed col less prio next run
                            cwidths[ci] -= 3
                    cwidths = cwidths_min

        # reformat worktable (for width align)
        for ix, col in enumerate(self.worktable):
            try:
                col.reformat(width=cwidths[ix], **options)
            except Exception:
                raise

        # equalize heights for each row (we must do this here, since it may have changed to fit new
        # widths)
        cheights = [
            max(cell.get_height() for cell in (col[iy] for col in self.worktable))
            for iy in range(nrowmax)
        ]

        if self.height:
            # if we are fixing the table height, it means cells must crop text instead of resizing.
            if nrowmax:

                # get minimum possible cell heights for each column
                cheights_min = [
                    max(cell.get_min_height() for cell in (col[iy] for col in self.worktable))
                    for iy in range(nrowmax)
                ]
                chmin = sum(cheights_min)

                # get which cols have separately set heights - these should be locked
                # note that we need to remove cheights_min for each lock to avoid counting
                # it twice (in chmin and in locked_cols)
                locked_cols = {
                    icol: col.options["height"] - cheights_min[icol]
                    for icol, col in enumerate(self.worktable)
                    if "height" in col.options
                }
                locked_height = sum(locked_cols.values())

                excess = self.height - chmin - locked_height

                if chmin > self.height:
                    # we cannot shrink any more
                    raise Exception(
                        "Cannot shrink table height to %s. Minimum "
                        "size (and/or fixed-height rows) sets minimum at %s."
                        % (self.height, chmin + locked_height)
                    )

                # Add all the excess at the end of the table
                # Note: Older solutions tried to balance individual
                # rows' vsize. This could lead to empty rows that
                # looked like a bug. This solution instead
                # adds empty rows at the end which is less sophisticated
                # but much more visually consistent.
                cheights_min[-1] += excess
                cheights = cheights_min

                # we must tell cells to crop instead of expanding
            options["enforce_size"] = True

        # reformat table (for vertical align)
        for ix, col in enumerate(self.worktable):
            for iy, cell in enumerate(col):
                try:
                    col.reformat_cell(iy, height=cheights[iy], **options)
                except Exception as e:
                    msg = "ix=%s, iy=%s, height=%s: %s" % (ix, iy, cheights[iy], e.message)
                    raise Exception("Error in vertical align:\n %s" % msg)

        # calculate actual table width/height in characters
        self.cwidth = sum(cwidths)
        self.cheight = sum(cheights)

    def _generate_lines(self):
        """
        Generates lines across all columns
        (each cell may contain multiple lines)
        This will also balance the table.
        """
        self._balance()
        for iy in range(self.nrows):
            cell_row = [col[iy] for col in self.worktable]
            # this produces a list of lists, each of equal length
            cell_data = [cell.get() for cell in cell_row]
            cell_height = min(len(lines) for lines in cell_data)
            for iline in range(cell_height):
                yield ANSIString("").join(_to_ansi(celldata[iline] for celldata in cell_data))

    def add_header(self, *args, **kwargs):
        """
        Add header to table. This is a number of texts to be put at
        the top of the table. They will replace an existing header.

        Args:
            args (str): These strings will be used as the header texts.

        Keyword Args:
            Same keywords as per `EvTable.__init__`. Will be applied
            to the new header's cells.

        """
        self.header = True
        self.add_row(ypos=0, *args, **kwargs)

    def add_column(self, *args, **kwargs):
        """
        Add a column to table. If there are more rows in new column
        than there are rows in the current table, the table will
        expand with empty rows in the other columns. If too few, the
        new column with get new empty rows. All filling rows are added
        to the end.

        Args:
            args (`EvColumn` or multiple strings): Either a single EvColumn instance or
                a number of data string arguments to be used to create a new column.
            header (str, optional): The header text for the column
            xpos (int, optional): Index position in table *before* which
               to input new column. If not given, column will be added to the end
               of the table. Uses Python indexing (so first column is `xpos=0`)

        Keyword Args:
            Other keywords as per `Cell.__init__`.

        """
        # this will replace default options with new ones without changing default
        options = dict(list(self.options.items()) + list(kwargs.items()))

        xpos = kwargs.get("xpos", None)

        if args and isinstance(args[0], EvColumn):
            column = args[0]
            column.reformat(**kwargs)
        else:
            column = EvColumn(*args, **options)
        wtable = self.ncols
        htable = self.nrows

        header = kwargs.get("header", None)
        if header:
            column.add_rows(str(header), ypos=0, **options)
            self.header = True
        elif self.header:
            # we have a header already. Offset
            column.add_rows("", ypos=0, **options)

        # Calculate whether the new column needs to expand to the
        # current table size, or if the table needs to expand to
        # the column size.
        # This needs to happen after the header rows have already been
        # added to the column in order for the size calculations to match.
        excess = len(column) - htable
        if excess > 0:
            # we need to add new rows to table
            for col in self.table:
                empty_rows = ["" for _ in range(excess)]
                col.add_rows(*empty_rows, **options)
            self.nrows += excess
        elif excess < 0:
            # we need to add new rows to new column
            empty_rows = ["" for _ in range(abs(excess))]
            column.add_rows(*empty_rows, **options)
            self.nrows -= excess

        if xpos is None or xpos > wtable - 1:
            # add to the end
            self.table.append(column)
        else:
            # insert column
            xpos = min(wtable - 1, max(0, int(xpos)))
            self.table.insert(xpos, column)
        self.ncols += 1

    def add_row(self, *args, **kwargs):
        """
        Add a row to table (not a header). If there are more cells in
        the given row than there are cells in the current table the
        table will be expanded with empty columns to match. These will
        be added to the end of the table. In the same way, adding a
        line with too few cells will lead to the last ones getting
        padded.

        Args:
            args (str): Any number of string argumnets to use as the
                data in the row (one cell per argument).
            ypos (int, optional): Index position in table before which to
                 input new row. If not given, will be added to the end of the table.
                 Uses Python indexing (so first row is `ypos=0`)

        Keyword Args:
            Other keywords are as per `EvCell.__init__`.

        """
        # this will replace default options with new ones without changing default
        row = list(args)
        options = dict(list(self.options.items()) + list(kwargs.items()))

        ypos = kwargs.get("ypos", None)
        wtable = self.ncols
        htable = self.nrows
        excess = len(row) - wtable

        if excess > 0:
            # we need to add new empty columns to table
            empty_rows = ["" for _ in range(htable)]
            self.table.extend([EvColumn(*empty_rows, **options) for _ in range(excess)])
        elif excess < 0:
            # we need to add more cells to row
            row.extend(["" for _ in range(abs(excess))])
        self.ncols = len(self.table)

        if ypos is None or ypos > htable - 1:
            # add new row to the end
            for icol, col in enumerate(self.table):
                col.add_rows(row[icol], **options)
        else:
            # insert row elsewhere
            ypos = min(htable - 1, max(0, int(ypos)))
            for icol, col in enumerate(self.table):
                col.add_rows(row[icol], ypos=ypos, **options)
        self.nrows += 1
        # self._balance()

    def reformat(self, **kwargs):
        """
        Force a re-shape of the entire table.

        Keyword Args:
            Table options as per `EvTable.__init__`.

        """
        self.width = kwargs.pop("width", self.width)
        self.height = kwargs.pop("height", self.height)
        for key, value in kwargs.items():
            setattr(self, key, value)

        hchar = kwargs.pop("header_line_char", self.header_line_char)

        # border settings are also passed on into EvCells (so kwargs.get, not kwargs.pop)
        self.header_line_char = hchar[0] if hchar else self.header_line_char
        self.border_width = kwargs.get("border_width", self.border_width)
        self.corner_char = kwargs.get("corner_char", self.corner_char)
        self.header_line_char = kwargs.get("header_line_char", self.header_line_char)

        self.corner_top_left_char = _to_ansi(kwargs.pop("corner_top_left_char", self.corner_char))
        self.corner_top_right_char = _to_ansi(kwargs.pop("corner_top_right_char", self.corner_char))
        self.corner_bottom_left_char = _to_ansi(
            kwargs.pop("corner_bottom_left_char", self.corner_char)
        )
        self.corner_bottom_right_char = _to_ansi(
            kwargs.pop("corner_bottom_right_char", self.corner_char)
        )

        self.options.update(kwargs)

    def reformat_column(self, index, **kwargs):
        """
        Sends custom options to a specific column in the table.

        Args:
            index (int): Which column to reformat. The column index is
                given from 0 to Ncolumns-1.

        Keyword Args:
            Column options as per `EvCell.__init__`.

        Raises:
            Exception: if an invalid index is found.

        """
        if index > len(self.table):
            raise Exception("Not a valid column index")
        # we update the columns' options which means eventual width/height
        # will be 'locked in' and withstand auto-balancing width/height from the table later
        self.table[index].options.update(kwargs)
        self.table[index].reformat(**kwargs)

    def get(self):
        """
        Return lines of table as a list.

        Returns:
            table_lines (list): The lines of the table, in order.

        """
        return [line for line in self._generate_lines()]

    def __str__(self):
        """print table (this also balances it)"""
        # h = "12345678901234567890123456789012345678901234567890123456789012345678901234567890"
        return str(str(ANSIString("\n").join([line for line in self._generate_lines()])))
