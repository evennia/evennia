"""
Gendersub

Griatch 2015

This is a simple gender-aware Character class for allowing users to
insert custom markers in their text to indicate gender-aware
messaging. It relies on a modified msg() and is meant as an
inspiration and starting point to how to do stuff like this.

An object can have the following genders:
 - male (he/his)
 - female (her/hers)
 - neutral (it/its)
 - ambiguous (they/them/their/theirs)

Usage

When in use, messages can contain special tags to indicate pronouns gendered
based on the one being addressed. Capitalization will be retained.

- `|s`, `|S`: Subjective form: he, she, it, He, She, It, They
- `|o`, `|O`: Objective form: him, her, it, Him, Her, It, Them
- `|p`, `|P`: Possessive form: his, her, its, His, Her, Its, Their
- `|a`, `|A`: Absolute Possessive form: his, hers, its, His, Hers, Its, Theirs

For example,

```
char.msg("%s falls on |p face with a thud." % char.key)
"Tom falls on his face with a thud"
```

The default gender is "ambiguous" (they/them/their/theirs).

To use, have DefaultCharacter inherit from this, or change
setting.DEFAULT_CHARACTER to point to this class.

The `gender` command is used to set the gender. It needs to be added to the
default cmdset before it becomes available.

"""

import re

from evennia import Command, DefaultCharacter
from evennia.utils import logger

# gender maps

_GENDER_PRONOUN_MAP = {
    "male": {"s": "he", "o": "him", "p": "his", "a": "his"},
    "female": {"s": "she", "o": "her", "p": "her", "a": "hers"},
    "neutral": {"s": "it", "o": "it", "p": "its", "a": "its"},
    "ambiguous": {"s": "they", "o": "them", "p": "their", "a": "theirs"},
}
_RE_GENDER_PRONOUN = re.compile(r"(?<!\|)\|(?!\|)[sSoOpPaA]")

# in-game command for setting the gender


class SetGender(Command):
    """
    Sets gender on yourself

    Usage:
      @gender male||female||neutral||ambiguous

    """

    key = "gender"
    aliases = "sex"
    locks = "call:all()"

    def func(self):
        """
        Implements the command.
        """
        caller = self.caller
        arg = self.args.strip().lower()
        if arg not in ("male", "female", "neutral", "ambiguous"):
            caller.msg("Usage: @gender male||female||neutral||ambiguous")
            return
        caller.db.gender = arg
        caller.msg("Your gender was set to %s." % arg)


# Gender-aware character class


class GenderCharacter(DefaultCharacter):
    """
    This is a Character class aware of gender.

    """

    def at_object_creation(self):
        """
        Called once when the object is created.
        """
        super().at_object_creation()
        self.db.gender = "ambiguous"

    def _get_pronoun(self, regex_match):
        """
        Get pronoun from the pronoun marker in the text. This is used as
        the callable for the re.sub function.

        Args:
            regex_match (MatchObject): the regular expression match.

        Notes:
            - `|s`, `|S`: Subjective form: he, she, it, He, She, It, They
            - `|o`, `|O`: Objective form: him, her, it, Him, Her, It, Them
            - `|p`, `|P`: Possessive form: his, her, its, His, Her, Its, Their
            - `|a`, `|A`: Absolute Possessive form: his, hers, its, His, Hers, Its, Theirs

        """
        typ = regex_match.group()[1]  # "s", "O" etc
        gender = self.attributes.get("gender", default="ambiguous")
        gender = gender if gender in ("male", "female", "neutral") else "ambiguous"
        pronoun = _GENDER_PRONOUN_MAP[gender][typ.lower()]
        return pronoun.capitalize() if typ.isupper() else pronoun

    def msg(self, text=None, from_obj=None, session=None, **kwargs):
        """
        Emits something to a session attached to the object.
        Overloads the default msg() implementation to include
        gender-aware markers in output.

        Args:
            text (str or tuple, optional): The message to send. This
                is treated internally like any send-command, so its
                value can be a tuple if sending multiple arguments to
                the `text` oob command.
            from_obj (obj, optional): object that is sending. If
                given, at_msg_send will be called
            session (Session or list, optional): session or list of
                sessions to relay to, if any. If set, will
                force send regardless of MULTISESSION_MODE.
        Notes:
            `at_msg_receive` will be called on this Object.
            All extra kwargs will be passed on to the protocol.

        """
        if text is None:
            super().msg(from_obj=from_obj, session=session, **kwargs)
            return

        try:
            if text and isinstance(text, tuple):
                text = (_RE_GENDER_PRONOUN.sub(self._get_pronoun, text[0]), *text[1:])
            else:
                text = _RE_GENDER_PRONOUN.sub(self._get_pronoun, text)
        except TypeError:
            pass
        except Exception as e:
            logger.log_trace(e)
        super().msg(text, from_obj=from_obj, session=session, **kwargs)
