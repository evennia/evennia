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
from evennia.utils.evmenu import EvMenu
from evennia.utils.utils import is_iter

_MAX_NR_CHARACTERS = settings.MAX_NR_CHARACTERS

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
        in_progress = [chara for chara in account.characters if chara.db.chargen_step]

        if len(in_progress):
            # we're continuing chargen for a WIP character
            new_character = in_progress[0]
        else:
            # generate a randomized key so the player can choose a character name later
            key = "".join(choices(string.ascii_letters + string.digits, k=10))
            new_character, errors = account.create_character(
                key=key, location=None, ip=session.address
            )

            if errors:
                self.msg(errors)
            if not new_character:
                return
            # initalize the new character to the beginning of the chargen menu
            new_character.db.chargen_step = "menunode_welcome"
            # make sure the character first logs in at the settings-defined start location
            new_character.db.prelogout_location = ObjectDB.objects.get_id(settings.START_LOCATION)

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
    output to incorporate in-progress characters.
    """

    def at_look(self, target=None, session=None, **kwargs):
        """
        Called when this object executes a look. It allows to customize
        just what this means.

        Args:
            target (Object or list, optional): An object or a list
                objects to inspect. This is normally a list of characters.
            session (Session, optional): The session doing this look.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Returns:
            look_string (str): A prepared look string, ready to send
                off to any recipient (usually to ourselves)

        """

        if target and not is_iter(target):
            # single target - just show it
            if hasattr(target, "return_appearance"):
                return target.return_appearance(self)
            else:
                return f"{target} has no in-game appearance."

        # multiple targets - this is a list of characters
        characters = list(tar for tar in target if tar) if target else []
        ncars = len(characters)
        sessions = self.sessions.all()
        nsess = len(sessions)

        if not nsess:
            # no sessions, nothing to report
            return ""

        # header text
        txt_header = f"Account |g{self.name}|n (you are Out-of-Character)"

        # sessions
        sess_strings = []
        for isess, sess in enumerate(sessions):
            ip_addr = sess.address[0] if isinstance(sess.address, tuple) else sess.address
            addr = f"{sess.protocol_key} ({ip_addr})"
            sess_str = (
                f"|w* {isess + 1}|n"
                if session and session.sessid == sess.sessid
                else f"  {isess + 1}"
            )

            sess_strings.append(f"{sess_str} {addr}")

        txt_sessions = "|wConnected session(s):|n\n" + "\n".join(sess_strings)

        if not characters:
            txt_characters = "You don't have a character yet. Use |wcharcreate|n."
        else:
            max_chars = (
                "unlimited"
                if self.is_superuser or _MAX_NR_CHARACTERS is None
                else _MAX_NR_CHARACTERS
            )

            char_strings = []
            for char in characters:
                csessions = char.sessions.all()
                if csessions:
                    for sess in csessions:
                        # character is already puppeted
                        sid = sess in sessions and sessions.index(sess) + 1
                        if sess and sid:
                            char_strings.append(
                                f" - |G{char.name}|n [{', '.join(char.permissions.all())}] "
                                f"(played by you in session {sid})"
                            )
                        else:
                            char_strings.append(
                                f" - |R{char.name}|n [{', '.join(char.permissions.all())}] "
                                "(played by someone else)"
                            )
                elif char.db.chargen_step:
                    # currently in-progress character; don't display placeholder names
                    char_strings.append(" - |Yin progress|n (|wcharcreate|n to continue)")
                    continue
                else:
                    # character is "free to puppet"
                    char_strings.append(f" - {char.name} [{', '.join(char.permissions.all())}]")

            txt_characters = (
                f"Available character(s) ({ncars}/{max_chars}, |wic <name>|n to play):|n\n"
                + "\n".join(char_strings)
            )
        return self.ooc_appearance_template.format(
            header=txt_header,
            sessions=txt_sessions,
            characters=txt_characters,
            footer="",
        )
