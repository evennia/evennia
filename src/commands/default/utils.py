"""
This defines some test commands for use while testing the MUD and its components.

"""

from django.conf import settings 
from django.db import IntegrityError
from src.comms.models import Msg
from src.utils import create, debug, utils
from src.commands.default.muxcommand import MuxCommand

from src.commands import cmdsethandler


# Test permissions

class CmdTest(MuxCommand):
    """
    test the command system

    Usage:
      @test <any argument or switch>

    This command will echo back all argument or switches
    given to it, showcasing the muxcommand style. 
    """

    key = "@test"
    aliases = ["@te", "@test all"]
    help_category = "Utils"
    locks = "cmd:perm(Wizards)"

    # the muxcommand class itself handles the display
    # so we just defer to it by not adding any function.

    def func(self):
        
        def test():
            li = []
            for l in range(10000):
                li.append(l)            
            self.caller.msg(li[-1]) 
            return "This is the return text"
            #print 1/0
        def succ(f):
            self.caller.msg("This is called after successful completion. Return value: %s" % f)            
        def err(e):
            self.caller.msg("An error was encountered... %s" % e)

        #self.caller.msg("printed before call to sync run ...")
        #test()
        #self.caller.msg("after after call to sync run...")

        self.caller.msg("printed before call to async run ...")
        utils.run_async(test, at_return=succ, at_err=err)
        self.caller.msg("printed after call to async run ...")
    
        #cmdsetname = "game.gamesrc.commands.default.cmdset_default.DefaultCmdSet"
        #self.caller.msg(cmdsethandler.CACHED_CMDSETS)
        #cmdsethandler.import_cmdset(cmdsetname, self, self)
        #self.caller.msg("Imported %s" % cmdsetname)
        #self.caller.msg(cmdsethandler.CACHED_CMDSETS)

class TestCom(MuxCommand):
    """
    Test the command system

    Usage:
      @testcom/create/list [channel]
    """
    key = "@testcom"    
    locks = "cmd:perm(Wizards)"
    help_category = "Utils"
    def func(self):
        "Run the test program"
        caller = self.caller
        
        if 'create' in self.switches:
            if self.args:
                chankey = self.args
                try:
                    channel = create.create_channel(chankey)
                except IntegrityError:
                    caller.msg("Channel '%s' already exists." % chankey)
                    return 
            channel.connect_to(caller)
            caller.msg("Created new channel %s" % chankey)
            msgobj = create.create_message(caller.player,
                                           "First post to new channel!")
            channel.msg(msgobj)

            return
        elif 'list' in self.switches:
            msgresults = Msg.objects.get_messages_by_sender(caller)
            string = "\n".join(["%s %s: %s" % (msg.date_sent,
                                               [str(chan.key) for chan in msg.channels.all()],
                                               msg.message)
                                for msg in msgresults])
            caller.msg(string)
            return 
        caller.msg("Usage: @testcom/create channel")
