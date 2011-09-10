Setting up a solo coding environment with version control
=========================================================

*This page deals with working as a lone coder. See also how to use
version control to collaborate with many people on a game
`here <StaffVersionControl.html>`_.*

Version control software allows you to easily backtrack changes to your
code, help to share your development efforts and more. Even if you are
not contributing to Evennia itself, but is "just" developing your own
game using Evennia, having a version control system in place is a good
idea. If you want more info, start with the wikipedia article about it
`here <http://en.wikipedia.org/wiki/Version_control>`_. Note that this
page deals with commands in the Linux operating system. Details may vary
for other systems.

Bazaar and SVN
--------------

Evennia itself uses the *Subversion* (SVN)version control system. This
relatively old version control system lacks some of the more modern
features of later systems, but is universally recognized and easy to
use. Just because we use SVN centrally does not mean that you have to
use it when working with Evennia on your local machine however.

`Bazaar <http://bazaar.canonical.com>`_ (bzr) is a version control
system written entirely in Python. It's available for all major
platforms. It's a more modern system than SVN and is generally easy to
use, also for newbies (other commonly seen systems similar to Bazaar are
GIT and Mercurial). We won't go into the details of what makes Bazaar
different from SVN, there are many texts about this on the internet.
What is important though is that Bazaar interfaces very well with SVN,
by use of a plugin called, *bzr-svn*.

Prerequisites
-------------

Bazaar and bzr-svn are both available from the normal Linux package
managers (see the homepage for how to download for other systems).
Install those first, then give the command ``bzr`` in a terminal to make
sure it's available.

First, identify to bazaar by giving the command
``bzr whoami name <email>``

``bzr whoami Harry Olsson <harry@gmail.com>``

You can put a nickname here too if you want. This is just so the system
knows what to put to identify new revisions.

Setting up for a single developer
---------------------------------

We will here assume you are downloading Evennia for the first time. We
will set up a simple environment for hacking your game in.

Make a new folder on your hard drive, for example named *evennia*.
Outside this folder, give the command

``bzr init-repo evennia``

This sets the ``evennia`` folder up as a Bazaar repository, ready to
use. Enter this folder now. Next we obtain the Evennia server, except we
now use Bazaar to do it and not SVN.

``bzr checkout http://evennia.googlecode.com/svn/trunk/ evennia-trunk``

(Contributors use the contributor URL instead). A new folder
``evennia-trunk`` has appeared in your repository! In it you will find
the entire Evennia source. Working with this folder works almost
identically to how it would work with SVN - you use ``bzr update`` to
get the latest version, contributors use ``bzr commit`` to enter their
changes to the server. Actually coding away in this folder is not ideal
however. As mentioned, doing ``bzr commit`` will (attempt to) push your
changes to the main Evennia repository, which is most often not what you
want when developing your own game. This is where Bazaar kicks in. We
will leave ``evennia-trunk`` be and create a separate *branch* to do our
work in. Change your directory to the root ``evennia`` one, then copy to
a new branch, let's call it ``evennia-mygame``:

``bzr branch evennia-trunk evennia-mygame``

A new folder appeared, containing a copy of the code. ``evennia-mygame``
is where you do all your work. If you do commits in here, they will be
committed locally, not to Evennia central. You now have full version
control on your machine. Updating your work code becomes a simple
two-step process of updating ``evennia-trunk`` and then *merging* those
changes into ``evennia-mygame``. Read on.

Example work process for single developer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

First we make sure our copy of Evennia is up-to-date. Go to
``evennia-trunk``

``bzr update``

Bazaar goes online and gets the latest Evennia revision from the central
repository, merging it automatically into the branch.

So ``evennia-trunk`` is now up-to-date. Go to ``evennia-mygame``.
``bzr merge ../evennia-trunk``

The changes in ``evennia-trunk`` are pulled in and merged with
``evennia-mygame``. You can now continue to hack away in
``evennia-mygame``. Maybe you define new commands, fix bugs, create
batchfiles or what have you. If you create any new files, you must tell
Bazaar to handle them too, using the ``add`` command:

``bzr add <filenames>``

Check the current status of the version control with

``bzr status``

If you don't get any return value, you haven't made any changes since
last commit. Otherwise you will get a list of modified files. "Unknown"
files need to be added with ``add`` before Bazaar can track them.

It's usually a good idea to commit your changes often. This gives you a
snapshot of your work that you can get back to.

``bzr commit``

This will open a text editor where you can add a message detailing your
changes. These are the messages you see in the Evennia update list. If
you don't want to use the editor you can set the message right away with
the ``-m`` flag:

``bzr commit -m "This should fix the bug Sarah talked about."``

If you did changes that you wish you hadn't, you can easily get rid of
everything since your latest commit:

``bzr revert``

You can view the full log of committed changes with

``bzr log``

See the Bazaar manuals for learning more about useful day-to-day
commands, and special situations such as dealing with text collisions
etc.

Evennia Contributor
~~~~~~~~~~~~~~~~~~~

If you are an Evennia contributor, you can also have use of the Bazaar
setup above. The only difference is that you then also have commit
permission to the Evennia main repository.

You can have any number of work branches in your ``evennia`` folder.
Let's say your work branch for fixing Evennia bugs and features is
``evennia-work``. You update and work with this the same way as
``evennia-mygame`` above.

After having committed your latest changes, move to the
``evennia-trunk`` folder.

``bzr update``

This makes sure your local trunk is up-to-date.

``bzr merge ../evennia-work``

This merges your updates into the ``evennia-trunk`` branch.

``bzr commit``

Give the commit message and your changes will be pushed to the central
repository. Done!

.. figure:: http://d.imagehost.org/0452/bazaar_repo1.png
   :align: center
   :alt: 

