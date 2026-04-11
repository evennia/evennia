"""
Truecolor 24bit hex color support, on the form `|#00FF00`, `|[00FF00` or `|#0F0 or `|[#0F0`

"""

import re


class HexColors:
    """
    This houses a method for converting hex codes to xterm truecolor codes
    or falls back to evennia xterm256 codes to be handled by sub_xterm256

    Based on code from @InspectorCaracal
    """

    _RE_FG = r"\|#"
    _RE_BG = r"\|\[#"
    _RE_FG_OR_BG = r"\|\[?#"
    _RE_HEX_LONG = "[0-9a-fA-F]{6}"
    _RE_HEX_SHORT = "[0-9a-fA-F]{3}"
    _RE_BYTE = "[0-2]?[0-9]?[0-9]"
    _RE_XTERM_TRUECOLOR = rf"\[([34])8;2;({_RE_BYTE});({_RE_BYTE});({_RE_BYTE})m"

    # Used in hex_sub
    _RE_HEX_PATTERN = f"({_RE_FG_OR_BG})({_RE_HEX_LONG}|{_RE_HEX_SHORT})"

    # Used for greyscale
    _GREYS = "abcdefghijklmnopqrstuvwxyz"

    TRUECOLOR_FG = rf"\x1b\[38;2;{_RE_BYTE};{_RE_BYTE};{_RE_BYTE}m"
    TRUECOLOR_BG = rf"\x1b\[48;2;{_RE_BYTE};{_RE_BYTE};{_RE_BYTE}m"

    # Our matchers for use with ANSIParser and ANSIString
    hex_sub = re.compile(rf"{_RE_HEX_PATTERN}", re.DOTALL)

    def _split_hex_to_bytes(self, tag: str) -> tuple[str, str, str]:
        """
        Splits hex string into separate bytes:
            #00FF00 -> ('00', 'FF', '00')
            #CF3    -> ('CC', 'FF', '33')

        Args:
            tag (str): the tag to convert

        Returns:
            str: the text with converted tags
        """
        strip_leading = re.compile(rf"{self._RE_FG_OR_BG}")
        tag = strip_leading.sub("", tag)

        if len(tag) == 6:
            # 6 digits
            r, g, b = (tag[i : i + 2] for i in range(0, 6, 2))

        else:
            # 3 digits
            r, g, b = (tag[i : i + 1] * 2 for i in range(0, 3, 1))

        return r, g, b

    def _grey_int(self, num: int) -> int:
        """
        Returns a grey greyscale integer

        Returns:

        """
        return round(max((int(num) - 8), 0) / 10)

    def _hue_int(self, num: int) -> int:
        return round(max((int(num) - 45), 0) / 40)

    def _hex_to_rgb_24_bit(self, hex_code: str) -> tuple[int, int, int]:
        """
        Converts a hex color code (#000 or #000000) into
        a 3-int tuple (0, 255, 90)

        Args:
            hex_code (str): HTML hex color code

        Returns:
            24-bit rgb tuple: (int, int, int)
        """
        # Strip the leading indicator if present
        hex_code = re.sub(rf"{self._RE_FG_OR_BG}", "", hex_code)

        r, g, b = self._split_hex_to_bytes(hex_code)

        return int(r, 16), int(g, 16), int(b, 16)

    def _rgb_24_bit_to_256(self, r: int, g: int, b: int) -> tuple[int, int, int]:
        """
        converts 0-255 hex color codes to 0-5

        Args:
            r (int): red
            g (int): green
            b (int): blue

        Returns:
            256 color rgb tuple: (int, int, int)

        """

        return self._hue_int(r), self._hue_int(g), self._hue_int(b)

    def sub_truecolor(self, match: re.Match, truecolor=False) -> str:
        """
        Converts a hex string to xterm truecolor code, greyscale, or
        falls back to evennia xterm256 to be handled by sub_xterm256

        Args:
            match (re.match): first group is the leading indicator,
                              second is the tag
            truecolor (bool): return xterm truecolor or fallback

        Returns:
            Newly formatted indicator and tag (str)

        """
        indicator, tag = match.groups()

        # Remove the # sign
        indicator = indicator.replace("#", "")

        r, g, b = self._hex_to_rgb_24_bit(tag)

        if not truecolor:
            # Fallback to xterm256 syntax
            r, g, b = self._rgb_24_bit_to_256(r, g, b)
            return f"{indicator}{r}{g}{b}"

        else:
            xtag = f"\033["
            if "[" in indicator:
                # Background Color
                xtag += "4"

            else:
                xtag += "3"

            xtag += f"8;2;{r};{g};{b}m"
            return xtag

    def xterm_truecolor_to_html_style(self, fg="", bg="") -> str:
        """
        Converts xterm truecolor to an html style property

        Args:
            fg: xterm truecolor
            bg: xterm truecolor

        Returns: style='color and or background-color'

        """
        prop = 'style="'
        if fg != "":
            res = re.search(self._RE_XTERM_TRUECOLOR, fg, re.DOTALL)
            fg_bg, r, g, b = res.groups()
            r = hex(int(r))[2:].zfill(2)
            g = hex(int(g))[2:].zfill(2)
            b = hex(int(b))[2:].zfill(2)
            prop += f"color: #{r}{g}{b};"
        if bg != "":
            res = re.search(self._RE_XTERM_TRUECOLOR, bg, re.DOTALL)
            fg_bg, r, g, b = res.groups()
            r = hex(int(r))[2:].zfill(2)
            g = hex(int(g))[2:].zfill(2)
            b = hex(int(b))[2:].zfill(2)
            prop += f"background-color: #{r}{g}{b};"
        prop += f'"'
        return prop
