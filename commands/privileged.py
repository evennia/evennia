import defines_global
import functions_general
import functions_db
import ansi

"""
This file contains commands that require special permissions to use. These
are generally @-prefixed commands, but there are exceptions.
"""

def cmd_reload(cdat):
   """
   Reloads all modules.
   """
   session = cdat['session']
   server = session.server.reload(session)

def cmd_boot(cdat):
   """
   Boot a player object from the server.
   """
   session = cdat['session']
   pobject = session.get_pobject()
   args = cdat['uinput']['splitted'][1:]
   eq_args = ' '.join(args).split('=')
   searchstring = ''.join(eq_args[0])
   switches = cdat['uinput']['root_chunk'][1:]
   switch_quiet = False
   switch_port = False

   if not pobject.is_staff():
      session.msg("You do not have permission to do that.")
      return

   if "quiet" in switches:
      switch_quiet = True

   if "port" in switches:
      switch_port = True

   if len(args) == 0:
      session.msg("Who would you like to boot?")
      return
   else:
      boot_list = []
      if switch_port:
         sessions = session_mgr.get_session_list(True)
         for sess in sessions:
            if sess.getClientAddress()[1] == int(searchstring):
               boot_list.append(sess)
               # We're done here
               break
      else:
         # Grab the objects that match
         objs = functions_db.global_object_name_search(searchstring)
         
         if len(objs) < 1:
            session.msg("Who would you like to boot?")
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

      for boot in boot_list:
         if not switch_quiet:
            boot.msg("You have been disconnected by %s." % (pobject.name))
         boot.disconnectClient()
         session_mgr.remove_session(boot)
         return

def cmd_newpassword(cdat):
   """
   Set a player's password.
   """
   session = cdat['session']
   pobject = session.get_pobject()
   args = cdat['uinput']['splitted'][1:]
   eq_args = ' '.join(args).split('=')
   searchstring = ''.join(eq_args[0])
   newpass = ''.join(eq_args[1:])
   
   if len(args) == 0:   
      session.msg("What player's password do you want to change")
      return
   if len(newpass) == 0:
      session.msg("You must supply a new password.")
      return

   target_obj = functions_db.standard_plr_objsearch(session, searchstring)
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
      target_obj.emit_to("%s has changed your password." % (pobject.get_name(show_dbref=False),))

def cmd_shutdown(cdat):
   """
   Shut the server down gracefully.
   """
   session = cdat['session']
   server = cdat['server']
   pobject = session.get_pobject()
   
   session.msg('Shutting down...')
   print 'Server shutdown by %s' % (pobject.get_name(show_dbref=False),)
   server.shutdown()
