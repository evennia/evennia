import commands.general
import commands.privileged
import commands.comsys
import commands.unloggedin
import commands.info
import commands.objmanip

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

# -- Unlogged-in Command Table --
# Command Name        Command Function                      Privilege Tuple
uncon_ctable = {
     "connect":        (commands.unloggedin.cmd_connect,    None),
     "create":         (commands.unloggedin.cmd_create,     None),
     "quit":           (commands.unloggedin.cmd_quit,       None),
}


# -- Command Table --
# Command Name        Command Function                      Privilege Tuple
ctable = {
     "addcom":        (commands.comsys.cmd_addcom,          None),
     "comlist":       (commands.comsys.cmd_comlist,         None),
     "delcom":        (commands.comsys.cmd_delcom,          None),
     "drop":          (commands.general.cmd_drop,           None),
     "examine":       (commands.general.cmd_examine,        None),
     "get":           (commands.general.cmd_get,            None),
     "help":          (commands.general.cmd_help,           None),
     "idle":          (commands.general.cmd_idle,           None),
     "inventory":     (commands.general.cmd_inventory,      None),
     "look":          (commands.general.cmd_look,           None),
     "page":          (commands.general.cmd_page,           None),
     "pose":          (commands.general.cmd_pose,           None),
     "quit":          (commands.general.cmd_quit,           None),
     "say":           (commands.general.cmd_say,            None),
     "time":          (commands.info.cmd_time,              None),
     "uptime":        (commands.info.cmd_uptime,            None),
     "version":       (commands.info.cmd_version,           None),
     "who":           (commands.general.cmd_who,            None),
     "@alias":        (commands.objmanip.cmd_alias,         None),
     "@boot":         (commands.privileged.cmd_boot,        ("genperms.manage_players")),
     "@ccreate":      (commands.comsys.cmd_ccreate,         ("objects.add_commchannel")),
     "@cdestroy":     (commands.comsys.cmd_cdestroy,        ("objects.delete_commchannel")),
     "@cemit":        (commands.comsys.cmd_cemit,           None),
     "@clist":        (commands.comsys.cmd_clist,           None),
     "@create":       (commands.objmanip.cmd_create,        ("genperms.builder")),
     "@describe":     (commands.objmanip.cmd_description,   None),
     "@destroy":      (commands.objmanip.cmd_destroy,       ("genperms.builder")),
     "@dig":          (commands.objmanip.cmd_dig,           ("genperms.builder")),
     "@emit":         (commands.general.cmd_emit,           ("genperms.announce")),
#     "@pemit":        (commands.general.cmd_pemit,          None),
     "@find":         (commands.objmanip.cmd_find,          ("genperms.builder")),
     "@link":         (commands.objmanip.cmd_link,          ("genperms.builder")),
     "@list":         (commands.info.cmd_list,              ("genperms.process_control")),
     "@name":         (commands.objmanip.cmd_name,          None),
     "@nextfree":     (commands.objmanip.cmd_nextfree,      ("genperms.builder")),
     "@newpassword":  (commands.privileged.cmd_newpassword, ("genperms.manage_players")),
     "@open":         (commands.objmanip.cmd_open,          ("genperms.builder")),
     "@password":     (commands.general.cmd_password,       None),
     "@ps":           (commands.info.cmd_ps,                ("genperms.process_control")),
     "@reload":       (commands.privileged.cmd_reload,      ("genperms.process_control")),
     "@set":          (commands.objmanip.cmd_set,           None),
     "@shutdown":     (commands.privileged.cmd_shutdown,    ("genperms.process_control")),
     "@stats":        (commands.info.cmd_stats,             None),
     "@teleport":     (commands.objmanip.cmd_teleport,      ("genperms.builder")),
     "@unlink":       (commands.objmanip.cmd_unlink,        ("genperms.builder")),
     "@wall":         (commands.general.cmd_wall,           ("genperms.announce")),
     "@wipe":         (commands.objmanip.cmd_wipe,          None),
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
