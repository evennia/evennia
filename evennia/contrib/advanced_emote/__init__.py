"""
Advanced Emote - Rhicora 2023

To implement this, go to your character command set and add the line:

from evennia.contrib.advanced_emote.actor_emote import CmdI

Then make sure CmdI is available to PCs from creation:

class PCCmdSet(CmdSet):
    def at_cmdset_creation(self):
        self.add(CmdI)

Finally, make sure you have the dependency 'nltk', or things will break!

"""

from .actor_emote import CmdI  # noqa