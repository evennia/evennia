import re, datetime
from . command import MuxCommand
from .. lib.penn import header,STAFFREP,msghead
from .. lib.charmatch import charmatch
from .. lib.EVPot.models import Pose

class CmdPot(MuxCommand):
    """
    String here.
    """
       
    key = "+pot"
    locks = "cmd:all()"
    help_category = "RP Tools"
    
    def func(self):
        caller = self.caller
        switches = self.switches
        rhs = self.rhs
        lhs = self.lhs
        self.sysname = "INFO"
        isadmin = self.isadmin
        playswitches = ['brief','private']
        admswitches = ['wipe','enable','disable']
        
        if isadmin:
            callswitches = playswitches + admswitches
        else:
            callswitches = playswitches
        switches = self.partial(switches,callswitches)

