"""
Aetos discovery -- finding a game's own data so a developer does not have to
write a provider class to show a health bar.

WHY THIS EXISTS. Today, putting a number on the screen means writing Python: a
provider class, registered in `AETOS_PROVIDERS`, returning a normalised payload.
That is the right architecture and it is too much to ask of somebody who has a
`hp` attribute and wants a bar. The D-track's answer is `AETOS_BINDINGS` -- a
declaration in settings, no class anywhere -- and discovery is the tool that
writes the first draft of that declaration by looking at the game.

WHAT IT IS NOT. It is a **suggestion engine**. It reads, it prints, and a
developer decides. It never edits settings, never writes to the database and
never claims a binding it has not checked it could resolve. A suggestion that
fails when pasted is worse than no suggestion, because the developer now
distrusts the tool and has to debug something they did not write.

THE BOUNDARY. This package imports Django and the standard library. It must not
import anything that talks to a browser: no protocol, no manifest, no inputfunc,
no static asset. Discovery is a terminal command run by a developer, and it has
no player-facing surface at all -- there is a test that asserts the import graph
stays that way, because the easiest version of this feature to build by accident
is one where a player can ask the server to enumerate its own internals.

TWO WAYS TO LOOK, AND BOTH ARE NEEDED.

- **Statically** (`static_scan`), by parsing the game's typeclass source with
  `ast`. Nothing is imported and nothing is executed, so a game whose code has a
  syntax error or an expensive import is still scannable, and scanning cannot
  have side effects.
- **At runtime** (`runtime_scan`), by reading the attributes of a Character that
  already exists. Evennia attributes are database rows: `character.db.hp = 50`
  in a command creates an attribute that appears nowhere in the typeclass
  source, so the static scan cannot see it and the runtime scan can.

Neither is sufficient. A brand-new game has typeclass source and no characters; a
game that sets everything from commands has characters and nothing in its
typeclass. The two are merged, and each candidate says which one found it, so a
developer can judge it.

STATUS: D0 is a spike. What is here defines the boundary, the data model, the
binding schema and the security model, and proves the two scans. The resolver
that turns a binding into a live value is D1, and the declarative providers that
consume it are D2.

"""

# The grammar lives in `bindings`, not here.
#
# D0 defined it in this package because that is where it was being written, and
# D1 moved it: the resolver is runtime code and discovery is a development tool,
# so the live client depending on this package would have been backwards. The
# dependency runs one way now -- discovery imports the binding schema, and
# nothing in `bindings` imports discovery -- which also means the schema has one
# definition rather than one on each side that can drift.
from evennia.contrib.base_systems.aetos_webclient.bindings.schema import (  # noqa: F401
    BINDING_SLOTS,
    EXPRESSION_PATTERN,
    REJECTED_EXPRESSIONS,
    is_valid_expression,
)
from evennia.contrib.base_systems.aetos_webclient.discovery.candidates import (  # noqa: F401
    Candidate,
    CandidateSet,
)
from evennia.contrib.base_systems.aetos_webclient.discovery.roots import (  # noqa: F401
    APPROVED_ROOTS,
    ScanRootError,
    approved_files,
)

__all__ = [
    "Candidate",
    "CandidateSet",
    "APPROVED_ROOTS",
    "ScanRootError",
    "approved_files",
    "BINDING_SLOTS",
    "EXPRESSION_PATTERN",
    "REJECTED_EXPRESSIONS",
    "is_valid_expression",
]
