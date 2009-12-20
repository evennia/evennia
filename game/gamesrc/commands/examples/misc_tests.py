"""
This module contains various commands for testing some
of Evennia's subsystems. They were used for initial testing
but are also instructive for playing around with to learn
how different systems work. See also state_example.py. 

To make these commands available in-game, add this module
to the CUSTOM_COMMAND_MODULES tuple in game/settings.py
as 'game.gamesrc.commands.examples.misc_tests'. 

None of these commands are auto-added to the help database
(they have no docstrings) in order to help make it clean. 
"""

from src.cmdtable import GLOBAL_CMD_TABLE

#------------------------------------------------------------
# Tests of the event system 
#------------------------------------------------------------

def cmd_testevent(command):
    #
    # This test allows testing the event system 
    #
    # Usage:
    #   @testevent [pid]
    #
    # Without argument, this command creates
    # a dummy event in the process table.
    # Use @ps to see it. Give the equivalent
    # pid to remove it again (careful though,
    # this command can also remove useful
    # events if you give the wrong pid).
    # 
    from src import events
    from src import scheduler

    source_object = command.source_object

    if not source_object.is_superuser():
        # To avoid accidental access to process table
        source_object.emit_to("This command is superuser only.")
        return 

    if not command.command_argument:
        # No argument given; create a new test event. 
        event = events.IntervalEvent()
        event.description = "Test event created with @testevent."
        event.repeats = 3
        event.interval = 5
        pid = scheduler.add_event(event)
        string = "Event with pid %s added. " % pid
        string += "It repeats %i times and waits " % event.repeats
        string += "for %i seconds between each repeat." % event.interval
        string += "After all repeats, it will delete itself."
        string += "\nUse @ps to see it and give this "
        string += "command with the pid as argument to delete it."
        source_object.emit_to(string)
    else:
        # An argument given; assume this is a pid. 
        try:
            pid = int(command.command_argument)
        except:
            source_object.emit_to("Not a valid argument. You must give a number.")
            return 
        if pid < 3:
            string = "This low pid might belong to a system process, \n"
            string += "so as a safety measure you cannot delete it using \n"
            string += "this test command. Use @delevent instead."
            source_object.emit_to(string)
            return 
        pid = command.command_argument
        scheduler.del_event(pid)
        string = "Event with pid %s removed (if it existed)." % pid
        string += " Confirm this worked using @ps."
        source_object.emit_to(string)
GLOBAL_CMD_TABLE.add_command("@testevent", cmd_testevent,
                             auto_help_override=False)    


#------------------------------------------------------------
# Test of Cache system
#------------------------------------------------------------

def cmd_testcache(command):    
    #
    # Tests the cache system by writing to it
    # back and forth several times.
    # 
    # Usage: 
    #    @testcache [get]
    #
    # Use without 'get' to store test data in
    # caches and with 'get' to read them back
    # and make sure they all saved as they
    # should. You might also want to
    # try shut down the server between
    # calls to make sure the persistent
    # cache does survive the shutdown. 

    from src.cache import cache
    from src import gametime

    source_object = command.source_object
    switches = command.command_switches

    s1 = "Value: Cache: OK"
    s2 = "Value: PCache 1 (set using property assignment): OK"
    s3 = "Value: PCache 2 (set using function call): OK"
    if switches and "get" in switches:
        # Reading from cache
        source_object.emit_to("Reading from cache ...")
        cache.load_pcache()
        cache_vol = source_object.cache.testcache        
        source_object.emit_to("< volatile cache:\n  %s" % cache_vol)
        cache_perm = source_object.pcache.testcache_perm
        source_object.emit_to("< persistent cache 1/2:\n  %s" % cache_perm)
        cache_perm2 = cache.get_pcache("permtest2")
        source_object.emit_to("< persistent cache 2/2:\n  %s" % cache_perm2)
    else:
        # Saving to cache
        source_object.emit_to("Save to cache ...")
        source_object.cache.testcache = s1
        # using two different ways to set pcache
        source_object.pcache.testcache_perm = s2
        cache.set_pcache("permtest2", s3)

        source_object.emit_to("> volatile cache:\n  %s" % s1)
        source_object.emit_to("> persistent cache 1/2:\n  %s" % s2)
        source_object.emit_to("> persistent cache 2/2:\n  %s" % s3)
        cache.save_pcache()
        string = "Caches saved. Use /get as a switch to read them back."
        source_object.emit_to(string)
    source_object.emit_to("Running Gametime: %i" % gametime.time())
GLOBAL_CMD_TABLE.add_command("@testcache", cmd_testcache,
                             auto_help_override=False)   
