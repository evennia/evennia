"""
These commands typically are to do with building or modifying Objects.
"""
from django.conf import settings 
from src.permissions.permissions import has_perm, has_perm_string
from src.objects.models import ObjectDB, ObjAttribute
from game.gamesrc.commands.default.muxcommand import MuxCommand
from src.utils import create, utils 

    
##         
## def cmd_chown(command):
##     """
##     @chown - change ownerships

##     Usage:
##       @chown <Object> = <NewOwner>  
    
##     Changes the ownership of an object. The new owner specified must be a
##     player object.    
##     """
##     caller = command.caller

##     if not command.command_argument:
##         caller.msg("Usage: @chown <object> = <newowner>")
##         return

##     eq_args = command.command_argument.split('=', 1)
##     target_name = eq_args[0]
##     owner_name = eq_args[1]    

##     if len(target_name) == 0:
##         caller.msg("Change the ownership of what?")
##         return

##     if len(eq_args) > 1:
##         target_obj = caller.search_for_object(target_name)
##         # Use search_for_object to handle duplicate/nonexistant results.
##         if not target_obj:
##             return

##         if not caller.controls_other(target_obj) and not caller.has_perm("objects.admin_ownership"):
##             caller.msg(defines_global.NOCONTROL_MSG)
##             return

##         owner_obj = caller.search_for_object(owner_name)
##         # Use search_for_object to handle duplicate/nonexistant results.
##         if not owner_obj:
##             return
##         if not owner_obj.is_player():
##             caller.msg("Only players may own objects.")
##             return
##         if target_obj.is_player():
##             caller.msg("You may not change the ownership of player objects.")
##             return

##         target_obj.set_owner(owner_obj)
##         caller.msg("%s now owns %s." % (owner_obj, target_obj))
##     else:
##         # We haven't provided a target.
##         caller.msg("Who should be the new owner of the object?")
##         return
## GLOBAL_CMD_TABLE.add_command("@chown", cmd_chown, priv_tuple=("objects.modify_attributes",
##                                                               "objects.admin_ownership"),
##                              help_category="Building" )
            
                

#NOT VALID IN NEW SYSTEM!
## def cmd_lock(command):
##     """
##     @lock - limit use of objects

##     Usage:
##       @lock[/switch] <obj> [:type] [= <key>[,key2,key3,...]]    

##     Switches:
##       add    - add a lock (default) from object 
##       del    - remove a lock from object  
##       list   - view all locks on object (default)
##     type:
##       DefaultLock  - the default lock type (default)
##       UseLock      - prevents usage of objects' commands
##       EnterLock    - blocking objects from entering the object
      
##     Locks an object for everyone except those matching the keys.
##     The keys can be of the following types (and searched in this order):
##        - a user #dbref (#2, #45 etc)
##        - a Group name (Builder, Immortal etc, case sensitive)
##        - a Permission string (genperms.get, etc)
##        - a Function():return_value pair. (ex: alliance():Red). The
##            function() is called on the locked object (if it exists) and
##            if its return value matches the Key is passed. If no
##            return_value is given, matches against True.
##        - an Attribute:return_value pair (ex: key:yellow_key). The
##            Attribute is the name of an attribute defined on the locked
##            object. If this attribute has a value matching return_value,
##            the lock is passed. If no return_value is given, 
##            attributes will be searched, requiring a True
##            value.
        
##     If no keys at all are given, the object is locked for everyone.
##     When the lock blocks a user, you may customize which error is given by
##     storing error messages in an attribute. For DefaultLocks, UseLocks and
##     EnterLocks, these attributes are called lock_msg, use_lock_msg and
##     enter_lock_msg respectively.

##     [[lock_types]]

##     Lock types:

##     Name:          Affects:        Effect:  
##     -----------------------------------------------------------------------
##     DefaultLock:   Exits:          controls who may traverse the exit to
##                                    its destination.
##                    Rooms:          controls whether the player sees a failure
##                                    message after the room description when
##                                    looking at the room.
##                    Players/Things: controls who may 'get' the object.

##      UseLock:      All but Exits:  controls who may use commands defined on
##                                    the locked object.

##      EnterLock:    Players/Things: controls who may enter/teleport into
##                                    the object.      
##      VisibleLock:  Players/Things: controls if the object is visible to
##                                    someone using the look command.

##     Fail messages echoed to the player are stored in the attributes 'lock_msg',
##     'use_lock_msg', 'enter_lock_msg' and 'visible_lock_msg' on the locked object
##     in question. If no such message is stored, a default will be used (or none at
##     all in some cases). 
##     """

##     caller = command.caller
##     arg = command.command_argument
##     switches = command.command_switches
    
##     if not arg:
##         caller.msg("Usage: @lock[/switch] <obj> [:type] [= <key>[,key2,key3,...]]")        
##         return
##     keys = "" 
##     #deal with all possible arguments. 
##     try: 
##         lside, keys = arg.split("=",1)
##     except ValueError:
##         lside = arg    
##     lside, keys = lside.strip(), keys.strip()
##     try:
##         obj_name, ltype = lside.split(":",1)
##     except:
##         obj_name = lside
##         ltype = "DefaultLock"
##     obj_name, ltype = obj_name.strip(), ltype.strip()

##     if ltype not in ["DefaultLock","UseLock","EnterLock","VisibleLock"]: 
##         caller.msg("Lock type '%s' not recognized." % ltype)
##         return    

##     obj = caller.search_for_object(obj_name)
##     if not obj:
##         return    

##     obj_locks = obj.LOCKS

##     if "list" in switches:        
##         if not obj_locks:
##             s = "There are no locks on %s." % obj.name
##         else:
##             s = "Locks on %s:" % obj.name
##             s += obj_locks.show()
##         caller.msg(s)        
##         return
    
##     # we are trying to change things. Check permissions.
##     if not caller.controls_other(obj):
##         caller.msg(defines_global.NOCONTROL_MSG)
##         return
    
##     if "del" in switches:
##         # clear a lock
##         if obj_locks:
##             if not obj_locks.has_type(ltype):
##                 caller.msg("No %s set on this object." % ltype)
##             else:
##                 obj_locks.del_type(ltype)
##                 obj.LOCKS = obj_locks
##                 caller.msg("Cleared lock %s on %s." % (ltype, obj.name))
##         else:
##             caller.msg("No %s set on this object." % ltype)
##         return     
##     else:
##         #try to add a lock
##         if not obj_locks:
##             obj_locks = locks.Locks()
##         if not keys:
##             #add an impassable lock
##             obj_locks.add_type(ltype, locks.Key())            
##             caller.msg("Added impassable '%s' lock to %s." % (ltype, obj.name))
##         else: 
##             keys = [k.strip() for k in keys.split(",")]
##             obj_keys, group_keys, perm_keys = [], [], []
##             func_keys, attr_keys = [], []
##             allgroups = [g.name for g in Group.objects.all()]
##             allperms = ["%s.%s" % (p.content_type.app_label, p.codename)
##                         for p in Permission.objects.all()]
##             for key in keys:
##                 #differentiate different type of keys
##                 if Object.objects.is_dbref(key):
##                     # this is an object key, like #2, #6 etc
##                     obj_keys.append(key)
##                 elif key in allgroups:
##                     # a group key 
##                     group_keys.append(key)
##                 elif key in allperms:
##                     # a permission string 
##                     perm_keys.append(key)
##                 elif '()' in key:                    
##                     # a function()[:returnvalue] tuple.
##                     # Check if we also request a return value 
##                     funcname, rvalue = [k.strip() for k in key.split('()',1)]
##                     if not funcname:
##                         funcname = "lock_func"
##                     rvalue = rvalue.lstrip(':')
##                     if not rvalue:
##                         rvalue = True
##                     # pack for later adding.
##                     func_keys.append((funcname, rvalue))
##                 elif ':' in key: 
##                     # an attribute[:returnvalue] tuple.
##                     attr_name, rvalue = [k.strip() for k in key.split(':',1)]
##                     # pack for later adding
##                     attr_keys.append((attr_name, rvalue))
##                 else:
##                     caller.msg("Key '%s' is not recognized as a valid dbref, group or permission." % key)
##                     return 
##             # Create actual key objects from the respective lists
##             keys = []
##             if obj_keys:
##                 keys.append(locks.ObjKey(obj_keys))
##             if group_keys:
##                 keys.append(locks.GroupKey(group_keys))
##             if perm_keys:
##                 keys.append(locks.PermKey(perm_keys))
##             if func_keys: 
##                 keys.append(locks.FuncKey(func_keys, obj.dbref))
##             if attr_keys:
##                 keys.append(locks.AttrKey(attr_keys))
                
##             #store the keys in the lock
##             obj_locks.add_type(ltype, keys)            
##             kstring = " "
##             for key in keys:
##                 kstring += " %s," % key 
##             kstring = kstring[:-1]
##             caller.msg("Added lock '%s' to %s with keys%s." % (ltype, obj.name, kstring))
##         obj.LOCKS = obj_locks
## GLOBAL_CMD_TABLE.add_command("@lock", cmd_lock, priv_tuple=("objects.create",), help_category="Building")





