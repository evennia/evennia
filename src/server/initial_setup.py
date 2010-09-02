"""
This module handles initial database propagation, which is only run the first
time the game starts. It will create some default channels, objects, and
other things.

Everything starts at handle_setup()
"""

from django.contrib.auth.models import User
from django.core import management
from django.conf import settings

from src.config.models import ConfigValue, ConnectScreen
from src.objects.models import ObjectDB
from src.comms.models import Channel, ChannelConnection
from src.players.models import PlayerDB
from src.help.models import HelpEntry
from src.scripts import scripts
from src.utils import create 
from src.utils import gametime

def create_config_values():
    """
    Creates the initial config values.
    """
    ConfigValue.objects.conf("default_home", "2")
    ConfigValue.objects.conf("site_name", settings.SERVERNAME)
    ConfigValue.objects.conf("idle_timeout", settings.IDLE_TIMEOUT)
    #ConfigValue.objects.conf("money_name_singular", "Credit")
    #ConfigValue.objects.conf("money_name_plural", "Credits")

def create_connect_screens():
    """
    Creates the default connect screen(s).
    """
    
    print " Creating startup screen(s) ..."

    text = "%ch%cb==================================================================%cn"
    text += "\r\n Welcome to %chEvennia%cn! Please type one of the following to begin:\r\n"
    text += "\r\n If you have an existing account, connect to it by typing:\r\n        "
    text += "%chconnect <email> <password>%cn\r\n If you need to create an account, "
    text += "type (without the <>'s):\r\n        "
    text += "%chcreate \"<username>\" <email> <password>%cn\r\n"
    text += "\r\n Enter %chhelp%cn for more info. %chlook%cn will re-show this screen.\r\n"
    text += "%ch%cb==================================================================%cn\r\n"
    ConnectScreen(db_key="Default", db_text=text, db_is_active=True).save()

def get_god_user():
    """
    Returns the initially created 'god' User object.
    """
    return User.objects.get(id=1)

def create_objects():
    """
    Creates the #1 player and Limbo room.
    """
    
    print " Creating objects (Player #1 and Limbo room) ..."

    # Set the initial User's account object's username on the #1 object.
    # This object is pure django and only holds name, email and password. 
    god_user = get_god_user()

    # Create a Player 'user profile' object to hold eventual
    # mud-specific settings for the bog standard User object. This is
    # accessed by user.get_profile() and can also store attributes.
    # It also holds mud permissions, but for a superuser these
    # have no effect anyhow. 

    character_typeclass = settings.BASE_CHARACTER_TYPECLASS

    # Create the Player object as well as the in-game god-character
    # for user #1. We can't set location and home yet since nothing
    # exists. Also, all properties (name, email, password, is_superuser)
    # is inherited from the user so we don't specify it again here. 

    god_character = create.create_player(god_user.username, None, None, 
                                         create_character=True,
                                         typeclass=character_typeclass,
                                         user=god_user)    
    god_character.id = 1
    god_character.db.desc = 'This is User #1.'
    god_character.save()
   
    # Limbo is the initial starting room.

    object_typeclass = settings.BASE_OBJECT_TYPECLASS
    limbo_obj = create.create_object(object_typeclass, 'Limbo')
    limbo_obj.id = 2
    string = "Welcome to your new %chEvennia%cn-based game."
    string += " From here you are ready to begin development."
    string += " If you should need help or would like to participate"
    string += " in community discussions, visit http://evennia.com."
    limbo_obj.db.desc = string
    limbo_obj.save()

    # Now that Limbo exists, set the user up in Limbo.
    god_character.location = limbo_obj
    god_character.home = limbo_obj
    
def create_channels():
    """
    Creates some sensible default channels.
    """
    print " Creating default channels ..."

    # public channel
    key, aliases, desc, perms = settings.CHANNEL_PUBLIC
    pchan = create.create_channel(key, aliases, desc, perms)
    # mudinfo channel 
    key, aliases, desc, perms = settings.CHANNEL_MUDINFO
    ichan = create.create_channel(key, aliases, desc, perms)
    # connectinfo channel
    key, aliases, desc, perms = settings.CHANNEL_CONNECTINFO
    cchan = create.create_channel(key, aliases, desc, perms)

    # connect the god user to all these channels by default.
    goduser = get_god_user()
    ChannelConnection.objects.create_connection(goduser, pchan)
    ChannelConnection.objects.create_connection(goduser, ichan)
    ChannelConnection.objects.create_connection(goduser, cchan)
         
def import_MUX_help_files():
    """
    Imports the MUX help files.
    """ 
    print " Importing MUX help database (devel reference only) ..."
    management.call_command('loaddata', '../src/help/mux_help_db.json', verbosity=0)    
    # categorize the MUX help files into its own category.
    default_category = "MUX"
    print " Moving imported help db to help category '%s'." \
                                                   % default_category
    HelpEntry.objects.all_to_category(default_category)

def create_permission_groups():
    """
    This sets up the default permissions groups
    by parsing a permission config file.

    Note that we don't catch any exceptions here,
    this must be debugged until it works. 
    """

    print " Creating and setting up permissions/groups ..."
    
    # We try to get the data from config first. 
    setup_path = settings.PERMISSION_SETUP_MODULE
    if not setup_path:
        # go with the default 
        setup_path = "src.permissions.default_permissions"            
    module = __import__(setup_path, fromlist=[True])
    # We have a successful import. Get the dicts. 
    groupdict = module.GROUPS
    
    # Create groups and populate them
    for group in groupdict:
        group = create.create_permission_group(group, desc=group,
                                               group_perms=groupdict[group])
        if not group:
            print " Creation of Group '%s' failed." % group 
    
def create_system_scripts():
    """
    Setup the system repeat scripts. They are automatically started
    by the create_script function. 
    """

    print " Creating and starting global scripts ..."
    
    # check so that all sessions are alive. 
    script1 = create.create_script(scripts.CheckSessions)
    # validate all scripts in script table.
    script2 = create.create_script(scripts.ValidateScripts)
    # update the channel handler to make sure it's in sync
    script3 = create.create_script(scripts.ValidateChannelHandler)
    if not script1 or not script2 or not script3:
        print " Error creating system scripts."
     
def start_game_time():
    """
    This starts a persistent script that keeps track of the
    in-game time (in whatever accelerated reference frame), but also
    the total run time of the server as well as its current uptime
    (the uptime can also be found directly from the server though).
    """
    print " Starting in-game time ..."

    gametime.init_gametime()
    
def handle_setup(last_step):
    """
    Main logic for the module. It allows to restart the initialization
    if one of the modules should crash. 
    """

    if last_step < 0:
        # this means we don't need to handle setup since
        # it already ran sucessfully once.         
        return
    elif last_step == None:
        # config doesn't exist yet. First start of server
        last_step = 0
        
    # setting up the list of functions to run    
    setup_queue = [
        create_config_values,    
        create_connect_screens,  
        create_objects,          
        create_channels,
        create_permission_groups, 
        create_system_scripts,
        import_MUX_help_files,
        start_game_time]

    if not settings.IMPORT_MUX_HELP:
        # skip importing of the MUX helpfiles, they are 
        # not interesting except for developers.
        del setup_queue[6]

    #print " Initial setup: %s steps." % (len(setup_queue)) 

    # step through queue, from last completed function
    for num, setup_func in enumerate(setup_queue[last_step:]):  
        # run the setup function. Note that if there is a
        # traceback we let it stop the system so the config
        # step is not saved.                
        #print "%s..." % num

        try:
            setup_func()
        except Exception:
            if last_step + num == 2:
                for obj in ObjectDB.objects.all():
                    obj.delete()
                for profile in PlayerDB.objects.all():
                    profile.delete()
            elif last_step + num == 3:
                for chan in Channel.objects.all():
                    chan.delete()
                for conn in ChannelConnection.objects.all():
                    conn.delete()
                

            raise 
        ConfigValue.objects.conf("last_initial_setup_step", last_step + num + 1) 
    # We got through the entire list. Set last_step to -1 so we don't
    # have to run this again.
    ConfigValue.objects.conf("last_initial_setup_step", -1) 
