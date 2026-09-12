"""
Constants shared across the Aetos Web Client contrib.

Values here are part of Aetos's public contract with games and clients. Changing
`PROTOCOL_VERSION` is a breaking change and must be accompanied by a documented
migration path.

"""

# Aetos protocol version. Incremented only for breaking wire-format changes.
PROTOCOL_VERSION = 1

# Identifier a client sends in its `aetos_hello` handshake.
CLIENT_NAME = "aetos"

# The template name Evennia's webclient view renders. Aetos supplies its own
# template under this name and wins by being placed ahead of Evennia's in
# TEMPLATES[0]["DIRS"] (see AETOS_TEMPLATE_DIR in __init__.py).
WEBCLIENT_TEMPLATE_NAME = "webclient.html"

# Aetos's own base template. Aetos deliberately does not extend Evennia's
# `webclient/base.html`, which loads eight third-party CDN resources for the
# stock GUI that Aetos does not use. See templates/aetos/base.html.
AETOS_BASE_TEMPLATE = "aetos/base.html"

# Evennia's transport library, loaded unmodified from Evennia's own static files.
EVENNIA_TRANSPORT_SCRIPT = "webclient/js/evennia.js"

# Version stamped onto static asset URLs.
#
# Bumped whenever a shipped asset changes. Browsers cache static files, so
# without this a player returning after a game upgrades Aetos can keep running
# the previous JavaScript against the new server -- which presents as features
# mysteriously missing rather than as a caching problem.
ASSET_VERSION = "1.0.0"
