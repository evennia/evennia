"""
Turning candidates into something a developer can paste.

THE OUTPUT IS THE PRODUCT. Discovery's whole value is that the developer does
not have to look anything up, so the report is a settings block in the exact
shape `AETOS_BINDINGS` takes, with the evidence beside it as comments. What is
printed should be correct if pasted unchanged and obvious where it needs
editing.

**Printed, never written.** Discovery does not open settings.py. A tool that
edits a developer's settings file has to be trusted before it is understood,
which is the wrong way round for the first thing somebody runs.

EVERY SUGGESTION ANSWERS FIVE QUESTIONS (Addendum B.33): what was found, where,
why it may matter, how confident discovery is, and what accepting it generates.
They are the `found:`, `why:`, `makes:` lines and the level beside the name.

LOW CONFIDENCE IS SHOWN, NOT SELECTED (B.28). A low-confidence entry is printed
commented out, in place, so pasting the block unchanged activates only what
discovery could justify and uncommenting one line is all it takes to accept the
rest. The block still evaluates -- comments are not code -- and there is a test
that D1's own validator accepts it.

THE ONE FIELD THAT IS ALWAYS A GUESS is the label. The scan knows the attribute
is called `hp`; it does not know the game calls it "Vitality", and it certainly
does not know what it is called in the language the game is played in. So the
label is made from the attribute name and the report says, once, that this is
the field to change. Once is deliberate -- a comment on every line is noise, and
noise is what gets pasted without reading.

"""

import json

from evennia.contrib.base_systems.aetos_webclient.bindings.schema import (
    BINDING_SLOTS,
    is_valid_expression,
)
from evennia.contrib.base_systems.aetos_webclient.discovery import confidence, redaction

# D0 carried a `BINDINGS_ARE_LIVE = False` flag here, and a paragraph warning
# that pasting the output would not change anything, because the resolver did not
# exist yet. D1 built it, so both are gone rather than left as a constant that is
# never false: a flag with one possible value is a note about history wearing a
# switch's clothes, and the note belongs in `notes/d1-binding-resolver.md`, where
# it is.

HEADER = """\
# Suggested by `evennia aetos discover`. Nothing has been changed for you --
# paste what you want into server/conf/settings.py and delete the rest.
#
# The `label` on every line is a guess made from the attribute name. It is the
# text a player reads, so it is the first thing worth changing.
#
# Entries marked LOW are commented out: discovery found them but cannot justify
# selecting them. Uncomment one to accept it."""

NOTHING_SELECTED = """\
# Nothing below was confident enough to select, so every entry is commented out.
# Each says what held it back."""

NOTHING_FOUND = """\
No candidates found.

Discovery reads three things: the typeclass source under typeclasses/, world/
and commands/, the attributes of characters that already exist, and the
Character typeclass and commands Evennia has loaded for them. Finding nothing
usually means one of:

  - the game stores its values somewhere other than character attributes, in
    which case a provider class is the supported route -- see AETOS_PROVIDERS;
  - the attributes are set from code discovery does not read, and no character
    has been played yet, so neither scan could see them;
  - the game directory has no typeclasses/ yet."""

#: The key the target slot reserves for the target's name (D2).
TARGET_NAME_KEY = "name"


def _label_for(name):
    """
    A first-draft label for an attribute name.

    Args:
        name (str): The attribute name, e.g. `hp_max` or `stats.hp`.

    Returns:
        str: A readable label, e.g. `Hp max` -- from the last segment only.

    Notes:
        Underscores to spaces and the first letter capitalised, and nothing
        cleverer. Expanding `hp` to `Health` would be a guess about the game
        that happens to be right often enough to stop developers checking it.

    """
    words = name.rpartition(".")[2].replace("_", " ").strip()
    return words[:1].upper() + words[1:]


def _q(text):
    """
    A string as a Python literal, safe whatever it contains.

    Args:
        text (str): Any text.

    Returns:
        str: A double-quoted literal. JSON's escapes are valid Python, so a
            command key with a quote or a backslash in it cannot break the block.

    """
    return json.dumps(str(text), ensure_ascii=False)


def _explanation(item, heading):
    """
    The comment block above one suggestion.

    Args:
        item: A `Candidate` or `ActionCandidate`.
        heading (str): What the entry is, e.g. `hp, with ceiling hp_max`.

    Returns:
        list: Comment lines, unindented.

    """
    lines = ["# %s -- %s" % (heading, item.confidence), "#   found: %s" % item.evidence]
    for index, reason in enumerate(item.reasons):
        lines.append("#   %s %s" % ("why:  " if index == 0 else "      ", reason))
    for warning in item.warnings:
        lines.append("#   check: %s" % warning)
    lines.append("#   makes: %s" % confidence.makes(item))
    return lines


def _fields(slot, item):
    """
    The key and fields of one generated entry.

    Args:
        slot (str): The binding slot.
        item: A `Candidate` or `ActionCandidate`.

    Returns:
        tuple: `(key, [(field, value), ...])`, or `(None, None)` if the entry
            would not pass the grammar.

    Notes:
        An expression the grammar would refuse never reaches the page. The scans
        only build valid ones, so this guards against a future scan rather than
        today's -- and it is the cheapest place to keep the promise that what is
        printed works when pasted.

    """
    if slot == "actions":
        return item.key, [("label", _label_for(item.key)), ("command", item.command)]
    if not is_valid_expression(item.expression):
        return None, None
    if slot == "target":
        return TARGET_NAME_KEY, [("label", "Target"), ("value", item.expression)]
    fields = [("label", _label_for(item.name)), ("value", item.expression)]
    if slot == "resources" and item.maximum and is_valid_expression(item.maximum):
        fields.append(("maximum", item.maximum))
    return item.key, fields


def entry_for(slot, item):
    """
    The key and fields one candidate would generate, for anything that needs
    them outside this module.

    Args:
        slot (str): The binding slot.
        item: A `Candidate` or `ActionCandidate`.

    Returns:
        tuple: `(key, [(field, value), ...])`.

    Notes:
        The wizard offers the developer exactly what the report would print, so
        both ask the same function. Two copies of "what does a resource entry
        look like" would drift, and the one that drifted would be the one
        nobody reads.

    """
    return _fields(slot, item)


def _heading(slot, item):
    """
    The name line of an explanation.

    Args:
        slot (str): The binding slot.
        item: A `Candidate` or `ActionCandidate`.

    Returns:
        str: e.g. `db.hp, with ceiling db.hp_max`.

    """
    if slot == "actions":
        return "the %s command" % item.key
    if getattr(item, "maximum", None):
        return "%s, with ceiling %s" % (item.expression, item.maximum)
    return item.expression


def _slot_lines(slot, items):
    """
    One slot of the generated block.

    Args:
        slot (str): The binding slot.
        items (list): Its suggestions, most confident first.

    Returns:
        tuple: `(lines, selected)` -- the lines, and whether anything in the
            slot is selected rather than commented out.

    """
    selected = any(item.confidence != confidence.LOW for item in items)
    outer = "" if selected else "# "
    lines = [outer + "    %s: {" % _q(slot)]

    if slot == "target" and len(items) > 1:
        lines.append("        # Only one of these can name the target -- choose one.")

    for item in items:
        key, fields = _fields(slot, item)
        if key is None:
            continue
        inner = "# " if (item.confidence == confidence.LOW and selected) else outer
        for line in _explanation(item, _heading(slot, item)):
            lines.append("        " + line)
        lines.append(inner + "        %s: {" % _q(key))
        for name, value in fields:
            lines.append(inner + "            %s: %s," % (_q(name), _q(value)))
        lines.append(inner + "        },")

    lines.append(outer + "    },")
    return lines, selected


def _context_lines(context):
    """
    What was read, for the top of the report (B.45).

    Args:
        context (dict): Optional `gamedir`, `generated_at`, `characters`,
            `lineages`, `commands_from`.

    Returns:
        list: Comment lines.

    """
    lines = []
    if context.get("gamedir"):
        lines.append("# Game: %s" % context["gamedir"])
    if context.get("generated_at"):
        lines.append("# Generated: %s" % context["generated_at"])
    if context.get("characters"):
        lines.append("# Characters read: %s" % ", ".join(context["characters"]))
    for chain in context.get("lineages") or []:
        lines.append("# Typeclass: %s" % " <- ".join(chain))
    if context.get("commands_from"):
        lines.append("# Commands read from: %s" % context["commands_from"])
    return lines


def render(candidate_set, problems=(), include_all=False, context=None):
    """
    The report, as text.

    Args:
        candidate_set (CandidateSet): What the scans found, assessed.
        problems (iterable, optional): Human-readable notes about what could not
            be read, or what was deliberately left out.
        include_all (bool, optional): Include bookkeeping attributes.
        context (dict, optional): What was read -- see `_context_lines`.

    Returns:
        str: The report.

    """
    context = context or {}
    problems = list(problems)
    slots = [(slot, candidate_set.by_slot(slot, include_all)) for slot in BINDING_SLOTS]
    slots = [(slot, items) for slot, items in slots if items]
    unslotted = candidate_set.unslotted(include_all)

    lines = []
    if not slots and not unslotted:
        lines.append(NOTHING_FOUND)
        about = _context_lines(context)
        if about:
            lines.append("")
            lines.extend(about)
    else:
        lines.append(HEADER)
        about = _context_lines(context)
        if about:
            lines.append("#")
            lines.extend(about)
        lines.append("")

        body, any_selected = [], False
        for slot, items in slots:
            slot_lines, selected = _slot_lines(slot, items)
            body.extend(slot_lines)
            any_selected = any_selected or selected

        if slots and not any_selected:
            lines.append(NOTHING_SELECTED)
        lines.append("AETOS_BINDINGS = {")
        lines.extend(body)
        lines.append("}")

        if unslotted:
            lines.append("")
            lines.append("# Also found, and not placed above -- no slot shows these as they are:")
            for item in unslotted:
                lines.append("#   %s -- %s, %s" % (item.expression, item.kind, item.evidence))

    unmentioned = [
        name for name in sorted(candidate_set.withheld) if not any(name in p for p in problems)
    ]
    if unmentioned:
        problems.append(
            "Withheld because the names look like credentials: %s"
            % ", ".join("%s = %s" % (name, redaction.REDACTED) for name in unmentioned)
        )

    if problems:
        lines.append("")
        lines.append("Notes:")
        for problem in problems:
            lines.append("  - %s" % problem)

    return "\n".join(lines)
