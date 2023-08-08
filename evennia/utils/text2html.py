"""
ANSI -> html converter

Credit for original idea and implementation
goes to Muhammad Alkarouri and his
snippet #577349 on http://code.activestate.com.

(extensively modified by Griatch 2010)
"""

import re
from html import escape as html_escape

_COLOR_LIST = [
        'X','R','G','Y','B','M','C','W','x','r','g','y','b','m','c','w'
    ] + [
        f'{r}{g}{b}' for b in range(6) for g in range(6) for r in range(6)
    ] + [
        f'={x}' for x in 'abcdefghijklmnopqrstuvwxyz'
    ]

_RE_MXPLINK = re.compile(r"\|lc(.*?)\|lt(.*?)\|le", re.DOTALL)
_RE_MXPURL = re.compile(r"\|lu(.*?)\|lt(.*?)\|le", re.DOTALL)
_RE_LINE = re.compile(r'^(-+|_+)$', re.MULTILINE)
_RE_COLORS = re.compile(r'([rRgGbBcCyYwWxXmM]|[0-5]{3}|\=[a-z]|#[0-9a-f]{6})')
_RE_STRING = re.compile(
        r"(?P<htmlchars>[<&>])|(?P<tab>[\t]+)|(?P<lineend>\r\n|\r|\n)",
        re.S | re.M | re.I,
    )
_RE_URL = re.compile(
        r'(?<!=")(\b(?:ftp|www|https?)\W+(?:(?!\.(?:\s|$)|&\w+;)[^"\',;$*^\\(){}<>\[\]\s])+)(\.(?:\s|$)|&\w+;|)'
    )
_RE_XTERM = re.compile(r'([0-5][0-5][0-5]|\=[a-z])')


class TextToHTMLparser(object):
    """
    This class describes a parser for converting from ANSI to html.
    """

    tabstop = 4

    # make these class properties so they're overridable
    re_mxplink = _RE_MXPLINK
    re_mxpurl = _RE_MXPURL
    re_line = _RE_LINE
    re_colors = _RE_COLORS
    re_string = _RE_STRING
    re_url = _RE_URL
    re_protocol = re.compile(r"^(?:ftp|https?)://")
    re_valid_no_protocol = re.compile(
        r"^(?:www|ftp)\.[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b[-a-zA-Z0-9@:%_\+.~#?&//=]*"
    )
    # this is just for the webclient's class-based styling
    color_list = _COLOR_LIST

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

    def parse_markup(self, text, **kwargs):
        """
        Parses evennia style tags into html
        Args:
            text (str): The string to process.
        Returns:
            text (str): Processed text.
        """
        # TODO: consider better alternatives to avoid circular imports
        from evennia.utils.evstring import hex_to_xterm

        text = self.re_string.sub(self.sub_text, text)
        text = self.re_mxplink.sub(self.sub_mxp_links, text)
        text = self.re_mxpurl.sub(self.sub_mxp_urls, text)
        # escape escaped pipes
        text = text.replace("||","&#124;").replace("|/","\n")
        # replace ---- with hr element
        text = self.re_line.sub("<hr/>",text)
        text = text.replace("<hr/>\n","<hr/>")

        # split out the ANSI codes and clean out any empty items
        str_list = [substr for substr in text.split("|") if substr]
        output = []
        # initialize all the flags and classes
        color = ""
        bgcolor = ""
        classes = set()
        clean = True
        inverse = False

        # special handling in case the first item isn't formatted
        if not text.startswith("|"):
            output.append(str_list[0])
            str_list = str_list[1:]

        for substr in str_list:
            code = None
            is_bg = False
            # check if this is a background color flag
            if substr.startswith('['):
                is_bg = False
                substr = substr[1:]

            if match := self.re_colors.match(substr):
                code = match.group(0)
                substr = substr[len(code):]
                if code.startswith('#'):
                    # falling back to xterm for now since the webclient doesn't support hex
                    code = hex_to_xterm(code[1:])
                else:
                # get the class code
                    code = "{:03d}".format(self.color_list.index(code))
            # check style codes
            elif substr == "u":
                classes.add("underline")
                substr = substr[1:]
            elif substr in ">-":
                output.append(" " * self.indent)
                output.append(substr[1:])
                continue
            elif substr == "_":
                output.append(" ")
                output.append(substr[1:])
                continue
            elif substr == "*":
                inverse = True
                substr = substr[1:]

            # check if it's a reset
            elif substr.startswith('n'):
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
                output.append("|"+substr)
                continue

            # add the styling
            if not clean:
                output.append("</span>")

            new_span = "<span"
            # stop! colortime
            if is_bg:
                bgcolor = code
            else:
                color = code


            class_list = list(classes)
            # special handling to invert colors
            if inverse:
                if bgcolor:
                    class_list.append(f"color-{bgcolor}")
                if color:
                    class_list.append(f"bgcolor-{color}")
            else:
                # normal coloring
                if color:
                    class_list.append(f"color-{color}")
                if bgcolor:
                    class_list.append(f"bgcolor-{bgcolor}")

            if class_list:
                new_span += f' class="{" ".join(class_list)}"'
                clean=False
            
            new_span += ">"
            output.append(new_span)
            output.append(substr)

        return "".join(output)

HTML_PARSER = TextToHTMLparser()


#
# Access function
#


def parse_html(string, strip_ansi=False, parser=HTML_PARSER):
    """
    Parses a string, replace ANSI markup with html
    """
    return parser.parse(string, strip_ansi=strip_ansi)
