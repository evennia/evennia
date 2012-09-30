Getting Started
===============

This will help you download, install and start Evennia for the first
time.

*Note: You don't need to make anything visible to the 'net in order to
run and test out Evennia. Apart from installing and updating you don't
even need to have an internet connection. Of course you'll probably want
to put your game online once it matures enough, but until then it works
fine to develop and play around completely in the sanctity and isolation
of your local machine.*

Quick start
-----------

For you who are extremely impatient, here's the gist of getting a
vanilla Evennia install running.

#. *Get the pre-requisites (Python, Django, Twisted and Mercurial)*.
#. *Start a command terminal/dos prompt and change directory to where
   you want to have your 'evennia' folder appear*.
#. ``hg clone https://code.google.com/p/evennia/ evennia``
#. *Change directory to evennia/game*.
#. ``python manage.py``
#. ``python manage.py syncdb``
#. ``python manage.py migrate`` (only if using South)
#. ``python evennia.py -i start``

Evennia should now be running and you can connect to it by pointing a
web browser to ``http://localhost:8000`` or a MUD telnet client to
``localhost:4000``.

Read on for more detailed instructions and configurations.

Prerequisites
-------------

As far as operating systems go, any system with Python support should
work.

-  Linux/Unix
-  Windows (2000, XP, Vista, Win7)
-  Mac OSX (>=10.5 recommended)

If you run into problems, or have success running Evennia on another
platform, please let us know.

You'll need the following packages and minimum versions in order to run
Evennia:

-  **`Python <http://www.python.org>`_** (v2.6+, not supporting v3.x)

   -  Windows users are recommended to use
      `ActivePython <http://www.activestate.com/activepython/downloads>`_
      instead.

-  **`Twisted <http://twistedmatrix.com>`_** (v10.0+)

   -  `ZopeInterface <http://www.zope.org/Products/ZopeInterface>`_
      (v3.0+) - usually included in Twisted packages
   -  Windows users might also need
      `pywin32 <http://sourceforge.net/projects/pywin32>`_.

-  **`Django <http://www.djangoproject.com>`_** (v1.3+ or latest dev
   build recommended)

   -  `PIL <http://www.pythonware.com/products/pil>`_ (Python Image
      Library) - often distributed with Django.

To download/update Evennia:

-  **`Mercurial <http://mercurial.selenic.com/>`_**

Optional packages:

-  **`South <http://south.aeracode.org/>`_** (v0.7+)

   -  Optional, but highly recommended. Makes it easy to keep up with
      Evennia updates to the database schema.

-  **`Apache2 <http://httpd.apache.org>`_**

   -  Optional. Only use if you don't want to use Evennia's own threaded
      webserver. Other equivalent web servers with a Python interpreter
      module can also be used.

Installing pre-requisites
~~~~~~~~~~~~~~~~~~~~~~~~~

**All platforms** can set up an *virtual Python environment* and install
Evennia to that. All you need pre-installed is Python. Setup is
described in detail
[`GettingStarted <GettingStarted.html>`_\ #Optional:\ *A\_separate\_installation\_environment\_with\_virtualenv
here]. Windows users will probably want to go the ActivePython way
instead though (see below), there are issues with installing certain
extensions in Windows.*

**Linux** package managers should usually handle all this for you.
Python itself is definitely available through all distributions. On
Debian-derived systems (such as Ubuntu) you can do something like this
(as root) to get all you need:

::

     apt-get install python python-django python-twisted mercurial python-django-south

(Gentoo note: Gentoo (and maybe other distros?) seems to distribute
Twisted in multiple packages. Beyond the main twisted package you will
also need to get at least twisted-conch and twisted-web too).\ **

Few distros actually keep the latest updated security updates (notably
django and twisted) in their repos though. So it might be worth to use
Python's
`easy\_install <http://packages.python.org/distribute/easy_install.html>`_
or the alternative
`pip <http://www.pip-installer.org/en/latest/index.html>`_ to get some
or all of these instead:

::

     easy_install django twisted pil mercurial south

::

     pip install django twisted pil mercurial south

If you already have Python and mercurial, and have downloaded Evennia,
the package comes with a ``requirements.txt`` file. This can be used
with ``pip`` to install the remaining dependencies (possibly useful for
automated build systems):

::

     pip install -r requirements.txt

**Mac** users should be able to get most dependencies through
``easy_install`` or ``pip`` like Linux users do. All interaction is done
from a terminal window. There are some reports that you might need to
get the `Xcode <https://developer.apple.com/xcode/>`_ development system
to install the packages that requires extension compiling. You can also
retrieve the dependencies directly and install them through their native
installers or python setups. Some users have reported problems compiling
the ``PIL`` library on Mac, it's however not strictly required in order
to use Django (it's used for images).

\_Note (June 2012): Some versions of MacOSX does not seem to have a
locale setting out of the box, and this causes a traceback during
database creation. This is a known upstream bug in Django 1.4, described
`here <http://code.google.com/p/evennia/wiki/Quirks#Known_upstream_bugs>`_.
In the bug comments is also described how to add the locale and
circumvent this bug for now. This affects also Unix/Linux systems, but
those usually have the locale set out of the box.

**Windows** users should first and foremost recognize that the Evennia
server is run from the command line, something which some might not be
familiar with (based on the questions we have received). In the Windows
launch menu, just start *All Programs -> Accessories -> command prompt*
and you will get the Windows command line interface. There are plenty of
online tutorials on using the Windows command line, one example is found
`here <http://www.bleepingcomputer.com/tutorials/windows-command-prompt-introduction/>`_.

Windows users may want to install
`ActivePython <http://www.activestate.com/activepython/downloads>`_
instead of the usual Python. Get the 32-bit version (it seems the 64-bit
one won't let you download any packages without paying for a "Business"
license). If ActivePython is installed, you can use
`pypm <http://docs.activestate.com/activepython/2.6/pypm.html>`_ in the
same manner as ``easy_install``/``pip`` above. This *greatly* simplifies
getting started on Windows since that platform is by default missing
many of the sane developer systems that Linux users take for granted.

After installing ActivePython you may need to restart the terminal/DOS
window to make the pypm command available on the command line:

::

     pypm install Django Twisted PIL Mercurial South

This installs everything you need in one go.

Windows users not using ActivePython or virtual environments will have
to manually download and install the packages in turn (including their
own dependencies in the list above). Most have normal Windows
installers, but in some cases you'll need to know how to use the Windows
command prompt to execute python install scripts (it's usually not
harder than running ``python setup.py install`` from the downloaded
package's folder).

Step 1: Obtaining the Server
----------------------------

To download Evennia you need the Mercurial client to grab a copy of the
source.

For command-line Mercurial client users, something like this will do the
trick (first place yourself in a directory where you want a new folder
``evennia`` to be created):

::

     hg clone https://code.google.com/p/evennia/ evennia

(Mercurial is abbreviated ``hg`` since this is the chemical symbol for
mercury).

In the future, you just do

::

     hg pull
     hg update

from your ``evennia/`` directory to obtain the latest updates.

If you use a graphical Mercurial client, use the equivalent buttons to
perform the above operations. See
`here <http://code.google.com/p/evennia/wiki/VersionControl>`_ for more
advanced suggestions to set up a development environment with Mercurial.

Step 2: Setting up the Server
-----------------------------

From within the Evennia ``game`` directory (``evennia/game/``, if you
followed the Mercurial instructions above) type the following to trigger
the automatic creation of an empty ``settings.py`` file.

::

     python manage.py

Your new ``settings.py`` file will just be an empty template initially.
In ``evennia/src/settings_default.py`` you will find the settings that
may be copied/pasted into your ``settings.py`` to override the defaults.
This will be the case if you want to adjust paths or use something other
than the default SQLite3 database engine. You *never* want to modify
``settings_default.py`` directly - as the server is developed, this file
might be overwritten with new versions and features.

If you would like to use something other than the default SQLite setup
(which works "out of the box"), you'll need to copy the ``DATABASE_*``
variables from ``settings_defaults.py`` and paste them to
``settings.py``, making your modifications there.

*Note that the settings.py file is in fact a normal python module which
imports the default settings. This means that all variables have been
set to default values by the time you get to change things. So to
customize a particular variable you have to copy&paste it to your
settings file - and you have to do so also for variables that depend on
that variable (if any), or the dependent variables will remain at the
default values.*

Finally, enter the following command in a terminal or shell to create
the database file (in the case of SQLite3) and populate the database
with the standard tables and values:

::

     python manage.py syncdb

You should be asked for a superuser username, email, and password. Make
**sure** you create a superuser here when asked, this becomes your login
name for the superuser account ``#1`` in game. After this you will see a
lot of spammy install messages. If all goes well, you're ready to
continue to the next step. If not, look at the error messages and
double-check your ``settings.py`` file.

If you installed ``South`` for database schema migrations, you will then
need to do this:

::

     python manage.py migrate

This will migrate the server to the latest version. If you don't use
``South``, migrations will not be used and your server will already be
at the latest version (but your existing database might have to be
manually edited to match eventual future schema changes that we do).

Step 3: Starting and Stopping the Server
----------------------------------------

To start the server, make sure you're in the ``evennia/game`` directory
and execute ``evennia.py`` like this:

::

     python evennia.py -i start

This starts the server and portal. The ``-i`` flag means that the server
starts in *interactive mode*, as a foreground process. You will see
debug/log messages directly in the terminal window instead of logging
them to a file.

To stop Evennia, do:

::

     python evennia.py stop

See `Running
Evennia <https://code.google.com/p/evennia/wiki/StartStopReload>`_ for
more advanced options on controlling Evennia's processes.

Step 4: Connecting to the server
--------------------------------

The Evennia server is now up and running. You should be able to login
with any mud client or telnet client using the email address and
password you specified when syncing the database. If you are just
testing the server out on your local machine, the server name will most
likely be ``localhost`` whereas the port used by default is ``4000``.

If the defaults are not changed, Evennia will also start its own
Twisted-based web server on port 8000. Point your web browser to
``http://localhost:8000/``. The *admin interface* allows you to edit the
game database online and you can connect directly to the game by use of
the ajax web client.

Welcome to Evennia! Why not try `building
something <BuildingQuickstart.html>`_ next?

Optional: A separate installation environment with virtualenv
=============================================================

Apart from installing the packages and versions as above, you can also
set up a very easy self-contained Evennia install using the
`virtualenv <http://pypi.python.org/pypi/virtualenv>`_ program. If you
are unsure how to get it, just grab the
`virtualenv.py <https://raw.github.com/pypa/virtualenv/master/virtualenv.py>`_
file from that page and run it directly in the terminal with
``python virtualenv.py``.

Virtualenv sets aside a folder on your harddrive as a stand-alone Python
environment. It should work both on Linux/Unix and Windows. First,
install Python as normal, then get virtualenv and install it so you can
run it from the command line. This is an example for setting up Evennia
in an isolated new folder *mudenv*:

::

    python virtualenv mudenv --no-site-packages

Or, if you grabbed ``virtualenv.py`` and is running it directly:

::

    python virtualenv.py mudenv --no-site-packages

Followed by

::

    cd mudenv

Now we should be in our new directory *mudenv*. Next we activate the
virtual environment in here.

::

    # for Linux/Unix:
    source bin/activate
    # for Windows:
    <path_to_this_place>\Scripts\activate.bat

The virtual environment within our *mudenv* folder is now active. Next
we get all the requirements with *pip*, which is included with
virtualenv:

::

    pip install django twisted pil mercurial south

The difference from the normal install described earlier is that these
installed packages are *only* localized to the virtual environment, they
do not affect the normal versions of programs you run in the rest of
your system. So you could for example experiment with bleeding-edge,
unstable libraries or go back to older versions without having to worry
about messing up other things. It's also very easy to uninstall the
whole thing in one go - just delete your ``mudenv`` folder.

You can now refer to **Step 1** above and continue on from there to
install Evennia into *mudenv*. In the future, just go into the folder
and activate it before starting or working with Evennia.
