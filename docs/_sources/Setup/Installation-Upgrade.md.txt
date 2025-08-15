# Upgrading an existing installation

This is relevant to you already having code in an older Evennia version. If you are new, or don't have much code yet, it may be easier to just start fresh with the [Installation](./Installation.md) instructions and copy over things manually.

## Evennia v0.9.5 to 1.0+

### Upgrading the Evennia library

Prior to 1.0, all Evennia installs were [Git-installs](./Installation-Git.md). These instructions assume that you already have a cloned `evennia` repo, and use a virtualenv (best practices). 

- Make sure to stop Evennia 0.9.5 entirely with `evennia stop` from your game dir.
- `deactivate` to leave your active virtualenv.
- Delete the old virtualenv `evenv` folder, or rename it (in case you want to keep using 0.9.5 for a while).
- `cd` into your `evennia/` root folder (you want to be where you see the `docs/` and  `bin/` directories as well as a nested `evennia/` folder)
- `git pull`
- `git checkout main` (instead of `master` which was used for `0.9.5`)

From here on, proceed with the [Git Installation](./Installation-Git.md), except skip cloning Evennia (since you already have the repo). Note that you can also follow the normal [pip install](./Installation.md) if you don't need or want to use git to track bleeding edge changes nor want to be able to help contribute to Evennia itself. 

### Upgrading your game dir

If you don't have anything you want to keep in your existing game dir, you can just start a new one using the normal [install instructions](./Installation.md). If you want to keep/convert your existing game dir, continue below.

- First, make a _backup_ of your exising game dir! If you use version control, make sure to commit your current state.
- `cd` to your existing 0.9.5-based game folder (like `mygame`).
- If you have changed `mygame/web`, _rename_ the folder to `web_0.9.5`. If you didn't change anything (or don't have anything you want to keep), you can _delete_ it entirely.
- Copy `evennia/evennia/game_template/web` to `mygame/` (e.g. using `cp -Rf` or a file manager). This new `web` folder _replaces the old one_ and has a very different structure.
- It's possible you need to replace/comment out import and calls to the deprecated [`django.conf.urls`](https://docs.djangoproject.com/en/4.1/ref/urls/#url). The new way to call it is [available here](https://docs.djangoproject.com/en/4.0/ref/urls/#django.urls.re_path).
- Run `evennia migrate`  - note that it's normal to see some warnings here, _don't_ run `makemigrations` even if the system asks you to.
- Run `evennia start`

If you made extensive work in your game dir, you may well find that you need to do some (hopefully minor) changes to your code before it will start with Evennia 1.0. Some important points:

- The `evennia/contrib/` folder changed structure - there are now categorized sub-folders, so you have to update your imports.
- Any `web` changes need to be moved back from your backup into the new structure of `web/` manually.
- See the [Evennia 1.0 Changelog](../Coding/Changelog.md) for all changes.
