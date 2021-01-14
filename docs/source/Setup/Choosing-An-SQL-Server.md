# Choosing An SQL Server


This page gives an overview of the supported SQL databases as well as instructions on install:

 - SQLite3 (default)
 - PostgreSQL
 - MySQL / MariaDB

Since Evennia uses [Django](http://djangoproject.com), most of our notes are based off of what we
know from the community and their documentation. While the information below may be useful, you can
always find the most up-to-date and "correct" information at Django's [Notes about supported
Databases](http://docs.djangoproject.com/en/dev/ref/databases/#ref-databases) page.

## SQLite3

[SQLite3](https://sqlite.org/) is a light weight single-file database. It is our default database
and Evennia will set this up for you automatically if you give no other options. SQLite stores the
database in a single file (`mygame/server/evennia.db3`). This means it's very easy to reset this
database - just delete (or move) that `evennia.db3` file and run `evennia migrate` again! No server
process is needed and the administrative overhead and resource consumption is tiny. It is also very
fast since it's run in-memory. For the vast majority of Evennia installs it will probably be all
that's ever needed.

SQLite will generally be much faster than MySQL/PostgreSQL but its performance comes with two
drawbacks:

* SQLite [ignores length constraints by design](https://www.sqlite.org/faq.html#q9); it is possible
to store very large strings and numbers in fields that technically should not accept them. This is
not something you will notice; your game will read and write them and function normally, but this
*can* create some data migration problems requiring careful thought if you do need to change
databases later.
* SQLite can scale well to storage of millions of objects, but if you end up with a thundering herd
of users trying to access your MUD and web site at the same time, or you find yourself writing long-
running functions to update large numbers of objects on a live game, either will yield errors and
interference. SQLite does not work reliably with multiple concurrent threads or processes accessing
its records. This has to do with file-locking clashes of the database file. So for a production
server making heavy use of process- or thread pools (or when using a third-party webserver like
Apache), a proper database is a more appropriate choice.

### Install of SQlite3

This is installed and configured as part of Evennia. The database file is created as
`mygame/server/evennia.db3` when you run

    evennia migrate

without changing any database options. An optional requirement is the `sqlite3` client program -
this is required if you want to inspect the database data manually. A shortcut for using it with the
evennia database is `evennia dbshell`. Linux users should look for the `sqlite3` package for their
distro while Mac/Windows should get the [sqlite-tools package from this
page](https://sqlite.org/download.html).

To inspect the default Evennia database (once it's been created), go to your game dir and do 

```bash
    sqlite3 server/evennia.db3
    # or 
    evennia dbshell
```

This will bring you into the sqlite command line. Use `.help` for instructions and `.quit` to exit.
See [here](https://gist.github.com/vincent178/10889334) for a cheat-sheet of commands.

## PostgreSQL

[PostgreSQL](https://www.postgresql.org/) is an open-source database engine, recommended by Django.
While not as fast as SQLite for normal usage, it will scale better than SQLite, especially if your
game has an very large database and/or extensive web presence through a separate server process.

### Install and initial setup of PostgreSQL 

First, install the posgresql server. Version `9.6` is tested with Evennia. Packages are readily
available for all distributions. You need to also get the `psql` client (this is called `postgresql-
client` on debian-derived systems). Windows/Mac users can [find what they need on the postgresql
download page](https://www.postgresql.org/download/). You should be setting up a password for your
database-superuser (always called `postgres`) when you install.

For interaction with Evennia you need to also install `psycopg2` to your Evennia install (`pip
install psycopg2-binary` in your virtualenv). This acts as the python bridge to the database server.

Next, start the postgres client:

```bash
    psql -U postgres --password
```
> :warning: **Warning:** With the `--password` argument, Postgres should prompt you for a password.
If it won't, replace that with `-p yourpassword` instead. Do not use the `-p` argument unless you
have to since the resulting command, and your password, will be logged in the shell history.

This will open a console to the postgres service using the psql client. 

On the psql command line: 

```sql
CREATE USER evennia WITH PASSWORD 'somepassword';
CREATE DATABASE evennia;

-- Postgres-specific optimizations
-- https://docs.djangoproject.com/en/dev/ref/databases/#optimizing-postgresql-s-configuration
ALTER ROLE evennia SET client_encoding TO 'utf8';
ALTER ROLE evennia SET default_transaction_isolation TO 'read committed';
ALTER ROLE evennia SET timezone TO 'UTC';

GRANT ALL PRIVILEGES ON DATABASE evennia TO evennia;
-- Other useful commands: 
--  \l       (list all databases and permissions)
--  \q       (exit)

```
[Here](https://gist.github.com/Kartones/dd3ff5ec5ea238d4c546) is a cheat-sheet for psql commands.

We create a database user 'evennia' and a new database named `evennia` (you can call them whatever
you want though). We then grant the 'evennia' user full privileges to the new database so it can
read/write etc to it.
If you in the future wanted to completely wipe the database, an easy way to do is to log in as the
`postgres` superuser again, then do `DROP DATABASE evennia;`, then `CREATE` and `GRANT` steps above
again to recreate the database and grant privileges.

### Evennia PostgreSQL configuration

Edit `mygame/server/conf/secret_settings.py and add the following section: 

```python
#
# PostgreSQL Database Configuration
#
DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'evennia',
            'USER': 'evennia',
            'PASSWORD': 'somepassword',
            'HOST': 'localhost',
            'PORT': ''    # use default
        }}
```

If you used some other name for the database and user, enter those instead. Run

    evennia migrate

to populate your database. Should you ever want to inspect the database directly you can from now on
also use

    evennia dbshell

as a shortcut to get into the postgres command line for the right database and user.

With the database setup you should now be able to start start Evennia normally with your new
database.

### Advanced Usage (Remote Server)
> :warning: **Warning:** The example below is for a server within a private
network that is not open to the Internet.  Be sure to understand the details
before making any changes to an Internet accessible server.

The above discussion is for hosting a local server.  In certain configurations
it may make sense host the database on a remote server.  One example case is
where code development may be done on multiple machines by multiple users.  In
this configuration, a local data base (such as SQLite3) is not feasible
since all the machines and developers do not have access to the file.

Choose a remote machine to host the database and PostgreSQl server.  Follow
the instructions [above](#install-and-initial-setup-of-postgresql) on that
server.  Depending on distribution, PostgreSQL will only accept connections on
the local machine (localhost).  In order to enable remote access two files
need to be changed.

First, determine which cluster is running your database.  Use `pg_lscluster`:
```bash
$ pg_lsclusters
Ver Cluster Port Status Owner    Data directory              Log file
12  main    5432 online postgres /var/lib/postgresql/12/main /var/log/postgresql/postgresql-12-main.log
```

Next, edit the database's `postgresql.conf`.  This is found on Ubuntu systems
in `/etc/postgresql/<ver>/<cluster>`, where `<ver>` and `<cluster>` are
what are reported in the `pg_lscluster` output.  So, for the above example,
the file is `/etc/postgresql/12/main/postgresql.conf`.

In this file, look for the line with `listen_addresses`.  For example:
```
listen_address = 'localhost'    # What IP address(es) to listen on;
                                # comma-separated list of addresses;
                                # defaults to 'localhost'; use '*' for all
```
> :warning: **Warning:** Misconfiguring the wrong cluster may cause problems
with existing clusters.

Also, note the line with `port =` and keep the port number in mind.

Set `listen_addresses` to `'*'`.  This permits postgresql to accept connections
on any interface.

> :warning: **Warning:** Setting `listen_addresses` to `'*'` opens a port on
all interfaces.  If your server has access to the Internet, ensure your
firewall is configured appropriately to limit access to this port as necessary.
(You may also list explicit addresses and subnets to listen.  See the
postgresql documentation for more details.)

Finally, modify the `pg_hba.conf` (in the same directory as `postgresql.conf`).
Look for a line with:
```
# IPv4 local connections:
host    all             all             127.0.0.1/32            md5
```
Add a line with:
```
host    all             all             0.0.0.0/0               md5
```
> :warning: **Warning:** This permits incoming connections from *all* IPs.  See the PosgreSQL documentation on how to limit this.

Now, restart your cluster:
```bash
$ pg_ctlcluster 12 main restart
```

Finally, update the database settings in your Evennia secret_settings.py (as
described [above](#evennia-postgresql-configuration) modifying `SERVER` and
`PORT` to match your server.

Now your Evennia installation should be able to connect and talk with a remote
server.

## MySQL / MariaDB

[MySQL](https://www.mysql.com/) is a commonly used proprietary database system, on par with
PostgreSQL. There is an open-source alternative called [MariaDB](https://mariadb.org/) that mimics
all functionality and command syntax of the former. So this section covers both.

### Installing and initial setup of MySQL/MariaDB

First, install and setup MariaDB or MySQL for your specific server. Linux users should look for the
`mysql-server` or `mariadb-server` packages for their respective distributions. Windows/Mac users
will find what they need from the [MySQL downloads](https://www.mysql.com/downloads/) or [MariaDB
downloads](https://mariadb.org/download/) pages. You also need the respective database clients
(`mysql`, `mariadb-client`), so you can setup the database itself. When you install the server you
should usually be asked to set up the database root user and password.

You will finally also need a Python interface to allow Evennia to talk to the database. Django
recommends the  `mysqlclient` one. Install this into the evennia virtualenv with `pip install
mysqlclient`.

Start the database client (this is named the same for both mysql and mariadb):

```bash
mysql -u root -p
```

You should get to enter your database root password (set this up when you installed the database
server).

Inside the database client interface:

```sql
CREATE USER 'evennia'@'localhost' IDENTIFIED BY 'somepassword';
CREATE DATABASE evennia;
ALTER DATABASE `evennia` CHARACTER SET utf8; -- note that it's `evennia` with back-ticks, not
quotes!
GRANT ALL PRIVILEGES ON evennia.* TO 'evennia'@'localhost';
FLUSH PRIVILEGES;
-- use 'exit' to quit client
```
[Here](https://gist.github.com/hofmannsven/9164408) is a mysql command cheat sheet. 

Above we created a new local user and database (we called both 'evennia' here, you can name them
what you prefer). We set the character set to `utf8` to avoid an issue with prefix character length
that can pop up on some installs otherwise. Next we grant the 'evennia' user all privileges on the
`evennia` database and make sure the privileges are applied. Exiting the client brings us back to
the normal terminal/console.

> Note: If you are not using MySQL for anything else you might consider granting the 'evennia' user
full privileges with `GRANT ALL PRIVILEGES ON *.* TO 'evennia'@'localhost';`. If you do, it means
you can use `evennia dbshell` later to connect to mysql, drop your database and re-create it as a
way of easy reset. Without this extra privilege you will be able to drop the database but not re-
create it without first switching to the database-root user.

## Add MySQL configuration to Evennia

To tell Evennia to use your new database you need to edit `mygame/server/conf/settings.py` (or
`secret_settings.py` if you don't want your db info passed around on git repositories).

> Note: The Django documentation suggests using an external `db.cnf` or other external conf-
formatted file. Evennia users have however found that this leads to problems (see e.g. [issue
#1184](https://git.io/vQdiN)). To avoid trouble we recommend you simply put the configuration in
your settings as below.

```python
    #
    # MySQL Database Configuration
    #
    DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.mysql',
           'NAME': 'evennia', 
           'USER': 'evennia', 
           'PASSWORD': 'somepassword', 
           'HOST': 'localhost',  # or an IP Address that your DB is hosted on
           'PORT': '', # use default port
       }
    }
```
Change this to fit your database setup. Next, run:

    evennia migrate

to populate your database. Should you ever want to inspect the database directly you can from now on
also use

    evennia dbshell

as a shortcut to get into the postgres command line for the right database and user.

With the database setup you should now be able to start start Evennia normally with your new
database.

## Others

No testing has been performed with Oracle, but it is also supported through Django. There are
community maintained drivers for [MS SQL](http://code.google.com/p/django-mssql/) and possibly a few
others. If you try other databases out, consider expanding this page with instructions.
