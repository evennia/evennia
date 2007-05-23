import commands_unloggedin
import commands_general
import commands_privileged
import commands_comsys

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

# Unlogged-in Command Table
uncon_ctable = {
   "connect": (commands_unloggedin.cmd_connect, None),
   "create":  (commands_unloggedin.cmd_create, None),
   "quit":    (commands_unloggedin.cmd_quit, None),
}


# Command Table
ctable = {
   "addcom":       (commands_comsys.cmd_addcom, None),
   "comlist":      (commands_comsys.cmd_comlist, None),
   "delcom":       (commands_comsys.cmd_delcom, None),
   "drop":         (commands_general.cmd_drop, None),
   "examine":      (commands_general.cmd_examine, None),
   "get":          (commands_general.cmd_get, None),
   "help":         (commands_general.cmd_help, None),
   "idle":         (commands_general.cmd_idle, None),
   "inventory":    (commands_general.cmd_inventory, None),
   "look":         (commands_general.cmd_look, None),
   "page":         (commands_general.cmd_page, None),
   "pose":         (commands_general.cmd_pose, None),
   "quit":         (commands_general.cmd_quit, None),
   "say":          (commands_general.cmd_say, None),
   "time":         (commands_general.cmd_time, None),
   "uptime":       (commands_general.cmd_uptime, None),
   "version":      (commands_general.cmd_version, None),
   "who":          (commands_general.cmd_who, None),
   "@ccreate":     (commands_comsys.cmd_ccreate, ("objects.add_commchannel")),
   "@cdestroy":    (commands_comsys.cmd_cdestroy, ("objects.delete_commchannel")),
   "@cemit":       (commands_comsys.cmd_cemit, None),
   "@clist":       (commands_comsys.cmd_clist, None),
   "@create":      (commands_privileged.cmd_create, ("genperms.builder")),
   "@description": (commands_privileged.cmd_description, None),
   "@destroy":     (commands_privileged.cmd_destroy, ("genperms.builder")),
   "@dig":         (commands_privileged.cmd_dig, ("genperms.builder")),
   "@emit":        (commands_privileged.cmd_emit, ("genperms.announce")),
   "@find":        (commands_privileged.cmd_find, ("genperms.builder")),
   "@link":        (commands_privileged.cmd_link, ("genperms.builder")),
   "@list":        (commands_privileged.cmd_list, ("genperms.process_control")),
   "@name":        (commands_privileged.cmd_name, None),
   "@nextfree":    (commands_privileged.cmd_nextfree, ("genperms.builder")),
   "@newpassword": (commands_privileged.cmd_newpassword, ("genperms.manage_players")),
   "@open":        (commands_privileged.cmd_open, ("genperms.builder")),
   "@password":    (commands_privileged.cmd_password, None),
   "@ps":          (commands_privileged.cmd_ps, ("genperms.process_control")),
   "@reload":      (commands_privileged.cmd_reload, ("genperms.process_control")),
   "@set":         (commands_privileged.cmd_set, None),
   "@shutdown":    (commands_privileged.cmd_shutdown, ("genperms.process_control")),
   "@teleport":    (commands_privileged.cmd_teleport, ("genperms.builder")),
   "@unlink":      (commands_privileged.cmd_unlink, ("genperms.builder")),
   "@wall":        (commands_privileged.cmd_wall, ("genperms.announce")),
} 

def return_cmdtuple(func_name, unlogged_cmd=False):
   """
   Returns a reference to the command's tuple. If there are no matches,
   returns false.
   """
   if not unlogged_cmd:
      cfunc = ctable.get(func_name, False)
   else:
      cfunc = uncon_ctable.get(func_name, False)
      
   return cfunc
