"""
Content-Security-Policy for the Aetos client page.

A CSP is the difference between "an XSS in this client would be bad" and "an XSS
in this client has nothing to execute". Aetos already rebuilds every piece of
server markup from an allowlist and never uses `innerHTML`, but a policy is
worth having precisely for the bug nobody found.

**Why the policy is declared in the document rather than sent as a header.**
The client page is served by Evennia's own webclient view. A contrib cannot add
a response header without owning the view or installing middleware, and
middleware would apply the policy to the game's whole website -- its front page,
its admin, its wiki -- which is not a decision a webclient gets to make for a
game. A `<meta http-equiv>` policy applies to exactly one page: this one.

The cost of that choice is honest and worth stating: `frame-ancestors`,
`report-uri` and `sandbox` are ignored in a meta policy. A game that wants
clickjacking protection needs `X-Frame-Options` or a real `frame-ancestors`
header, and `README.md` says so rather than leaving the impression that the meta
policy covers it.

**What the default policy assumes.** That the client is served from the game's
own origin and talks to the game's own websocket, and that media a game declares
may live anywhere it likes over http or https. A game that serves scripts,
styles or fonts from elsewhere must say so:

```python
AETOS_CSP = {"img-src": ["https://cdn.example.com"]}
```

Sources are *added* to the defaults rather than replacing them, so a game
extending one directive cannot silently drop the protections in the others.
`AETOS_CSP = False` disables the meta policy entirely, for a game that sets its
own header and does not want two policies intersecting -- which is the failure
mode nobody debugs successfully, because two CSPs both apply and the result is
their intersection.

"""

from django.conf import settings

#: Directives Aetos declares, and the sources it allows by default.
#:
#: Ordered for reading rather than for the browser, which does not care.
DEFAULT_POLICY = {
    # Everything not named below. Deny by default and open specifically.
    "default-src": ["'self'"],
    # No inline scripts, no `eval`, no CDN. The client is vanilla JavaScript
    # served from the game's own origin, so this is the strict form -- and the
    # reason M26 moved the last inline script out of the page.
    "script-src": ["'self'"],
    # The one concession. Theme tokens and layout sizes are written as inline
    # styles (`element.style.setProperty`), which CSP counts as inline style.
    # See the note in README.md: this permits no script execution, and Aetos's
    # sanitiser accepts no `style` attribute or `<style>` element from game
    # content at all, so there is no injection point for it to widen.
    "style-src": ["'self'", "'unsafe-inline'"],
    # The websocket is usually on a different port from the page, which makes
    # it a different origin, so `'self'` does not cover it. Narrowed by scheme
    # rather than by host: a game behind a proxy, a tunnel or a custom domain
    # reaches its websocket at a name this module cannot predict.
    "connect-src": ["'self'", "ws:", "wss:"],
    # `data:` for the inline favicon and for AAC symbol packs, which are
    # deliberately allowed to embed their images so that a board keeps working
    # offline. `https:` because media is game-declared and may be hosted
    # anywhere; the server-side scheme allowlist in `media.py` is what stops it
    # being `javascript:`.
    "img-src": ["'self'", "data:", "https:"],
    "media-src": ["'self'", "https:"],
    "font-src": ["'self'"],
    # Aetos loads no plugins, embeds no frames and submits no forms. Each of
    # these is a way an injected page could act, closed off because none of them
    # is used.
    "object-src": ["'none'"],
    "frame-src": ["'none'"],
    "form-action": ["'none'"],
    "base-uri": ["'none'"],
    # The service worker and the manifest are same-origin by construction.
    "worker-src": ["'self'"],
    "manifest-src": ["'self'"],
}

#: Directives a `<meta http-equiv>` policy cannot express. Named so that a game
#: declaring one is told, rather than believing it took effect.
META_IGNORED_DIRECTIVES = ("frame-ancestors", "report-uri", "report-to", "sandbox")


class AetosCspError(Exception):
    """Raised when `AETOS_CSP` is malformed."""


def _validate(extra):
    """
    Check a game's `AETOS_CSP` declaration.

    Args:
        extra (dict): The setting's value.

    Returns:
        dict: The validated mapping of directive to list of sources.

    Raises:
        AetosCspError: If the declaration is malformed.

    """
    if not isinstance(extra, dict):
        raise AetosCspError(
            "AETOS_CSP must be a dict of directive -> list of sources, got %r"
            % type(extra).__name__
        )

    validated = {}
    for directive, sources in extra.items():
        if not isinstance(directive, str):
            raise AetosCspError("AETOS_CSP directive names must be strings, got %r" % (directive,))
        if directive in META_IGNORED_DIRECTIVES:
            # An error rather than a silent drop. A game that sets
            # `frame-ancestors` here believes it is protected from framing and
            # is not; finding that out at deploy time is much better than
            # finding it out from an incident.
            raise AetosCspError(
                "AETOS_CSP cannot set %r: a <meta> policy cannot express it. "
                "Send it as a real Content-Security-Policy header instead "
                "(or X-Frame-Options for frame-ancestors)." % directive
            )
        if directive not in DEFAULT_POLICY:
            raise AetosCspError(
                "AETOS_CSP has unknown directive %r. Valid directives: %s"
                % (directive, ", ".join(sorted(DEFAULT_POLICY)))
            )
        if isinstance(sources, str) or not isinstance(sources, (list, tuple)):
            raise AetosCspError(
                "AETOS_CSP[%r] must be a list of sources, got %r"
                % (directive, type(sources).__name__)
            )
        for source in sources:
            if not isinstance(source, str) or not source.strip():
                raise AetosCspError(
                    "AETOS_CSP[%r] sources must be non-empty strings, got %r" % (directive, source)
                )
            if ";" in source or "," in source:
                # A source containing a separator would end the directive early
                # and start another one -- policy injection through a settings
                # file is unlikely, but a typo producing a silently different
                # policy is not.
                raise AetosCspError(
                    "AETOS_CSP[%r] source %r contains a separator" % (directive, source)
                )
        validated[directive] = list(sources)
    return validated


def build_policy():
    """
    Build the policy string for the client page.

    Returns:
        str: The policy, or "" if a game has disabled it.

    Raises:
        AetosCspError: If `AETOS_CSP` is malformed.

    """
    extra = getattr(settings, "AETOS_CSP", None)
    if extra is False or extra is None and hasattr(settings, "AETOS_CSP"):
        # Explicitly disabled. `None` is treated the same as `False` only when
        # the setting is actually present, so an absent setting still gets the
        # default policy rather than none.
        return ""
    validated = _validate(extra) if extra else {}

    parts = []
    for directive, defaults in DEFAULT_POLICY.items():
        sources = list(defaults)
        for source in validated.get(directive, []):
            if source not in sources:
                sources.append(source)
        parts.append("%s %s" % (directive, " ".join(sources)))
    return "; ".join(parts)
