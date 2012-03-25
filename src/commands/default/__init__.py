"""
Groups all default commands for access from the API. 

To use via ev API, import this module with 
  from ev import default_cmds,
you can then access the command classes as members of default_cmds.

"""
from src.commands.default.cmdset_default import DefaultCmdSet
from src.commands.default.cmdset_ooc import OOCCmdSet
from src.commands.default.cmdset_unloggedin import UnloggedinCmdSet

from src.commands.default.muxcommand import MuxCommand

from src.commands.default.admin import *
from src.commands.default.batchprocess import *
from src.commands.default.building import *
from src.commands.default.comms import *
from src.commands.default.general import *
from src.commands.default.help import *
from src.commands.default import syscommands
from src.commands.default.system import *
from src.commands.default.unloggedin import *

del cmdset_default, cmdset_ooc, cmdset_unloggedin, muxcommand
del admin, batchprocess, building, comms, general, 
del help, system, unloggedin
