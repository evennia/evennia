"""
This module handles initial database propagation, which is only run the first time the game starts.
It will create some default objects (notably give #1 its evennia-specific properties, and create the
Limbo room). It will also hooks, and then perform an initial restart.

Everything starts at handle_setup()
"""


import time

from django.conf import settings
from django.utils.translation import gettext as _

from evennia.accounts.models import AccountDB
from evennia.server.models import ServerConfig
from evennia.utils import create, logger

ERROR_NO_SUPERUSER = """
    No superuser exists yet. The superuser is the 'owner' account on
    the Evennia server. Create a new superuser using the command

       evennia createsuperuser

    Follow the prompts, then restart the server.
    """


LIMBO_DESC = _(
    """
Welcome to your new |wEvennia|n-based game! Visit https://www.evennia.com if you need
help, want to contribute, report issues or just join the community.

As a privileged user, write |wbatchcommand tutorial_world.build|n to build
tutorial content. Once built, try |wintro|n for starting help and |wtutorial|n to
play the demo game.
"""
)


WARNING_POSTGRESQL_FIX = """
    PostgreSQL-psycopg2 compatibility fix:
    The in-game channels {chan1}, {chan2} and {chan3} were created,
    but the superuser was not yet connected to them. Please use in
    game commands to connect Account #1 to those channels when first
    logging in.
"""


def _get_superuser_account():
    """
    Get the superuser (created at the command line) and don't take no for an answer.

    Returns:
        Account: The first superuser (User #1).

    Raises:
        AccountDB.DoesNotExist: If the superuser couldn't be found.

    """
    try:
        superuser = AccountDB.objects.get(id=1)
    except AccountDB.DoesNotExist:
        raise AccountDB.DoesNotExist(ERROR_NO_SUPERUSER)
    return superuser


def create_objects():
    """
    Creates the #1 account and Limbo room.

    """

    logger.log_info("Initial setup: Creating objects (Account #1 and Limbo room) ...")

    # Set the initial User's account object's username on the #1 object.
    # This object is pure django and only holds name, email and password.
    superuser = _get_superuser_account()
    from evennia.objects.models import ObjectDB

    # Create an Account 'user profile' object to hold eventual
    # mud-specific settings for the AccountDB object.
    account_typeclass = settings.BASE_ACCOUNT_TYPECLASS

    # run all creation hooks on superuser (we must do so manually
    # since the manage.py command does not)
    superuser.swap_typeclass(account_typeclass, clean_attributes=True)
    superuser.basetype_setup()
    superuser.at_account_creation()
    superuser.locks.add(
        "examine:perm(Developer);edit:false();delete:false();boot:false();msg:all()"
    )
    # this is necessary for quelling to work correctly.
    superuser.permissions.add("Developer")

    # Limbo is the default "nowhere" starting room

    # Create the in-game god-character for account #1 and set
    # it to exist in Limbo.
    character_typeclass = settings.BASE_CHARACTER_TYPECLASS
    try:
        superuser_character = ObjectDB.objects.get(id=1)
    except ObjectDB.DoesNotExist:
        superuser_character = create.create_object(
            character_typeclass, key=superuser.username, nohome=True
        )

    superuser_character.db_typeclass_path = character_typeclass
    superuser_character.db.desc = _("This is User #1.")
    superuser_character.locks.add(
        "examine:perm(Developer);edit:false();delete:false();boot:false();msg:all();puppet:false()"
    )
    # we set this low so that quelling is more useful
    superuser_character.permissions.add("Developer")
    superuser_character.save()

    superuser.attributes.add("_first_login", True)
    superuser.attributes.add("_last_puppet", superuser_character)

    try:
        superuser.db._playable_characters.append(superuser_character)
    except AttributeError:
        superuser.db_playable_characters = [superuser_character]

    room_typeclass = settings.BASE_ROOM_TYPECLASS
    try:
        limbo_obj = ObjectDB.objects.get(id=2)
    except ObjectDB.DoesNotExist:
        limbo_obj = create.create_object(room_typeclass, _("Limbo"), nohome=True)

    limbo_obj.db_typeclass_path = room_typeclass
    limbo_obj.db.desc = LIMBO_DESC.strip()
    limbo_obj.save()

    # Now that Limbo exists, try to set the user up in Limbo (unless
    # the creation hooks already fixed this).
    if not superuser_character.location:
        superuser_character.location = limbo_obj
    if not superuser_character.home:
        superuser_character.home = limbo_obj


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
    logger.log_info("Initial setup: Running at_initial_setup() hook.")
    if mod.__dict__.get("at_initial_setup", None):
        mod.at_initial_setup()


def collectstatic():
    """
    Run collectstatic to make sure all web assets are loaded.

    """
    from django.core.management import call_command

    logger.log_info("Initial setup: Gathering static resources using 'collectstatic'")
    call_command("collectstatic", "--noinput")


def reset_server():
    """
    We end the initialization by resetting the server. This makes sure
    the first login is the same as all the following ones,
    particularly it cleans all caches for the special objects.  It
    also checks so the warm-reset mechanism works as it should.

    """
    ServerConfig.objects.conf("server_epoch", time.time())
    from evennia.server.sessionhandler import SESSIONS

    logger.log_info("Initial setup complete. Restarting Server once.")
    SESSIONS.portal_reset_server()


def handle_setup(last_step=None):
    """
    Main logic for the module. It allows for restarting the
    initialization at any point if one of the modules should crash.

    Args:
        last_step (str, None): The last stored successful step, for starting
            over on errors. None if starting from scratch. If this is 'done',
            the function will exit immediately.

    """
    if last_step in ("done", -1):
        # this means we don't need to handle setup since
        # it already ran sucessfully once. -1 is the legacy
        # value for existing databases.
        return

    # setup sequence
    setup_sequence = {
        "create_objects": create_objects,
        "at_initial_setup": at_initial_setup,
        "collectstatic": collectstatic,
        "done": reset_server,
    }

    # determine the sequence so we can skip ahead
    steps = list(setup_sequence)
    steps = steps[steps.index(last_step) + 1 if last_step is not None else 0 :]

    # step through queue from last completed function. Once completed,
    # the 'done' key should be set.
    for stepname in steps:
        try:
            setup_sequence[stepname]()
        except Exception:
            # we re-raise to make sure to stop startup
            raise
        else:
            # save the step
            ServerConfig.objects.conf("last_initial_setup_step", stepname)
            if stepname == "done":
                # always exit on 'done'
                break
