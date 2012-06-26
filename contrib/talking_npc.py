"""

Evennia Talkative NPC

Contribution - Griatch 2011

This is a simple NPC object capable of holding a
simple menu-driven conversation. Create it by
creating an object of typeclass contrib.talking_npc.TalkingNPC,
For example using @create:

 @create John : contrib.talking_npc.TalkingNPC

Walk up to it and give the talk command
to strike up a conversation. If there are many
talkative npcs in the same room you will get to
choose which one's talk command to call (Evennia
handles this automatically).

Note that this is only a prototype class, showcasing
the uses of the menusystem module. It is NOT a full
mob implementation.

"""

from contrib import menusystem
from game.gamesrc.objects.baseobjects import Object
from game.gamesrc.commands.basecmdset import CmdSet
from game.gamesrc.commands.basecommand import MuxCommand


#
# The talk command
#

class CmdTalk(MuxCommand):
    """
    talks to an npc

    Usage:
      talk

    This command is only available if a talkative non-player-character (NPC)
    is actually present. It will strike up a conversation with that NPC
    and give you options on what to talk about.
    """
    key = "talk"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        "Implements the command."

        # self.obj is the NPC this is defined on
        obj = self.obj

        self.caller.msg("(You walk up and talk to %s.)" % self.obj.key)

        # conversation is a dictionary of keys, each pointing to a dictionary defining
        # the keyword arguments to the MenuNode constructor.
        conversation = obj.db.conversation
        if not conversation:
            self.caller.msg("%s says: 'Sorry, I don't have time to talk right now.'" % (self.obj.key))
            return

        # build all nodes by loading them from the conversation tree.
        menu = menusystem.MenuTree(self.caller)
        for key, kwargs in conversation.items():
            menu.add(menusystem.MenuNode(key, **kwargs))
        menu.start()

class TalkingCmdSet(CmdSet):
    "Stores the talk command."
    key = "talkingcmdset"
    def at_cmdset_creation(self):
        "populates the cmdset"
        self.add(CmdTalk())

#
# Discussion tree. See contrib.menusystem.MenuNode for the keywords.
# (This could be in a separate module too)
#

CONV = {"START":{"text": "Hello there, how can I help you?",
                 "links":["info1", "info2"],
                 "linktexts":["Hey, do you know what this 'Evennia' thing is all about?",
                              "What's your name, little NPC?"],
                 "keywords":None,
                 "code":None},
        "info1":{"text": "Oh, Evennia is where you are right now! Don't you feel the power?",
                 "links":["info3", "info2", "END"],
                 "linktexts":["Sure, *I* do, not sure how you do though. You are just an NPC.",
                              "Sure I do. What's yer name, NPC?",
                              "Ok, bye for now then."],
                 "keywords":None,
                 "code":None},
        "info2":{"text":"My name is not really important ... I'm just an NPC after all.",
                 "links":["info3", "info1"],
                 "linktexts":["I didn't really want to know it anyhow.",
                              "Okay then, so what's this 'Evennia' thing about?"],
                 "keywords":None,
                 "code":None},
        "info3":{"text":"Well ... I'm sort of busy so, have to go. NPC business. Important stuff. You wouldn't understand.",
                 "links":["END", "info2"],
                 "linktexts":["Oookay ... I won't keep you. Bye.",
                              "Wait, why don't you tell me your name first?"],
                 "keywords":None,
                 "code":None},
        }

class TalkingNPC(Object):
    """
    This implements a simple Object using the talk command and using the
    conversation defined above. .
    """

    def at_object_creation(self):
        "This is called when object is first created."
        # store the conversation.
        self.db.conversation = CONV
        self.db.desc = "This is a talkative NPC."
        # assign the talk command to npc
        self.cmdset.add_default(TalkingCmdSet, permanent=True)
