"""
This file contains commands that require special permissions to use. These
are generally @-prefixed commands, but there are exceptions.
"""

from django.contrib.auth.models import Permission, Group
from django.conf import settings
from src.objects.models import Object
from src import session_mgr
from src import comsys
from src.scripthandler import rebuild_cache
from src.cmdtable import GLOBAL_CMD_TABLE
from src.helpsys.models import HelpEntry
from src.helpsys import helpsystem
from src.config.models import CommandAlias
from src.config import edit_aliases
from src import cache 
def cmd_reload(command):
    """
    @reload - reload game subsystems

    Usage:
      @reload/switches

    Switches:
      aliases          - alias definitions
      commands         - the command modules
      scripts, parents - the script parent modules      
      all              - reload all of the above 
      
      cache            - flush the volatile cache (warning, this
                         might cause unexpected results if your
                         script parents use the cache a lot)
      reset            - flush cache then reload all 

    Reloads all the identified subsystems. Flushing the cache is
    generally not needed outside the main game development. 
    """
    source_object = command.source_object
    switches = command.command_switches    
    if not switches or switches[0] not in ['all','aliases','alias',
                                           'commands','command',
                                           'scripts','parents',
                                           'cache','reset']:
        source_object.emit_to("Usage: @reload/<aliases|scripts|commands|all>")
        return
    switch = switches[0]
    sname = source_object.get_name(show_dbref=False)

    if switch in ["reset", "cache"]:
        # Clear the volatile cache 
        cache.flush()        
        comsys.cemit_mudinfo("%s flushed the non-persistent cache." % sname)
    if switch in ["reset","all","aliases","alias"]:
        # Reload Aliases
        command.session.server.reload_aliases(source_object=source_object)
        comsys.cemit_mudinfo("%s reloaded Aliases." % sname)    
    if switch in ["reset","all","scripts","parents"]:
        # Reload Script parents
        rebuild_cache()
        comsys.cemit_mudinfo("%s reloaded Script parents." % sname)        
    if switch in ["reset","all","commands","command"]:
        # Reload command objects.
        comsys.cemit_mudinfo("%s is reloading Command modules ..." % sname)
        command.session.server.reload(source_object=command.source_object)
        comsys.cemit_mudinfo("... all Command modules were reloaded.")

GLOBAL_CMD_TABLE.add_command("@reload", cmd_reload,
                             priv_tuple=("genperms.process_control",), help_category="Admin")
GLOBAL_CMD_TABLE.add_command("@restart", cmd_reload,
                             priv_tuple=("genperms.process_control",), help_category="Admin")

def cmd_boot(command):
    """
    @boot 

    Usage
      @boot <player obj>
      
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
                             priv_tuple=("genperms.manage_players",),
                             help_category="Admin")

def cmd_newpassword(command):
    """
    @newpassword

    Usage:
      @newpassword <user obj> = <new password>

    Set a player's password.
    """
    source_object = command.source_object
    eq_args = command.command_argument.split('=', 1)
    searchstring = eq_args[0]
    newpass = eq_args[1]
    
    if not command.command_argument or len(searchstring) == 0:    
        source_object.emit_to("What player's password do you want to change?")
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
                             priv_tuple=("genperms.manage_players",),
                             help_category="Admin")

def cmd_home(command):
    """
    home

    Usage:
      home 

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
                             priv_tuple=("genperms.process_control",),
                             help_category="Admin")

def cmd_shutdown(command):
    """
    @shutdown

    Usage:
      @shutdown 

    Shut the game server down gracefully.
    """    
    command.source_object.emit_to('Shutting down...')
    print 'Server shutdown by %s' % (command.source_object.get_name(show_dbref=False),)
    command.session.server.shutdown()
GLOBAL_CMD_TABLE.add_command("@shutdown", cmd_shutdown,
                             priv_tuple=("genperms.process_control",),
                             help_category="Admin")


# permission administration

# Django automatically creates a host of permissions that we don't want to
# mess with, but which are not very useful from inside the game. While these
# permissions are ok to use, we only show the permissions that we have defined
# in our settings file in order to give better control. 

APPS_NOSHOW = ("news","admin","auth","config","contentypes",
               "flatpages","news","sessions","sites")
SETTINGS_PERM_NAMES = []
for apps in settings.PERM_ALL_DEFAULTS + settings.PERM_ALL_CUSTOM:
    for permtuples in apps:
        SETTINGS_PERM_NAMES.append(permtuples[1])

def cmd_setperm(command):
    """
    @setperm - set permissions

    Usage:
      @setperm[/switch] [<user>] = [<permission>]

    Switches:
      add : add a permission from <user>
      del : delete a permission from <user>
      list : list all permissions, or those set on <user>
            
    This command sets/clears individual permission bits on a user.
    Use /list without any arguments to see all available permissions or those
    defined on the <user> argument. 
    """
    source_object = command.source_object
    args = command.command_argument
    switches = command.command_switches

    if not args:
        if "list" not in switches:
            source_object.emit_to("Usage: @setperm[/switch] [user] = [permission]")
            return
        else:
            #just print all available permissions
            s = "\n---Permission name  %s  ---Description" % (24 * " ") 
            permlist  = [perm for perm in Permission.objects.all() if perm.content_type.app_label not in APPS_NOSHOW and
                                                                      perm.name in SETTINGS_PERM_NAMES]
            for p in permlist:
                app = p.content_type.app_label                
                if app not in APPS_NOSHOW:
                    s += "\n%s.%s%s\t%s" % (app, p.codename, (35 - len(app) - len(p.codename)) * " ", p.name)
            source_object.emit_to(s)
            return 
    #we have command arguments.     
    arglist = args.split('=',1)
    obj_name = arglist[0].strip()
    if not obj_name:
        source_object.emit_to("Usage: @setperm[/switch] [user] [= permission]")
        return
    obj = source_object.search_for_object(obj_name)
    if not obj:
        return
    user = obj.get_user_account()
    if not user:
        return 
    if len(arglist) == 1:
        #if we didn't have any =, we list the permissions set on <object>. 
        s = ""
        if obj.is_superuser():
            s += "\n  This is a SUPERUSER account! All permissions are automatically set."
        if not user.is_active:
            s += "\n  ACCOUNT NOT ACTIVE."
        if obj.is_staff():
            s += "\n  Member of staff (can enter Admin interface)"            
        aperms = user.get_all_permissions()
        gperms = user.get_group_permissions()
        uperms = [perm for perm in aperms if perm not in gperms]
        if gperms: 
            s += "\n  Group-inherited Permissions:"
            for p in gperms:
                s += "\n  --- %s" % p
        if uperms:
            s += "\n Individually granted Permisssions:"            
            for p in uperms:
                s += "\n  ---- %s" % p        
        if not s:
            s = "User %s has no permissions." % obj.get_name()
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
        if not switches:
            source_object.emit_to("You must supply a switch /add or /del.")
            return 
        if "add" in switches:
            #add the permission to this user            
            if user.is_superuser:
                source_object.emit_to("As a superuser you always have all permissions.")
                return 
            if user.has_perm(perm_string):
                source_object.emit_to("User already has this permission.")
                return
            user.user_permissions.add(permission)
            user.save();obj.save()
            source_object.emit_to("%s gained the permission '%s'." % (obj.get_name(), permission.name))       
            obj.emit_to("%s gave you the permission '%s'." % (source_object.get_name(show_dbref=False,no_ansi=True),
                                                             permission.name))
        if "del" in switches:
            #delete the permission from this user
            if user.is_superuser:
                source_object.emit_to("As a superuser you always have all permissions.")
                return 
            if not user.has_perm(perm_string):
                source_object.emit_to("User is already lacking this permission.")
                return 
            user.user_permissions.remove(permission)
            user.save();obj.save()
            source_object.emit_to("%s lost the permission '%s'." % (obj.get_name(), permission.name))            
            obj.emit_to("%s removed your permission '%s'." % (source_object.get_name(show_dbref=False,no_ansi=True),
                                                             permission.name))            
GLOBAL_CMD_TABLE.add_command("@setperm", cmd_setperm,
                             priv_tuple=("auth.change_permission",
                                         "genperms.admin_perm"),
                             help_category="Admin")
            
def cmd_setgroup(command):
    """
    @setgroup - manage group memberships

    Usage:
      @setgroup[/switch] [<user>] [= <group>]

    Switches:
      add  - add user to a group
      del  - remove user from a group
      list - list all groups a user is part of, or list all available groups if no user is given

    Changes and views the group membership of a user. 
    """
    source_object = command.source_object
    args = command.command_argument
    switches = command.command_switches

    if not args:
        if "list" not in switches:
            source_object.emit_to("Usage: @setgroup[/switch] [user] [= permission]")
            return
        else:
            #just print all available permissions
            s = "\n---Group name (and grouped permissions):"
            for g in Group.objects.all():
                s += "\n %s" % g.name 
                for p in g.permissions.all():
                    app = p.content_type.app_label
                    if app not in APPS_NOSHOW:
                        s += "\n --- %s.%s%s\t%s" % (app, p.codename,
                                                     (35 - len(app) - len(p.codename)) * " ", p.name)
            source_object.emit_to(s)
            return 
    #we have command arguments.     
    arglist = args.split('=',1)
    obj_name = arglist[0].strip()
    if not obj_name:
        source_object.emit_to("Usage: @setgroup[/switch] [user] = [permission]")
        return
    obj = source_object.search_for_object(obj_name)
    if not obj:
        return
    if not obj.is_player():
        source_object.emit_to("Only players may be members of permission groups.")
        return
    user = obj.get_user_account()
    if not user:
        return 
    if len(arglist) == 1:
        #if we didn't have any =, we list the groups this user is member of
        s = ""
        if obj.is_superuser():
            s += "\n  This is a SUPERUSER account! Group membership does not matter."
        if not user.is_active:
            s += "\n  ACCOUNT NOT ACTIVE."
        for g in user.groups.all():
            s += "\n --- %s" % g 
            for p in g.permissions.all():
                app = p.content_type.app_label
                s += "\n   -- %s.%s%s\t%s" % (app, p.codename, (35 - len(app) - len(p.codename)) * " ", p.name)                
        if not s:
            s = "User %s is not a member of any groups." % obj.get_name()
        else: 
            s = "\nGroup memberships for user %s: %s" % (obj.get_name(),s)     
        source_object.emit_to(s)
    else:
        # we supplied an argument on the form obj = group
        group_string = arglist[1].strip()
        try: 
            group = Group.objects.get(name=group_string)            
        except Group.DoesNotExist:
            source_object.emit_to("Group '%s' is not a valid group. Remember that the name is case-sensitive.\nUse @chperm/list for help with valid group names." % group_string)
            return
        if not switches:
            source_object.emit_to("You must supply a switch /add or /del.")
            return 
        if "add" in switches:
            #add the user to this group
            if user.is_superuser:
                source_object.emit_to("As a superuser, group access does not matter.")
                return
            if user.groups.filter(name=group_string):
                source_object.emit_to("User is already a member of this group.")
                return
            user.groups.add(group)
            user.save(); obj.save()
            source_object.emit_to("%s added to group '%s'." % (obj.get_name(), group.name))       
            obj.emit_to("%s added you to the group '%s'." % (source_object.get_name(show_dbref=False,no_ansi=True),
                                                             group.name))
        if "del" in switches:
            #delete the permission from this user
            if user.is_superuser:
                source_object.emit_to("As a superuser, group access does not matter.")
                return
            if not user.groups.filter(name=group_string):
                source_object.emit_to("User was not in this group to begin with.")
                return
            
            user.groups.remove(group)
            user.save(); obj.save()
            source_object.emit_to("%s was removed from group '%s'." % (obj.get_name(), group.name))            
            obj.emit_to("%s removed you from group '%s'." % (source_object.get_name(show_dbref=False,no_ansi=True),
                                                             group.name))            
GLOBAL_CMD_TABLE.add_command("@setgroup", cmd_setgroup,
                             priv_tuple=("auth.change_group",
                                         "genperms.admin_group"),
                             help_category="Admin")

def cmd_sethelp(command):
    """
    @sethelp - edit the help database

    Usage:
      @sethelp[/switches] <topic>[,category][(permissions)][:<text>]

    Switches:
      add    - add or replace a new topic with text.
      append - add text to the end of topic.
      delete - remove help topic.
      force  - (used with add) create help topic also if the topic
               already exists. 
      newl   - (used with append) add a newline between the old
               text and the appended text. 

    Examples:
      @sethelp/add throw : This throws something at ...
      @sethelp/add throw, General (genperms.throwing) : This throws ...
      @sethelp/add throw : 1st help entry

    [[@sethelp_markup]]

    @sethelp Help markup
            
    The <text> entry in @sethelp supports markup to automatically divide the help text into 
    several sub-entries. The beginning of each new entry is marked in the form 

     [ [Title, category, (privtuple)] ]  (with no spaces between the square brackets)

    In the markup header, Title is mandatory, the other parts are optional. A new
    help entry named Title will be created for each occurence. It is recommended
    that the help entries should begin similarly since the system will then identify
    them and better handle a list of recommended topics. 
    """

    source_object = command.source_object
    arg = command.command_argument
    switches = command.command_switches

    if not arg or not switches:
        source_object.emit_to("Usage: @sethelp/[add|del|append] <topic>[,category][:<text>]")
        return     

    topicstr = ""
    category = ""
    text = ""
    permtuple = ()
    
    # analyze the argument
    arg = arg.split(':', 1)
    if len(arg) < 2:
        # no : detected; this means we are deleting something.
        topicstr = arg[0].strip()
    else:
        text = arg[1].strip()
        # we have 4 possibilities:
        # topicstr 
        # topicstr, category
        # topicstr (perm1,perm2,...) 
        # topicstr, category, (perm1,perm2,...)
        arg = arg[0].split('(',1)
        if len(arg) > 1:
            # we have a perm tuple
            arg, permtuple = arg
            try:
                permtuple = permtuple.strip()[:-1] # cut last ')'
            except IndexError:
                source_object.emit_to("Malformed permission tuple. %s" % permtuple)
                return 
            permtuple = tuple(permtuple.split(','))
        else:
            # no perm tuple
            arg = arg[0]        
        arg = arg.split(',', 1)
        if len(arg) > 1:
            # we have a category
            category = arg[1].strip()            
        topicstr = arg[0].strip()            

    if 'add' in switches:
        # add a new help entry. 
        if not topicstr or not text:
            source_object.emit_to("Usage: @sethelp/add <topic>[,category]:<text>")
            return 
        force_create = ('for' in switches) or ('force' in switches)
        topics = helpsystem.edithelp.add_help_manual(source_object, topicstr,
                                                     category, text,
                                                     permissions=permtuple,
                                                     force=force_create)
        if not topics:
            return 
        if len(topics) == 1:
            string = "The topic already exists. Use /force to overwrite it."
        elif len(topics)>1:
            string = "The following results are similar to '%s'."
            string += " Make sure you are not misspelling, then "
            string += "use the /force flag to create a new entry."
            string += "\n    ".join(topics)            
        source_object.emit_to(string)
        
    elif 'append' in switches or 'app' in switches:
        # add text to the end of a help topic        
        if not topicstr or not text:
            source_object.emit_to("Usage: @sethelp/append <topic>:<text>")
            return
        # find the topic to append to
        topics = HelpEntry.objects.find_topicmatch(source_object, topicstr)        
        if not topics:
            source_object.emit_to("Help topic '%s' not found." % topicstr)        
        elif len(topics) > 1:
            string = "Multiple matches to this topic. Refine your search."
            string += "\n    ".join(topics)
        else:
            # we have exactly one match. Extract all info from it,
            # append the text and feed it back into the system. 
            newtext = topics[0].get_entrytext_ingame()
            category = topics[0].category            
            perm_tuple = topics[0].canview
            if perm_tuple:
                perm_tuple = tuple(perm for perm in perm_tuple.split(','))

            newl = "\n"
            if 'newl' in switches or 'newline' in switches:
                newl = "\n\n"
            newtext += "%s%s" % (newl, text)
        
            topics = helpsystem.edithelp.add_help_manual(source_object,
                                                         topicstr,
                                                         category,
                                                         newtext,
                                                         perm_tuple,
                                                         force=True)
            
    elif 'del' in switches or 'delete' in switches:
        #delete a help entry
        topics = helpsystem.edithelp.del_help_manual(source_object, topicstr)
        if not topics:
            return 
        else:  
            string = "Multiple matches for '%s'. Please specify:" % topicstr 
            string += "\n    ".join(topics)

GLOBAL_CMD_TABLE.add_command("@sethelp", cmd_sethelp,
                             priv_tuple=("helpsys.add_help",
                                         "helpsys.del_help",
                                         "helpsys.admin_heelp"),
                             help_category="Admin")

def cmd_setcmdalias(command):
    """
    @setcmdalias - define shortcuts for commands

    Usage:
      @setcmdalias[/switch] alias [= command]

    Switches:
      list - view all command aliases
      add - add alias
      del - remove and existing alias

    This defins a new alias for a common command,
    for example like letting 'l' work as
    well as 'look'. When you change an alias you must
    use @reload/aliases before the alias-change gets
    recognized.
    """
    source_object = command.source_object
    args = command.command_argument
    switches = command.command_switches

    if "list" in switches:
        # show all aliases
        string = "Command aliases defined:"
        aliases = CommandAlias.objects.all()
        if not aliases:
            string = "No command aliases defined."
        for alias in aliases:
            string += "\n  %s -> %s" % (alias.user_input, alias.equiv_command)
        source_object.emit_to(string)
        return

    if not args:
        source_object.emit_to("Usage: @setcmdalias[/list/add/del] alias [= command]")
        return
    
    equiv_command = ""
    user_input = ""
    # analyze args
    if '=' in args:
        user_input, equiv_command = [arg.strip() for arg in args.split("=",1)]
    else:
        user_input = args.strip()

    if 'add' in switches:
        # add alias
        edit_aliases.add_alias(user_input, equiv_command)
        source_object.emit_to("Alias %s -> %s added. Now do '@reload/aliases'." % (user_input, equiv_command))
        return
    elif 'del' in switches:
        # delete alias
        edit_aliases.del_alias(user_input)
        source_object.emit_to("Removed alias %s (if it existed). Now do '@reload/aliases'." % user_input)
    else:
        source_object.emit_to("Usage: @setcmdalias[/switch] [command = ] alias")
GLOBAL_CMD_TABLE.add_command("@setcmdalias", cmd_setcmdalias,
                             priv_tuple=("genperms.process_control",),
                             help_category="Admin")
