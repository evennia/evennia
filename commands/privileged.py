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
