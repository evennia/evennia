"""
Godot Websocket - ChrisLR 2022

This file contains the necessary code and data to convert text with color tags to bbcode (For godot)
"""
from evennia.utils.ansi import *
from evennia.utils.text2html import TextToHTMLparser

# All xterm256 RGB equivalents

XTERM256_FG = "\033[38;5;{}m"
XTERM256_BG = "\033[48;5;{}m"

COLOR_INDICE_TO_HEX = {
    "color-000": "#000000",
    "color-001": "#800000",
    "color-002": "#008000",
    "color-003": "#808000",
    "color-004": "#000080",
    "color-005": "#800080",
    "color-006": "#008080",
    "color-007": "#c0c0c0",
    "color-008": "#808080",
    "color-009": "#ff0000",
    "color-010": "#00ff00",
    "color-011": "#ffff00",
    "color-012": "#0000ff",
    "color-013": "#ff00ff",
    "color-014": "#00ffff",
    "color-015": "#ffffff",
    "color-016": "#000000",
    "color-017": "#00005f",
    "color-018": "#000087",
    "color-019": "#0000af",
    "color-020": "#0000df",
    "color-021": "#0000ff",
    "color-022": "#005f00",
    "color-023": "#005f5f",
    "color-024": "#005f87",
    "color-025": "#005faf",
    "color-026": "#005fdf",
    "color-027": "#005fff",
    "color-028": "#008700",
    "color-029": "#00875f",
    "color-030": "#008787",
    "color-031": "#0087af",
    "color-032": "#0087df",
    "color-033": "#0087ff",
    "color-034": "#00af00",
    "color-035": "#00af5f",
    "color-036": "#00af87",
    "color-037": "#00afaf",
    "color-038": "#00afdf",
    "color-039": "#00afff",
    "color-040": "#00df00",
    "color-041": "#00df5f",
    "color-042": "#00df87",
    "color-043": "#00dfaf",
    "color-044": "#00dfdf",
    "color-045": "#00dfff",
    "color-046": "#00ff00",
    "color-047": "#00ff5f",
    "color-048": "#00ff87",
    "color-049": "#00ffaf",
    "color-050": "#00ffdf",
    "color-051": "#00ffff",
    "color-052": "#5f0000",
    "color-053": "#5f005f",
    "color-054": "#5f0087",
    "color-055": "#5f00af",
    "color-056": "#5f00df",
    "color-057": "#5f00ff",
    "color-058": "#5f5f00",
    "color-059": "#5f5f5f",
    "color-060": "#5f5f87",
    "color-061": "#5f5faf",
    "color-062": "#5f5fdf",
    "color-063": "#5f5fff",
    "color-064": "#5f8700",
    "color-065": "#5f875f",
    "color-066": "#5f8787",
    "color-067": "#5f87af",
    "color-068": "#5f87df",
    "color-069": "#5f87ff",
    "color-070": "#5faf00",
    "color-071": "#5faf5f",
    "color-072": "#5faf87",
    "color-073": "#5fafaf",
    "color-074": "#5fafdf",
    "color-075": "#5fafff",
    "color-076": "#5fdf00",
    "color-077": "#5fdf5f",
    "color-078": "#5fdf87",
    "color-079": "#5fdfaf",
    "color-080": "#5fdfdf",
    "color-081": "#5fdfff",
    "color-082": "#5fff00",
    "color-083": "#5fff5f",
    "color-084": "#5fff87",
    "color-085": "#5fffaf",
    "color-086": "#5fffdf",
    "color-087": "#5fffff",
    "color-088": "#870000",
    "color-089": "#87005f",
    "color-090": "#870087",
    "color-091": "#8700af",
    "color-092": "#8700df",
    "color-093": "#8700ff",
    "color-094": "#875f00",
    "color-095": "#875f5f",
    "color-096": "#875f87",
    "color-097": "#875faf",
    "color-098": "#875fdf",
    "color-099": "#875fff",
    "color-100": "#878700",
    "color-101": "#87875f",
    "color-102": "#878787",
    "color-103": "#8787af",
    "color-104": "#8787df",
    "color-105": "#8787ff",
    "color-106": "#87af00",
    "color-107": "#87af5f",
    "color-108": "#87af87",
    "color-109": "#87afaf",
    "color-110": "#87afdf",
    "color-111": "#87afff",
    "color-112": "#87df00",
    "color-113": "#87df5f",
    "color-114": "#87df87",
    "color-115": "#87dfaf",
    "color-116": "#87dfdf",
    "color-117": "#87dfff",
    "color-118": "#87ff00",
    "color-119": "#87ff5f",
    "color-120": "#87ff87",
    "color-121": "#87ffaf",
    "color-122": "#87ffdf",
    "color-123": "#87ffff",
    "color-124": "#af0000",
    "color-125": "#af005f",
    "color-126": "#af0087",
    "color-127": "#af00af",
    "color-128": "#af00df",
    "color-129": "#af00ff",
    "color-130": "#af5f00",
    "color-131": "#af5f5f",
    "color-132": "#af5f87",
    "color-133": "#af5faf",
    "color-134": "#af5fdf",
    "color-135": "#af5fff",
    "color-136": "#af8700",
    "color-137": "#af875f",
    "color-138": "#af8787",
    "color-139": "#af87af",
    "color-140": "#af87df",
    "color-141": "#af87ff",
    "color-142": "#afaf00",
    "color-143": "#afaf5f",
    "color-144": "#afaf87",
    "color-145": "#afafaf",
    "color-146": "#afafdf",
    "color-147": "#afafff",
    "color-148": "#afdf00",
    "color-149": "#afdf5f",
    "color-150": "#afdf87",
    "color-151": "#afdfaf",
    "color-152": "#afdfdf",
    "color-153": "#afdfff",
    "color-154": "#afff00",
    "color-155": "#afff5f",
    "color-156": "#afff87",
    "color-157": "#afffaf",
    "color-158": "#afffdf",
    "color-159": "#afffff",
    "color-160": "#df0000",
    "color-161": "#df005f",
    "color-162": "#df0087",
    "color-163": "#df00af",
    "color-164": "#df00df",
    "color-165": "#df00ff",
    "color-166": "#df5f00",
    "color-167": "#df5f5f",
    "color-168": "#df5f87",
    "color-169": "#df5faf",
    "color-170": "#df5fdf",
    "color-171": "#df5fff",
    "color-172": "#df8700",
    "color-173": "#df875f",
    "color-174": "#df8787",
    "color-175": "#df87af",
    "color-176": "#df87df",
    "color-177": "#df87ff",
    "color-178": "#dfaf00",
    "color-179": "#dfaf5f",
    "color-180": "#dfaf87",
    "color-181": "#dfafaf",
    "color-182": "#dfafdf",
    "color-183": "#dfafff",
    "color-184": "#dfdf00",
    "color-185": "#dfdf5f",
    "color-186": "#dfdf87",
    "color-187": "#dfdfaf",
    "color-188": "#dfdfdf",
    "color-189": "#dfdfff",
    "color-190": "#dfff00",
    "color-191": "#dfff5f",
    "color-192": "#dfff87",
    "color-193": "#dfffaf",
    "color-194": "#dfffdf",
    "color-195": "#dfffff",
    "color-196": "#ff0000",
    "color-197": "#ff005f",
    "color-198": "#ff0087",
    "color-199": "#ff00af",
    "color-200": "#ff00df",
    "color-201": "#ff00ff",
    "color-202": "#ff5f00",
    "color-203": "#ff5f5f",
    "color-204": "#ff5f87",
    "color-205": "#ff5faf",
    "color-206": "#ff5fdf",
    "color-207": "#ff5fff",
    "color-208": "#ff8700",
    "color-209": "#ff875f",
    "color-210": "#ff8787",
    "color-211": "#ff87af",
    "color-212": "#ff87df",
    "color-213": "#ff87ff",
    "color-214": "#ffaf00",
    "color-215": "#ffaf5f",
    "color-216": "#ffaf87",
    "color-217": "#ffafaf",
    "color-218": "#ffafdf",
    "color-219": "#ffafff",
    "color-220": "#ffdf00",
    "color-221": "#ffdf5f",
    "color-222": "#ffdf87",
    "color-223": "#ffdfaf",
    "color-224": "#ffdfdf",
    "color-225": "#ffdfff",
    "color-226": "#ffff00",
    "color-227": "#ffff5f",
    "color-228": "#ffff87",
    "color-229": "#ffffaf",
    "color-230": "#ffffdf",
    "color-231": "#ffffff",
    "color-232": "#080808",
    "color-233": "#121212",
    "color-234": "#1c1c1c",
    "color-235": "#262626",
    "color-236": "#303030",
    "color-237": "#3a3a3a",
    "color-238": "#444444",
    "color-239": "#4e4e4e",
    "color-240": "#585858",
    "color-241": "#606060",
    "color-242": "#666666",
    "color-243": "#767676",
    "color-244": "#808080",
    "color-245": "#8a8a8a",
    "color-246": "#949494",
    "color-247": "#9e9e9e",
    "color-248": "#a8a8a8",
    "color-249": "#b2b2b2",
    "color-250": "#bcbcbc",
    "color-251": "#c6c6c6",
    "color-252": "#d0d0d0",
    "color-253": "#dadada",
    "color-254": "#e4e4e4",
    "color-255": "#eeeeee",
    "bgcolor-000": "#000000",
    "bgcolor-001": "#800000",
    "bgcolor-002": "#008000",
    "bgcolor-003": "#808000",
    "bgcolor-004": "#000080",
    "bgcolor-005": "#800080",
    "bgcolor-006": "#008080",
    "bgcolor-007": "#c0c0c0",
    "bgcolor-008": "#808080",
    "bgcolor-009": "#ff0000",
    "bgcolor-010": "#00ff00",
    "bgcolor-011": "#ffff00",
    "bgcolor-012": "#0000ff",
    "bgcolor-013": "#ff00ff",
    "bgcolor-014": "#00ffff",
    "bgcolor-015": "#ffffff",
    "bgcolor-016": "#000000",
    "bgcolor-017": "#00005f",
    "bgcolor-018": "#000087",
    "bgcolor-019": "#0000af",
    "bgcolor-020": "#0000df",
    "bgcolor-021": "#0000ff",
    "bgcolor-022": "#005f00",
    "bgcolor-023": "#005f5f",
    "bgcolor-024": "#005f87",
    "bgcolor-025": "#005faf",
    "bgcolor-026": "#005fdf",
    "bgcolor-027": "#005fff",
    "bgcolor-028": "#008700",
    "bgcolor-029": "#00875f",
    "bgcolor-030": "#008787",
    "bgcolor-031": "#0087af",
    "bgcolor-032": "#0087df",
    "bgcolor-033": "#0087ff",
    "bgcolor-034": "#00af00",
    "bgcolor-035": "#00af5f",
    "bgcolor-036": "#00af87",
    "bgcolor-037": "#00afaf",
    "bgcolor-038": "#00afdf",
    "bgcolor-039": "#00afff",
    "bgcolor-040": "#00df00",
    "bgcolor-041": "#00df5f",
    "bgcolor-042": "#00df87",
    "bgcolor-043": "#00dfaf",
    "bgcolor-044": "#00dfdf",
    "bgcolor-045": "#00dfff",
    "bgcolor-046": "#00ff00",
    "bgcolor-047": "#00ff5f",
    "bgcolor-048": "#00ff87",
    "bgcolor-049": "#00ffaf",
    "bgcolor-050": "#00ffdf",
    "bgcolor-051": "#00ffff",
    "bgcolor-052": "#5f0000",
    "bgcolor-053": "#5f005f",
    "bgcolor-054": "#5f0087",
    "bgcolor-055": "#5f00af",
    "bgcolor-056": "#5f00df",
    "bgcolor-057": "#5f00ff",
    "bgcolor-058": "#5f5f00",
    "bgcolor-059": "#5f5f5f",
    "bgcolor-060": "#5f5f87",
    "bgcolor-061": "#5f5faf",
    "bgcolor-062": "#5f5fdf",
    "bgcolor-063": "#5f5fff",
    "bgcolor-064": "#5f8700",
    "bgcolor-065": "#5f875f",
    "bgcolor-066": "#5f8787",
    "bgcolor-067": "#5f87af",
    "bgcolor-068": "#5f87df",
    "bgcolor-069": "#5f87ff",
    "bgcolor-070": "#5faf00",
    "bgcolor-071": "#5faf5f",
    "bgcolor-072": "#5faf87",
    "bgcolor-073": "#5fafaf",
    "bgcolor-074": "#5fafdf",
    "bgcolor-075": "#5fafff",
    "bgcolor-076": "#5fdf00",
    "bgcolor-077": "#5fdf5f",
    "bgcolor-078": "#5fdf87",
    "bgcolor-079": "#5fdfaf",
    "bgcolor-080": "#5fdfdf",
    "bgcolor-081": "#5fdfff",
    "bgcolor-082": "#5fff00",
    "bgcolor-083": "#5fff5f",
    "bgcolor-084": "#5fff87",
    "bgcolor-085": "#5fffaf",
    "bgcolor-086": "#5fffdf",
    "bgcolor-087": "#5fffff",
    "bgcolor-088": "#870000",
    "bgcolor-089": "#87005f",
    "bgcolor-090": "#870087",
    "bgcolor-091": "#8700af",
    "bgcolor-092": "#8700df",
    "bgcolor-093": "#8700ff",
    "bgcolor-094": "#875f00",
    "bgcolor-095": "#875f5f",
    "bgcolor-096": "#875f87",
    "bgcolor-097": "#875faf",
    "bgcolor-098": "#875fdf",
    "bgcolor-099": "#875fff",
    "bgcolor-100": "#878700",
    "bgcolor-101": "#87875f",
    "bgcolor-102": "#878787",
    "bgcolor-103": "#8787af",
    "bgcolor-104": "#8787df",
    "bgcolor-105": "#8787ff",
    "bgcolor-106": "#87af00",
    "bgcolor-107": "#87af5f",
    "bgcolor-108": "#87af87",
    "bgcolor-109": "#87afaf",
    "bgcolor-110": "#87afdf",
    "bgcolor-111": "#87afff",
    "bgcolor-112": "#87df00",
    "bgcolor-113": "#87df5f",
    "bgcolor-114": "#87df87",
    "bgcolor-115": "#87dfaf",
    "bgcolor-116": "#87dfdf",
    "bgcolor-117": "#87dfff",
    "bgcolor-118": "#87ff00",
    "bgcolor-119": "#87ff5f",
    "bgcolor-120": "#87ff87",
    "bgcolor-121": "#87ffaf",
    "bgcolor-122": "#87ffdf",
    "bgcolor-123": "#87ffff",
    "bgcolor-124": "#af0000",
    "bgcolor-125": "#af005f",
    "bgcolor-126": "#af0087",
    "bgcolor-127": "#af00af",
    "bgcolor-128": "#af00df",
    "bgcolor-129": "#af00ff",
    "bgcolor-130": "#af5f00",
    "bgcolor-131": "#af5f5f",
    "bgcolor-132": "#af5f87",
    "bgcolor-133": "#af5faf",
    "bgcolor-134": "#af5fdf",
    "bgcolor-135": "#af5fff",
    "bgcolor-136": "#af8700",
    "bgcolor-137": "#af875f",
    "bgcolor-138": "#af8787",
    "bgcolor-139": "#af87af",
    "bgcolor-140": "#af87df",
    "bgcolor-141": "#af87ff",
    "bgcolor-142": "#afaf00",
    "bgcolor-143": "#afaf5f",
    "bgcolor-144": "#afaf87",
    "bgcolor-145": "#afafaf",
    "bgcolor-146": "#afafdf",
    "bgcolor-147": "#afafff",
    "bgcolor-148": "#afdf00",
    "bgcolor-149": "#afdf5f",
    "bgcolor-150": "#afdf87",
    "bgcolor-151": "#afdfaf",
    "bgcolor-152": "#afdfdf",
    "bgcolor-153": "#afdfff",
    "bgcolor-154": "#afff00",
    "bgcolor-155": "#afff5f",
    "bgcolor-156": "#afff87",
    "bgcolor-157": "#afffaf",
    "bgcolor-158": "#afffdf",
    "bgcolor-159": "#afffff",
    "bgcolor-160": "#df0000",
    "bgcolor-161": "#df005f",
    "bgcolor-162": "#df0087",
    "bgcolor-163": "#df00af",
    "bgcolor-164": "#df00df",
    "bgcolor-165": "#df00ff",
    "bgcolor-166": "#df5f00",
    "bgcolor-167": "#df5f5f",
    "bgcolor-168": "#df5f87",
    "bgcolor-169": "#df5faf",
    "bgcolor-170": "#df5fdf",
    "bgcolor-171": "#df5fff",
    "bgcolor-172": "#df8700",
    "bgcolor-173": "#df875f",
    "bgcolor-174": "#df8787",
    "bgcolor-175": "#df87af",
    "bgcolor-176": "#df87df",
    "bgcolor-177": "#df87ff",
    "bgcolor-178": "#dfaf00",
    "bgcolor-179": "#dfaf5f",
    "bgcolor-180": "#dfaf87",
    "bgcolor-181": "#dfafaf",
    "bgcolor-182": "#dfafdf",
    "bgcolor-183": "#dfafff",
    "bgcolor-184": "#dfdf00",
    "bgcolor-185": "#dfdf5f",
    "bgcolor-186": "#dfdf87",
    "bgcolor-187": "#dfdfaf",
    "bgcolor-188": "#dfdfdf",
    "bgcolor-189": "#dfdfff",
    "bgcolor-190": "#dfff00",
    "bgcolor-191": "#dfff5f",
    "bgcolor-192": "#dfff87",
    "bgcolor-193": "#dfffaf",
    "bgcolor-194": "#dfffdf",
    "bgcolor-195": "#dfffff",
    "bgcolor-196": "#ff0000",
    "bgcolor-197": "#ff005f",
    "bgcolor-198": "#ff0087",
    "bgcolor-199": "#ff00af",
    "bgcolor-200": "#ff00df",
    "bgcolor-201": "#ff00ff",
    "bgcolor-202": "#ff5f00",
    "bgcolor-203": "#ff5f5f",
    "bgcolor-204": "#ff5f87",
    "bgcolor-205": "#ff5faf",
    "bgcolor-206": "#ff5fdf",
    "bgcolor-207": "#ff5fff",
    "bgcolor-208": "#ff8700",
    "bgcolor-209": "#ff875f",
    "bgcolor-210": "#ff8787",
    "bgcolor-211": "#ff87af",
    "bgcolor-212": "#ff87df",
    "bgcolor-213": "#ff87ff",
    "bgcolor-214": "#ffaf00",
    "bgcolor-215": "#ffaf5f",
    "bgcolor-216": "#ffaf87",
    "bgcolor-217": "#ffafaf",
    "bgcolor-218": "#ffafdf",
    "bgcolor-219": "#ffafff",
    "bgcolor-220": "#ffdf00",
    "bgcolor-221": "#ffdf5f",
    "bgcolor-222": "#ffdf87",
    "bgcolor-223": "#ffdfaf",
    "bgcolor-224": "#ffdfdf",
    "bgcolor-225": "#ffdfff",
    "bgcolor-226": "#ffff00",
    "bgcolor-227": "#ffff5f",
    "bgcolor-228": "#ffff87",
    "bgcolor-229": "#ffffaf",
    "bgcolor-230": "#ffffdf",
    "bgcolor-231": "#ffffff",
    "bgcolor-232": "#080808",
    "bgcolor-233": "#121212",
    "bgcolor-234": "#1c1c1c",
    "bgcolor-235": "#262626",
    "bgcolor-236": "#303030",
    "bgcolor-237": "#3a3a3a",
    "bgcolor-238": "#444444",
    "bgcolor-239": "#4e4e4e",
    "bgcolor-240": "#585858",
    "bgcolor-241": "#606060",
    "bgcolor-242": "#666666",
    "bgcolor-243": "#767676",
    "bgcolor-244": "#808080",
    "bgcolor-245": "#8a8a8a",
    "bgcolor-246": "#949494",
    "bgcolor-247": "#9e9e9e",
    "bgcolor-248": "#a8a8a8",
    "bgcolor-249": "#b2b2b2",
    "bgcolor-250": "#bcbcbc",
    "bgcolor-251": "#c6c6c6",
    "bgcolor-252": "#d0d0d0",
    "bgcolor-253": "#dadada",
    "bgcolor-254": "#e4e4e4",
    "bgcolor-255": "#eeeeee",
}


"""
The classes below exist to properly encapsulate text and other tag classes
because the order of how tags are opened and closed are important to display in godot.
"""


class RootTag:
    """
    The Root tag class made to contain other tags.
    """

    __slots__ = ("child",)

    def __init__(self):
        self.child = None

    def __str__(self):
        return str(self.child) if self.child else ""


class ChildTag:
    """
    A node made to be contained.
    """

    def __init__(self, parent):
        self.parent = parent
        if parent:
            parent.child = self

    def set_parent(self, parent):
        self.parent = parent
        if parent:
            parent.child = self


class TextTag(ChildTag):
    """
    A BBCodeTag node to output regular text.
    Output: SomeText
    """

    __slots__ = ("parent", "child", "text")

    def __init__(self, parent, text):
        super().__init__(parent)
        self.text = text
        self.child = None

    def __str__(self):
        return f"{self.text}{self.child or ''}"


class BBCodeTag(ChildTag):
    """
    Base BBCodeTag node to encapsulate and be encapsulated.
    """

    __slots__ = (
        "parent",
        "child",
    )

    code = ""

    def __init__(self, parent):
        super().__init__(parent)
        self.child = None

    def __str__(self):
        return f"[{self.code}]{self.child or ''}[/{self.code}]"


class UnderlineTag(BBCodeTag):
    """
    A BBCodeTag node for underlined text.
    Output: [u]Underlined Text[/u]
    """

    code = "u"


class BlinkTag(BBCodeTag):
    """
    A BBCodeTag node for blinking text.
    Output: [blink]Blinking Text[/blink]
    """

    code = "blink"


class ColorTag(BBCodeTag):
    """
    A BBCodeTag node for foreground color.
    Output: [fgcolor=#000000]Colorized Text[/fgcolor]
    """

    __slots__ = (
        "parent",
        "child",
        "color_hex",
    )

    code = "color"

    def __init__(self, parent, color_hex):
        super().__init__(parent)
        self.color_hex = color_hex

    def __str__(self):
        return f"[{self.code}={self.color_hex}]{self.child or ''}[/{self.code}]"


class BGColorTag(ColorTag):
    """
    A BBCodeTag node for background color.
    Output: [bgcolor=#000000]Colorized Text[/bgcolor]
    """

    code = "bgcolor"


class UrlTag(BBCodeTag):
    """
    A BBCodeTag node used for urls.
    Output: [url=www.example.com]Child Text[/url]

    """

    __slots__ = (
        "parent",
        "child",
        "url_data",
    )

    code = "url"

    def __init__(self, parent, url_data=""):
        super().__init__(parent)
        self.url_data = url_data

    def __str__(self):
        return f"[{self.code}={self.url_data}]{self.child or ''}[/{self.code}]"


class TextToBBCODEparser(TextToHTMLparser):
    """
    This class describes a parser for converting from ANSI to BBCode.
    It inherits from the TextToHTMLParser and overrides the specifics for bbcode.
    """

    def convert_urls(self, text):
        """
        Converts urls within text to bbcode style

        Args:
            text (str): Text to parse

        Returns:
             text (str): Processed text
        """
        # Converts to bbcode styled urls
        return self.re_url.sub(r"[url=\1]\1[/url]\2", text)

    def sub_mxp_links(self, match):
        """
        Helper method to be passed to re.sub,
        replaces MXP links with bbcode.

        Args:
            match (re.Matchobject): Match for substitution.

        Returns:
            text (str): Processed text.

        """
        cmd, text = [grp.replace('"', "\\&quot;") for grp in match.groups()]
        val = f"[mxp=send cmd={cmd}]{text}[/mxp]"

        return val

    def sub_mxp_urls(self, match):
        """
        Helper method to be passed to re.sub,
        replaces MXP links with bbcode.
        Args:
            match (re.Matchobject): Match for substitution.
        Returns:
            text (str): Processed text.
        """

        url, text = [grp.replace('"', "\\&quot;") for grp in match.groups()]
        val = f"[url={url}]{text}[/url]"

        return val

    def sub_text(self, match):
        """
        Helper method to be passed to re.sub,
        for handling all substitutions.

        Args:
            match (re.Matchobject): Match for substitution.

        Returns:
            text (str): Processed text.

        """
        cdict = match.groupdict()
        if cdict["lineend"]:
            return "\n"

        return None

    def format_styles(self, text):
        """
        Takes a string with parsed ANSI codes and replaces them with bbcode style tags

        Args:
            text (str): The string to process.

        Returns:
            text (str): Processed text.
        """

        # split out the ANSI codes and clean out any empty items
        str_list = [substr for substr in self.re_style.split(text) if substr]

        inverse = False
        # default color is light grey - unhilite + white
        hilight = ANSI_UNHILITE
        fg = ANSI_WHITE
        # default bg is black
        bg = ANSI_BACK_BLACK
        previous_fg = None
        previous_bg = None
        blink = False
        underline = False
        new_style = False

        parts = []
        root_tag = RootTag()
        current_tag = root_tag

        for i, substr in enumerate(str_list):
            # reset all current styling
            if substr == ANSI_NORMAL:
                # close any existing span if necessary
                parts.append(str(root_tag))
                root_tag = RootTag()
                current_tag = root_tag
                # reset to defaults
                inverse = False
                hilight = ANSI_UNHILITE
                fg = ANSI_WHITE
                bg = ANSI_BACK_BLACK
                previous_fg = None
                previous_bg = None
                blink = False
                underline = False
                new_style = False

            # change color
            elif substr in self.ansi_color_codes + self.xterm_fg_codes:
                # set new color
                fg = substr
                new_style = True

            # change bg color
            elif substr in self.ansi_bg_codes + self.xterm_bg_codes:
                # set new bg
                bg = substr
                new_style = True

            # non-color codes
            elif substr in self.style_codes:
                new_style = True

                # hilight codes
                if substr in (ANSI_HILITE, ANSI_UNHILITE, ANSI_INV_HILITE, ANSI_INV_BLINK_HILITE):
                    # set new hilight status
                    hilight = ANSI_UNHILITE if substr == ANSI_UNHILITE else ANSI_HILITE

                # inversion codes
                if substr in (ANSI_INVERSE, ANSI_INV_HILITE, ANSI_INV_BLINK_HILITE):
                    inverse = True

                # blink codes
                if substr in (ANSI_BLINK, ANSI_BLINK_HILITE, ANSI_INV_BLINK_HILITE) and not blink:
                    blink = True
                    current_tag = BlinkTag(current_tag)

                # underline
                if substr == ANSI_UNDERLINE and not underline:
                    underline = True
                    current_tag = UnderlineTag(current_tag)

            else:
                close_tags = False
                color_tag = None
                bgcolor_tag = None
                # normal text, add text back to list
                if new_style:
                    # prior entry was cleared, which means style change
                    # get indices for the fg and bg codes
                    bg_index = self.bglist.index(bg)
                    try:
                        color_index = self.colorlist.index(hilight + fg)
                    except ValueError:
                        # xterm256 colors don't have the hilight codes
                        color_index = self.colorlist.index(fg)

                    if inverse:
                        # inverse means swap fg and bg indices
                        bg_class = "bgcolor-{}".format(str(color_index).rjust(3, "0"))
                        color_class = "color-{}".format(str(bg_index).rjust(3, "0"))
                    else:
                        # use fg and bg indices for classes
                        bg_class = "bgcolor-{}".format(str(bg_index).rjust(3, "0"))
                        color_class = "color-{}".format(str(color_index).rjust(3, "0"))

                    # black bg is the default, don't explicitly style
                    if bg_class != "bgcolor-000":
                        color_hex = COLOR_INDICE_TO_HEX.get(bg_class)
                        bgcolor_tag = BGColorTag(None, color_hex=color_hex)
                        if previous_bg and previous_bg != color_hex:
                            close_tags = True
                        else:
                            previous_bg = color_hex

                    # light grey text is the default, don't explicitly style
                    if color_class != "color-007":
                        color_hex = COLOR_INDICE_TO_HEX.get(color_class)
                        color_tag = ColorTag(None, color_hex=color_hex)
                        if previous_fg and previous_fg != color_hex:
                            close_tags = True
                        else:
                            previous_fg = color_hex

                new_tag = TextTag(None, substr)
                if close_tags:
                    # Because the order is important, we need to close the tags and reopen those who shouldn't reset.
                    new_style = False
                    parts.append(str(root_tag))
                    root_tag = RootTag()
                    current_tag = root_tag
                    if blink:
                        current_tag = BlinkTag(current_tag)

                    if underline:
                        current_tag = UnderlineTag(current_tag)

                    if bgcolor_tag:
                        bgcolor_tag.set_parent(current_tag)
                        current_tag = bgcolor_tag

                    if color_tag:
                        color_tag.set_parent(current_tag)
                        current_tag = color_tag

                    new_tag.set_parent(current_tag)
                    current_tag = new_tag
                else:
                    if bgcolor_tag:
                        bgcolor_tag.set_parent(current_tag)
                        current_tag = bgcolor_tag

                    if color_tag:
                        color_tag.set_parent(current_tag)
                        current_tag = color_tag

                    new_tag.set_parent(current_tag)
                    current_tag = new_tag

        any_text = self._get_text_tag(root_tag)
        if any_text:
            # Only append tags if text was added.
            last_part = str(root_tag)
            parts.append(last_part)

        # recombine back into string
        return "".join(parts)

    def _get_text_tag(self, root):
        child = root.child
        while child:
            if isinstance(child, TextTag):
                return child
            else:
                child = child.child

        return None

    def parse(self, text, strip_ansi=False):
        """
        Main access function, converts a text containing ANSI codes
        into html statements.

        Args:
            text (str): Text to process.
            strip_ansi (bool, optional):

        Returns:
            text (str): Parsed text.

        """
        # parse everything to ansi first
        text = parse_ansi(text, strip_ansi=strip_ansi, xterm256=True, mxp=True)
        # convert all ansi to html
        result = re.sub(self.re_string, self.sub_text, text)
        result = re.sub(self.re_mxplink, self.sub_mxp_links, result)
        result = re.sub(self.re_mxpurl, self.sub_mxp_urls, result)
        result = self.remove_bells(result)
        result = self.format_styles(result)
        result = self.remove_backspaces(result)
        result = self.convert_urls(result)

        return result


BBCODE_PARSER = TextToBBCODEparser()


#
# Access function
#


def parse_to_bbcode(string, strip_ansi=False, parser=BBCODE_PARSER):
    """
    Parses a string, replace ANSI markup with bbcode
    """
    return parser.parse(string, strip_ansi=strip_ansi)
