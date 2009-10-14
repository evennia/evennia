"""
Commands that are available from the connect screen.
"""
import traceback
from django.contrib.auth.models import User
from src.objects.models import Object
from src import defines_global
from src.util import functions_general
from src.cmdtable import GLOBAL_UNCON_CMD_TABLE
from src.logger import log_errmsg

def cmd_connect(command):
    """
    This is the connect command at the connection screen. Fairly simple,
    uses the Django database API and User model to make it extremely simple.
    """

    session = command.session

    # Argument check.
    # Fail gracefully if no argument is provided
    if not command.command_argument:
        session.msg("No arguments provided.\n\r Usage (without <>): connect <email> <password>")
        return
    
    arg_list = command.command_argument.split()
    if not functions_general.cmd_check_num_args(session, arg_list, 2):
        session.msg("Not enough arguments provided.\n\r Usage (without <>): connect <email> <password>")
        return
    
    uemail = arg_list[0]
    password = arg_list[1]

    # Match an email address to an account.
    email_matches = Object.objects.get_user_from_email(uemail)
    
    # No username match
    if email_matches.count() == 0:
        session.msg("The email '%s' does not match any accounts.\n\rIf you are new you should create a new account." % uemail)
        return
    
    # We have at least one result, so we can check the password.
    user = email_matches[0]
        
    if not user.check_password(password):
        session.msg("Incorrect password.")
    else:
        uname = user.username
        session.login(user)
GLOBAL_UNCON_CMD_TABLE.add_command("connect", cmd_connect, auto_help_override=False)
        
def cmd_create(command):
    """
    Handle the creation of new accounts.
    """
    session = command.session
    
    # Argument check.
    # Fail gracefully if no argument is provided
    if not command.command_argument:
        session.msg("No arguments provided\n\r Usage (without <>): create \"<username>\" <email> <password>")
        return

    arg_list = command.command_argument.split()
    if not functions_general.cmd_check_num_args(session, arg_list, 2):
        session.msg("Too few arguments provided\n\r Usage (without <>): create \"<username>\" <email> <password>")
        return
    
    quote_split = command.command_argument.split("\"")
    
    if len(quote_split) < 2:
        session.msg("You must enclose your username in quotation marks.")
        return
    
    uname = quote_split[1]
    lastarg_split = quote_split[2].split()

    if len(lastarg_split) != 2:
        session.msg("You must specify an email address, followed by a password.")
        return
    
    email = lastarg_split[0].strip()
    password = lastarg_split[1].strip()

    #check so the email is at least on the form xxxx@xxx.xxx
    addr = email.split('@')
    if len(addr) != 2 or not len(addr[1].split('.')) > 1 or not addr[1].split('.')[-1]:
        session.msg("'%s' is not a valid e-mail address." % email)
        return

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
        session.msg("Sorry, there is already a player with that name.")
    elif not email_matches.count() == 0:
        session.msg("Sorry, there is already a player with that email address.")
    elif len(password) < 3:
        session.msg("Your password must be at least 3 characters or longer.\n\rFor best security, make it at least 8 characters long, avoid making it a real word and mix numbers into it.")
    else:
        try:
            Object.objects.create_user(command, uname, email, password)
        except:
            # we have to handle traceback ourself at this point, if we don't errors will givo no feedback.  
            session.msg("This is a bug. Please e-mail an admin if the problem persists.\n%s" % traceback.format_exc())
            log_errmsg(traceback.format_exc())
            raise
        
GLOBAL_UNCON_CMD_TABLE.add_command("create", cmd_create, auto_help_override=False)

def cmd_quit(command):
    """
    We're going to maintain a different version of the quit command
    here for unconnected users for the sake of simplicity. The logged in
    version will be a bit more complicated.
    """
    session = command.session
    session.msg("Good bye! Disconnecting ...")
    session.handle_close()
GLOBAL_UNCON_CMD_TABLE.add_command("quit", cmd_quit, auto_help_override=False)
