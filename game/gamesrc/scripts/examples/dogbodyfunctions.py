"""
Example script for testing. This adds a simple timer that
has your character make observations and noices at irregular
intervals.

To test, use
  @script me = examples.bodyfunctions.BodyFunctions

The script will only send messages to the object it
is stored on, so make sure to put it on yourself
or you won't see any messages!

"""
import random
from ev import Script
import ev

class DogBodyFunctions(Script):
    """
    This class defines the script itself
    """

    def at_script_creation(self):
        self.key = "dogbodyfunction"
        self.desc = "Adds various timed events to a character."
        #self.interval = 5  # seconds
        self.interval = 20  # seconds
        #self.repeats = 5  # repeat only a certain number of times
        self.start_delay = True  # wait self.interval until first call
        self.persistent = True
        self.delay_counter = 0

    def at_repeat(self):
        """
        This gets called every self.interval seconds. We make
        a random check here so as to only return 33% of the time.
        """
        if self.delay_counter > 0:
            self.delay_counter -= 1
            if random.random() < 0.1:
                self.obj.location.msg_contents("{0} is here but it pays no attention to you".format(self.obj))
            return

        happy_msgs = ["wags its tail happily", "snifs", "streches its front legs and yawns", "scratches its neck vigorously"]
        angry_msgs = ["growls 'grrr grrr'", "barks angrily 'Grr WOOF WOOF GRRR'"]

        bones = self.obj.search('bone', quiet = True)
        bones = [bone for bone in bones if (bone.location == self.obj.location or bone in self.obj.contents)]
        for bone in bones:
            self.obj.msg("bone found: {0} at {1} from home {2}".format(bone, bone.location, bone.home))

        msgs = angry_msgs
        if len(bones) > 0:
            msgs = happy_msgs
            self.obj.location.msg_contents("{0} sniffs {1} ...".format(self.obj.name, random.choice(bones)))

        if random.random() < 0.1:
            # no message this time
            return

        rand = random.random()
        # return a random message
        string = "raises its ears and looks attentively"
        if rand < 0.4:
            string = random.choice(msgs)
        elif rand < 0.6:
            string = "raises its ears and looks around cautiously"
        elif rand < 0.8:
            string = "barks 'Woof Woof'"
        else:
            if len(self.obj.location.exits) > 0:
                string = "turns around and growls at {0}".format(random.choice(self.obj.location.exits))

        # echo the message to the object
        limbo = self.obj.search(ev.settings.DEFAULT_HOME)
        for bone in bones:
            if random.random() < 0.5: 
                self.obj.location.msg_contents("{0} grabs {1}, it goes to the corner and starts chewing it".format(self.obj.name, bone.name))
            else:
                self.obj.location.msg_contents("{0} grabs {1} ... runs around with it ... stops and buries it".format(self.obj.name, bone.name))
            bone.move_to(limbo, quiet = True)
            self.delay_counter = 10
        else:
            self.obj.location.msg_contents("{0} {1}".format(self.obj.name, string))

