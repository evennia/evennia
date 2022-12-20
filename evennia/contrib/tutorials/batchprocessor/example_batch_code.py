#
# Batchcode script
#
#
# The Batch-code processor accepts full Python modules (e.g. "batch.py") that
# look identical to normal Python files with a few exceptions that allows them
# to be executed in blocks. This way of working assures a sequential execution
# of the file and allows for features like stepping from block to block
# (without executing those coming before), as well as automatic deletion
# of created objects etc. You can however also run a batch-code python file
# directly using Python.

# Code blocks are separated by python comments starting with special code words.

# #HEADER - this denotes commands global to the entire file, such as
#           import statements and global variables. They will
#           automatically be made available for each block.  Observe
#           that changes to these variables made in one block are not
#           preserved between blocks!)
# #CODE (infotext) [objname, objname, ...] - This designates a code block that
#            will be executed like a stand-alone piece of code together with
#            any #HEADER defined.
#            infotext is a describing text about what goes on in this block.
#            It will be shown by the batch-processing command.
#            <objname>s mark the (variable-)names of objects created in
#            the code, and which may be auto-deleted by the processor if
#            desired (such as when debugging the script). E.g., if the code
#            contains the command myobj = create.create_object(...), you could
#            put 'myobj' in the #CODE header regardless of what the created
#            object is actually called in-game.
# #INSERT filename - this includes another code batch file into this one. The
#            named file will be loaded and run at the position of the #INSERT.
#            Note that the inserted file will use its own #HEADERs and not
#            have access to the #HEADERs of the inserting file.

# The following variable is automatically made available for the script:

# caller - the object executing the script
#


# HEADER

# everything in this block will be appended to the beginning of
# all other #CODE blocks when they are executed.

from evennia import DefaultObject, create_object, search_object
from evennia.contrib.tutorials import red_button

limbo = search_object("Limbo")[0]


# CODE

# This is the first code block. Within each block, Python
# code works as normal. Note how we make use if imports and
# 'limbo' defined in the #HEADER block. This block's header
# offers no information about red_button variable, so it
# won't be able to be deleted in debug mode.

# create a red button in limbo
red_button = create_object(
    red_button.RedButton, key="Red button", location=limbo, aliases=["button"]
)

# we take a look at what we created
caller.msg("A %s was created." % red_button.key)

# CODE

# this code block has 'table' and 'chair' set as deletable
# objects. This means that when the batchcode processor runs in
# testing mode, objects created in these variables will be deleted
# again (so as to avoid duplicate objects when testing the script many
# times).

# the Python variables we assign to must match the ones given in the
# header for the system to be able to delete them afterwards during a
# debugging run.
table = create_object(DefaultObject, key="Table", location=limbo)
chair = create_object(DefaultObject, key="Chair", location=limbo)

string = "A %s and %s were created."
if DEBUG:
    string += " Since debug was active, they were deleted again."
    table.delete()
    chair.delete()

caller.msg(string % (table, chair))
