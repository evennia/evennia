from django.contrib.auth.models import User
import functions_db

"""
Commands that are available from the connect screen.
"""

def cmd_connect(cdat):
   """
   This is the connect command at the connection screen. Fairly simple,
   uses the Django database API and User model to make it extremely simple.
   """
   session = cdat['session']
   uname = cdat['uinput']['splitted'][1]
   password = cdat['uinput']['splitted'][2]
   
   account = User.objects.filter(username=uname)
   user = account[0]
   
   autherror = "Invalid username or password!"
   if account.count() == 0:
      session.msg(autherror)
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
   uname = cdat['uinput']['splitted'][1]
   email = cdat['uinput']['splitted'][2]
   password = cdat['uinput']['splitted'][3]
   
   # Search for a user object with the specified username.
   account = User.objects.filter(username=uname)
   
   if not account.count() == 0:
      session.msg("There is already a player with that name!")
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
