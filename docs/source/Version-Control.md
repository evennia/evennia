# Version Control


Version control software allows you to track the changes you make to your code, as well as being able to easily backtrack these changes, share your development efforts and more. Even if you are not contributing to Evennia itself, and only wish to develop your own MU* using Evennia, having a version control system in place is a good idea (and standard coding practice). For an introduction to the concept, start with the Wikipedia article [here](http://en.wikipedia.org/wiki/Version_control). Evennia uses the version control system [Git](https://git-scm.com/) and this is what will be covered henceforth. Note that this page also deals with commands for Linux operating systems, and the steps below may vary for other systems, however where possible links will be provided for alternative instructions.

For more help on using Git, please refer to the [Official GitHub documentation](https://help.github.com/articles/set-up-git#platform-all).

## Setting up Git

If you have gotten Evennia installed, you will have Git already and can skip to **Step 2** below. Otherwise you will need to install Git on your platform. You can find expanded instructions for installation [here](http://git-scm.com/book/en/Getting-Started-Installing-Git).

### Step 1: Install Git

- **Fedora Linux**

        yum install git-core  

- **Debian Linux** _(Ubuntu, Linux Mint, etc.)_ 

        apt-get install git    

- **Windows**: It is recommended to use [Git for Windows](http://msysgit.github.io/). 
- **Mac**:  Mac platforms offer two methods for installation, one via MacPorts, which you can find out about [here](http://git-scm.com/book/en/Getting-Started-Installing-Git#Installing-on-Mac), or you can use the [Git OSX Installer](https://sourceforge.net/projects/git-osx-installer/).
 
### Step 2: Define user/e-mail Settings for Git

To avoid a common issue later, you will need to set a couple of settings; first you will need to tell Git your username, followed by your e-mail address, so that when you commit code later you will be properly credited. 

> Note that your commit information will be visible to everyone if you ever contribute to Evennia or use an online service like github to host your code. So if you are not comfortable with using your real, full name online, put a nickname here.  

1. Set the default name for git to use when you commit:

        git config --global user.name "Your Name Here"

2. Set the default email for git to use when you commit:

        git config --global user.email "your_email@example.com"


## Putting your game folder under version control

> Note: The game folder's version control is completely separate from Evennia's repository. 

After you have set up your game you will have created a new folder to host your particular game (let's call this folder `mygame` for now). 

This folder is *not* under version control at this point. 

    git init mygame

Your mygame folder is now ready for version control! Now add all the content and make a first commit:

    cd mygame
    git add *
    git commit -m "Initial commit"

Read on for help on what these commands do. 


### Tracking files

When working on your code or fix bugs in your local branches you may end up creating new files. If you do you must tell Git to track them by using the add command: 

```
git add <filename>
```

You can check the current status of version control with `git status`.  This will show if you have any modified, added or otherwise changed files. Some files, like database files, logs and temporary PID files are usually *not* tracked in version control. These should either not show up or have a question mark in front of them. 

### Controlling tracking

You will notice that some files are not covered by your git version control, notably your settings file (`mygame/server/conf/settings.py`) and your sqlite3 database file `mygame/server/evennia.db3`. This is controlled by the hidden file `mygame/.gitignore`.  Evennia creates this file as part of the creation of your game directory. Everything matched in this file will be ignored by GIT. If you want to, for example, include your settings file for collaborators to access, remove that entry in `.gitignore`.

> Note: You should *never* put your sqlite3 database file into git by removing its entry in `.gitignore`. GIT is for backing up your code, not your database. That way lies madness and a good chance you'll confuse yourself so that after a few commits and reverts don't know what is in your database or not. If you want to backup your database, do so by simply copying the file on your hard drive to a backup-name.

### Committing your Code

> Committing means storing the current snapshot of your code within git. This creates a "save point" or "history" of your development process. You can later jump back and forth in your history, for example to figure out just when a bug was introduced or see what results the code used to produce compared to now. 

It's usually a good idea to commit your changes often. Committing is fast and local only - you will never commit anything online at this point. To commit your changes, use

```
git commit --all 
```  

This will save all changes you made since last commit. The command will open a text editor where you can add a message detailing the changes you've made. Make it brief but informative. You can see the history of commits with `git log`. If you don't want to use the editor you can set the message directly by using the `-m` flag:

```
git commit --all -m "This fixes a bug in the combat code."  
```

### Changing your mind

If you have non-committed changes that you realize you want to throw away, you can do the following:

```
git checkout <file to revert>
```

This will revert the file to the state it was in at your last `commit`, throwing away the changes you did to it since. It's a good way to make wild experiments without having to remember just what you changed. If you do ` git checkout .` you will throw away _all_ changes since the last commit. 

### Pushing your code online

So far your code is only located on your private machine. A good idea is to back it up online. The easiest way to do this is to push it to your own remote repository on GitHub. 

1. Make sure you have your game directory setup under git version control as described above. Make sure to commit any changes. 
2. Create a new, empty repository on Github. Github explains how [here](https://help.github.com/articles/create-a-repo/) (do *not* "Initialize the repository with a README" or else you'll create unrelated histories). 
3. From your local game dir, do `git remote add origin <github URL>` where `<github URL>` is the URL to your online repo. This tells your game dir that it should be pushing to the remote online dir.
4. `git remote -v` to verify the online dir.
5. `git push origin master` now pushes your game dir online so you can see it on github.com.

You can commit your work locally (`git commit --all -m "Make a change that ..."`) as many times as you want. When you want to push those changes to your online repo, you do `git push`. You can also `git clone <url_to_online_repo>` from your online repo to somewhere else (like your production server) and henceforth do `git pull` to update that to the latest thing you pushed. 

Note that GitHub's repos are, by default publicly visible by all. Creating a publicly visible online clone might not be what you want for all parts of your development process - you may prefer a more private venue when sharing your revolutionary work with your team. If that's the case you can change your repository to "Private" in the github settings. Then your code will only be visible to those you specifically grant access. 


## Forking Evennia

This helps you set up an online *fork* of Evennia so you can easily commit fixes and help with upstream development. 

### Step 1: Fork the evennia/master repository

> Before proceeding with the following step, make sure you have registered and created an account on [GitHub.com](https://github.com/).  This is necessary in order to create a fork of Evennia's master repository, and to push your commits to your fork either for yourself or for contributing to Evennia.

A _fork_ is a clone of the master repository that you can make your own commits and changes to. At the top of [this page](https://github.com/evennia/evennia), click the "Fork" button, as it appears below.  ![](https://github-images.s3.amazonaws.com/help/bootcamp/Bootcamp-Fork.png)

### Step 2: Clone your fork

The fork only exists online as of yet. In a terminal, change your directory to the folder you wish to develop in. From this directory run the following command: 

```
git clone https://github.com/yourusername/evennia.git
```

This will download your fork to your computer. It creates a new folder `evennia/` at your current location.
 
### Step 3: Configure remotes

A _remote_ is a repository stored on another computer, in this case on GitHub's server. When a repository is cloned, it has a default remote called `origin`. This points to your fork on GitHub, not the original repository it was forked from. To easily keep track of the original repository (that is, Evennia's official repository), you need to add another remote. The standard name for this remote is "upstream".

Below we change the active directory to the newly cloned "evennia" directory and then assign the original Evennia repository to a remote called "upstream":

```
cd evennia
git remote add upstream https://github.com/evennia/evennia.git
```

If you also want to access Evennia's `develop` branch (the bleeding edge development branch) do the following:

```
git fetch upstream develop
git checkout develop
```

You should now have the upstream branch available locally. You can use this instead of `master` below if you are contributing new features rather than bug fixes.


## Working with your fork

> A _branch_ is a separate instance of your code. Changes you do to code in a branch does not affect that in other branches (so if you for example add/commit a file to one branch and then switches to another branch, that file will be gone until you switch back to the first branch again). One can switch between branches at will and create as many branches as one needs for a given project. The content of branches can also be merged together or deleted without affecting other branches. This is not only a common way to organize development but also to test features without messing with existing code.

The default _branch_ of git is called the "master" branch. As a rule of thumb, you should *never* make modifications directly to your local copy of the master branch. Rather keep the master clean and only update it by pulling our latest changes to it. Any work you do should instead happen in a local, other branches.

### Making a work branch

```
git checkout -b myfixes
``` 

This command will checkout and automatically create the new branch `myfixes` on your machine. If you stared out in the master branch, *myfixes* will be a perfect copy of the master branch. You can see which branch you are on with `git branch` and change between different branches with `git checkout <branchname>`.

Branches are fast and cheap to create and manage. It is common practice to create a new branch for every bug you want to work on or feature you want to create, then create a *pull request* for that branch to be merged upstream (see below). Not only will this organize your work, it will also make sure that *your* master branch version of Evennia is always exactly in sync with the upstream version's master branch. 

### Updating with upstream changes

When Evennia's official repository updates, first make sure to commit all your changes to your branch and then checkout the "clean" master branch:

```
git commit --all
git checkout master
```

Pull the latest changes from upstream:

```
git pull upstream master
```

This should sync your local master branch with upstream Evennia's master branch. Now we go back to our own work-branch (let's say it's still called "myfixes") and _merge_ the updated master into our branch.

```
git checkout myfixes
git merge master
```

If everything went well, your `myfixes` branch will now have the latest version of Evennia merged with whatever changes you have done.  Use `git log` to see what has changed. You may need to restart the server or run `manage.py migrate` if the database schema changed (this will be seen in the commit log and on the mailing list). See the [Git manuals](http://git-scm.com/documentation) for learning more about useful day-to-day commands, and special situations such as dealing with merge collisions.

## Sharing your Code Publicly

Up to this point your `myfixes` branch only exists on your local computer. No one else can see it. If you want a copy of this branch to also appear in your online fork on GitHub, make sure to have checked out your "myfixes" branch and then run the following:

```
git push -u origin myfixes
```

This will create a new _remote branch_ named "myfixes" in your online repository (which is refered to as "origin" by default); the `-u` flag makes sure to set this to the default push location. Henceforth you can just use `git push` from your myfixes branch to push your changes online. This is a great way to keep your source backed-up and accessible. Remember though that by default your repository will be public so everyone will be able to browse and download your code (same way as you can with Evennia itself). If you want secrecy you can change your repository to "Private" in the Github settings. Note though that if you do, you might have trouble contributing to Evennia (since we can't see the code you want to share). 

*Note: If you hadn't setup a public key on GitHub or aren't asked for a username/password, you might get an error `403: Forbidden Access` at this stage. In that case, some users have reported that the workaround is to create a file `.netrc` under your home directory and add your credentials there:*

```bash
machine github.com
login <my_github_username>
password <my_github_password>
```

## Committing fixes to Evennia

_Contributing_ can mean both bug-fixes or adding new features to Evennia.  Please note that if your change is not already listed and accepted in the [Issue Tracker](https://github.com/evennia/evennia/issues), it is recommended that you first hit the developer mailing list or IRC chat to see beforehand if your feature is deemed suitable to include as a core feature in the engine. When it comes to bug-fixes, other developers may also have good input on how to go about resolving the issue.

To contribute you need to have [forked Evennia](Version-Control#forking-evennia) first. As described above you should do your modification in a separate local branch (not in the master branch). This branch is what you then present to us (as a *Pull request*, PR, see below). We can then merge your change into the upstream master and you then do `git pull` to update master usual. Now that the master is updated with your fixes, you can safely delete your local work branch. Below we describe this work flow.

First update the Evennia master branch to the latest Evennia version:

```
git checkout master
git pull upstream master
```

Next, create a new branch to hold your contribution. Let's call it the "fixing_strange_bug" branch:

```
git checkout -b fixing_strange_bug
```

It is wise to make separate branches for every fix or series of fixes you want to contribute. You are now in your new `fixing_strange_bug` branch. You can list all branches with `git branch` and jump between branches with `git checkout <branchname>`. Code and test things in here, committing as you go:

```
git commit --all -m "Fix strange bug in look command. Resolves #123."
```

You can make multiple commits if you want, depending on your work flow and progress. Make sure to always make clear and descriptive commit messages so it's easy to see what you intended. To refer to, say, issue number 123, write `#123`, it will turn to a link on GitHub. If you include the text "Resolves #123", that issue will be auto-closed on GitHub if your commit gets merged into main Evennia. 

>If you refer to in-game commands that start with `@`(such as `@examine`), please put them in backticks \`, for example \`@examine\`. The reason for this is that GitHub uses `@username` to refer to GitHub users, so if you forget the ticks, any user happening to be named `examine` will get a notification .... 

If you implement multiple separate features/bug-fixes, split them into different branches if they are very different and should be handled as separate PRs. You can do any number of commits to your branch as you work. Once you are at a stage where you want to show the world what you did you might want to consider making it clean for merging into Evennia's master branch by using [git rebase](https://www.git-scm.com/book/en/v2/Git-Branching-Rebasing) (this is not always necessary, and if it sounds too hard, say so and we'll handle it on our end). 

Once you are ready, push your work to your online Evennia fork on github, in a new remote branch:

```
git push -u origin fixing_strange_bug
```

The `-u` flag is only needed the first time - this tells GIT to create a remote branch. If you already created the remote branch earlier, just stand in your `fixing_strange_bug` branch and do `git push`.

Now you should tell the Evennia developers that they should consider merging your brilliant changes into Evennia proper. [Create a pull request](https://github.com/evennia/evennia/pulls) and follow the instructions. Make sure to specifically select your `fixing_strange_bug` branch to be the source of the merge. Evennia developers will then be able to examine your request and merge it if it's deemed suitable. 

Once your changes have been merged into Evennia your local `fixing_strange_bug` can be deleted (since your changes are now available in the "clean" Evennia repository). Do 

```
git branch -D fixing_strange_bug
```

to delete your work branch. Update your master branch (`checkout master` and then `git pull`) and you should get your fix back, now as a part of official Evennia! 


## GIT tips and tricks

Some of the GIT commands can feel a little long and clunky if you need to do them often. Luckily you can create aliases for those. Here are some useful commands to run:


```
# git st 
# - view brief status info
git config --global alias.st 'status -s'
```

Above, you only need to ever enter the `git config ...` command once - you have then added the new alias. Afterwards, just do `git st` to get status info. All the examples below follow the same template. 

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
git config --global alias.ls 'log --pretty=format:"%C(green)%h\ %C(yellow)[%ad]%Cred%d\ %Creset%s%Cblue\ [%cn]" --decorate --date=relative --graph'
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
