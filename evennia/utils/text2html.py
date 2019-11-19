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

XTERM256_FG = "\033[38;5;%sm"
XTERM256_BG = "\033[48;5;%sm"


class TextToHTMLparser(object):
    """
    This class describes a parser for converting from ANSI to html.
    """

    tabstop = 4
    # mapping html color name <-> ansi code.
    hilite = ANSI_HILITE
    unhilite = ANSI_UNHILITE  # this will be stripped - there is no css equivalent.
    normal = ANSI_NORMAL  # "
    underline = ANSI_UNDERLINE
    blink = ANSI_BLINK
    inverse = ANSI_INVERSE  # this will produce an outline; no obvious css equivalent?
    colorcodes = [
        ("color-000", unhilite + ANSI_BLACK),  # pure black
        ("color-001", unhilite + ANSI_RED),
        ("color-002", unhilite + ANSI_GREEN),
        ("color-003", unhilite + ANSI_YELLOW),
        ("color-004", unhilite + ANSI_BLUE),
        ("color-005", unhilite + ANSI_MAGENTA),
        ("color-006", unhilite + ANSI_CYAN),
        ("color-007", unhilite + ANSI_WHITE),  # light grey
        ("color-008", hilite + ANSI_BLACK),  # dark grey
        ("color-009", hilite + ANSI_RED),
        ("color-010", hilite + ANSI_GREEN),
        ("color-011", hilite + ANSI_YELLOW),
        ("color-012", hilite + ANSI_BLUE),
        ("color-013", hilite + ANSI_MAGENTA),
        ("color-014", hilite + ANSI_CYAN),
        ("color-015", hilite + ANSI_WHITE),  # pure white
    ] + [("color-%03i" % (i + 16), XTERM256_FG % ("%i" % (i + 16))) for i in range(240)]

    colorback = [
        ("bgcolor-000", ANSI_BACK_BLACK),  # pure black
        ("bgcolor-001", ANSI_BACK_RED),
        ("bgcolor-002", ANSI_BACK_GREEN),
        ("bgcolor-003", ANSI_BACK_YELLOW),
        ("bgcolor-004", ANSI_BACK_BLUE),
        ("bgcolor-005", ANSI_BACK_MAGENTA),
        ("bgcolor-006", ANSI_BACK_CYAN),
        ("bgcolor-007", ANSI_BACK_WHITE),  # light grey
        ("bgcolor-008", hilite + ANSI_BACK_BLACK),  # dark grey
        ("bgcolor-009", hilite + ANSI_BACK_RED),
        ("bgcolor-010", hilite + ANSI_BACK_GREEN),
        ("bgcolor-011", hilite + ANSI_BACK_YELLOW),
        ("bgcolor-012", hilite + ANSI_BACK_BLUE),
        ("bgcolor-013", hilite + ANSI_BACK_MAGENTA),
        ("bgcolor-014", hilite + ANSI_BACK_CYAN),
        ("bgcolor-015", hilite + ANSI_BACK_WHITE),  # pure white
    ] + [("bgcolor-%03i" % (i + 16), XTERM256_BG % ("%i" % (i + 16))) for i in range(240)]

    # make sure to escape [
    # colorcodes = [(c, code.replace("[", r"\[")) for c, code in colorcodes]
    # colorback = [(c, code.replace("[", r"\[")) for c, code in colorback]
    fg_colormap = dict((code, clr) for clr, code in colorcodes)
    bg_colormap = dict((code, clr) for clr, code in colorback)

    # create stop markers
    fgstop = "(?:\033\[1m|\033\[22m){0,1}\033\[3[0-8].*?m|\033\[0m|$"
    bgstop = "(?:\033\[1m|\033\[22m){0,1}\033\[4[0-8].*?m|\033\[0m|$"
    bgfgstop = bgstop[:-2] + r"(\s*)" + fgstop

    fgstart = "((?:\033\[1m|\033\[22m){0,1}\033\[3[0-8].*?m)"
    bgstart = "((?:\033\[1m|\033\[22m){0,1}\033\[4[0-8].*?m)"
    bgfgstart = bgstart + r"(\s*)" + "((?:\033\[1m|\033\[22m){0,1}\033\[[3-4][0-8].*?m){0,1}"

    # extract color markers, tagging the start marker and the text marked
    re_fgs = re.compile(fgstart + "(.*?)(?=" + fgstop + ")")
    re_bgs = re.compile(bgstart + "(.*?)(?=" + bgstop + ")")
    re_bgfg = re.compile(bgfgstart + "(.*?)(?=" + bgfgstop + ")")

    re_normal = re.compile(normal.replace("[", r"\["))
    re_hilite = re.compile("(?:%s)(.*)(?=%s|%s)" % (hilite.replace("[", r"\["), fgstop, bgstop))
    re_unhilite = re.compile("(?:%s)(.*)(?=%s|%s)" % (unhilite.replace("[", r"\["), fgstop, bgstop))
    re_uline = re.compile("(?:%s)(.*?)(?=%s|%s)" % (underline.replace("[", r"\["), fgstop, bgstop))
    re_blink = re.compile("(?:%s)(.*?)(?=%s|%s)" % (blink.replace("[", r"\["), fgstop, bgstop))
    re_inverse = re.compile("(?:%s)(.*?)(?=%s|%s)" % (inverse.replace("[", r"\["), fgstop, bgstop))
    re_string = re.compile(
        r"(?P<htmlchars>[<&>])|(?P<firstspace>(?<=\S)  )|(?P<space> [ \t]+)|"
        r"(?P<spacestart>^ )|(?P<lineend>\r\n|\r|\n)",
        re.S | re.M | re.I,
    )
    re_dblspace = re.compile(r" {2,}", re.M)
    re_url = re.compile(
        r'((?:ftp|www|https?)\W+(?:(?!\.(?:\s|$)|&\w+;)[^"\',;$*^\\(){}<>\[\]\s])+)(\.(?:\s|$)|&\w+;|)'
    )
    re_mxplink = re.compile(r"\|lc(.*?)\|lt(.*?)\|le", re.DOTALL)

    def _sub_bgfg(self, colormatch):
        # print("colormatch.groups()", colormatch.groups())
        bgcode, prespace, fgcode, text, postspace = colormatch.groups()
        if not fgcode:
            ret = r"""<span class="%s">%s%s%s</span>""" % (
                self.bg_colormap.get(bgcode, self.fg_colormap.get(bgcode, "err")),
                prespace and "&nbsp;" * len(prespace) or "",
                postspace and "&nbsp;" * len(postspace) or "",
                text,
            )
        else:
            ret = r"""<span class="%s"><span class="%s">%s%s%s</span></span>""" % (
                self.bg_colormap.get(bgcode, self.fg_colormap.get(bgcode, "err")),
                self.fg_colormap.get(fgcode, self.bg_colormap.get(fgcode, "err")),
                prespace and "&nbsp;" * len(prespace) or "",
                postspace and "&nbsp;" * len(postspace) or "",
                text,
            )
        return ret

    def _sub_fg(self, colormatch):
        code, text = colormatch.groups()
        return r"""<span class="%s">%s</span>""" % (self.fg_colormap.get(code, "err"), text)

    def _sub_bg(self, colormatch):
        code, text = colormatch.groups()
        return r"""<span class="%s">%s</span>""" % (self.bg_colormap.get(code, "err"), text)

    def re_color(self, text):
        """
        Replace ansi colors with html color class names.  Let the
        client choose how it will display colors, if it wishes to.

        Args:
            text (str): the string with color to replace.

        Returns:
            text (str): Re-colored text.

        """
        text = self.re_bgfg.sub(self._sub_bgfg, text)
        text = self.re_fgs.sub(self._sub_fg, text)
        text = self.re_bgs.sub(self._sub_bg, text)
        text = self.re_normal.sub("", text)
        return text

    def re_bold(self, text):
        """
        Clean out superfluous hilights rather than set <strong>to make
        it match the look of telnet.

        Args:
            text (str): Text to process.

        Returns:
            text (str): Processed text.

        """
        text = self.re_hilite.sub(r"<strong>\1</strong>", text)
        return self.re_unhilite.sub(r"\1", text)  # strip unhilite - there is no equivalent in css.

    def re_underline(self, text):
        """
        Replace ansi underline with html underline class name.

        Args:
            text (str): Text to process.

        Returns:
            text (str): Processed text.

        """
        return self.re_uline.sub(r'<span class="underline">\1</span>', text)

    def re_blinking(self, text):
        """
        Replace ansi blink with custom blink css class

        Args:
            text (str): Text to process.

        Returns:
            text (str): Processed text.
        """
        return self.re_blink.sub(r'<span class="blink">\1</span>', text)

    def re_inversing(self, text):
        """
        Replace ansi inverse with custom inverse css class

        Args:
            text (str): Text to process.

        Returns:
            text (str): Processed text.
        """
        return self.re_inverse.sub(r'<span class="inverse">\1</span>', text)

    def remove_bells(self, text):
        """
        Remove ansi specials

        Args:
            text (str): Text to process.

        Returns:
            text (str): Processed text.

        """
        return text.replace("\07", "")

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
        # -> added target to output prevent the web browser from attempting to
        # change pages (and losing our webclient session).
        return self.re_url.sub(r'<a href="\1" target="_blank">\1</a>\2', text)

    def re_double_space(self, text):
        """
        HTML will swallow any normal space after the first, so if any slipped
        through we must make sure to replace them with " &nbsp;"
        """
        return self.re_dblspace.sub(self.sub_dblspace, text)

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
        elif cdict["firstspace"]:
            return " &nbsp;"
        elif cdict["space"] == "\t":
            return " " if self.tabstop == 1 else " " + "&nbsp;" * self.tabstop
        elif cdict["space"] or cdict["spacestart"]:
            text = match.group().replace("\t", "&nbsp;" * self.tabstop)
            text = text.replace(" ", "&nbsp;")
            return text
        return None

    def sub_dblspace(self, match):
        "clean up double-spaces"
        return " " + "&nbsp;" * (len(match.group()) - 1)

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
        result = self.re_color(result)
        result = self.re_bold(result)
        result = self.re_underline(result)
        result = self.re_blinking(result)
        result = self.re_inversing(result)
        result = self.remove_bells(result)
        result = self.convert_linebreaks(result)
        result = self.remove_backspaces(result)
        result = self.convert_urls(result)
        result = self.re_double_space(result)
        # clean out eventual ansi that was missed
        # result = parse_ansi(result, strip_ansi=True)

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
