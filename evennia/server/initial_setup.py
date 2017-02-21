"""
This module handles initial database propagation, which is only run the first
time the game starts. It will create some default channels, objects, and
other things.

Everything starts at handle_setup()
"""
from __future__ import print_function

import time
from django.conf import settings
from django.utils.translation import ugettext as _
from evennia.players.models import PlayerDB
from evennia.server.models import ServerConfig
from evennia.utils import create, logger


ERROR_NO_SUPERUSER = """
    No superuser exists yet. The superuser is the 'owner' account on
    the Evennia server. Create a new superuser using the command

       evennia createsuperuser

    Follow the prompts, then restart the server.
    """


LIMBO_DESC = _("""
Welcome to your new |wEvennia|n-based game! Visit http://www.evennia.com if you need
help, want to contribute, report issues or just join the community.
As Player #1 you can create a demo/tutorial area with |w@batchcommand tutorial_world.build|n.
    """)


WARNING_POSTGRESQL_FIX = """
    PostgreSQL-psycopg2 compatibility fix:
    The in-game channels {chan1}, {chan2} and {chan3} were created,
    but the superuser was not yet connected to them. Please use in
    game commands to connect Player #1 to those channels when first
    logging in.
    """


def get_god_player():
    """
    Creates the god user and don't take no for an answer.

    """
    try:
        god_player = PlayerDB.objects.get(id=1)
    except PlayerDB.DoesNotExist:
        raise PlayerDB.DoesNotExist(ERROR_NO_SUPERUSER)
    return god_player


def create_objects():
    """
    Creates the #1 player and Limbo room.

    """

    logger.log_info("Creating objects (Player #1 and Limbo room) ...")

    # Set the initial User's account object's username on the #1 object.
    # This object is pure django and only holds name, email and password.
    god_player = get_god_player()

    # Create a Player 'user profile' object to hold eventual
    # mud-specific settings for the PlayerDB object.
    player_typeclass = settings.BASE_PLAYER_TYPECLASS

    # run all creation hooks on god_player (we must do so manually
    # since the manage.py command does not)
    god_player.swap_typeclass(player_typeclass, clean_attributes=True)
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
                                         key=god_player.username,
                                         nohome=True)

    god_character.id = 1
    god_character.save()
    god_character.db.desc = _('This is User #1.')
    god_character.locks.add("examine:perm(Immortals);edit:false();delete:false();boot:false();msg:all();puppet:false()")
    god_character.permissions.add("Immortals")

    god_player.attributes.add("_first_login", True)
    god_player.attributes.add("_last_puppet", god_character)

    try:
        god_player.db._playable_characters.append(god_character)
    except AttributeError:
        god_player.db_playable_characters = [god_character]

    room_typeclass = settings.BASE_ROOM_TYPECLASS
    limbo_obj = create.create_object(room_typeclass, _('Limbo'), nohome=True)
    limbo_obj.id = 2
    limbo_obj.save()
    limbo_obj.db.desc = LIMBO_DESC.strip()
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
    logger.log_info("Creating default channels ...")

    goduser = get_god_player()
    for channeldict in settings.DEFAULT_CHANNELS:
        channel = create.create_channel(**channeldict)
        channel.connect(goduser)


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
    logger.log_info(" Running at_initial_setup() hook.")
    if mod.__dict__.get("at_initial_setup", None):
        mod.at_initial_setup()


def reset_server():
    """
    We end the initialization by resetting the server. This makes sure
    the first login is the same as all the following ones,
    particularly it cleans all caches for the special objects.  It
    also checks so the warm-reset mechanism works as it should.

    """
    ServerConfig.objects.conf("server_epoch", time.time())
    from evennia.server.sessionhandler import SESSIONS
    logger.log_info(" Initial setup complete. Restarting Server once.")
    SESSIONS.server.shutdown(mode='reset')


def handle_setup(last_step):
    """
    Main logic for the module. It allows for restarting the
    initialization at any point if one of the modules should crash.

    Args:
        last_step (int): The last stored successful step, for starting
            over on errors. If `< 0`, initialization has finished and no
            steps need to be redone.

    """

    if last_step < 0:
        # this means we don't need to handle setup since
        # it already ran sucessfully once.
        return
    # if None, set it to 0
    last_step = last_step or 0

    # setting up the list of functions to run
    setup_queue = [create_objects,
                   create_channels,
                   at_initial_setup,
                   reset_server]

    # step through queue, from last completed function
    for num, setup_func in enumerate(setup_queue[last_step:]):
        # run the setup function. Note that if there is a
        # traceback we let it stop the system so the config
        # step is not saved.

        try:
            setup_func()
        except Exception:
            if last_step + num == 1:
                from evennia.objects.models import ObjectDB
                for obj in ObjectDB.objects.all():
                    obj.delete()
            elif last_step + num == 2:
                from evennia.comms.models import ChannelDB
                ChannelDB.objects.all().delete()
            raise
        # save this step
        ServerConfig.objects.conf("last_initial_setup_step", last_step + num + 1)
    # We got through the entire list. Set last_step to -1 so we don't
    # have to run this again.
    ServerConfig.objects.conf("last_initial_setup_step", -1)
