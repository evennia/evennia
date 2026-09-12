"""
`AETOS_BINDINGS` -- a health bar from a settings declaration, with no Python.

WHAT THIS REPLACES. Nothing, and that is the point. Putting a number on screen
already worked: write a provider class, register it in `AETOS_PROVIDERS`, return
a normalised payload. That is the right architecture and it is more than somebody
with a `hp` attribute should have to do. So a binding is a **declaration of where
a value lives**::

    AETOS_BINDINGS = {
        "resources": {
            "health": {"label": "Health", "value": "db.hp", "maximum": "db.hp_max"},
        },
    }

and Aetos does the fetching. No class, no import path, no file.

WHY THIS IS A SEPARATE PACKAGE FROM `discovery`.

Discovery is a development-time tool that *suggests* bindings; bindings are
runtime code that *reads* them. The dependency runs one way -- discovery imports
this package's grammar, and nothing here imports discovery -- so a game running
in production never loads the source scanner, and the schema has exactly one
definition rather than one on each side that can drift.

D0 put the grammar in `discovery/` because that is where it was being defined.
Leaving it there would have made the live client depend on a developer tool, and
that is the sort of thing which is easy to fix now and permanent in a year.

THE SECURITY LINE, RESTATED FROM `schema`.

`AETOS_BINDINGS` is written by the game's own developer, so this is not a defence
against a hostile author -- somebody who can edit settings.py can already run
anything. It is a defence against **the resolver becoming an expression
evaluator**. Every "just method calls" or "just indexing" that would make one
game work is another step towards `eval`, and the grammar is what stops the
first step being taken.

PRECEDENCE: custom > binding > default.

A game that has written a provider class keeps it. A binding fills a slot nobody
has claimed, and the stock default fills what is left. Stated in that order in
`providers.get_providers()`, so a developer migrating from a class to a
declaration is never surprised by both being live at once.

"""

from evennia.contrib.base_systems.aetos_webclient.bindings.resolver import (  # noqa: F401
    AetosBindingError,
    AetosBindingResolver,
)
from evennia.contrib.base_systems.aetos_webclient.bindings.schema import (  # noqa: F401
    BINDING_FIELDS,
    BINDING_SLOTS,
    EXPRESSION_PATTERN,
    REJECTED_EXPRESSIONS,
    expression_parts,
    is_valid_expression,
    validate_bindings,
)
from evennia.contrib.base_systems.aetos_webclient.bindings.settings_source import (  # noqa: F401
    bound_slots,
    get_bindings,
    provider_for,
)

__all__ = [
    "AetosBindingError",
    "AetosBindingResolver",
    "BINDING_FIELDS",
    "BINDING_SLOTS",
    "EXPRESSION_PATTERN",
    "REJECTED_EXPRESSIONS",
    "expression_parts",
    "is_valid_expression",
    "validate_bindings",
    "bound_slots",
    "get_bindings",
    "provider_for",
]
