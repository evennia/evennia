import commands_unloggedin
import commands_general
import commands_privileged
import commands_comsys

# Unlogged-in Command Table
uncon_ctable = {
   "connect": commands_unloggedin.cmd_connect,
   "create":  commands_unloggedin.cmd_create,
   "quit":    commands_unloggedin.cmd_quit,
}

# Command Table
ctable = {
   "addcom":       commands_comsys.cmd_addcom,
   "comlist":      commands_comsys.cmd_comlist,
   "delcom":       commands_comsys.cmd_delcom,
   "drop":         commands_general.cmd_drop,
   "examine":      commands_general.cmd_examine,
   "get":          commands_general.cmd_get,
   "help":         commands_general.cmd_help,
   "idle":         commands_general.cmd_idle,
   "inventory":    commands_general.cmd_inventory,
   "look":         commands_general.cmd_look,
   "page":         commands_general.cmd_page,
   "pose":         commands_general.cmd_pose,
   "quit":         commands_general.cmd_quit,
   "say":          commands_general.cmd_say,
   "time":         commands_general.cmd_time,
   "uptime":       commands_general.cmd_uptime,
   "version":      commands_general.cmd_version,
   "who":          commands_general.cmd_who,
   "@ccreate":     commands_comsys.cmd_ccreate,
   "@cdestroy":    commands_comsys.cmd_cdestroy,
   "@cemit":       commands_comsys.cmd_cemit,
   "@clist":       commands_comsys.cmd_clist,
   "@create":      commands_privileged.cmd_create,
   "@description": commands_privileged.cmd_description,
   "@destroy":     commands_privileged.cmd_destroy,
   "@dig":         commands_privileged.cmd_dig,
   "@emit":        commands_privileged.cmd_emit,
   "@find":        commands_privileged.cmd_find,
   "@link":        commands_privileged.cmd_link,
   "@list":        commands_privileged.cmd_list,
   "@name":        commands_privileged.cmd_name,
   "@nextfree":    commands_privileged.cmd_nextfree,
   "@newpassword": commands_privileged.cmd_newpassword,
   "@open":        commands_privileged.cmd_open,
   "@password":    commands_privileged.cmd_password,
   "@reload":      commands_privileged.cmd_reload,
   "@set":         commands_privileged.cmd_set,
   "@shutdown":    commands_privileged.cmd_shutdown,
   "@teleport":    commands_privileged.cmd_teleport,
   "@unlink":      commands_privileged.cmd_unlink,
   "@wall":        commands_privileged.cmd_wall,
   
} 

def return_cfunc(func_name, unlogged_cmd=False):
   """
   Returns a reerence to the command's function. If there are no matches,
   returns false.
   """
   if not unlogged_cmd:
      return ctable.get(func_name, False)
   else:
      return uncon_ctable.get(func_name, False)