"""
Contains commands for managing script parents.
"""
from src import scripthandler
from src.cmdtable import GLOBAL_CMD_TABLE
      
def cmd_scriptcache(command):
    """
    Shows the contents of the script cache.
    """
    cache_dict = scripthandler.CACHED_SCRIPTS
    
    retval = "Currently Cached Script Parents\n"
    retval += "-" * 78
    for script in cache_dict.keys():
        retval += "\n " + script
    retval += "\n" + "-" * 78 + "\n"
    retval += "%d cached parents" % len(cache_dict)
    command.source_object.emit_to(retval)
GLOBAL_CMD_TABLE.add_command("@scriptcache", cmd_scriptcache,
                             priv_tuple=("genperms.builder"))

def cmd_parent(command):
    """
    Sets an object's script parent.
    """
    source_object = command.source_object

    if not command.command_argument:
        source_object.emit_to("Change the parent of what?")
        return

    eq_args = command.command_argument.split('=', 1)
    target_name = eq_args[0]
    parent_name = eq_args[1]    

    if len(target_name) == 0:
        source_object.emit_to("Change the parent of what?")
        return

    if len(eq_args) > 1:
        target_obj = source_object.search_for_object(target_name)
        # Use search_for_object to handle duplicate/nonexistant results.
        if not target_obj:
            return

        if not source_object.controls_other(target_obj):
            source_object.emit_to(defines_global.NOCONTROL_MSG)
            return

        # Allow the clearing of a zone
        if parent_name.lower() == "none":
            target_obj.set_script_parent(None)
            source_object.emit_to("%s reverted to default parent." % (target_obj))
            return

        target_obj.set_script_parent(parent_name)
        source_object.emit_to("%s is now a child of %s." % (target_obj, parent_name))

    else:
        # We haven't provided a target zone.
        source_object.emit_to("What should the object's parent be set to?")
        return
GLOBAL_CMD_TABLE.add_command("@parent", cmd_parent,
                             priv_tuple=("genperms.builder"))

