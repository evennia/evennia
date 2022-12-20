# -*- coding: utf-8 -*-
"""
EvMore - pager mechanism

This is a pager for displaying long texts and allows stepping up and down in
the text (the name comes from the traditional 'more' unix command).

To use, simply pass the text through the EvMore object:


```python

    from evennia.utils.evmore import EvMore

    text = some_long_text_output()
    EvMore(caller, text, always_page=False, session=None, justify_kwargs=None, **kwargs)
```

One can also use the convenience function `msg` from this module to avoid
having to set up the `EvMenu` object manually:

```python

    from evennia.utils import evmore

    text = some_long_text_output()
    evmore.msg(caller, text, always_page=False, session=None, justify_kwargs=None, **kwargs)
```

The `always_page` argument  decides if the pager is used also if the text is not long
enough to need to scroll, `session` is used to determine which session to relay
to and `justify_kwargs` are kwargs to pass to utils.utils.justify in order to
change the formatting of the text. The remaining `**kwargs` will be passed on to
the `caller.msg()` construct every time the page is updated.

----

"""
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models.query import QuerySet
from django.utils.translation import gettext as _

from evennia.commands import cmdhandler
from evennia.commands.cmdset import CmdSet
from evennia.commands.command import Command
from evennia.utils.ansi import ANSIString
from evennia.utils.utils import dedent, inherits_from, justify, make_iter

_CMD_NOMATCH = cmdhandler.CMD_NOMATCH
_CMD_NOINPUT = cmdhandler.CMD_NOINPUT

# we need to use NAWS for this
_SCREEN_WIDTH = settings.CLIENT_DEFAULT_WIDTH
_SCREEN_HEIGHT = settings.CLIENT_DEFAULT_HEIGHT

_EVTABLE = None

_LBR = ANSIString("\n")

# text

_DISPLAY = """{text}
|n(|wPage|n [{pageno}/{pagemax}] |wn|next|n || |wp|nrevious || |wt|nop || |we|nnd || |wq|nuit)"""


class CmdMore(Command):
    """
    Manipulate the text paging. Catch no-input with aliases.
    """

    key = _CMD_NOINPUT
    aliases = ["quit", "q", "abort", "a", "next", "n", "previous", "p", "top", "t", "end", "e"]
    auto_help = False

    def func(self):
        """
        Implement the command
        """
        more = self.caller.ndb._more
        if not more and hasattr(self.caller, "account"):
            more = self.caller.account.ndb._more
        if not more:
            self.caller.msg("Error in loading the pager. Contact an admin.")
            return

        cmd = self.cmdstring

        if cmd in ("abort", "a", "q"):
            more.page_quit()
        elif cmd in ("previous", "p"):
            more.page_back()
        elif cmd in ("top", "t", "look", "l"):
            more.page_top()
        elif cmd in ("end", "e"):
            more.page_end()
        else:
            # return or n, next
            more.page_next()


class CmdMoreExit(Command):
    """
    Any non-more command will exit the pager.

    """

    key = _CMD_NOMATCH

    def func(self):
        """
        Exit pager and re-fire the failed command.

        """
        more = self.caller.ndb._more
        more.page_quit()

        # re-fire the command (in new cmdset)
        self.caller.execute_cmd(self.raw_string)


class CmdSetMore(CmdSet):
    """
    Stores the more command
    """

    key = "more_commands"
    priority = 110
    mergetype = "Replace"

    def at_cmdset_creation(self):
        self.add(CmdMore())
        self.add(CmdMoreExit())


# resources for handling queryset inputs
def queryset_maxsize(qs):
    return qs.count()


class EvMore(object):
    """
    The main pager object
    """

    def __init__(
        self,
        caller,
        inp,
        always_page=False,
        session=None,
        justify=False,
        justify_kwargs=None,
        exit_on_lastpage=False,
        exit_cmd=None,
        page_formatter=str,
        **kwargs,
    ):

        """
        Initialization of the EvMore pager.

        Args:
            caller (Object or Account): Entity reading the text.
            inp (str, EvTable, Paginator or iterator): The text or data to put under paging.

                - If a string, paginage normally. If this text contains
                  one or more `\\\\f` format symbol, automatic pagination and justification
                  are force-disabled and page-breaks will only happen after each `\\\\f`.
                - If `EvTable`, the EvTable will be paginated with the same
                  setting on each page if it is too long. The table
                  decorations will be considered in the size of the page.
                - Otherwise `inp` is converted to an iterator, where each step is
                  expected to be a line in the final display. Each line
                  will be run through `iter_callable`.

            always_page (bool, optional): If `False`, the
                pager will only kick in if `inp` is too big
                to fit the screen.
            session (Session, optional): If given, this session will be used
                to determine the screen width and will receive all output.
            justify (bool, optional): If set, auto-justify long lines. This must be turned
                off for fixed-width or formatted output, like tables. It's force-disabled
                if `inp` is an EvTable.
            justify_kwargs (dict, optional): Keywords for the justify function. Used only
                if `justify` is True. If this is not set, default arguments will be used.
            exit_on_lastpage (bool, optional): If reaching the last page without the
                page being completely filled, exit pager immediately. If unset,
                another move forward is required to exit. If set, the pager
                exit message will not be shown.
            exit_cmd (str, optional): If given, this command-string will be executed on
                the caller when the more page exits. Note that this will be using whatever
                cmdset the user had *before* the evmore pager was activated (so none of
                the evmore commands will be available when this is run).
            kwargs (any, optional): These will be passed on to the `caller.msg` method.

        Examples:

            ```python
            super_long_text = " ... "
            EvMore(caller, super_long_text)
            ```
            Paginator
            ```python
            from django.core.paginator import Paginator
            query = ObjectDB.objects.all()
            pages = Paginator(query, 10)  # 10 objs per page
            EvMore(caller, pages)
            ```
            Every page an EvTable
            ```python
            from evennia import EvTable
            def _to_evtable(page):
                table = ... # convert page to a table
                return EvTable(*headers, table=table, ...)
            EvMore(caller, pages, page_formatter=_to_evtable)
            ```

        """
        self._caller = caller
        self._always_page = always_page

        if not session:
            # if not supplied, use the first session to
            # determine screen size
            sessions = caller.sessions.get()
            if not sessions:
                return
            session = sessions[0]
        self._session = session

        self._justify = justify
        self._justify_kwargs = justify_kwargs
        self.exit_on_lastpage = exit_on_lastpage
        self.exit_cmd = exit_cmd
        self._exit_msg = _("|xExited pager.|n")
        self._kwargs = kwargs

        self._data = None

        self._pages = []
        self._npos = 0

        self._npages = 1
        self._paginator = self.paginator_index
        self._page_formatter = str

        # set up individual pages for different sessions
        height = max(4, session.protocol_flags.get("SCREENHEIGHT", {0: _SCREEN_HEIGHT})[0] - 4)
        self.width = session.protocol_flags.get("SCREENWIDTH", {0: _SCREEN_WIDTH})[0]
        # always limit number of chars to 10 000 per page
        self.height = min(10000 // max(1, self.width), height)

        # does initial parsing of input
        self.init_pages(inp)

        # kick things into gear
        self.start()

    # EvMore functional methods

    def display(self, show_footer=True):
        """
        Pretty-print the page.
        """
        pos = 0
        text = "[no content]"
        if self._npages > 0:
            pos = self._npos
            text = self.page_formatter(self.paginator(pos))
        if show_footer:
            page = _DISPLAY.format(text=text, pageno=pos + 1, pagemax=self._npages)
        else:
            page = text
        # check to make sure our session is still valid
        sessions = self._caller.sessions.get()
        if not sessions:
            self.page_quit()
            return
        # this must be an 'is', not == check
        if not any(ses for ses in sessions if self._session is ses):
            self._session = sessions[0]
        self._caller.msg(text=page, session=self._session, **self._kwargs)

    def page_top(self):
        """
        Display the top page
        """
        self._npos = 0
        self.display()

    def page_end(self):
        """
        Display the bottom page.
        """
        self._npos = self._npages - 1
        self.display()

    def page_next(self):
        """
        Scroll the text to the next page. Quit if already at the end
        of the page.
        """
        if self._npos >= self._npages - 1:
            # exit if we are already at the end
            self.page_quit()
        else:
            self._npos += 1
            if self.exit_on_lastpage and self._npos >= (self._npages - 1):
                self.display(show_footer=False)
                self.page_quit(quiet=True)
            else:
                self.display()

    def page_back(self):
        """
        Scroll the text back up, at the most to the top.
        """
        self._npos = max(0, self._npos - 1)
        self.display()

    def page_quit(self, quiet=False):
        """
        Quit the pager
        """
        del self._caller.ndb._more
        if not quiet:
            self._caller.msg(text=self._exit_msg, **self._kwargs)
        self._caller.cmdset.remove(CmdSetMore)
        if self.exit_cmd:
            self._caller.execute_cmd(self.exit_cmd, session=self._session)

    def start(self):
        """
        Starts the pagination
        """
        if self._npages <= 1 and not self._always_page:
            # no need for paging; just pass-through.
            self.display(show_footer=False)
        else:
            # go into paging mode
            # first pass on the msg kwargs
            self._caller.ndb._more = self
            self._caller.cmdset.add(CmdSetMore)

            # goto top of the text
            self.page_top()

    # default paginators - responsible for extracting a specific page number

    def paginator_index(self, pageno):
        """Paginate to specific, known index"""
        return self._data[pageno]

    def paginator_slice(self, pageno):
        """
        Paginate by slice. This is done with an eye on memory efficiency (usually for
        querysets); to avoid fetching all objects at the same time.

        """
        return self._data[pageno * self.height : pageno * self.height + self.height]

    def paginator_django(self, pageno):
        """
        Paginate using the django queryset Paginator API. Note that his is indexed from 1.
        """
        return self._data.page(pageno + 1)

    # default helpers to set up particular input types

    def init_evtable(self, table):
        """The input is an EvTable."""
        if table.height:
            # enforced height of each paged table, plus space for evmore extras
            self.height = table.height - 4

        # convert table to string
        text = str(table)
        self._justify = False
        self._justify_kwargs = None  # enforce
        self.init_str(text)

    def init_queryset(self, qs):
        """The input is a queryset"""
        nsize = qs.count()  # we assume each will be a line
        self._npages = nsize // self.height + (0 if nsize % self.height == 0 else 1)
        self._data = qs

    def init_django_paginator(self, pages):
        """
        The input is a django Paginator object.
        """
        self._npages = pages.num_pages
        self._data = pages

    def init_iterable(self, inp):
        """The input is something other than a string - convert to iterable of strings"""
        inp = make_iter(inp)
        nsize = len(inp)
        self._npages = nsize // self.height + (0 if nsize % self.height == 0 else 1)
        self._data = inp

    def init_f_str(self, text):
        """
        The input contains `\\f` markers. We use `\\f` to indicate the user wants to
        enforce their line breaks on their own. If so, we do no automatic
        line-breaking/justification at all.

        Args:
            text (str): The string to format with f-markers.

        """
        self._data = text.split("\f")
        self._npages = len(self._data)

    def init_str(self, text):
        """The input is a string"""

        if self._justify:
            # we must break very long lines into multiple ones. Note that this
            # will also remove spurious whitespace.
            justify_kwargs = self._justify_kwargs or {}
            width = self._justify_kwargs.get("width", self.width)
            justify_kwargs["width"] = width
            justify_kwargs["align"] = self._justify_kwargs.get("align", "l")
            justify_kwargs["indent"] = self._justify_kwargs.get("indent", 0)

            lines = []
            for line in text.split("\n"):
                if len(line) > width:
                    lines.extend(justify(line, **justify_kwargs).split("\n"))
                else:
                    lines.append(line)
        else:
            # no justification. Simple division by line
            lines = text.split("\n")

        self._data = [
            _LBR.join(lines[i : i + self.height]) for i in range(0, len(lines), self.height)
        ]
        self._npages = len(self._data)

    # Hooks for customizing input handling and formatting (override in a child class)

    def init_pages(self, inp):
        """
        Initialize the pagination. By default, will analyze input type to determine
        how pagination automatically.

        Args:
            inp (any): Incoming data to be paginated. By default, handles pagination of
                strings, querysets, django.Paginator, EvTables and any iterables with strings.

        Notes:
            If overridden, this method must perform the following  actions:

            - read and re-store `self._data` (the incoming data set) if needed for pagination to
              work.
            - set `self._npages` to the total number of pages. Default is 1.
            - set `self._paginator` to a callable that will take a page number 1...N and return
              the data to display on that page (not any decorations or next/prev buttons). If only
              wanting to change the paginator, override `self.paginator` instead.
            - set `self._page_formatter` to a callable that will receive the page from
              `self._paginator` and format it with one element per line. Default is `str`. Or
              override `self.page_formatter` directly instead.

            By default, helper methods are called that perform these actions
            depending on supported inputs.

        """
        if inherits_from(inp, "evennia.utils.evtable.EvTable"):
            # an EvTable
            self.init_evtable(inp)
            self._paginator = self.paginator_index
        elif isinstance(inp, QuerySet):
            # a queryset
            self.init_queryset(inp)
            self._paginator = self.paginator_slice
        elif isinstance(inp, Paginator):
            self.init_django_paginator(inp)
            self._paginator = self.paginator_django
        elif not isinstance(inp, str):
            # anything else not a str
            self.init_iterable(inp)
            self._paginator = self.paginator_slice
        elif "\f" in inp:
            # string with \f line-break markers in it
            self.init_f_str(inp)
            self._paginator = self.paginator_index
        else:
            # a string
            self.init_str(inp)
            self._paginator = self.paginator_index

    def paginator(self, pageno):
        """
        Paginator. The data operated upon is in `self._data`.

        Args:
            pageno (int): The page number to view, from 0...N-1
        Returns:
            str: The page to display (without any decorations, those are added
                by EvMore).

        """
        return self._paginator(pageno)

    def page_formatter(self, page):
        """
        Page formatter. Every page passes through this method. Override
        it to customize behavior per-page. A common use is to generate a new
        EvTable for every page (this is more efficient than to generate one huge
        EvTable across many pages and feed it into EvMore all at once).

        Args:
            page (any): A piece of data representing one page to display. This must

        Returns:
            str: A ready-formatted page to display. Extra footer with help about
                switching to the next/prev page will be added automatically

        """
        return self._page_formatter(page)


# helper function


def msg(
    caller,
    text="",
    always_page=False,
    session=None,
    justify=False,
    justify_kwargs=None,
    exit_on_lastpage=True,
    **kwargs,
):
    """
    EvMore-supported version of msg, mimicking the normal msg method.

    """
    EvMore(
        caller,
        text,
        always_page=always_page,
        session=session,
        justify=justify,
        justify_kwargs=justify_kwargs,
        exit_on_lastpage=exit_on_lastpage,
        **kwargs,
    )


msg.__doc__ += dedent(EvMore.__init__.__doc__)
