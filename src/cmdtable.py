"""
Command Table Entries
---------------------
Each command entry consists of a key and a tuple containing a reference to the
command's function, and a tuple of the permissions to match against. The user
only need have one of the permissions in the permissions tuple to gain
access to the command. Obviously, super users don't have to worry about this
stuff. If the command is open to all (or you want to implement your own
privilege checking in the command function), use None in place of the
permissions tuple.
"""
import commands.general
import commands.paging
import commands.privileged
import commands.comsys
import commands.unloggedin
import commands.info
import commands.objmanip
import logger

class CommandTable(object):
    """
    Stores command tables and performs lookups.
    """
    ctable = {}
    
    def add_command(self, command_string, function, priv_tuple=None):
        """
        Adds a command to the command table.
        
        command_string: (string) Command string (IE: WHO, QUIT, look).
        function: (reference) The command's function.
        priv_tuple: (tuple) String tuple of permissions required for command.
        """
        self.ctable[command_string] = (function, priv_tuple)
        
    def get_command_tuple(self, func_name):
        """
        Returns a reference to the command's tuple. If there are no matches,
        returns false.
        """
        return self.ctable.get(func_name, False)

"""
Global command table for logged in users.
"""
GLOBAL_CMD_TABLE = CommandTable()
GLOBAL_CMD_TABLE.add_command("addcom", commands.comsys.cmd_addcom),
GLOBAL_CMD_TABLE.add_command("comlist", commands.comsys.cmd_comlist),
GLOBAL_CMD_TABLE.add_command("delcom", commands.comsys.cmd_delcom),
GLOBAL_CMD_TABLE.add_command("drop", commands.general.cmd_drop),
GLOBAL_CMD_TABLE.add_command("examine", commands.general.cmd_examine),
GLOBAL_CMD_TABLE.add_command("get", commands.general.cmd_get),
GLOBAL_CMD_TABLE.add_command("help", commands.general.cmd_help),
GLOBAL_CMD_TABLE.add_command("idle", commands.general.cmd_idle),
GLOBAL_CMD_TABLE.add_command("inventory", commands.general.cmd_inventory),
GLOBAL_CMD_TABLE.add_command("look", commands.general.cmd_look),
GLOBAL_CMD_TABLE.add_command("page", commands.paging.cmd_page),
GLOBAL_CMD_TABLE.add_command("pose", commands.general.cmd_pose),
GLOBAL_CMD_TABLE.add_command("quit", commands.general.cmd_quit),
GLOBAL_CMD_TABLE.add_command("say", commands.general.cmd_say),
GLOBAL_CMD_TABLE.add_command("time", commands.info.cmd_time),
GLOBAL_CMD_TABLE.add_command("uptime", commands.info.cmd_uptime),
GLOBAL_CMD_TABLE.add_command("version", commands.info.cmd_version),
GLOBAL_CMD_TABLE.add_command("who", commands.general.cmd_who),
GLOBAL_CMD_TABLE.add_command("@alias", commands.objmanip.cmd_alias),
GLOBAL_CMD_TABLE.add_command("@boot", commands.privileged.cmd_boot,        
                             priv_tuple=("genperms.manage_players")),
GLOBAL_CMD_TABLE.add_command("@ccreate", commands.comsys.cmd_ccreate,
                             priv_tuple=("objects.add_commchannel")),
GLOBAL_CMD_TABLE.add_command("@cdestroy", commands.comsys.cmd_cdestroy,
                             priv_tuple=("objects.delete_commchannel")),
GLOBAL_CMD_TABLE.add_command("@cemit", commands.comsys.cmd_cemit),
GLOBAL_CMD_TABLE.add_command("@clist", commands.comsys.cmd_clist),
GLOBAL_CMD_TABLE.add_command("@create", commands.objmanip.cmd_create,
                             priv_tuple=("genperms.builder")),
GLOBAL_CMD_TABLE.add_command("@describe", commands.objmanip.cmd_description),
GLOBAL_CMD_TABLE.add_command("@destroy", commands.objmanip.cmd_destroy,
                             priv_tuple=("genperms.builder")),
GLOBAL_CMD_TABLE.add_command("@dig", commands.objmanip.cmd_dig,
                             priv_tuple=("genperms.builder")),
GLOBAL_CMD_TABLE.add_command("@emit", commands.general.cmd_emit,
                             priv_tuple=("genperms.announce")),
#GLOBAL_CMD_TABLE.add_command("@pemit", commands.general.cmd_pemit),
GLOBAL_CMD_TABLE.add_command("@find", commands.objmanip.cmd_find,
                             priv_tuple=("genperms.builder")),
GLOBAL_CMD_TABLE.add_command("@link", commands.objmanip.cmd_link,
                             priv_tuple=("genperms.builder")),
GLOBAL_CMD_TABLE.add_command("@list", commands.info.cmd_list,
                             priv_tuple=("genperms.process_control")),
GLOBAL_CMD_TABLE.add_command("@name", commands.objmanip.cmd_name),
GLOBAL_CMD_TABLE.add_command("@nextfree", commands.objmanip.cmd_nextfree,
                             priv_tuple=("genperms.builder")),
GLOBAL_CMD_TABLE.add_command("@newpassword", commands.privileged.cmd_newpassword, 
                             priv_tuple=("genperms.manage_players")),
GLOBAL_CMD_TABLE.add_command("@open", commands.objmanip.cmd_open,
                             priv_tuple=("genperms.builder")),
GLOBAL_CMD_TABLE.add_command("@password", commands.general.cmd_password),
GLOBAL_CMD_TABLE.add_command("@ps", commands.info.cmd_ps,
                             priv_tuple=("genperms.process_control")),
GLOBAL_CMD_TABLE.add_command("@reload", commands.privileged.cmd_reload,
                             priv_tuple=("genperms.process_control")),
GLOBAL_CMD_TABLE.add_command("@set", commands.objmanip.cmd_set),
GLOBAL_CMD_TABLE.add_command("@shutdown", commands.privileged.cmd_shutdown,
                             priv_tuple=("genperms.process_control")),
GLOBAL_CMD_TABLE.add_command("@stats", commands.info.cmd_stats),
GLOBAL_CMD_TABLE.add_command("@teleport", commands.objmanip.cmd_teleport,
                             priv_tuple=("genperms.builder")),
GLOBAL_CMD_TABLE.add_command("@unlink", commands.objmanip.cmd_unlink,
                             priv_tuple=("genperms.builder")),
GLOBAL_CMD_TABLE.add_command("@wall", commands.general.cmd_wall,
                             priv_tuple=("genperms.announce")),
GLOBAL_CMD_TABLE.add_command("@wipe", commands.objmanip.cmd_wipe),

"""
Global unconnected command table, for unauthenticated users.
"""
GLOBAL_UNCON_CMD_TABLE = CommandTable()
GLOBAL_UNCON_CMD_TABLE.add_command("connect", commands.unloggedin.cmd_connect)
GLOBAL_UNCON_CMD_TABLE.add_command("create", commands.unloggedin.cmd_create)
GLOBAL_UNCON_CMD_TABLE.add_command("quit", commands.unloggedin.cmd_quit)
