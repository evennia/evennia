from django.contrib.auth.models import User
import functions_db
import functions_general

"""
Commands that are available from the connect screen.
"""

def cmd_connect(cdat):
   """
   This is the connect command at the connection screen. Fairly simple,
   uses the Django database API and User model to make it extremely simple.
   """

   session = cdat['session']

   # Argument check.
   if not functions_general.cmd_check_num_args(session, cdat['uinput']['splitted'], 2):
      return
   
   uemail = cdat['uinput']['splitted'][1]
   password = cdat['uinput']['splitted'][2]

   # Match an email address to an account.
   email_matches = functions_db.get_user_from_email(uemail)
   
   autherror = "Specified email does not match any accounts!"
   # No username match
   if email_matches.count() == 0:
      session.msg(autherror)
      return
   
   # We have at least one result, so we can check the password.
   user = email_matches[0]
      
   if not user.check_password(password):
      session.msg(autherror)
   else:
      uname = user.username
      session.login(user)
      
def cmd_create(cdat):
   """
   Handle the creation of new accounts.
   """
   session = cdat['session']

   # Argument check.
   if not functions_general.cmd_check_num_args(session, cdat['uinput']['splitted'], 2):
      return
   
   server = session.server
   quote_split = ' '.join(cdat['uinput']['splitted']).split("\"")
   
   if len(quote_split) < 2:
      session.msg("You must enclose your username in quotation marks.")
      return
   
   uname = quote_split[1]
   lastarg_split = quote_split[2].split()

   if len(lastarg_split) != 2:
      session.msg("You must specify an email address, followed by a password!")
      return
   
   email = lastarg_split[0]
   password = lastarg_split[1]

   # Search for a user object with the specified username.
   account = User.objects.filter(username=uname)
   # Match an email address to an account.
   email_matches = functions_db.get_user_from_email(email)
   
   if not account.count() == 0:
      session.msg("There is already a player with that name!")
   elif not email_matches.count() == 0:
      session.msg("There is already a player with that email address!")
   elif len(password) < 3:
      session.msg("Your password must be 3 characters or longer.")
   else:
      functions_db.create_user(cdat, uname, email, password)

def cmd_quit(cdat):
   """
   We're going to maintain a different version of the quit command
   here for unconnected users for the sake of simplicity. The logged in
   version will be a bit more complicated.
   """
   session = cdat['session']
   session.msg("Disconnecting...")
   session.handle_close()
