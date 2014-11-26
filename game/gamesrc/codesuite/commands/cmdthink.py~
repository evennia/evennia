from game.gamesrc.codesuite.commands.command import MuxCommand

class CmdThink(MuxCommand):
    """
    think - emit back a string.
    
    Usage:
        think <text>
    
    This simply returns whatever you enter
    """

    key = "think"
    aliases = ["echo"]
    locks = "cmd:all()"
    
    def func(self):
        if self.args:
            self.caller.msg(self.args)