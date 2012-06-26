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
installs it will probably be more than adequate or even the best choice.
No server process is needed, the administrative overhead is tiny (as is
resource consumption). The database will appear as a simple file
(``game/evennia.db3``) and since we run SQLite as an in-memory process
without any socket overhead, it might well be faster than Postgres/MySQL
unless your database is huge.

**Note:** If you for some reason need to use a third-party web server
like Apache rather than Evennia's internal web server, SQLite is
probably not the best choice. This is due to the possibility of clashes
with file-locking when using SQLite from more than one process.

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
