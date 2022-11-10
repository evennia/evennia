"""
Roleplaying emotes and language - Griatch, 2015

"""

from .rplanguage import LanguageExistsError  # noqa
from .rplanguage import LanguageHandler  # noqa
from .rplanguage import (
    LanguageError,
    add_language,
    available_languages,
    obfuscate_language,
    obfuscate_whisper,
)
from .rpsystem import CmdSay  # noqa
from .rpsystem import ContribRPCharacter  # noqa
from .rpsystem import ContribRPObject  # noqa
from .rpsystem import ContribRPRoom  # noqa
from .rpsystem import RPSystemCmdSet  # noqa
from .rpsystem import (
    CmdEmote,
    CmdMask,
    CmdPose,
    CmdRecog,
    CmdSdesc,
    EmoteError,
    LanguageError,
    RecogError,
    RecogHandler,
    RPCommand,
    SdescError,
    SdescHandler,
    parse_language,
    parse_sdescs_and_recogs,
    send_emote,
)
