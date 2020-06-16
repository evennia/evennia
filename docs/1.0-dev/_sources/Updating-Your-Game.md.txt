# Updating Your Game


Fortunately, it's extremely easy to keep your Evennia server up-to-date. If you haven't already, see
the [Getting Started guide](Getting-Started) and get everything running.

### Updating with the latest Evennia code changes

Very commonly we make changes to the Evennia code to improve things. There are many ways to get told
when to update: You can subscribe to the RSS feed or manually check up on the feeds from
http://www.evennia.com. You can also simply fetch the latest regularly.

When you're wanting to apply updates, simply `cd` to your cloned `evennia` root directory and type:

     git pull

assuming you've got the command line client. If you're using a graphical client, you will probably
want to navigate to the `evennia` directory and either right click and find your client's pull
function, or use one of the menus (if applicable).

You can review the latest changes with

     git log

or the equivalent in the graphical client. You can also see the latest changes online
[here](https://github.com/evennia/evennia/blob/master/CHANGELOG.md).

You will always need to do `evennia reload` (or `reload` from -in-game) from your game-dir to have
the new code affect your game. If you want to be really sure you should run a full `evennia reboot`
so that both Server and Portal can restart (this will disconnect everyone though, so if you know the
Portal has had no updates you don't have to do that).

### Upgrading Evennia dependencies

On occasion we update the versions of third-party libraries Evennia depend on (or we may add a new
dependency). This will be announced on the mailing list/forum. If you run into errors when starting
Evennia, always make sure you have the latest versions of everything. In some cases, like for
Django, starting the server may also give warning saying that you are using a working, but too-old
version that should not be used in production.

Upgrading `evennia` will automatically fetch all the latest packages that it now need. First `cd` to
your cloned `evennia` folder. Make sure your `virtualenv` is active and use
    
    pip install --upgrade -e . 

Remember the period (`.`) at the end - that applies the upgrade to the current location (your
`evennia` dir).

> The `-e` means that we are _linking_ the evennia sources rather than copying them into the
environment. This means we can most of the time just update the sources (with `git pull`) and see
those changes directly applied to our installed `evennia` package. Without installing/upgrading the
package with `-e`, we would have to remember to upgrade the package every time we downloaded any new
source-code changes.

Follow the upgrade output to make sure it finishes without errors. To check what packages are
currently available in your python environment after the upgrade, use

    pip list  

This will show you the version of all installed packages. The `evennia` package will also show the
location of its source code.

## Migrating the Database Schema

Whenever we change the database layout of Evennia upstream (such as when we add new features) you
will need to *migrate* your existing database. When this happens it will be clearly noted in the
`git log` (it will say something to the effect of "Run migrations"). Database changes will also be
announced on the Evennia [mailing list](https://groups.google.com/forum/#!forum/evennia).

When the database schema changes, you just go to your game folder and run

     evennia migrate

> Hint: If the `evennia` command is not found, you most likely need to activate your
[virtualenv](Glossary#virtualenv).

## Resetting your database

Should you ever want to start over completely from scratch, there is no need to re-download Evennia
or anything like that. You just need to clear your database. Once you are done, you just rebuild it
from scratch as described in [step 2](Getting-Started#step-2-setting-up-your-game) of the [Getting
Started guide](Getting-Started).

First stop a running server with

    evennia stop

If you run the default `SQlite3` database (to change this you need to edit your `settings.py` file),
the database is actually just a normal file in `mygame/server/` called `evennia.db3`. *Simply delete
that file* - that's it. Now run `evennia migrate` to recreate a new, fresh one.

If you run some other database system you can instead flush the database:

    evennia flush

This will empty the database. However, it will not reset the internal counters of the database, so
you will start with higher dbref values. If this is okay, this is all you need.

Django also offers an easy way to start the database's own management should we want more direct
control:

     evennia dbshell

In e.g. MySQL you can then do something like this (assuming your MySQL database is named "Evennia":

    mysql> DROP DATABASE Evennia;
    mysql> exit

> NOTE: Under Windows OS, in order to access SQLite dbshell you need to [download the SQLite
command-line shell program](https://www.sqlite.org/download.html). It's a single executable file
(sqlite3.exe) that you should place in the root of either your MUD folder or Evennia's (it's the
same, in both cases Django will find it).

## More about schema migrations

If and when an Evennia update modifies the database *schema* (that is, the under-the-hood details as
to how data is stored in the database), you must update your existing database correspondingly to
match the change. If you don't, the updated Evennia will complain that it cannot read the database
properly. Whereas schema changes should become more and more rare as Evennia matures, it may still
happen from time to time.

One way one could handle this is to apply the changes manually to your database using the database's
command line. This often means adding/removing new tables or fields as well as possibly convert
existing data to match what the new Evennia version expects. It should be quite obvious that this
quickly becomes cumbersome and error-prone.  If your database doesn't contain anything critical yet
it's probably easiest to simply reset it and start over rather than to bother converting.

Enter *migrations*. Migrations keeps track of changes in the database schema and applies them
automatically for you. Basically, whenever the schema changes we distribute small files called
"migrations" with the source. Those tell the system exactly how to implement the change so you don't
have to do so manually. When a migration has been added we will tell you so on Evennia's mailing
lists and in commit messages -
you then just run `evennia migrate` to be up-to-date again. 