Apache Configuration
====================

This is an optional section only relevant for advanced users preferring
to use a third-party web server to power Evennia's front-end. For most
users the in-built Twisted web server should be enough. The in-built
server works out of the box without any extra configuration. Note that
the ajax web client will probably *not* work (at least not without
tweaking) on a third-party web server.

You can run Evennia's web front end with
`apache2 <http://httpd.apache.org/>`_ and
`mod\_wsgi <http://code.google.com/p/modwsgi/>`_. However, there seems
to be no reason why the codebase should not also work with other modern
web servers like nginx/lighttpd + gunicorn, Tornado, uwsgi, etc.

Note that the Apache instructions below might be slightly outdated. If
something is not working right, or you use Evennia with a different
server, please let us know.

SQLite Note
-----------

It's important to note that on Windows, you will be unable to run the
game and your web presence at the same time due to evennia.db3 being
locked while one has it opened. While Linux/Unix will let you run both
concurrently, there **may** be issues with simultaneous read/writes by
the game and the web front-end. The best bet to any game wishing to
power their web presence with Evennia is to use Postgres, MySQL, Oracle,
or any other supported full-blown relational database.

mod\_wsgi Setup
---------------

Install mod\_wsgi
~~~~~~~~~~~~~~~~~

mod\_wsgi is an excellent, secure, and high-performance way to serve
Python projects. Code reloading is a breeze, Python modules are executed
as a user of your choice (which is a great security win), and mod\_wsgi
is easy to set up on most distributions.

For the sake of brevity, this guide will refer you to mod\_wsgi's
`installation
instructions <http://code.google.com/p/modwsgi/wiki/InstallationInstructions>`_
page, as their guides are great. For those that are running Debian or
Ubuntu, you may install the entire stack with the following command:

``sudo aptitude install libapache2-mod-wsgi``

This should install apache2 (if it isn't already), mod\_wsgi, and load
the module. On Fedora or CentOS, you'll do this with ``yum`` and a
similar package name that you'll need to search for. On Windows, you'll
need to download and install apache2 and mod\_wsgi binaries.

Copy and modify the VHOST
~~~~~~~~~~~~~~~~~~~~~~~~~

After mod\_wsgi is installed, copy the
``evennia/game/web/utils/evennia_wsgi_apache.conf`` file to your apache2
vhosts/sites folder. On Debian/Ubuntu, this is
``/etc/apache2/sites-enabled/``. Make your modifications **after**
copying the file there.

Read the comments and change the paths to point to the appropriate
locations within your setup.

Restart/Reload Apache
~~~~~~~~~~~~~~~~~~~~~

You'll then want to reload or restart apache2. On Debian/Ubuntu, this
may be done via:

``sudo /etc/init.d/apache2 restart`` or
``sudo /etc/init.d/apache2 reload``

Enjoy
~~~~~

With any luck, you'll be able to point your browser at your domain or
subdomain that you set up in your vhost and see the nifty default
Evennia webpage. If not, read the hopefully informative error message
and work from there. Questions may be directed to our `Evennia Community
site <http://evennia.com>`_.

A note on code reloading
~~~~~~~~~~~~~~~~~~~~~~~~

If your mod\_wsgi is set up to run on daemon mode (as will be the case
by default on Debian and Ubuntu), you may tell mod\_wsgi to reload by
using the ``touch`` command on
``evennia/game/web/utils/apache_wsgi.conf``. When mod\_wsgi sees that
the file modification time has changed, it will force a code reload. Any
modifications to the code will not be propagated to the live instance of
your site until reloaded.

If you are not running in daemon mode or want to force the issue, simply
restart or reload apache2 to apply your changes.

Further notes and hints:
~~~~~~~~~~~~~~~~~~~~~~~~

If you get strange (and usually uninformative) ``Permission denied``
errors from Apache, make sure that your ``evennia`` directory is located
in a place the webserver may actually access. For example, some Linux
distributions may default to very restrictive access permissions on a
user's ``/home`` directory.

One user commented that they had to add the following to their Apache
config to get things to work. Not confirmed, but worth trying if there
are trouble.

::

    <Directory "/home/<yourname>/evennia/game/web">
                    Options +ExecCGI
                    Allow from all
    </Directory>

