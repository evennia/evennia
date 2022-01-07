# Talkative NPC example

Contribution - Griatch 2011, grungies1138, 2016

This is a static NPC object capable of holding a simple menu-driven
conversation. It's just meant as an example.

## Installation

Create the NPC by creating an object of typeclass `contrib.tutorials.talking_npc.TalkingNPC`,
For example:

    create/drop John : contrib.tutorials.talking_npc.TalkingNPC

Use `talk` in the same room as the NPC to start a conversation.

If there are many talkative npcs in the same room you will get to choose which
one's talk command to call (Evennia handles this automatically).

This use of EvMenu is very simplistic; See EvMenu for a lot more complex
possibilities.


----

<small>This document page is generated from `evennia/contrib/tutorials/talking_npc/README.md`. Changes to this
file will be overwritten, so edit that file rather than this one.</small>
