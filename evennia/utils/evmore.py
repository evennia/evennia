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
        lines = text.split("\n")
        self._pages = []
        self._npages = []
        self._npos = []
        # we use the first session here
        session = caller.sessions[0]
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
            caller.msg(**kwargs)
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
        self._caller.msg(page)

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
        print "page_next:", self._pos
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



class CmdTestMore(Command):
    """
    Test the more functionality.
    """
    key = "testmore"

    def func(self):
        testtext = """
        Chapter Four

        “So,” Emperor Palpatine said, his eyes glinting from the
        shadows beneath the peak of his hood. “It is as I suspected.
        Moff Glovstoak is a traitor.”

        “He’s at least an embezzler, my lord,” Mara said. “I don’t yet
        know whether or not he’s committed actual treason.”

        “I consider theft of Imperial funds to be treason,” the
        Emperor countered. “Your part in this is now ended, my
        child–others will carry on from here. You have done well.”

        “Thank you,” Mara said, feeling the warmth of his approval ﬂow
        through her. “Then unless there’s something more urgent
        pending, I’d like permission to do an investigation of the six
        artworks I found in Glovstoak’s safe. The ones I examined
        appear to be from a batch of ten that were stolen from a
        gallery ﬁve years ago during an attack on a Rebel cell on
        Krintrino.”

        The Emperor’s face darkened. “So as well as being an
        embezzler, Glovstoak may also be connected with the Rebel
        Alliance?”

        “Or he may have a connection with the Imperial forces who
        carried out the attack,” Mara pointed out, a little
        cautiously. The Emperor was a wise and good man, but he had an
        odd tendency sometimes to see Rebels and Rebel conspiracies
        where they might not actually exist. “Or it could have been
        pirates or thieves who simply took advantage of the attack’s
        chaos to grab and run. The interesting point is that Glovstoak
        apparently bought them through an auction house, which
        suggests he and the seller wanted a stamp of legitimacy put on
        the transfer.”

        “You said ten were stolen,” the Emperor said. “Yet only six
        were in Glovstoak’s safe?” “Yes,” Mara conﬁrmed. “And all six
        were apparently bought at the same time about eighteen months
        ago.”

        “Where are the other four?”

        “As far as I know, they’re still missing,” Mara said. “That’s
        one of the questions I’d like an answer to. Another is why the
        original owner suddenly decided he needed such a large inﬂux
        of cash a year and a half ago.”

        For a minute the Emperor remained silent, and Mara felt a
        ﬂicker of satisfaction. Private transfers of valuable objects
        happened all the time across the Empire, for any number of
        legitimate or borderline-shady reasons. Such questions coming
        from many of the Emperor’s other advisers and assistants would
        likely have been dismissed out of hand as irrelevant.

        But Mara was the Emperor’s Hand, recruited and trained
        personally by him, and he trusted her instincts. “The loss of
        the Death Star was a great shock to even my strongest
        supporters,” he said at last. “Some, perhaps, might be
        wondering if my Empire is indeed the likely winner in this
        conﬂict with the Rebel Alliance.”

        “Of course it is,” Mara said automatically.

        The Emperor gave her another thin smile. “Indeed,” he agreed.
        “But not everyone sees things as clearly as you and I. If
        Glovstoak is not connected to the Rebellion, perhaps one of
        our wealthier citizens has decided to play both sides. Tell
        me, what is the current Rebel presence in Shelsha sector?”

        “I don’t know yet,” Mara said. “I was planning to comm
        Shelkonwa and ask Governor Choard’s ofﬁce to prepare a summary
        for me.”

        “Don’t,” the Emperor said, the corners of his lips turning
        down with contempt. “Barshnis Choard is a competent
        administrator, but he has far too many ties with the wealthy
        and powerful of his sector. He might leak news of your
        investigation to the very people you seek. No, you will
        instead use my personal library for your research.”

        Mara bowed her head. “Thank you, my lord.”

        The Emperor held out his hand to her. “Go,” he said.

        Mara stepped forward and took his outstretched hand, feeling a
        fresh wave of warmth and strength ﬂow into her, then stepped
        back again. “One other thing, my lord,” she said. “When you
        have Moff Glovstoak and his administration arrested, I would
        ask that a member of his staff, General Deerian, be exempted
        from punishment.”

        The Emperor regarded her thoughtfully. “You believe him to be
        innocent of Glovstoak’s treason?”

        “I’m certain of it,” Mara said. “He’s also an honest and
        honorable man. I don’t wish to see the Empire deprived of his
        service.”

        The other’s lip may have twitched slightly at the word
        honorable. But he merely nodded. “As you wish, my child,” he
        said. “I will have General Deerian transferred immediately to
        a position here on Imperial Center, where he will remain
        untouched by Glovstoak’s imminent destruction.”

        “Thank you,” Mara said. Turning, she strode across the expanse
        of the throne room, passed between the silent red-robed Royal
        Guards, and stepped into the turbolift.

        The Emperor’s library was a large and very private place, used
        only by a few of his top people, and only with his express
        permission. Normally, there were a handful of attendants on
        hand to assist, but as Mara walked between the tall stacks of
        data card ﬁle cabinets toward the retrieval stations at the
        center she was struck by the unusual silence. Apparently all
        the attendants had suddenly found a need to be elsewhere.

        As she rounded the last cabinet she discovered the reason for
        their absence. Seated alone at one of the three computer
        stations was Darth Vader.

        “Lord Vader,” she said politely as she stepped past, her eyes
        ﬂicking automatically to the display screen in front of him.

        His arm came up, just high enough to block her view.
        “Emperor’s Hand,” he greeted her in turn, his voice deep and
        stiff and darker even than usual. “What do you want?”

        “I was given permission to do some research,” Mara said,
        continuing past him and seating herself at one of the other
        stations.

        But even as she turned on the console and started keying for
        her data search, she could sense his brooding attention switch
        from his research to Mara herself. Vader had always been
        polite enough, but even without Mara’s Force sensitivity it
        would have been abundantly clear that he didn’t like her.


        She’d never ﬁgured out why that was. Certainly their goals
        were the same: service to the Emperor and his New Order.
        Perhaps he thought her training had taken too much of the
        Emperor’s time and attention, or perhaps he suspected her of
        trying to supplant him in the great man’s eyes.

        Both thoughts were ridiculous, of course. Mara had her work to
        do, and Vader had his, and there was no point trying to
        second-guess the Emperor’s wisdom in the way he employed
        either of them.

        But she had yet to ﬁnd a way to get that message through to
        Vader.

        “You seek information on the Rebels,” Vader said.

        “Don’t we all?” Mara said drily. “Speciﬁcally, I’m interested
        in the ones in Shelsha sector. Would you happen to know
        anything about that?”

        “There are no known or suspected bases in the sector,” the
        Dark Lord rumbled. “The single major listening post was raided
        and destroyed a few days ago. I suspect there to also be some
        important supply lines running through the sector, but that
        has yet to be veriﬁed.”

        “Any important sympathizers?”

        The sense of coldness around him deepened. “There are
        sympathizers everywhere,” he said. “As well as others who
        conspire to overthrow their superiors.”

        Mara felt an unpleasant trickle run through her. “Lord Vader,
        rest assured that I have no intention–”

        “Good day, Emperor’s Hand,” Vader cut her off. With a swirl of
        black cloak, he stood, turning off the console as he did so.
        Turning his back, he strode away.

        “Thank you for your assistance, Lord Vader,” Mara called after
        him.

        The other didn’t reply, the sense of coldness fading as he
        departed. The door slid open at his gesture, and he strode
        from the library.

        Mara took a deep breath, let it out in a weary sigh. What was
        he worried about, anyway? Loyalty was, after all, one of the
        Emperor’s greatest qualities; loyalty to all who were loyal to
        him. How could Vader even think his Master would push him
        aside for anyone else? Especially for someone as young and
        inexperienced as Mara?

        Shaking her head, she turned back to her console, forcing her
        mind back to her job. So the Rebels had supply lines through
        Shelsha sector. That was good to know. She ﬁnished keying in
        her request for general Rebel data, then added a search for
        major and minor trafﬁc lanes, out-ofthe-way spaceports, and
        any known centers of smuggling or other criminal activity.


        The computer set to work, and Mara sat back to wait . . . and
        as she hunched her tired shoulders, her eyes drifted over to
        Vader’s console. The Dark Lord was never very pleasant, but as
        she thought back on their brief encounter it seemed to her
        that he’d been even more on edge than usual.

        Maybe she could ﬁnd out why.
        """
        msg(self.caller, testtext)
