# Core Beliefs

Design principles that inform implementation decisions in Evennia. When in doubt, these guide tradeoffs.

## Evennia is a toolkit, not a game

Evennia provides infrastructure (networking, persistence, command routing) without imposing genre, mechanics, or game style. Never add features that assume a specific type of game. Keep the core generic — game-specific systems belong in `contrib/` or downstream game code.

## Think in Python, not SQL

The typeclass system exists so developers work with Python classes, not database schemas. One `ObjectDB` table holds all objects; the `db_typeclass_path` field points to the Python class that gives it behavior. New entity types are created by subclassing in Python, not by adding database tables. Attributes (`db` handler) store arbitrary Python data without schema changes.

## Extend through hooks, not patches

Objects define clear hook methods called at specific lifecycle points (`at_object_creation`, `at_init`, `at_pre_move`, `at_look`, etc.). New behavior goes in hook overrides, not by modifying core internals. This keeps custom code predictable and upgrade-safe.

## Compose, don't branch

CommandSets merge using set operations (union, intersection, difference). Adding a CmdSet and then removing it restores the original state. This allows layering complex states (combat + darkness + status effects) without nested conditionals. Prefer composable, removable components over boolean flags.

## Fail closed

The lock system denies access by default. Everything is inaccessible unless explicitly permitted. When designing access checks, start locked and whitelist — don't start open and blacklist.

## Objects carry their own state

Handlers (Attributes, Tags, Locks, Scripts, Commands) attach directly to objects. State and behavior travel with the object, not in external registries. The idmapper cache ensures you always get the same Python instance for a given database object, so on-object state is reliable.

## Portal and Server are separate concerns

The Portal handles network protocols and stays running across reloads. The Server handles game logic and can be hot-reloaded. Neither knows the other's internals — they communicate via AMP. Don't leak protocol details into game logic or vice versa.

## The framework should be complete

Evennia includes its own web server, webclient, admin interface, and REST API. All connection methods (telnet, websocket, SSH) use the same game objects. Avoid requiring external services for core functionality.

## Keep the schema simple

Complexity grows through Python objects (typeclasses, attributes, tags), not through database tables. The core schema is intentionally minimal and stable. Resist adding new models — use Attributes and Tags on existing models instead when possible.
