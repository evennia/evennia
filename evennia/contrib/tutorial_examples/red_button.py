"""

This is a more advanced example object. It combines functions from
script.examples as well as commands.examples to make an interactive
button typeclass.

Create this button with

 @create/drop examples.red_button.RedButton

Note that you must drop the button before you can see its messages!
"""
import random
from evennia import DefaultObject
from evennia.contrib.tutorial_examples import red_button_scripts as scriptexamples
from evennia.contrib.tutorial_examples import cmdset_red_button as cmdsetexamples

#
# Definition of the object itself
#


class RedButton(DefaultObject):
    """
    This class describes an evil red button.  It will use the script
    definition in contrib/examples/red_button_scripts to blink at regular
    intervals.  It also uses a series of script and commands to handle
    pushing the button and causing effects when doing so.

    The following attributes can be set on the button:
     desc_lid_open - description when lid is open
     desc_lid_closed - description when lid is closed
     desc_lamp_broken - description when lamp is broken

    """
    def at_object_creation(self):
        """
        This function is called when object is created. Use this
        instead of e.g. __init__.
        """
        # store desc (default, you can change this at creation time)
        desc = "This is a large red button, inviting yet evil-looking. "
        desc += "A closed glass lid protects it."
        self.db.desc = desc

        # We have to define all the variables the scripts
        # are checking/using *before* adding the scripts or
        # they might be deactivated before even starting!
        self.db.lid_open = False
        self.db.lamp_works = True
        self.db.lid_locked = False

        self.cmdset.add_default(cmdsetexamples.DefaultCmdSet, permanent=True)

        # since the cmdsets relevant to the button are added 'on the fly',
        # we need to setup custom scripts to do this for us (also, these scripts
        # check so they are valid (i.e. the lid is actually still closed)).
        # The AddClosedCmdSet script makes sure to add the Closed-cmdset.
        self.scripts.add(scriptexamples.ClosedLidState)
        # the script EventBlinkButton makes the button blink regularly.
        self.scripts.add(scriptexamples.BlinkButtonEvent)

    # state-changing methods

    def open_lid(self):
        """
        Opens the glass lid and start the timer so it will soon close
        again.

        """

        if self.db.lid_open:
            return
        desc = self.db.desc_lid_open
        if not desc:
            desc = "This is a large red button, inviting yet evil-looking. "
            desc += "Its glass cover is open and the button exposed."
        self.db.desc = desc
        self.db.lid_open = True

        # with the lid open, we validate scripts; this will clean out
        # scripts that depend on the lid to be closed.
        self.scripts.validate()
        # now add new scripts that define the open-lid state
        self.scripts.add(scriptexamples.OpenLidState)
        # we also add a scripted event that will close the lid after a while.
        # (this one cleans itself after being called once)
        self.scripts.add(scriptexamples.CloseLidEvent)

    def close_lid(self):
        """
        Close the glass lid. This validates all scripts on the button,
        which means that scripts only being valid when the lid is open
        will go away automatically.

        """

        if not self.db.lid_open:
            return
        desc = self.db.desc_lid_closed
        if not desc:
            desc = "This is a large red button, inviting yet evil-looking. "
            desc += "Its glass cover is closed, protecting it."
        self.db.desc = desc
        self.db.lid_open = False

        # clean out scripts depending on lid to be open
        self.scripts.validate()
        # add scripts related to the closed state
        self.scripts.add(scriptexamples.ClosedLidState)

    def break_lamp(self, feedback=True):
        """
        Breaks the lamp in the button, stopping it from blinking.

        Args:
            feedback (bool): Show a message about breaking the lamp.

        """
        self.db.lamp_works = False
        desc = self.db.desc_lamp_broken
        if not desc:
            self.db.desc += "\nThe big red button has stopped blinking for the time being."
        else:
            self.db.desc = desc

        if feedback and self.location:
            self.location.msg_contents("The lamp flickers, the button going dark.")
        self.scripts.validate()

    def press_button(self, pobject):
        """
        Someone was foolish enough to press the button!

        Args:
            pobject (Object): The person pressing the button

        """
        # deactivate the button so it won't flash/close lid etc.
        self.scripts.add(scriptexamples.DeactivateButtonEvent)
        # blind the person pressing the button. Note that this
        # script is set on the *character* pressing the button!
        pobject.scripts.add(scriptexamples.BlindedState)

    # script-related methods

    def blink(self):
        """
        The script system will regularly call this
        function to make the button blink. Now and then
        it won't blink at all though, to add some randomness
        to how often the message is echoed.
        """
        loc = self.location
        if loc:
            rand = random.random()
            if rand < 0.2:
                string = "The red button flashes briefly."
            elif rand < 0.4:
                string = "The red button blinks invitingly."
            elif rand < 0.6:
                string = "The red button flashes. You know you wanna push it!"
            else:
                # no blink
                return
            loc.msg_contents(string)
