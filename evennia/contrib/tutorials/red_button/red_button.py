"""
Red Button

Griatch - 2011

This is a more advanced example object. It combines functions from
script.examples as well as commands.examples to make an interactive
button typeclass.

Create this button with

    create/drop tutorials.red_button.RedButton

Note that you must drop the button before you can see its messages!

## Technical

The button's functionality is controlled by CmdSets that gets added and removed
depending on the 'state' the button is in.

- Lid-closed state: In this state the button is covered by a glass cover and trying
  to 'push' it will fail. You can 'nudge', 'smash' or 'open' the lid.
- Lid-open state: In this state the lid is open but will close again after a certain
  time. Using 'push' now will press the button and trigger the Blind-state.
- Blind-state: In this mode you are blinded by a bright flash. This will affect your
  normal commands like 'look' and help until the blindness wears off after a certain
  time.

Timers are handled by persistent delays on the button. These are examples of
`evennia.utils.utils.delay` calls that wait a certain time before calling a method -
such as when closing the lid and un-blinding a character.

"""
import random

from evennia import CmdSet, Command, DefaultObject
from evennia.utils.utils import delay, interactive, repeat

# Commands on the button (not all awailable at the same time)


# Commands for the state when the lid covering the button is closed.


class CmdPushLidClosed(Command):
    """
    Push the red button (lid closed)

    Usage:
      push button

    """

    key = "push button"
    aliases = ["push", "press button", "press"]
    locks = "cmd:all()"

    def func(self):
        """
        This is the version of push used when the lid is closed.

        An alternative would be to make a 'push' command in a default cmdset
        that is always available on the button and then use if-statements to
        check if the lid is open or closed.

        """
        self.caller.msg("You cannot push the button = there is a glass lid covering it.")


class CmdNudge(Command):
    """
    Try to nudge the button's lid.

    Usage:
      nudge lid

    This command will have you try to push the lid of the button away.

    """

    key = "nudge lid"  # two-word command name!
    aliases = ["nudge"]
    locks = "cmd:all()"

    def func(self):
        """
        Nudge the lid. Random chance of success to open it.

        """
        rand = random.random()
        if rand < 0.5:
            self.caller.msg("You nudge at the lid. It seems stuck.")
        elif rand < 0.7:
            self.caller.msg("You move the lid back and forth. It won't budge.")
        else:
            self.caller.msg("You manage to get a nail under the lid.")
            # self.obj is the button object
            self.obj.to_open_state()


class CmdSmashGlass(Command):
    """
    Smash the protective glass.

    Usage:
      smash glass

    Try to smash the glass of the button.

    """

    key = "smash glass"
    aliases = ["smash lid", "break lid", "smash"]
    locks = "cmd:all()"

    def func(self):
        """
        The lid won't open, but there is a small chance of causing the lamp to
        break.

        """
        rand = random.random()
        self.caller.location.msg_contents(
            f"{self.caller.name} tries to smash the glass of the button.", exclude=self.caller
        )

        if rand < 0.2:
            string = (
                "You smash your hand against the glass"
                " with all your might. The lid won't budge"
                " but you cause quite the tremor through the button's mount."
                "\nIt looks like the button's lamp stopped working for the time being, "
                "but the lid is still as closed as ever."
            )
            # self.obj is the button itself
            self.obj.break_lamp()
        elif rand < 0.6:
            string = "You hit the lid hard. It doesn't move an inch."
        else:
            string = (
                "You place a well-aimed fist against the glass of the lid."
                " Unfortunately all you get is a pain in your hand. Maybe"
                " you should just try to just ... open the lid instead?"
            )
        self.caller.msg(string)


class CmdOpenLid(Command):
    """
    open lid

    Usage:
      open lid

    """

    key = "open lid"
    aliases = ["open button"]
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
            f"{self.caller.name} opens the lid of the button.", exclude=self.caller
        )
        self.obj.to_open_state()


class LidClosedCmdSet(CmdSet):
    """
    A simple cmdset tied to the redbutton object.

    It contains the commands that launches the other
    command sets, making the red button a self-contained
    item (i.e. you don't have to manually add any
    scripts etc to it when creating it).

    Note that this is given with a `key_mergetype` set. This
    is set up so that the cmdset with merge with Union merge type
    *except* if the other cmdset to merge with is LidOpenCmdSet,
    in which case it will Replace that. So these two cmdsets will
    be mutually exclusive.

    """

    key = "LidClosedCmdSet"

    def at_cmdset_creation(self):
        "Populates the cmdset when it is instantiated."
        self.add(CmdPushLidClosed())
        self.add(CmdNudge())
        self.add(CmdSmashGlass())
        self.add(CmdOpenLid())


# Commands for the state when the button's protective cover is open - now the
# push command will work. You can also close the lid again.


class CmdPushLidOpen(Command):
    """
    Push the red button

    Usage:
      push button

    """

    key = "push button"
    aliases = ["push", "press button", "press"]
    locks = "cmd:all()"

    @interactive
    def func(self):
        """
        This version of push will immediately trigger the next button state.

        The use of the @interactive decorator allows for using `yield` to add
        simple pauses in how quickly a message is returned to the user.  This
        kind of pause will not survive a server reload.

        """
        # pause a little between each message.
        self.caller.msg("You reach out to press the big red button ...")
        yield (2)  # pause 2s before next message
        self.caller.msg("\n\n|wBOOOOM! A bright light blinds you!|n")
        yield (1)  # pause 1s before next message
        self.caller.msg("\n\n|xThe world goes dark ...|n")

        name = self.caller.name
        self.caller.location.msg_contents(
            f"{name} presses the button. BOOM! {name} is blinded by a flash!", exclude=self.caller
        )
        self.obj.blind_target(self.caller)


class CmdCloseLid(Command):
    """
    Close the lid

    Usage:
      close lid

    Closes the lid of the red button.
    """

    key = "close lid"
    aliases = ["close"]
    locks = "cmd:all()"

    def func(self):
        "Close the lid"

        self.obj.to_closed_state()

        # this will clean out scripts dependent on lid being open.
        self.caller.msg("You close the button's lid. It clicks back into place.")
        self.caller.location.msg_contents(
            f"{self.caller.name} closes the button's lid.", exclude=self.caller
        )


class LidOpenCmdSet(CmdSet):
    """
    This is the opposite of the Closed cmdset.

    Note that this is given with a `key_mergetype` set. This
    is set up so that the cmdset with merge with Union merge type
    *except* if the other cmdset to merge with is LidClosedCmdSet,
    in which case it will Replace that. So these two cmdsets will
    be mutually exclusive.

    """

    key = "LidOpenCmdSet"

    def at_cmdset_creation(self):
        """Setup the cmdset"""
        self.add(CmdPushLidOpen())
        self.add(CmdCloseLid())


# Commands for when the button has been pushed and the player is blinded. This
# replaces commands on the player making them 'blind' for a while.


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
            string = (
                "You are temporarily blinded by the flash. "
                "Until it wears off, all you can do is feel around blindly."
            )
        self.caller.msg(string)
        self.caller.location.msg_contents(
            f"{self.caller.name} stumbles around, blinded.", exclude=self.caller
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
        """
        Just give a message while blinded. We could have added this to the
        CmdBlindLook command too if we wanted to keep things more compact.

        """
        self.caller.msg("You are beyond help ... until you can see again.")


class BlindCmdSet(CmdSet):
    """
    This is the cmdset added to the *account* when
    the button is pushed.

    Since this has mergetype Replace it will completely remove the commands of
    all other cmdsets while active. To allow some limited interaction
    (pose/say) we import those default commands and add them too.

    We also disable all exit-commands generated by exits and
    object-interactions while blinded by setting `no_exits` and `no_objs` flags
    on the cmdset. This is to avoid the player walking off or interfering with
    other objects while blinded. Account-level commands however (channel messaging
    etc) will not be affected by the blinding.

    """

    key = "BlindCmdSet"
    # we want it to completely replace all normal commands
    # until the timed script removes it again.
    mergetype = "Replace"
    # we want to stop the player from walking around
    # in this blinded state, so we hide all exits too.
    # (channel commands will still work).
    no_exits = True  # keep player in the same room
    no_objs = True  # don't allow object commands

    def at_cmdset_creation(self):
        "Setup the blind cmdset"
        from evennia.commands.default.general import CmdPose, CmdSay

        self.add(CmdSay())
        self.add(CmdPose())
        self.add(CmdBlindLook())
        self.add(CmdBlindHelp())


#
# Definition of the object itself
#


class RedButton(DefaultObject):
    """
    This class describes an evil red button.  It will blink invitingly and
    temporarily blind whomever presses it.

    The button can take a few optional attributes controlling how things will
    be displayed in its various states. This is a useful way to give builders
    the option to customize a complex object from in-game. Actual return messages
    to event-actions are (in this example) left with each command, but one could
    also imagine having those handled via Attributes as well, if one wanted a
    completely in-game customizable button without needing to tweak command
    classes.

    Attributes:
    - `desc_closed_lid`:  This is the description to show of the button
      when the lid is closed.
    - `desc_open_lid`": Shown when the lid is open
    - `auto_close_msg`: Message to show when lid auto-closes
    - `desc_add_lamp_broken`: Extra desc-line added after normal desc when lamp
      is broken.
    - blink_msg: A list of strings to randomly choose from when the lamp
      blinks.

    Notes:
    The button starts with lid closed. To set the initial description,
    you can either set desc after creating it or pass a `desc` attribute
    when creating it, such as
    `button = create_object(RedButton, ..., attributes=[('desc', 'my desc')])`.

    """

    # these are the pre-set descriptions. Setting attributes will override
    # these on the fly.

    desc_closed_lid = (
        "This is a large red button, inviting yet evil-looking. A closed glass lid protects it."
    )
    desc_open_lid = (
        "This is a large red button, inviting yet evil-looking. "
        "Its glass cover is open and the button exposed."
    )
    auto_close_msg = "The button's glass lid silently slides back in place."
    lamp_breaks_msg = "The lamp flickers, the button going dark."
    desc_add_lamp_broken = "\nThe big red button has stopped blinking for the time being."
    # note that this is a list. A random message will display each time
    blink_msgs = [
        "The red button flashes briefly.",
        "The red button blinks invitingly.",
        "The red button flashes. You know you wanna push it!",
    ]

    def at_object_creation(self):
        """
        This function is called (once) when object is created.

        """
        self.db.lamp_works = True

        # start closed
        self.to_closed_state()

        # start blinking every 35s.
        repeat(35, self._do_blink, persistent=True)

    def _do_blink(self):
        """
        Have the button blink invitingly unless it's broken.

        """
        if self.location and self.db.lamp_works:
            possible_messages = self.db.blink_msgs or self.blink_msgs
            self.location.msg_contents(random.choice(possible_messages))

    def _set_desc(self, attrname=None):
        """
        Set a description, based on the attrname given, taking the lamp-status
        into account.

        Args:
            attrname (str, optional): This will first check for an Attribute with this name,
                secondly for a property on the class. So if `attrname="auto_close_msg"`,
                we will first look for an attribute `.db.auto_close_msg` and if that's
                not found we'll use `.auto_close_msg` instead. If unset (`None`), the
                currently set desc will not be changed (only lamp will be checked).

        Notes:
            If `self.db.lamp_works` is `False`, we'll append
            `desc_add_lamp_broken` text.

        """
        if attrname:
            # change desc
            desc = self.attributes.get(attrname) or getattr(self, attrname)
        else:
            # use existing desc
            desc = self.db.desc

        if not self.db.lamp_works:
            # lamp not working. Add extra to button's desc
            desc += self.db.desc_add_lamp_broken or self.desc_add_lamp_broken

        self.db.desc = desc

    # state-changing methods and actions

    def to_closed_state(self, msg=None):
        """
        Switches the button to having its lid closed.

        Args:
            msg (str, optional): If given, display a message to the room
            when lid closes.

        This will first try to get the Attribute (self.db.desc_closed_lid) in
        case it was set by a builder and if that was None, it will fall back to
        self.desc_closed_lid, the default description (note that lack of .db).
        """
        self._set_desc("desc_closed_lid")
        # remove lidopen-state, if it exists
        self.cmdset.remove(LidOpenCmdSet)
        # add lid-closed cmdset
        self.cmdset.add(LidClosedCmdSet, persistent=True)

        if msg and self.location:
            self.location.msg_contents(msg)

    def to_open_state(self):
        """
        Switches the button to having its lid open. This also starts a timer
        that will eventually close it again.

        """
        self._set_desc("desc_open_lid")
        # remove lidopen-state, if it exists
        self.cmdset.remove(LidClosedCmdSet)
        # add lid-open cmdset
        self.cmdset.add(LidOpenCmdSet, persistent=True)

        # wait 20s then call self.to_closed_state with a message as argument
        delay(
            35, self.to_closed_state, self.db.auto_close_msg or self.auto_close_msg, persistent=True
        )

    def _unblind_target(self, caller):
        """
        This is called to un-blind after a certain time.

        """
        caller.cmdset.remove(BlindCmdSet)
        caller.msg("You blink feverishly as your eyesight slowly returns.")
        self.location.msg_contents(
            f"{caller.name} seems to be recovering their eyesight, blinking feverishly.",
            exclude=caller,
        )

    def blind_target(self, caller):
        """
        Someone was foolish enough to press the button! Blind them
        temporarily.

        Args:
            caller (Object): The one to be blinded.

        """

        # we don't need to remove other cmdsets, this will replace all,
        # then restore whatever was there when it goes away.
        # we don't make this persistent, to make sure any problem is just a reload away
        caller.cmdset.add(BlindCmdSet)

        # wait 20s then call self._unblind to remove blindness effect. The
        # persistent=True means the delay should survive a server reload.
        delay(20, self._unblind_target, caller, persistent=True)

    def _unbreak_lamp(self):
        """
        This is called to un-break the lamp after a certain time.

        """
        # we do this quietly, the user will just notice it starting blinking again
        self.db.lamp_works = True
        self._set_desc()

    def break_lamp(self):
        """
        Breaks the lamp in the button, stopping it from blinking for a while

        """
        self.db.lamp_works = False
        # this will update the desc with the info about the broken lamp
        self._set_desc()
        self.location.msg_contents(self.db.lamp_breaks_msg or self.lamp_breaks_msg)

        # wait 21s before unbreaking the lamp again
        delay(21, self._unbreak_lamp)
