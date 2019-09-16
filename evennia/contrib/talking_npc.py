"""
Evennia Talkative NPC

Contribution - Griatch 2011, grungies1138, 2016

This is a static NPC object capable of holding a simple menu-driven
conversation. It's just meant as an example. Create it by creating an
object of typeclass contrib.talking_npc.TalkingNPC, For example using
@create:

    @create/drop John : contrib.talking_npc.TalkingNPC

Walk up to it and give the talk command to strike up a conversation.
If there are many talkative npcs in the same room you will get to
choose which one's talk command to call (Evennia handles this
automatically). This use of EvMenu is very simplistic; See EvMenu for
a lot more complex possibilities.


"""

from evennia import DefaultObject, CmdSet, default_cmds
from evennia.utils.evmenu import EvMenu


# Menu implementing the dialogue tree


def menu_start_node(caller):
    text = "'Hello there, how can I help you?'"

    options = (
        {"desc": "Hey, do you know what this 'Evennia' thing is all about?", "goto": "info1"},
        {"desc": "What's your name, little NPC?", "goto": "info2"},
    )

    return text, options


def info1(caller):
    text = "'Oh, Evennia is where you are right now! Don't you feel the power?'"

    options = (
        {"desc": "Sure, *I* do, not sure how you do though. You are just an NPC.", "goto": "info3"},
        {"desc": "Sure I do. What's yer name, NPC?", "goto": "info2"},
        {"desc": "Ok, bye for now then.", "goto": "END"},
    )

    return text, options


def info2(caller):
    text = "'My name is not really important ... I'm just an NPC after all.'"

    options = (
        {"desc": "I didn't really want to know it anyhow.", "goto": "info3"},
        {"desc": "Okay then, so what's this 'Evennia' thing about?", "goto": "info1"},
    )

    return text, options


def info3(caller):
    text = "'Well ... I'm sort of busy so, have to go. NPC business. Important stuff. You wouldn't understand.'"

    options = (
        {"desc": "Oookay ... I won't keep you. Bye.", "goto": "END"},
        {"desc": "Wait, why don't you tell me your name first?", "goto": "info2"},
    )

    return text, options


def END(caller):
    text = "'Goodbye, then.'"

    options = ()

    return text, options


#
# The talk command (sits on the NPC)
#


class CmdTalk(default_cmds.MuxCommand):
    """
   Talks to an npc

   Usage:
     talk

   This command is only available if a talkative non-player-character
   (NPC) is actually present. It will strike up a conversation with
   that NPC and give you options on what to talk about.
   """

    key = "talk"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        "Implements the command."

        # self.obj is the NPC this is defined on
        self.caller.msg("(You walk up and talk to %s.)" % self.obj.key)

        # Initiate the menu. Change this if you are putting this on
        # some other custom NPC class.
        EvMenu(self.caller, "evennia.contrib.talking_npc", startnode="menu_start_node")


class TalkingCmdSet(CmdSet):
    "Stores the talk command."
    key = "talkingcmdset"

    def at_cmdset_creation(self):
        "populates the cmdset"
        self.add(CmdTalk())


class TalkingNPC(DefaultObject):
    """
    This implements a simple Object using the talk command and using
    the conversation defined above.
    """

    def at_object_creation(self):
        "This is called when object is first created."
        self.db.desc = "This is a talkative NPC."
        # assign the talk command to npc
        self.cmdset.add_default(TalkingCmdSet, permanent=True)
