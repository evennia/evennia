# Talkative NPC example

Contribution by Griatch 2011. Updated by grungies1138, 2016

This is an example of a static NPC object capable of holding a simple menu-driven
conversation. Suitable for example as a quest giver or merchant.

## Installation

Create the NPC by creating an object of typeclass `contrib.tutorials.talking_npc.TalkingNPC`,
For example:

    create/drop John : contrib.tutorials.talking_npc.TalkingNPC

Use `talk` in the same room as the NPC to start a conversation.

If there are many talkative npcs in the same room you will get to choose which
one's talk command to call (Evennia handles this automatically).

This use of EvMenu is very simplistic; See EvMenu for a lot more complex
possibilities.
