Using Version Control to collaboratively manage and develop a game
==================================================================

*TODO: This page does not yet deal much with the specifics of access
control and protocols used when allowing access to a remove repository.
The example commands also lack proper testing!*

Using modern `version control
software <http://en.wikipedia.org/wiki/Version_control>`_ is a powerful
way for a small development team to collaborate on a MUD project. Not
only will it help you keep track of your changes (and undo bad things
you do), it will also help combine the efforts of many people into one
joint place.

Evennia uses version control in the form of the program Subversion (SVN)
to manage the entire project. It allows multiple coders to contribute
without getting in each other's way. The same mechanic would work just
as well on the next level - with several people collaborating to build
and code a MUD.

This page uses the Python-based
`Bazaar <http://bazaar.canonical.com/en/>`_ version control system as an
example of how to manage your MUD project. There are many other options
though, notably *GIT* or *Mercurial* are worth checking out if Bazaar is
not your thing. We use Bazaar's command-line interface, but Bazaar also
has a full graphical GUI called *Bazaar Explorer* that might make it
easier for newbies to get their head around the concept of version
control. We also cannot go into much detail here, please refer to the
very good Bazaar manuals for more help.

Premise
-------

Let's say you are the admin/owner of a new MUD initiative, based on
Evennia. The whole project will primarily be hosted on your computer.
You are doing this with a few good friends that will help you implement
the actual game system. You also have a few Builders/Coders of varying
skill to help with creating the game world. Apart from building through
their MUD clients, you also want them to be able to submit
build-batchfiles, small code snippets, custom typeclasses and scripts --
without giving them full access to your custom-coded game source.

First you need to set up a `development environment for a single
developer <BazaarDevel.html>`_. That link will also teach you the basics
of using Bazaar. Return here when you are done.

You should by this point have a Bazaar repository *evennia* containing
two branches, ``evennia-trunk`` and ``evennia-mygame``.

Collaborating with trusted coders
---------------------------------

There are many ways to make your code base available to your fellow
administrators/coders.

Branching remotely
~~~~~~~~~~~~~~~~~~

The absolutely easiest way is to have them use Bazaar to simply branch
your ``evennia-mygame`` branch as if it was any other branch. To do this
they need to set up their own repository first with

``bzr init-repo``

Then they branch normally, but over the net:

``bzr branch sftp://url.to.your.computer/evennia-mygame myworkcopy``

(This example uses sftp, but which protocol is used need to be setup and
agreed on. You also need to check so you don't have a firewall blocking
that protocol. The `Bazaar branching
manual <http://doc.bazaar.canonical.com/bzr.2.2/en/user-guide/branching%3Ci%3Ea%3C/i%3Eproject.html>`_
gives a lot more info.)

This will create their very own copy of the branch named ``myworkcopy``,
which they can work on as if it was their own. They can commit changes
to it etc without affecting you. To keep their branches up-to-date
against your branch they need to do a *pull*:

``bzr pull sftp://url.to.your.computer/evennia-mygame``

When they are ready to merge back their changes into your branch, they
need to do a *push*:

``bzr push sftp://url.to.your.computer/evennia-mygame``

SVN-like checkout
~~~~~~~~~~~~~~~~~

Another variant is to make a separate branch for your development
effort, and make this a *checkin branch*. Let's call this branch
*evennia-share*:

``bzr branch evennia-mygame evennia-share``

So far this is the same as ``evennia-mygame``. With the *bind* command
you make this branch act as a centralized, SVN-like repository:

``bzr bind evennia-share``

From now on, people now use ``commit`` and ``update`` from this branch,
and use ``checkout`` to retrieve their personal copy. In fact, users and
contributors can relate to this in the same way you deal with the main
Evennia repository, by setting up equivalents to ``evennia-trunk`` and
``evennia-mygame``. You merge to and from it as usual.

Collaborating with limited access
---------------------------------

Not everyone should (or need) to download your entire customized
codebase (the contents of ``evennia-mygame``) just because they
volunteered to build a region of your game, or is scripting a new
object. And whereas some building can surely happen on-line through MUD
commands, the power of Evennia lies in its Python scripting abilities.
This means them sending you files of code one way or another. Using
e-mail or other communication methods works, but can quickly be a hassle
with many files of different versions.

There are many ways to resolve this with version control, the easiest
might be to simply set aside an isolated place for them to upload their
data to you.

You could have one branch for all builders (so they could collaborate
amongst themselves), or create a completely independent branch for each
builder:

``bzr init anna-builds``

``bzr init peter-builds``

You could for example copy example files / builder instructions etc in
there as needed (``cp`` is a Linux/Unix command, use whatever method is
suitable in your OS): ``cp instructions.txt anna-builds``

``bzr add anna-builds/instructions.txt``

``bzr commit``

You could also *bind* this branch

``bzr bind anna-builds``

so the builder in the future can simply use ``commit`` and ``update`` to
get things in and out of their respective upload area (they'd probably
not mind that they upload to your machine every time they make a
commit).

You can in this way manually inspect submitted files before copying them
into the main branch as desired, using ``bzr add`` to have Bazaar track
them.

.. figure:: http://b.imagehost.org/0824/bazaar_repo2.png
   :align: center
   :alt: 

