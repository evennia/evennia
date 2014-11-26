from .. command import MuxCommand
from src.players.models import PlayerDB
from src.utils import utils, gametime, evtable
#from .. lib.align import PrettyTable


class CmdAccountList(MuxCommand):

    key = "+accounts"
    locks = "cmd:perm(Wizards)"
    
    def func(self):

        plyrs = PlayerDB.objects.all()
        latesttable = evtable.EvTable("dbref","name","perms","characters",boder="cells",width=78,align="l")
        for ply in plyrs:
            charlist = []
            for char in ply.db._playable_characters:
                charlist.append(char.key)
            latesttable.add_row(ply.dbref, ply.key,", ".join(ply.permissions),", ".join(charlist))
        self.caller.msg(latesttable)