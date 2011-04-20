"""
Debug mechanisms for easier developing advanced game objects


The functions in this module are intended to stress-test various
aspects of an in-game entity, notably objects and scripts, during 
development. This allows to run several automated tests on the 
entity without having to do the testing by creating/deleting etc
in-game. 

The default Evennia accesses the methods of this module through 
a special state and cmdset, using the @debug command. 

"""

from traceback import format_exc
from src.utils import create 


def trace():
    "Format the traceback."
    errlist = format_exc().split('\n')
    if len(errlist) > 4:
        errlist = errlist[4:]
    ret = "\n" + "\n".join("<<< {r%s{n" % line for line in errlist if line)
    return ret

#
# Testing scripts
#

def debug_script(script_path, obj=None, auto_delete=True):
    """
    This function takes a script database object (ScriptDB) and tests
    all its hooks for syntax errors. Note that no run-time errors
    will be caught, only weird python syntax.

    script_path - the full path to the script typeclass module and class.

    """
    try:
        string = "Test-creating a new script of this type ... "
        scriptobj = create.create_script(script_path, autostart=False)
        scriptobj.obj = obj
        scriptobj.save()
        string += "{gOk{n."
    except Exception:
        string += trace()
        try: scriptobj.delete()
        except: pass
        return string 

    string += "\nRunning syntax check ..."
    try:
        string += "\nTesting syntax of at_script_creation(self) ... "
        ret = scriptobj.at_script_creation()
        string += "{gOk{n."
    except Exception:
        string += trace()
    try:
        string += "\nTesting syntax of is_valid(self) ... "
        ret = scriptobj.is_valid()
        string += "{gOk{n."
    except Exception:
        string += trace()        
    try:
        string += "\nTesting syntax of at_start(self) ... "
        ret = scriptobj.at_start()
        string += "{gOk{n."
    except Exception:
        string += trace()
    try:
        string += "\nTesting syntax of at_repeat(self) ... "
        ret = scriptobj.at_repeat()
        string += "{gOk{n."
    except Exception:
        string += trace()
    try:
        string += "\nTesting syntax of at_stop(self) ... "
        ret =  scriptobj.at_script_creation()
        string += "{gOk{n."
    except Exception:
        string += trace()

    if auto_delete:
        try: 
            scriptobj.delete()
        except: 
            string += trace()

    return string

#
# Testing objects
#

def debug_object(obj_path, caller):
    """
    Auto-test an object's hooks and methods.
    """
    try:
        string = "\n Test-creating a new object of path {w%s{n ... " % obj_path
        obj = create.create_object(obj_path)
        obj.location = caller.location
        string += "{gOk{n."
    except Exception:
        string += trace()
        try: obj.delete()
        except: pass
        return string 
    string += "\nRunning syntax checks ..."    
    try:
        string += "\nCalling at_first_login(self) ... "
        ret = obj.at_first_login()
        string += "{gOk{n."
    except Exception:
        string += trace()
    try:
        string += "\nCalling at_pre_login(self) ... "
        ret = obj.at_pre_login()
        string += "{gOk{n."
    except Exception:
        string += trace()
    try:
        string += "\nCalling at_post_login(self) ... "
        ret = obj.at_post_login()
        string += "{gOk{n."
    except Exception:
        string += trace()
    try:
        string += "\nCalling at_disconnect(self) ... "
        ret = obj.at_disconnect()
        string += "{gOk{n."
    except Exception:
        string += trace()
    try:
        string += "\nCalling at_before_move(self, dest) ... "
        ret = obj.at_before_move(caller.location)
        string += "{gOk{n: returns %s" % ret
    except Exception:
        string += trace()
    try:
        string += "\nCalling announce_move_from(self, dest) ... "
        ret = obj.announce_move_from(caller.location)
        string += "{gOk{n"
    except Exception:
        string += trace()
    try:
        string += "\nCalling announce_move_to(self, source_loc) ... "
        ret = obj.announce_move_from(caller.location)
        string += "{gOk{n."
    except Exception:
        string += trace()
    try:
        string += "\nCalling at_after_move(self, source_loc) ... "
        ret = obj.at_after_move(caller.location)
        string += "{gOk{n."
    except Exception:
        string += trace()
    try:
        string += "\nCalling at_object_receive(self, caller, source_loc) ... "
        ret = obj.at_object_receive(caller, caller.location)
        string += "{gOk{n."
    except Exception:
        string += trace()
    try:
        string += "\nCalling return_appearance(self, caller) ... "
        ret = obj.return_appearance(caller)
        string += "{gOk{n."
    except Exception:
        string += trace()
    try:
        string += "\nCalling at_msg_receive(self, msg, from_obj) ... "
        ret = obj.at_msg_receive("test_message_receive", caller)
        string += "{gOk{n."
    except Exception:
        string += trace()
    try:
        string += "\nCalling at_msg_send(self, msg, to_obj) ... "
        ret = obj.at_msg_send("test_message_send", caller)
        string += "{gOk{n."
    except Exception:
        string += trace()
    try:
        string += "\nCalling at_desc(self, looker) ... "
        ret = obj.at_desc(caller)
        string += "{gOk{n."
    except Exception:
        string += trace()
    try:
        string += "\nCalling at_object_delete(self) ... "
        ret = obj.at_object_delete()
        string += "{gOk{n."
    except Exception:
        string += trace()
    try:
        string += "\nCalling at_get(self, getter) ... "
        ret = obj.at_get(caller)
        string += "{gOk{n."
    except Exception:
        string += trace()    
    try:
        string += "\nCalling at_drop(self, dropper) ... "
        ret = obj.at_drop(caller)
        string += "{gOk{n."
    except Exception:
        string += trace()
    try:
        string += "\nCalling at_say(self, speaker, message) ... "
        ret = obj.at_say(caller, "test_message_say")
        string += "{gOk{n."
    except Exception:
        string += trace()

    try: 
        obj.delete()
    except: 
        string += trace()
    return string 

def debug_object_scripts(obj_path, caller):
    """
    Create an object and test all its associated scripts 
    independently. 
    """

    try:
        string = "\n Testing scripts on {w%s{n ... " % obj_path
        obj = create.create_object(obj_path)
        obj.location = caller.location
        obj = obj.dbobj
        string += "{gOk{n."
    except Exception:
        string += trace()
        try: obj.delete()
        except: pass
        return string 
    scripts = obj.scripts.all()
    if scripts:
        string += "\n Running tests on %i object scripts ... " % (len(scripts))
        for script in scripts:
            string += "\n {wTesting %s{n ..." % script.key
            path = script.typeclass_path
            string += debug_script(path, obj=obj)
            #string += debug_run_script(path, obj=obj)
    else:
        string += "\n No scripts defined on object."

    try: 
        obj.delete()
    except: 
        string += trace()
    return string 


