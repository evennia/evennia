"""
Contains commands for managing script parents.
"""
from src import scripthandler
from src import defines_global
from src.cmdtable import GLOBAL_CMD_TABLE
      
def cmd_scriptcache(command):
    """
    @scriptcache 

    Usage
      @scriptcache

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
                             priv_tuple=("genperms.builder",), help_category="Admin")

def cmd_parent(command):
    """
    @parent - set script parent

    Usage:
      @parent <object> = <parent>

    Example:
      @parent button = examples.red_button
      
    Sets an object's script parent. The parent must be identified
    by its location using dot-notation pointing to the script
    parent module.
    """
    source_object = command.source_object

    if not command.command_argument:
        source_object.emit_to("Usage: @parent <object> [=<parent]")
        return

    eq_args = command.command_argument.split('=', 1)
    target_name = eq_args[0]
    target_obj = source_object.search_for_object(target_name)

    if not target_obj:
        return

    if len(eq_args) > 1:
        #if we gave a command of the form @parent obj=something we want to
        #somehow affect the parent.

        parent_name = eq_args[1]    

        #check permissions
        if not source_object.controls_other(target_obj):
            source_object.emit_to(defines_global.NOCONTROL_MSG)
            return

        # Clear parent if command was @parent obj= or obj=none
        if not parent_name or parent_name.lower() == "none":
            target_obj.set_script_parent(None)
            target_obj.scriptlink.at_object_creation()
            new_parent = target_obj.scriptlink()
            source_object.emit_to("%s reverted to its default parent (%s)." %
                                  (target_obj, new_parent))
            return        

        # If we reach this point, attempt to change parent.        
        former_parent = target_obj.get_scriptlink()
        if target_obj.set_script_parent(parent_name):
            #new script path added; initialize the parent
            target_obj.scriptlink.at_object_creation()

            s = "%s's parent is now %s (instead of %s).\n\r"
            s += "Note that the new parent type could have overwritten "
            s += "same-named attributes on the existing object."            
            source_object.emit_to(s)
        else:
            source_object.emit_to("'%s' is not a valid parent path." % parent_name)

    else:
        # We haven't provided a target; list the current parent
        current_parent = target_obj.get_scriptlink()
        source_object.emit_to("Current parent of %s is %s." %
                              (target_obj,current_parent)) 
        
GLOBAL_CMD_TABLE.add_command("@parent", cmd_parent,
                             priv_tuple=("genperms.builder",), help_category="Building" )

