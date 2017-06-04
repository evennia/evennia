"""
This file is meant for when you want to share your game dir with
others but don't want to share all details of your specific game
or local server setup. The settings in this file will override those
in settings.py and is in .gitignore by default.

A good guideline when sharing your game dir is that you want your
game to run correctly also without this file and only use this
to override your public, shared settings.

"""

# The secret key is randomly seeded upon creation. It is used to sign
# Django's cookies and should not be publicly known. It should also
# generally not be changed once people have registered with the game
# since it will invalidate their existing sessions.
SECRET_KEY = {secret_key}
