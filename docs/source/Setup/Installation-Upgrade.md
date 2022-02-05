# Upgrading an existing installation

## Evennia v0.9.5 to  1.0

Prior to 1.0, all Evennia installs were [Git-installs](./Installation-Git.md). These instructions
assume that you have a cloned `evennia` repo and use a virtualenv (best practices).

- Make sure to stop Evennia 0.9.5 entirely with `evennia stop`.
- `deactivate` to leave your active virtualenv.
- Make a _backup_ of your entire `mygame` folder, just to be sure! 
- Delete the old `evenv` folder, or rename it (in case you want to keep using 0.9.5 for a while).
- Install Python 3.10 (recommended) or 3.9. Follow the [Git-installation](./Installation-Git.md) for your OS if needed.
- If using virtualenv, make a _new_ one with `python3.10 -m venv evenv`, then activate with `source evenv/bin/activate`
  (linux/mac) or `\evenv\Script\activate` (windows)
- `cd` into your `evennia/` folder (you want to see the `docs/`, `bin/` directories as well as a nested `evennia/` folder)
- **Prior to 1.0 release only** - do `git checkout develop` to switch to the develop branch. After release, this will
  be found on the default master branch.
- `git pull` 
- `pip install -e .`
- If you want the optional extra libs, do `pip install -r requirements_extra.txt`.
- Test that you can run the `evennia` command.

If you don't have anything you want to keep in your existing game dir, you can just start a new onew 
using the normal [install instructions](./Installation.md). If you want to keep/convert your existing 
game dir, continue below. 

- `cd` to your existing 0.9.5-based game folder (like `mygame`.)
- If you have changed `mygame/web`, _rename_ the folder to `web_0.9.5`. If you didn't change anything (or don't have 
anything you want to keep), you can _delete_ it entirely.
- Copy `evennia/evennia/game_template/web` to `mygame/` (e.g. using `cp -Rf` or a file manager). This new `web` folder
replaces the old one and has a very different structure.
- `evennia migrate`
- `evennia start`

If you made extensive work in your game dir, you may well find that you need to do some (hopefully minor) 
changes to your code before it will start with Evennia 1.0. Some important points: 

- The `evennia/contrib/` folder changed structure - there are now categorized sub-folders, so you have to update 
your imports.
- Any `web` changes need to be moved back from your backup into the new structure of `web/` manually.
- See the [Evennia 1.0 Changelog](./Changelog.md) for all changes.