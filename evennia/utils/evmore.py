# -*- coding: utf-8 -*-
"""
EvMore - pager mechanism

This is a pager for displaying long texts and allows stepping up and
down in the text (the name comes from the traditional 'more' unix
command).

To use, simply pass the text through the EvMore object:

    from evennia.utils.evmore import EvMore

    text = some_long_text_output()
    EvMore(caller, text, always_page=False, session=None, justify_kwargs=None, **kwargs)

One can also use the convenience function msg from this module:

    from evennia.utils import evmore

    text = some_long_text_output()
    evmore.msg(caller, text, always_page=False, session=None, justify_kwargs=None, **kwargs)

Where always_page decides if the pager is used also if the text is not
long enough to need to scroll, session is used to determine which session to relay to
and justify_kwargs are kwargs to pass to utils.utils.justify in order to change the formatting
of the text. The remaining **kwargs will be passed on to the
caller.msg() construct every time the page is updated.

"""
from django.conf import settings
from django.db.models.query import QuerySet
from evennia import Command, CmdSet
from evennia.commands import cmdhandler
from evennia.utils.utils import make_iter, inherits_from, justify

_CMD_NOMATCH = cmdhandler.CMD_NOMATCH
_CMD_NOINPUT = cmdhandler.CMD_NOINPUT

# we need to use NAWS for this
_SCREEN_WIDTH = settings.CLIENT_DEFAULT_WIDTH
_SCREEN_HEIGHT = settings.CLIENT_DEFAULT_HEIGHT

_EVTABLE = None

# text

_DISPLAY = """{text}
(|wmore|n [{pageno}/{pagemax}] retur|wn|n|||wb|nack|||wt|nop|||we|nnd|||wq|nuit)"""


class CmdMore(Command):
    """
    Manipulate the text paging
    """

    key = _CMD_NOINPUT
    aliases = ["quit", "q", "abort", "a", "next", "n", "back", "b", "top", "t", "end", "e"]
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
        elif cmd in ("back", "b"):
            more.page_back()
        elif cmd in ("top", "t", "look", "l"):
            more.page_top()
        elif cmd in ("end", "e"):
            more.page_end()
        else:
            # return or n, next
            more.page_next()


class CmdMoreLook(Command):
    """
    Override look to display window and prevent OOCLook from firing
    """

    key = "look"
    aliases = ["l"]
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
        more.display()


class CmdSetMore(CmdSet):
    """
    Stores the more command
    """

    key = "more_commands"
    priority = 110

    def at_cmdset_creation(self):
        self.add(CmdMore())
        self.add(CmdMoreLook())


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
        text,
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
        Initialization of the text handler.

        Args:
            caller (Object or Account): Entity reading the text.
            text (str, EvTable or iterator): The text or data to put under paging.
                - If a string, paginage normally. If this text contains
                   one or more `\f` format symbol, automatic pagination and justification
                   are force-disabled and page-breaks will only happen after each `\f`.
                - If `EvTable`, the EvTable will be paginated with the same
                   setting on each page if it is too long. The table
                   decorations will be considered in the size of the page.
                - Otherwise `text` is converted to an iterator, where each step is
                   expected to be a line in the final display. Each line
                   will be run through `iter_callable`.
            always_page (bool, optional): If `False`, the
                pager will only kick in if `text` is too big
                to fit the screen.
            session (Session, optional): If given, this session will be used
                to determine the screen width and will receive all output.
            justify (bool, optional): If set, auto-justify long lines. This must be turned
                off for fixed-width or formatted output, like tables. It's force-disabled
                if `text` is an EvTable.
            justify_kwargs (dict, optional): Keywords for the justifiy function. Used only
                if `justify` is True. If this is not set, default arguments will be used.
            exit_on_lastpage (bool, optional): If reaching the last page without the
                page being completely filled, exit pager immediately. If unset,
                another move forward is required to exit. If set, the pager
                exit message will not be shown.
            exit_cmd (str, optional): If given, this command-string will be executed on
                the caller when the more page exits. Note that this will be using whatever
                cmdset the user had *before* the evmore pager was activated (so none of
                the evmore commands will be available when this is run).
            page_formatter (callable, optional): If given, this function will be passed the
                contents of each extracted page. This is useful when paginating
                data consisting something other than a string or a list of strings. Especially
                queryset data is likely to always need this argument specified. Note however,
                that all size calculations assume this function to return one single line
                per element on the page!
            kwargs (any, optional): These will be passed on to the `caller.msg` method.

        Examples:
            super_long_text = " ... "
            EvMore(caller, super_long_text)

            from django.core.paginator import Paginator
            query = ObjectDB.objects.all()
            pages = Paginator(query, 10)  # 10 objs per page
            EvMore(caller, pages)   # will repr() each object per line, 10 to a page

            multi_page_table = [ [[..],[..]], ...]
            EvMore(caller, multi_page_table, use_evtable=True,
                   evtable_args=("Header1", "Header2"),
                   evtable_kwargs={"align": "r", "border": "tablecols"})

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
        self._exit_msg = "Exited |wmore|n pager."
        self._page_formatter = page_formatter
        self._kwargs = kwargs

        self._data = None
        self._paginator = None
        self._pages = []
        self._npages = 1
        self._npos = 0

        # set up individual pages for different sessions
        height = max(4, session.protocol_flags.get("SCREENHEIGHT", {0: _SCREEN_HEIGHT})[0] - 4)
        self.width = session.protocol_flags.get("SCREENWIDTH", {0: _SCREEN_WIDTH})[0]
        # always limit number of chars to 10 000 per page
        self.height = min(10000 // max(1, self.width), height)

        if inherits_from(text, "evennia.utils.evtable.EvTable"):
            # an EvTable
            self.init_evtable(text)
        elif isinstance(text, QuerySet):
            # a queryset
            self.init_queryset(text)
        elif not isinstance(text, str):
            # anything else not a str
            self.init_iterable(text)
        elif "\f" in text:
            # string with \f line-break markers in it
            self.init_f_str(text)
        else:
            # a string
            self.init_str(text)

        # kick things into gear
        self.start()

    # page formatter

    def format_page(self, page):
        """
        Page formatter. Uses the page_formatter callable by default.
        This allows to easier override the class if needed.
        """
        return self._page_formatter(page)

    # paginators - responsible for extracting a specific page number

    def paginator_index(self, pageno):
        """Paginate to specific, known index"""
        return self._data[pageno]

    def paginator_slice(self, pageno):
        """
        Paginate by slice. This is done with an eye on memory efficiency (usually for
        querysets); to avoid fetching all objects at the same time.
        """
        return self._data[pageno * self.height : pageno * self.height + self.height]

    # inits for different input types

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
        self._paginator = self.paginator_slice

    def init_iterable(self, inp):
        """The input is something other than a string - convert to iterable of strings"""
        inp = make_iter(inp)
        nsize = len(inp)
        self._npages = nsize // self.height + (0 if nsize % self.height == 0 else 1)
        self._data = inp
        self._paginator = self.paginator_slice

    def init_f_str(self, text):
        """
        The input contains \f markers. We use \f to indicate the user wants to
        enforce their line breaks on their own. If so, we do no automatic
        line-breaking/justification at all.
        """
        self._data = text.split("\f")
        self._npages = len(self._data)
        self._paginator = self.paginator_index

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
            "\n".join(lines[i : i + self.height]) for i in range(0, len(lines), self.height)
        ]
        self._npages = len(self._data)
        self._paginator = self.paginator_index

    # display helpers and navigation

    def display(self, show_footer=True):
        """
        Pretty-print the page.
        """
        pos = self._npos
        text = self.format_page(self._paginator(pos))
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

    Args:
        caller (Object or Account): Entity reading the text.
        text (str, EvTable or iterator): The text or data to put under paging.
            - If a string, paginage normally. If this text contains
              one or more `\f` format symbol, automatic pagination is disabled
              and page-breaks will only happen after each `\f`.
            - If `EvTable`, the EvTable will be paginated with the same
                setting on each page if it is too long. The table
                decorations will be considered in the size of the page.
            - Otherwise `text` is converted to an iterator, where each step is
              is expected to be a line in the final display, and each line
              will be run through repr().
        always_page (bool, optional): If `False`, the
            pager will only kick in if `text` is too big
            to fit the screen.
        session (Session, optional): If given, this session will be used
            to determine the screen width and will receive all output.
        justify (bool, optional): If set, justify long lines in output. Disable for
            fixed-format output, like tables.
        justify_kwargs (dict, bool or None, optional): If given, this should
            be valid keyword arguments to the utils.justify() function. If False,
            no justification will be done.
        exit_on_lastpage (bool, optional): Immediately exit pager when reaching the last page.
        use_evtable (bool, optional): If True, each page will be rendered as an
            EvTable. For this to work, `text` must be an iterable, where each element
            is the table (list of list) to render on that page.
        evtable_args (tuple, optional): The args to use for EvTable on each page.
        evtable_kwargs (dict, optional): The kwargs to use for EvTable on each
            page (except `table`, which is supplied by EvMore per-page).
        kwargs (any, optional): These will be passed on
            to the `caller.msg` method.

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
