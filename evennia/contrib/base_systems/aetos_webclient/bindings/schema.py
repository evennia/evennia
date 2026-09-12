"""
The `AETOS_BINDINGS` schema, and the expression grammar underneath it.

Defined at D0 and enforced by the resolver at D1, in that order deliberately:
the grammar is the security boundary of the whole D-track, and it is easier to
argue about on its own than inside a resolver.

THE GRAMMAR IS A DENY-BY-DEFAULT WHITELIST, NOT A BLOCKLIST.

`AETOS_BINDINGS` is written by a game developer in their own settings file, so
this is not a defence against a hostile author -- somebody who can edit
settings.py can already run anything. It is a defence against **the resolver
becoming an expression evaluator**, which is what happens the first time
somebody adds "just method calls" or "just indexing" to make one game work.
Every addition looks small and the sum of them is `eval` with extra steps.

So the grammar is two forms and nothing else::

    db.<name>
    db.<name>.<name>

`db` is Evennia's attribute handler, `<name>` is a plain identifier, and that is
the entire language. Anything else is refused with a message naming what was
wrong, because a binding that silently resolves to `None` is the failure mode
that wastes an afternoon.

WHAT IS DELIBERATELY NOT EXPRESSIBLE, and why each one stays out:

- **Method calls** (`db.hp()`): calling is running. A resolver that calls is a
  resolver that can be handed `db.delete` by a typo.
- **Indexing** (`db.stats[0]`): `__getitem__` is arbitrary code on a custom
  type, and the useful cases are dict keys, which the second `.name` form
  already covers for Evennia's saver-dicts.
- **Arithmetic** (`db.hp + db.bonus`): the moment two values combine, the
  resolver needs an evaluator. A game that needs a computed value has a
  provider class, which is the supported way to run its own code.
- **Dunders** (`db.__class__`, `db.__globals__`): the standard route from any
  attribute traversal to the interpreter.
- **Statements** (`import os`, `x; y`, embedded newlines): a binding is a path,
  not a program. These are listed explicitly in the rejection table because
  they are what somebody tries first.

"""

import re

#: The slots a binding may declare. Each corresponds to a provider Aetos already
#: normalises, which is the point: a binding feeds the *existing* pipeline rather
#: than being a second way into the client.
#:
#: Order matters only for the report, which lists them this way so the most
#: commonly wanted one is first.
BINDING_SLOTS = ("resources", "equipment", "target", "effects", "actions")

#: Fields whose value is a binding expression rather than plain text.
#:
#: Named, rather than inferred from "it looks like `db.something`". A game that
#: wrote `"label": "db.hp"` meant the words -- an odd label, but theirs -- and a
#: validator that guessed would refuse a legal declaration. A game that wrote
#: `"value": "hp"` meant the attribute and is told so.
EXPRESSION_FIELDS = frozenset({"value", "maximum", "minimum", "remaining", "duration"})

#: Fields a binding entry may carry, per slot. D0 defined this so the discovery
#: report only ever suggests something the validator will accept; D1 is what
#: enforces it.
BINDING_FIELDS = {
    "resources": {
        "required": ("label", "value"),
        "optional": ("maximum", "minimum", "display", "severity"),
    },
    "equipment": {"required": ("label", "value"), "optional": ("kind", "category")},
    "target": {"required": ("label", "value"), "optional": ("maximum", "minimum", "kind")},
    "effects": {
        "required": ("label", "value"),
        "optional": ("kind", "remaining", "duration", "description"),
    },
    "actions": {"required": ("label", "command"), "optional": ("kind",)},
}

# There is no `order` field, and the first draft had one.
#
# It would have done nothing. Python dicts keep insertion order, so the order in
# settings.py is already the order on screen; `order` would have been a second
# way to say the same thing, and a control that appears to work and changes
# nothing is the defect this project keeps finding. Removed before it shipped
# rather than after somebody relied on it.

#: `db.name` or `db.name.child`, and nothing else.
#:
#: Two things here are easy to get wrong and both were, in this file, before the
#: tests were run:
#:
#: **Anchoring.** An unanchored pattern matches the `db.hp` inside
#: `db.hp.__class__` and reports the whole string as valid -- the exact mistake
#: this grammar exists to prevent, made in the grammar itself.
#:
#: **Dunders are identifiers.** `__class__` and `__globals__` are ordinary
#: Python names: they start with a letter-or-underscore and continue with word
#: characters, so an identifier whitelist accepts them. That is not a small gap
#: -- `db.__class__` is the first step of every attribute-traversal escape there
#: is, and it passed the first version of this pattern.
#:
#: So each segment carries `(?!__)`. A single leading underscore stays allowed,
#: because `db._internal` is an ordinary attribute name a game may genuinely
#: want on screen; two is the marker of Python's own namespace and nothing a
#: game stores should begin that way.
_SEGMENT = r"(?!__)[A-Za-z_][A-Za-z0-9_]*"
EXPRESSION_PATTERN = re.compile(r"^db\.%s(\.%s)?$" % (_SEGMENT, _SEGMENT))

#: Expressions that must be refused, paired with what is wrong with each.
#:
#: These are not the only invalid expressions -- the whitelist decides that --
#: they are the ones with a *test each*, taken from Addendum B.59. A resolver
#: that quietly accepts any one of them has reintroduced `eval`, and the failure
#: would not be visible in any output.
REJECTED_EXPRESSIONS = {
    "db.__class__": "dunder attribute",
    "db.hp.__class__": "dunder attribute",
    "db.__globals__": "dunder attribute",
    "db.hp()": "call",
    "db.get('hp')": "call",
    "db.stats[0]": "subscript",
    "db.stats['hp']": "subscript",
    "db.hp + db.bonus": "arithmetic",
    "db.hp - 1": "arithmetic",
    "lambda: 1": "not an attribute path",
    "import os": "statement",
    "db.hp; db.mp": "statement separator",
    "db.hp\ndb.mp": "embedded newline",
    "db.hp.mp.sp": "too deep -- two levels only",
    "hp": "does not start at db",
    "db": "names no attribute",
    "db.": "names no attribute",
    ".db.hp": "does not start at db",
    "self.db.hp": "does not start at db",
    "db.hp ": "trailing whitespace",
    " db.hp": "leading whitespace",
    "": "empty",
}


def is_valid_expression(expression):
    """
    Whether a binding expression is one this grammar allows.

    Args:
        expression (str): The expression as written in `AETOS_BINDINGS`.

    Returns:
        bool: True if it is `db.name` or `db.name.child`.

    Notes:
        Non-strings are refused rather than coerced. A game that wrote
        `"value": 5` meant something, and guessing what turns a typo into a
        silently wrong health bar.

    """
    if not isinstance(expression, str):
        return False
    return bool(EXPRESSION_PATTERN.match(expression))


def expression_parts(expression):
    """
    The attribute names in a valid expression.

    Args:
        expression (str): A valid binding expression.

    Returns:
        tuple: One or two attribute names, without the leading `db`.

    Raises:
        ValueError: If the expression is not valid. Callers should ask
            `is_valid_expression` first; this refuses rather than returning a
            half-parsed result, because a caller that ignores the return value
            of a parse is the caller this exists to stop.

    """
    if not is_valid_expression(expression):
        raise ValueError("not a valid Aetos binding expression: %r" % (expression,))
    return tuple(expression.split(".")[1:])


def explain_expression(expression):
    """
    Why an expression was refused, in words a beginner can act on.

    Args:
        expression: The expression as written.

    Returns:
        str: One sentence naming what is wrong and what is allowed.

    Notes:
        This exists because the alternative is a regular expression in an error
        message. `AETOS_BINDINGS` is the setting for somebody who did not want to
        write Python, and telling them their value "did not match
        `^db\\.(?!__)[A-Za-z_]...`" is telling them to go and find somebody who
        did.

        The specific cases below are recognised rather than merely rejected,
        because "you cannot call a method here" is a fix and "invalid" is a
        puzzle. Anything unrecognised falls through to the general message, which
        still says what the two valid shapes are.

    """
    if not isinstance(expression, str):
        return (
            'must be a string like "db.hp", not %s. Quote it: "value": "db.hp"'
            % type(expression).__name__
        )
    if not expression.strip():
        return 'is empty. It should name an attribute, like "db.hp"'
    if expression != expression.strip():
        return (
            "has a space at the start or end: %r. Aetos does not trim it for you, "
            'because "db.hp " and "db.hp" would then be the same binding and only '
            "one of them is what you typed" % expression
        )
    if "(" in expression:
        return (
            "looks like a method call. A binding names where a value is stored, and "
            "Aetos never calls anything to get it -- if the value has to be computed, "
            "that is what a provider class in AETOS_PROVIDERS is for"
        )
    if "[" in expression:
        return (
            "uses [] to index. Use a second dotted name instead: a dict stored at "
            'db.stats is reached as "db.stats.hp"'
        )
    if "__" in expression:
        return (
            "names a Python internal (something with a double underscore). Bindings "
            "reach your game's own attributes only"
        )
    if any(operator in expression for operator in "+-*/%"):
        return (
            "does arithmetic. A binding is a place, not a sum -- a value that has to "
            "be calculated needs a provider class in AETOS_PROVIDERS"
        )
    if ";" in expression or "\n" in expression:
        return "contains more than one statement. A binding is a single attribute path"
    if not expression.startswith("db."):
        return (
            "must start with db. -- that is Evennia's attribute store, where "
            "`character.db.hp = 50` puts things. You wrote %r" % expression
        )
    if expression.count(".") > 2:
        return (
            "goes more than two levels deep. Aetos reads db.name or db.name.child, "
            "and stops there on purpose: further traversal is how a setting becomes a "
            "little programming language"
        )
    return (
        'is not a valid binding. Use "db.name" for an attribute, or "db.name.child" '
        "for a key inside a dict stored in one"
    )


def validate_bindings(raw, error_class=ValueError):
    """
    Check a game's whole `AETOS_BINDINGS` declaration.

    Args:
        raw: The setting's value, as the game wrote it.
        error_class (type, optional): Exception to raise. The caller supplies
            `AetosBindingError` so that this module stays free of the resolver.

    Returns:
        dict: The declaration, slot by slot, containing only what was declared.

    Raises:
        error_class: On anything malformed, with a message naming the slot, the
            key and the field.

    Notes:
        **Validated as a whole, and refused as a whole.** A declaration with one
        bad entry does not silently ship the other three: a game that misspelled
        one binding would then have a client that half worked, and "half of my
        bars appeared" is a much harder thing to debug than "Aetos refused to
        start and told me which line".

        This is called from a Django system check at startup as well as at use,
        so in practice the developer is told while they are still looking.

    """
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise error_class(
            "AETOS_BINDINGS must be a dict of slots, got %s. It looks like:\n"
            '    AETOS_BINDINGS = {"resources": {"health": {...}}}' % type(raw).__name__
        )

    unknown = set(raw) - set(BINDING_SLOTS)
    if unknown:
        raise error_class(
            "AETOS_BINDINGS has unknown slot(s) %s. Valid slots: %s"
            % (sorted(unknown), ", ".join(BINDING_SLOTS))
        )

    validated = {}
    for slot, entries in raw.items():
        if not isinstance(entries, dict):
            raise error_class(
                "AETOS_BINDINGS[%r] must be a dict of named entries, got %s"
                % (slot, type(entries).__name__)
            )

        fields = BINDING_FIELDS[slot]
        allowed = set(fields["required"]) | set(fields["optional"])
        checked = {}

        for key, entry in entries.items():
            where = "AETOS_BINDINGS[%r][%r]" % (slot, key)
            if not isinstance(key, str) or not key:
                raise error_class("%s: the name must be a non-empty string" % where)
            if not isinstance(entry, dict):
                raise error_class(
                    "%s must be a dict, got %s. It looks like:\n"
                    '    {"label": "Health", "value": "db.hp"}' % (where, type(entry).__name__)
                )

            missing = [name for name in fields["required"] if name not in entry]
            if missing:
                raise error_class(
                    "%s is missing %s. Every %s binding needs %s"
                    % (
                        where,
                        " and ".join(repr(name) for name in missing),
                        slot,
                        " and ".join(repr(name) for name in fields["required"]),
                    )
                )

            extra = sorted(set(entry) - allowed)
            if extra:
                raise error_class(
                    "%s has unknown field(s) %s. A %s binding takes: %s"
                    % (where, extra, slot, ", ".join(sorted(allowed)))
                )

            for name, value in entry.items():
                if name in EXPRESSION_FIELDS:
                    if not is_valid_expression(value):
                        raise error_class("%s[%r] %s" % (where, name, explain_expression(value)))
                elif not isinstance(value, (str, int, float)):
                    raise error_class(
                        "%s[%r] must be text or a number, got %s"
                        % (where, name, type(value).__name__)
                    )

            checked[key] = dict(entry)

        validated[slot] = checked

    return validated
