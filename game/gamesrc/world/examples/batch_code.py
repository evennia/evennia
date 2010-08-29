#
# Batchcode script
# 
#
# The Batch-code processor accepts full python modules (e.g. "batch.py") that
# looks identical to normal Python files with a few exceptions that allows them
# to the executed in blocks. This way of working assures a sequential execution
# of the file and allows for features like stepping from block to block
# (without executing those coming before), as well as automatic deletion
# of created objects etc. You can however also run a batch-code python file
# directly using Python (and can also be de). 

# Code blocks are separated by python comments starting with special code words. 

# #HEADER - this denotes commands global to the entire file, such as
#           import statements and global variables. They will
#           automatically be made available for each block.  Observe
#           that changes to these variables made in one block is not
#           preserved between blocks!)
# #CODE [objname, objname, ...] - This designates a code block that will be executed like a 
#            stand-alone piece of code together with any #HEADER
#            defined. <objname>s mark the (variable-)names of objects created in the code, 
#            and which may be auto-deleted by the processor if desired (such as when 
#            debugging the script). E.g., if the code contains the command 
#            myobj = create.create_object(...), you could put 'myobj' in the #CODE header
#            regardless of what the created object is actually called in-game. 

# The following variables are automatically made available for the script:

# caller - the object executing the script
#
#

#HEADER 

# everything in this block will be imported to all CODE blocks when
# they are executed.

from src.utils import create, search
from game.gamesrc.typeclasses.examples import red_button
from game.gamesrc.typeclasses import basetypes

#CODE 

# This is the first code block. Within each block, python
# code works as normal.

# get the limbo room.
limbo = search.objects(caller, 'Limbo', global_search=True)[0]
caller.msg(limbo)
# create a red button in limbo
red_button = create.create_object(red_button.RedButton, key="Red button", 
                                  location=limbo, aliases=["button"])

# we take a look at what we created
caller.msg("A %s was created." % red_button.key)

#CODE table, chair

# this code block has 'table' and 'chair' set as deletable
# objects. This means that when the batchcode processor runs in
# testing mode, objects created in these variables will be deleted
# again (so as to avoid duplicate objects when testing the script).

limbo = search.objects(caller, 'Limbo', global_search=True)[0]
caller.msg(limbo.key)
table = create.create_object(basetypes.Object, key="Table", location=limbo)
chair = create.create_object(basetypes.Object, key="Chair", location=limbo)

string = "A %s and %s were created. If debug was active, they were deleted again." 
caller.msg(string % (table, chair))
