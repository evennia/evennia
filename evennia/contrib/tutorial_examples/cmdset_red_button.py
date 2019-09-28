"""
This defines the cmdset for the red_button. Here we have defined
the commands and the cmdset in the same module, but if you
have many different commands to merge it is often better
to define the cmdset separately, picking and choosing from
among the available commands as to what should be included in the
cmdset - this way you can often re-use the commands too.
"""

import random
from evennia import Command, CmdSet

# Some simple commands for the red button

# ------------------------------------------------------------
# Commands defined on the red button
# ------------------------------------------------------------


class CmdNudge(Command):
    """
    Try to nudge the button's lid

    Usage:
      nudge lid

    This command will have you try to
    push the lid of the button away.
    """

    key = "nudge lid"  # two-word command name!
    aliases = ["nudge"]
    locks = "cmd:all()"

    def func(self):
        """
        nudge the lid. Random chance of success to open it.
        """
        rand = random.random()
        if rand < 0.5:
            self.caller.msg("You nudge at the lid. It seems stuck.")
        elif rand < 0.7:
            self.caller.msg("You move the lid back and forth. It won't budge.")
        else:
            self.caller.msg("You manage to get a nail under the lid.")
            self.caller.execute_cmd("open lid")


class CmdPush(Command):
    """
    Push the red button

    Usage:
      push button

    """

    key = "push button"
    aliases = ["push", "press button", "press"]
    locks = "cmd:all()"

    def func(self):
        """
        Note that we choose to implement this with checking for
        if the lid is open/closed. This is because this command
        is likely to be tried regardless of the state of the lid.

        An alternative would be to make two versions of this command
        and tuck them into the cmdset linked to the Open and Closed
        lid-state respectively.

        """

        if self.obj.db.lid_open:
            string = "You reach out to press the big red button ..."
            string += "\n\nA BOOM! A bright light blinds you!"
            string += "\nThe world goes dark ..."
            self.caller.msg(string)
            self.caller.location.msg_contents(
                "%s presses the button. BOOM! %s is blinded by a flash!"
                % (self.caller.name, self.caller.name),
                exclude=self.caller,
            )
            # the button's method will handle all setup of scripts etc.
            self.obj.press_button(self.caller)
        else:
            string = "You cannot push the button - there is a glass lid covering it."
            self.caller.msg(string)


class CmdSmashGlass(Command):
    """
    smash glass

    Usage:
      smash glass

    Try to smash the glass of the button.
    """

    key = "smash glass"
    aliases = ["smash lid", "break lid", "smash"]
    locks = "cmd:all()"

    def func(self):
        """
        The lid won't open, but there is a small chance
        of causing the lamp to break.
        """
        rand = random.random()

        if rand < 0.2:
            string = "You smash your hand against the glass"
            string += " with all your might. The lid won't budge"
            string += " but you cause quite the tremor through the button's mount."
            string += "\nIt looks like the button's lamp stopped working for the time being."
            self.obj.lamp_works = False
        elif rand < 0.6:
            string = "You hit the lid hard. It doesn't move an inch."
        else:
            string = "You place a well-aimed fist against the glass of the lid."
            string += " Unfortunately all you get is a pain in your hand. Maybe"
            string += " you should just try to open the lid instead?"
        self.caller.msg(string)
        self.caller.location.msg_contents(
            "%s tries to smash the glass of the button." % (self.caller.name), exclude=self.caller
        )


class CmdOpenLid(Command):
    """
    open lid

    Usage:
      open lid

    """

    key = "open lid"
    aliases = ["open button", "open"]
    locks = "cmd:all()"

    def func(self):
        "simply call the right function."

        if self.obj.db.lid_locked:
            self.caller.msg("This lid seems locked in place for the moment.")
            return

        string = "\nA ticking sound is heard, like a winding mechanism. Seems "
        string += "the lid will soon close again."
        self.caller.msg(string)
        self.caller.location.msg_contents(
            "%s opens the lid of the button." % (self.caller.name), exclude=self.caller
        )
        # add the relevant cmdsets to button
        self.obj.cmdset.add(LidClosedCmdSet)
        # call object method
        self.obj.open_lid()


class CmdCloseLid(Command):
    """
    close the lid

    Usage:
      close lid

    Closes the lid of the red button.
    """

    key = "close lid"
    aliases = ["close"]
    locks = "cmd:all()"

    def func(self):
        "Close the lid"

        self.obj.close_lid()

        # this will clean out scripts dependent on lid being open.
        self.caller.msg("You close the button's lid. It clicks back into place.")
        self.caller.location.msg_contents(
            "%s closes the button's lid." % (self.caller.name), exclude=self.caller
        )


class CmdBlindLook(Command):
    """
    Looking around in darkness

    Usage:
      look <obj>

    ... not that there's much to see in the dark.

    """

    key = "look"
    aliases = ["l", "get", "examine", "ex", "feel", "listen"]
    locks = "cmd:all()"

    def func(self):
        "This replaces all the senses when blinded."

        # we decide what to reply based on which command was
        # actually tried

        if self.cmdstring == "get":
            string = "You fumble around blindly without finding anything."
        elif self.cmdstring == "examine":
            string = "You try to examine your surroundings, but can't see a thing."
        elif self.cmdstring == "listen":
            string = "You are deafened by the boom."
        elif self.cmdstring == "feel":
            string = "You fumble around, hands outstretched. You bump your knee."
        else:
            # trying to look
            string = "You are temporarily blinded by the flash. "
            string += "Until it wears off, all you can do is feel around blindly."
        self.caller.msg(string)
        self.caller.location.msg_contents(
            "%s stumbles around, blinded." % (self.caller.name), exclude=self.caller
        )


class CmdBlindHelp(Command):
    """
    Help function while in the blinded state

    Usage:
      help

    """

    key = "help"
    aliases = "h"
    locks = "cmd:all()"

    def func(self):
        "Give a message."
        self.caller.msg("You are beyond help ... until you can see again.")


# ---------------------------------------------------------------
# Command sets for the red button
# ---------------------------------------------------------------

# We next tuck these commands into their respective command sets.
# (note that we are overdoing the cdmset separation a bit here
# to show how it works).


class DefaultCmdSet(CmdSet):
    """
    The default cmdset always sits
    on the button object and whereas other
    command sets may be added/merge onto it
    and hide it, removing them will always
    bring it back. It's added to the object
    using obj.cmdset.add_default().
    """

    key = "RedButtonDefault"
    mergetype = "Union"  # this is default, we don't really need to put it here.

    def at_cmdset_creation(self):
        "Init the cmdset"
        self.add(CmdPush())


class LidClosedCmdSet(CmdSet):
    """
    A simple cmdset tied to the redbutton object.

    It contains the commands that launches the other
    command sets, making the red button a self-contained
    item (i.e. you don't have to manually add any
    scripts etc to it when creating it).
    """

    key = "LidClosedCmdSet"
    # default Union is used *except* if we are adding to a
    # cmdset named LidOpenCmdSet - this one we replace
    # completely.
    key_mergetype = {"LidOpenCmdSet": "Replace"}

    def at_cmdset_creation(self):
        "Populates the cmdset when it is instantiated."
        self.add(CmdNudge())
        self.add(CmdSmashGlass())
        self.add(CmdOpenLid())


class LidOpenCmdSet(CmdSet):
    """
    This is the opposite of the Closed cmdset.
    """

    key = "LidOpenCmdSet"
    # default Union is used *except* if we are adding to a
    # cmdset named LidClosedCmdSet - this one we replace
    # completely.
    key_mergetype = {"LidClosedCmdSet": "Replace"}

    def at_cmdset_creation(self):
        "setup the cmdset (just one command)"
        self.add(CmdCloseLid())


class BlindCmdSet(CmdSet):
    """
    This is the cmdset added to the *account* when
    the button is pushed.
    """

    key = "BlindCmdSet"
    # we want it to completely replace all normal commands
    # until the timed script removes it again.
    mergetype = "Replace"
    # we want to stop the account from walking around
    # in this blinded state, so we hide all exits too.
    # (channel commands will still work).
    no_exits = True  # keep account in the same room
    no_objs = True  # don't allow object commands

    def at_cmdset_creation(self):
        "Setup the blind cmdset"
        from evennia.commands.default.general import CmdSay
        from evennia.commands.default.general import CmdPose

        self.add(CmdSay())
        self.add(CmdPose())
        self.add(CmdBlindLook())
        self.add(CmdBlindHelp())
