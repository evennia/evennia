
"""
ANSI -> html converter

Credit for original idea and implementation 
goes to Muhammad Alkarouri and his 
snippet #577349 on http://code.activestate.com.

(extensively modified by Griatch 2010)
"""

import re
import cgi
from src.utils import ansi

class TextToHTMLparser(object):
    """
    This class describes a parser for converting from ansi to html.
    """    
    
    # mapping html color name <-> ansi code. 
    # Obs order matters - longer ansi codes are replaced first.
    colorcodes = [('white', '\033[1m\033[37m'),
                  ('cyan', '\033[1m\033[36m'),
                  ('blue', '\033[1m\033[34m'),
                  ('red', '\033[1m\033[31m'),
                  ('magenta', '\033[1m\033[35m'),
                  ('lime', '\033[1m\033[32m'), 
                  ('yellow', '\033[1m\033[33m'),
                  ('gray', '\033[37m'),
                  ('teal', '\033[36m'), 
                  ('navy', '\033[34m'),
                  ('maroon', '\033[31m'),
                  ('purple', '\033[35m'),
                  ('green', '\033[32m'),
                  ('olive', '\033[33m')]
    normalcode = '\033[0m'                
    tabstop = 4

    re_string = re.compile(r'(?P<htmlchars>[<&>])|(?P<space>^[ \t]+)|(?P<lineend>\r\n|\r|\n)|(?P<protocol>(^|\s)((http|ftp)://.*?))(\s|$)', 
                           re.S|re.M|re.I)

    def re_color(self, text):
        "Replace ansi colors with html color tags"
        for colorname, code in self.colorcodes:
            regexp = "(?:%s)(.*?)(?:%s)" % (code, self.normalcode)
            regexp = regexp.replace('[', r'\[')
            text = re.sub(regexp, r'''<span style="color: %s">\1</span>''' % colorname, text)
        return text

    def re_bold(self, text):
        "Replace ansi hilight with bold text"
        regexp = "(?:%s)(.*?)(?:%s)" % ('\033[1m', self.normalcode)
        regexp = regexp.replace('[', r'\[')
        return re.sub(regexp, r'<span style="font-weight:bold">\1</span>', text)

    def re_underline(self, text):
        "Replace ansi underline with html equivalent"
        regexp = "(?:%s)(.*?)(?:%s)" % ('\033[4m', self.normalcode)
        regexp = regexp.replace('[', r'\[')
        return re.sub(regexp, r'<span style="text-decoration: underline">\1</span>', text)

    def remove_bells(self, text):
        "Remove ansi specials"
        return text.replace('\07', '')

    def remove_backspaces(self, text):
        "Removes special escape sequences"
        backspace_or_eol = r'(.\010)|(\033\[K)'
        n = 1
        while n > 0:
            text, n = re.subn(backspace_or_eol, '', text, 1)
        return text

    def convert_linebreaks(self, text):
        "Extra method for cleaning linebreaks"
        return text.replace(r'\n', r'<br>')

    def convert_urls(self, text):
        "Replace urls (http://...) by valid HTML"
        regexp = r"((ftp|www|http)(\W+\S+[^).,:;?\]\}(\<span\>) \r\n$]+))"
        return re.sub(regexp, r'<a href="\1">\1</a>', text)

    def do_sub(self, m):
        "Helper method to be passed to re.sub."
        c = m.groupdict()
        if c['htmlchars']:
            return cgi.escape(c['htmlchars'])
        if c['lineend']:
            return '<br>'
        elif c['space']:
            t = m.group().replace('\t', '&nbsp;'*self.tabstop)
            t = t.replace(' ', '&nbsp;')
            return t
        elif c['space'] == '\t':
            return ' '*self.tabstop
        else:
            url = m.group('protocol')
            if url.startswith(' '):
                prefix = ' '
                url = url[1:]
            else:
                prefix = ''
            last = m.groups()[-1]
            if last in ['\n', '\r', '\r\n']:
                last = '<br>'
            return '%s%s' % (prefix, url)

    def parse(self, text):
        """
        Main access function, converts a text containing 
        ansi codes into html statements. 
        """

        # parse everything to ansi first 
        text = ansi.parse_ansi(text)

        # convert all ansi to html
        result = re.sub(self.re_string, self.do_sub, text)
        result = self.re_color(result)
        result = self.re_bold(result)
        result = self.re_underline(result)
        result = self.remove_bells(result)
        result = self.convert_linebreaks(result)
        result = self.remove_backspaces(result)
        result = self.convert_urls(result)

        # clean out eventual ansi that was missed
        result = ansi.parse_ansi(result, strip_ansi=True)
    
        return result 

HTML_PARSER = TextToHTMLparser()

#
# Access function
#

def parse_html(string, parser=HTML_PARSER):
    """
    Parses a string, replace ansi markup with html
    """
    return parser.parse(string)
