"""
Aetos Web Client.

A genre-agnostic graphical webclient framework for Evennia. Aetos replaces the
stock webclient GUI while leaving Evennia's transport layer (`evennia.js` and the
Portal websocket) completely untouched.

Aetos is useful on an ordinary Evennia game immediately, and becomes progressively
more capable as a game chooses to expose structured metadata through providers. It
makes no assumptions about genre, combat, magic, character model, map format,
inventory, or resources.

This module exposes the paths a game needs in order to install Aetos. See
`README.md` for the installation snippet.

"""

import os

#: Absolute path to the Aetos template directory.
#:
#: A game inserts this at the front of ``TEMPLATES[0]["DIRS"]`` so that Aetos's
#: ``webclient.html`` is found ahead of the stock one.
#:
#: Note for maintainers: prepending to DIRS is required rather than relying on
#: Django's app-directory loader. Django searches every DIRS entry before any
#: installed app, and stock Evennia always places
#: ``<evennia>/web/templates/webclient`` in DIRS, so an app-level template of the
#: same name can never win. Changing ``WEBCLIENT_TEMPLATE`` does not help either:
#: ``settings_default`` interpolates that value into ``TEMPLATES`` at import time,
#: so reassigning it in a game's settings has no effect on the already-built list.
AETOS_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

#: Absolute path to the Aetos static asset directory.
#:
#: Normally unused: registering Aetos in ``INSTALLED_APPS`` lets Django's
#: ``AppDirectoriesFinder`` discover these assets automatically. It is exposed for
#: games that have customised ``STATICFILES_FINDERS`` and disabled that finder.
AETOS_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
