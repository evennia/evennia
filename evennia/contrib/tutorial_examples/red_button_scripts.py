"""
Example of scripts.

These are scripts intended for a particular object - the
red_button object type in contrib/examples. A few variations
on uses of scripts are included.

"""
from evennia import DefaultScript
from evennia.contrib.tutorial_examples import cmdset_red_button as cmdsetexamples

#
# Scripts as state-managers
#
# Scripts have many uses, one of which is to statically
# make changes when a particular state of an object changes.
# There is no "timer" involved in this case (although there could be),
# whenever the script determines it is "invalid", it simply shuts down
# along with all the things it controls.
#
# To show as many features as possible of the script and cmdset systems,
# we will use three scripts controlling one state each of the red_button,
# each with its own set of commands, handled by cmdsets - one for when
# the button has its lid open, and one for when it is closed and a
# last one for when the player pushed the button and gets blinded by
# a bright light. The last one also has a timer component that allows it
# to remove itself after a while (and the player recovers their eyesight).


class ClosedLidState(DefaultScript):
    """
    This manages the cmdset for the "closed" button state. What this
    means is that while this script is valid, we add the RedButtonClosed
    cmdset to it (with commands like open, nudge lid etc)
    """

    def at_script_creation(self):
        "Called when script first created."
        self.key = "closed_lid_script"
        self.desc = "Script that manages the closed-state cmdsets for red button."
        self.persistent = True

    def at_start(self):
        """
        This is called once every server restart, so we want to add the
        (memory-resident) cmdset to the object here. is_valid is automatically
        checked so we don't need to worry about adding the script to an
        open lid.
        """
        # All we do is add the cmdset for the closed state.
        self.obj.cmdset.add(cmdsetexamples.LidClosedCmdSet)

    def is_valid(self):
        """
        The script is only valid while the lid is closed.
        self.obj is the red_button on which this script is defined.
        """
        return not self.obj.db.lid_open

    def at_stop(self):
        """
        When the script stops we must make sure to clean up after us.

        """
        self.obj.cmdset.delete(cmdsetexamples.LidClosedCmdSet)


class OpenLidState(DefaultScript):
    """
    This manages the cmdset for the "open" button state. This will add
    the RedButtonOpen
    """

    def at_script_creation(self):
        "Called when script first created."
        self.key = "open_lid_script"
        self.desc = "Script that manages the opened-state cmdsets for red button."
        self.persistent = True

    def at_start(self):
        """
        This is called once every server restart, so we want to add the
        (memory-resident) cmdset to the object here. is_valid is
        automatically checked, so we don't need to worry about
        adding the cmdset to a closed lid-button.
        """
        self.obj.cmdset.add(cmdsetexamples.LidOpenCmdSet)

    def is_valid(self):
        """
        The script is only valid while the lid is open.
        self.obj is the red_button on which this script is defined.
        """
        return self.obj.db.lid_open

    def at_stop(self):
        """
        When the script stops (like if the lid is closed again)
        we must make sure to clean up after us.
        """
        self.obj.cmdset.delete(cmdsetexamples.LidOpenCmdSet)


class BlindedState(DefaultScript):
    """
    This is a timed state.

    This adds a (very limited) cmdset TO THE ACCOUNT, during a certain time,
    after which the script will close and all functions are
    restored. It's up to the function starting the script to actually
    set it on the right account object.
    """

    def at_script_creation(self):
        """
        We set up the script here.
        """
        self.key = "temporary_blinder"
        self.desc = "Temporarily blinds the account for a little while."
        self.interval = 20  # seconds
        self.start_delay = True  # we don't want it to stop until after 20s.
        self.repeats = 1  # this will go away after interval seconds.
        self.persistent = False  # we will ditch this if server goes down

    def at_start(self):
        """
        We want to add the cmdset to the linked object.

        Note that the RedButtonBlind cmdset is defined to completly
        replace the other cmdsets on the stack while it is active
        (this means that while blinded, only operations in this cmdset
        will be possible for the account to perform). It is however
        not persistent, so should there be a bug in it, we just need
        to restart the server to clear out of it during development.
        """
        self.obj.cmdset.add(cmdsetexamples.BlindCmdSet)

    def at_stop(self):
        """
        It's important that we clear out that blinded cmdset
        when we are done!
        """
        self.obj.msg("You blink feverishly as your eyesight slowly returns.")
        self.obj.location.msg_contents(
            "%s seems to be recovering their eyesight." % self.obj.name, exclude=self.obj
        )
        self.obj.cmdset.delete()  # this will clear the latest added cmdset,
        # (which is the blinded one).


#
# Timer/Event-like Scripts
#
# Scripts can also work like timers, or "events". Below we
# define three such timed events that makes the button a little
# more "alive" - one that makes the button blink menacingly, another
# that makes the lid covering the button slide back after a while.
#


class CloseLidEvent(DefaultScript):
    """
    This event closes the glass lid over the button
    some time after it was opened. It's a one-off
    script that should be started/created when the
    lid is opened.
    """

    def at_script_creation(self):
        """
        Called when script object is first created. Sets things up.
        We want to have a lid on the button that the user can pull
        aside in order to make the button 'pressable'. But after a set
        time that lid should auto-close again, making the button safe
        from pressing (and deleting this command).
        """
        self.key = "lid_closer"
        self.desc = "Closes lid on a red buttons"
        self.interval = 20  # seconds
        self.start_delay = True  # we want to pospone the launch.
        self.repeats = 1  # we only close the lid once
        self.persistent = True  # even if the server crashes in those 20 seconds,
        # the lid will still close once the game restarts.

    def is_valid(self):
        """
        This script can only operate if the lid is open; if it
        is already closed, the script is clearly invalid.

        Note that we are here relying on an self.obj being
        defined (and being a RedButton object) - this we should be able to
        expect since this type of script is always tied to one individual
        red button object and not having it would be an error.
        """
        return self.obj.db.lid_open

    def at_repeat(self):
        """
        Called after self.interval seconds. It closes the lid. Before this method is
        called, self.is_valid() is automatically checked, so there is no need to
        check this manually.
        """
        self.obj.close_lid()


class BlinkButtonEvent(DefaultScript):
    """
    This timed script lets the button flash at regular intervals.
    """

    def at_script_creation(self):
        """
        Sets things up. We want the button's lamp to blink at
        regular intervals, unless it's broken (can happen
        if you try to smash the glass, say).
        """
        self.key = "blink_button"
        self.desc = "Blinks red buttons"
        self.interval = 35  # seconds
        self.start_delay = False  # blink right away
        self.persistent = True  # keep blinking also after server reboot

    def is_valid(self):
        """
        Button will keep blinking unless it is broken.
        """
        return self.obj.db.lamp_works

    def at_repeat(self):
        """
        Called every self.interval seconds. Makes the lamp in
        the button blink.
        """
        self.obj.blink()


class DeactivateButtonEvent(DefaultScript):
    """
    This deactivates the button for a short while (it won't blink, won't
    close its lid etc). It is meant to be called when the button is pushed
    and run as long as the blinded effect lasts. We cannot put these methods
    in the AddBlindedCmdSet script since that script is defined on the *account*
    whereas this one must be defined on the *button*.
    """

    def at_script_creation(self):
        """
        Sets things up.
        """
        self.key = "deactivate_button"
        self.desc = "Deactivate red button temporarily"
        self.interval = 21  # seconds
        self.start_delay = True  # wait with the first repeat for self.interval seconds.
        self.persistent = True
        self.repeats = 1  # only do this once

    def at_start(self):
        """
        Deactivate the button. Observe that this method is always
        called directly, regardless of the value of self.start_delay
        (that just controls when at_repeat() is called)
        """
        # closing the lid will also add the ClosedState script
        self.obj.close_lid()
        # lock the lid so other accounts can't access it until the
        # first one's effect has worn off.
        self.obj.db.lid_locked = True
        # breaking the lamp also sets a correct desc
        self.obj.break_lamp(feedback=False)

    def at_repeat(self):
        """
        When this is called, reset the functionality of the button.
        """
        # restore button's desc.

        self.obj.db.lamp_works = True
        desc = "This is a large red button, inviting yet evil-looking. "
        desc += "Its glass cover is closed, protecting it."
        self.db.desc = desc
        # re-activate the blink button event.
        self.obj.scripts.add(BlinkButtonEvent)
        # unlock the lid
        self.obj.db.lid_locked = False
        self.obj.scripts.validate()
