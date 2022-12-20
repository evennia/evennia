# Barter system

Contribution by Griatch, 2012

This implements a full barter system - a way for players to safely
trade items between each other in code rather than simple `give/get`
commands. This increases both safety (at no time will one player have 
both goods and payment in-hand) and speed, since agreed goods will 
be moved automatically). By just replacing one side with coin objects,
(or a mix of coins and goods), this also works fine for regular money 
transactions.

## Installation

Just import the CmdsetTrade command into (for example) the default
cmdset. This will make the trade (or barter) command available
in-game.

```python
# in mygame/commands/default_cmdsets.py

from evennia.contrib.game_systems import barter  # <---

# ...
class CharacterCmdSet(default_cmds.CharacterCmdSet):
    # ...
    def at cmdset_creation(self):
        # ...
        self.add(barter.CmdsetTrade)  # <---

```

## Usage

In this module, a "barter" is generally referred to as a "trade".

Below is an example of a barter sequence. A and B are the parties.
The `A>` and `B>` are their inputs.

1) opening a trade

    A> trade B: Hi, I have a nice extra sword. You wanna trade?

    B sees:
    A says: "Hi, I have a nice extra sword. You wanna trade?"
       A wants to trade with you. Enter 'trade A <emote>' to accept.

    B> trade A: Hm, I could use a good sword ...

    A sees:
    B says: "Hm, I could use a good sword ...
       B accepts the trade. Use 'trade help' for aid.

    B sees:
    You are now trading with A. Use 'trade help' for aid.

2) negotiating

    A> offer sword: This is a nice sword. I would need some rations in trade.

    B sees: A says: "This is a nice sword. I would need some rations in trade."
       [A offers Sword of might.]

    B> evaluate sword
    B sees:
    <Sword's description and possibly stats>

    B> offer ration: This is a prime ration.

    A sees:
    B says: "This is a prime ration."
      [B offers iron ration]

    A> say Hey, this is a nice sword, I need something more for it.

    B sees:
    A says: "Hey this is a nice sword, I need something more for it."

    B> offer sword,apple: Alright. I will also include a magic apple. That's my last offer.

    A sees:
    B says: "Alright, I will also include a magic apple. That's my last offer."
      [B offers iron ration and magic apple]

    A> accept: You are killing me here, but alright.

    B sees: A says: "You are killing me here, but alright."
      [A accepts your offer. You must now also accept.]

    B> accept: Good, nice making business with you.
      You accept the deal. Deal is made and goods changed hands.

    A sees: B says: "Good, nice making business with you."
      B accepts the deal. Deal is made and goods changed hands.

At this point the trading system is exited and the negotiated items
are automatically exchanged between the parties. In this example B was
the only one changing their offer, but also A could have changed their
offer until the two parties found something they could agree on. The
emotes are optional but useful for RP-heavy worlds.

## Technical info

The trade is implemented by use of a TradeHandler. This object is a
common place for storing the current status of negotiations. It is
created on the object initiating the trade, and also stored on the
other party once that party agrees to trade. The trade request times
out after a certain time - this is handled by a Script. Once trade
starts, the CmdsetTrade cmdset is initiated on both parties along with
the commands relevant for the trading.

## Ideas for NPC bartering

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
