# Coding using Version Control

[Version control](https://en.wikipedia.org/wiki/Version_control) allows you to track changes to your code. You can save 'snapshots' of your progress which means you can roll back undo things easily. Version control also allows you to easily back up your code to an online _repository_ such as Github. It also allows you to collaborate with others on the same code without clashing or worry about who changed what. 

```{sidebar} Do it!
It's _strongly_ recommended that you [put your game folder under version control](#putting-your-game-dir-under-version-control). Using git is is also the way to contribue to Evennia itself.
```

Evennia uses the most commonly used version control system, [Git](https://git-scm.com/) .  For additional help on using Git, please refer to the [Official GitHub documentation](https://help.github.com/articles/set-up-git#platform-all).

## Setting up Git

- **Fedora Linux**

        yum install git-core

- **Debian Linux** _(Ubuntu, Linux Mint, etc.)_

        apt-get install git

- **Windows**: It is recommended to use [Git for Windows](https://gitforwindows.org/).
- **Mac**:  Mac platforms offer two methods for installation, one via MacPorts, which you can find out about [here](https://git-scm.com/book/en/Getting-Started-Installing-Git#Installing-on-Mac), or you can use the [Git OSX Installer](https://sourceforge.net/projects/git-osx-installer/).

> You can find expanded instructions for installation [here](https://git-scm.com/book/en/Getting-Started-Installing-Git).

```{sidebar} Git user nickname
If you ever make your code available online (or contribute to Evennia), your name will be visible to those reading the code-commit history. So if you are not comfortable with using your real, full name online, put a nickname (or your github handler) here.
```
To avoid a common issue later, you will need to set a couple of settings; first you will need to tell Git your username, followed by your e-mail address, so that when you commit code later you will be properly credited. 


1. Set the default name for git to use when you commit:

        git config --global user.name "Your Name Here"

2. Set the default email for git to use when you commit:

        git config --global user.email "your_email@example.com"

> To get a running start with Git, here's [a good YouTube talk about it](https://www.youtube.com/watch?v=1ffBJ4sVUb4#t=1m58s). It's a bit long but it will help you understand the underlying ideas behind GIT (which in turn makes it a lot more intuitive to use).

## Common Git commands 

```{sidebar} Git repository
This is just a fancy name for the folder you have designated to be under version control. We will make your `mygame` game folder into such a repository. The Evennia code  is also in a (separate) git repository.
```
Git can be controlled via a GUI. But it's often easier to use the base terminal/console commands, since it makes it clear if something goes wrong. 

All these actions need to be done from inside the _git repository_ . 

Git may seem daunting at first. But when working with git, you'll be using the same 2-3 commands 99% of the time. And you can make git _aliases_ to have them be even easier to remember.  


### `git init`

This initializes a folder/directory on your drive as a 'git repository'

    git init .

The `.` means to apply to the current directory. If you are inside `mygame`, this makes your game dir into a git repository. That's all there is to it, really. You only need to do this once.

### `git add` 

    git add <file> 

This tells Git to start to _track_ the file under version control. You need to do this when you create a new file. You can also add all files in your current directory: 

    git add . 

Or 

    git add *

All files in the current directory are now tracked by Git. You only need to do this once for every file you want to track. 

### `git commit`

    git commit -a -m "This is the initial commit"

This _commits_ your changes. It stores a snapshot of all (`-a`) your code at the current time, adding a message `-m` so you know what you did. Later you can _check out_ your code the way it was at a given time.  The message is mandatory and you will thank yourself later if write clear and descriptive log messages. If you don't add `-m`, a text editor opens for you to write the message instead.

The `git commit` is something you'll be using all the time, so it can be useful to make a _git alias_ for it: 

    git config --global alias.cma 'commit -a -m'

After you've run this, you can commit much simpler, like this: 

    git cma "This is the initial commit"

Much easier to remember! 

### `git status`, `git diff` and `git log`


    git status -s 

This gives a short (`-s`) of the files that changes since your last `git commit`. 

    git diff --word-diff`

This shows exactly what changed in each file since you last made a `git commit`. The `--word-diff`  option means it will mark if a single word changed on a line. 

    git log

This shows the log of all `commits` done. Each log will show you who made the change, the  commit-message and a unique _hash_ (like `ba214f12ab12e123...`) that uniquely describes that commit. 

You can make the `log` command more succinct with some more options: 

    ls=log --pretty=format:%C(green)%h\ %C(yellow)[%ad]%Cred%d\ %Creset%s%Cblue\ [%an] --decorate --date=relative

This adds coloration and another fancy effects (use `git help log` to see what they mean).

Let's add aliases: 

    git config --global alias.st 'status -s'
    git config --global alias.df 'diff --word-diff'
    git config --global alias.ls 'log --pretty=format:%C(green)%h\ %C(yellow)[%ad]%Cred%d\ %Creset%s%Cblue\ [%an] --decorate --date=relative'

You can now use the much shorter

    git st    # short status
    git dif   # diff with word-marking
    git ls    # log with pretty formatting

for these useful functions.

### `git branch`, `checkout` and `merge`

Git allows you to work with _branches_. These are separate development paths your code may take, completely separate from each other. You can later _merge_ the code from a branch back into another branch. Evennia's `master` and `develop` branches are examples of this.

    git branch -b branchaname 

This creates a new branch, exactly identical to the branch you were on.  It also moves you to that branch.

    git branch -D branchname 

Deletes a branch.

    git branch 

Shows all your branches, marking which one you are currently on.

    git checkout branchname 

This checks out another branch. As long as you are in a branch all `git commit`s will commit the code to that branch only.

    git checkout .

This checks out your _current branch_ and has the effect of throwing away all your changes since your last commit. This is like undoing what you did since the last save point.

    git checkout b2342bc21c124

This checks out a particular _commit_, identified by the hash you find with `git log`. This open a 'temporary branch' where the  code is as it was when you made this commit. As an example, you can use this to check where a bug was introduced. Check out an existing branch to go back to your normal timeline, or use `git branch -b newbranch` to break this code off into a new branch you can continue working from. 

    git merge branchname

This _merges_ the code from `branchname` into the branch you are currently in. Doing so may lead to _merge conflicts_ if the same code changed in different ways in the two branches. See [how to resolve merge conflicts in git](https://phoenixnap.com/kb/how-to-resolve-merge-conflicts-in-git) for more help.

### `git glone`, `git push` and `git pull`

All of these other commands have dealt with code only sitting in your local repository-folder. These commands instead allows you to exchange code with a _remote_ repository - usually one that is online (like on github). 

> How you actually set up a remote repository is described [in the next section](#pushing-your-code-online).

    git clone repository/path

This copies the remote repository to your current location. If you used the [Git installation instructions](../Setup/Installation-Git.md) to install Evennia, this is what you used to get your local copy of the Evennia repository. 

    git pull

Once you cloned or otherwise set up  a remote repository, using `git pull` will re-sync the remote with what you have locally. If what you download clashes with local changes, git will force you to `git commit` your changes before you can continue with `git pull`.

    git push 

This uploads your local changes _of your current branch_ to the same-named branch on the remote repository. To be able to do this you must have write-permissions to the remote repository.

### Other git commands 

There are _many_ other git commands. Read up on them online: 

    git reflog 

Shows hashes of individual git actions. This allows you to go back in the git event history itself. 


    git reset 
    
Force reset a branch to an earlier commit. This could throw away some history, so be careful.

    git grep -n -I -i <query>

Quickly search for a phrase/text in all files tracked by git. Very useful to quickly find where things are. Set up an alias `git gr` with

```
git config --global alias.gr 'grep -n -I -i'
```

## Putting your game dir under version control

This makes use  of the git commands listed in the previous section.

```{sidebar} git aliases
If you set up the git aliases for commands suggested in the previous section, you can use them instead!
```

    cd mygame 
    git init . 
    git add *
    git commit -a -m "Initial commit"

    
Your game-dir is now tracked by git.

You will notice that some files are not covered by your git version control, notably your secret-settings file (`mygame/server/conf/secret_settings.py`) and your sqlite3 database file `mygame/server/evennia.db3`. This is intentional and controlled from the file  `mygame/.gitignore`. 

```{warning}
You should *never* put your sqlite3 database file into git by removing its entry
in `.gitignore`. GIT is for backing up your code, not your database. That way
lies madness and a good chance you'll confuse yourself. Make one mistake or local change and after a few commits and reverts you will have lost track of what is in your database or not. If you want to backup your SQlite3 database, do so by simply copying the database file to a safe location.
```

### Pushing your code online

So far your code is only located on your private machine. A good idea is to back it up online. The easiest way to do this is to `git push` it to your own remote repository on GitHub. So for this you need a (free) Github account.

If you don't want your code to be publicly visible, Github also allows you set up a _private_ repository, only visible to you.


```{note} 
Github's defaults have changed to calling the primary branch 'main' rather than 'master'. While Evennia still uses 'master' branch (and this is what we refer to below), you can use either name for your personal primary branch - they are equivalent.
```

Create a new, empty repository on Github. [Github explains how here](https://help.github.com/articles/create-a-repo/) . _Don't_ allow it to add a README, license etc, that will just clash with what we upload later.

```{sidebar} Origin
We label the remote repository 'origin'. This is the git default and means we won't need to specify it explicitly later.
```

Make sure you are in your local game dir (previously initialized as a git repo).

    git remote add origin <github URL>

This tells Git that there is a remote repository at `<github URL>`. See the  github docs as to which URL to use. Verify that the remote works with `git remote -v`

Now we push to the remote (labeled 'origin' which is the default):

    git push

Depending on how you set up your authentication with github, you may be asked to enter your github username and password. If you set up SSH authentication, this command will just work.

You use `git push` to upload your local changes so the remote repository is in sync with your local one. If you edited a file online using the Github editor (or a collaborator pushed code), you use `git pull` to sync in the other direction.

## Contributing to Evennia 

If you want to help contributing to Evennia you must do so by _forking_ - making your own remote copy of the Evennia repository on Github. So for this, you need a (free) Github account. Doing so is a completely separate process from [putting your game dir under version control](#putting-your-game-dir-under-version-control) (which you should also do!).

At the top right of [the evennia github page](https://github.com/evennia/evennia), click the "Fork" button:

![fork button](../_static/images/fork_button.png)

This will create a new online fork Evennia under your github account. 

The fork only exists online as of yet. In a terminal, `cd` to  the folder you wish to develop in. This folder should _not_ be your game dir, nor the place you cloned Evennia into if you used the [Git installation](../Setup/Installation-Git.md).

From this directory run the following command:

    git clone https://github.com/yourusername/evennia.git evennia

This will download your fork to your computer. It creates a new folder `evennia/` at your current location. If you installed Evennia using the [Git installation](../Setup/Installation-Git.md), this folder will be identical in content to the `evennia` folder you cloned during that installation. The difference is that this repo is connected to your remote fork and not to the 'original' _upstream_ Evennia.

When we cloned our fork, git automatically set up a 'remote repository' labeled `origin` pointing to it. So if we do `git pull` and `git push`, we'll push to our fork. 

We now want to add a second remote repository linked to the original Evennia repo. We will label this remote repository `upstream`: 

    cd evennia
    git remote add upstream https://github.com/evennia/evennia.git

If you also want to access Evennia's `develop` branch (the bleeding edge development) do the following:

    git fetch upstream develop
    git checkout develop

Use

    git checkout master
    git checkout develop

to switch between the branches. 

To pull the latest from upstream Evennia, just checkout the branch you want and do 

    git pull upstream

```{sidebar} Pushing to upstream
You can't do `git push upstream` unless you have write-access to the upstream Evennia repository. So there is no risk of you accidentally pushing your own code into the main, public repository.
```

### Fixing an Evennia bug or feature

This should be done in your fork of Evennia. You should _always_ do this in a _separate git branch_ based off the Evennia branch you want to improve. 

    git checkout master (or develop)
    git branch - b myfixbranch

Now fix whatever needs fixing. Abide by the [Evennia code style](./Evennia-Code-Style.md). You can `git commit` commit your changes along the way as normal.

Upstream Evennia is not standing still, so you want to make sure that your work is up-to-date with upstream changes. Make sure to first commit your `myfixbranch` changes, then

    git checkout master (or develop)
    git pull upstream 
    git checkout myfixbranch
    git merge master (or develop)

Up to this point your `myfixbranch` branch only exists on your local computer. No
one else can see it.  

    git push

This will automatically create a matching `myfixbranch` in your forked version of Evennia and push to it. On github you will be able to see appear it in the `branches` dropdown. You can keep pushing to your remote `myfixbranch` as much as you like.

Once you feel you have something to share, you need to [create a pull request](https://github.com/evennia/evennia/pulls) (PR): 
This is a formal request for upstream Evennia to adopt and pull your code into the main repository.  
1. Click `New pull request`
2.  Choose `compare across forks`
3. Select your fork from dropdown list of `head repository` repos. Pick the right branch to `compare`.
4. On the Evennia side (to the left) make sure to pick the right `base` branch: If you want to contribute a change to the `develop` branch, you must pick `develop` as the `base`.
5. Then click `Create pull request` and fill in as much information as you can in the form.
6. Optional: Once you saved your PR, you can go into your code (on github) and add some per-line comments; this can help reviewers by explaining complex code or decisions you made. 

Now you just need to wait for your code to be reviewed. Expect to get feedback and be asked to make changes, add more documentation etc. Getting as PR merged can take a few iterations. 

```{sidebar} Not all PRs can merge
While most PRs get merged, Evennia can't **guarantee** that your PR code will be deemed suitable to merge into upstream Evennia. For this reason it's a good idea to check in with the community _before_ you spend a lot of time on a large piece of code (fixing bugs is always a safe bet though!)
```


## Troubleshooting

### Getting 403: Forbidden access

Some users have experienced this on `git push` to their remote repository. They are not asked for username/password (and don't have a ssh key set up). 

Some users have reported that the workaround is to create a file `.netrc` under your home directory and add your github credentials there:

```bash
machine github.com
login <my_github_username>
password <my_github_password>
```