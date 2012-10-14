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
# #CODE (infotext) [objname, objname, ...] - This designates a code block that will be executed like a
#            stand-alone piece of code together with any #HEADER
#            defined.
#            infotext is a describing text about what goes in in this block. It will be
#            shown by the batchprocessing command.
#            <objname>s mark the (variable-)names of objects created in the code,
#            and which may be auto-deleted by the processor if desired (such as when
#            debugging the script). E.g., if the code contains the command
#            myobj = create.create_object(...), you could put 'myobj' in the #CODE header
#            regardless of what the created object is actually called in-game.
# #INSERT filename - this includes another code batch file. The named file will be loaded and
#            run at this point. Note that code from the inserted file will NOT share #HEADERs
#            with the importing file, but will only use the headers in the importing file.
#            make sure to not create a cyclic import here!

# The following variable is automatically made available for the script:

# caller - the object executing the script
#


#HEADER

# everything in this block will be appended to the beginning of
# all other #CODE blocks when they are executed.

from ev import create_object, search_object
from game.gamesrc.objects.examples import red_button
from ev import Object

limbo = search_object('Limbo')[0]


#CODE (create red button)

# This is the first code block. Within each block, python
# code works as normal. Note how we make use if imports and
# 'limbo' defined in the #HEADER block. This block's header
# offers no information about red_button variable, so it
# won't be able to be deleted in debug mode.

# create a red button in limbo
red_button = create_object(red_button.RedButton, key="Red button",
                                  location=limbo, aliases=["button"])

# we take a look at what we created
caller.msg("A %s was created." % red_button.key)

#CODE (create table and chair) table, chair

# this code block has 'table' and 'chair' set as deletable
# objects. This means that when the batchcode processor runs in
# testing mode, objects created in these variables will be deleted
# again (so as to avoid duplicate objects when testing the script many
# times).

# the python variables we assign to must match the ones given in the
# header for the system to be able to delete them afterwards during a
# debugging run.
table = create_object(Object, key="Table", location=limbo)
chair = create_object(Object, key="Chair", location=limbo)

string = "A %s and %s were created. If debug was active, they were deleted again."
caller.msg(string % (table, chair))
