"""
This file contains commands that require special permissions to
use. These are generally @-prefixed commands, but there are
exceptions.
"""

import traceback
from django.contrib.auth.models import User
from django.conf import settings
from src.server import sessionhandler
from src.players.models import PlayerDB
from src.scripts.models import ScriptDB
from src.objects.models import ObjectDB
from src.config.models import ConfigValue
from src.permissions.models import PermissionGroup
from src.utils import reloads, create, logger, utils
from src.permissions.permissions import has_perm, has_perm_string
from game.gamesrc.commands.default.muxcommand import MuxCommand


class CmdReload(MuxCommand):
    """
    Reload the system

    Usage:
      @reload

    This reloads the system modules and
    re-validates all scripts. 
    """
    key = "@reload"
    permissions = "cmd:reload"
    help_category = "System"

    def func(self):
        """
        Reload the system. 
        """        
        caller = self.caller 
        reloads.reload_modules()                 

        max_attempts = 4 
        for attempt in range(max_attempts):            
            # if reload modules take a long time,
            # we might end up in a situation where
            # the subsequent commands fail since they
            # can't find the reloads module (due to it
            # not yet fully loaded). So we retry a few 
            # times before giving up. 
            try:
                reloads.reload_scripts()
                reloads.reload_commands()
                break
            except AttributeError:
                if attempt < max_attempts-1:
                    caller.msg("            Waiting for modules(s) to finish (%s) ..." % attempt)
                    pass 
                else:
                    string =  "            ... The module(s) took too long to reload, "
                    string += "\n            so the remaining reloads where skipped."
                    string += "\n            Re-run @reload again when modules have fully "
                    string += "\n            re-initialized."
                    caller.msg(string)

class CmdPy(MuxCommand):
    """
    Execute a snippet of python code 

    Usage:
      @py <cmd>

    In this limited python environment.

    available_vars: 'self','me'  : caller
                    'here'  : caller.location
                    'obj'   : dummy obj instance
                    'script': dummy script instance
                    'config': dummy conf instance
                    'ObjectDB' : ObjectDB class
                    'ScriptDB' : ScriptDB class
                    'ConfigValue' ConfigValue class
    only two
    variables are defined: 'self'/'me' which refers to one's
    own object, and 'here' which refers to the current
    location. 
    """
    key = "@py"
    aliases = ["!"]
    permissions = "cmd:py"
    help_category = "Admin"
    
    def func(self):
        "hook function"
        
        caller = self.caller        
        pycode = self.args

        if not pycode:
            string = "Usage: @py <code>"
            caller.msg(string)
            return
        # create temporary test objects for playing with
        script = create.create_script("src.scripts.scripts.DoNothing",
                                      'testscript')
        obj = create.create_object("src.objects.objects.Object",
                                   'testobject')        
        conf = ConfigValue() # used to access conf values
        available_vars = {'self':caller,
                          'me':caller,
                          'here':caller.location,
                          'obj':obj,
                          'script':script,
                          'config':conf,
                          'ObjectDB':ObjectDB,
                          'ScriptDB':ScriptDB,
                          'ConfigValue':ConfigValue}

        caller.msg(">>> %s" % pycode)
        try:
            ret = eval(pycode, {}, available_vars)
            ret = "<<< %s" % str(ret)
        except Exception:
            try:
                exec(pycode, {}, available_vars)
                ret = "<<< Done."
            except Exception:
                errlist = traceback.format_exc().split('\n')
                if len(errlist) > 4:
                    errlist = errlist[4:]
                ret = "\n".join("<<< %s" % line for line in errlist if line)
        caller.msg(ret)
        obj.delete()
        script.delete()

class CmdListScripts(MuxCommand):
    """
    Operate on scripts.

    Usage:
      @scripts[/switches] [<obj or scriptid>]
      
    Switches:
      stop - stops an existing script
      validate - run a validation on the script(s)

    If no switches are given, this command just views all active
    scripts. The argument can be either an object, at which point it
    will be searched for all scripts defined on it, or an script name
    or dbref. For using the /stop switch, a unique script dbref is
    required since whole classes of scripts often have the same name.
    """
    key = "@scripts"
    aliases = "@listscripts"
    permissions = "cmd:listscripts"
    help_category = "Admin"

    def format_script_list(self, scripts):
        "Takes a list of scripts and formats the output."
        if not scripts:
            return "<No scripts>"

        table = [["id"], ["obj"], ["key"],["intval"],["next"],["rept"], ["db"],["typeclass"],["desc"]]
        for script in scripts:

            table[0].append(script.id)            
            if not hasattr(script, 'obj') or not script.obj:
                table[1].append("<Global>")
            else:
                table[1].append(script.obj.key)            
            table[2].append(script.key)                
            if not hasattr(script, 'interval') or not script.interval:
                table[3].append("--")
            else:
                table[3].append("%ss" % script.interval)                
            next = script.time_until_next_repeat()
            if not next:
                table[4].append("--")
            else:
                table[4].append("%ss" % next)

            if not hasattr(script, 'repeats') or not script.repeats:
                table[5].append("--")
            else:
                table[5].append("%ss" % script.repeats)
            if script.persistent:
                table[6].append("*")
            else:
                table[6].append("-")           
            typeclass_path = script.typeclass_path.rsplit('.', 1)
            table[7].append("%s" % typeclass_path[-1])
            table[8].append(script.desc)

        ftable = utils.format_table(table)
        string = ""
        for irow, row in enumerate(ftable):
            if irow == 0:
                srow = "\n" + "".join(row)
                srow = "{w%s{n" % srow.rstrip()
            else:
                srow = "\n" + "{w%s{n" % row[0] + "".join(row[1:])
            string += srow.rstrip()
        return string.strip()

    def func(self):
        "implement method"

        caller = self.caller
        args = self.args
        
        string = ""
        if args:

            # test first if this is a script match
            scripts = ScriptDB.objects.get_all_scripts(key=args)
            if not scripts:
                # try to find an object instead.
                objects = ObjectDB.objects.object_search(caller, 
                                                         args, 
                                                         global_search=True)
                if objects:                    
                    scripts = []
                    for obj in objects:
                        # get all scripts on the object(s)
                        scripts.extend(ScriptDB.objects.get_all_scripts_on_obj(obj))   
        else:
            # we want all scripts.
            scripts = ScriptDB.objects.get_all_scripts()

        if not scripts:
            string = "No scripts found with a key '%s', or on an object named '%s'." % (args, args)
            caller.msg(string)
            return         
            
        if self.switches and self.switches[0] in ('stop', 'del', 'delete'):
            # we want to delete something
            if not scripts:
                string = "No scripts/objects matching '%s'. " % args
                string += "Be more specific."
            elif len(scripts) == 1:
                # we have a unique match! 
                string = "Stopping script '%s'." % scripts[0].key
                scripts[0].stop()
                ScriptDB.objects.validate() #just to be sure all is synced
            else:
                # multiple matches.
                string = "Multiple script matches. Please refine your search:\n"
                string += self.format_script_list(scripts)        
        elif self.switches and self.switches[0] in ("validate", "valid", "val"):
            # run validation on all found scripts
            nr_started, nr_stopped = ScriptDB.objects.validate(scripts=scripts)
            string = "Validated %s scripts. " % ScriptDB.objects.all().count()
            string += "Started %s and stopped %s scripts." % (nr_started, nr_stopped)
        else:
            # No stopping or validation. We just want to view things.
            string = self.format_script_list(scripts)        
        caller.msg(string)


class CmdListCmdSets(MuxCommand):
    """
    list command sets on an object

    Usage:
      @listcmdsets [obj]

    This displays all cmdsets assigned
    to a user. Defaults to yourself.
    """
    key = "@listcmdsets"
    permissions = "cmd:listcmdsets"
    
    def func(self):
        "list the cmdsets"

        caller = self.caller
        if self.arglist:
            obj = caller.search(self.arglist[0]) 
            if not obj:
                return 
        else:
            obj = caller
        string = "%s" % obj.cmdset 
        caller.msg(string)

class CmdListObjects(MuxCommand):
    """
    Give a summary of object types in database

    Usage:
      @objects [<nr>]

    Gives statictics on objects in database as well as 
    a list of <nr> latest objects in database. If not 
    given, <nr> defaults to 10.
    """
    key = "@objects"
    aliases = ["@listobjects", "@listobjs"]
    permissions = "cmd:listobjects"
    help_category = "Building"

    def func(self):
        "Implement the command"

        caller = self.caller

        if self.args and self.args.isdigit():
            nlim = int(self.args)
        else:
            nlim = 10
        dbtotals = ObjectDB.objects.object_totals()
        #print dbtotals 
        string = "\n{wDatase Object totals:{n"
        table = [["Count"], ["Typeclass"]]
        for path, count in dbtotals.items():            
            table[0].append(count)
            table[1].append(path)
        ftable = utils.format_table(table, 3)
        for irow, row in enumerate(ftable):
            srow = "\n" + "".join(row)
            srow = srow.rstrip()
            if irow == 0:
                srow = "{w%s{n" % srow
            string += srow

        string += "\n\n{wLast %s Objects created:{n" % nlim
        objs = list(ObjectDB.objects.all())[-nlim:]               

        table = [["Created"], ["dbref"], ["name"], ["typeclass"]]
        for i, obj in enumerate(objs):
            table[0].append(utils.datetime_format(obj.date_created))
            table[1].append(obj.dbref)
            table[2].append(obj.key)
            table[3].append(str(obj.typeclass))
        ftable = utils.format_table(table, 5)
        for irow, row in enumerate(ftable):
            srow = "\n" + "".join(row)
            srow = srow.rstrip()
            if irow == 0:
                srow = "{w%s{n" % srow
            string += srow

        caller.msg(string)
    
class CmdBoot(MuxCommand):
    """
    @boot 

    Usage
      @boot[/switches] <player obj> [: reason]

    Switches:
      quiet - Silently boot without informing player
      port - boot by port number instead of name or dbref
      
    Boot a player object from the server. If a reason is
    supplied it will be echoed to the user unless /quiet is set. 
    """
    
    key = "@boot"
    permissions = "cmd:boot"
    help_category = "Admin"

    def func(self):
        "Implementing the function"
        caller = self.caller
        args = self.args
        
        if not args:
            caller.msg("Usage: @boot[/switches] <player> [:reason]")
            return

        if ':' in args:
            args, reason = [a.strip() for a in args.split(':', 1)]
        boot_list = []
        reason = ""

        if 'port' in self.switches:
            # Boot a particular port.
            sessions = sessionhandler.get_session_list(True)
            for sess in sessions:
                # Find the session with the matching port number.
                if sess.getClientAddress()[1] == int(args):
                    boot_list.append(sess)
                    break
        else:
            # Boot by player object
            pobj = caller.search("*%s" % args, global_search=True)
            if not pobj:
                return
            pobj = pobj
            if pobj.has_player:
                if not has_perm(caller, pobj, 'can_boot'):
                    string = "You don't have the permission to boot %s."
                    pobj.msg(string)
                    return 
                # we have a bootable object with a connected user
                matches = sessionhandler.sessions_from_object(pobj)
                for match in matches:
                    boot_list.append(match)
            else:
                caller.msg("That object has no connected player.")
                return

        if not boot_list:
            caller.msg("No matches found.")
            return

        # Carry out the booting of the sessions in the boot list.

        feedback = None 
        if not 'quiet' in self.switches:
            feedback = "You have been disconnected by %s.\n" % caller.name
            if reason:
                feedback += "\nReason given: %s" % reason

        for session in boot_list:
            name = session.name
            if feedback:
                session.msg(feedback)
            session.disconnectClient()
            sessionhandler.remove_session(session)
            caller.msg("You booted %s." % name)


class CmdDelPlayer(MuxCommand):
    """
    delplayer - delete player from server

    Usage:
      @delplayer[/switch] <name> [: reason]
      
    Switch:
      delobj - also delete the player's currently
                assigned in-game object.   

    Completely deletes a user from the server database,
    making their nick and e-mail again available.    
    """

    key = "@delplayer"
    permissions = "cmd:delplayer"
    help_category = "Admin"

    def func(self):
        "Implements the command."

        caller = self.caller
        args = self.args 

        if not args:
            caller.msg("Usage: @delplayer[/delobj] <player/user name or #id>")
            return

        reason = ""
        if ':' in args:
            args, reason = [arg.strip() for arg in args.split(':', 1)]

        # We use player_search since we want to be sure to find also players
        # that lack characters.
        players = PlayerDB.objects.filter(db_key=args)
        if not players:
            try:
                players = PlayerDB.objects.filter(id=args)
            except ValueError:
                pass

        if not players:            
            # try to find a user instead of a Player
            try:
                user = User.objects.get(id=args)
            except Exception:            
                try:
                    user = User.objects.get(username__iexact=args)                        
                except Exception:
                    string = "No Player nor User found matching '%s'." % args
                    caller.msg(string)
                    return                     
            try:
                player = user.get_profile()
            except Exception:
                player = None
                                
            if not has_perm_string(caller, 'manage_players'):
                string = "You don't have the permissions to delete this player."
                caller.msg(string)
                return 
            string = ""
            name = user.username
            user.delete()
            if player:
                name = player.name
                player.delete()
                string = "Player %s was deleted." % name
            else:
                string += "The User %s was deleted, but had no Player associated with it." % name
            caller.msg(string)
            return 
    
        elif len(players) > 1:
            string = "There where multiple matches:"
            for player in players:
                string += "\n %s %s" % (player.id, player.key) 
            return 

        else:
            # one single match

            player = players[0]
            user = player.user
            character = player.character

            if not has_perm(caller, player, 'manage_players'):
                string = "You don't have the permissions to delete that player."
                caller.msg(string)
                return 

            uname = user.username
            # boot the player then delete 
            if character and character.has_player:
                caller.msg("Booting and informing player ...")
                string = "\nYour account '%s' is being *permanently* deleted.\n" %  uname
                if reason:
                    string += " Reason given:\n  '%s'" % reason
                character.msg(string)
                caller.execute_cmd("@boot %s" % uname)
                
            player.delete()
            user.delete()    
            caller.msg("Player %s was successfully deleted." % uname)


class CmdNewPassword(MuxCommand):
    """
    @newpassword

    Usage:
      @newpassword <user obj> = <new password>

    Set a player's password.
    """
    
    key = "@newpassword"
    permissions = "cmd:newpassword"
    help_category = "Admin"

    def func(self):
        "Implement the function."

        caller = self.caller

        if not self.rhs:
            caller.msg("Usage: @newpassword <user obj> = <new password>")
            return 
        
        # the player search also matches 'me' etc. 
        character = caller.search("*%s" % self.lhs, global_search=True)            
        if not character:
            return     
        player = character.player
        player.user.set_password(self.rhs)
        player.user.save()
        caller.msg("%s - new password set to '%s'." % (player.name, self.rhs))
        if character != caller:
            player.msg("%s has changed your password to '%s'." % (caller.name, self.rhs))

class CmdHome(MuxCommand):
    """
    home

    Usage:
      home 

    Teleport the player to their home.
    """
    
    key = "home"
    permissions = "cmd:home"
    
    def func(self):
        "Implement the command"
        caller = self.caller        
        home = caller.home
        if not home:
            caller.msg("You have no home set.")
        else:
            caller.move_to(home)
            caller.msg("There's no place like home ...")
        

class CmdService(MuxCommand):
    """
    @service - manage services

    Usage:
      @service[/switch] <service>

    Switches:
      start  - activates a service
      stop   - stops a service
      list   - shows all available services
      
    Service management system. Allows for the listing,
    starting, and stopping of services.
    """

    key = "@service"
    permissions = "cmd:service"
    help_category = "Admin"

    def func(self):
        "Implement command"
        
        caller = self.caller
        switches = self.switches
        
        if not switches or \
                switches[0] not in ["list","start","stop"]:
            caller.msg("Usage: @service/<start|stop|list> [service]")
            return             
        switch = switches[0]

        # get all services
        sessions = caller.sessions
        if not sessions:             
            return 
        service_collection = sessions[0].server.service_collection

        if switch == "list":
            # Just display the list of installed services and their
            # status, then exit.
            string = "-" * 40
            string += "\nService Listing"     
            
            for service in service_collection.services:
                if service.running:
                    status = 'Running'
                else:
                    status = 'Inactive'
                string += '\n * %s (%s)' % (service.name, status)
            string += "\n" + "-" * 40
            caller.msg(string)
            return

        # Get the service to start / stop
        
        try:
            service = service_collection.getServiceNamed(self.args)
        except Exception:
            string = 'Invalid service name. This command is case-sensitive. ' 
            string += 'See @service/list.'
            caller.msg(string)
            return

        if switch == "stop":
            # Stopping a service gracefully closes it and disconnects
            # any connections (if applicable).

            if not service.running:
                caller.msg('That service is not currently running.')
                return
            # We don't want to kill the main Evennia TCPServer services
            # here. If wanting to kill a listening port, one needs to
            # do it through settings.py and a restart.
            if service.name[:7] == 'Evennia':
                string = "You can not stop Evennia TCPServer services this way."
                string += "\nTo e.g. remove a listening port, change settings file and restart."
                caller.msg(string)
                return        
            #comsys.cemit_mudinfo("%s is *Stopping* the service '%s'." % (sname, service.name)) #TODO!
            service.stopService()
            return

        if switch == "start":
            #Starts a service.
            if service.running:
                caller.msg('That service is already running.')
                return
            #comsys.cemit_mudinfo("%s is *Starting* the service '%s'." % (sname,service.name)) #TODO!
            service.startService()

class CmdShutdown(MuxCommand):

    """
    @shutdown

    Usage:
      @shutdown [announcement]

    Shut the game server down gracefully. 
    """    
    key = "@shutdown"
    permissions = "cmd:shutdown"
    help_category = "System"
    
    def func(self):
        "Define function"
        try:
            session = self.caller.sessions[0]
        except Exception:
            return         
        self.caller.msg('Shutting down server ...')
        announcement = "\nServer is being SHUT DOWN!\n"
        if self.args: 
            announcement += "%s\n" % self.args

        sessionhandler.announce_all(announcement)          
        logger.log_infomsg('Server shutdown by %s.' % self.caller.name)

        # access server through session so we don't call server directly 
        # (importing it directly would restart it...)
        session.server.shutdown()

class CmdPerm(MuxCommand):
    """
    @perm - set permissions

    Usage:
      @perm[/switch] [<object>] = [<permission>]
      @perm[/switch] [*<player>] = [<permission>]

    Switches:
      del : delete the given permission from <object>.
      list : list all permissions, or those set on <object>
            
    Use * before the search string to add permissions to a player. 
    This command sets/clears individual permission strings on an object.
    Use /list without any arguments to see all available permissions
    or those defined on the <object>/<player> argument. 
    """
    key = "@perm"
    aliases = "@setperm"
    permissions = "cmd:perm"
    help_category = "Admin"

    def func(self):
        "Implement function"

        caller = self.caller
        switches = self.switches
        lhs, rhs = self.lhs, self.rhs

        if not self.args:
            
            if "list" not in switches:
                string = "Usage: @setperm[/switch] [object = permission]\n" 
                string +="       @setperm[/switch] [*player = permission]"
                caller.msg(string)
                return
            else:
                #just print all available permissions
                string = "\nAll defined permission groups and keys (i.e. not locks):"
                pgroups = list(PermissionGroup.objects.all())
                pgroups.sort(lambda x,y: cmp(x.key, y.key)) # sort by group key

                for pgroup in pgroups:
                    string += "\n\n - {w%s{n (%s):" % (pgroup.key, pgroup.desc)
                    string += "\n%s" % \
                        utils.fill(", ".join(sorted(pgroup.group_permissions)))                
                caller.msg(string)
                return 

        # locate the object/player         
        obj = caller.search(lhs, global_search=True)
        if not obj:
            return         
        
        pstring = ""
        if utils.inherits_from(obj, settings.BASE_PLAYER_TYPECLASS):
            pstring = " Player "
        
        if not rhs: 
            string = "Permission string on %s{w%s{n: " % (pstring, obj.key)
            if not obj.permissions:
                string += "<None>"
            else:
                string += ", ".join(obj.permissions)
            if pstring and obj.is_superuser:
                string += "\n(... But this player is a SUPERUSER! "
                string += "All access checked are passed automatically.)"
            elif obj.player and obj.player.is_superuser:
                string += "\n(... But this object's player is a SUPERUSER! "
                string += "All access checked are passed automatically.)"
            caller.msg(string)
            return 
            
        # we supplied an argument on the form obj = perm

        cstring = ""
        tstring = ""
        if 'del' in switches:
            # delete the given permission(s) from object.
            for perm in self.rhslist:
                try:
                    index = obj.permissions.index(perm)
                except ValueError:
                    cstring += "\nPermission '%s' was not defined on %s%s." % (perm, pstring, lhs)
                    continue
                permissions = obj.permissions
                del permissions[index]
                obj.permissions = permissions 
                cstring += "\nPermission '%s' was removed from %s%s." % (perm, pstring, obj.name)
                tstring += "\n%s revokes the permission '%s' from you." % (caller.name, perm)
        else:
            # As an extra check, we warn the user if they customize the 
            # permission string (which is okay, and is used by the lock system)            
            permissions = obj.permissions
            for perm in self.rhslist:

                if perm in permissions:
                    cstring += "\nPermission '%s' is already defined on %s%s." % (rhs, pstring, obj.name)
                else:
                    permissions.append(perm)
                    obj.permissions = permissions
                    cstring += "\nPermission '%s' given to %s%s." % (rhs, pstring, obj.name)
                    tstring += "\n%s granted you the permission '%s'." % (caller.name, rhs)        
        caller.msg(cstring.strip())
        if tstring:
            obj.msg(tstring.strip())
