from .. command import MuxCommand
from .. lib.penn import speak

class CmdSay(MuxCommand):
    """
    say

    Usage:
      say <message>

    Talk to those in your current location.
    """

    key = "say"
    aliases = ['"', "'"]
    locks = "cmd:all()"

    def func(self):
        "Run the say command"

        caller = self.caller

        if not self.args:
            caller.msg("Say what?")
            return

        speech = self.args

        # calling the speech hook on the location
        speech = caller.location.at_say(caller, speech)

        # Feedback for the object doing the talking.
        caller.msg('You say, "%s{n"' % speech)

        # Build the string to emit to neighbors.
        emit_string = '%s says, "%s{n"' % (caller.name,
                                               speech)
        caller.location.msg_contents(emit_string,
                                     exclude=caller)

class CmdPose(MuxCommand):
    """
    pose - strike a pose

    Usage:
      pose <pose text>
      pose's <pose text>

    Example:
      pose is standing by the wall, smiling.
       -> others will see:
      Tom is standing by the wall, smiling.

    Describe an action being taken. The pose text will
    automatically begin with your name.
    """
    key = "pose"
    aliases = [":", "emote"]
    locks = "cmd:all()"

    def parse(self):
        """
        Custom parse the cases where the emote
        starts with some special letter, such
        as 's, at which we don't want to separate
        the caller's name and the emote with a
        space.
        """
        args = self.args
        if args and not args[0] in ["'", ",", ":"]:
            args = " %s" % args.strip()
        self.args = args

    def func(self):
        "Hook function"
        if not self.args:
            msg = "What do you want to do?"
            self.caller.msg(msg)
        else:
            msg = "%s%s" % (self.caller.name, self.args)
            self.caller.location.msg_contents(msg)

class CmdSemiPose(MuxCommand):
    """
    semipose - strike a pose

    Usage:
      semipose <pose text>

    Example:
      sempose 's standing by the wall, smiling.
      ;'s standing by the wall, smiling.
       -> others will see:
      Tom's standing by the wall, smiling.

    Describe an action being taken. The pose text will
    automatically begin with your name.
    """
    key = "semipose"
    aliases = [";"]
    locks = "cmd:all()"

    def parse(self):
        """
        Custom parse the cases where the emote
        starts with some special letter, such
        as 's, at which we don't want to separate
        the caller's name and the emote with a
        space.
        """
        args = self.args
        if args and not args[0] in [";"]:
            args = "%s" % args.strip()
        self.args = args

    def func(self):
        "Hook function"
        if not self.args:
            msg = "What do you want to do?"
            self.caller.msg(msg)
        else:
            msg = "%s%s" % (self.caller.name, self.args)
            self.caller.location.msg_contents(msg)
            
class CmdEmit(MuxCommand):
    """
    @emit

    Usage:
      @emit <message>

    Emits a message to the local room, visible to all objects and players.
    """
    key = "@emit"
    aliases = ['spoof']
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        if not self.args:
            self.caller.msg("What will you emanate?")
            return

        self.caller.location.msg_contents(self.args)
        

class CmdOTalk(MuxCommand):
    """
    +ooc - speak out of character in a room, same as a channel.
           Begin with : to 'pose' the OOC message, ; to 'semipose it.'
    osay - like above.
    opose - works like pose but with the OOC header.
    osemipose - works like semipose but with the OOC header.
    """
    
    key = "+ooc"
    aliases = ['osay','opose','osemipose']
    locks = "cmd:all()"
    help_category = "General"
    
    def func(self):
        if not self.args:
            self.caller.msg("What will you say?")
            return
        
        oheader = "{n{x-<{rOOC{x>-{n"
        if self.cmdstring.lower() in ["+ooc","osay"] or self.args[0] in [';',':']:
            msg = speak(self.caller.key,self.args,fancy=True)
        if self.cmdstring.lower() == "opose":
            msg = speak(self.caller.key,":%s" % self.args,fancy=True)
        if self.cmdstring.lower() == "osemipose":
            msg = speak(self.caller.key,";%s" % self.args,fancy=True)
        
        self.caller.location.msg_contents("%s %s" % (oheader,msg))