"""
This module installs monkey patches to Rich, allowing it to support MXP.

MudRich system, by Volund, ported the hard way to Evennia.
"""
import html
from dataclasses import dataclass
import random
import re
from marshal import loads, dumps

from typing import Any, Dict, Iterable, List, Optional, Type, Union, Tuple

from rich.color import Color, ColorSystem

from rich.style import Style as OLD_STYLE
from rich.text import Text as OLD_TEXT, Segment, Span
from rich.console import Console as OLD_CONSOLE, ConsoleOptions as OLD_CONSOLE_OPTIONS, NoChange, NO_CHANGE
from rich.console import JustifyMethod, OverflowMethod


_RE_SQUISH = re.compile("\S+")
_RE_NOTSPACE = re.compile("[^ ]+")


class MudStyle(OLD_STYLE):
    _tag: str

    __slots__ = [
        "_tag",
        "_xml_attr",
        "_xml_attr_data"
    ]

    def __init__(
            self,
            *,
            color: Optional[Union[Color, str]] = None,
            bgcolor: Optional[Union[Color, str]] = None,
            bold: Optional[bool] = None,
            dim: Optional[bool] = None,
            italic: Optional[bool] = None,
            underline: Optional[bool] = None,
            blink: Optional[bool] = None,
            blink2: Optional[bool] = None,
            reverse: Optional[bool] = None,
            conceal: Optional[bool] = None,
            strike: Optional[bool] = None,
            underline2: Optional[bool] = None,
            frame: Optional[bool] = None,
            encircle: Optional[bool] = None,
            overline: Optional[bool] = None,
            link: Optional[str] = None,
            meta: Optional[Dict[str, Any]] = None,
            tag: Optional[str] = None,
            xml_attr: Optional[Dict] = None,
    ):
        super().__init__(color=color, bgcolor=bgcolor, bold=bold, dim=dim, italic=italic,
                         underline=underline, blink=blink, blink2=blink2, reverse=reverse,
                         conceal=conceal, strike=strike, underline2=underline2, frame=frame,
                         encircle=encircle, overline=overline, link=link, meta=meta)

        self._tag = tag
        self._xml_attr = xml_attr
        if self._xml_attr:
            self._xml_attr_data = (
                " ".join(f'{k}="{html.escape(v)}"' for k, v in xml_attr.items())
                if xml_attr
                else ""
            )
        else:
            self._xml_attr_data = ""

        self._hash = hash(
            (
                self._color,
                self._bgcolor,
                self._attributes,
                self._set_attributes,
                link,
                self._meta,
                tag,
                self._xml_attr_data
            )
        )

        self._null = not (self._set_attributes or color or bgcolor or link or meta or tag)

    @classmethod
    def upgrade(cls, old):
        return cls.parse(str(old))

    def render(
        self,
        text: str = "",
        *,
        color_system: Optional[ColorSystem] = ColorSystem.TRUECOLOR,
        legacy_windows: bool = False,
        mxp: bool = False,
        pueblo: bool = False,
        links: bool = True,
    ) -> str:
        """Render the ANSI codes for the style.

        Args:
            text (str, optional): A string to style. Defaults to "".
            color_system (Optional[ColorSystem], optional): Color system to render to. Defaults to ColorSystem.TRUECOLOR.

        Returns:
            str: A string containing ANSI style codes.
        """
        out_text = text
        if mxp:
            out_text = html.escape(out_text)
        if not out_text:
            return out_text
        if color_system is not None:
            attrs = self._make_ansi_codes(color_system)
            rendered = f"\x1b[{attrs}m{out_text}\x1b[0m" if attrs else out_text
        else:
            rendered = out_text
        if links and self._link and not legacy_windows:
            rendered = (
                f"\x1b]8;id={self._link_id};{self._link}\x1b\\{rendered}\x1b]8;;\x1b\\"
            )
        if (pueblo or mxp) and self._tag:
            if mxp:
                if self._xml_attr:
                    rendered = f"\x1b[4z<{self._tag} {self._xml_attr_data}>{rendered}\x1b[4z</{self._tag}>"
                else:
                    rendered = f"\x1b[4z<{self._tag}>{rendered}\x1b[4z</{self._tag}>"
            else:
                if self._xml_attr:
                    rendered = (
                        f"{self._tag} {self._xml_attr_data}>{rendered}</{self._tag}>"
                    )
                else:
                    rendered = f"<{self._tag}>{rendered}</{self._tag}>"
        return rendered

    def __add__(self, style: Union["Style", str]) -> "Style":
        if isinstance(style, str):
            style = self.__class__.parse(style)
        if not (isinstance(style, MudStyle) or style is None):
            return NotImplemented
        if style is None or style._null:
            return self
        if self._null:
            return style
        new_style: MudStyle = self.__new__(MudStyle)
        new_style._ansi = None
        new_style._style_definition = None
        new_style._color = style._color or self._color
        new_style._bgcolor = style._bgcolor or self._bgcolor
        new_style._attributes = (self._attributes & ~style._set_attributes) | (
            style._attributes & style._set_attributes
        )
        new_style._set_attributes = self._set_attributes | style._set_attributes
        new_style._link = style._link or self._link
        new_style._link_id = style._link_id or self._link_id

        new_style._tag = None
        if hasattr(style, "_tag") and hasattr(self, "_tag"):
            new_style._tag = style._tag or self._tag

        new_style._xml_attr = None
        if hasattr(style, "_xml_attr") and hasattr(self, "_xml_attr"):
            new_style._xml_attr = style._xml_attr or self._xml_attr

        new_style._xml_attr_data = ""
        if hasattr(style, "_xml_attr_data") and hasattr(self, "_xml_attr_data"):
            new_style._xml_attr_data = style._xml_attr_data or self._xml_attr_data

        new_style._hash = style._hash
        new_style._null = self._null or style._null
        if self._meta and style._meta:
            new_style._meta = dumps({**self.meta, **style.meta})
        else:
            new_style._meta = self._meta or style._meta

        return new_style

    def __radd__(self, other):
        if isinstance(other, str):
            other = self.__class__.parse(other)
            return other + self
        return NotImplemented


@dataclass
class MudConsoleOptions(OLD_CONSOLE_OPTIONS):
    mxp: Optional[bool] = False
    """Enable MXP/MUD HTML when printing. For MUDs only."""
    pueblo: Optional[bool] = False
    """Enable Pueblo/MUD HTML when printing. For MUDs only."""
    links: Optional[bool] = True
    """Enable ANSI Links when printing. Turn off if MXP/Pueblo is on."""

    def update(
        self,
        *,
        width: Union[int, NoChange] = NO_CHANGE,
        min_width: Union[int, NoChange] = NO_CHANGE,
        max_width: Union[int, NoChange] = NO_CHANGE,
        justify: Union[Optional[JustifyMethod], NoChange] = NO_CHANGE,
        overflow: Union[Optional[OverflowMethod], NoChange] = NO_CHANGE,
        no_wrap: Union[Optional[bool], NoChange] = NO_CHANGE,
        highlight: Union[Optional[bool], NoChange] = NO_CHANGE,
        markup: Union[Optional[bool], NoChange] = NO_CHANGE,
        height: Union[Optional[int], NoChange] = NO_CHANGE,
        mxp: Union[Optional[bool], NoChange] = NO_CHANGE,
        pueblo: Union[Optional[bool], NoChange] = NO_CHANGE,
        links: Union[Optional[bool], NoChange] = NO_CHANGE,
    ) -> "ConsoleOptions":
        """Update values, return a copy."""
        options = self.copy()
        if not isinstance(width, NoChange):
            options.min_width = options.max_width = max(0, width)
        if not isinstance(min_width, NoChange):
            options.min_width = min_width
        if not isinstance(max_width, NoChange):
            options.max_width = max_width
        if not isinstance(justify, NoChange):
            options.justify = justify
        if not isinstance(overflow, NoChange):
            options.overflow = overflow
        if not isinstance(no_wrap, NoChange):
            options.no_wrap = no_wrap
        if not isinstance(highlight, NoChange):
            options.highlight = highlight
        if not isinstance(markup, NoChange):
            options.markup = markup
        if not isinstance(height, NoChange):
            options.height = None if height is None else max(0, height)
        if not isinstance(mxp, NoChange):
            options.mxp = mxp
        if not isinstance(pueblo, NoChange):
            options.pueblo = pueblo
        if not isinstance(links, NoChange):
            options.links = links
        return options


class MudConsole(OLD_CONSOLE):

    def __init__(self, **kwargs):
        mxp = kwargs.pop("mxp", False)
        pueblo = kwargs.pop("pueblo", False)
        links = kwargs.pop("links", False)
        super().__init__(**kwargs)

        self._mxp = mxp
        self._pueblo = pueblo
        self._links = links

    def export_text(self, *, clear: bool = True, styles: bool = False) -> str:
        """Generate text from console contents (requires record=True argument in constructor).
        Args:
            clear (bool, optional): Clear record buffer after exporting. Defaults to ``True``.
            styles (bool, optional): If ``True``, ansi escape codes will be included. ``False`` for plain text.
                Defaults to ``False``.
        Returns:
            str: String containing console contents.
        """
        assert (
            self.record
        ), "To export console contents set record=True in the constructor or instance"

        with self._record_buffer_lock:
            if styles:
                text = "".join(
                    (style.render(
                        text,
                        color_system=self.color_system,
                        legacy_windows=self.legacy_windows,
                        mxp=self._mxp,
                        pueblo=self._pueblo,
                        links=self._links,
                    ) if style else text)
                    for text, style, _ in self._record_buffer
                )
            else:
                text = "".join(
                    segment.text
                    for segment in self._record_buffer
                    if not segment.control
                )
            if clear:
                del self._record_buffer[:]
        return text

    def _render_buffer(self, buffer: Iterable[Segment]) -> str:
        """Render buffered output, and clear buffer."""
        output: List[str] = []
        append = output.append
        color_system = self._color_system
        legacy_windows = self.legacy_windows
        not_terminal = not self.is_terminal
        if self.no_color and color_system:
            buffer = Segment.remove_color(buffer)
        for text, style, control in buffer:
            if style:
                append(
                    style.render(
                        text,
                        color_system=color_system,
                        legacy_windows=legacy_windows,
                        mxp=self._mxp,
                        pueblo=self._pueblo,
                        links=self._links,
                    )
                )
            elif not (not_terminal and control):
                append(text)

        rendered = "".join(output)
        return rendered


class MudText(OLD_TEXT):

    def __radd__(self, other):
        if isinstance(other, str):
            other = self.__class__(text=other)
            return other + self
        return NotImplemented

    def __iadd__(self, other: Any) -> "Text":
        if isinstance(other, (str, OLD_TEXT)):
            self.append(other)
            return self
        return NotImplemented

    def __mul__(self, other):
        if not isinstance(other, int):
            return self
        if other <= 0:
            return self.__class__()
        if other == 1:
            return self.copy()
        if other > 1:
            out = self.copy()
            for i in range(other - 1):
                out.append(self)
            return out

    def __rmul__(self, other):
        if not isinstance(other, int):
            return self
        return self * other

    def __format__(self, format_spec):
        """
        Allows use of f-strings, although styling is not preserved.
        """
        return self.plain.__format__(format_spec)

        # Begin implementing Python String Api below...

    def capitalize(self):
        return self.__class__(text=self.plain.capitalize(), style=self.style, spans=list(self.spans))

    def count(self, *args, **kwargs):
        return self.plain.count(*args, **kwargs)

    def startswith(self, *args, **kwargs):
        return self.plain.startswith(*args, **kwargs)

    def endswith(self, *args, **kwargs):
        return self.plain.endswith(*args, **kwargs)

    def find(self, *args, **kwargs):
        return self.plain.find(*args, **kwargs)

    def index(self, *args, **kwargs):
        return self.plain.index(*args, **kwargs)

    def isalnum(self):
        return self.plain.isalnum()

    def isalpha(self):
        return self.plain.isalpha()

    def isdecimal(self):
        return self.plain.isdecimal()

    def isdigit(self):
        return self.plain.isdigit()

    def isidentifier(self):
        return self.plain.isidentifier()

    def islower(self):
        return self.plain.islower()

    def isnumeric(self):
        return self.plain.isnumeric()

    def isprintable(self):
        return self.plain.isprintable()

    def isspace(self):
        return self.plain.isspace()

    def istitle(self):
        return self.plain.istitle()

    def isupper(self):
        return self.plain.isupper()

    def center(self, width, fillchar=" "):
        changed = self.plain.center(width, fillchar)
        start = changed.find(self.plain)
        lside = changed[:start]
        rside = changed[len(lside) + len(self.plain):]
        idx = self.disassemble_bits()
        new_idx = list()
        for c in lside:
            new_idx.append((None, c))
        new_idx.extend(idx)
        for c in rside:
            new_idx.append((None, c))
        return self.__class__.assemble_bits(new_idx)

    def ljust(self, width: int, fillchar: Union[str, "MudText"] = " "):
        diff = width - len(self)
        out = self.copy()
        if diff <= 0:
            return out
        else:
            if isinstance(fillchar, str):
                fillchar = self.__class__(fillchar)
            out.append(fillchar * diff)
            return out

    def rjust(self, width: int, fillchar: Union[str, "MudText"] = " "):
        diff = width - len(self)
        if diff <= 0:
            return self.copy()
        else:
            if isinstance(fillchar, str):
                fillchar = self.__class__(fillchar)
            out = fillchar * diff
            out.append(self)
            return out

    def lstrip(self, chars: str = None):
        lstripped = self.plain.lstrip(chars)
        strip_count = len(self.plain) - len(lstripped)
        return self[strip_count:]

    def strip(self, chars: str = " "):
        out_map = self.disassemble_bits()
        for i, e in enumerate(out_map):
            if e[1] != chars:
                out_map = out_map[i:]
                break
        out_map.reverse()
        for i, e in enumerate(out_map):
            if e[1] != chars:
                out_map = out_map[i:]
                break
        out_map.reverse()
        return self.__class__.assemble_bits(out_map)

    def replace(self, old: str, new: Union[str, "Text"], count=None) -> "Text":
        if not (indexes := self.find_all(old)):
            return self.clone()
        if count and count > 0:
            indexes = indexes[:count]
        old_len = len(old)
        new_len = len(new)
        other = self.clone()
        markup_idx_map = self.disassemble_bits()
        other_map = other.disassemble_bits()

        for idx in reversed(indexes):
            final_markup = markup_idx_map[idx + old_len][0]
            diff = abs(old_len - new_len)
            replace_chars = min(new_len, old_len)
            # First, replace any characters that overlap.
            for i in range(replace_chars):
                other_map[idx + i] = (markup_idx_map[idx + i][0], new[i])
            if old_len == new_len:
                pass  # the nicest case. nothing else needs doing.
            elif old_len > new_len:
                # slightly complex. pop off remaining characters.
                for i in range(diff):
                    deleted = other_map.pop(idx + new_len)
            elif new_len > old_len:
                # slightly complex. insert new characters.
                for i in range(diff):
                    other_map.insert(
                        idx + old_len + i, (final_markup, new[old_len + i])
                    )

        return self.__class__.assemble_bits(other_map)

    def find_all(self, sub: str):
        indexes = list()
        start = 0
        while True:
            start = self.plain.find(sub, start)
            if start == -1:
                return indexes
            indexes.append(start)
            start += len(sub)

    def scramble(self):
        idx = self.disassemble_bits()
        random.shuffle(idx)
        return self.__class__.assemble_bits(idx)

    def reverse(self):
        idx = self.disassemble_bits()
        idx.reverse()
        return self.__class__.assemble_bits(idx)

    @classmethod
    def assemble_bits(cls, idx: List[Tuple[Optional[Union[str, MudStyle, None]], str]]):
        out = cls()
        for i, t in enumerate(idx):
            s = [Span(0, 1, t[0])]
            out.append_text(cls(text=t[1], spans=s))
        return out

    def style_at_index(self, offset: int) -> MudStyle:
        if offset < 0:
            offset = len(self) + offset
        style = MudStyle.null()
        for start, end, span_style in self._spans:
            if end > offset >= start:
                style = style + span_style
        return style

    def disassemble_bits(self) -> List[Tuple[Optional[Union[str, MudStyle, None]], str]]:
        idx = list()
        for i, c in enumerate(self.plain):
            idx.append((self.style_at_index(i), c))
        return idx

    def squish(self) -> "MudText":
        """
        Removes leading and trailing whitespace, and coerces all internal whitespace sequences
        into at most a single space. Returns the results.
        """
        out = list()
        matches = _RE_SQUISH.finditer(self.plain)
        for match in matches:
            out.append(self[match.start(): match.end()])
        return self.__class__(" ").join(out)

    def squish_spaces(self) -> "MudText":
        """
        Like squish, but retains newlines and tabs. Just squishes spaces.
        """
        out = list()
        matches = _RE_NOTSPACE.finditer(self.plain)
        for match in matches:
            out.append(self[match.start(): match.end()])
        return self.__class__(" ").join(out)

    def serialize(self) -> dict:
        def ser_style(style):
            if isinstance(style, str):
                style = MudStyle.parse(style)
            if not isinstance(style, MudStyle):
                style = MudStyle.upgrade(style)
            return style.serialize()

        def ser_span(span):
            if not span.style:
                return None
            return {
                "start": span.start,
                "end": span.end,
                "style": ser_style(span.style),
            }

        out = {"text": self.plain}

        if self.style:
            out["style"] = ser_style(self.style)

        out_spans = [s for span in self.spans if (s := ser_span(span))]

        if out_spans:
            out["spans"] = out_spans

        return out

    @classmethod
    def deserialize(cls, data) -> "Text":
        text = data.get("text", None)
        if text is None:
            return cls("")
        style = data.get("style", None)
        if style:
            style = MudStyle(**style)

        spans = data.get("spans", None)

        if spans:
            spans = [Span(s["start"], s["end"], MudStyle(**s["style"])) for s in spans]

        return cls(text=text, style=style, spans=spans)


DEFAULT_STYLES = dict()


def install():
    from rich import style, text, console, default_styles, themes, syntax, traceback
    global DEFAULT_STYLES
    style.Style = MudStyle
    style.NULL_STYLE = MudStyle()
    text.Text = MudText
    console.Console = MudConsole
    console.ConsoleOptions = MudConsoleOptions

    traceback.Style = MudStyle
    syntax.Style = MudStyle
    traceback.Text = MudText
    syntax.Text = MudText

    for k, v in default_styles.DEFAULT_STYLES.items():
        DEFAULT_STYLES[k] = MudStyle.upgrade(v)

    for theme in syntax.RICH_SYNTAX_THEMES.values():
        for k, v in theme.items():
            if isinstance(v, OLD_STYLE):
                theme[k] = MudStyle.upgrade(v)

    default_styles.DEFAULT_STYLES = DEFAULT_STYLES
    themes.DEFAULT = themes.Theme(DEFAULT_STYLES)