# Aetos Web Client

Contribution by Gary E Mix, 2026

A genre-agnostic graphical webclient framework for Evennia. Aetos replaces the
stock webclient interface while leaving Evennia's transport layer -- `evennia.js`
and the Portal websocket -- completely untouched.

Install it and you immediately get a better client on an ordinary Evennia game,
with no changes to your game code. Teach it about your game's data and it becomes
your game's graphical interface.

Aetos makes no assumptions about genre, combat, magic, character model, map
format, inventory, or resources. Anything a game does not expose simply does not
appear.

## Features

Everything below works today and is covered by tests.

### Out of the box, on a pristine game

No game code, no settings beyond installation.

- Replaces the stock GUI while reusing Evennia's transport unmodified
- Console with bounded scrollback and full ANSI / xterm-256 colour
- Room, exits, people and items panels, honouring your `view` and `search` locks
- Inventory panel, from ordinary `contents`
- Local map built by walking exits the character can actually see, with a
  written equivalent generated from the same data
- Context menus on every listed entity, offering `look`, `get` and `drop`
- Movement and route-walking by clicking the map, one ordinary command at a time
- Command palette (`Ctrl+K`) and in-client help (`F1`)
- Layout editing, workspaces, and a responsive layout from phone to wide monitor

### When your game exposes them

Progressive enhancement: declare a feature and supply a provider, and the
matching interface appears. Declare nothing and nothing appears.

- Generic resource meters with thresholds and spoken announcements
- Equipment by slot, current target, and temporary effects with countdowns
- Game-supplied context actions on any entity

### Player tools, stored only in the player's browser

- Hotbars and macros of up to five commands, run through a visible queue
- Aliases with `$1`/`$*` argument substitution
- Triggers on game output, plain text or regular expression, rate limited
- Timers on a schedule
- Aetos Script: a small sandboxed language with a purpose-built interpreter
- Private notes, relationship tags, map notes and points of interest
- Profile export and import as a single JSON file
- A privacy panel reporting what is stored, counted from storage

### Reading, reviewing and presentation

- Full session history with search, and a Review Mode that pins the console to
  a moment so you can read around it without losing what arrives next
- Non-destructive display rules: filter or highlight output without the record
  of what happened being altered
- Automation groups -- switch a whole set of your macros, aliases and triggers
  on or off together, for a fight or for a shop
- Themes with automatic contrast validation, so a theme cannot ship a
  combination that fails to be readable
- Audio and multimedia with a durable caption list, and per-category volume

### Installable, and honest when offline

- Installs as an application on browsers that support it, with its own window
- Offline, the client's own files load and say clearly that the game has not.
  **No game output is ever cached** -- that would be a copy of a player's
  session sitting on their device
- On a dropped connection, every panel dims and says that what it shows is the
  last state received. Commands typed while disconnected are refused and said
  to be refused, rather than reported as sent and quietly lost
- Touch gestures on phones and tablets, each with a keyboard equivalent

### For people building on it

- A documented widget SDK: third-party widgets get the same contract the
  built-in ones have, including failure isolation -- a widget that throws is
  disabled on its own and takes nothing else with it
- A developer inspector showing the live protocol, providers, state and events
- `AETOS_UI`: describe your interface's resources and panels from settings,
  with no client code at all
- Capture and replay of a session as JSONL, for reproducing a bug exactly

### Throughout

- Versioned protocol with handshake and capability manifest
- Provider system for exposing your game's data without editing Aetos
- Allowlist sanitisation of all server-provided markup; `innerHTML` is never used
- A Content-Security-Policy on the client page: no inline script, no `eval`
- Keyboard operation of everything; colour never carries meaning alone
- Startup checks that report a misconfigured install by name, with the fix
- No CDN, no build step, no JavaScript framework

**Still to come:** voice input and speech accessibility, and the
assistive-technology validation described under Accessibility below. See the
project repository for the full roadmap.

## Installation

Add the following to your game's `server/conf/settings.py`:

```python
from evennia.contrib.base_systems.aetos_webclient import AETOS_TEMPLATE_DIR

INSTALLED_APPS += ["evennia.contrib.base_systems.aetos_webclient"]
TEMPLATES[0]["DIRS"].insert(0, AETOS_TEMPLATE_DIR)
INPUT_FUNC_MODULES.append("evennia.contrib.base_systems.aetos_webclient.inputfuncs")
```

Then restart so that static assets are collected:

```
evennia reload
```

Aetos now serves at your existing webclient URL (`/webclient/` by default). No
files are copied into your game directory and no Evennia file is modified.

### What each line does

`TEMPLATES[0]["DIRS"].insert(...)` is what makes Aetos's `webclient.html` take
precedence over Evennia's. It cannot be omitted: Django searches every `DIRS`
entry before any installed app, and Evennia always places its own
`web/templates/webclient` in `DIRS`, so registering the app alone would never win.

`INSTALLED_APPS` is what makes Django's `AppDirectoriesFinder` discover Aetos's
static assets, so `collectstatic` picks them up without further configuration.

`INPUT_FUNC_MODULES` registers the two server-side handlers Aetos adds: the
`aetos_hello` handshake, which replies with the manifest describing what your game
exposes, and `aetos_request_sync`, which the client uses to ask for fresh state.
Those two are the entire server-side surface. Without them the client still loads
and plays, but the server logs an
"Input command not recognized" error on every connect and no manifest is sent, so
no progressive-enhancement features appear.

> Note: setting `WEBCLIENT_TEMPLATE` does **not** work for this. Evennia builds
> the `TEMPLATES` list at import time in `settings_default`, so reassigning
> `WEBCLIENT_TEMPLATE` in your own settings has no effect on the already-built
> list.

## Uninstalling

Delete the block above and restart. The stock webclient returns unchanged.

## Configuration

Aetos requires no configuration. Everything below is optional, and every setting
is checked at `evennia start` -- a malformed one is reported by name with the fix
in the message, rather than surfacing later as a feature that quietly does not
appear.

| Setting | What it does | Documented in |
|---|---|---|
| `AETOS_PROVIDERS` | Where your game's data comes from, one dotted path per slot | [Teaching Aetos about your game](#teaching-aetos-about-your-game) |
| `AETOS_FEATURES` | Which structured subsystems your game exposes | below |
| `AETOS_AUTOMATION` | What the client is permitted to offer players | below |
| `AETOS_UI` | Names, order and announcement thresholds for your resources and panels, from settings alone | below |
| `AETOS_BINDINGS` | Where a value lives, so a resource needs no provider class | [Bindings](#bindings----a-resource-bar-with-no-python-at-all) |
| `AETOS_DIAGNOSTICS` | Whether the developer inspector and capture tools are available | below |
| `AETOS_CSP` | Extra sources for the client page's Content-Security-Policy | [Security](#security) |

### Automation policy

What the client is permitted to offer. Defaults shown:

```python
AETOS_AUTOMATION = {
    "macros": True,
    "aliases": True,
    "triggers": True,
    "timers": False,
    "scripting": False,
    "voice": True,
}
```

The client honours these. With `scripting` false, no scripting editor is offered
at all. These are policy, not security: they shape the interface, while the server
remains the thing that decides whether any command succeeds.

**`voice` is reserved and nothing honours it yet.** Voice input is not built, so
there is no spoken input for the flag to govern. It is in the defaults so that
setting it is not an error and so the capability has its place, but setting it
today changes nothing.

### Features

Which structured subsystems your game exposes. All default to `False`, which is
why a pristine game gets a clean client rather than empty widgets:

```python
AETOS_FEATURES = {"resources": True, "map": True}
```

### Describing your interface

`AETOS_UI` names things and orders them. It says a resource called `health`
exists, what to call it, where it sits and when it is worth announcing -- and it
says nothing about where the number comes from, which is a provider's job. That
separation is deliberate: you can describe your interface today and change how
the values are sourced later without rewriting any of this.

```python
AETOS_UI = {
    "resources": [
        {
            "id": "health",
            "label": "Vitality",
            "order": 1,
            "thresholds": [
                {"at": 0.25, "label": "badly hurt", "level": "critical"},
                {"at": 0.5, "label": "hurt", "level": "warning"},
            ],
        },
    ],
    "panels": {"inventory": {"title": "Pack"}},
}
```

Unknown sections, unknown panels and unknown threshold keys are refused with an
error naming what would have been valid. A typo in a settings key is otherwise
silent, and a developer who believed they had renamed a gauge would simply never
see it change.

### Developer tools

Off by default, because the inspector shows the live protocol and session state:

```python
AETOS_DIAGNOSTICS = True
```

With it on, the client offers a developer inspector -- providers, manifest, live
events, layout and storage -- and the ability to capture a session to a JSONL
file and replay it. Useful when a player reports something you cannot reproduce.

## Teaching Aetos about your game

There are four levels, and most games stop at the second.

| Level | What you write | When |
|---|---|---|
| 0 | nothing | a stock game already works: room, exits, people, items, inventory, map, movement |
| 1 | `AETOS_BINDINGS` in settings | your game keeps a value on the character -- `db.hp`, `db.oxygen` -- and you want it on screen |
| 2 | `AETOS_UI` in settings | you want to rename, reorder or set announcement thresholds for what you already have |
| 3 | a provider class | the value has to be calculated, or lives somewhere a setting cannot name |

**Not sure what your game has?** `evennia aetos discover` reads it and suggests
the bindings; `evennia aetos setup` walks you through them one at a time and
reads each value off a live character so you see the number before you keep it.
Neither changes anything -- see [Finding what to bind](#finding-what-to-bind).

The Aetos Web Client never guesses, scans, or assumes your game's data model
**during gameplay**. You explicitly bind game data to Aetos fields or supply a
provider. The optional server-side Aetos Discovery tool can inspect your game
**during development** and suggest those bindings for you.

### Bindings -- a resource bar with no Python at all

If your game already keeps the value on the character, you do not need a provider
class. Declare where it lives:

```python
AETOS_BINDINGS = {
    "resources": {
        "health": {"label": "Health", "value": "db.hp", "maximum": "db.hp_max"},
    },
}
```

That is the whole integration. No class, no import path, no file.

A binding is a **path, not an expression**. Aetos reads `db.name`, or
`db.name.child` for a key inside a dict you stored in an attribute, and nothing
else -- no method calls, no indexing, no arithmetic. If a value has to be
*computed*, that is what a provider is for. The restriction is deliberate: a
setting that could compute would be a small programming language living in
settings.py, and there would be no way back from the first "just this one
exception".

**A binding switches its own feature flag on.** You do not also have to set
`AETOS_FEATURES = {"resources": True}` -- declaring the binding said that. If you
set the flag explicitly it wins, in both directions, so `False` still turns the
widget off.

**Precedence is custom > binding > default.** A provider class you wrote always
wins over a binding for the same slot, so migrating between them is never
ambiguous.

#### The other four slots

`equipment`, `effects`, `target` and `actions` are declared the same way.

```python
AETOS_BINDINGS = {
    "equipment": {
        "weapon": {"label": "Weapon", "value": "db.gear.weapon"},
        "head": {"label": "Head", "value": "db.gear.head"},
    },
    "effects": {
        "poison": {"label": "Poisoned", "value": "db.poison",
                   "remaining": "db.poison_left", "kind": "harmful"},
    },
    "target": {
        "name": {"label": "Target", "value": "db.target_name"},
        "health": {"label": "Health", "value": "db.target_hp",
                   "maximum": "db.target_max"},
    },
    "actions": {
        "attack": {"label": "Attack", "command": "attack {target}"},
    },
}
```

Each has one rule worth knowing:

- **Equipment keeps its empty slots.** "Nothing on your head" is information a
  player needs. (A resource that will not resolve is *dropped*, because that
  means the game never had the number — a bar reading 0 would say something
  false.)
- **An effect is shown when its value is truthy**, so `True` and a stack count
  both work. Zero is not active: a countdown that reached 0 has expired.
- **`target` has one reserved key, `name`.** It supplies the target's identity;
  every other entry becomes one of the target's resources, which go through the
  same normaliser as your own — so the two bars cannot disagree about
  thresholds or rounding. No name, no target.
- **An action is a label and an ordinary command**, with `{target}` replaced by
  the name of the entity whose menu was opened. Offering an action does not make
  it legal: the command travels the ordinary command path and your server decides,
  exactly as if the player had typed it.

#### What a binding cannot do

**Declare thresholds.** A resource with no thresholds is never announced, so a
game that wants spoken announcements at meaningful crossings still needs
`AETOS_UI` or a provider. That is a real limit of the zero-code path rather than
an oversight.

#### Finding what to bind

```
evennia aetos discover
```

reads your typeclass source -- parsed, never imported, so running it cannot have
side effects -- the attributes of characters that already exist, and the
Character typeclass and commands Evennia has loaded for them. In source it
recognises `self.db.hp = 100`, `attributes.add("hp", 100)`,
`hp = AttributeProperty(100)`, reads like `character.db.mana`, and your own
`Command` classes. It prints a
suggested `AETOS_BINDINGS` block with the evidence for every line. It changes
nothing and never writes to your settings; you paste what you want.

```
evennia aetos discover --character #12
```

reads one character you choose instead of a sample of the newest. Worth doing:
a character mid-way through your game carries what a fresh one does not.
`--typeclass` samples a different typeclass, and its subclasses.

Every suggestion is marked `HIGH`, `MEDIUM` or `LOW`, and says what was found,
where, why it might matter, and what accepting it would put on screen. `LOW`
entries are printed **commented out**, so pasting the block unchanged activates
only what discovery could justify. A value and its ceiling are paired by
structure -- `oxygen` with `oxygen_capacity`, `hull_integrity` with
`hull_capacity` -- not from a list of fantasy stat names.

It is bounded, and says when a bound was hit rather than truncating quietly: it
will tell you how many files it did not scan, and name any file it skipped for
being too large. A source file whose *name* looks like it holds credentials --
`world/api_keys.py` -- is skipped without being read.

### The guided version

```
evennia aetos setup
```

walks the same suggestions one at a time, and does the thing a printed report
cannot: it **reads each expression off a live character and shows you the
number** before asking whether to keep it. A binding that resolves to nothing
looks exactly like a correct one until you have a browser open and a bar
missing.

For each candidate you can accept it, edit it (a label or an expression, without
editing Python), ignore it, or ask it to explain itself. At the end it writes
what you accepted to `aetos-discovery/`:

```
aetos-discovery/
├── report.txt               what was read, accepted, ignored and warned about
├── suggested_bindings.py    the accepted candidates, ready to paste
└── suggested_provider.py    only when a binding genuinely cannot reach a value
```

Nothing in that directory is imported by anything, and your `settings.py` is
never touched -- you copy across what you want. Quitting part-way writes
nothing.

Two things it deliberately will not do. Attributes whose names look like
credentials (`password`, `token`, `api_key` and similar) are never read, printed
or suggested; the report shows `<redacted>` in their place. And values behind a
handler -- `character.stats.get("health")` -- are never turned into a binding,
because a binding cannot call anything. Discovery names the handler and points
you at a provider instead.

### Providers -- advanced, for values a setting cannot name

Reach for this when a binding cannot do the job: the value is calculated, comes
from a handler you have to call, or is assembled from several places. If your
game simply keeps it on the character, a binding is the shorter road and needs
no Python at all.

Aetos never assumes where you store anything:

```python
AETOS_PROVIDERS = {
    "resources": "world.aetos.MyResourceProvider",
}
```

Unlisted slots keep their defaults, so you override one without restating the
rest.

| Slot | Default | What it supplies |
| --- | --- | --- |
| `entities` | works out of the box | what is in the room |
| `map` | works out of the box | the local room and exit graph |
| `inventory` | works out of the box | what a character carries |
| `actions` | `look` / `get` / `drop` | context-menu commands |
| `resources` | exposes nothing | whatever your game measures |
| `equipment` | exposes nothing | equipped items, by slot |
| `target` | exposes nothing | the current target |
| `effects` | exposes nothing | temporary conditions |

The four defaults that work use nothing but ordinary rooms, contents and exits,
and honour your `view` and `search` locks, so hidden objects and secret exits
stay hidden.

The four that expose nothing do so deliberately. There is no genre-neutral way
to guess what your game's resources are, what its equipment slots are called, or
whether it has a notion of a current target -- so Aetos shows no widget rather
than an empty one implying a system you do not have.

A worked example:

```python
# world/aetos.py
from evennia.contrib.base_systems.aetos_webclient.providers.base import (
    AetosResourceProvider,
)


class MyResources(AetosResourceProvider):
    def get_resources(self, character):
        return [
            {
                "id": "health",
                "label": "Health",
                "value": character.db.hp or 0,
                "maximum": character.db.hp_max or 100,
                "thresholds": [
                    {"at": 0.25, "level": "warning", "message": "Health is low."},
                ],
            }
        ]
```

```python
# server/conf/settings.py
AETOS_PROVIDERS = {"resources": "world.aetos.MyResources"}
AETOS_FEATURES = {"resources": True}
```

### Real-time updates (optional)

By default the client asks for a sync after connecting and after each command it
sends, which needs no cooperation from your game. If you want true push, call
`push_sync` from your own hooks:

```python
from evennia.contrib.base_systems.aetos_webclient import state


class Character(DefaultCharacter):
    def at_post_move(self, source_location, **kwargs):
        super().at_post_move(source_location, **kwargs)
        for session in self.sessions.all():
            state.push_sync(session, self)
```

A misconfigured provider fails at startup with a message naming the setting and
the import that failed. A provider that raises at runtime is contained: you lose
that widget, not the player's session.

## Local data and privacy

Aetos never stores personal player data on your server. Layouts, workspaces,
notes, relationship tags, map notes, macros, aliases, triggers, timers, scripts,
keybindings and preferences all live in the player's own browser, scoped to your
game's origin.

This is structural rather than a policy. The contrib adds no models and no
migrations, installing it creates no database rows, and it registers exactly two
input functions -- the handshake and a sync request. There is no code path that
could send player configuration to your server.

Players can see everything stored, export it as a single JSON file, and delete
it, from the client's own privacy panel.

The server keeps only the transient session state the protocol needs.

## Server authority

Aetos is never authoritative for game mechanics. A button labelled "Attack
Goblin" sends exactly the text `attack goblin`, identical to a player typing it.
Locks, cooldowns, permissions and command availability are enforced by your
server exactly as they always were. Nothing in Aetos can bypass a command.

## Accessibility

Accessibility is not a feature of Aetos; it is one of the mechanisms by which
Aetos is built. It is governed by a normative specification, Addendum A, whose
`A11Y-` requirement IDs are release gates rather than aspirations.

**You cannot switch it off, and you are not asked to.** `AETOS_AUTOMATION`
governs gameplay automation -- whether players may script or use timers. It does
not govern whether a player gets a usable interface. Semantic HTML, keyboard
operation, focus management, accessible labels, non-drag alternatives, contrast
and reduced-motion support are always present.

### What your players get, with no work from you

- Every function is operable from the keyboard. Dragging is never the only path.
- Combat spam never floods speech. The transcript is a `role="log"` region with
  `aria-live="off"` set deliberately, so a screen reader is not made to read
  every line as it arrives -- the full text stays reviewable on demand.
- One central announcer. No widget owns its own live region, so nothing competes
  for speech.
- No character-only keyboard shortcuts, which would collide with the single
  letters NVDA and JAWS use for structural navigation.
- Colour never carries meaning alone. Severity, effect tone and status are
  written in words.
- The map has a text equivalent generated from the *same* graph as the picture,
  so the two cannot disagree.
- Game events never move focus. Dialogs trap focus and return it where they
  found it.

### The Settings dashboard

A **Settings** button in the status bar opens one place listing everything a
player can configure: display and accessibility, themes, automation groups,
reminders, symbol packs, privacy, and profile export/import. Every destination
existed before; none of them had a way in other than the command palette.

**A second section appears for game developers when you set
`AETOS_DIAGNOSTICS = True`** — the inspector, the diagnostics report, the
automation validator and the contrast report. Those describe *your game's*
configuration rather than the player's client, which is why they are opt-in.

Two things worth being plain about:

- **It is game-wide, not per-account.** Everybody on a game with diagnostics on
  sees that section. Aetos is not told who is staff; per-account gating needs a
  field in the manifest and is not built yet.
- **It grants no authority.** The inspector shows a player their own session and
  the report names your provider classes. Hiding the section is tidiness, not a
  security boundary, and the panel says so on screen rather than implying
  otherwise.

### Two modes, and two control panels

At the top right there is a switch labelled **Accessible mode** (also
`Ctrl+Shift+A` from anywhere). It moves between two interfaces rather than trying
to be both at once.

**Standard mode is the client as it comes.** Nothing is compromised to
accommodate anybody, because the accommodations are not applied.

**Accessible mode applies what the player chose.** Every option is separate;
there is no bundle to accept or refuse.

**Switching back to standard stops them applying and erases nothing.** That is
what makes the switch safe to try: the way back is one keystroke, and it restores
the interface somebody built rather than an empty one. Leaving says so out loud,
names what stopped, and gives the keystroke.

Beside the switch is an **Options** button, and it works in both modes:

| | Standard mode | Accessible mode |
|---|---|---|
| Text size | ✔ | ✔ |
| Sound and mute | ✔ | ✔ |
| Touch gestures | ✔ | ✔ |
| Orientation help | ✔ | ✔ |
| Contrast, motion, visual detail | | ✔ |
| Announcement verbosity | | ✔ |
| Quiet and focus modes | | ✔ |
| Picture and word board | | ✔ |

**Text size is in both, deliberately.** Being able to set the size of text is not
an accommodation somebody opts into; it is a basic property of a text interface,
and browser zoom scales the page rather than the client. It survives the mode
switch, and `Larger text` / `Smaller text` are palette commands so nobody has to
open a settings panel they cannot read.

The four options in the left column are never reverted by the mode, because
their *off* state is the accommodation: reverting mute would start playing sound
at somebody, and reverting gestures would switch them back on for the person who
turned them off.

**None of this reaches the baseline.** Keyboard operation, focus management,
landmarks, accessible names, the announcer and colour never carrying meaning
alone are unconditional in both modes. A client that is only operable by keyboard
when a box is ticked is not an accessible client with a toggle; it is an
inaccessible client with an apology. The panel lists them under "Always on", so
somebody deciding whether to switch can see what was never off.

### What a player can turn on for themselves

These are what accessible mode applies. None of them needs anything from you, and
all of them are stored in the player's own browser:

- A contrast and colour-scheme choice, with every theme validated against WCAG
  contrast ratios before it can be applied -- a theme cannot ship a combination
  that is not readable
- Reduced motion and reduced stimulation, honouring the operating system's own
  setting as the default
- Announcement verbosity, so a player decides what is worth speaking rather than
  Aetos deciding for them
- A simplified layout that reduces what is on screen at once. Nothing is
  removed: every feature is still reachable, and it can be switched back
- Orientation help -- where you are, how you got here, and how to go back --
  built only from moves the game confirmed, never from guesses about intent
- Reminders and a resume card, for picking up an interrupted session
- A picture-and-word board for composing commands from symbols rather than
  spelling them. **This is not a claim of AAC support**; see the honest status
  below

### What only you can supply

Aetos can make an ordinary Evennia game substantially more accessible. It cannot
invent information your game does not expose.

- **Captions for meaningful audio.** No caption can be reliably invented. If a
  sound carries information, describe it in the media descriptor.
- **`state_text` on resources** -- a short word for a value, so a bar reads as
  "healthy" rather than only as a number.
- **`description` on actions**, where the label alone is ambiguous.
- **`importance_hint`** on state events, if you want to advise which changes
  matter. It is advisory only; the player's own preference always decides what
  is spoken.

### Honest status

This project is **designed toward WCAG 2.2 Level AA**. It does not claim
compliance, JAWS compatibility or braille compatibility, because the
assistive-technology testing that would justify those claims has not yet been
done. Testing against NVDA, JAWS, Orca and refreshable braille is a scheduled
release gate, and no claim will ship ahead of its evidence.

The same applies to the picture-and-word board. It is a symbol-supported way to
compose commands, and it has not been reviewed by anyone who works with
augmentative and alternative communication. Until it has, Aetos does not
describe itself as supporting AAC -- the architecture is there, the judgement
that it serves the people it is for is not.

Automated accessibility testing runs on every release and currently reports no
violations at any severity. That is worth exactly what it is worth: it finds
missing names, broken roles and unreachable regions. It cannot tell whether a
label means anything, whether a task takes forty keystrokes, or whether a braille
display keeps losing its place.

## Security

All server-provided markup is parsed in an inert document and rebuilt from an
allowlist of elements and attributes. Aetos never uses `innerHTML`. Elements
outside the allowlist are replaced by their text content rather than discarded, so
game output is never silently lost. Nesting deeper than 64 levels is flattened to
text rather than followed, so hostile markup cannot exhaust the stack in the code
path that draws your game's output.

Aetos evaluates no JavaScript at runtime. The scripting language players can
write is tokenised, parsed and interpreted from its own syntax tree; `eval` and
`Function` appear nowhere in the client.

### Content-Security-Policy

The client page carries its own policy:

```text
default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';
connect-src 'self' ws: wss:; img-src 'self' data: https:;
media-src 'self' https:; font-src 'self'; object-src 'none'; frame-src 'none';
form-action 'none'; base-uri 'none'; worker-src 'self'; manifest-src 'self'
```

It is declared in the document rather than sent as a header, because a contrib
does not own the webclient view, and middleware would apply the policy to your
whole website -- front page, admin, wiki -- which is not a decision a webclient
should make on your behalf.

**Two things that costs you, stated plainly:**

- **`frame-ancestors` cannot be expressed in a `<meta>` policy.** Neither can
  `report-uri` or `sandbox`. If you want clickjacking protection, send
  `X-Frame-Options: SAMEORIGIN` or a real `Content-Security-Policy` header with
  `frame-ancestors` from your own web server or middleware. Aetos will refuse
  `AETOS_CSP = {"frame-ancestors": ...}` with an error rather than let you
  believe it took effect.
- **`style-src` needs `'unsafe-inline'`.** Theme tokens and layout sizes are
  written as inline styles. This permits no script execution, and the sanitiser
  accepts no `style` attribute or `<style>` element from game content at all, so
  there is no injection point for it to widen.

If your game serves media, fonts or scripts from another host, add them --
sources are added to the defaults rather than replacing them:

```python
AETOS_CSP = {"img-src": ["https://cdn.example.com"]}
```

To send your own header instead, turn the page's policy off. Do not run both:
two policies both apply and the result is their intersection, which is very hard
to debug.

```python
AETOS_CSP = False
```

### Rate limiting

Aetos adds no throttle of its own. Every message a client sends -- including
`aetos_hello` and `aetos_request_sync` -- passes through Evennia's Portal, which
applies `MAX_COMMAND_RATE` to all input rather than only to typed commands. A
client that exceeds it gets `COMMAND_RATE_WARNING` and its excess is dropped. If
you want Aetos's sync requests limited differently, change that setting; a second
throttle inside the contrib would only be able to disagree with the first.

## Requirements

Core Evennia only. Aetos adds no Python dependencies, requires no Node or
JavaScript build tooling, and declares no Python version constraint of its own --
it supports whatever your Evennia supports.

**Browsers:** Chrome/Edge 87+, Firefox 75+, Safari 14.1+ (2020-2021). The limit
comes from CSS layout features, not from JavaScript: Aetos is written in ES5 plus
promises, because a syntax the browser cannot parse takes the whole file with it
while a missing layout feature only makes the spacing wrong.

Below that floor the client still loads and plays; spacing degrades. The full
matrix, including what each optional feature falls back to and **which platforms
have actually been tested rather than merely expected to work**, is in the project
repository's `docs/compatibility.md`.

## Help for your players

Aetos documents itself. `F1` -- or "Help" in the command palette -- opens a
searchable reference covering every feature, with worked examples.

Topics are gated on your automation policy, so a game with `scripting` disabled
has no scripting topic. Documenting a feature a player cannot use sends them
looking for a button that is not there.

The last topic is written for you rather than your players: provider examples,
settings, and the full slot list.

## Troubleshooting

**Start here: read what `evennia start` printed.** Aetos checks its own
installation and settings at startup and reports problems by name, with the fix
in the message. They are warnings rather than errors, so the game still starts --
a typo in a webclient setting should not stop a MUD that also serves telnet.

| Code | Meaning |
|---|---|
| `aetos.W001` | The template directory is not in `TEMPLATES[0]["DIRS"]`, so the stock client is being served |
| `aetos.W002` | It is there, but after a directory that also has a `webclient.html`, so it still loses -- `append` instead of `insert(0, ...)` |
| `aetos.W003` | The input handlers are not registered, so no manifest is sent and no configured features appear |
| `aetos.W01x` | One of the `AETOS_*` settings is malformed; the message names the key |

**The checks themselves are silent.** They are registered by Aetos's app config,
so they only run when the app is in `INSTALLED_APPS`. If you are seeing no Aetos
warnings *and* no Aetos, that line is the one to check first.

**The stock client still appears.** The `TEMPLATES` insert is missing or ran
before `settings_default` was imported. It must come after the
`from evennia.settings_default import *` line. `aetos.W001` and `aetos.W002`
catch both shapes of this.

**Styles or scripts 404.** Static files were not collected. Restart with
`evennia reload`, which runs `collectstatic`.

**Colours show as literal tags.** `ansi.css` is not being served; check the same
static-file setup as above.
