Updating your Game
==================

Fortunately, it's extremely easy to keep your Evennia server up-to-date
via Subversion. If you haven't already, see the `Getting Started
guide <GettingStarted.html>`_ and get your installation up. You'll then
want to join the `Evennia Commit
Log <http://groups.google.com/group/evennia-commits/>`_ group. This will
notify you via email whenever updates are made to the source in the
Subversion repository, letting you know you need to update. You can also
subscribe to the RSS feed or check up on the feeds from
`http://www.evennia.com. <http://www.evennia.com.>`_ When you're wanting
to apply updates, simply ``cd`` to your ``evennia`` root directory and
type:

``svn update``

Assuming you've got the command line client. If you're using a graphical
client, you will probably want to navigate to the ``evennia`` directory
and either right click and find your client's update function, or use
one of the menus (if applicable).

You can review the latest changes with

``svn log``

or the equivalent in the graphical client. You can also see the latest
changes online `here <http://code.google.com/p/evennia/source/list>`_.

A Note on Schema Migration
--------------------------

Database migration becomes an issue when/if the database models of
Evennia changes in an update (this should be gradually more and more
rare as Evennia matures). If you already have a database, this then has
to be updated to match the latest server version or you are likely to
run into trouble down the line.

One way to solve this is to manually add/remove the new tables or fields
to your existing database (or simply reset your database if you don't
have anything important in it yet). Enter
`South <http://south.aeracode.org/>`_. South is a Django database schema
migration tool. It keep tracks of changes in the database schema and
applies those changes to the database for you.

Using South is optional, but if you install South, Evennia will use it
automatically. See correct section of
`GettingStarted <GettingStarted.html>`_ on how to install South and the
slightly changed way to start a clean database server when South is used
(you have to give the ``mange.py migrate`` command as well as
``manage.py syncdb``).

Once you have a database ready to use South, you work as normal.
Whenever a new Evennia update tells you that the database schema has
changed (check ``svn log`` or the online list), you go to ``game/`` and
run this command:

``python manage.py migrate``

This will convert your database to the new schema and you should be set
to go.
