"""
Commands that are available from the connect screen.
"""
import traceback
#from django.contrib.auth.models import User
from django.conf import settings 
from django.contrib.auth.models import User
from src.players.models import PlayerDB
from src.objects.models import ObjectDB
from src.config.models import ConfigValue 
from src.comms.models import Channel
from src.utils import create, logger, utils
from game.gamesrc.commands.default.muxcommand import MuxCommand 

class CmdConnect(MuxCommand):
    """
    Connect to the game.

    Usage (at login screen): 
      connect <email> <password>
      
    Use the create command to first create an account before logging in.
    """  
    key = "connect"
    aliases = ["conn", "con", "co"]

    def func(self):
        """
        Uses the Django admin api. Note that unlogged-in commands
        have a unique position in that their func() receives
        a session object instead of a source_object like all
        other types of logged-in commands (this is because
        there is no object yet before the player has logged in)
        """

        session = self.caller        
        arglist = self.arglist

        if not arglist or len(arglist) < 2:
            session.msg("\n\r Usage (without <>): connect <email> <password>")
            return
        email = arglist[0]
        password = arglist[1]
        
        # Match an email address to an account.
        player = PlayerDB.objects.get_player_from_email(email)
        # No playername match
        if not player:
            string = "The email '%s' does not match any accounts." % email
            string += "\n\r\n\rIf you are new you should first create a new account "
            string += "using the 'create' command."
            session.msg(string)
            return
        # We have at least one result, so we can check the password.
        if not player.user.check_password(password):
            session.msg("Incorrect password.")
            return 

        # We are logging in, get/setup the player object controlled by player

        character = player.character
        if not character:
            # Create a new character object to tie the player to. This should
            # usually not be needed unless the old character object was manually 
            # deleted.
            default_home_id = ConfigValue.objects.conf(db_key="default_home")            
            default_home = ObjectDB.objects.get_id(default_home_id)
            typeclass = settings.BASE_CHARACTER_TYPECLASS
            character = create.create_object(typeclass=typeclass,
                                             key=player.name,
                                             location=default_home, 
                                             home=default_home,
                                             player=player)            
            
            character.db.FIRST_LOGIN = "True"
            
        # Getting ready to log the player in.

        # Check if this is the first time the 
        # *player* connects
        if player.db.FIRST_LOGIN:
            player.at_first_login()
            del player.db.FIRST_LOGIN

        # check if this is the first time the *character*
        # character (needs not be the first time the player
        # does so, e.g. if the player has several characters)
        if character.db.FIRST_LOGIN:
            character.at_first_login()
            del character.db.FIRST_LOGIN
            
        # actually do the login, calling
        # customization hooks before and after. 
        player.at_pre_login()        
        character.at_pre_login()

        session.login(player)

        player.at_post_login()
        character.at_post_login()
        # run look
        #print "character:", character, character.scripts.all(), character.cmdset.current
        character.execute_cmd('look')

class CmdCreate(MuxCommand):
    """
    Create a new account.

    Usage (at login screen):
      create \"playername\" <email> <password>

    This creates a new player account.

    """
    key = "create"
    aliases = ["cre", "cr"]
                   
    def parse(self):
        """
        The parser must handle the multiple-word player
        name enclosed in quotes:
        connect "Long name with many words" my@myserv.com mypassw
        """
        super(CmdCreate, self).parse()

        self.playerinfo = []
        if len(self.arglist) < 3:
            return 
        if len(self.arglist) > 3:
            # this means we have a multi_word playername. pop from the back.
            password = self.arglist.pop()
            email = self.arglist.pop()
            # what remains is the playername.
            playername = " ".join(self.arglist) 
        else:
            playername, email, password = self.arglist
        
        playername = playername.replace('"', '') # remove "
        playername = playername.replace("'", "")
        self.playerinfo = (playername, email, password)

    def func(self):
        "Do checks and create account"

        session = self.caller

        try: 
            playername, email, password = self.playerinfo
        except ValueError:            
            string = "\n\r Usage (without <>): create \"<playername>\" <email> <password>"
            session.msg(string)
            return
        if not playername: 
            # entered an empty string
            session.msg("\n\r You have to supply a longer playername, surrounded by quotes.")
            return
        if not email or not password:
            session.msg("\n\r You have to supply an e-mail address followed by a password." ) 
            return 

        if not utils.validate_email_address(email):
            # check so the email at least looks ok.
            session.msg("'%s' is not a valid e-mail address." % email)
            return             

        # Run sanity and security checks 

        if PlayerDB.objects.get_player_from_name(playername) or User.objects.filter(username=playername):
            # player already exists
            session.msg("Sorry, there is already a player with the name '%s'." % playername)
        elif PlayerDB.objects.get_player_from_email(email):
            # email already set on a player
            session.msg("Sorry, there is already a player with that email address.")
        elif len(password) < 3:
            # too short password
            string = "Your password must be at least 3 characters or longer."
            string += "\n\rFor best security, make it at least 8 characters long, "
            string += "avoid making it a real word and mix numbers into it."
            session.msg(string)
        else:
            # everything's ok. Create the new player account
            try:
                default_home_id = ConfigValue.objects.conf(db_key="default_home")            
                default_home = ObjectDB.objects.get_id(default_home_id)                
                
                typeclass = settings.BASE_CHARACTER_TYPECLASS
                permissions = settings.PERMISSION_PLAYER_DEFAULT

                new_character = create.create_player(playername, email, password,
                                                     permissions=permissions,
                                                     location=default_home,
                                                     typeclass=typeclass,
                                                     home=default_home)                

                # set a default description
                new_character.db.desc = "This is a Player."

                new_character.db.FIRST_LOGIN = True                
                new_player = new_character.player
                new_player.db.FIRST_LOGIN = True 
                                
                # join the new player to the public channel                
                pchanneldef = settings.CHANNEL_PUBLIC
                if pchanneldef:
                    pchannel = Channel.objects.get_channel(pchanneldef[0])
                    if not pchannel.connect_to(new_player):
                        string = "New player '%s' could not connect to public channel!" % new_player.key
                        logger.log_errmsg(string)

                string = "A new account '%s' was created with the email address %s. Welcome!"
                string += "\n\nYou can now log with the command 'connect %s <your password>'."                
                session.msg(string % (playername, email, email))
            except Exception:
                # we have to handle traceback ourselves at this point, if 
                # we don't, errors will give no feedback.  
                string = "%s\nThis is a bug. Please e-mail an admin if the problem persists."
                session.msg(string % (traceback.format_exc()))
                logger.log_errmsg(traceback.format_exc())            

class CmdQuit(MuxCommand):
    """
    We maintain a different version of the quit command
    here for unconnected players for the sake of simplicity. The logged in
    version is a bit more complicated.
    """
    key = "quit"
    aliases = ["q", "qu"]

    def func(self):
        "Simply close the connection."
        session = self.caller
        session.msg("Good bye! Disconnecting ...")
        session.handle_close()

class CmdUnconnectedLook(MuxCommand):
    """
    This is an unconnected version of the look command for simplicity. 
    All it does is re-show the connect screen. 
    """
    key = "look"
    aliases = "l"
    
    def func(self):
        "Show the connect screen."
        try:
            self.caller.game_connect_screen()
        except Exception:
            self.caller.msg("Connect screen not found. Enter 'help' for aid.")

class CmdUnconnectedHelp(MuxCommand):
    """
    This is an unconnected version of the help command,
    for simplicity. It shows a pane or info. 
    """
    key = "help"
    aliases = ["h", "?"]

    def func(self):
        "Shows help"
        
        string = \
            """Welcome to Evennia! 

Commands available at this point:
  create - create a new account
  connect - login with an existing account
  look - re-show the connect screen
  help - this help
  quit - leave

To login to the system, you need to do one of the following:

1) If you have no previous account, you need to use the 'create'
   command followed by your desired character name (in quotes), your 
   e-mail address and finally a password of your choice. Like 
   this: 

   > create "Anna the Barbarian" anna@myemail.com tuK3221mP

   It's always a good idea (not only here, but everywhere on the net)
   to not use a regular word for your password. Make it longer than 
   3 characters (ideally 6 or more) and mix numbers and capitalization 
   into it. Now proceed to 2). 

2) If you have an account already, either because you just created 
   one in 1) above, or you are returning, use the 'connect' command 
   followed by the e-mail and password you previously set. 
   Example: 

   > connect anna@myemail.com tuK3221mP

   This should log you in. Run 'help' again once you're logged in 
   to get more aid. Hope you enjoy your stay! 

You can use the 'look' command if you want to see the connect screen again. 
"""
        self.caller.msg(string)
