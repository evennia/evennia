Choosing an SQL Server
======================

Since Evennia uses `Django <http://djangoproject.com>`_, most of our
notes are based off of what we know from the community and their
documentation. While the information below may be useful, you can always
find the most up-to-date and "correct" information at Django's `Notes
about supported
Databases <http://docs.djangoproject.com/en/dev/ref/databases/#ref-databases>`_
page.

SQLite
------

This is the default database used, and for the vast majority of Evennia
installs it will probably be more than adequate for a long time. No
server process is needed, the administrative overhead is tiny (as is
resource consumption). The database will appear as a simple file
(``game/evennia.db3``). SQLite is excellent for development and easy
testing. The database is however hampered in speed by not allowing
concurrent reads. For a full production game with many users accessing
the database, a more fully featured database engine (MySQL, Postgres
etc) is probably better.

**Note:** If you run Windows and for some reason need to use a
third-party web server like Apache rather than Evennia's internal web
server, sqlite is probably also not be the best choice. This is due to
the possibility of clashes with file-locking of the database file under
Windows.

Postgres
--------

This is Django's recommended database engine, usable for all sites
aspiring to grow to a larger size. While not as fast as SQLite for
simple purposes, it will scale infinitely better than SQLite, especially
if your game has an extensive web presence.

**Warning:** Postgres has issues with Evennia on some installs at the
moment. "http://code.google.com/p/evennia/issues/detail?id

151">Issue 151 outlines this. If unsure, avoid Postgres for now.

MySQL
-----

MySQL **may** be slightly faster than Postgres depending on your setup
and software versions involved. Older versions of MySQL had some
peculiarities though, so check out Django's `Notes about supported
Databases <http://docs.djangoproject.com/en/dev/ref/databases/#ref-databases>`_
to make sure you use the correct version.

Others
------

No testing has been performed with Oracle, but it is also supported.
There are community maintained drivers for `MS
SQL <http://code.google.com/p/django-mssql/>`_ and possibly a few others
(found via our friend, Google).
