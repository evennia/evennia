"""
Roleplaying emotes and language - Griatch, 2015

"""

from .rpsystem import EmoteError, SdescError, RecogError, LanguageError  # noqa
from .rpsystem import ordered_permutation_regex, regex_tuple_from_key_alias  # noqa
from .rpsystem import parse_language, parse_sdescs_and_recogs, send_emote  # noqa
from .rpsystem import SdescHandler, RecogHandler  # noqa
from .rpsystem import RPCommand, CmdEmote, CmdSay, CmdSdesc, CmdPose, CmdRecog, CmdMask  # noqa
from .rpsystem import RPSystemCmdSet  # noqa
from .rpsystem import ContribRPObject  # noqa
from .rpsystem import ContribRPRoom  # noqa
from .rpsystem import ContribRPCharacter  # noqa

from .rplanguage import LanguageError, LanguageExistsError  # noqa
from .rplanguage import LanguageHandler  # noqa
from .rplanguage import obfuscate_language, obfuscate_whisper  # noqa
from .rplanguage import add_language, available_languages  # noqa
