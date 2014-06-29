"""
This module handles initial database propagation, which is only run the first
time the game starts. It will create some default channels, objects, and
other things.

Everything starts at handle_setup()
"""

import django
from django.conf import settings
from django.contrib.auth import get_user_model
from src.server.models import ServerConfig
from src.utils import create
from django.utils.translation import ugettext as _


def create_config_values():
    """
    Creates the initial config values.
    """
    ServerConfig.objects.conf("site_name", settings.SERVERNAME)
    ServerConfig.objects.conf("idle_timeout", settings.IDLE_TIMEOUT)


def get_god_player():
    """
    Creates the god user.
    """
    PlayerDB = get_user_model()
    try:
        god_player = PlayerDB.objects.get(id=1)
    except PlayerDB.DoesNotExist:
        txt = "\n\nNo superuser exists yet. The superuser is the 'owner'"
        txt += "\account on the Evennia server. Create a new superuser using"
        txt += "\nthe command"
        txt += "\n\n  python manage.py createsuperuser"
        txt += "\n\nFollow the prompts, then restart the server."
        raise Exception(txt)
    return god_player


def create_objects():
    """
    Creates the #1 player and Limbo room.
    """

    print " Creating objects (Player #1 and Limbo room) ..."

    # Set the initial User's account object's username on the #1 object.
    # This object is pure django and only holds name, email and password.
    god_player = get_god_player()

    # Create a Player 'user profile' object to hold eventual
    # mud-specific settings for the PlayerDB object.
    player_typeclass = settings.BASE_PLAYER_TYPECLASS

    # run all creation hooks on god_player (we must do so manually
    # since the manage.py command does not)
    god_player.typeclass_path = player_typeclass
    god_player.basetype_setup()
    god_player.at_player_creation()
    god_player.locks.add("examine:perm(Immortals);edit:false();delete:false();boot:false();msg:all()")
    # this is necessary for quelling to work correctly.
    god_player.permissions.add("Immortals")

    # Limbo is the default "nowhere" starting room

    # Create the in-game god-character for player #1 and set
    # it to exist in Limbo.
    character_typeclass = settings.BASE_CHARACTER_TYPECLASS
    god_character = create.create_object(character_typeclass,
                                           key=god_player.username, nohome=True)

    god_character.id = 1
    god_character.db.desc = _('This is User #1.')
    god_character.locks.add("examine:perm(Immortals);edit:false();delete:false();boot:false();msg:all();puppet:false()")
    god_character.permissions.add("Immortals")

    god_character.save()
    god_player.attributes.add("_first_login", True)
    god_player.attributes.add("_last_puppet", god_character)
    god_player.db._playable_characters.append(god_character)

    room_typeclass = settings.BASE_ROOM_TYPECLASS
    limbo_obj = create.create_object(room_typeclass, _('Limbo'), nohome=True)
    limbo_obj.id = 2
    string = " ".join([
        "Welcome to your new {wEvennia{n-based game. From here you are ready",
        "to begin development. Visit http://evennia.com if you should need",
        "help or would like to participate in community discussions. If you",
        "are logged in as User #1 you can create a demo/tutorial area with",
        "'@batchcommand contrib.tutorial_world.build'. Log out and create",
        "a new non-admin account at the login screen to play the tutorial",
        "properly."])
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
    print " Creating default channels ..."

    # public channel
    key1, aliases, desc, locks = settings.CHANNEL_PUBLIC
    pchan = create.create_channel(key1, aliases, desc, locks=locks)
    # mudinfo channel
    key2, aliases, desc, locks = settings.CHANNEL_MUDINFO
    ichan = create.create_channel(key2, aliases, desc, locks=locks)
    # connectinfo channel
    key3, aliases, desc, locks = settings.CHANNEL_CONNECTINFO
    cchan = create.create_channel(key3, aliases, desc, locks=locks)

    # TODO: postgresql-psycopg2 has a strange error when trying to
    # connect the user to the default channels. It works fine from inside
    # the game, but not from the initial startup. We are temporarily bypassing
    # the problem with the following fix. See Evennia Issue 151.
    if ((".".join(str(i) for i in django.VERSION) < "1.2"
                    and settings.DATABASE_ENGINE == "postgresql_psycopg2")
        or (hasattr(settings, 'DATABASES')
            and settings.DATABASES.get("default", {}).get('ENGINE', None)
            == 'django.db.backends.postgresql_psycopg2')):
        warning = """
        PostgreSQL-psycopg2 compatability fix:
        The in-game channels %s, %s and %s were created,
        but the superuser was not yet connected to them. Please use in
        game commands to onnect Player #1 to those channels when first
        logging in.
        """ % (key1, key2, key3)
        print warning
        return

    # connect the god user to all these channels by default.
    goduser = get_god_player()
    pchan.connect(goduser)
    ichan.connect(goduser)
    cchan.connect(goduser)


def create_system_scripts():
    """
    Setup the system repeat scripts. They are automatically started
    by the create_script function.
    """
    from src.scripts import scripts

    print " Creating and starting global scripts ..."

    # check so that all sessions are alive.
    script1 = create.create_script(scripts.CheckSessions)
    # validate all scripts in script table.
    script2 = create.create_script(scripts.ValidateScripts)
    # update the channel handler to make sure it's in sync
    script3 = create.create_script(scripts.ValidateChannelHandler)
    # flush the idmapper cache
    script4 = create.create_script(scripts.ValidateIdmapperCache)

    if not script1 or not script2 or not script3 or not script4:
        print " Error creating system scripts."


def start_game_time():
    """
    This starts a persistent script that keeps track of the
    in-game time (in whatever accelerated reference frame), but also
    the total run time of the server as well as its current uptime
    (the uptime can also be found directly from the server though).
    """
    print " Starting in-game time ..."
    from src.utils import gametime
    gametime.init_gametime()


def at_initial_setup():
    """
    Custom hook for users to overload some or all parts of the initial
    setup. Called very last in the sequence. It tries to import and
    srun a module settings.AT_INITIAL_SETUP_HOOK_MODULE and will fail
    silently if this does not exist or fails to load.
    """
    modname = settings.AT_INITIAL_SETUP_HOOK_MODULE
    if not modname:
        return
    try:
        mod = __import__(modname, fromlist=[None])
    except (ImportError, ValueError):
        return
    print " Running at_initial_setup() hook."
    if mod.__dict__.get("at_initial_setup", None):
        mod.at_initial_setup()


def reset_server():
    """
    We end the initialization by resetting the server. This
    makes sure the first login is the same as all the following
    ones, particularly it cleans all caches for the special objects.
    It also checks so the warm-reset mechanism works as it should.
    """
    from src.server.sessionhandler import SESSIONS
    print " Initial setup complete. Restarting Server once."
    SESSIONS.server.shutdown(mode='reset')


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
    elif last_step is None:
        # config doesn't exist yet. First start of server
        last_step = 0

    # setting up the list of functions to run
    setup_queue = [
        create_config_values,
        create_objects,
        create_channels,
        create_system_scripts,
        start_game_time,
        at_initial_setup,
        reset_server
        ]

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
                from src.comms.models import ChannelDB, PlayerChannelConnection
                ChannelDB.objects.all().delete()
                PlayerChannelConnection.objects.all().delete()
            raise
        ServerConfig.objects.conf("last_initial_setup_step", last_step + num + 1)
    # We got through the entire list. Set last_step to -1 so we don't
    # have to run this again.
    ServerConfig.objects.conf("last_initial_setup_step", -1)
