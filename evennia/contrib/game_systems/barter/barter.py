"""
Barter system

Evennia contribution - Griatch 2012


This implements a full barter system - a way for players to safely
trade items between each other using code rather than simple free-form
talking.  The advantage of this is increased buy/sell safety but it
also streamlines the process and makes it faster when doing many
transactions (since goods are automatically exchanged once both
agree).

This system is primarily intended for a barter economy, but can easily
be used in a monetary economy as well -- just let the "goods" on one
side be coin objects (this is more flexible than a simple "buy"
command since you can mix coins and goods in your trade).

In this module, a "barter" is generally referred to as a "trade".


- Trade example

A trade (barter) action works like this: A and B are the parties.

1) opening a trade

A: trade B: Hi, I have a nice extra sword. You wanna trade?
B sees: A says: "Hi, I have a nice extra sword. You wanna trade?"
   A wants to trade with you. Enter 'trade A <emote>' to accept.
B: trade A: Hm, I could use a good sword ...
A sees: B says: "Hm, I could use a good sword ...
   B accepts the trade. Use 'trade help' for aid.
B sees: You are now trading with A. Use 'trade help' for aid.

2) negotiating

A: offer sword: This is a nice sword. I would need some rations in trade.
B sees: A says: "This is a nice sword. I would need some rations in trade."
   [A offers Sword of might.]
B evaluate sword
B sees: <Sword's description and possibly stats>
B: offer ration: This is a prime ration.
A sees: B says: "This is a prime ration."
  [B offers iron ration]
A: say Hey, this is a nice sword, I need something more for it.
B sees: A says: "Hey this is a nice sword, I need something more for it."
B: offer sword,apple: Alright. I will also include a magic apple. That's my last offer.
A sees: B says: "Alright, I will also include a magic apple. That's my last offer."
  [B offers iron ration and magic apple]
A accept: You are killing me here, but alright.
B sees: A says: "You are killing me here, but alright."
  [A accepts your offer. You must now also accept.]
B accept: Good, nice making business with you.
  You accept the deal. Deal is made and goods changed hands.
A sees: B says: "Good, nice making business with you."
  B accepts the deal. Deal is made and goods changed hands.

At this point the trading system is exited and the negotiated items
are automatically exchanged between the parties. In this example B was
the only one changing their offer, but also A could have changed their
offer until the two parties found something they could agree on. The
emotes are optional but useful for RP-heavy worlds.

- Technical info

The trade is implemented by use of a TradeHandler. This object is a
common place for storing the current status of negotiations. It is
created on the object initiating the trade, and also stored on the
other party once that party agrees to trade. The trade request times
out after a certain time - this is handled by a Script. Once trade
starts, the CmdsetTrade cmdset is initiated on both parties along with
the commands relevant for the trading.

- Ideas for NPC bartering:

This module is primarily intended for trade between two players. But
it can also in principle be used for a player negotiating with an
AI-controlled NPC. If the NPC uses normal commands they can use it
directly -- but more efficient is to have the NPC object send its
replies directly through the tradehandler to the player. One may want
to add some functionality to the decline command, so players can
decline specific objects in the NPC offer (decline <object>) and allow
the AI to maybe offer something else and make it into a proper
barter.  Along with an AI that "needs" things or has some sort of
personality in the trading, this can make bartering with NPCs at least
moderately more interesting than just plain 'buy'.

- Installation:

Just import the CmdTrade command into (for example) the default
cmdset. This will make the trade (or barter) command available
in-game.

"""

from evennia.commands.cmdset import CmdSet
from evennia.commands.command import Command
from evennia.scripts.scripts import DefaultScript

TRADE_TIMEOUT = 60  # timeout for B to accept trade


class TradeTimeout(DefaultScript):
    """
    This times out the trade request, in case player B did not reply in time.
    """

    def at_script_creation(self):
        """
        Called when script is first created
        """
        self.key = "trade_request_timeout"
        self.desc = "times out trade requests"
        self.interval = TRADE_TIMEOUT
        self.start_delay = True
        self.repeats = 1
        self.persistent = False

    def at_repeat(self):
        """
        called once
        """
        if self.ndb.tradeevent:
            self.obj.ndb.tradeevent.finish(force=True)
        self.obj.msg("Trade request timed out.")

    def is_valid(self):
        """
        Only valid if the trade has not yet started
        """
        return self.obj.ndb.tradeevent and not self.obj.ndb.tradeevent.trade_started


class TradeHandler(object):
    """
    Objects of this class handles the ongoing trade, notably storing the current
    offers from each side and wether both have accepted or not.
    """

    def __init__(self, part_a, part_b):
        """
        Initializes the trade. This is called when part A tries to
        initiate a trade with part B. The trade will not start until
        part B repeats this command (B will then call the self.join()
        command)

        Args:
            part_a (object): The party trying to start barter.
            part_b (object): The party asked to barter.

        Notes:
            We also store the back-reference from the respective party
            to this object.

        """
        # parties
        self.part_a = part_a
        self.part_b = part_b

        self.part_a.cmdset.add(CmdsetTrade())
        self.trade_started = False
        self.part_a.ndb.tradehandler = self
        # trade variables
        self.part_a_offers = []
        self.part_b_offers = []
        self.part_a_accepted = False
        self.part_b_accepted = False

    def msg_other(self, sender, string):
        """
        Relay a message to the *other* party without needing to know
        which party that is. This allows the calling command to not
        have to worry about which party they are in the handler.

        Args:
            sender (object): One of A or B. The method will figure
                out the *other* party to send to.
            string (str): Text to send.
        """
        if self.part_a == sender:
            self.part_b.msg(string)
        elif self.part_b == sender:
            self.part_a.msg(string)
        else:
            # no match, relay to oneself
            sender.msg(string) if sender else self.part_a.msg(string)

    def get_other(self, party):
        """
        Returns the other party of the trade

        Args:
            party (object): One of the parties of the negotiation

        Returns:
            party_other (object): The other party, not the first party.

        """
        if self.part_a == party:
            return self.part_b
        if self.part_b == party:
            return self.part_a
        return None

    def join(self, part_b):
        """
        This is used once B decides to join the trade

        Args:
            part_b (object): The party accepting the barter.

        """
        if self.part_b == part_b:
            self.part_b.ndb.tradehandler = self
            self.part_b.cmdset.add(CmdsetTrade())
            self.trade_started = True
            return True
        return False

    def unjoin(self, part_b):
        """
        This is used if B decides not to join the trade.

        Args:
            part_b (object): The party leaving the barter.

        """
        if self.part_b == part_b:
            self.finish(force=True)
            return True
        return False

    def offer(self, party, *args):
        """
        Change the current standing offer. We leave it up to the
        command to do the actual checks that the offer consists
        of real, valid, objects.

        Args:
            party (object): Who is making the offer
            args (objects or str): Offerings.

        """
        if self.trade_started:
            # reset accept statements whenever an offer changes
            self.part_a_accepted = False
            self.part_b_accepted = False
            if party == self.part_a:
                self.part_a_offers = list(args)
            elif party == self.part_b:
                self.part_b_offers = list(args)
            else:
                raise ValueError

    def list(self):
        """
        List current offers.

        Returns:
            offers (tuple): A tuple with two lists, (A_offers, B_offers).

        """
        return self.part_a_offers, self.part_b_offers

    def search(self, offername):
        """
        Search current offers.

        Args:
            offername (str or int): Object to search for, or its index in
                the list of offered items.

        Returns:
            offer (object): An object on offer, based on the search criterion.

        """
        all_offers = self.part_a_offers + self.part_b_offers
        if isinstance(offername, int):
            # an index to return
            if 0 <= offername < len(all_offers):
                return all_offers[offername]

        all_keys = [offer.key for offer in all_offers]
        try:
            imatch = all_keys.index(offername)
            return all_offers[imatch]
        except ValueError:
            for offer in all_offers:
                if offer.aliases.get(offername):
                    return offer
        return None

    def accept(self, party):
        """
        Accept the current offer.

        Args:
            party (object): The party accepting the deal.

        Returns:
            result (object): `True` if this closes the deal, `False`
                otherwise

        Notes:
            This will only close the deal if both parties have
            accepted independently. This is done by calling the
            `finish()` method.

        """
        if self.trade_started:
            if party == self.part_a:
                self.part_a_accepted = True
            elif party == self.part_b:
                self.part_b_accepted = True
            else:
                raise ValueError
            return self.finish()  # try to close the deal
        return False

    def decline(self, party):
        """
        Decline the offer (or change one's mind).

        Args:
            party (object): Party declining the deal.

        Returns:
            did_decline (bool): `True` if there was really an
                `accepted` status to change, `False` otherwise.

        Notes:
            If previously having used the `accept` command, this
            function will only work as long as the other party has not
            yet accepted.

        """
        if self.trade_started:
            if party == self.part_a:
                if self.part_a_accepted:
                    self.part_a_accepted = False
                    return True
                return False
            elif party == self.part_b:
                if self.part_b_accepted:
                    self.part_b_accepted = False
                    return True
                return False
            else:
                raise ValueError
        return False

    def finish(self, force=False):
        """
        Conclude trade - move all offers and clean up

        Args:
            force (bool, optional): Force cleanup regardless of if the
                trade was accepted or not (if not, no goods will change
                hands but trading will stop anyway)
        Returns:
            result (bool): If the finish was successful.

        """
        fin = False
        if self.trade_started and self.part_a_accepted and self.part_b_accepted:
            # both accepted - move objects before cleanup
            for obj in self.part_a_offers:
                obj.location = self.part_b
            for obj in self.part_b_offers:
                obj.location = self.part_a
            fin = True
        if fin or force:
            # cleanup
            self.part_a.cmdset.delete("cmdset_trade")
            self.part_b.cmdset.delete("cmdset_trade")
            self.part_a_offers = None
            self.part_b_offers = None
            self.part_a.scripts.stop("trade_request_timeout")
            # this will kill it also from B
            del self.part_a.ndb.tradehandler
            if self.part_b.ndb.tradehandler:
                del self.part_b.ndb.tradehandler
            return True
        return False


# trading commands (will go into CmdsetTrade, initialized by the
# CmdTrade command further down).


class CmdTradeBase(Command):
    """
    Base command for Trade commands to inherit from. Implements the
    custom parsing.
    """

    def parse(self):
        """
        Parse the relevant parts and make it easily
        available to the command
        """
        self.args = self.args.strip()
        self.tradehandler = self.caller.ndb.tradehandler
        self.part_a = self.tradehandler.part_a
        self.part_b = self.tradehandler.part_b

        self.other = self.tradehandler.get_other(self.caller)
        self.msg_other = self.tradehandler.msg_other

        self.trade_started = self.tradehandler.trade_started
        self.emote = ""
        self.str_caller = "Your trade action: %s"
        self.str_other = "%s:s trade action: " % self.caller.key + "%s"
        if ":" in self.args:
            self.args, self.emote = [part.strip() for part in self.args.rsplit(":", 1)]
            self.str_caller = 'You say, "' + self.emote + '"\n  [%s]'
            if self.caller.has_account:
                self.str_other = '|c%s|n says, "' % self.caller.key + self.emote + '"\n  [%s]'
            else:
                self.str_other = '%s says, "' % self.caller.key + self.emote + '"\n  [%s]'


# trade help


class CmdTradeHelp(CmdTradeBase):
    """
    help command for the trade system.

    Usage:
        trade help

    Displays help for the trade commands.
    """

    key = "trade help"
    locks = "cmd:all()"
    help_category = "Trade"

    def func(self):
        """Show the help"""
        string = """
        Trading commands

        |woffer <objects> [:emote]|n
            offer one or more objects for trade. The emote can be used for
            RP/arguments. A new offer will require both parties to re-accept
            it again.
        |waccept [:emote]|n
            accept the currently standing offer from both sides. Also 'agree'
            works. Once both have accepted, the deal is finished and goods
            will change hands.
        |wdecline [:emote]|n
            change your mind and remove a previous accept (until other
            has also accepted)
        |wstatus|n
            show the current offers on each side of the deal. Also 'offers'
            and 'deal' works.
        |wevaluate <nr> or <offer>|n
            examine any offer in the deal. List them with the 'status' command.
        |wend trade|n
            end the negotiations prematurely. No trade will take place.

        You can also use |wemote|n, |wsay|n etc to discuss
        without making a decision or offer.
        """
        self.caller.msg(string)


# offer


class CmdOffer(CmdTradeBase):
    """
    offer one or more items in trade.

    Usage:
      offer <object> [, object2, ...][:emote]

    Offer objects in trade. This will replace the currently
    standing offer.
    """

    key = "offer"
    locks = "cmd:all()"
    help_category = "Trading"

    def func(self):
        """implement the offer"""

        caller = self.caller
        if not self.args:
            caller.msg("Usage: offer <object> [, object2, ...] [:emote]")
            return
        if not self.trade_started:
            caller.msg("Wait until the other party has accepted to trade with you.")
            return

        # gather all offers
        offers = [part.strip() for part in self.args.split(",")]
        offerobjs = []
        for offername in offers:
            obj = caller.search(offername)
            if not obj:
                return
            offerobjs.append(obj)
        self.tradehandler.offer(self.caller, *offerobjs)

        # output
        if len(offerobjs) > 1:
            objnames = (
                ", ".join("|w%s|n" % obj.key for obj in offerobjs[:-1])
                + " and |w%s|n" % offerobjs[-1].key
            )
        else:
            objnames = "|w%s|n" % offerobjs[0].key

        caller.msg(self.str_caller % ("You offer %s" % objnames))
        self.msg_other(caller, self.str_other % ("They offer %s" % objnames))


# accept


class CmdAccept(CmdTradeBase):
    """
    accept the standing offer

    Usage:
      accept [:emote]
      agreee [:emote]

    This will accept the current offer. The other party must also accept
    for the deal to go through. You can use the 'decline' command to change
    your mind as long as the other party has not yet accepted. You can inspect
    the current offer using the 'offers' command.
    """

    key = "accept"
    aliases = ["agree"]
    locks = "cmd:all()"
    help_category = "Trading"

    def func(self):
        """accept the offer"""
        caller = self.caller
        if not self.trade_started:
            caller.msg("Wait until the other party has accepted to trade with you.")
            return
        if self.tradehandler.accept(self.caller):
            # deal finished. Trade ended and cleaned.
            caller.msg(
                self.str_caller
                % "You |gaccept|n the deal. |gDeal is made and goods changed hands.|n"
            )
            self.msg_other(
                caller,
                self.str_other % "%s |gaccepts|n the deal."
                " |gDeal is made and goods changed hands.|n" % caller.key,
            )
        else:
            # a one-sided accept.
            caller.msg(
                self.str_caller
                % "You |Gaccept|n the offer. %s must now also accept."
                % self.other.key
            )
            self.msg_other(
                caller,
                self.str_other % "%s |Gaccepts|n the offer. You must now also accept." % caller.key,
            )


# decline


class CmdDecline(CmdTradeBase):
    """
    decline the standing offer

    Usage:
      decline [:emote]

    This will decline a previously 'accept'ed offer (so this allows you to
    change your mind). You can only use this as long as the other party
    has not yet accepted the deal. Also, changing the offer will automatically
    decline the old offer.
    """

    key = "decline"
    locks = "cmd:all()"
    help_category = "Trading"

    def func(self):
        """decline the offer"""
        caller = self.caller
        if not self.trade_started:
            caller.msg("Wait until the other party has accepted to trade with you.")
            return
        offer_a, offer_b = self.tradehandler.list()
        if not offer_a or not offer_b:
            caller.msg("No offers have been made yet, so there is nothing to decline.")
            return
        if self.tradehandler.decline(self.caller):
            # changed a previous accept
            caller.msg(self.str_caller % "You change your mind, |Rdeclining|n the current offer.")
            self.msg_other(
                caller,
                self.str_other
                % "%s changes their mind, |Rdeclining|n the current offer."
                % caller.key,
            )
        else:
            # no acceptance to change
            caller.msg(self.str_caller % "You |Rdecline|n the current offer.")
            self.msg_other(caller, self.str_other % "%s declines the current offer." % caller.key)


# evaluate

# Note: This version only shows the description. If your particular game
# lists other important properties of objects (such as weapon damage, weight,
# magical properties, ammo requirements or whatnot), then you need to add this
# here.


class CmdEvaluate(CmdTradeBase):
    """
    evaluate objects on offer

    Usage:
      evaluate <offered object>

    This allows you to examine any object currently on offer, to
    determine if it's worth your while.
    """

    key = "evaluate"
    aliases = ["eval"]
    locks = "cmd:all()"
    help_category = "Trading"

    def func(self):
        """evaluate an object"""
        caller = self.caller
        if not self.args:
            caller.msg("Usage: evaluate <offered object>")
            return
        # we also accept indices
        try:
            ind = int(self.args)
            self.args = ind - 1
        except Exception:
            # not a valid index - ignore
            pass

        offer = self.tradehandler.search(self.args)
        if not offer:
            caller.msg("No offer matching '%s' was found." % self.args)
            return
        # show the description
        caller.msg(offer.db.desc)


# status


class CmdStatus(CmdTradeBase):
    """
    show a list of the current deal

    Usage:
      status
      deal
      offers

    Shows the currently suggested offers on each sides of the deal. To
    accept the current deal, use the 'accept' command. Use 'offer' to
    change your deal. You might also want to use 'say', 'emote' etc to
    try to influence the other part in the deal.
    """

    key = "status"
    aliases = ["offers", "deal"]
    locks = "cmd:all()"
    help_category = "Trading"

    def func(self):
        """Show the current deal"""
        caller = self.caller
        part_a_offers, part_b_offers = self.tradehandler.list()
        count = 1
        part_a_offerlist = []
        for offer in part_a_offers:
            part_a_offerlist.append("\n |w%i|n %s" % (count, offer.key))
            count += 1
        if not part_a_offerlist:
            part_a_offerlist = "\n <nothing>"
        part_b_offerlist = []
        for offer in part_b_offers:
            part_b_offerlist.append("\n |w%i|n %s" % (count, offer.key))
            count += 1
        if not part_b_offerlist:
            part_b_offerlist = "\n <nothing>"

        string = "|gOffered by %s:|n%s\n|yOffered by %s:|n%s" % (
            self.part_a.key,
            "".join(part_a_offerlist),
            self.part_b.key,
            "".join(part_b_offerlist),
        )
        accept_a = self.tradehandler.part_a_accepted and "|gYes|n" or "|rNo|n"
        accept_b = self.tradehandler.part_b_accepted and "|gYes|n" or "|rNo|n"
        string += "\n\n%s agreed: %s, %s agreed: %s" % (
            self.part_a.key,
            accept_a,
            self.part_b.key,
            accept_b,
        )
        string += "\n Use 'offer', 'eval' and 'accept'/'decline' to trade. See also 'trade help'."
        caller.msg(string)


# finish


class CmdFinish(CmdTradeBase):
    """
    end the trade prematurely

    Usage:
      end trade [:say]
      finish trade [:say]

    This ends the trade prematurely. No trade will take place.

    """

    key = "end trade"
    aliases = "finish trade"
    locks = "cmd:all()"
    help_category = "Trading"

    def func(self):
        """end trade"""
        caller = self.caller
        self.tradehandler.finish(force=True)
        caller.msg(self.str_caller % "You |raborted|n trade. No deal was made.")
        self.msg_other(
            caller, self.str_other % "%s |raborted|n trade. No deal was made." % caller.key
        )


# custom Trading cmdset


class CmdsetTrade(CmdSet):
    """
    This cmdset is added when trade is initated. It is handled by the
    trade event handler.
    """

    key = "cmdset_trade"

    def at_cmdset_creation(self):
        """Called when cmdset is created"""
        self.add(CmdTradeHelp())
        self.add(CmdOffer())
        self.add(CmdAccept())
        self.add(CmdDecline())
        self.add(CmdEvaluate())
        self.add(CmdStatus())
        self.add(CmdFinish())


# access command - once both have given this, this will create the
# trading cmdset to start trade.


class CmdTrade(Command):
    """
    Initiate trade with another party

    Usage:
      trade <other party> [:say]
      trade <other party> accept [:say]
      trade <other party> decline [:say]

    Initiate trade with another party. The other party needs to repeat
    this command with trade accept/decline within a minute in order to
    properly initiate the trade action. You can use the decline option
    yourself if you want to retract an already suggested trade. The
    optional say part works like the say command and allows you to add
    info to your choice.
    """

    key = "trade"
    aliases = ["barter"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        """Initiate trade"""

        if not self.args:
            if self.caller.ndb.tradehandler and self.caller.ndb.tradeevent.trade_started:
                self.caller.msg("You are already in a trade. Use 'end trade' to abort it.")
            else:
                self.caller.msg("Usage: trade <other party> [accept|decline] [:emote]")
            return
        self.args = self.args.strip()

        # handle the emote manually here
        selfemote = ""
        theiremote = ""
        if ":" in self.args:
            self.args, emote = [part.strip() for part in self.args.rsplit(":", 1)]
            selfemote = 'You say, "%s"\n  ' % emote
            if self.caller.has_account:
                theiremote = '|c%s|n says, "%s"\n  ' % (self.caller.key, emote)
            else:
                theiremote = '%s says, "%s"\n  ' % (self.caller.key, emote)

        # for the sake of this command, the caller is always part_a; this
        # might not match the actual name in tradehandler (in the case of
        # using this command to accept/decline a trade invitation).
        part_a = self.caller
        accept = "accept" in self.args
        decline = "decline" in self.args
        if accept:
            part_b = self.args.rstrip("accept").strip()
        elif decline:
            part_b = self.args.rstrip("decline").strip()
        else:
            part_b = self.args
        part_b = self.caller.search(part_b)
        if not part_b:
            return
        if part_a == part_b:
            part_a.msg("You play trader with yourself.")
            return

        # messages
        str_init_a = "You ask to trade with %s. They need to accept within %s secs."
        str_init_b = "%s wants to trade with you. Use |wtrade %s accept/decline [:emote]|n to answer (within %s secs)."
        str_noinit_a = "%s declines the trade"
        str_noinit_b = "You decline trade with %s."
        str_start_a = "%s starts to trade with you. See |wtrade help|n for aid."
        str_start_b = "You start to trade with %s. See |wtrade help|n for aid."

        if not (accept or decline):
            # initialization of trade
            if self.caller.ndb.tradehandler:
                # trying to start trade without stopping a previous one
                if self.caller.ndb.tradehandler.trade_started:
                    string = "You are already in trade with %s. You need to end trade first."
                else:
                    string = "You are already trying to initiate trade with %s. You need to decline that trade first."
                self.caller.msg(string % part_b.key)
            elif part_b.ndb.tradehandler and part_b.ndb.tradehandler.part_b == part_a:
                # this is equivalent to part_a accepting a trade from part_b (so roles are reversed)
                part_b.ndb.tradehandler.join(part_a)
                part_b.msg(theiremote + str_start_a % part_a.key)
                part_a.msg(selfemote + str_start_b % part_b.key)
            else:
                # initiate a new trade
                TradeHandler(part_a, part_b)
                part_a.msg(selfemote + str_init_a % (part_b.key, TRADE_TIMEOUT))
                part_b.msg(theiremote + str_init_b % (part_a.key, part_a.key, TRADE_TIMEOUT))
                part_a.scripts.add(TradeTimeout)
            return
        elif accept:
            # accept a trade proposal from part_b (so roles are reversed)
            if part_a.ndb.tradehandler:
                # already in a trade
                part_a.msg(
                    "You are already in trade with %s. You need to end that first." % part_b.key
                )
                return
            if part_b.ndb.tradehandler.join(part_a):
                part_b.msg(theiremote + str_start_a % part_a.key)
                part_a.msg(selfemote + str_start_b % part_b.key)
            else:
                part_a.msg("No trade proposal to accept.")
            return
        else:
            # decline trade proposal from part_b (so roles are reversed)
            if part_a.ndb.tradehandler and part_a.ndb.tradehandler.part_b == part_a:
                # stopping an invite
                part_a.ndb.tradehandler.finish(force=True)
                part_b.msg(theiremote + "%s aborted trade attempt with you." % part_a)
                part_a.msg(selfemote + "You aborted the trade attempt with %s." % part_b)
            elif part_b.ndb.tradehandler and part_b.ndb.tradehandler.unjoin(part_a):
                part_b.msg(theiremote + str_noinit_a % part_a.key)
                part_a.msg(selfemote + str_noinit_b % part_b.key)
            else:
                part_a.msg("No trade proposal to decline.")
            return
