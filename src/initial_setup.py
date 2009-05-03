"""
This module handles initial database propagation, which is only ran the first
time the game starts. It will create some default channels, objects, and
other things.

Everything starts at handle_setup()
"""
from django.contrib.auth.models import User, Group
from django.core import management
from django.conf import settings
from src.objects.models import Object
from src.config.models import ConfigValue, CommandAlias, ConnectScreen
from src import comsys, defines_global

def get_god_user():
    """
    Returns the initially created 'god' User object.
    """
    return User.objects.get(id=1)

def get_god_obj():
    """
    Returns the initially created 'god' user's PLAYER object.
    """
    return Object.objects.get(id=1)

def create_objects():
    """
    Creates the #1 player and Limbo room.
    """
    # Set the initial User's account object's username on the #1 object.
    god_user = get_god_user()
    # Create the matching PLAYER object in the object DB.
    god_user_obj = Object(id=1, type=defines_global.OTYPE_PLAYER)
    god_user_obj.set_name(god_user.username)
    god_user_obj.set_attribute('desc', 'You are Player #1.')
    god_user_obj.scriptlink.at_player_creation()
    god_user_obj.save()
    
    # Limbo is the initial starting room.
    limbo_obj = Object(id=2, type=defines_global.OTYPE_ROOM)
    limbo_obj.set_owner(god_user_obj)
    limbo_obj.set_name('%ch%ccLimbo%cn')
    limbo_obj.set_attribute('desc',"Welcome to your new Evennia-based game. From here you are ready to begin development. If you should need help or would like to participate in community discussions, visit http://evennia.com.")
    limbo_obj.scriptlink.at_object_creation()
    limbo_obj.save()

    # Now that Limbo exists, set the user up in Limbo.
    god_user_obj.location = limbo_obj
    god_user_obj.set_home(limbo_obj)
    
def create_groups():
    """
    Creates the default permissions groups.
    """
    groups = ("Immortals", "Wizards", "Builders", "Player Helpers")
    for group in groups:
        newgroup = Group()
        newgroup.name = group
        newgroup.save()
        
def create_channels():
    """
    Creates some sensible default channels.
    """
    god_user_obj = get_god_obj()
    chan_pub = comsys.create_channel("Public", god_user_obj, 
                                     description="Public Discussion")
    chan_pub.is_joined_by_default = True
    chan_pub.save()
    comsys.create_channel(settings.COMMCHAN_MUD_INFO, god_user_obj, 
                          description="Informative messages")
    comsys.create_channel(settings.COMMCHAN_MUD_CONNECTIONS, god_user_obj, 
                          description="Connection log")
    
def create_config_values():
    """
    Creates the initial config values.
    """
    ConfigValue(conf_key="default_home", conf_value="2").save()
    ConfigValue(conf_key="idle_timeout", conf_value="3600").save()
    ConfigValue(conf_key="money_name_singular", conf_value="Credit").save()
    ConfigValue(conf_key="money_name_plural", conf_value="Credits").save()
    ConfigValue(conf_key="player_dbnum_start", conf_value="2").save()
    ConfigValue(conf_key="site_name", conf_value="Evennia Test Site").save()
    # We don't want to do initial setup tasks every startup, only the first.
    ConfigValue(conf_key="game_firstrun", conf_value="0").save()
    
def create_connect_screens():
    """
    Creates the default connect screen(s).
    """
    ConnectScreen(name="Default",
                  text="%ch%cb==================================================================%cn\r\n Welcome to Evennia! Please type one of the following to begin:\r\n\r\n If you have an existing account, connect to it by typing:\r\n        %chconnect <email> <password>%cn\r\n If you need to create an account, type (without the <>'s):\r\n        %chcreate \"<username>\" <email> <password>%cn\r\n%ch%cb==================================================================%cn\r\n",
                  is_active=True).save()
                  
def create_aliases():
    """
    Populates the standard aliases.
    """
    CommandAlias(user_input="@desc", equiv_command="@describe").save()
    CommandAlias(user_input="@dest", equiv_command="@destroy").save()
    CommandAlias(user_input="@nuke", equiv_command="@destroy").save()
    CommandAlias(user_input="@tel", equiv_command="@teleport").save()
    CommandAlias(user_input="i", equiv_command="inventory").save()
    CommandAlias(user_input="inv", equiv_command="inventory").save()
    CommandAlias(user_input="l", equiv_command="look").save()
    CommandAlias(user_input="ex", equiv_command="examine").save()
    CommandAlias(user_input="sa", equiv_command="say").save()
    CommandAlias(user_input="emote", equiv_command="pose").save()
    CommandAlias(user_input="p", equiv_command="page").save()
    
def import_help_files():
    """
    Imports the help files.
    """
    management.call_command('loaddata', 'docs/help_files.json', verbosity=0)

def handle_setup():
    """
    Main logic for the module.
    """
    create_config_values()
    create_aliases()
    create_connect_screens()
    create_objects()
    create_groups()
    create_channels()
    import_help_files()
