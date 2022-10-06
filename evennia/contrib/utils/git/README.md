# In-game Git Integration

Contribution by helpme (2022)

A module to integrate a stripped-down version of git within the game, allowing developers to keep their evennia version updated, commit code to their git repository, change branches, and pull updated code. After a successful pull or checkout, the git command will reload the game: You may need to restart manually to apply certain changes that would impact persistent scripts etc. 

Once the contrib is set up, integrating remote changes is as simple as entering the following into your game:

```
git pull
```

Of course, your game directory must be a git directory to begin with for this command to function. 

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

This utility will only work if your game and evennia directories are git directories. If they are not, you will be prompted to initiate your directory as a git repository using the following commands in your terminal:

```
git init
git remote add origin [link to your repository]
```

By default, the git commands are only available to those with Developer permissions and higher. You can change this by overriding the command and setting its locks from "cmd:pperm(Developer)" to the lock of your choice.

The supported commands are:
* git status: An overview of your git repository, which files have been changed locally, and the commit you're on.
* git branch: What branches are available for you to check out.
* git checkout 'branch': Checkout a branch.
* git pull: Pull the latest code from your current branch.

* All of these commands are also available with 'evennia', to serve the same functionality related to your evennia directory. So:
* git status evennia
* git branch evennia
* git checkout evennia 'branch'
* git pull evennia: Pull the latest evennia code.

## Settings Used

The utility uses the existing GAME_DIR and EVENNIA_DIR settings from settings.py. You should not need to alter these if you have a standard directory setup, they ought to exist without any setup required from you.