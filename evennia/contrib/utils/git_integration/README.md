# In-game Git Integration

Contribution by helpme (2022)

A module to integrate a stripped-down version of git within the game, allowing developers to view their git status, change branches, and pull updated code of both their local mygame repo and Evennia core. After a successful pull or checkout, the git command will reload the game: Manual restarts may be required to to apply certain changes that would impact persistent scripts etc. 

Once the contrib is set up, integrating remote changes is as simple as entering the following into your game:

```
git pull
```

The repositories you want to work with, be it only your local mygame repo, only Evennia core, or both, must be git directories for the command to function. If you are only interested in using this to get upstream Evennia changes, only the Evennia repository needs to be a git repository. [Get started with version control here.](https://www.evennia.com/docs/1.0-dev/Coding/Version-Control.html)

## Dependencies

This package requires the dependency "gitpython", a python library used to interact with git repositories. To install, it's easiest to install Evennia's extra requirements:

- Activate your `virtualenv`
- `cd` to the root of the Evennia repository. There should be an `requirements_extra.txt` file here.
- `pip install -r requirements_extra.txt`

## Installation

This utility adds a simple assortment of 'git' commands. Import the module into your commands and add it to your command set to make it available.

Specifically, in `mygame/commands/default_cmdsets.py`:

```python
...
from evennia.contrib.utils.git_integration import GitCmdSet   # <---

class CharacterCmdset(default_cmds.Character_CmdSet):
    ...
    def at_cmdset_creation(self):
        ...
        self.add(GitCmdSet)  # <---

```

Then `reload` to make the git command available.

## Usage

This utility will only work if the directory you wish to work with is a git directory. If they are not, you will be prompted to initiate your directory as a git repository using the following commands in your terminal:

```
git init
git remote add origin 'link to your repository'
```

By default, the git commands are only available to those with Developer permissions and higher. You can change this by overriding the command and setting its locks from "cmd:pperm(Developer)" to the lock of your choice.

The supported commands are:
* git status: An overview of your git repository, which files have been changed locally, and the commit you're on.
* git branch: What branches are available for you to check out.
* git checkout 'branch': Checkout a branch.
* git pull: Pull the latest code from your current branch.

* All of these commands are also available with 'evennia', to serve the same functionality related to your Evennia directory. So:
* git evennia status
* git evennia branch
* git evennia checkout 'branch'
* git evennia pull: Pull the latest Evennia code.

## Settings Used

The utility uses the existing GAME_DIR and EVENNIA_DIR settings from settings.py. You should not need to alter these if you have a standard directory setup, they ought to exist without any setup required from you.