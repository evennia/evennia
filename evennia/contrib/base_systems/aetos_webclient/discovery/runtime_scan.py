"""
Pass 1 -- reading the attributes a game's characters actually have.

WHY THE STATIC SCAN IS NOT ENOUGH. Evennia attributes are database rows, not
class members. `caller.db.reputation = 0` typed once in a command creates an
attribute that exists on every character from then on and appears in no
typeclass, so source parsing cannot see it. On a game that has been played for a
while, most of what is worth showing is in this category.

WHY THIS ONE IS NOT ENOUGH EITHER. A brand-new game has a Character typeclass
and no characters, and this scan returns nothing at all. The scans are merged and
each candidate says which found it.

READ-ONLY, AND THAT IS NOT INCIDENTAL. This runs against a live game's database,
possibly a production one, from a command a developer is trying out for the first
time. It queries and it reads; it does not create a character to inspect, does
not touch an attribute to see what happens, and does not write a marker
anywhere. A discovery tool that modified the game it was describing would be
unusable exactly where it is most wanted.

A REPRESENTATIVE, NOT A CENSUS (Addendum B.20, B.21). The developer can name the
character to read -- `--character #12` -- and should, because a character mid-way
through the game carries what a fresh one does not. Without one, a bounded sample
of the newest characters is read. It never walks the whole database: a game with
fifty thousand characters is not fifty thousand times more informative, because
attribute *names* repeat and the names are what discovery is after.

CREDENTIALS ARE REFUSED BY NAME, BEFORE THE VALUE IS READ (B.46). See
`redaction`.

"""

from collections.abc import Mapping

from django.conf import settings

from evennia.contrib.base_systems.aetos_webclient.discovery import redaction, values
from evennia.contrib.base_systems.aetos_webclient.discovery.candidates import Candidate

#: How many characters to read when none is named.
#:
#: Enough that an attribute set by one feature on some characters is seen, small
#: enough that this stays a query a developer can run on a live game without
#: thinking about it. Newest first, because a half-built feature's attributes are
#: on the characters somebody made while building it.
SAMPLE_SIZE = 25

#: How many keys of one dict attribute are read.
#:
#: `db.stats = {"hp": 5, "hp_max": 9}` is common and reachable as
#: `db.stats.hp`. A dict with ten thousand keys is a data store, not a stat
#: block, and reading all of it is the memory problem B.53 lists.
MAX_CHILDREN = 50

#: How many names to list in one note before summarising.
MAX_NAMED = 8


class SelectionError(Exception):
    """The developer named a character or typeclass that cannot be used."""


def describe(character):
    """
    How a character is named in the report.

    Args:
        character (Object): A character.

    Returns:
        str: `#12 Ada`, from the id and the `db_key` column.

    """
    return "#%s %s" % (getattr(character, "id", "?"), getattr(character, "db_key", ""))


def _named(items):
    """
    A bounded, comma-separated list.

    Args:
        items (iterable): Strings.

    Returns:
        str: At most `MAX_NAMED` of them, then how many more.

    """
    items = sorted(items)
    shown = ", ".join(items[:MAX_NAMED])
    if len(items) > MAX_NAMED:
        shown += " and %d more" % (len(items) - MAX_NAMED)
    return shown


def select_characters(character=None, typeclass=None, limit=SAMPLE_SIZE):
    """
    The characters to read.

    Args:
        character (str, optional): `#12` or a name. The developer's choice of
            representative, read alone.
        typeclass (str, optional): A typeclass path to sample from instead of
            `BASE_CHARACTER_TYPECLASS`.
        limit (int, optional): Sample size when no character is named.

    Returns:
        list: Objects, possibly empty.

    Raises:
        SelectionError: If the named character does not exist, the name is
            ambiguous, or the typeclass will not import. An error rather than an
            empty report, because "no candidates" reads as "your game has
            nothing" when the truth is "you mistyped the name".

    Notes:
        The sample includes **subclasses** of the typeclass. D0 matched the
        exact path, and a game whose characters all use a subclass of its base
        -- the ordinary case once a game has NPCs -- read nobody.

    """
    from evennia.objects.models import ObjectDB

    if character:
        text = str(character).strip()
        if text.startswith("#") and text[1:].isdigit():
            matches = list(ObjectDB.objects.filter(id=int(text[1:])))
        else:
            matches = list(ObjectDB.objects.filter(db_key__iexact=text).order_by("id")[:MAX_NAMED])
        if not matches:
            raise SelectionError("nothing in the game is called %s" % text)
        if len(matches) > 1:
            raise SelectionError(
                "more than one object is called %s: %s. Name one by number, e.g. "
                "--character #%s" % (text, ", ".join(describe(m) for m in matches), matches[0].id)
            )
        return matches

    path = typeclass or getattr(settings, "BASE_CHARACTER_TYPECLASS", None)
    if not path:
        return list(ObjectDB.objects.all().order_by("-id")[:limit])
    try:
        query = ObjectDB.objects.typeclass_search(path, include_children=True)
    except Exception as error:
        raise SelectionError(
            "the typeclass %s could not be loaded (%s)" % (path, " ".join(str(error).split()))
        )
    return list(query.order_by("-id")[:limit])


def _empty(value):
    """
    Whether a value says nothing about its kind.

    Args:
        value: A live value.

    Returns:
        bool: True for None and for empty built-in containers and strings.

    Notes:
        Not `value in (None, "", [], {})`. `in` compares with `==`, and `==` on
        an object of the game's choosing is the game's code.

    """
    if value is None:
        return True
    if isinstance(value, (str, list, tuple, dict, set)):
        return len(value) == 0
    return False


class _Readings:
    """What the scan has seen so far, keyed by expression."""

    def __init__(self):
        """Start with nothing seen."""
        self.seen = {}

    def note(self, expression, name, value, character_id):
        """
        Record one value on one character.

        Args:
            expression (str): e.g. `db.stats.hp`.
            name (str): e.g. `stats.hp`.
            value: The live value.
            character_id (int): Whose it is.

        """
        record = self.seen.setdefault(
            expression, {"name": name, "count": 0, "kind": "unknown", "shown": None, "observed": []}
        )
        record["count"] += 1
        kind = values.kind_of(value)
        if record["kind"] == "unknown" and not _empty(value):
            record["kind"] = kind
            record["shown"] = values.shown(value)
        if kind == "number":
            record["observed"].append((character_id, value))


def scan_characters(characters=None, limit=SAMPLE_SIZE):
    """
    Candidates from the attributes live characters carry.

    Args:
        characters (list, optional): Characters to read. Defaults to a sample.
        limit (int, optional): Sample size when `characters` is not given.

    Returns:
        tuple: `(candidates, problems)`.

    Notes:
        One candidate per attribute *name*, not per character: the same `hp` on
        twenty characters is one thing to bind. The evidence names how many
        carried it, which is the number that tells a developer whether they are
        looking at a real feature or at one character somebody experimented on.

    """
    if characters is None:
        characters = select_characters(limit=limit)

    readings = _Readings()
    withheld = set()
    categorised = {}
    truncated = set()
    problems = []
    counted = 0

    for character in characters:
        counted += 1
        who = getattr(character, "id", None)
        try:
            attributes = character.attributes.all()
        except Exception as error:  # pragma: no cover - defensive
            # A single unreadable character must not end the scan. Naming it in
            # the report is more use than a traceback, because the developer can
            # go and look at that object.
            problems.append("could not read attributes of #%s (%s)" % (who, error))
            continue

        for attribute in attributes:
            key = getattr(attribute, "key", None)
            if not isinstance(key, str) or not key.isidentifier() or key.startswith("__"):
                # Evennia allows attribute keys that are not identifiers. They
                # cannot be written in the binding grammar, so suggesting one
                # would produce a line that does not work.
                continue
            category = getattr(attribute, "category", None)
            if category:
                # The grammar has no way to say a category. Reported, not
                # skipped: Evennia's traits contrib keeps stats this way, and a
                # game built on it deserves a reason for an empty report.
                categorised.setdefault(str(category), set()).add(key)
                continue
            if redaction.is_sensitive(key):
                # Decided on the name. The value is never loaded.
                withheld.add(key)
                continue

            try:
                value = attribute.value
            except Exception:  # pragma: no cover - defensive
                continue
            readings.note("db.%s" % key, key, value, who)

            if isinstance(value, Mapping):
                for index, (child, child_value) in enumerate(value.items()):
                    if index >= MAX_CHILDREN:
                        truncated.add(key)
                        break
                    if not isinstance(child, str) or not child.isidentifier():
                        continue
                    if child.startswith("__"):
                        continue
                    if redaction.is_sensitive(child):
                        withheld.add("%s.%s" % (key, child))
                        continue
                    if values.kind_of(child_value) in ("number", "boolean", "object"):
                        readings.note(
                            "db.%s.%s" % (key, child), "%s.%s" % (key, child), child_value, who
                        )

    plural = "" if counted == 1 else "s"
    candidates = []
    for expression, record in sorted(readings.seen.items()):
        where = "on %d of %d character%s sampled" % (record["count"], counted, plural)
        if record["shown"] is not None:
            where += " (%s %s)" % ("now" if counted == 1 else "e.g.", record["shown"])
        candidates.append(
            Candidate(
                expression=expression,
                name=record["name"],
                origin="runtime",
                evidence=where,
                kind=record["kind"],
                shown=record["shown"],
                observed=tuple(record["observed"]),
                count=record["count"],
            )
        )

    if withheld:
        problems.append(
            "Withheld because the names look like credentials -- the values were never "
            "read and none is suggested: %s"
            % _named("%s = %s" % (name, redaction.REDACTED) for name in withheld)
        )
    if categorised:
        problems.append(
            "Attributes stored under a category were not suggested, because the binding "
            "grammar reaches uncategorised attributes only: %s. If these are what you "
            "want on screen -- Evennia's traits contrib keeps stats this way -- a "
            "provider class in AETOS_PROVIDERS can read them."
            % "; ".join(
                "%s (%s)" % (category, _named(keys))
                for category, keys in sorted(categorised.items())
            )
        )
    if truncated:
        problems.append(
            "Only the first %d keys of %s were read." % (MAX_CHILDREN, _named(truncated))
        )
    if not counted:
        problems.append(
            "no characters exist yet, so only the typeclass source could be read. "
            "Run this again once somebody has played."
        )

    return candidates, problems
