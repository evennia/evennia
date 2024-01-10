"""
ANSI -> html converter

Credit for original idea and implementation
goes to Muhammad Alkarouri and his
snippet #577349 on http://code.activestate.com.

(extensively modified by Griatch 2010)
"""

import re
from html import escape as html_escape
from django.conf import settings

_EVSTRING = None

_COLOR_LIST = [
        'X','R','G','Y','B','M','C','W','x','r','g','y','b','m','c','w'
    ] + [
        f'{r}{g}{b}' for b in range(6) for g in range(6) for r in range(6)
    ] + [
        f'={x}' for x in 'abcdefghijklmnopqrstuvwxyz'
    ]
_GREYS = "abcdefghijklmnopqrstuvwxyz"
_RE_COLORS = re.compile(r'([rRgGbBcCyYwWxXmM]|[0-5]{3}|\=[a-z]|#[0-9a-f]{6})')
_RE_URL = re.compile(
        r'(?<!=")(\b(?:ftp|www|https?)\W+(?:(?!\.(?:\s|$)|&\w+;)[^"\',;$*^\\(){}<>\[\]\s])+)(\.(?:\s|$)|&\w+;|)'
    )
_RE_PROTOCOL = re.compile(r"^(?:ftp|https?)://")
_RE_VALID_NO_PROTOCOL = re.compile(
        r"^(?:www|ftp)\.[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b[-a-zA-Z0-9@:%_\+.~#?&//=]*"
    )
_RE_LINE = re.compile(r'^(-+|_+)$', re.MULTILINE)
_RE_COLORS = re.compile(r'([rRgGbBcCyYwWxXmM]|[0-5]{3}|\=[a-z]|#[0-9a-f]{6})')
_RE_STRING = re.compile(
        r"(?P<htmlchars>[<&>])|(?P<tab>[\t]+)|(?P<lineend>\r\n|\r|\n)",
        re.S | re.M | re.I,
    )

_PARSE_CACHE = dict()
_PARSE_CACHE_SIZE = 10000

# we won't need this once the webclient can support rgb codes
_MARKUP_CHAR = settings.MARKUP_CHAR
def hex_to_xterm(string, bg=False):
    """
    Converts a hexadecimal rgb string to an xterm256 rgb string

    Args:
      string (str): the text to convert

    Returns:
      str: the converted tag
    """
    def split_hex(text):
        return ( int(text[i:i+2],16) for i in range(0,6,2) )
         
    def grey_int(num):
        return round( max((num-8),0)/10 )

    def hue_int(num):
        return round(max((num-45),0)/40)
        
    r, g, b = split_hex(string)

    if r == g and g == b:
        # greyscale
        i = grey_int(r)
        string = _MARKUP_CHAR + '=' + _GREYS[i]
    else:
        string = f"{_MARKUP_CHAR}{'[' if bg else ''}{hue_int(r)}{hue_int(g)}{hue_int(b)}"
        
    return string

class RenderToHTML(object):
    """
    This class describes a parser for rendering Evennia-markup text as HTML.
    """

    # assign these as class properties for easier customizing
    re_colors = _RE_COLORS
    re_url = _RE_URL
    re_protocol = _RE_PROTOCOL
    re_valid_no_protocol = _RE_VALID_NO_PROTOCOL
    re_string = _RE_STRING
    re_line = _RE_LINE

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
        Convert plain-text urls (http://...) to valid anchor elements.

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
        cdict = match.groupdict()
        if cdict["htmlchars"]:
            return html_escape(cdict["htmlchars"])
        elif cdict["lineend"]:
            return "<br>"
        return None

    def _make_html(self, text, **kwargs):
        """
        Replaces various substrings with browser-friendly versions.
        """
        text = self.re_string.sub(self.sub_text, text)
        # escape escaped pipes
#        text = text.replace("||","&#124;")
        # replace ---- with hr element'
        # commented out for now because the core webclient doesn't support hr elements
        # text = self.re_line.sub("<hr/>",text)
        # text = text.replace("<hr/>\n","<hr/>")
        return text

    def create_link(self, text, link_type="c", link_value=''):
        """Create an anchor link with the given text, either to a URL or as an MXP command"""
        val = text
        if link_type == 'c':
            # MXP command
            val = (
                r"""<a class="mxplink" href="#" """
                """onclick="Evennia.msg(&quot;text&quot;,[&quot;{cmd}&quot;],{{}});"""
                """return false;">{text}</a>""".format(cmd=link_value, text=text)
            )
        elif link_type == 'u':
            # URL link
            val = r"""<a class="mxplink" href="{url}" target="_blank">{text}</a>""".format(
                url=link_value, text=text
            )

        return val

    def convert_markup(self, chunks, **kwargs):
        """
        Converts pre-split markup codes and text into HTML syntax.

        Args:
            chunks (tuple): The chunks to process.
        Returns:
            text (str): Processed text.
        """
        global _EVSTRING
        if not _EVSTRING:
            from evennia.utils.evstring import EvString as _EVSTRING

        # check cached parsings
        # global _PARSE_CACHE
        # cachekey = ''.join(chunks)
        # if cachekey in _PARSE_CACHE:
        #     return _PARSE_CACHE[cachekey]
        # dangit, this doesn't work any more because it can't flatten to a string

        from evennia.utils.evstring import EvLink

        output = []

        # initialize all the flags and classes
        color = ""
        bgcolor = ""
        classes = set()
        clean = True
        inverse = False
        hilight = False
        lowlight = False

        for chunk in chunks:
            if isinstance(chunk, EvLink):
                # we're processing a link
                link = chunk.data()
                link_text = _EVSTRING(link.text, html=self).to_html()
                link_text = self.create_link(link_text, link_type=link.key, link_value=link.link)
                output.append(link_text)

            else:
                # we're processing some possibly-styled text
                style_tup, text = chunk
                style_dict = dict(style_tup)

                if style_dict.get('reset'):
                    if not clean:
                        output.append("</span>")
                    color = ""
                    bgcolor = ""
                    classes = set()
                    clean = True
                    inverse = False
                    hilight = False
                    lowlight = False

                if code_str := style_dict.get('str'):
                    # we just want to use it like a string
                    if code_str in ">-":
                        output.append("\t")
                    elif code_str == "_":
                        output.append(" ")
                    else:
                        # add anything else as-is
                        output.append(code_str)

                # this is a non-color, layerable style
                if style_dict.get('underline'):
                    classes.add("underline")
                if style_dict.get('blink'):
                    classes.add("blink")
                if style_dict.get('invert'):
                    inverse = True
                if style_dict.get('hilight'):
                    hilight = True
                    lowlight = False
                elif style_dict.get('lowlight'):
                    hilight = False
                    lowlight = True

                # special handling for the "highlight" codes
                elif code_str == "h":
                    # "hilight" dark ANSI
                    if 0 >= int(color) >= 7:
                        code = "{:03d}".format(self.color_list.index(int(color)+8))
                elif code_str == "H":
                    # "unhilight" bright ANSI
                    if 8 >= int(color) >= 15:
                        code = "{:03d}".format(self.color_list.index(int(color)-8))


                else:
                    # check for foreground colors
                    if new_color := style_dict.get('fg_hex'):
                        # falling back to xterm for now since the webclient doesn't yet support hex
                        color = hex_to_xterm(new_color)
                    elif new_color := style_dict.get('fg_xterm'):
                        color = "{:03d}".format(self.color_list.index(new_color))
                    elif new_color := style_dict.get('fg_color'):
                        # handle applying the expected "hilight" flag for cross-compat
                        modifier = 0
                        if hilight:
                            modifier = 8
                        elif lowlight:
                            modifier = -8
                        color = "{:03d}".format(self.color_list.index(new_color) - modifier)

                    # check for background colors
                    if new_color := style_dict.get('bg_hex'):
                        # falling back to xterm for now since the webclient doesn't yet support hex
                        bgcolor = hex_to_xterm(new_color)
                    elif new_color := style_dict.get('bg_xterm'):
                        bgcolor = "{:03d}".format(self.color_list.index(new_color))
                    elif new_color := style_dict.get('bg_color'):
                        bgcolor = "{:03d}".format(self.color_list.index(new_color))

                # time to style the text!
                if not clean:
                    output.append("</span>")
                new_span = "<span"

                class_list = list(classes)
                # special handling to invert colors
                if inverse:
                    if bgcolor:
                        class_list.append(f"color-{bgcolor}")
                    else:
                        # default bg color is black
                        class_list.append(f"color-000")
                    if color:
                        class_list.append(f"bgcolor-{color}")
                    else:
                        # default color is light grey
                        class_list.append(f"bgcolor-007")
                else:
                    # normal coloring
                    if color:
                        class_list.append(f"color-{color}")
                    if bgcolor:
                        class_list.append(f"bgcolor-{bgcolor}")

                if class_list:
                    new_span += f' class="{" ".join(sorted(class_list))}"'
                    clean=False
                
                new_span += ">"
                # only append the span tag if it does something
                if new_span != "<span>":
                    output.append(new_span)

                # then add the displayable text
                output.append(self._make_html(text))

        parsed_string = "".join(output)
        if not clean and not parsed_string.endswith("</span>"):
            parsed_string += "</span>"
        # cache and crop old cache
        # _PARSE_CACHE[cachekey] = parsed_string
        # if len(_PARSE_CACHE) > _PARSE_CACHE_SIZE:
        #     _PARSE_CACHE.popitem(last=False)

        return parsed_string

    def parse(self, text, strip_markup=False):
        """
        Allows you to pass a plain text string to the HTML renderer. It can also accept
        EvStrings.
        
        Args:
            text (str or EvString): the string to process
        
        Keyword args:
            strip_markup (bool): whether or not to remove Evennia markup first
        
        Returns:
            result (str): the string as HTML
        """
        global _EVSTRING
        if not _EVSTRING:
            from evennia.utils.evstring import EvString as _EVSTRING

        # ensure we use this renderer for conversion
        text = _EVSTRING(text, html=self)
        
        if strip_markup:
            return self.convert_markup( (text.clean,) )
        else:
            return text.to_html()

HTML_PARSER = RenderToHTML()


#
# Access function
#


def to_html(string, strip_markup=False, parser=HTML_PARSER):
    """
    Converts a plain string or EvString to HTML
    """
    return parser.parse(string, strip_markup=strip_markup)
