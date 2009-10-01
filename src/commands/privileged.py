"""
This file contains commands that require special permissions to use. These
are generally @-prefixed commands, but there are exceptions.
"""

from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from src.objects.models import Object
from src import defines_global
from src import ansi
from src import session_mgr
from src import comsys
from src.scripthandler import rebuild_cache
from src.util import functions_general
from src.cmdtable import GLOBAL_CMD_TABLE

def cmd_reload(command):
    """
    Reloads all modules.
    """
    source_object = command.source_object
    switches = command.command_switches    
    if not switches or switches[0] not in ['all','aliases','alias',
                                           'commands','command',
                                           'scripts','parents']:
        source_object.emit_to("Usage: @reload/<aliases|scripts|commands|all>")
        return
    switch = switches[0]
    sname = source_object.get_name(show_dbref=False)
    
    if switch in ["all","aliases","alias"]:
        #reload Aliases
        command.session.server.reload_aliases(source_object=source_object)
        comsys.cemit_mudinfo("%s reloaded Aliases." % sname)    
    if switch in ["all","scripts","parents"]:
        #reload Script parents
        rebuild_cache()
        comsys.cemit_mudinfo("%s reloaded Script parents." % sname)        
    if switch in ["all","commands","command"]:
        #reload command objects.
        comsys.cemit_mudinfo("%s is reloading Command modules ..." % sname)
        command.session.server.reload(source_object=command.source_object)
        comsys.cemit_mudinfo("... all Command modules were reloaded.")

GLOBAL_CMD_TABLE.add_command("@reload", cmd_reload,
                             priv_tuple=("genperms.process_control",)),
GLOBAL_CMD_TABLE.add_command("@restart", cmd_reload,
                             priv_tuple=("genperms.process_control",)),

def cmd_boot(command):
    """
    Boot a player object from the server.
    """
    source_object = command.source_object
    switch_quiet = False
    switch_port = False

    if "quiet" in command.command_switches:
        # Don't tell the player they've been disconnected, silently boot them.
        switch_quiet = True

    if "port" in command.command_switches:
        # Boot by port number instead of name or dbref.
        switch_port = True

    if not command.command_argument:
        source_object.emit_to("Who would you like to boot?")
        return
    else:
        boot_list = []
        if switch_port:
            # Boot a particular port.
            sessions = session_mgr.get_session_list(True)
            for sess in sessions:
                # Find the session with the matching port number.
                if sess.getClientAddress()[1] == int(command.command_argument):
                    boot_list.append(sess)
                    # Match found, kill the loop and continue with booting.
                    break
        else:
            # Grab the objects that match
            objs = Object.objects.local_and_global_search(source_object, 
                                                    command.command_argument)
            
            if not objs:
                source_object.emit_to("No name or dbref match found for booting.")
                return

            if not objs[0].is_player():
                source_object.emit_to("You can only boot players.")
                return

            if not source_object.controls_other(objs[0]):
                if objs[0].is_superuser():
                    source_object.emit_to("You cannot boot a Wizard.")
                    return
                else:
                    source_object.emit_to("You do not have permission to boot that player.")
                    return

            if objs[0].is_connected_plr():
                matches = session_mgr.sessions_from_object(objs[0])
                for match in matches:
                    boot_list.append(match)
            else:
                source_object.emit_to("That player is not connected.")
                return

        if not boot_list:
            source_object.emit_to("No matches found.")
            return
        
        # Carry out the booting of the sessions in the boot list.
        for boot in boot_list:
            if not switch_quiet:
                boot.msg("You have been disconnected by %s." % (source_object.name))
            boot.disconnectClient()
            session_mgr.remove_session(boot)
            return
GLOBAL_CMD_TABLE.add_command("@boot", cmd_boot,        
                             priv_tuple=("genperms.manage_players",))

def cmd_newpassword(command):
    """
    Set a player's password.
    """
    source_object = command.source_object
    eq_args = command.command_argument.split('=', 1)
    searchstring = eq_args[0]
    newpass = eq_args[1]
    
    if not command.command_argument or len(searchstring) == 0:    
        source_object.emit_to("What player's password do you want to change")
        return
    if len(newpass) == 0:
        source_object.emit_to("You must supply a new password.")
        return

    target_obj = source_object.search_for_object(searchstring)
    # Use search_for_object to handle duplicate/nonexistant results.
    if not target_obj:
        return

    if not target_obj.is_player():
        source_object.emit_to("You can only change passwords on players.")
    elif not source_object.controls_other(target_obj):
        source_object.emit_to("You do not control %s." % (target_obj.get_name(),))
    else:
        uaccount = target_obj.get_user_account()
        if len(newpass) == 0:
            uaccount.set_password()
        else:
            uaccount.set_password(newpass)
        uaccount.save()
        source_object.emit_to("%s - PASSWORD set." % (target_obj.get_name(),))
        target_obj.emit_to("%s has changed your password." % 
                           (source_object.get_name(show_dbref=False),))
GLOBAL_CMD_TABLE.add_command("@newpassword", cmd_newpassword, 
                             priv_tuple=("genperms.manage_players",))

def cmd_home(command):
    """
    Teleport the player to their home.
    """
    pobject = command.source_object
    if pobject.home == None:
        pobject.emit_to("You have no home set, @link yourself to somewhere.")
    else:
        pobject.emit_to("There's no place like home...")
        pobject.move_to(pobject.get_home())
GLOBAL_CMD_TABLE.add_command("home", cmd_home,
                             priv_tuple=("genperms.tel_anywhere",))

def cmd_service(command):
    """
    Service management system. Allows for the listing, starting, and stopping
    of services.
    """
    source_object = command.source_object
    switches = command.command_switches
    if not switches or switches[0] not in ["list","start","stop"]:
        source_object.emit_to("Usage: @servive/<start|stop|list> [service]")
        return 
    switch = switches[0].strip()
    sname = source_object.get_name(show_dbref=False)

    if switch == "list":        
        #Just display the list of installed services and their status, then exit.
        s = "-" * 40
        s += "\nService Listing"        
        for service in command.session.server.service_collection.services:
            # running is either 1 or 0, 1 meaning the service is running.
            if service.running == 1:
                status = 'Running'
            else:
                status = 'Inactive'
            s += '\n * %s (%s)' % (service.name, status)
        s += "\n" + "-" * 40
        source_object.emit_to(s)
        return
    
    if switch in ["stop", "start"]:
        # This stuff is common to both start and stop switches.

        collection = command.session.server.service_collection
        try:
            service = collection.getServiceNamed(command.command_argument)
        except:
            source_object.emit_to('Invalid service name. This command is case-sensitive. See @service/list.')
            return
        
    if switch == "stop":
        """
        Stopping a service gracefully closes it and disconnects any connections
        (if applicable).
        """
        if service.running == 0:
            source_object.emit_to('That service is not currently running.')
            return
        # We don't want killing main Evennia TCPServer services here. If
        # wanting to kill a listening port, one needs to do it through
        # settings.py and a restart.
        if service.name[:7] == 'Evennia':
            s = "You can not stop Evennia TCPServer services this way."
            s += "\nTo e.g. remove a listening port, change settings file and restart."
            source_object.emit_to(s)
            return        
        comsys.cemit_mudinfo("%s is *Stopping* the service '%s'." % (sname, service.name))
        service.stopService()
        return
    
    if switch == "start":
        """
        Starts a service.
        """
        if service.running == 1:
            source_object.emit_to('That service is already running.')
            return
        comsys.cemit_mudinfo("%s is *Starting* the service '%s'." % (sname,service.name))
        service.startService()
        return
    
GLOBAL_CMD_TABLE.add_command("@service", cmd_service,
                             priv_tuple=("genperms.process_control",))

def cmd_shutdown(command):
    """
    Shut the server down gracefully.
    """    
    command.source_object.emit_to('Shutting down...')
    print 'Server shutdown by %s' % (command.source_object.get_name(show_dbref=False),)
    command.session.server.shutdown()
GLOBAL_CMD_TABLE.add_command("@shutdown", cmd_shutdown,
                             priv_tuple=("genperms.process_control",))

def cmd_chperm(command):
    """@chperm

    Usage:
      @chperm[/switch] [<user>] = [<permission>]

    Switches:
      add : add a permission from <user>
      del : delete a permission from <user>
      list : list all permissions set on <user>
            
      @chperm (change permission) sets/clears individual permission bits on a user.
      Use /list without any arguments to see all available permissions. 
    """
    source_object = command.source_object
    args = command.command_argument
    switches = command.command_switches

    if not args:
        if "list" not in switches:
            source_object.emit_to("Usage: @chperm[/switch] [user] = [permission]")
            return
        else:
            #just print all available permissions
            s = "\n---Permission name  %s  ---Description" % (24 * " ") 
            for p in Permission.objects.all():
                app = p.content_type.app_label                
                s += "\n%s.%s%s\t%s" % (app, p.codename, (35 - len(app) - len(p.codename)) * " ", p.name)
            source_object.emit_to(s)
            return 
    #we have command arguments. 
    arglist = args.split('=',1)
    obj_name = arglist[0].strip()
    obj = source_object.search_for_object(obj_name)
    if not obj:
        return
    if not obj.is_player():
        source_object.emit_to("Only players may have permissions.")
        return
    try: 
        user = User.objects.get(username=obj.get_name(show_dbref=False,no_ansi=True))
    except:
        raise
    if len(arglist) == 1:
        #if we didn't have any =, we list the permissions set on <object>. 
        s = ""
        if obj.is_superuser():
            s += "\n  This is a SUPERUSER account! All permissions are automatically set."
        if not user.is_active:
            s += "\n  ACCOUNT NOT ACTIVE."
        if obj.is_staff():
            s += "\n  Member of staff (can enter Admin interface)"            
        groups = user.groups.all()
        if groups:
            s += "\n Group memberships:"
            for g in groups:
                s += "\n  --- %s" % g 
        aperms = user.get_all_permissions()
        if aperms: 
            s += "\n  Extra User permissions:"
            gperms = user.get_group_permissions()
            for p in aperms:
                if p in gperms:
                    s += "\n  --- %s (group)"
                else:
                    s += "\n  ---- %s" % p        
        if not s:
            s = "User %s has no extra permissions." % obj.get_name()
        else: 
            s = "\nPermissions for user %s: %s" % (obj.get_name(),s)     
        source_object.emit_to(s)
    else:
        # we supplied an argument on the form obj = perm
        perm_string = arglist[1].strip()
        try: 
            app_label, codename = perm_string.split(".",1)
        except ValueError:
            source_object.emit_to("Permission should be on the form 'application.permission' .")
            return
        try: 
            permission = Permission.objects.filter(content_type__app_label=app_label).get(codename=codename)
        except Permission.DoesNotExist:
            source_object.emit_to("Permission type '%s' is not a valid permission.\nUse @chperm/list for help with valid permission strings." % perm_string)
            return
        if "add" in switches:
            #add the permission to this user
            if not source_object.has_perm("auth.add_permission"):
                source_object.emit_to(defines_global.NOPERMS_MSG)
                return
            if user.is_superuser:
                source_object.emit_to("As a superuser you always have all permissions.")
                return 
            if user.has_perm(perm_string):
                source_object.emit_to("User already has this permission.")
                return
            user.user_permissions.add(permission)
            user.save()
            obj.save()
            source_object.emit_to("%s gained the permission '%s'." % (obj.get_name(), permission.name))       
            obj.emit_to("%s gave you the permission '%s'." % (source_object.get_name(show_dbref=False,no_ansi=True),
                                                             permission.name))
        if "del" in switches:
            #delete the permission from this user
            if not source_object.has_perm("auth.delete_permission"):
                source_object.emit_to(defines_global.NOPERMS_MSG)
                return
            print obj.has_perm_list(perm_string)
            print obj.has_perm(perm_string)
            if user.is_superuser:
                source_object.emit_to("As a superuser you always have all permissions.")
                return 
            if not user.has_perm(perm_string):
                source_object.emit_to("User is already lacking this permission.")
                return 
            user.user_permissions.remove(permission)
            user.save()
            obj.save()
            source_object.emit_to("%s lost the permission '%s'." % (obj.get_name(), permission.name))            
            obj.emit_to("%s removed your permission '%s'." % (source_object.get_name(show_dbref=False,no_ansi=True),
                                                             permission.name))            
GLOBAL_CMD_TABLE.add_command("@chperm", cmd_chperm,
                             priv_tuple=("auth.change_permission",))
            
