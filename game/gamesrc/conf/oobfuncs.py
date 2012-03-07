"""
 Example module holding functions for out-of-band protocols to
 import and map to given commands from the client. This module 
 is selected by settings.OOB_FUNC_MODULE. 
 
 All functions defined global in this module will be available
 for the oob system to call. They will be called with a session/character
 as first argument (depending on if the session is logged in or not), 
 following by any number of extra arguments. The return value will
 be packed and returned to the oob protocol and can be on any form. 
"""

def testoob(character, *args, **kwargs):
    "Simple test function"
    print "Called testoob: %s" % val
    return "testoob did stuff to the input string '%s'!" % val
