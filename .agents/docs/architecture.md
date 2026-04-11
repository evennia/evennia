# Evennia Architecture

## Two-Process Model

Evennia runs as two cooperating Twisted processes:

- **Portal** (`server/portal/`) — faces the internet, handles all network protocols (telnet, SSH, SSL, websocket). Stays running during reloads.
- **Server** (`server/`) — runs game logic, Django ORM, commands. Can be reloaded without disconnecting players.

They communicate via an internal AMP (Asynchronous Messaging Protocol) connection.

## Typeclass System

The central abstraction. Every persistent game entity has two layers:

- **Database model** (e.g. `ObjectDB`, `AccountDB`, `ScriptDB`, `ChannelDB`) — Django model, stores data in the database.
- **Typeclass** (e.g. `DefaultObject`, `DefaultCharacter`, `DefaultRoom`, `DefaultExit`) — Python class that adds game logic, linked 1:1 to a DB model via `typeclass_path`.

Typeclasses live in `objects/`, `accounts/`, `scripts/`, `comms/`. The DB models are in `*/models.py`, typeclasses in `*/objects.py`, `*/accounts.py`, `*/scripts.py`, `*/comms.py`.

**Attributes and Tags** (`typeclasses/attributes.py`, `typeclasses/tags.py`) are the key-value and labeling systems stored on any typeclassed object. `AttributeProperty` and `TagProperty` allow declaring them as class-level descriptors.

## Command System

`commands/` — Commands are Python classes inheriting from `Command` (or `MuxCommand` for MUX-style parsing). They are grouped into `CmdSet` objects that merge/override each other on objects, accounts, and sessions.

Flow: input → `cmdhandler.py` (dispatch) → `cmdparser.py` (matching) → `Command.func()` execution.

Default commands are in `commands/default/` organized by category: `general.py`, `building.py`, `admin.py`, `comms.py`, `system.py`, `unloggedin.py`, `account.py`, `help.py`.

## Key Subsystems

- **Scripts** (`scripts/`) — Timed/persistent objects. Houses global handlers: `TICKER_HANDLER`, `MONITOR_HANDLER`, `TASK_HANDLER`, `ON_DEMAND_HANDLER`.
- **Locks** (`locks/`) — String-based permission system parsed at runtime. Lock functions in `lockfuncs.py`.
- **Help** (`help/`) — Database-backed help entries plus auto-generated help from command docstrings.
- **Prototypes** (`prototypes/`) — Dict-based templates for spawning objects via `evennia.spawn()`.
- **Web** (`web/`) — Django views, REST API (`web/api/`), webclient (`web/webclient/`), admin interface.
- **Utils** (`utils/`) — `EvMenu`, `EvTable`, `EvForm`, `EvEditor`, `EvMore`, `FuncParser`, `ANSIString`, `search_*` and `create_*` functions.
- **Contrib** (`contrib/`) — Community modules organized as `base_systems/`, `game_systems/`, `rpg/`, `grid/`, `tutorials/`, `utils/`, `full_systems/`.

## Flat API

`evennia/__init__.py` exposes a flat API — most important classes and functions are accessible as `evennia.DefaultObject`, `evennia.search_object()`, `evennia.create_object()`, etc. This API is lazy-loaded after Django initialization via `_init()`.

## Settings

`settings_default.py` (~1850 lines) is the master settings template. Game developers override specific values in their game dir's `server/conf/settings.py`. Never modify `settings_default.py` directly for a game — only when changing Evennia's own defaults.
