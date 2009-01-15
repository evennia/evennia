"""
This file contains commands that require special permissions to use. These
are generally @-prefixed commands, but there are exceptions.
"""
from src.objects.models import Object
from src import defines_global
from src import ansi
from src import session_mgr
from src.util import functions_general

def cmd_reload(command):
    """
    Reloads all modules.
    """
    session = command.session
    session.msg("To be implemented...")
    #session.server.reload(session)

def cmd_boot(command):
    """
    Boot a player object from the server.
    """
    session = command.session
    pobject = session.get_pobject()
    switch_quiet = False
    switch_port = False

    if "quiet" in command.command_switches:
        # Don't tell the player they've been disconnected, silently boot them.
        switch_quiet = True

    if "port" in command.command_switches:
        # Boot by port number instead of name or dbref.
        switch_port = True

    if not command.command_argument:
        session.msg("Who would you like to boot?")
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
            objs = Object.objects.local_and_global_search(pobject, 
                                                    command.command_argument)
            
            if not objs:
                session.msg("No name or dbref match found for booting.")
                return

            if not objs[0].is_player():
                session.msg("You can only boot players.")
                return

            if not pobject.controls_other(objs[0]):
                if objs[0].is_superuser():
                    session.msg("You cannot boot a Wizard.")
                    return
                else:
                    session.msg("You do not have permission to boot that player.")
                    return

            if objs[0].is_connected_plr():
                boot_list.append(session_mgr.session_from_object(objs[0]))
            else:
                session.msg("That player is not connected.")
                return

        if not boot_list:
            session.msg("No matches found.")
            return
        
        # Carry out the booting of the sessions in the boot list.
        for boot in boot_list:
            if not switch_quiet:
                boot.msg("You have been disconnected by %s." % (pobject.name))
            boot.disconnectClient()
            session_mgr.remove_session(boot)
            return

def cmd_newpassword(command):
    """
    Set a player's password.
    """
    session = command.session
    pobject = session.get_pobject()
    eq_args = command.command_argument.split('=', 1)
    searchstring = eq_args[0]
    newpass = eq_args[1]
    
    if not command.command_argument or len(searchstring) == 0:    
        session.msg("What player's password do you want to change")
        return
    if len(newpass) == 0:
        session.msg("You must supply a new password.")
        return

    target_obj = Object.objects.standard_plr_objsearch(session, searchstring)
    # Use standard_plr_objsearch to handle duplicate/nonexistant results.
    if not target_obj:
        return

    if not target_obj.is_player():
        session.msg("You can only change passwords on players.")
    elif not pobject.controls_other(target_obj):
        session.msg("You do not control %s." % (target_obj.get_name(),))
    else:
        uaccount = target_obj.get_user_account()
        if len(newpass) == 0:
            uaccount.set_password()
        else:
            uaccount.set_password(newpass)
        uaccount.save()
        session.msg("%s - PASSWORD set." % (target_obj.get_name(),))
        target_obj.emit_to("%s has changed your password." % 
                           (pobject.get_name(show_dbref=False),))

def cmd_shutdown(command):
    """
    Shut the server down gracefully.
    """
    session = command.session
    server = command.server
    pobject = session.get_pobject()
    
    session.msg('Shutting down...')
    print 'Server shutdown by %s' % (pobject.get_name(show_dbref=False),)
    server.shutdown()
