"""
Commands that are available from the connect screen.
"""
from django.contrib.auth.models import User

from apps.objects.models import Attribute, Object
from src import defines_global
from src.util import functions_general

def cmd_connect(command):
    """
    This is the connect command at the connection screen. Fairly simple,
    uses the Django database API and User model to make it extremely simple.
    """

    session = command.session

    # Argument check.
    arg_list = command.command_argument.split()
    if not functions_general.cmd_check_num_args(session, arg_list, 2):
        return
    
    uemail = arg_list[0]
    password = arg_list[1]

    # Match an email address to an account.
    email_matches = Object.objects.get_user_from_email(uemail)
    
    # No username match
    if email_matches.count() == 0:
        session.msg("Specified email does not match any accounts!")
        return
    
    # We have at least one result, so we can check the password.
    user = email_matches[0]
        
    if not user.check_password(password):
        session.msg("Incorrect password.")
    else:
        uname = user.username
        session.login(user)
        
def cmd_create(command):
    """
    Handle the creation of new accounts.
    """
    session = command.session

    # Argument check.
    arg_list = command.command_argument.split()
    if not functions_general.cmd_check_num_args(session, arg_list, 2):
        return
    
    server = session.server
    quote_split = command.command_argument.split("\"")
    
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
    email_matches = Object.objects.get_user_from_email(email)
    # Look for any objects with an 'Alias' attribute that matches
    # the requested username
    alias_matches = Object.objects.filter(attribute__attr_name__exact="ALIAS", 
            attribute__attr_value__iexact=uname).filter(
                    type=defines_global.OTYPE_PLAYER)
    
    if not account.count() == 0 or not alias_matches.count() == 0:
        session.msg("There is already a player with that name!")
    elif not email_matches.count() == 0:
        session.msg("There is already a player with that email address!")
    elif len(password) < 3:
        session.msg("Your password must be 3 characters or longer.")
    else:
        Object.objects.create_user(command, uname, email, password)

def cmd_quit(command):
    """
    We're going to maintain a different version of the quit command
    here for unconnected users for the sake of simplicity. The logged in
    version will be a bit more complicated.
    """
    session = command.session
    session.msg("Disconnecting...")
    session.handle_close()
