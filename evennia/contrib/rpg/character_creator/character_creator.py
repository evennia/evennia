"""
Character Creator contrib, by InspectorCaracal

# Features

The primary feature of this contrib is defining the name and attributes
of a new character through an EvMenu. It provides an alternate `charcreate`
command as well as a modified `at_look` method for your Account class.

# Usage

In order to use the contrib, you will need to create your own chargen
EvMenu. The included `example_menu.py` gives a number of useful techniques
and examples, including how to allow players to choose and confirm
character names from within the menu.

"""
import string
from random import choices

from django.conf import settings

from evennia import DefaultAccount
from evennia.commands.default.muxcommand import MuxAccountCommand
from evennia.objects.models import ObjectDB
from evennia.utils import create, search
from evennia.utils.evmenu import EvMenu

_CHARACTER_TYPECLASS = settings.BASE_CHARACTER_TYPECLASS
try:
    _CHARGEN_MENU = settings.CHARGEN_MENU
except AttributeError:
    _CHARGEN_MENU = "evennia.contrib.rpg.character_creator.example_menu"


class ContribCmdCharCreate(MuxAccountCommand):
    """
    create a new character

    Begin creating a new character, or resume character creation for
    an existing in-progress character.

    You can stop character creation at any time and resume where
    you left off later.
    """

    key = "charcreate"
    locks = "cmd:pperm(Player) and is_ooc()"
    help_category = "General"

    def func(self):
        "create the new character"
        account = self.account
        session = self.session

        # only one character should be in progress at a time, so we check for WIPs first
        in_progress = [chara for chara in account.db._playable_characters if chara.db.chargen_step]

        if len(in_progress):
            # we're continuing chargen for a WIP character
            new_character = in_progress[0]
        else:
            # we're making a new character
            charmax = settings.MAX_NR_CHARACTERS

            if not account.is_superuser and (
                account.db._playable_characters and len(account.db._playable_characters) >= charmax
            ):
                plural = "" if charmax == 1 else "s"
                self.msg(f"You may only create a maximum of {charmax} character{plural}.")
                return

            # create the new character object, with default settings
            # start_location = ObjectDB.objects.get_id(settings.START_LOCATION)
            default_home = ObjectDB.objects.get_id(settings.DEFAULT_HOME)
            permissions = settings.PERMISSION_ACCOUNT_DEFAULT
            # generate a randomized key so the player can choose a character name later
            key = "".join(choices(string.ascii_letters + string.digits, k=10))
            new_character = create.create_object(
                _CHARACTER_TYPECLASS,
                key=key,
                location=None,
                home=default_home,
                permissions=permissions,
            )
            # only allow creator (and developers) to puppet this char
            new_character.locks.add(
                f"puppet:pid({account.id}) or perm(Developer) or"
                f" pperm(Developer);delete:id({account.id}) or perm(Admin)"
            )
            # initalize the new character to the beginning of the chargen menu
            new_character.db.chargen_step = "menunode_welcome"
            account.db._playable_characters.append(new_character)

        # set the menu node to start at to the character's last saved step
        startnode = new_character.db.chargen_step
        # attach the character to the session, so the chargen menu can access it
        session.new_char = new_character

        # this gets called every time the player exits the chargen menu
        def finish_char_callback(session, menu):
            char = session.new_char
            if not char.db.chargen_step:
                # this means character creation was completed - start playing!
                # execute the ic command to start puppeting the character
                account.execute_cmd("ic {}".format(char.key))

        EvMenu(session, _CHARGEN_MENU, startnode=startnode, cmd_on_exit=finish_char_callback)


class ContribChargenAccount(DefaultAccount):
    """
    A modified Account class that makes minor changes to the OOC look
    output, to incorporate in-progress characters.
    """

    def at_look(self, target=None, session=None, **kwargs):
        """
        Called by the OOC look command. It displays a list of playable
        characters and should be mostly identical to the core method.

        Args:
            target (Object or list, optional): An object or a list
                objects to inspect.
            session (Session, optional): The session doing this look.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Returns:
            look_string (str): A prepared look string, ready to send
                off to any recipient (usually to ourselves)
        """

        # list of targets - make list to disconnect from db
        characters = list(tar for tar in target if tar) if target else []
        sessions = self.sessions.all()
        is_su = self.is_superuser

        # text shown when looking in the ooc area
        result = [f"Account |g{self.key}|n (you are Out-of-Character)"]

        nsess = len(sessions)
        if nsess == 1:
            result.append("\n\n|wConnected session:|n")
        elif nsess > 1:
            result.append(f"\n\n|wConnected sessions ({nsess}):|n")
        for isess, sess in enumerate(sessions):
            csessid = sess.sessid
            addr = "{protocol} ({address})".format(
                protocol=sess.protocol_key,
                address=isinstance(sess.address, tuple)
                and str(sess.address[0])
                or str(sess.address),
            )
            if session.sessid == csessid:
                result.append(f"\n |w* {isess+1}|n {addr}")
            else:
                result.append(f"\n   {isess+1} {addr}")

        result.append("\n\n |whelp|n - more commands")
        result.append("\n |wpublic <Text>|n - talk on public channel")

        charmax = settings.MAX_NR_CHARACTERS

        if is_su or len(characters) < charmax:
            result.append("\n |wcharcreate|n - create a new character")

        if characters:
            result.append("\n |wchardelete <name>|n - delete a character (cannot be undone!)")
        plural = "" if len(characters) == 1 else "s"
        result.append("\n |wic <character>|n - enter the game (|wooc|n to return here)")
        if is_su:
            result.append(f"\n\nAvailable character{plural} ({len(characters)}/unlimited):")
        else:
            result.append(f"\n\nAvailable character{plural} ({len(characters)}/{charmax}):")

        for char in characters:
            if char.db.chargen_step:
                # currently in-progress character; don't display placeholder names
                result.append("\n - |Yin progress|n (|wcharcreate|n to continue)")
                continue
            csessions = char.sessions.all()
            if csessions:
                for sess in csessions:
                    # character is already puppeted
                    sid = sess in sessions and sessions.index(sess) + 1
                    if sess and sid:
                        result.append(
                            f"\n - |G{char.key}|n [{', '.join(char.permissions.all())}] (played by"
                            f" you in session {sid})"
                        )
                    else:
                        result.append(
                            f"\n - |R{char.key}|n [{', '.join(char.permissions.all())}] (played by"
                            " someone else)"
                        )
            else:
                # character is available
                result.append(f"\n - {char.key} [{', '.join(char.permissions.all())}]")
        look_string = ("-" * 68) + "\n" + "".join(result) + "\n" + ("-" * 68)
        return look_string
