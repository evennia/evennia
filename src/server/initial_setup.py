"""
This module handles initial database propagation, which is only run the first
time the game starts. It will create some default channels, objects, and
other things.

Everything starts at handle_setup()
"""

from django.contrib.auth.models import User
from django.core import management
from django.conf import settings
from src.server.models import ServerConfig
from src.help.models import HelpEntry
from src.utils import create 

# i18n
from django.utils.translation import ugettext as _

def create_config_values():
    """
    Creates the initial config values.
    """    
    ServerConfig.objects.conf("site_name", settings.SERVERNAME)
    ServerConfig.objects.conf("idle_timeout", settings.IDLE_TIMEOUT)

def get_god_user():
    """
    Returns the initially created 'god' User object.
    """
    return User.objects.get(id=1)

def create_objects():
    """
    Creates the #1 player and Limbo room.
    """
    
    print _(" Creating objects (Player #1 and Limbo room) ...")

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
                                         user=god_user,   
                                         create_character=True,
                                         character_typeclass=character_typeclass)

    if not god_character:
        raise Exception(_("#1 could not be created. Check the Player/Character typeclass for bugs."))

    god_character.id = 1
    god_character.db.desc = _('This is User #1.')
    god_character.locks.add("examine:perm(Immortals);edit:false();delete:false();boot:false();msg:all();puppet:false()")

    god_character.save()
   
    # Limbo is the default "nowhere" starting room

    room_typeclass = settings.BASE_ROOM_TYPECLASS
    limbo_obj = create.create_object(room_typeclass, _('Limbo'))
    limbo_obj.id = 2
    string = " Welcome to your new {wEvennia{n-based game."
    string += " From here you are ready to begin development."
    string += " If you should need help or would like to participate"
    string += " in community discussions, visit http://evennia.com."
    string += " If you are logged in as User #1 you can create a"
    string += " demo/tutorial area with '@batchcommand contrib.tutorial_world.build'."
    string = _(string)
    limbo_obj.db.desc = string
    limbo_obj.save()

    # Now that Limbo exists, try to set the user up in Limbo (unless
    # the creation hooks already fixed this).
    if not god_character.location:        
        god_character.location = limbo_obj
    if not god_character.home:
        god_character.home = limbo_obj
    
def create_channels():
    """
    Creates some sensible default channels.
    """
    print _(" Creating default channels ...")

    # public channel
    key, aliases, desc, locks = settings.CHANNEL_PUBLIC
    pchan = create.create_channel(key, aliases, desc, locks=locks)
    # mudinfo channel 
    key, aliases, desc, locks = settings.CHANNEL_MUDINFO
    ichan = create.create_channel(key, aliases, desc, locks=locks)
    # connectinfo channel
    key, aliases, desc, locks = settings.CHANNEL_CONNECTINFO
    cchan = create.create_channel(key, aliases, desc, locks=locks)

    # connect the god user to all these channels by default.
    goduser = get_god_user()
    from src.comms.models import PlayerChannelConnection
    PlayerChannelConnection.objects.create_connection(goduser, pchan)
    PlayerChannelConnection.objects.create_connection(goduser, ichan)
    PlayerChannelConnection.objects.create_connection(goduser, cchan)
         
def import_MUX_help_files():
    """
    Imports the MUX help files.
    """ 
    print _(" Importing MUX help database (devel reference only) ...")
    management.call_command('loaddata', '../src/help/mux_help_db.json', verbosity=0)    
    # categorize the MUX help files into its own category.
    default_category = "MUX"
    print _(" Moving imported help db to help category '%(default)s'." \
                                                   % {'default': default_category})
    HelpEntry.objects.all_to_category(default_category)
    
def create_system_scripts():
    """
    Setup the system repeat scripts. They are automatically started
    by the create_script function. 
    """
    from src.scripts import scripts

    print _(" Creating and starting global scripts ...")

    # check so that all sessions are alive. 
    script1 = create.create_script(scripts.CheckSessions)
    # validate all scripts in script table.
    script2 = create.create_script(scripts.ValidateScripts)
    # update the channel handler to make sure it's in sync
    script3 = create.create_script(scripts.ValidateChannelHandler)
    if not script1 or not script2 or not script3:
        print _(" Error creating system scripts.")
     
def start_game_time():
    """
    This starts a persistent script that keeps track of the
    in-game time (in whatever accelerated reference frame), but also
    the total run time of the server as well as its current uptime
    (the uptime can also be found directly from the server though).
    """
    print _(" Starting in-game time ...")
    from src.utils import gametime
    gametime.init_gametime()

def create_admin_media_links():
    """
    This traverses to src/web/media and tries to create a symbolic
    link to the django media files from within the MEDIA_ROOT. 
    These are files we normally don't
    want to mess with (use templates to customize the admin
    look). Linking is needed since the Twisted webserver otherwise has no
    notion of where the default files are - and we cannot hard-code it
    since the django install may be at different locations depending
    on system.
    """
    import django, os
    dpath = os.path.join(django.__path__[0], 'contrib', 'admin', 'media')
    apath = os.path.join(settings.ADMIN_MEDIA_ROOT)
    if os.path.isdir(apath):
        print _(" ADMIN_MEDIA_ROOT already exists. Ignored.")
        return 
    if os.name == 'nt':        
        print _(" Admin-media files copied to ADMIN_MEDIA_ROOT (Windows mode).")
        os.mkdir(apath)
        os.system('xcopy "%s" "%s" /e /q /c' % (dpath, apath))
    if os.name == 'posix':
        os.symlink(dpath, apath)
        print _(" Admin-media symlinked to ADMIN_MEDIA_ROOT.")
    else:
        print _(" Admin-media files should be copied manually to ADMIN_MEDIA_ROOT.")

def at_initial_setup():
    """
    Custom hook for users to overload some or all parts of the initial
    setup. Called very last in the sequence. It tries to import and
    run a module settings.AT_INITIAL_SETUP_HOOK_MODULE and will fail
    silently if this does not exist or fails to load.
    """
    try:
        mod = __import__(settings.AT_INITIAL_SETUP_HOOK_MODULE, fromlist=[None])
    except ImportError:
        return 
    print _(" Running at_initial_setup() hook.")
    if mod.__dict__.get("at_initial_setup", None):
        mod.at_initial_setup()                   
        
def handle_setup(last_step):
    """
    Main logic for the module. It allows for restarting
    the initialization at any point if one of the modules 
    should crash. 
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
        create_objects,          
        create_channels,
        create_system_scripts,
        start_game_time,
        create_admin_media_links,
        import_MUX_help_files,
        at_initial_setup]

    if not settings.IMPORT_MUX_HELP:
        # skip importing of the MUX helpfiles, they are 
        # not interesting except for developers.
        del setup_queue[-2]

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
                from src.players.models import PlayerDB
                from src.objects.models import ObjectDB

                for obj in ObjectDB.objects.all():
                    obj.delete()
                for profile in PlayerDB.objects.all():
                    profile.delete()
            elif last_step + num == 3:
                from src.comms.models import Channel, PlayerChannelConnection

                for chan in Channel.objects.all():
                    chan.delete()
                for conn in PlayerChannelConnection.objects.all():
                    conn.delete()
                

            raise 
        ServerConfig.objects.conf("last_initial_setup_step", last_step + num + 1) 
    # We got through the entire list. Set last_step to -1 so we don't
    # have to run this again.
    ServerConfig.objects.conf("last_initial_setup_step", -1) 
