"""
Script example

Griatch - 2012

Example script for testing. This adds a simple timer that has your
character make observations and notices at irregular intervals.

To test, use
  script me = tutorial_examples.bodyfunctions.BodyFunctions

The script will only send messages to the object it is stored on, so
make sure to put it on yourself or you won't see any messages!

"""
import random

from evennia import DefaultScript


class BodyFunctions(DefaultScript):
    """
    This class defines the script itself

    """

    def at_script_creation(self):
        self.key = "bodyfunction"
        self.desc = "Adds various timed events to a character."
        self.interval = 20  # seconds
        # self.repeats = 5  # repeat only a certain number of times
        self.start_delay = True  # wait self.interval until first call
        # self.persistent = True

    def at_repeat(self):
        """
        This gets called every self.interval seconds. We make
        a random check here so as to only return 33% of the time.
        """
        if random.random() < 0.66:
            # no message this time
            return
        self.send_random_message()

    def send_random_message(self):
        rand = random.random()
        # return a random message
        if rand < 0.1:
            string = "You tap your foot, looking around."
        elif rand < 0.2:
            string = "You have an itch. Hard to reach too."
        elif rand < 0.3:
            string = (
                "You think you hear someone behind you. ... but when you look there's noone there."
            )
        elif rand < 0.4:
            string = "You inspect your fingernails. Nothing to report."
        elif rand < 0.5:
            string = "You cough discreetly into your hand."
        elif rand < 0.6:
            string = "You scratch your head, looking around."
        elif rand < 0.7:
            string = "You blink, forgetting what it was you were going to do."
        elif rand < 0.8:
            string = "You feel lonely all of a sudden."
        elif rand < 0.9:
            string = "You get a great idea. Of course you won't tell anyone."
        else:
            string = "You suddenly realize how much you love Evennia!"

        # echo the message to the object
        self.obj.msg(string)
