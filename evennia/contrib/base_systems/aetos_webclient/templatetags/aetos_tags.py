"""
Template tags for the Aetos Web Client.

Provides `{% aetos_static %}`, a version-stamping wrapper around Django's
`{% static %}`.

Why this exists: static files are served with caching headers, so after a game
upgrades Evennia (and with it Aetos), a returning player's browser can keep
serving the *previous* Aetos JavaScript against the *new* server. The symptoms
are baffling -- features silently missing, or a protocol mismatch that looks like
a server fault -- and the player has no reason to think of clearing their cache.

Stamping each asset URL with the Aetos version means an upgrade changes the URL,
so browsers fetch the new file without anyone having to know why.

"""

import os

from django import template
from django.conf import settings
from django.templatetags.static import static

from evennia.contrib.base_systems.aetos_webclient import (
    AETOS_STATIC_DIR,
    constants,
    csp,
)

register = template.Library()


def _development_stamp(path):
    """
    Return the asset's modification time, for use while DEBUG is on.

    A fixed version is right for released code but wrong while developing: a
    contributor editing Aetos JavaScript would keep being served the cached copy
    and see no effect from their change, which reads as "my code does not work"
    rather than "my browser did not refetch".

    Args:
        path (str): Static path, as given to `{% static %}`.

    Returns:
        str or None: The mtime as an integer string, or None if unavailable.

    """
    # Aetos assets live under static/aetos/..., and `path` already starts with
    # "aetos/", so it resolves directly against the contrib static root.
    candidate = os.path.join(AETOS_STATIC_DIR, *path.split("/"))
    try:
        return str(int(os.path.getmtime(candidate)))
    except OSError:
        return None


@register.simple_tag
def aetos_static(path):
    """
    Return a versioned URL for an Aetos static asset.

    Args:
        path (str): Static path, as given to `{% static %}`.

    Returns:
        str: The static URL with a cache-busting version appended.

    """
    version = constants.ASSET_VERSION
    if getattr(settings, "DEBUG", False):
        stamp = _development_stamp(path)
        if stamp:
            version = "%s-%s" % (version, stamp)
    return "%s?v=%s" % (static(path), version)


@register.simple_tag
def aetos_csp():
    """
    Return the Content-Security-Policy for the client page.

    Returns:
        str: The policy string, or "" if the game has disabled it.

    """
    return csp.build_policy()
