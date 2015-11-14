# -*- coding: utf-8 -*-
"""
EvMore - pager mechanism

This is a pager for displaying long texts and allows stepping up and
down in the text (the name comes from the traditional 'more' unix
command).

To use, simply pass the text through the EvMore object:

    from evennia.utils.evmore import EvMore

    text = some_long_text_output()
    EvMore(caller, text, always_page=False, **kwargs)

One can also use the convenience function msg from this module:

    from evennia.utils import evmore

    text = some_long_text_output()
    evmore.msg(caller, text, **kwargs)

Where always_page decides if the pager is used also if the text is not
long enough to need to scroll and **kwargs will be passed on to the
caller.msg() construct (text will be using the pager restrictor).

"""
from builtins import object, range

from django.conf import settings
from evennia import Command, CmdSet
from evennia.commands import cmdhandler

_CMD_NOMATCH = cmdhandler.CMD_NOMATCH
_CMD_NOINPUT = cmdhandler.CMD_NOINPUT

# we need to use NAWS for this
_SCREEN_WIDTH = settings.CLIENT_DEFAULT_WIDTH
_SCREEN_HEIGHT = settings.CLIENT_DEFAULT_HEIGHT

# text

_DISPLAY = \
"""{text}
({{wmore{{n [{pageno}/{pagemax}] retur{{wn{{n|{{wb{{nack|{{wt{{nop|{{we{{nnd|{{wa{{nbort)"""


class CmdMore(Command):
    """
    Manipulate the text paging
    """
    key = _CMD_NOINPUT
    aliases = ["abort", "a", "next", "n", "back", "b", "top", "t", "end", "e"]
    auto_help = False

    def func(self):
        """
        Implement the command
        """
        more = self.caller.ndb._more
        cmd = self.cmdstring

        if cmd in ("abort", "a"):
            more.page_quit()
        elif cmd in ("back", "b"):
            more.page_back()
        elif cmd in ("top", "t"):
            more.page_top()
        elif cmd in ("end", "e"):
            more.page_end()
        else:
            # return or n, next
            more.page_next()


class CmdSetMore(CmdSet):
    """
    Stores the more command
    """
    key = "more_commands"
    priority = 110

    def at_cmdset_creation(self):
        self.add(CmdMore)


class EvMore(object):
    """
    The main pager object
    """
    def __init__(self, caller, text, always_page=False, **kwargs):
        """
        Initialization of the text handler.

        Args:
            caller (Object or Player): Entity reading the text.
            text (str): The text to put under paging.
            always_page (bool, optional): If `False`, the
                pager will only kick in if `text` is too big
                to fit the screen.
            kwargs (any, optional): These will be passed on
                to the `caller.msg` method.

        """
        self._caller = caller
        self._kwargs = kwargs
        lines = text.split("\n")
        self._pages = []
        self._npages = []
        self._npos = []
        # we use the first session here
        sessions = caller.sessions.get()
        if not sessions:
            return
        session = sessions[0]
        # set up individual pages for different sessions
        height = session.protocol_flags.get("SCREENHEIGHT", {0:_SCREEN_HEIGHT})[0] - 2
        self._pages = ["\n".join(lines[i:i+height]) for i in range(0, len(lines), height)]
        self._npages = len(self._pages)
        self._npos = 0

        if self._npages <= 1 and not always_page:
            # no need for paging; just pass-through.
            caller.msg(text=text, **kwargs)
        else:
            # go into paging mode
            # first pass on the msg kwargs
            caller.ndb._more = self
            caller.cmdset.add(CmdSetMore)

            # goto top of the text
            self.page_top()

    def _display(self):
        """
        Pretty-print the page.
        """
        pos = self._pos
        text = self._pages[pos]
        page = _DISPLAY.format(text=text,
                               pageno=pos + 1,
                               pagemax=self._npages)
        self._caller.msg(text=page, **self._kwargs)

    def page_top(self):
        """
        Display the top page
        """
        self._pos = 0
        self._display()

    def page_end(self):
        """
        Display the bottom page.
        """
        self._pos = self._npages - 1
        self._display()

    def page_next(self):
        """
        Scroll the text to the next page. Quit if already at the end
        of the page.
        """
        if self._pos >= self._npages - 1:
            # exit if we are already at the end
            self.page_quit()
        else:
            self._pos += 1
            self._display()

    def page_back(self):
        """
        Scroll the text back up, at the most to the top.
        """
        self._pos = max(0, self._pos - 1)
        self._display()

    def page_quit(self):
        """
        Quit the pager
        """
        del self._caller.ndb._more
        self._caller.cmdset.remove(CmdSetMore)


def msg(caller, text="", **kwargs):
    """
    More-supported version of msg, mimicking the
    normal msg method.
    """
    always_more = kwargs.pop("always_more", False)
    EvMore(caller, text, always_more, **kwargs)

