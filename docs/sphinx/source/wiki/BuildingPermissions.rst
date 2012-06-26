Giving permissions to your staff
================================

*OBS: This gives only a brief introduction to the access system. Locks
and permissions are fully detailed* `here <Locks.html>`_.

The super user
--------------

There are strictly speaking two types of users in Evennia, the *super
user* and everyone else. The superuser is the first user you create,
object #1. This is the all-powerful server-owner account. A superuser
account has access to everything and no locks affect them. Technically
the superuser not only has all access, it even bypasses the permission
checks entirely. This makes the superuser impossible to lock out, but
makes it unsuitable to actually play-test the game's locks and
restrictions with. Usually there is no need to have but one superuser.

Assigning permissions
---------------------

Whereas permissions can be used for anything, those put in
settings.PERMISSION\_HIERARCHY will have a ranking relative each other
as well. By default Evennia creates the following hierarchy:

#. *Immortals* - these basically have all the same access as superusers
   (except that they do not sidestep the Permission system). Assign only
   to really trusted server-admin staff.
#. *Wizards* can do everything except affecting the server functions
   itself. So a wizard couldn't reload or shutdown the server for
   example. They also cannot execute arbitrary Python code on the
   console or import files from the hard drive.
#. *Builders* has all the build commands, but cannot affect other
   players or mess with the server.
#. *PlayerHelpers* are almost like a normal *Player*, but they can also
   add help files to the database.
#. *Players* is the default group that new players end up in. A new
   player have permission to use tells, to use and create new channels.

A user having a higher-level permission also automatically have access
to locks requiring only lower-level access.

To assign a new permission from inside the game, you need to be able to
use the ``@perm`` command. This is an *Immortal*-level command, but it
could in principle be made lower-access since it only allows assignments
equal or lower to your current level (so you cannot use it to escalate
your own permission level). So, assuming you yourself have *Immortal*
access (or is superuser), you assign a new player "Tommy" to your core
staff with the command

::

    @perm/add Tommy = Immortals

