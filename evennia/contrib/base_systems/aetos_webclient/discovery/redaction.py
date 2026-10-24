"""
What discovery never prints, and never suggests.

WHY THIS IS A NAME TEST AND NOT A VALUE TEST. Discovery reads a live game's
attributes, and a game that keeps an API token or a hashed password on a
character keeps it in an attribute like any other. By the time a value has been
read it is too late to decide not to have read it, so the decision is made on the
**name**, before the value is touched: an attribute called `api_token` is
reported as `<redacted>` and its value is never loaded (Addendum B.46).

WHY IT IS DELIBERATELY TOO EAGER. `db.tokens` in a game where tokens are a
currency is withheld here, and that is the right way round. A false positive
costs a developer one line they write by hand, and the report says which name it
withheld so they know to. A false negative prints a secret into a file somebody
pastes into an issue.

This is the one place in discovery where a list of English words is correct. The
genre-neutrality rule -- pairing by structure, never by a list of resource names
-- is about guessing what somebody else's *game* means. This list is about what
credentials are called, and the cost of a miss is not a worse suggestion.

"""

#: What a withheld value is printed as, wherever one would have appeared.
REDACTED = "<redacted>"

#: Fragments that mark a name as a credential.
#:
#: Addendum B.46's list, matched against the name with underscores and hyphens
#: removed and case folded, so `API_Key`, `apikey` and `api-key` are the same
#: name. `key` on its own is not here: `db.key` and `db.room_key` are ordinary,
#: and `api_key` and `private_key` are caught by their longer forms.
CREDENTIAL_MARKERS = (
    "password",
    "passwd",
    "secret",
    "token",
    "apikey",
    "privatekey",
    "credential",
)


def _folded(name):
    """
    A name reduced to the form the markers are written in.

    Args:
        name (str): An attribute name or dict key.

    Returns:
        str: Lower case, with `_` and `-` removed.

    """
    return str(name).lower().replace("_", "").replace("-", "")


def is_sensitive(name):
    """
    Whether a name looks like it holds a credential.

    Args:
        name (str): An attribute name, or one segment of a binding expression.

    Returns:
        bool: True if its value must not be read, printed or suggested.

    """
    folded = _folded(name)
    return any(marker in folded for marker in CREDENTIAL_MARKERS)


def is_sensitive_expression(expression):
    """
    Whether any segment of a binding expression looks like a credential.

    Args:
        expression (str): e.g. `db.auth.token`.

    Returns:
        bool: True if any segment after `db` is sensitive. A dict called
            `secrets` withholds every key inside it, not only the ones whose own
            names give them away.

    """
    return any(is_sensitive(part) for part in str(expression).split(".")[1:])
