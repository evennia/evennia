import datetime, ev, time
from src.commands.default.comms import find_channel
from .. command import MuxCommand
from .. lib.penn import speak,msghead,header,cemit,stringsecs,STAFFREP,utcnow
from .. lib.align import PrettyTable
from src.utils import create
from django.utils.timezone import utc

now = datetime.datetime.utcnow().replace(tzinfo=utc)

class SystemSendToChannel(MuxCommand):
    """
    This is a special command that the cmdhandler calls
    when it detects that the command given matches
    an existing Channel object key (or alias).
    """

    key = ev.syscmdkeys.CMD_CHANNEL
    locks = "cmd:all()"
    auto_help = False
    
    def parse(self):
        super(SystemSendToChannel, self).parse()
        channelname, msg = self.args.split(':', 1)
        self.args = channelname.strip(), msg.strip()

    def speaker_name(self,channel):
        displaymode = channel.get_conf('displaymode')
        if displaymode == 0:
            return self.caller.key
        elif displaymode == 1:
            return self.player.key
        elif displaymode == 2:
            return self.character.key
        elif displaymode == 3:
            if self.isic:
                return "%s.%s" % (self.player.key,self.character.key)
            else:
                return self.player.key
            
    def speaker_title(self,channel):
        displaymode = channel.get_conf('displaymode')
        if displaymode == 0:
            if self.isic:
                return self.player.get_comm_char_conf(channel,self.character,'title')
            else:
                return self.player.get_comm_play_conf(channel,'title')
        elif displaymode == 1:
            return self.player.get_comm_play_conf(channel,'title')
        elif displaymode == 2:
            return self.player.get_comm_char_conf(channel,self.character,'title')
        elif displaymode == 3:
            return self.player.get_comm_char_conf(channel,self.character,'title')

    def func(self):
        """
        Create a new message and send it to channel, using
        the already formatted input.
        """
        caller = self.caller
        channelkey, msg = self.args
        if not msg:
            caller.msg("Say what?")
            return
        channel = find_channel(self.caller,channelkey)
        if not channel:
            caller.msg("Channel '%s' not found." % channelkey)
            return
        if not channel.has_connection(caller):
            string = "You are not connected to channel '%s'."
            caller.msg(string % channelkey)
            return
        if not channel.access(caller, 'send'):
            string = "You are not permitted to send to channel '%s'."
            caller.msg(string % channelkey)
            return
        
        
        # Channel Mode 0: just use self.caller.key for name
        # Channel Mode 1: Always use the Player's Key/name.
        # Channel Mode 2: always use Character's Name. Must be @ic.
        # Channel Mode 3: Use Player name if @ooc, and Playername.Charactername if @IC.
        
        #chanconf, created = ChanCommConf.objects.get_or_create(chankey=channel)
        #playconf, created = PlayCommConf.objects.get_or_create(chankey=channel,pid=self.player.dbobj)

        #Okay, let's check to see if the player is muzzled!
        if self.player.get_comm_play_conf(channel,'muzzled'):
            if self.player.get_comm_play_conf(channel,'muzzled') > utcnow():
                string = "Your account has been gagged from channel '%s' by %s until %s"
                caller.msg(string % (channel.db_key,self.player.get_comm_play_conf(channel,'muzzledby'),
                                     self.player.get_comm_play_conf(channel,'muzzled').ctime()))
                return
        #How about this specific character?
        
        if self.isic:
            if self.player.get_comm_char_conf(channel,self.character,'muzzled'):
                if self.player.get_comm_char_conf(channel,self.character,'muzzled') > utcnow():
                    string = "Your current character has been gagged from channel '%s' by %s until %s"
                    caller.msg(string % (channel.db_key, self.player.get_comm_char_conf(channel,self.character,'muzzledby'),
                                         self.player.get_comm_char_conf(channel,self.character,'muzzled').ctime()))
                    return
        
        # Enforce Mode 2's 'only when IC' feature and call character specific data if so.
        if channel.get_conf('displaymode') == 2:
            if not self.isic:
                string = "You can only use channel '%s' while @ic."
                caller.msg(string % channel.db_key)
                return

        # Determine 'name' of speaker and any titles.
        speaker = self.speaker_name(channel)
        title = self.speaker_title(channel)
        #messg = create.create_message(caller, msg, channels=[channel])
        channel.msg(msg,senders=caller,sender_strings=speaker,external=False,title=title)
        
class CmdChannel(MuxCommand):
    """
    @channel - This replicates some features of PennMUSH's @channel command.
    
    Usage:
        @channel[/switch] <channel>[=<input>]
        
        Switches:
        on - turns on a channel, using +[first letter] or [<input>] as an alias.
        off - remove an alias to a channel. Removing all aliases removes the channel.
        list - show all channels.
        who - shows everyone subscribed to a channel.
        title - With no input, displays your title (Player's if @ooc, Char's if @ic)
                for the channel. =<input> sets it, but if <input> is blank, deletes.
        add - works exactly like @ccreate
        rename - renames a channel to <input>
        delete - works exactly like @cdestroy
        lock - works exactly like @cset
        mode - works exactly like @cmode with no switches.
    """
    key = "@channel"
    aliases = ["@chan"]
    locks = "cmd:all()"
    sysname = "COMM"
    help_category = "Comms"

    def func(self):
        caller = self.caller
        switches = self.switches
        rhs = self.rhs
        lhs = self.lhs
        isadmin = self.caller.locks.check_lockstring(self.caller, "dummy:perm(Wizards)")
        playswitches = ['list','who','on','off','title','recall','add','rename','delete','lock','mode']
        
        switches = self.partial(switches,playswitches)
        
        #Pick a switch, any switch! Or no switch.
        if 'add' in switches:
            self.switch_add()
        elif 'delete' in switches:
            self.switch_delete()
        elif 'lock' in switches:
            self.switch_lock(lhs,rhs)
        elif 'rename' in switches:
            self.switch_rename(lhs,rhs)
        elif 'mode' in switches:
            self.switch_mode(lhs,rhs)
        elif 'list' in switches:
            self.switch_list()
        elif 'who' in switches:
            self.switch_who()
        elif 'on' in switches:
            self.switch_on(lhs,rhs)
        elif 'off' in switches:
            self.switch_off()
        elif 'title' in switches:
            self.switch_title()
        elif 'recall' in switches:
            self.switch_recall(lhs,rhs)
        else:
            self.caller.msg("%s requires a switch. See help %s" % (self.key,self.key))

    def switch_on(self,lhs,rhs):
        if rhs:
            self.caller.execute_cmd("addcom %s=%s" % (rhs,lhs))
        else:
            self.caller.execute_cmd("addcom %s=%s" % ("+" + lhs[0].lower(),lhs))
    
    def switch_off(self):
        self.caller.execute_cmd("delcom %s" % self.args)
        
    def switch_title(self):
        self.caller.execute_cmd("@ctitle %s" % self.args)
        
    def switch_add(self,lhs,rhs):
        self.caller.execute_cmd("@ccreate %s" % self.args)
        
    def switch_delete(self):
        self.caller.execute_cmd("@cdestroy %s" % self.args)
        
    def switch_who(self):
        self.caller.execute_cmd("@cwho %s" % self.args)
        
    def switch_recall(self):
        self.caller.execute_cmd("@crecall %s" % self.args)
        
    def switch_list(self):
        self.caller.execute_cmd("@clist %s" % self.args)
    
    def switch_lock(self):
        self.caller.execute_cmd("@cset %s" % self.args)

    def switch_mode(self):
        self.caller.execute_cmd("@cmode %s" % self.args)

class CmdCRename(MuxCommand):
    """
    @crename - Rename a channel.
    
    Usage:
        @crename <channel>=<newname>
        
    You must control the channel for this to work.
    """
    key = "@crename"
    locks = "cmd:all()"
    sysname = "COMM"
    help_category = "Comms"
    
    def func(self):
        caller = self.caller
        switches = self.switches
        rhs = self.rhs
        lhs = self.lhs
        isadmin = self.caller.locks.check_lockstring(self.caller, "dummy:perm(Wizards)")
        
        if not lhs:
            string = "No channel entered to rename."
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        channel = find_channel(self.caller,lhs)
        if not channel:
            string = "Channel '%s' not found." % lhs
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        if not channel.access(self.caller, "control"):
            string = "You don't control this channel."
            self.msg(msghead(self.sysname,error=True) + string)
            return
        if not rhs:
            string = "You must enter a new name for the channel."
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        channel2 = find_channel(self.caller,rhs)
        if len(channel2):
            string = "A channel by that name already exists." % lhs
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        string = "Channel '%s' renamed to '%s'!" % (channel,rhs)
        self.caller.msg(msghead(self.sysname) + string)
        cemit(channel,"Channel was Renamed to '%s' by %s" % (rhs,self.player.key))
        channel.db_key = rhs
        channel.save()
        
class CmdCTitle(MuxCommand):
    """
    @ctitle - set a channel title.
    
    Usage:
        @ctitle[/switch] <channel>[=<title>]
        
    Switches:
        clear - clears a chantitle for given channel.
        player - force to set player title.
        
    Used without a =, such as @ctitle Public, displays relevant title.
    
    When you are @ic, this sets a title for the character, or player if @ooc. 
    Use /player to force it to set or show your Player title.
    
    Setting a title to nothing (such as using @ctitle Public=) is the same as
    using /clear.

    Channel titles show only on channels that are set to Mode 0, 1, or 2.
    """
    key = "@ctitle"
    locks = "cmd:all()"
    sysname = "COMM"
    help_category = "Comms"

    def func(self):
        caller = self.caller
        switches = self.switches
        rhs = self.rhs
        lhs = self.lhs
        isadmin = self.caller.locks.check_lockstring(self.caller, "dummy:perm(Wizards)")
        playswitches = ['player','clear']
        admswitches = []
        
        if isadmin:
            callswitches = playswitches + admswitches
        else:
            callswitches = playswitches
        switches = self.partial(switches,callswitches)
        
        if not lhs:
            self.caller.msg(msghead(self.sysname,error=True) + "No channel entered.")
            return
        channel = Channel.objects.get_channel(lhs)
        if not channel:
            self.caller.msg(msghead(self.sysname,error=True) + "Channel '%s' not found." % lhs)
            return
        if self.isic or 'player' not in switches:
            charconf, created = CharCommConf.objects.get_or_create(chankey=channel,cid=self.character.dbobj)
        else:
            playconf, created = PlayCommConf.objects.get_or_create(chankey=channel,pid=self.player.dbobj)

        #This check is for clearing titles.
        if (not rhs and "=" in self.args) or 'clear' in switches:
            if self.isic and 'player' not in switches:
                charconf.ctitle = ""
                string = "Title for Channel '%s' cleared." % channel.db_key
                self.caller.msg(msghead(self.sysname) + string)
                charconf.save()
            else:
                playconf.ptitle = ""
                string = "Title for Channel '%s' cleared." % channel.db_key
                self.caller.msg(msghead(self.sysname) + string)
                playconf.save()
                
        #This check is for displaying titles.
        elif not rhs:
            if self.isic and 'player' not in switches:
                string = "Title for Channel '%s': %s" % (channel.db_key,charconf.ctitle)
            else:
                string = "Title for Channel '%s': %s" % (channel.db_key,playconf.ptitle)
            self.caller.msg(msghead(self.sysname) + string)
            
        #This branch sets a new Title.
        else:
            if self.isic and 'player' not in switches:
                charconf.ctitle = rhs
                charconf.save()
            else:
                playconf.ptitle = rhs
                playconf.save()
            string = "Title for Channel '%s' set to: %s" % (channel.db_key,rhs)
            self.caller.msg(msghead(self.sysname) + string)
            
class CmdCMode(MuxCommand):
    """
    @cmode - change a channel's display mode.
    
    Usage:
        @cmode[/switch] <channel>=<mode>
        
        You must control the channel to change its mode.
        
        Mode 0: Evennia Default. The user's name is their Player if @ooc, Character
                if IC.
        Mode 1: The channel only shows Player names, regardless of @ic or @ooc.
        Mode 2: The channel can only be used by Characters.
        Mode 3: The channel displays Player names if @ooc, and Playername.Charactername
                if @ic. Does not use titles.
                
    Switches:
        title - instead of setting mode, set titles allowance. <mode> must be
                boolean or equivalent: yes/1 or no/0.
        color - instead of setting mode, sets color. Must use a single character.
    """
    key = "@cmode"
    locks = "cmd:all()"
    sysname = "COMM"
    help_category = "Comms"
    
    
    
    def func(self):
        caller = self.caller
        switches = self.switches
        rhs = self.rhs
        lhs = self.lhs
        isadmin = self.caller.locks.check_lockstring(self.caller, "dummy:perm(Wizards)")
        playswitches = ['title','color']
        admswitches = []
        
        if isadmin:
            callswitches = playswitches + admswitches
        else:
            callswitches = playswitches
        switches = self.partial(switches,callswitches)
        
        
        if not lhs:
            string = "No channel entered to modeset."
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        channel = Channel.objects.get_channel(lhs)
        if not channel:
            string = "Channel '%s' not found." % lhs
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        if not channel.access(self.caller, "control"):
            string = "You don't control this channel."
            self.msg(msghead(self.sysname,error=True) + string)
            return
        chanconf, created=ChanCommConf.objects.get_or_create(chankey=channel)
        if not rhs:
            string = "You must enter a new mode for the channel."
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        
        if 'title' in switches:
            if rhs.lower() not in ['yes','no','0','1']:
                string = "Title mode must be Yes, No, or Boolean equivalents 1 or 0."
                self.caller.msg(msghead(self.sysname,error=True) + string)
                return
            if rhs.lower() in ['yes','1']:
                titles = True
            elif rhs.lower() in ['no','0']:
                titles = False
            string = "Channel '%s' Titles Allowed set to '%s'!" % (channel.db_key,titles)
            self.caller.msg(msghead(self.sysname) + string)
            msg = "Channel Mode was changed to '%s' by %s" % (titles,self.player.key)
            chanconf.titles = titles
        elif 'color' in switches:
            if len(rhs) > 1:
                string = "Color mode must be a single character."
                self.caller.msg(msghead(self.sysname,error=True) + string)
                return
            string = "Channel '%s' Color set to '%s'!" % (channel.db_key,rhs)
            self.caller.msg(msghead(self.sysname) + string)
            msg = "Channel Mode was changed to '%s' by %s" % (rhs,self.player.key)
            chanconf.color = rhs
        else:
            if rhs not in ['0','1','2','3']:
                string = "Mode must be an integer 0 to 3."
                self.caller.msg(msghead(self.sysname,error=True) + string)
                return
            string = "Channel '%s' modeset to '%s'!" % (channel.db_key,rhs)
            self.caller.msg(msghead(self.sysname) + string)
            msg = "Channel Mode was changed to '%s' by %s" % (rhs,self.player.key)
            channel.msg()
            chanconf.displaymode = rhs
        cemit(channel.db_key,msg)
        chanconf.save()
        
class CmdCMuzzle(MuxCommand):
    """
    @cmuzzle - restrict a player from a channel for a length of time.
    
    Usage:
        @cmuzzle[/switch] <channel>=<player>/<duration>
        
    You must control the channel to muzzle or unmuzzle a player.

    <duration> must be a series of time values, such as: 5d 2h 6s
        (5 days, 2 hours, 6 seconds). 
    Invalid input will be ignored. Order does not matter.
    
        s = second
        m = minute
        h = hour
        d = day
        w = week
        y = year
        (sorry, no months.)

    Switches:
        remove - Undoes an existing muzzle. Duration ignored.
    """
    key = "@cmuzzle"
    locks = "cmd:all()"
    sysname = "COMM"
    help_category = "Comms"
    
    def func(self):
        caller = self.caller
        switches = self.switches
        rhs = self.rhs
        lhs = self.lhs
        isadmin = self.caller.locks.check_lockstring(self.caller, "dummy:perm(Wizards)")
        playswitches = ['remove']
        admswitches = []
        
        if isadmin:
            callswitches = playswitches + admswitches
        else:
            callswitches = playswitches
        switches = self.partial(switches,callswitches)
        
        if not lhs:
            string = "No channel entered to moderate."
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        channel = Channel.objects.get_channel(lhs)
        if not channel:
            string = "Channel '%s' not found." % lhs
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        if not channel.access(self.caller, "control"):
            string = "You don't control this channel."
            self.msg(msghead(self.sysname,error=True) + string)
            return

        if not rhs:
            muzzled = PlayCommConf.objects.filter(chankey=channel,muzzled__gt=datetime.datetime.now())
            if not len(muzzled):
                self.caller.msg(msghead(self.sysname) + "No Muzzlings to show.")
                return
            self.caller.msg(header("Muzzlings: %s" % channel.db_key))
            table = PrettyTable(['Name','Muzzled By','Muzzled Until'])
            table.max_width['Name'] = 20
            table.max_width['Muzzled By'] = 20
            table.max_width['Muzzled Until'] = 40
            for entry in muzzled:
                table.add_row([entry.pid.key,entry.muzzledby.key,entry.muzzled.ctime()])
            self.caller.msg(table)
            self.caller.msg(header())
            return
        
        if "/" in rhs:
            tname, durstring = rhs.split("/",1)
        else:
            tname = rhs

        target = ev.search_player(tname)
        if len(target):
            target = target[0]
        else:
            string = "Player '%s' not found!" % tname
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        if self.caller.locks.check_lockstring(target, "dummy:perm(Wizards)"):
            string = "On whose authority?"
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        playconf,created = PlayCommConf.objects.get_or_create(chankey=channel,pid=target.dbobj)
        
        if 'remove' in switches:
            playconf.muzzled = now
            playconf.save()
            string = "You unmuzzle '%s' from '%s'." % (target.key,channel.db_key)
            self.caller.msg(msghead(self.sysname) + string)
            string = "%s has removed your Channel '%s' muzzle." % (self.player.key,channel.db_key)
            target.msg(msghead(self.sysname) + string)
            cemit(STAFFREP,"%s removed %s's Muzzle from Channel '%s'" % (self.player.key,target.key,channel.db_key))
            cemit(channel.db_key,"%s removed %s' Muzzle." % (self.player.key,target.key))
        else:
            if not durstring:
                string = "Must include a duration!"
                self.caller.msg(msghead(self.sysname,error=True) + string)
                return
            duration = stringsecs(durstring)
            if not duration:
                string = "Duration couldn't be calculated, please try again."
                self.caller.msg(msghead(self.sysname,error=True) + string)
                return
            playconf.muzzled = utcnow() + datetime.timedelta(seconds=duration)
            playconf.muzzledby = self.player.dbobj
            playconf.save()
            string = "You muzzle '%s' from '%s'." % (target.key,channel.db_key)
            self.caller.msg(msghead(self.sysname) + string)
            string = "%s has Muzzled you from Channel '%s'." % (self.player.key,channel.db_key)
            target.msg(msghead(self.sysname) + string)
            cemit(STAFFREP,"%s muzzled %s from Channel '%s' until %s" % (self.player.key,target.key,channel.db_key,playconf.muzzled.ctime()))
            cemit(channel.db_key,"%s muzzled %s until %s." % (self.player.key,target.key,playconf.muzzled.ctime()))