"""
ANSI -> html converter

Credit for original idea and implementation
goes to Muhammad Alkarouri and his
snippet #577349 on http://code.activestate.com.

(extensively modified by Griatch 2010)
"""

import re
from html import escape as html_escape

from .ansi import *

# All xterm256 RGB equivalents

XTERM256_FG = "\033[38;5;{}m"
XTERM256_BG = "\033[48;5;{}m"


class TextToHTMLparser(object):
    """
    This class describes a parser for converting from ANSI to html.
    """

    tabstop = 4

    style_codes = [
        # non-color style markers
        ANSI_NORMAL,
        ANSI_UNDERLINE,
        ANSI_HILITE,
        ANSI_UNHILITE,
        ANSI_INVERSE,
        ANSI_BLINK,
        ANSI_INV_HILITE,
        ANSI_BLINK_HILITE,
        ANSI_INV_BLINK,
        ANSI_INV_BLINK_HILITE,
    ]

    ansi_color_codes = [
        # Foreground colors
        ANSI_BLACK,
        ANSI_RED,
        ANSI_GREEN,
        ANSI_YELLOW,
        ANSI_BLUE,
        ANSI_MAGENTA,
        ANSI_CYAN,
        ANSI_WHITE,
    ]

    xterm_fg_codes = [XTERM256_FG.format(i + 16) for i in range(240)]

    ansi_bg_codes = [
        # Background colors
        ANSI_BACK_BLACK,
        ANSI_BACK_RED,
        ANSI_BACK_GREEN,
        ANSI_BACK_YELLOW,
        ANSI_BACK_BLUE,
        ANSI_BACK_MAGENTA,
        ANSI_BACK_CYAN,
        ANSI_BACK_WHITE,
    ]

    xterm_bg_codes = [XTERM256_BG.format(i + 16) for i in range(240)]

    re_style = re.compile(
        r"({})".format(
            "|".join(
                style_codes + ansi_color_codes + xterm_fg_codes + ansi_bg_codes + xterm_bg_codes
            ).replace("[", r"\[")
        )
    )

    colorlist = (
        [ANSI_UNHILITE + code for code in ansi_color_codes]
        + [ANSI_HILITE + code for code in ansi_color_codes]
        + xterm_fg_codes
    )

    bglist = ansi_bg_codes + [ANSI_HILITE + code for code in ansi_bg_codes] + xterm_bg_codes

    re_string = re.compile(
        r"(?P<htmlchars>[<&>])|(?P<tab>[\t]+)|(?P<lineend>\r\n|\r|\n)",
        re.S | re.M | re.I,
    )
    re_url = re.compile(
        r'(?<!=")(\b(?:ftp|www|https?)\W+(?:(?!\.(?:\s|$)|&\w+;)[^"\',;$*^\\(){}<>\[\]\s])+)(\.(?:\s|$)|&\w+;|)'
    )
    re_protocol = re.compile(r"^(?:ftp|https?)://")
    re_valid_no_protocol = re.compile(
        r"^(?:www|ftp)\.[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b[-a-zA-Z0-9@:%_\+.~#?&//=]*"
    )
    re_mxplink = re.compile(r"\|lc(.*?)\|lt(.*?)\|le", re.DOTALL)
    re_mxpurl = re.compile(r"\|lu(.*?)\|lt(.*?)\|le", re.DOTALL)

    def remove_bells(self, text):
        """
        Remove ansi specials

        Args:
            text (str): Text to process.

        Returns:
            text (str): Processed text.

        """
        return text.replace(ANSI_BEEP, "")

    def remove_backspaces(self, text):
        """
        Removes special escape sequences

        Args:
            text (str): Text to process.

        Returns:
            text (str): Processed text.

        """
        backspace_or_eol = r"(.\010)|(\033\[K)"
        n = 1
        while n > 0:
            text, n = re.subn(backspace_or_eol, "", text, 1)
        return text

    def convert_linebreaks(self, text):
        """
        Extra method for cleaning linebreaks

        Args:
            text (str): Text to process.

        Returns:
            text (str): Processed text.

        """
        return text.replace("\n", r"<br>")

    def convert_urls(self, text):
        """
        Replace urls (http://...) by valid HTML.

        Args:
            text (str): Text to process.

        Returns:
            text (str): Processed text.

        """
        m = self.re_url.search(text)
        if m:
            href = m.group(1)
            label = href
            # if there is no protocol (i.e. starts with www or ftp)
            # prefix with http:// so the link isn't treated as relative
            if not self.re_protocol.match(href):
                if not self.re_valid_no_protocol.match(href):
                    return text
                href = "http://" + href
            rest = m.group(2)
            # -> added target to output prevent the web browser from attempting to
            # change pages (and losing our webclient session).
            return (
                text[: m.start()]
                + f'<a href="{href}" target="_blank">{label}</a>{rest}'
                + text[m.end() :]
            )
        else:
            return text

    def sub_mxp_links(self, match):
        """
        Helper method to be passed to re.sub,
        replaces MXP links with HTML code.

        Args:
            match (re.Matchobject): Match for substitution.

        Returns:
            text (str): Processed text.

        """
        cmd, text = [grp.replace('"', "\\&quot;") for grp in match.groups()]
        val = (
            r"""<a id="mxplink" href="#" """
            """onclick="Evennia.msg(&quot;text&quot;,[&quot;{cmd}&quot;],{{}});"""
            """return false;">{text}</a>""".format(cmd=cmd, text=text)
        )
        return val

    def sub_mxp_urls(self, match):
        """
        Helper method to be passed to re.sub,
        replaces MXP links with HTML code.
        Args:
            match (re.Matchobject): Match for substitution.
        Returns:
            text (str): Processed text.
        """
        url, text = [grp.replace('"', "\\&quot;") for grp in match.groups()]
        val = r"""<a id="mxplink" href="{url}" target="_blank">{text}</a>""".format(
            url=url, text=text
        )
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
        if cdict["htmlchars"]:
            return html_escape(cdict["htmlchars"])
        elif cdict["lineend"]:
            return "<br>"
        elif cdict["tab"]:
            text = cdict["tab"].replace("\t", " " * (self.tabstop))
            return text
        return None

    def format_styles(self, text):
        """
        Takes a string with parsed ANSI codes and replaces them with
        HTML spans and CSS classes.

        Args:
            text (str): The string to process.

        Returns:
            text (str): Processed text.
        """

        # split out the ANSI codes and clean out any empty items
        str_list = [substr for substr in self.re_style.split(text) if substr]
        # initialize all the flags and classes
        classes = []
        clean = True
        inverse = False
        # default color is light grey - unhilite + white
        hilight = ANSI_UNHILITE
        fg = ANSI_WHITE
        # default bg is black
        bg = ANSI_BACK_BLACK

        for i, substr in enumerate(str_list):
            # reset all current styling
            if substr == ANSI_NORMAL:
                # close any existing span if necessary
                str_list[i] = "</span>" if not clean else ""
                # reset to defaults
                classes = []
                clean = True
                inverse = False
                hilight = ANSI_UNHILITE
                fg = ANSI_WHITE
                bg = ANSI_BACK_BLACK

            # change color
            elif substr in self.ansi_color_codes + self.xterm_fg_codes:
                # erase ANSI code from output
                str_list[i] = ""
                # set new color
                fg = substr

            # change bg color
            elif substr in self.ansi_bg_codes + self.xterm_bg_codes:
                # erase ANSI code from output
                str_list[i] = ""
                # set new bg
                bg = substr

            # non-color codes
            elif substr in self.style_codes:
                # erase ANSI code from output
                str_list[i] = ""

                # hilight codes
                if substr in (ANSI_HILITE, ANSI_UNHILITE, ANSI_INV_HILITE, ANSI_INV_BLINK_HILITE):
                    # set new hilight status
                    hilight = ANSI_UNHILITE if substr == ANSI_UNHILITE else ANSI_HILITE

                # inversion codes
                if substr in (ANSI_INVERSE, ANSI_INV_HILITE, ANSI_INV_BLINK_HILITE):
                    inverse = True

                # blink codes
                if (
                    substr in (ANSI_BLINK, ANSI_BLINK_HILITE, ANSI_INV_BLINK_HILITE)
                    and "blink" not in classes
                ):
                    classes.append("blink")

                # underline
                if substr == ANSI_UNDERLINE and "underline" not in classes:
                    classes.append("underline")

            else:
                # normal text, add text back to list
                if not str_list[i - 1]:
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
                        classes.append(bg_class)
                    # light grey text is the default, don't explicitly style
                    if color_class != "color-007":
                        classes.append(color_class)
                    # define the new style span
                    prefix = '<span class="{}">'.format(" ".join(classes))
                    # close any prior span
                    if not clean:
                        prefix = "</span>" + prefix
                    # add span to output
                    str_list[i - 1] = prefix

                    # clean out color classes to easily update next time
                    classes = [cls for cls in classes if "color" not in cls]
                    # flag as currently being styled
                    clean = False

        # close span if necessary
        if not clean:
            str_list.append("</span>")
        # recombine back into string
        return "".join(str_list)

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
        result = self.convert_linebreaks(result)
        result = self.remove_backspaces(result)
        result = self.convert_urls(result)
        # clean out eventual ansi that was missed
        ## result = parse_ansi(result, strip_ansi=True)

        return result


HTML_PARSER = TextToHTMLparser()


#
# Access function
#


def parse_html(string, strip_ansi=False, parser=HTML_PARSER):
    """
    Parses a string, replace ANSI markup with html
    """
    return parser.parse(string, strip_ansi=strip_ansi)
