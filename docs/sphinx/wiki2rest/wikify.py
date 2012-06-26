#!/usr/bin/python
#
# wikify.py - Convert from wikitext to HTML
# Based on large portions of JeremyRuston's TiddlyWiki JS Wikifier
# Changed to GoogleCode wiki syntax, python by Michael Crawford <mike@dataunity.com>
""" Convert wikitext to HTML """

# Jeremy's license:
#   Copyright (c) UnaMesa Association 2004-2007
#
#   Redistribution and use in source and binary forms, with or without modification,
#   are permitted provided that the following conditions are met:
#
#   Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright notice, this
#   list of conditions and the following disclaimer in the documentation and/or other
#   materials provided with the distribution.
#
#   Neither the name of the UnaMesa Association nor the names of its contributors may be
#   used to endorse or promote products derived from this software without specific
#   prior written permission.
#
#   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
#   AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#   IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
#   ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
#   LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#   CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
#   SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
#   INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
#   CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
#   ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
#   POSSIBILITY OF SUCH DAMAGE.
#
# My license:
#   Copyright (c) Data Unity 2007
#
#   Redistribution and use in source and binary forms, with or without modification,
#   are permitted provided that the following conditions are met:
#
#   Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright notice, this
#   list of conditions and the following disclaimer in the documentation and/or other
#   materials provided with the distribution.
#
#   Neither the name of the Data Unity nor the names of its contributors may be
#   used to endorse or promote products derived from this software without
#   specific prior written permission.
#
#   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
#   AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#   IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
#   ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
#   LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#   CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
#   SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
#   INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
#   CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
#   ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
#   POSSIBILITY OF SUCH DAMAGE.

import re, os, os.path, htmlentitydefs, urllib


class _HTML:
    """ An HTML node factory factory. """

    class Node:
        """ An HTML element. """
        def __init__(self, parent, tagname, text="", attribs={}, empty=False, **kwargs):
            self.tagname = tagname
            self.attribs = dict(attribs)
            self.children = list()
            self.empty = empty
            if text != "":
                self.appendText(text)
            if parent is not None:
                parent.children.append(self)
            self.parent = parent

        def appendText(self, text):
            if text == "": return
            _HTML.Text(self, text)

        def __str__(self):
            attrs = " ".join([ '%s="%s"' % i for i in self.attribs.iteritems() ])
            if attrs: attrs = " " + attrs
            if self.empty:
                return "<%s%s/>" % (self.tagname, attrs)

            children = "".join([str(c) for c in self.children])
            return "<%s%s>%s</%s>" % (self.tagname, attrs, children, self.tagname)

        def isInside(self, tagname):
            k = self
            while k is not None:
                if k.tagname == tagname:
                    return True
                k = k.parent
            return False

    class Text:
        """ Simple text node. """
        entities = [ (k,v)
             for k,v in htmlentitydefs.entitydefs.iteritems()
             if k != "amp" and k[0] != "#" ]

        def __init__(self, parent, text=""):
            self.text = self._clean(text)
            if parent is not None:
                parent.children.append(self)

        def _clean(self, text):
            text = text.replace("&", "&amp;")
            for k,v in self.entities:
                text = text.replace(v, "&%s;" % k)
            return text

        def __str__(self):
            return self.text


    def __getattr__(self, attr):
        """ Return an element constructor using the attribute as the tagname """
        def factory(parent=None, **kwargs):
            return self.Node(parent, attr, **kwargs)
        return factory

HTML = _HTML()

URLSTR = r"(?:file|http|https|mailto|ftp|irc|news|data):[^\s'\"]+(?:/|\b)"
URL = re.compile(URLSTR, re.M)
IMGURLSTR = r".+((\.[Pp][Nn][Gg])|(\.[Gg][Ii][Ff])|(\.[Jj][Pp][Ee]?[Gg]))"
IMGURL = re.compile(IMGURLSTR, re.M)
YOUTUBESTR = r"http://www.youtube.com/watch\?v=([A-Za-z0-9_-]+)"
YOUTUBEURL = re.compile(YOUTUBESTR, re.M)
YOUTUBEREPL = r'<object width="425" height="355"><param name="movie" value="http://www.youtube.com/v/%s&rel=1"></param><param name="wmode" value="transparent"></param><embed src="http://www.youtube.com/v/hQPHf_8J8Eg&rel=1" type="application/x-shockwave-flash" wmode="transparent" width="425" height="355"></embed></object>'
VIDEOURLSTR = r".+((\.[Aa][Vv][Ii])|(\.[Mm][Oo][Vv])|(\.[Mm][Pp][Ee]?[Gg]))"
VIDEOURL = re.compile(VIDEOURLSTR, re.M)
VIDEOREPL = r'<embed src = "%s"  width="400" height="350"  hidden=false autostart=true loop=1>'
CODEURLSTR = r"http://([^\.]+).googlecode.com/svn/trunk/([^#]+)#((?:(?:(?:[\d]+)?\-)?[\d]+)|(?:[\d]+\-?))((?:\:(?:[\:]|[^\W])+))?"
CODEURL = re.compile(CODEURLSTR, re.M)
CODEREPL = r'<a href="%(url)s">svn://%(site)s/trunk/%(file)s</a><pre name="code" class="%(class)s">%(lines)s</pre>'

def GoogleCode_ReadSVNFile(wikifier, domain, path, start, end):
    """ Try to read a file from subversion for inclusion in the wiki. """

    gcurl = "http://%s.googlecode.com/svn/trunk/%s" % (domain,path)
    fdata = urllib.urlopen(gcurl).readlines()
    return gcurl, fdata[start-1:end]


def GoogleCode_IsExternalLink(wikifier, link):
    """ See if the link points outside of the wiki. """

    if GoogleCode_Exists(wikifier, link):
        return False;

    if URL.match(link):
        return True

    if '.' in link or '\\' in link or '/' in link or '#' in link:
        return True

    return False

def GoogleCode_Exists(wikifier, wikipage):
    """ See if a wiki page exists inside this wiki. """
    path = os.path.join(wikifier.srcdir, "%s.wiki" % wikipage)
    if os.path.exists(path):
        return True
    return False


def GoogleCode_Heading(wikifier, termRegExp=None, **kwargs):
    termMatch = termRegExp.search(wikifier.source, wikifier.nextMatch)
    if termMatch is None: return
    if (len(wikifier.output.children) and
        "br" == getattr(wikifier.output.children[-1], 'tagname', '')):
        wikifier.output.children.pop(-1)
        if (len(wikifier.output.children) and
            "br" == getattr(wikifier.output.children[-1], 'tagname', '')):
            wikifier.output.children.pop(-1)
    output = HTML.Node(wikifier.output, "h%i" % wikifier.matchLength)
    wikifier.outputText(output, wikifier.nextMatch, termMatch.start())
    wikifier.nextMatch = termMatch.end()

def GoogleCode_SimpleElement(wikifier, termRegExp=None, tagName=None, **kwargs):
    if wikifier.output.isInside(tagName):
        wikifier.outputText(wikifier.output, wikifier.matchStart, wikifier.nextMatch)
        return
    elif wikifier.source[wikifier.nextMatch-1] == "_":
        wikifier.outputText(wikifier.output, wikifier.matchStart, wikifier.nextMatch-1)

    if termRegExp.search(wikifier.source, wikifier.nextMatch) is None: return
    output = HTML.Node(wikifier.output, tagName, **kwargs)
    wikifier.subWikifyTerm(output, termRegExp)
    #if wikifier.source[wikifer.nextMatch-2] == "_":
    #    wikifier.nextMatch -= 1

def GoogleCode_Blockquote(wikifier, termRegExp=None, **kwargs):
    sibs = wikifier.output.children
    if len(sibs) and getattr(sibs[-1], 'tagname', None) == "blockquote":
        wikifier.subWikifyTerm(sibs[-1], termRegExp)
    else:
        output = HTML.blockquote(wikifier.output, **kwargs)
        wikifier.subWikifyTerm(output, termRegExp)

def GoogleCode_Codeblock(wikifier, tagName=None, termRegExp=None, initRegExp=None, **kwargs):
    if 'attribs' not in kwargs:
        kwargs['attribs'] = {}

    kwargs['attribs']['name'] = 'code'
    if 'class' not in kwargs['attribs']:
        kwargs['attribs']['class'] = wikifier.defaultHiLang.lower()
    else:
        kwargs['attribs']['class'] += " " + wikifier.defaultHiLang.lower()

    output = HTML.Node(wikifier.output, tagName, **kwargs)
    tcount = 1
    matchStart = wikifier.nextMatch
    # Find the matching terminator
    while tcount > 0:
        nextTermMatch = termRegExp.search(wikifier.source, wikifier.nextMatch)
        nextInitMatch = initRegExp.search(wikifier.source, wikifier.nextMatch)

        if not nextTermMatch:
            # No terminator. Syntax error, just ignore it.
            matchEnd = matchStart
            tcount = 0
            break
        elif not nextInitMatch or nextTermMatch.start() <= nextInitMatch.start():
            # Terminator goes first.
            nextMatch = nextTermMatch
            tcount -= 1
            if tcount > 0:
                matchEnd = nextMatch.end()
            else:
                matchEnd = nextMatch.start()
        else:
            nextMatch = nextInitMatch
            tcount += 1
            matchEnd = nextMatch.end()

        wikifier.nextMatch = nextMatch.end()

    # Copy the content
    wikifier.outputText(output, matchStart, matchEnd)

    if "\n" not in wikifier.source[matchStart:matchEnd]:
        output.tagname = "code"

def GoogleCode_WikiWord(wikifier, **kwargs):
    if wikifier.matchStart > 0:
        # Make sure we're at the start of a word?
        preRegExp = re.compile("[!A-Za-z0-9]", re.M)
        preMatch = preRegExp.search(wikifier.source, wikifier.matchStart-1)
        if (preMatch is not None and
            preMatch.start() == wikifier.matchStart-1):
            wikifier.outputText(wikifier.output,wikifier.matchStart,wikifier.nextMatch)
            return

    if wikifier.source[wikifier.matchStart] == "!":
        wikifier.outputText(wikifier.output,wikifier.matchStart+1,wikifier.nextMatch)
    elif GoogleCode_Exists(wikifier, wikifier.matchText):
        # Full link, everybody sees it
        HTML.a(wikifier.output, text=wikifier.matchText, attribs={"href": wikifier.matchText + wikifier.suffix})
    elif wikifier.autolink:
        # Partial link - only authorized users
        wikifier.outputText(wikifier.output,wikifier.matchStart,wikifier.nextMatch)
        link = HTML.a(wikifier.output, text="?", attribs={"href": wikifier.matchText + wikifier.suffix})
    else:
        wikifier.outputText(wikifier.output,wikifier.matchStart,wikifier.nextMatch)

def GoogleCode_LineBreak(wikifier, **kwargs):
    sibs = wikifier.output.children
    if wikifier.multibreak:
        HTML.p(wikifier.output, **kwargs)
    elif len(sibs) and (not hasattr(sibs[-1], 'tagname') or
                        sibs[-1].tagname == "img"):
        # Only after an inline or header block.
        HTML.p(wikifier.output, **kwargs)
        HTML.p(wikifier.output, **kwargs)

def GoogleCode_PrettyLink(wikifier, lookaheadRegExp=None, **kwargs):
    lookMatch = lookaheadRegExp.search(wikifier.source, wikifier.matchStart)
    if lookMatch and lookMatch.start() == wikifier.matchStart:
        text = lookMatch.group(1)
        if lookMatch.group(2):
            # Pretty bracketted link
            link = text
            text = lookMatch.group(2)
            if GoogleCode_IsExternalLink(wikifier, link):
                # External link
                attribs={"href":link, "target": "_blank" }
            else:
                # Internal link
                attribs={"href":link + wikifier.suffix}

            e = HTML.a(wikifier.output, attribs=attribs)

            if URL.match(text):
                HTML.img(e, attribs={'src':text,
                                     'border': '0'})
                HTML.br(wikifier.output)
            else:
                HTML.Text(e, text)
        else:
            if GoogleCode_IsExternalLink(wikifier, text):
                # External link
                attribs={"href":link, "target": "_blank" }
            else:
                # Internal link
                attribs={"href":text + wikifier.suffix}

            # Simple bracketted link
            e = HTML.a(wikifier.output, text=text, attribs=attribs)
        wikifier.nextMatch = lookMatch.end()

def GoogleCode_UrlLink(wikifier, **kwargs):
    attribs = {"href": wikifier.matchText}
    if GoogleCode_IsExternalLink(wikifier, wikifier.matchText):
        attribs["target"] = "_blank"

    if IMGURL.match(wikifier.matchText):
        HTML.img(wikifier.output, attribs={'src':wikifier.matchText})
        HTML.br(wikifier.output)
    elif YOUTUBEURL.match(wikifier.matchText):
        match = YOUTUBEURL.match(wikifier.matchText)
        # Raw html ;)
        wikifier.output.children.append(YOUTUBEREPL % match.group(1))
    elif VIDEOURL.match(wikifier.matchText):
        # Raw html ;)
        wikifier.output.children.append(VIDEOREPL % wikifier.matchText)
    elif CODEURL.match(wikifier.matchText):
        # Raw html ;)
        # http://([^\.]+).googlecode.com/svn/trunk/([^\#]+)#([^\:]+)(?:\:([^\W]+))?

        codeMatch = CODEURL.match(wikifier.matchText)
        parts = { "class": (codeMatch.group(4) or "").lower()[1:],
                  "file": codeMatch.group(2),
                  "site": codeMatch.group(1)}

        lines = codeMatch.group(3)
        if '-' in lines:
            lines = lines.split('-')
            lines[0] = int(lines[0])
            lines[1] = int(lines[1])
        else:
            lines = [int(lines), int(lines)]

        parts['class'] += ":firstline[%i]" % lines[0]
        url, parts['lines'] = GoogleCode_ReadSVNFile(wikifier, parts['site'],
                                                parts['file'], *lines)
        parts['url'] = url
        parts['lines'] = "".join(parts['lines'])

        wikifier.output.children.append(CODEREPL % parts)
    else:
        HTML.a(wikifier.output, text=wikifier.matchText, attribs=attribs)


def GoogleCode_Table(wikifier, sepRegExp=None, termRegExp=None, **kwargs):
    sibs = wikifier.output.children
    if len(sibs) and getattr(sibs[-1], 'tagname', None) == "table":
        table = sibs[-1]
    else:
        table = HTML.table(wikifier.output)
    row = HTML.tr(table)

    termMatch = termRegExp.search(wikifier.source, wikifier.matchStart)
    if termMatch is None:
        termEnd = termStart = len(wikifier.source)
    else:
        termStart, termEnd = termMatch.start(), termMatch.end()

    # Skip over the leading separator
    sepMatch = sepRegExp.search(wikifier.source, wikifier.matchStart)
    wikifier.nextMatch = wikifier.matchStart = sepMatch.end()
    sepMatch = sepRegExp.search(wikifier.source, wikifier.matchStart)
    attribs = { "style": "border: 1px solid #aaa; padding: 5px;" }

    while sepMatch and sepMatch.end() <= termStart:
        cell = HTML.td(row, attribs=attribs)
        wikifier.subWikifyTerm(cell, sepRegExp)
        wikifier.nextMatch = sepMatch.end()
        sepMatch = sepRegExp.search(wikifier.source, wikifier.nextMatch)

    wikifier.nextMatch = termEnd


def GoogleCode_List(wikifier, lookaheadRegExp=None, termRegExp=None, **kwargs):
    currLevel = 0
    currType = None
    stack = [wikifier.output]
    indents = [currLevel]
    wikifier.nextMatch = wikifier.matchStart

    lookMatch = lookaheadRegExp.search(wikifier.source, wikifier.nextMatch)
    while lookMatch and lookMatch.start() == wikifier.nextMatch:
        # See what kind of list it is
        if lookMatch.group(1):
            listType = "ul"
            itemType = "li"
        elif lookMatch.group(2):
            listType = "ol"
            itemType = "li"

        listLevel = len(lookMatch.group(0))
        wikifier.nextMatch += len(lookMatch.group(0))

        # Check for any changes in list type or indentation
        if listLevel > currLevel:
            # Indent further
            indents.append(listLevel)
            if currLevel == 0:
                target = stack[-1]
            else:
                target = stack[-1].children[-1]

            stack.append(HTML.Node(target, listType))

        elif listLevel < currLevel:
            # Indent less
            while indents[-1] > listLevel:
                stack.pop(-1)
                indents.pop(-1)

        elif listLevel == currLevel and listType != currType:
            # Same level, different kind of list
            stack.pop(-1)
            stack.append(HTML.Node(stack[-1].children[-1], listType))

        currLevel = listLevel
        currType = listType

        # Output the item
        output = HTML.Node(stack[-1],itemType)
        wikifier.subWikifyTerm(output,termRegExp)

        # Roll again
        lookMatch = lookaheadRegExp.search(wikifier.source, wikifier.nextMatch)



GoogleCodeWikiFormat = [
    {
      "name": "tablerow",
      "match": r"^(?:\|\|.+\|\|)",
      "termRegExp": re.compile(r"(\n)", re.M),
      "sepRegExp": re.compile(r"(\|\|)", re.M),
      "handler": GoogleCode_Table
    },

    { "name": "heading",
      "match": r"^={1,6}",
      "termRegExp": re.compile(r"([=]+)", re.M),
      "handler": GoogleCode_Heading
    },

    { "name": "list",
      "match": r"^(?:[ ]+)(?:[\*#])",
      "lookaheadRegExp": re.compile(r"^(?:[ ]+)(?:(\*)|(#))",re.M),
      "termRegExp": re.compile(r"(\n)", re.M),
      "handler": GoogleCode_List
    },



    { "name": "blockquote",
      "match": r"^(?:[ ]+)",
      "termRegExp": re.compile(r"(\n)", re.M),
      "handler": GoogleCode_Blockquote,
      "tagName": "blockquote"
    },

    { "name": "codeword",
      "match": r"\`",
      "initRegExp": re.compile(r"(\`)", re.M),
      "termRegExp": re.compile(r"(\`)", re.M),
      "handler": GoogleCode_Codeblock,
      "tagName": "code"
    },

    { "name": "codeblock",
      "match": r"\{\{\{",
      "initRegExp": re.compile(r"(\{\{\{)", re.M),
      "termRegExp": re.compile(r"(\}\}\})", re.M),
      "handler": GoogleCode_Codeblock,
      "tagName": "pre",
      "attribs": { "class": "codeblock" }
    },

    { "name": "bold",
      "match": r"[\*]",
      "termRegExp": re.compile(r"([\*])", re.M),
      "handler": GoogleCode_SimpleElement,
      "tagName": "b"
    },

    { "name": "italic",
      "match": r"(?:[^\w\b]|^)[\_]",
      "termRegExp": re.compile(r"([\_])[^\w\b]", re.M),
      "handler": GoogleCode_SimpleElement,
      "tagName": "i"
    },

    { "name": "strike",
      "match": r"\~\~",
      "termRegExp": re.compile(r"(\~\~)", re.M),
      "handler": GoogleCode_SimpleElement,
      "tagName": "strike"
    },

    { "name": "superscript",
      "match": r"\^",
      "termRegExp": re.compile(r"(\^)", re.M),
      "handler": GoogleCode_SimpleElement,
      "tagName": "sup"
    },

    { "name": "subscript",
      "match": r",,",
      "termRegExp": re.compile(r"(,,)", re.M),
      "handler": GoogleCode_SimpleElement,
      "tagName": "sub"
    },

    { "name": "prettyLink",
      "match": r"\[(?:(?:[A-Za-z][A-Za-z0-9\_\-]+)|(?:(?:file|http|https|mailto|ftp|irc|news|data):[^\s'\"]+(?:/|\b)))(?: .*?)?\]",
      "lookaheadRegExp": re.compile(r'\[(.*?)(?: (.*?))?\]', re.M),
      "handler": GoogleCode_PrettyLink
    },

    { "name": "wikiword",
      "match": r"(?:\!?(?:[A-Z]+[a-z]+[A-Z][A-Za-z]*)|(?:[A-Z]{2,}[a-z]+))",
      "handler": GoogleCode_WikiWord
    },

    { "name": "urlLink",
      "match": URLSTR,
      "handler": GoogleCode_UrlLink
    },

    { "name": "linebreak",
      "match": r"\n\n",
      "handler": GoogleCode_LineBreak,
      "empty": True
    },

]



class Wikifier:

    def __init__(self, formatters, autolink=False, srcdir=os.getcwd(),
                       multibreak=False, tabwidth=8, suffix=".html",
                       hiLang="Python"):
        # Create the master regex
        forms = [ "(%s)" % r['match'] for r in formatters ]
        self.formatterRegExp = re.compile("|".join(forms), re.M)
        # Save the individual format handlers
        self.formatters = formatters
        self.autolink = autolink
        self.srcdir = srcdir
        self.multibreak = multibreak and True or False
        self.tabwidth = tabwidth
        self.suffix = suffix
        self.defaultHiLang = hiLang

    def _clean(self, text):
        text = text.replace("\r\n", "\n")

        # Out, out, damned tabs
        text = text.replace("\t", " " * self.tabwidth)

        if not self.multibreak:
            # Remove redundant line breaks
            tlen = len(text) + 1
            while tlen > len(text):
                tlen = len(text)
                text = text.replace("\n\n\n", "\n\n")

        while text.startswith("#"):
            # Process any wiki-headers
            line, text = text.split("\n", 1)
            self._header(line)

        return text

    def _header(self, line):
        tagname, content = line.split(" ", 1)
        if tagname == "#summary":
            self.summary = content
        elif tagname == "#labels":
            self.labels = tuple(content.split(","))

    def wikify(self, source, labels=None, summary=None):
        self.labels = labels
        self.summary = summary
        # Clean up the content
        self.source = self._clean(source)
        self.nextMatch = 0
        # Do it
        self.output = HTML.div(None)
        self.subWikifyUnterm()

        return "".join([str(c) for c in self.output.children])

    def findMatch(self, source, start):
        return self.formatterRegExp.search(source, start)

    def subWikifyUnterm(self, output=None):
        oldOutput = self.output
        if output is not None:
            self.output = output

        match = self.findMatch(self.source, self.nextMatch)
        while match:
            # Output any text before the match
            if match.start() > self.nextMatch:
                self.outputText(self.output, self.nextMatch, match.start())

            # Set the match parameters for the handler
            self.matchStart = match.start()
            self.matchLength = len(match.group(0))
            self.matchText = match.group(0)
            self.nextMatch = match.end()

            # Figure out which sub-group matched (zero-indexed)
            t,submatch = [ (t,s) for t, s in enumerate(match.groups()) if s ][0]

            # Handle it
            self.formatters[t]['handler'](self, **self.formatters[t])

            # Go back for more matches
            match = self.findMatch(self.source, self.nextMatch)

        if self.nextMatch < len(self.source):
            self.outputText(self.output, self.nextMatch, len(self.source))
            self.nextMatch = len(self.source)

        # Restore the destination node
        self.output = oldOutput

    def subWikifyTerm(self, output, termRegExp):
        oldOutput = self.output
        if output is not None:
            self.output = output

        # Get the first matches for the formatter and terminator RegExps
        termMatch = termRegExp.search(self.source, self.nextMatch)
        if termMatch:
            match = self.findMatch(self.source[:termMatch.start()], self.nextMatch)
        else:
            match = self.findMatch(self.source, self.nextMatch)

        while termMatch or match:
            # If the terminator comes before the next formatter match, we're done
            if termMatch and (not match or termMatch.start() <= match.start()):
                if termMatch.start() > self.nextMatch:
                    self.outputText(self.output,self.nextMatch,termMatch.start())
                self.matchText = termMatch.group(1)
                self.matchLength = len(self.matchText)
                self.matchStart = termMatch.start()
                self.nextMatch = self.matchStart + self.matchLength
                self.output = oldOutput
                return

            # Output any text before the match
            if match.start() > self.nextMatch:
                self.outputText(self.output, self.nextMatch, match.start())

            # Set the match parameters for the handler
            self.matchStart = match.start()
            self.matchLength = len(match.group(0))
            self.matchText = match.group(0)
            self.nextMatch = match.end()

            # Figure out which sub-group matched (zero-indexed)
            t,submatch = [ (t,s) for t, s in enumerate(match.groups()) if s ][0]

            # Handle it
            self.formatters[t]['handler'](self, **self.formatters[t])

            termMatch = termRegExp.search(self.source, self.nextMatch)
            if termMatch:
                match = self.findMatch(self.source[:termMatch.start()], self.nextMatch)
            else:
                match = self.findMatch(self.source, self.nextMatch)

        if self.nextMatch < len(self.source):
            self.outputText(self.output, self.nextMatch,len(self.source))
            self.nextMatch = len(self.source)

        self.output = oldOutput


    def outputText(self, output, startPos, endPos):
        HTML.Text(output, self.source[startPos:endPos])


DEFAULT_TEMPLATE = '''
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN">
<html>
    <head>
    </head>
    <body>
        <div id="page">

            <div id='header'>
                <br style="clear: both" /><br/>
            </div>

            <div id="pagecontent">
                <div class="index">
<!-- This is a (PRE) block.  Make sure it's left aligned or your toc title will be off. -->
%(toc)s
                </div>

                <i>%(title)s</i>

                <div class="summary">
                    %(summary)s
                </div>

                <div class="narrow">
                    %(wiki)s
                </div>

            </div>
        </div>
    </body>
</html>
'''

DEFAULT_TEMPLATE = '''
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN">
<html>
  <head>
  </head>
  <body>
    <div class="summary">
        %(summary)s
    </div>
    <div class="narrow">
        %(wiki)s
    </div>
  </body>
</html>
'''


def wikify(pages, options=None):
    # See options definition below.
    # Pass any object with those (potential) attributes
    srcdir = getattr(options, 'srcdir', os.getcwd())
    destdir = getattr(options, 'destdir', None)

    # Find all requested files
    onlyStale = False
    if getattr(options, 'all', False):
        pages = [ k for k in os.listdir(srcdir)
                 if k.endswith(".wiki") ]
        onlyStale = True
        if destdir is None:
            destdir = os.getcwd()

    # Create the magic 8-ball
    w = Wikifier(GoogleCodeWikiFormat,
                 autolink=getattr(options, 'autolink', False),
                 tabwidth=getattr(options, 'tabwidth', 8),
                 multibreak=getattr(options, 'multibreak', False),
                 srcdir=srcdir,
                 suffix=".html")

    rets = []
    for wikiname in pages:
        # Clean up the page name
        if wikiname.endswith(".wiki"):
            wikiname = wikiname[:-5]

        wikifilename = os.path.join(srcdir, "%s.wiki" % wikiname)
        if onlyStale:
            # See if the output is fresh, and if so, skip it
            wikidestname = os.path.join(destdir, "%s.html" % wikiname)
            try:
                sstat = os.stat(wikifilename)
            except:
                continue
            try:
                dstat = os.stat(wikidestname)
            except:
                pass
            else:
                if dstat.st_mtime > sstat.st_mtime:
                    continue

        # Load the wiki content
        wikifilename = os.path.join(srcdir, "%s.wiki" % wikiname)
        wikisrc = file(wikifilename).read()

        # Ask a question
        wikified = w.wikify(wikisrc)

        reFind = re.compile(r'<h(\d)>\s*([^\<]*[\S])\s*</h\d>')
        strRepl = r'<h\g<1>><a name="\g<2>">\g<2></a></h\g<1>>'

        # Number the sections
        if getattr(options, 'number', True):
            sectstack = []
            matches = []
            curLevel = 0
            match = reFind.search(wikified)
            while match is not None:
                level = int(match.group(1))

                while level > len(sectstack):
                    sectstack.append(1)

                while len(sectstack) > level:
                    sectstack.pop(-1)

                if curLevel >= level:
                    sectstack[-1] += 1
                curLevel = len(sectstack)

                sectnum = ".".join([str(n) for n in sectstack]) + "."
                matches.append((sectnum, match))
                match = reFind.search(wikified, match.end())

            matches.reverse()
            for sectnum, match in matches:
                wikified = wikified[:match.start()+4] + sectnum + " " + wikified[match.start()+4:]


        # Generate the TOC
        if getattr(options, 'toc', True):
            matches = [ '<b>%s: Contents</b>' % wikiname ]
            for match in reFind.findall(wikified):
                if int(match[0]) > getattr(options, 'levels', 3): continue
                indent = "&nbsp;" * ((int(match[0])) * 2)

                href = "#" + match[1]
                anchor = '%s<a href="%s">%s</a>' % (indent, href, match[1])
                matches.append(anchor)
            toc = "<br>".join(matches)
        else:
            toc = "" #-e -d /home/adam/src/CSpaceWiki/

        # Generate the body links
        if getattr(options, 'links', True):
            wikified = reFind.sub(strRepl, wikified)

        # Find a summary
        summary = ""
        if w.summary is not None:
            summary = w.summary

        if not getattr(options, 'raw', False):
            # Fill the template
            wikified = options.template % {
                    "toc": toc,
                    "title": wikiname,
                    "wiki": wikified,
                    "summary": summary }

        # Save it or write it
        if destdir is not None:
            outputname = os.path.join(destdir, "%s.html" % wikiname)
            file(outputname,"w").write(wikified)

            mainpage = getattr(options, 'mainpage', 'MainPage')
            if wikiname == mainpage:
                rets.append((wikiname, outputname))
                outputname = os.path.join(destdir, "index.html")
                file(outputname,"w").write(wikified)

            wikified = outputname
        rets.append((wikiname, wikified))
    return rets

if __name__ == "__main__":
    from optparse import OptionParser
    import sys

    parser = OptionParser()

    # Output format options
    parser.add_option("-t", "--template", dest="template",
                        help="use TPLTFILE to wrap wiki output", metavar="TPLTFILE")
    parser.add_option("-n", "--number", dest="number", metavar="NUMSTART",
                        help="number the headings in the body and table of contents starting with level NUMSTART")
    parser.add_option("-l", "--levels", dest="levels", type="int",
                        help="create toc to depth LEVELS", metavar="LEVELS")
    parser.add_option("-c", "--skiptoc", dest="toc", action="store_false",
                        help="leave toc out, even if template has slot")
    parser.add_option("-u", "--unlink", dest="links", action="store_false",
                        help="don't create named anchors for toc links")
    parser.add_option("-a", "--autolink", dest="autolink", action="store_false",
                        help="autolink wiki words that don't exist")
    parser.add_option("-w", "--tabwidth", dest="tabwidth", type="int",
                        help="replace tabs by WIDTH spaces", metavar="WIDTH")
    parser.add_option("-m", "--multibreak", dest="multibreak", action="store_true",
                        help="don't collapse multiple line breaks")
    parser.add_option("-r", "--raw", dest="raw", action="store_true",
                        help="raw wiki translation -- no wrapping, no toc, no links")
    parser.add_option("-p", "--mainpage", dest="mainpage", metavar="PAGENAME",
                        help="set main page to PAGENAME")

    # Batch / Location options
    parser.add_option("-s", "--srcdir", dest="srcdir",
                        help="wiki format sources in SRCDIR", metavar="SRCDIR")
    parser.add_option("-d", "--destdir", dest="destdir",
                        help="write html output into DESTDIR", metavar="DESTDIR")
    parser.add_option("-e", "--stale", dest="all", action="store_true",
                        help="convert all wiki files that are stale or missing from DESTDIR")


    parser.set_default('toc', True)
    parser.set_default('links', True)
    parser.set_default('template', None)
    parser.set_default('number', False)
    parser.set_default('levels', 3)
    parser.set_default('tabwidth', 8)
    parser.set_default('multibreak', False)
    parser.set_default('mainpage', "MainPage")  # Identity of index

    parser.set_default('srcdir', os.getcwd())
    parser.set_default('destdir', None)
    parser.set_default('all', False)

    # Parse the command line
    (options, args) = parser.parse_args()

    if options.template is None:
        options.template = DEFAULT_TEMPLATE
    elif os.path.exists(options.template):
        options.template = file(options.template).read()
    else:
        print "Template not found: %s" % options.template
        parser.print_usage()
        sys.exit()
    #sys.exit()
    for wikiname, htmldata in wikify(args, options):
        if options.destdir:
            #print wikiname + ":",
            if htmldata is not None:
                pass
                #print htmldata
            else:
                print "Complete."
        elif htmldata is not None:
            print htmldata



