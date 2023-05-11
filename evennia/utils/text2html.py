"""
ANSI -> html converter

Credit for original idea and implementation
goes to Muhammad Alkarouri and his
snippet #577349 on http://code.activestate.com.

(extensively modified by Griatch 2010)
"""

import re
from html import escape as html_escape

from .ansi import strip_ansi


class TextToHTMLparser(object):
    """
    This class describes a parser for converting from ANSI to html.
    """

    tabstop = 4
    ansi_color_map = {
        "r": "red1",
        "R": "red2",
        "y": "yellow1",
        "Y": "yellow2",
        "g": "green1",
        "G": "green2",
        "c": "cyan1",
        "C": "cyan2",
        "b": "blue1",
        "B": "blue2",
        "m": "magenta1",
        "M": "magenta2",
        "w": "hi-text",
        "W": "low-text",
        "x": "hi-bg",
        "X": "low-bg",
    }

    re_xterm = re.compile(r"\|([0-5][0-5][0-5]|\=[a-z])")
    re_xterm_bg = re.compile(r"\|\[([0-5][0-5][0-5]|\=[a-z])")

    re_string = re.compile(
        r"(?P<htmlchars>[<&>])|(?P<tab>[\t|\|-]+)|(?P<lineend>\r\n|\r|\n|\|/)",
        re.S | re.M | re.I,
    )
    re_line = re.compile(r"^(-+|_+)$", re.MULTILINE)

    re_url = re.compile(
        r'(?<!=")(\b(?:ftp|www|https?)\W+(?:(?!\.(?:\s|$)|&\w+;)[^"\',;$*^\\(){}<>\[\]\s])+)(\.(?:\s|$)|&\w+;|)'
    )
    re_protocol = re.compile(r"^(?:ftp|https?)://")
    re_valid_no_protocol = re.compile(
        r"^(?:www|ftp)\.[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b[-a-zA-Z0-9@:%_\+.~#?&//=]*"
    )
    re_mxplink = re.compile(r"\|lc(.*?)\|lt(.*?)\|le", re.DOTALL)
    re_mxpurl = re.compile(r"\|lu(.*?)\|lt(.*?)\|le", re.DOTALL)

    """
    Parses evennia style tags into html
    Args:
        text (str): The string to process.
    Returns:
        text (str): Processed text.
    """

    def xterm_to_hex(match, bg=False):
        def hue_hex(text):
            return format(int(text) * 40 + 25, "02x")

        def grey_hex(text):
            return format(_GREYS.index(text) * 10 + 8, "02x")

        start, end = match.span()
        flag = "|[#" if bg else "|#"
        tag = match.group(1)
        if tag[0] == "=":
            # greyscale
            hex = grey_hex(tag[1])
            message = message[:start] + flag + hex * 3 + message[end:]

        else:
            r, g, b = tag
            htag = flag + "{}{}{}".format(hue_hex(r), hue_hex(g), hue_hex(b))
            message = message[:start] + htag + message[end:]

        return message

    def xterm_bg_to_hex(match):
        return self.xterm_to_hex(match, bg=True)

    def sub_mxp_links(match):
        """
        Helper method to be passed to re.sub,
        replaces MXP links with HTML code.
        """
        cmd, text = [grp.replace('"', "\\&quot;") for grp in match.groups()]
        val = rf'<span class="mxplink" data-command="{cmd}">{text}</span>'
        return val

    def sub_mxp_urls(match):
        """
        Helper method to be passed to re.sub,
        replaces MXP links with HTML code.
        """
        url, text = [grp.replace('"', "\\&quot;") for grp in match.groups()]
        val = rf'<a href="{url}" target="_blank">{text}</a>'
        return val

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

    def sub_text(self, match):
        """
        Helper method to be passed to re.sub,
        for handling all substitutions.

        Args:
            match (re.Matchobject): Match for substitution.

        Returns:
            text (str): Processed text.

        """
        # TODO: possibly rework this, since i didn't do an equivalent
        cdict = match.groupdict()
        if cdict["htmlchars"]:
            return html_escape(cdict["htmlchars"])
        elif cdict["lineend"]:
            return "\n"
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

        # split out the style codes and clean out any empty items
        str_list = [substr for substr in message.split("|") if substr]
        output = []
        # initialize all the flags and classes
        color = ""
        bgcolor = ""
        classes = set()
        clean = True
        inverse = False

        # special handling in case the first item is formatted
        if not message.startswith("|"):
            output.append(str_list[0])
            str_list = str_list[1:]

        for substr in str_list:
            # it's a background color
            if substr.startswith("["):
                if substr[1] == "#":
                    # hex color, use as-is
                    bgcolor = substr[1:8]
                    substr = substr[8:]
                elif ccode := self.ansi_color_map.get(substr[1]):
                    bgcolor = f"var(--{ccode})"
                    substr = substr[2:]
            # check color codes
            elif substr.startswith("#"):
                # hex color, use as-is
                color = substr[:7]
                substr = substr[7:]
            elif ccode := self.ansi_color_map.get(substr[0]):
                color = f"var(--{ccode})"
                substr = substr[1:]

            # check style codes
            elif substr[0] == "u":
                classes.add("underline")
                substr = substr[1:]
            elif substr[0] in ">-":
                output.append(" " * self.tabstop)
                output.append(substr[1:])
                continue
            elif substr[0] == "_":
                output.append(" ")
                output.append(substr[1:])
                continue
            elif substr[0] == "*":
                inverse = True
                substr = substr[1:]

            # check if it's a reset
            elif substr.startswith("n"):
                if not clean:
                    color = ""
                    bgcolor = ""
                    classes = set()
                    clean = True
                    inverse = False
                    output.append("</span>")
                output.append(substr[1:])
                continue

            # it didn't match any codes, just add the pipe back in and keep going
            else:
                output.append("|" + substr)
                continue

            # add the styling
            if not clean:
                output.append("</span>")

            new_span = "<span"
            # stop! colortime
            if color or bgcolor:
                # special handling to invert colors
                if inverse:
                    if not bgcolor:
                        style = f'style="color: inherit;background-color: {color}"'
                    elif not color:
                        style = f'style="color: {bgcolor}"'
                    else:
                        style = f'style="color: {bgcolor};background-color: {color}"'
                else:
                    # normal coloring
                    style = 'style="'
                    if color:
                        style += f"color: {color};"
                    if bgcolor:
                        style += f"background-color: {bgcolor}"
                    style += '"'
                new_span += " " + style

            # add classes
            if len(classes):
                class_str = 'class="{}"'.format(" ".join(list(classes)))
                new_span += " " + class_str

            new_span += ">"
            output.append(new_span)
            clean = False
            output.append(substr)

        return "".join(output)

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
        if strip_ansi:
            text = strip_ansi(text)
        # escape html
        text = re.sub(self.re_string, self.sub_text, text)
        # replace escaped pipes
        text = text.replace("||", "&#124;")
        # parse MXP links, both kinds
        text = re.sub(self.re_mxplink, self.sub_mxp_links, text)
        text = re.sub(self.re_mxpurl, self.sub_mxp_urls, text)
        # replace ---- with hr element
        text = re.sub(self.re_line, "<hr/>", text)
        text = text.replace("<hr/>\n", "<hr/>")
        # convert XTERM codes to hex color codes
        text = re.sub(self.re_xterm, self.xterm_to_hex, text)
        text = re.sub(self.re_xterm_bg, self.xterm_bg_to_hex, text)
        # convert remaining flags to html
        text = self.format_styles(text)

        return text


HTML_PARSER = TextToHTMLparser()


#
# Access function
#


def parse_html(string, strip_ansi=False, parser=HTML_PARSER):
    """
    Parses a string, replace ANSI markup with html
    """
    return parser.parse(string, strip_ansi=strip_ansi)
