Choosing an SQL Server
======================

Since Evennia uses `Django <http://djangoproject.com>`_, most of our
notes are based off of what we know from the community and their
documentation. While the information below may be useful, you can always
find the most up-to-date and "correct" information at Django's `Notes
about supported
Databases <http://docs.djangoproject.com/en/dev/ref/databases/#ref-databases>`_
page.

SQLite3
-------

This is the default database used, and for the vast majority of Evennia
installs it will probably be more than adequate. It's definitely
recommended for most of your development. No server process is needed,
the administrative overhead is tiny (as is resource consumption). The
database will appear as a simple file (``game/evennia.db3``) and since
we run SQLite as an in-memory process without any socket overhead, it
might well be faster than Postgres/MySQL unless your database is huge.

The drawback with SQLite3 is that it does not work very well will
multiple concurrent threads or processes. This has to do with
file-locking clashes of the database file. So for a production server
making heavy use of process- or threadpools (or when using a third-party
webserver like Apache), a more full-featured database may be the better
choice.

Postgres
--------

This is Django's recommended database engine, While not as fast as
SQLite for normal usage, it will scale better than SQLite, especially if
your game has an very large database and/or extensive web presence
through a separate server process.

**Warning:** Postgres has issues with Evennia on some installs at the
moment. `Issue
151 <http://code.google.com/p/evennia/issues/detail?id=151>`_ outlines
this. If unsure, avoid Postgres for now.

MySQL
-----

MySQL *may* be slightly faster than Postgres depending on your setup and
software versions involved. Older versions of MySQL had some
peculiarities though, so check out Django's `Notes about supported
Databases <http://docs.djangoproject.com/en/dev/ref/databases/#ref-databases>`_
to make sure you use the correct version.

Others
------

No testing has been performed with Oracle, but it is also supported.
There are community maintained drivers for `MS
SQL <http://code.google.com/p/django-mssql/>`_ and possibly a few others
(found via our friend, Google).

Inspecting database data
========================

If you know SQL you can easily get command line access to your database
like this:

::

     python game/gamesrc.py dbshell

This will drop you into the command line interface for your respective
database.

There are also a host of easier graphical interfaces for the various
databases. For SQLite3 we recommend `SQLite
manager <https://addons.mozilla.org/En-us/firefox/addon/sqlite-manager/>`_.
This is a plugin for the
`Firefox <http://www.mozilla.org/en-US/firefox/new/>`_ web browser
making it usable across all operating systems. Just use it to open the
game/evennia.db3 file.
