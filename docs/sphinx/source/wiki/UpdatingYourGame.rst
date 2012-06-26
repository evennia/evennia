Updating your Game
==================

Fortunately, it's extremely easy to keep your Evennia server up-to-date
via Mercurial. If you haven't already, see the `Getting Started
guide <GettingStarted.html>`_ and get everything running. There are many
ways to get told when to update: You can subscribe to the RSS feed or
manually check up on the feeds from
`http://www.evennia.com <http://www.evennia.com>`_. You can also join
the `Evennia Commit
Log <http://groups.google.com/group/evennia-commits/>`_ group, which
will send you an email when the server repository changes.

When you're wanting to apply updates, simply ``cd`` to your ``evennia``
root directory and type:

::

     hg pull
     hg update

Assuming you've got the command line client. If you're using a graphical
client, you will probably want to navigate to the ``evennia`` directory
and either right click and find your client's pull function, or use one
of the menus (if applicable).

You can review the latest changes with

::

     hg log

or the equivalent in the graphical client. The log tends to scroll past
quite quickly, so if you are in linux it might be an idea to *pipe* the
output to a text reader like ``less``
(`here <http://mercurial.selenic.com/wiki/PagerExtension>`_ is a more
permanent solution):

::

     hg log | less

You can also see the latest changes online
`here <http://code.google.com/p/evennia/source/list>`_.

Resetting your database
-----------------------

Should you ever want to start over completely from scratch, there is no
need to re-download Evennia or anything like that. You just need to
clear your database. Once you are done, you just rebuild it from scratch
as described in step 2 of the `Getting Started
guide <GettingStarted.html>`_.

If you run the default ``SQlite3`` database (to change this you need to
edit your ``settings.py`` file), the database is actually just a normal
file in ``game/`` called ``evennia.db3``. Simply delete that file -
that's it.

Regardless of which database system you use, you can reset your database
via ``game/manage.py``. Since Evennia consists of many separate
components you need to clear the data from all of them:

::

     python manage.py reset server objects players scripts comms help web auth 

Django also offers an easy way to start the database's own management
should we want more direct control:

::

     python manage.py dbshell 

In e.g. MySQL you can then do something like this (assuming your MySQL
database is named "Evennia":

::

    mysql> DROP DATABASE Evennia; 
    mysql> exit

A Note on Schema Migration
--------------------------

If and when an Evennia update modifies the database *schema* (that is,
the under-the-hood details as to how data is stored in the database),
you must update your existing database correspondingly to match the
change. If you don't, the updated Evennia will complain that it cannot
read the database properly. Whereas schema changes should become more
and more rare as Evennia matures, it may still happen from time to time.

One way to handle this is to apply the changes manually to your database
using the database's command line. This often means adding/removing new
tables or fields as well as possibly convert existing data to match what
the new Evennia version expects. It should be quite obvious that this
quickly becomes cumbersome and error-prone. If your database doesn't
contain anything critical yet it's probably easiest to simply reset it
and start over rather than to bother converting.

Enter `South <http://south.aeracode.org/>`_. South keeps track of
changes in the database schema and applies them automatically for you.
Basically, whenever the schema changes we also distribute small files
called "migrations" with the source. Those tell South exactly how to
repeat that change so you don't have to do so manually.

Using South is optional, but if you do install it, Evennia *will* use
South automatically. See the correct section of
`GettingStarted <GettingStarted.html>`_ on how to install South and the
slightly different way to start a clean database server when South is
used (you have to give the ``mange.py migrate`` command as well as
``manage.py syncdb``).

Once you have a database ready and using South, you work as normal.
Whenever a new Evennia update tells you that the database schema has
changed (check ``hg log`` after you pulled the latest stuff, or read the
online list), you go to ``game/`` and run this command:

::

     python manage.py migrate

This will convert your database to the new schema and you should be set
to go.
