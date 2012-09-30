Setting up a coding environment with version control
====================================================

Version control software allows you to easily backtrack changes to your
code, help with sharing your development efforts and more. Even if you
are not contributing to Evennia itself, but is "just" developing your
own game, having a version control system in place is a good idea. If
you want more info, start with the wikipedia article about it
`here <http://en.wikipedia.org/wiki/Version_control>`_. Note that this
page deals with commands in the Linux operating system. Details may vary
for other systems.

Note: This is only one suggested way to use Mercurial by using separate
local clones. You could set up any number of different workflows if it
suited you better. See `here <http://mercurial.selenic.com/guide/>`_ for
some more examples.

Using Mercurial
===============

`Mercurial <http://mercurial.selenic.com/>`_ (abbreviated as ``hg``
after the chemical symbol for mercury) is a version control system
written mainly in Python. It's available for all major platforms.

First, identify to mercurial by creating a new file ``.hgrc`` in your
home directory and put the following content in it:

::

    [ui]
    username = MyName <myemail@mail.com>

You can put a nickname here too if you want. This is just so the system
knows how to credit new revisions.

Setting up
----------

We will here assume you are downloading Evennia for the first time. We
will set up a simple environment for hacking your game in. In the end it
will look like this:

::

     evennia/
         evennia-main
         evennia-mygame     

Create a new folder ``evennia`` and clone Evennia into it as
``evennia-main``:

::

     hg clone https://code.google.com/p/evennia/ evennia-main

A new folder ``evennia-main`` has appeared. In it you will find the
entire Evennia source repository, including all its commit history -
it's really a full copy of what's available on the web.

We'll let ``evennia-main`` only contain the "clean" Evennia install -
it's a good debugging tool to tell you if a bug you find is due to your
changes or also visible in the core server. We'll develop our game in
another repository instead:

::

     hg clone evennia-main evennia-mygame

This will create a new repository ``evennia-mygame`` on your machine. In
this directory you now code away, adding and editing things to your
heart's content to make your dream game.

Example work flow
-----------------

First we make sure our copy of Evennia is up-to-date. Go to
``evennia-main``:

::

     cd evennia-main 
     hg pull

Mercurial goes online and gets the latest Evennia revision from the
central repository, merging it automatically into your repository. It
will tell you that you need to ``update`` to incoorporate the latest
changes. Do so.

::

     hg update

So ``evennia-main`` is now up-to-date. If you want, you can review the
changes and make sure things work as they should. Finally go to
``evennia-mygame`` and pull the changes into that as well.

::

     
     cd ../evennia-mygame 
     hg commit                 # (only if you had any changes)
     hg pull ../evennia-main
     hg update 

You can now continue to hack away in ``evennia-mygame`` to build your
game. Maybe you define new commands, economic systems, create batchfiles
or what have you. If you create any new files, you must tell Mercurial
to track them by using the ``add`` command:

::

     hg add <filename(s)>

Check the current status of the version control with

::

     hg status

If you don't get any return value, you haven't made any changes since
last commit. Otherwise you will get a list of modified files.

It's usually a good idea to commit your changes often - it's fast and
only local - you will never commit anything online. This gives you a
"save" snapshot of your work that you can get back to.

::

     hg commit

This will open a text editor where you can add a message detailing your
changes. These are the messages you see in the Evennia update/log list.
If you don't want to use the editor you can set the message right away
with the ``-m`` flag:

::

     hg commit -m "This should fix the bug Sarah talked about."

If you did changes that you wish you hadn't, you can easily get rid of
everything since your latest commit:

::

     hg revert --all

Instead of ``--all`` you can also choose to revert individual files.

You can view the full log of committed changes with

::

     hg log

See the Mercurial manuals for learning more about useful day-to-day
commands, and special situations such as dealing with text collisions
etc.

Sharing your code with the world
================================

The most common case of this is when you have fixed an Evennia bug and
want to make the fix available to Evennia maintainers. But you can also
share your work with other people on your game-development team if you
aren't worried about the changes being publicly visible.

Let's take the example of debugging Evennia. Go online and create an
"online clone" of Evennia as described `here <Contributing.html>`_. Pull
this repo to your local machine -- so if your clone is named
``my-evennia-fixes``, you do something like this:

::

    hg clone https://<yourname>@code.google.com/r/my-evennia-fixes evennia-fixes

You will now have a new folder ``evennia-fixes``. Let's assume we want
to use this to push bug fixes to Evennia. It works like any other
mercurial repository except you also have push-rights to your online
clone from it. When working, you'd first update it to the latest
upstream Evennia version:

::

     cd evennia-main
     hg pull 
     hg update    
     cd ../evennia-fixes
     hg pull ../evennia-main
     hg update 

Now you fix things in ``evennia-fixes``. Commit your changes as
described above. Make sure to make clear and descriptive commit messages
so it's easy to see what you intended. You can do any number of commits
as you work. Once you are at a stage where you want to show what you did
to the world, you push all the so-far committed changes to your online
clone:

::

     hg push

(You'd next need to tell Evennia devs that they should merge your
brilliant changes into Evennia proper. Create a new
`Issue <https://code.google.com/p/evennia/issues/list>`_ of type *Merge
Request*, informing them of this.)

Apart from supporting Evennia itself you can have any number of online
clones for different purposes, such as sharing game code or collaborate
on solutions. Just pull stuff from whichever relevant local repository
you have (like ``evennia-mygame``) and push to a suitably named online
clone so people can get to it.

Sharing your code only with a small coding team
===============================================

Creating a publicly visible online clone might not be what you want for
all parts of your development process - you may prefer a more private
venue when sharing your revolutionary work with your team.

An online hosting provider offering private repositories is probably
your best bet. For example, if all your contributors are registered on
`BitBucket <https://bitbucket.org/>`_, that service offers free
"private" repositories that you could use for this.

An alternative simple way to share your work with a limited number of
people is to use mercurial's own simple webserver and let them connect
directly to your machine:

::

     cd evennia-mygame
     hg serve -p 8500

(the port was changed because the default port is 8000 and that is
normally used by Evennia's own webserver). Find out the IP address of
your machine visible to the net (make sure you know your firewall setup
etc). Your collaborators will then be able to first review the changes
in their browser:

::

     firefox http://192.168.178.100:8500

and pull if they like what they see:

::

     hg pull http://192.168.178.100:8500

See `here <http://mercurial.selenic.com/wiki/hgserve>`_ for more
information on using ``hg serve``.

Mercurial's in-built webserver is *very* simplistic and not particularly
robust. It only allows one connection at a time, lacks authorization and
doesn't even allow your collaborators to ``push`` data to you (there is
nothing stopping them to set up a server of their own so you can pull
from them though).
