"""

Contribution - Griatch 2011

[Note - with the advent of MULTISESSION_MODE=2, this is not really as
necessary anymore - the ooclook and @charcreate commands in that mode
replaces this module with better functionality.]

This is a simple character creation commandset. A suggestion is to
test this together with menu_login, which doesn't create a Character
on its own. This shows some more info and gives the Player the option
to create a character without any more customizations than their name
(further options are unique for each game anyway).

Since this extends the OOC cmdset, logging in from the menu will
automatically drop the Player into this cmdset unless they logged off
while puppeting a Character already before.

Installation:

Read the instructions in contrib/examples/cmdset.py in order to create
a new default cmdset module for Evennia to use (copy the template up
one level, and change the settings file's relevant variables to point
to the cmdsets inside). If you already have such a module you should
of course use that.

Next import this module in your custom cmdset module and add the
following line to the end of OOCCmdSet's at_cmdset_creation():

   self.add(chargen.OOCCmdSetCharGen)

"""

from django.conf import settings
from evennia import Command, create_object, utils
from evennia import default_cmds, managers

CHARACTER_TYPECLASS = settings.BASE_CHARACTER_TYPECLASS

class CmdOOCLook(default_cmds.CmdLook):
    """
    ooc look

    Usage:
      look
      look <character>

    This is an OOC version of the look command. Since a Player doesn't
    have an in-game existence, there is no concept of location or
    "self".

    If any characters are available for you to control, you may look
    at them with this command.
    """

    key = "look"
    aliases = ["l", "ls"]
    locks = "cmd:all()"
    help_cateogory = "General"

    def func(self):
        """
        Implements the ooc look command

        We use an attribute _character_dbrefs on the player in order
        to figure out which characters are "theirs". A drawback of this
        is that only the CmdCharacterCreate command adds this attribute,
        and thus e.g. player #1 will not be listed (although it will work).
        Existence in this list does not depend on puppeting rights though,
        that is checked by the @ic command directly.
        """

        # making sure caller is really a player
        self.character = None
        if utils.inherits_from(self.caller, "evennia.objects.objects.Object"):
            # An object of some type is calling. Convert to player.
            self.character = self.caller
            if hasattr(self.caller, "player"):
                self.caller = self.caller.player

        if not self.character:
            # ooc mode, we are players

            avail_chars = self.caller.db._character_dbrefs
            if self.args:
                # Maybe the caller wants to look at a character
                if not avail_chars:
                    self.caller.msg("You have no characters to look at. Why not create one?")
                    return
                objs = managers.objects.get_objs_with_key_and_typeclass(self.args.strip(), CHARACTER_TYPECLASS)
                objs = [obj for obj in objs if obj.id in avail_chars]
                if not objs:
                    self.caller.msg("You cannot see this Character.")
                    return
                self.caller.msg(objs[0].return_appearance(self.caller))
                return

            # not inspecting a character. Show the OOC info.
            charobjs = []
            charnames = []
            if self.caller.db._character_dbrefs:
                dbrefs = self.caller.db._character_dbrefs
                charobjs = [managers.objects.get_id(dbref) for dbref in dbrefs]
                charnames = [charobj.key for charobj in charobjs if charobj]
            if charnames:
                charlist = "The following Character(s) are available:\n\n"
                charlist += "\n\r".join(["{w    %s{n" % charname for charname in charnames])
                charlist += "\n\n   Use {w@ic <character name>{n to switch to that Character."
            else:
                charlist = "You have no Characters."
            string = \
"""   You, %s, are an {wOOC ghost{n without form. The world is hidden
   from you and besides chatting on channels your options are limited.
   You need to have a Character in order to interact with the world.

   %s

   Use {wcreate <name>{n to create a new character and {whelp{n for a
   list of available commands.""" % (self.caller.key, charlist)
            self.caller.msg(string)

        else:
            # not ooc mode - leave back to normal look
            # we have to put this back for normal look to work.
            self.caller = self.character
            super(CmdOOCLook, self).func()


class CmdOOCCharacterCreate(Command):
    """
    creates a character

    Usage:
      create <character name>

    This will create a new character, assuming
    the given character name does not already exist.
    """

    key = "create"
    locks = "cmd:all()"

    def func(self):
        """
        Tries to create the Character object. We also put an
        attribute on ourselves to remember it.
        """

        # making sure caller is really a player
        self.character = None
        if utils.inherits_from(self.caller, "evennia.objects.objects.Object"):
            # An object of some type is calling. Convert to player.
            self.character = self.caller
            if hasattr(self.caller, "player"):
                self.caller = self.caller.player

        if not self.args:
            self.caller.msg("Usage: create <character name>")
            return
        charname = self.args.strip()
        old_char = managers.objects.get_objs_with_key_and_typeclass(charname, CHARACTER_TYPECLASS)
        if old_char:
            self.caller.msg("Character {c%s{n already exists." % charname)
            return
        # create the character

        new_character = create_object(CHARACTER_TYPECLASS, key=charname)
        if not new_character:
            self.caller.msg("{rThe Character couldn't be created. This is a bug. Please contact an admin.")
            return
        # make sure to lock the character to only be puppeted by this player
        new_character.locks.add("puppet:id(%i) or pid(%i) or perm(Immortals) or pperm(Immortals)" %
                                (new_character.id, self.caller.id))

        # save dbref
        avail_chars = self.caller.db._character_dbrefs
        if avail_chars:
            avail_chars.append(new_character.id)
        else:
            avail_chars = [new_character.id]
        self.caller.db._character_dbrefs = avail_chars
        self.caller.msg("{gThe Character {c%s{g was successfully created!" % charname)


class OOCCmdSetCharGen(default_cmds.PlayerCmdSet):
    """
    Extends the default OOC cmdset.
    """
    def at_cmdset_creation(self):
        "Install everything from the default set, then overload"
        #super(OOCCmdSetCharGen, self).at_cmdset_creation()
        self.add(CmdOOCLook())
        self.add(CmdOOCCharacterCreate())
