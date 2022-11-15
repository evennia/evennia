# Version Control

Version control software allows you to track the changes you make to your code, as well as being
able to easily backtrack these changes, share your development efforts and more.

It's strongly recommended that you put your game code under version control. Version
control is also the way to contribue to Evennia itself.

For an introduction to the concept, start with the Wikipedia article
[here](https://en.wikipedia.org/wiki/Version_control). Evennia uses the version
control system [Git](https://git-scm.com/) and this is what will be covered
henceforth. Note that this page primarily shows commands for Linux, but the
syntax should be the same for Windows and Mac.

For more help on using Git, please refer to the [Official GitHub
documentation](https://help.github.com/articles/set-up-git#platform-all).

## Setting up Git

You can find expanded instructions for
installation [here](https://git-scm.com/book/en/Getting-Started-Installing-Git).

### Step 1: Install Git

- **Fedora Linux**

        yum install git-core

- **Debian Linux** _(Ubuntu, Linux Mint, etc.)_

        apt-get install git

- **Windows**: It is recommended to use [Git for Windows](https://gitforwindows.org/).
- **Mac**:  Mac platforms offer two methods for installation, one via MacPorts, which you can find
out about [here](https://git-scm.com/book/en/Getting-Started-Installing-Git#Installing-on-Mac), or
you can use the [Git OSX Installer](https://sourceforge.net/projects/git-osx-installer/).

### Step 2: Define user/e-mail Settings for Git

To avoid a common issue later, you will need to set a couple of settings; first you will need to
tell Git your username, followed by your e-mail address, so that when you commit code later you will
be properly credited.

> Note that your commit information will be visible to everyone if you ever contribute to Evennia or
use an online service like github to host your code. So if you are not comfortable with using your
real, full name online, put a nickname here.

1. Set the default name for git to use when you commit:

        git config --global user.name "Your Name Here"

2. Set the default email for git to use when you commit:

        git config --global user.email "your_email@example.com"


## Putting your game folder under version control

> Note: The game folder's version control is completely separate from Evennia's repository.

After you have set up your game you will have created a new folder to host your particular game
(let's call this folder `mygame` for now).

This folder is *not* under version control at this point.

    git init mygame

Your mygame folder is now ready for version control! Add all the content and make a first
commit:

    cd mygame
    git add *
    git commit -a -m "Initial commit"

In turn these commands:
- Move us into the `mygame` folder
- Tell `git` that everything `*` means everything) in this folder should be put
  under version control.
- _Commit_ all (`-a`) those newly added files to git and add a message `-m` so you remember
  what you did at this point. Doing a commit is like saving a snapshot of the
  current state of everything.

Read on for details!

### Tracking files

When working on your code or fix bugs in your local branches you may end up creating new files. If
you do you must tell Git to track them by using the add command.

    git add <filename>

You only need to do this once per file.

    git status

will show if you have any modified, added or otherwise changed files. Some
files, like database files, logs and temporary PID files are usually *not*
tracked in version control. These should either not show up or have a question
mark in front of them.

```{note}
You will notice that some files are not covered by your git version control,
notably your settings file (`mygame/server/conf/settings.py`) and your sqlite3
database file `mygame/server/evennia.db3`. What is auto-ignored by is controlled
by the hidden file `mygame/.gitignore`. Evennia creates this file as part of
the creation of your game directory. Everything matched in this file will be
ignored by git. If you want to, for example, include your settings file for
collaborators to access, remove that entry in `.gitignore`.
```

```{warning}
You should *never* put your sqlite3 database file into git by removing its entry
in `.gitignore`. GIT is for backing up your code, not your database. That way
lies madness and a good chance you'll confuse yourself so that after a few
commits and reverts don't know what is in your database or not. If you want to
backup your database, do so by simply copying the file on your hard drive to a
backup-name.
```

### Committing your Code

_Committing_ your code means storing the current snapshot of your code within
git. This creates a "save point" or "history" of your development process. You
can later jump back and forth in your history, for example to figure out just
when a bug was introduced or see what results the code used to produce compared
to now. Or just wiping everything since the last commit, if you did something
stupid.

It's usually a good idea to commit your changes often. Committing is fast and
local only - you will never commit anything online at this point. To commit your
changes, use

    git commit --all

Also `-a` works. This will open a text editor for you to describe your change.
Be brief but informative in your message - you'll appreciate it later.  When you
save and close the editor, the commit will be saved. You can create the message
directly with

    git commit -a -m "This fixes a bug in the combat code."


### Changing your mind

If you have non-committed changes that you realize you want to throw away, you
'check out' the file you want - this will re-load it from the last committed
state:

    git checkout <file_to_revert>
    git checkout foo/bar/dummy.py

If you want to revert _all_ changes you did since last commit, do

    git checkout .

(that is, add a single `.` at the end).

### Pushing your code online

So far your code is only located on your private machine. A good idea is to back
it up online. The easiest way to do this is to push it to your own remote
repository on GitHub.

```{important}
Just to avoid confusion, be aware that Github's documentation has changed to
calling the primary branch 'main' rather than 'master'. While Evennia still
uses 'master' branch (and this is what we refer to below), you can use either
name for your personal primary branch - they are equivalent.
```

1. Make sure you have your game directory setup under git version control as
   described in the previous section. Make sure to commit any changes you did.
2. Create a new, empty repository on Github. Github explains how
   [here](https://help.github.com/articles/create-a-repo/) (do *not* "Initialize
   the repository with a README" or else you'll create unrelated histories).
3. From your local game dir, do `git remote add origin <github URL>` where
   `<github URL>` is the URL to your online repo. This tells your game dir that
   it should be pushing to the remote online dir.
4. `git remote -v` to verify the online dir.
5. `git push origin master` (or `git push origin main`) now pushes your game dir
   online so you can see it on github.com.

You can commit your work locally (`git commit --all -m "Make a change that
..."`) as many times as you want. When you want to push those changes to your
online repo, you do `git push`. You can also `git clone <url_to_online_repo>`
from your online repo to somewhere else (like your production server) and
henceforth do `git pull` to update that to the latest thing you pushed.

Note that GitHub's repos are, by default publicly visible by all. Creating a
publicly visible online clone might not be what you want for all parts of your
development process - you may prefer a more private venue when sharing your
revolutionary work with your team. If that's the case you can change your
repository to "Private" in the github settings. Then your code will only be
visible to those you specifically grant access.


## Forking Evennia

This helps you set up an online *fork* of the main Evennia repository so you can
easily commit fixes and help with upstream development. You can do this step
also if you _didn't_ put your game dir under version control like in the
previous section - the evennia repo and your game dir repo are completely
separate.

### Step 1: Fork the evennia/master repository

> Before proceeding with the following step, make sure you have registered and
> created an account on [GitHub.com](https://github.com/). This is necessary in order to create a fork
of Evennia's master repository, and to push your commits to your fork either for
yourself or for contributing to
Evennia.

A _fork_ is a clone of the master repository that you can make your own commits
and changes to. At the top of [this page](https://github.com/evennia/evennia),
click the "Fork" button, as it appears below.
![](https://github-images.s3.amazonaws.com/help/bootcamp/Bootcamp-Fork.png)

### Step 2: Clone your online fork of Evennia

The fork only exists online as of yet. In a terminal, change your directory to
the folder you wish to develop in. From this directory run the following
command:

    git clone https://github.com/yourusername/evennia.git

This will download your fork to your computer. It creates a new folder
`evennia/` at your current location.

### Step 3: Configure remotes

Your Evennia-fork is now separate from upstream, 'official' Evennia. You will
want to set it up so that you can easily sync our updates and changes to your
fork.

We do this by setting up a new _remote_. We actually already have one remote,
that is our own github form of Evennia. This got created when you cloned the
repo and defaults to being called `origin`.

We will now create a new remote called `upstream`.

    cd evennia
    git remote add upstream https://github.com/evennia/evennia.git

This adds a remote to the main evennia repo.

If you also want to access Evennia's `develop` branch (the bleeding edge
development) do the following:

    git fetch upstream develop
    git checkout develop

Use
    git checkout master
    git checkout develop

to switch between the branches. If you want to contribute a fix, ask first which
branch to use. Normally `master` is for bug fixes and `develop` is for new
features, but late in the development of a new Evennia version, all changes
often go into `develop`.


## Working with your Evennia fork

_Branches_ are stand-alone editions of the same code. You make a commit to a
branch. Switching to a branch will change the code on-disk. You can easily
make a new branch off a parent branch, and then merge it back into the same
branch later (or throw it away). This is a very common way to work on new
features in safety and isolation.

### Updating to latest Evennia

When Evennia's official repository updates, first make sure to commit all your
changes to your branch and then checkout the "clean" master branch:

    git checkout master
    git pull upstream master

Or, if you are working against Evennia's development branch:

    git checkout develop
    git pull upstream develop

The `pull` command will fetch all the changes from the "upstream" remote and
merge it into your local master/develop branch. It should now be a perfect copy
of the latest Evennia changes.

### Making changes

As a rule of thumb you should _never_ work directly in Evennia's `master` or
`develop` branches. Instead you make a _new_ branch off the branch you want
and change _that_.

    git checkout master (or develop)
    check checkout -b strange_bug

You now have a new branch `strange_bug` that is an exact replica of the branch you
had checked out when you created it. Here you can now make your own
modifications.

    git branches

will show you which branches are available and which one you are currently
using. Use `git checkout <branch>` to move between them, but remember to commit
your changes before you do.

You often want to make sure also your work-branch has the latest upstream
changes. To do this, you need to first update your copy of the
`master`/`develop` branch and then _merge_ those changes into your work branch.
Make sure you have committed everything first!

    git commit -a -m "My latest changes ..."   # on your strange_bug branch
    git checkout master (or develop)
    git pull upstream develop
    git checkout strange_bug
    git merge master (or develop)

If everything went well, your `strange_bug` branch will now have the latest version
of Evennia merged with whatever changes you have done.

Now work away on your code and commit with reasonable commit messages

    git commit -a -m "Fixed the issue in ..."
    git commit -a -m "Adding unit tests. This resolves #123."

Use

    git diff

to see what you changed since last commit, and

    git log

to see past commits (including those made by Evennia upstream, remember that
your branch is a copy of the upstream one, including its history!)

## Sharing your Evennia fixes on Github

Up to this point your `strange_bug` branch only exists on your local computer. No
one else can see it.  If you want a copy of this branch to also appear in your
online fork on GitHub, make sure to have checked out your "myfixes" branch and
then run the following:

    git push -u origin strange_bug

You only need to do this once, the `-u` makes this the default push-location. In
the future, you can just push things online like this:

    git push

### Troubleshooting

If you hadn't setup a public key on GitHub or aren't asked for a
username/password, you might get an error `403: Forbidden Access` at this stage.
In that case, some users have reported that the workaround is to create a file
`.netrc` under your home directory and add your github credentials there:

```bash
machine github.com
login <my_github_username>
password <my_github_password>
```

## Making an Evennia Pull Request

If you think that the fixes you did in your `strange_bug` branch should be a
part of the regular Evennia, you should create a _Pull Request_ (PR). This is a
call for the Evennia maintainer to pull your change into an upstream branch.

> It is wise to make separate branches for every fix or series of fixes you want
to contribute.

Assuming you have followed the instructions above and have pushed your changes
online, [create a pull request](https://github.com/evennia/evennia/pulls) and
follow the instructions. Make sure to specifically select your `strange_bug`
branch to be the source of the merge and use the branch you based that branch
off (`master` or `develop`) as the target.

Evennia developers will then be able to examine your request and merge it if
it's deemed suitable. They may also come back with feedback and request you do
some changes.

Once approved and merged, your change will now be available in the upstream
branch:

    git checkout master (or develope)
    git pull upstream master (or develop)

Since your changes are now in upstream, your local `strange_bug` branch is now
superfluous and should be deleted:

    git branch -D strange_bug

You can also safely delete your online `strange_bug` branch in your fork
(you can do this from the PR page on github).


## GIT tips and tricks

Some of the GIT commands can feel a little long and clunky if you need to do them often. Luckily you
can create aliases for those. Here are some useful commands to run:


```
# git st
# - view brief status info
git config --global alias.st 'status -s'
```

Above, you only need to ever enter the `git config ...` command once - you have then added the new
alias. Afterwards, just do `git st` to get status info. All the examples below follow the same
template.

```
# git cl
# - clone a repository
git config --global alias.cl clone
```

```
# git cma "commit message"
# - commit all changes without opening editor for message
git config --global alias.cma 'commit -a -m'
```

```
# git ca
# - amend text to your latest commit message
git config --global alias.ca 'commit --amend'
```

```
# git fl
# - file log; shows diffs of files in latest commits
git config --global alias.fl 'log -u'
```

```
# git co [branchname]
# - checkout
git config --global alias.co checkout
```

```
# git br <branchname>
# - create branch
git config --global alias.br branch
```

```
# git ls
# - view log tree
git config --global alias.ls 'log --pretty=format:"%C(green)%h\ %C(yellow)[%ad]%Cred%d\
%Creset%s%Cblue\ [%cn]" --decorate --date=relative --graph'
```

```
# git diff
# - show current uncommitted changes
git config --global alias.diff 'diff --word-diff'
```

```
# git grep <query>
# - search (grep) codebase for a search criterion
git config --global alias.grep 'grep -Ii'
```

To get a further feel for GIT there is also [a good YouTube talk about it](https://www.youtube.com/watch?v=1ffBJ4sVUb4#t=1m58s) - it's a bit long but it will help you understand the underlying ideas behind GIT
(which in turn makes it a lot more intuitive to use).
