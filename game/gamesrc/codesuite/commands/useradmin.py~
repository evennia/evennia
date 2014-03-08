import ev
from . command import MuxCommand
from src.players.models import PlayerDB
from src.utils import utils, gametime
from .. lib.align import PrettyTable
from .. lib.penn import header,table,msghead
from .. lib.charmatch import charmatch
from .. lib.IPLog.models import Login

class CmdAccountList(MuxCommand):
    """
    +accounts - show all player objects and their characters.
    
    Usage:
        +accounts
    """
    key = "+accounts"
    aliases = ["+userlist","+players"]
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"
    def func(self):

        plyrs = PlayerDB.objects.all()
        print plyrs[0].db._playable_characters
        latesttable = PrettyTable(["dbref","name","perms","characters"])
        latesttable.align = 'l'
        latesttable.max_width["name"] = 20
        latesttable.max_width["perms"] = 15
        latesttable.max_width["characters"] = 35
        for ply in plyrs:
            charlist = []
            for char in ply.db._playable_characters:
                charlist.append(char.key)
            latesttable.add_row([ply.dbref, ply.key,", ".join(ply.permissions.all()),", ".join(charlist)])
        self.caller.msg(latesttable)
        
class CmdIP(MuxCommand):
    """
    +ip - check login records of a particular player, show players with same IP.
    
    Usage:
        +ip [<player>]

        Without a target, targets yourself.
    """
    
    key = "+ip"
    aliases = ["+sitematch"]
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"
    def func(self):
        #First, let's check what our target is!
        if not self.args:
            target = self.caller.player
        else:
            target = ev.search_player(self.args)
            if target: target = target[0]
        if not target:
            self.caller.msg("ERROR: Target not found.")
            return
        
        #Next, a simple Django search to figure out if the target has anything
        #to work with.
        search = Login.objects.filter(pid=target.dbobj).order_by('date')[:10]
        if not search:
            self.caller.msg("ERROR: Target has no logs to search.")
            return
        
        #Here we'll collect all of the ips from our results.
        sourceips = []
        for result in search:
            sourceips.append(result.ip)

        #Now we'll search for all players with a matching source IP in any logs.
        search2 = Login.objects.filter(ip__in=sourceips)
        if not search2:
            self.caller.msg("ERROR: Unable to locate logs.")
            return
        
        #Time to display results.
        self.caller.msg(header("Site Match Results for: %s" % target.key))
        distinctlist = []
        for ply in search2:
            if not ply.pid in distinctlist:
                distinctlist.append(ply.pid)
                plyr = ply.pid
                charlist = []
                for char in plyr.db._playable_characters:
                    charlist.append(char.key)
                self.caller.msg("%s (#%s): %s" % (plyr.key,plyr.id,", ".join(charlist)))
                loginsearch = Login.objects.filter(pid=ply.pid,result="success").order_by('date')[:10]
                if loginsearch:
                    self.caller.msg("{wSuccessful Logins:{n")
                    for loginattempt in loginsearch:
                        self.caller.msg("From %s on %s" % (loginattempt.ip,loginattempt.date.ctime()))
                failsearch = Login.objects.filter(pid=ply.pid,result__in=["invalid password","banned"]).order_by('date')[:10]
                if failsearch:
                    self.caller.msg("{wFailed Logins:{n")
                    for loginattempt in failsearch:
                        self.caller.msg("From %s on %s Reason: %s" % (loginattempt.ip,loginattempt.date.ctime(),loginattempt.result))
                self.caller.msg("\n")
        self.caller.msg(header("End of Results"))