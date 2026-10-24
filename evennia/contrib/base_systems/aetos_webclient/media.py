"""
Media descriptors: validation, captioning obligations and URL safety.

Addendum A.58, A.79. Blueprint milestone M18.

THE RULE THIS MODULE EXISTS TO ENFORCE
--------------------------------------

`A11Y-MEDIA-001`: no gameplay-essential information may exist only in audio.

Aetos cannot fix that by itself. It cannot listen to a sound file and describe
it, and it will not pretend to -- an invented caption is worse than none,
because it is confidently wrong to precisely the player who cannot check it.

So the obligation lands on the game (A.79), and Aetos makes it visible rather
than silent: media without a caption is still played, but it is reported as
uncaptioned, counted, and surfaced in the developer diagnostics. A developer who
never hears about it will never fix it, and their players will never know what
they missed.

Decorative media is the deliberate exception. `decorative: True` is a game
saying "this carries nothing" -- a wind loop, a UI click -- and such media is
played without announcement (`A11Y-MEDIA-003`). It is an assertion, not an
escape hatch: a game that marks its combat cues decorative has lied to its own
players, and no validator can catch that.

URL SAFETY
----------

A media URL is game-supplied and ends up in an element's `src`. Games are
trusted with their own content, but a game that interpolates *player* input into
a URL is not unusual, and `javascript:` in a `src` is a cross-site scripting
vector that would run with the client's full privileges.

So the scheme is checked against an allowlist rather than a denylist. A
denylist would need to anticipate every scheme a browser has ever supported;
an allowlist only needs to know the three that make sense here.

"""

from urllib.parse import urlparse

#: Media categories. These map onto the volume controls `A11Y-MEDIA-002`
#: requires, which is why they are a fixed set rather than free text: a
#: category the player has no slider for is a sound they cannot turn down.
MEDIA_CATEGORIES = ("music", "ambience", "effect", "ui", "voice", "image")

#: Schemes permitted in a media URL.
#:
#: Relative URLs (no scheme) are permitted and are the common case -- a game
#: serving its own static files. `data:` is deliberately absent: it is the one
#: form where the payload and the reference are the same string, which makes
#: size unbounded and content unreviewable.
ALLOWED_SCHEMES = ("http", "https", "")

#: Upper bound on media items in one sync. A provider looping over every object
#: in a room could otherwise hand the client a thousand audio elements.
MAX_MEDIA_ITEMS = 32

MAX_URL_LENGTH = 2048
MAX_TEXT_LENGTH = 300


def is_safe_url(url):
    """
    Check whether a media URL is safe to place in a `src` attribute.

    Args:
        url (str): The candidate URL.

    Returns:
        bool: True when the scheme is allowed and the URL is well formed.

    """
    if not isinstance(url, str):
        return False
    candidate = url.strip()
    if not candidate or len(candidate) > MAX_URL_LENGTH:
        return False
    # A backslash is treated as a forward slash by browsers in some positions,
    # which is how "https:/\evil.example" gets past naive parsers. Nothing
    # legitimate needs one in a URL.
    if "\\" in candidate:
        return False
    try:
        parsed = urlparse(candidate)
    except ValueError:
        return False
    return parsed.scheme.lower() in ALLOWED_SCHEMES


def normalize_media_item(raw):
    """
    Validate one media descriptor from a provider.

    Args:
        raw: Whatever the provider returned for this item.

    Returns:
        dict or None: A valid descriptor, or None if it cannot be used.

    """
    if not isinstance(raw, dict):
        return None

    url = raw.get("url")
    if not is_safe_url(url):
        return None
    url = url.strip()

    category = raw.get("category")
    if category not in MEDIA_CATEGORIES:
        # An unknown category has no volume slider, so the player could not
        # turn it down. Rejecting the item is better than playing a sound they
        # cannot control (A11Y-MEDIA-002).
        return None

    decorative = raw.get("decorative") is True
    caption = raw.get("caption")
    caption = (
        str(caption)[:MAX_TEXT_LENGTH] if isinstance(caption, str) and caption.strip() else None
    )
    description = raw.get("description")
    description = (
        str(description)[:MAX_TEXT_LENGTH]
        if isinstance(description, str) and description.strip()
        else None
    )

    volume = raw.get("volume")
    try:
        volume = float(volume)
    except (TypeError, ValueError):
        volume = 1.0
    volume = min(max(volume, 0.0), 1.0)

    return {
        # A stable id lets the client tell "still the same track" from "a new
        # one", so ambient music does not restart on every sync. Falling back
        # to the URL is right: the same file in the same category *is* the same
        # media as far as playback is concerned.
        "id": str(raw.get("id") or url)[:MAX_TEXT_LENGTH],
        "url": url,
        "category": category,
        "caption": caption,
        "description": description,
        "decorative": decorative,
        "loop": raw.get("loop") is True,
        "volume": volume,
        # Computed here rather than in the client, so the server-side
        # diagnostics and the client agree on what "uncaptioned" means.
        "uncaptioned": not decorative and not caption,
    }


def normalize_media(raw_media, limit=MAX_MEDIA_ITEMS):
    """
    Validate a provider's media list.

    One malformed descriptor is dropped on its own. A provider is game code, and
    a single bad entry must not cost the player every other one -- the same rule
    the resource and effect normalisers follow.

    Args:
        raw_media: Whatever the provider returned.
        limit (int): Maximum items to keep.

    Returns:
        dict: `{"items": [...], "uncaptioned": int}`.

    """
    if not isinstance(raw_media, (list, tuple)):
        return {"items": [], "uncaptioned": 0}

    items = []
    seen = set()
    for raw in raw_media[:limit]:
        item = normalize_media_item(raw)
        if item is None or item["id"] in seen:
            continue
        seen.add(item["id"])
        items.append(item)

    return {
        "items": items,
        # Reported rather than merely true of the items, so a developer sees a
        # number without auditing the list, and so the count survives into the
        # diagnostic report.
        "uncaptioned": sum(1 for item in items if item["uncaptioned"]),
    }
