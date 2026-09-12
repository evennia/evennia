"""
Pass 2 -- Evennia structural inspection (Addendum B.22).

The attribute scan reads what a character *carries*. This reads what the game
*declares*: the typeclass a character is, the `AttributeProperty` fields it
defines, the handlers it hangs off itself, and the commands it has. Three of
those can produce suggestions and one can only produce advice, and the
difference is the most important thing in this module.

**Handlers produce advice, never a binding.** Addendum B.66's complex game keeps
health at `character.stats.get("health").current`. That is a method call, the
grammar has no way to express one, and it never will -- the grammar is the
security boundary of the whole D-track. So when a typeclass has a handler of the
game's own, discovery names it and says a provider class is the supported route.
Guessing an expression that "probably" reaches the value would be the resolver
becoming an evaluator by the back door.

WHAT COUNTS AS "THE GAME'S OWN". Everything outside Evennia's core. A module
under `evennia.contrib.` counts as the game's, because a game that added a
contrib chose that feature exactly as it would have chosen code of its own --
the traits contrib's handler is precisely the case B.66 is about.

HOW THIS STAYS READ-ONLY. It only looks at classes that are already loaded,
because they belong to characters the runtime scan already fetched. Members are
read with `vars()` on each class in the MRO, never `getattr`: `getattr` on a
descriptor runs it, and an `AttributeProperty` read that way would go to the
database for a class that has no instance. Commands are read off command sets
Evennia had already built for the character.

"""

import re

from django.conf import settings

from evennia.contrib.base_systems.aetos_webclient.discovery import (
    confidence,
    redaction,
    values,
)
from evennia.contrib.base_systems.aetos_webclient.discovery.candidates import (
    ActionCandidate,
    Candidate,
)
from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils.utils import lazy_property

#: How many distinct character typeclasses are described. A sample of
#: twenty-five characters is usually one or two classes; this bounds the odd
#: game that gives every character its own.
MAX_CLASSES = 5

#: Permission lock functions whose argument is a level in the hierarchy.
_PERMISSION_CHECK = re.compile(
    r"\b(?:perm|perm_above|pperm|pperm_above)\(\s*['\"]?([A-Za-z_]+)['\"]?\s*\)"
)

#: The key Evennia gives the empty command set it substitutes when a real one
#: fails to import (`evennia.commands.cmdsethandler._ErrorCmdSet`).
ERROR_CMDSET_KEY = "_CMDSET_ERROR"

#: A line that introduces a command's usage in Evennia's docstring convention.
_USAGE_HEADING = re.compile(r"^\s*usage\s*:?\s*$", re.IGNORECASE)


def is_core(module):
    """
    Whether a module is part of Evennia itself rather than the game.

    Args:
        module (str): A dotted module path.

    Returns:
        bool: True under `evennia.` but not under `evennia.contrib.`.

    """
    module = module or ""
    return module.startswith("evennia.") and not module.startswith("evennia.contrib.")


def lineage(klass):
    """
    A typeclass's ancestry, from the game's class to the first Evennia base.

    Args:
        klass (type): The character's class.

    Returns:
        list: Dotted paths, most specific first. Stops at the first core
            Evennia class: everything above `DefaultCharacter` is the same in
            every game and says nothing about this one.

    """
    chain = []
    for cls in klass.__mro__:
        chain.append("%s.%s" % (cls.__module__, cls.__name__))
        if is_core(cls.__module__):
            break
    return chain


def _members(klass):
    """
    Every class-level member, with the class that defined it.

    Args:
        klass (type): The class.

    Returns:
        dict: `name -> (defining class, member)`, subclasses overriding bases.

    Notes:
        `vars()`, not `getattr()`. A descriptor read with `getattr` runs.

    """
    members = {}
    for cls in reversed(klass.__mro__):
        for name, member in vars(cls).items():
            members[name] = (cls, member)
    return members


def declared_attributes(klass):
    """
    `AttributeProperty` fields the game declared on a typeclass.

    Args:
        klass (type): The character's class.

    Returns:
        tuple: `(candidates, problems)`.

    Notes:
        A declared field is source evidence that does not need a parse: the
        class is loaded, so the declaration can be read directly. Its default is
        the class-level constant the developer wrote, which is safe to look at
        and says what kind the value is meant to be.

    """
    candidates, problems = [], []
    for name, (owner, member) in sorted(_members(klass).items()):
        if not isinstance(member, AttributeProperty) or is_core(owner.__module__):
            continue
        if not name.isidentifier() or name.startswith("__"):
            continue
        if redaction.is_sensitive(name):
            problems.append(
                "%s.%s is declared on the typeclass and its name looks like a credential, "
                "so it is not suggested (%s = %s)"
                % (owner.__name__, name, name, redaction.REDACTED)
            )
            continue
        category = getattr(member, "_category", None)
        if category:
            problems.append(
                "%s.%s is declared with category %r. The binding grammar reaches "
                "uncategorised attributes only; a provider class in AETOS_PROVIDERS "
                "can read it." % (owner.__name__, name, category)
            )
            continue

        default = getattr(member, "_default", None)
        plain = default is not None and not callable(default)
        kind = values.kind_of(default) if plain else "unknown"
        candidates.append(
            Candidate(
                expression="db.%s" % name,
                name=name,
                origin="typeclass",
                evidence="declared on %s as AttributeProperty(%s)"
                % (owner.__name__, values.shown(default) if plain else "..."),
                kind=kind,
            )
        )
    return candidates, problems


def handler_notes(klass):
    """
    Advice about handlers the game hangs off its characters.

    Args:
        klass (type): The character's class.

    Returns:
        list: One sentence per game handler, each recommending a provider.

    """
    notes = []
    for name, (owner, member) in sorted(_members(klass).items()):
        if not isinstance(member, lazy_property):
            continue
        module = getattr(member, "__module__", "") or owner.__module__
        if is_core(module):
            continue
        notes.append(
            "%s.%s is a handler defined in %s. Values behind a handler are reached by "
            "calling it -- character.%s.get(...) -- which a binding never does, so "
            "nothing is suggested for it. If what you want on screen lives there, a "
            "provider class in AETOS_PROVIDERS is the supported route."
            % (owner.__name__, name, module, name)
        )
    return notes


def permission_hierarchy():
    """
    The game's permission levels and the floor an ordinary account sits at.

    Returns:
        tuple: `(levels lowest-first in lower case, index of the default)`.

    """
    hierarchy = [level.lower() for level in (getattr(settings, "PERMISSION_HIERARCHY", []) or [])]
    default = (getattr(settings, "PERMISSION_ACCOUNT_DEFAULT", "Player") or "Player").lower()
    return hierarchy, (hierarchy.index(default) if default in hierarchy else 0)


def restricted(lockstring, hierarchy, floor):
    """
    Whether a command's `cmd` lock needs more than an ordinary player has.

    Args:
        lockstring (str): The command's lock string.
        hierarchy (list): Permission names, lowest first, lower case.
        floor (int): The index of the level new accounts get.

    Returns:
        bool: True for staff-only and hidden commands.

    Notes:
        Read from the lock string and never by calling the lock. Evaluating a
        lock runs lock functions, and a lock function is the game's code.

    """
    for part in str(lockstring or "").split(";"):
        access, _, rule = part.partition(":")
        if access.strip() != "cmd":
            continue
        rule = rule.strip().lower()
        if rule.startswith("false()"):
            return True
        if "all()" in rule:
            return False
        levels = [
            hierarchy.index(level.lower())
            for level in _PERMISSION_CHECK.findall(rule)
            if level.lower() in hierarchy
        ]
        return bool(levels) and min(levels) > floor
    return False


def takes_argument(key, doc):
    """
    How many arguments a command's usage line takes.

    Args:
        key (str): The command key.
        doc (str): The command class's docstring.

    Returns:
        int or None: The most arguments any usage line for this key shows --
            `<placeholders>` if it uses them, words otherwise -- 0 if usage
            lines exist and none takes anything, None if there is no usage line
            to go on.

    Notes:
        The count matters, not only whether there is one. `attack <target>`
        can take the thing a menu was opened on as its whole input;
        `setres <name> <value>` cannot, and the lab game's one command is the
        second kind -- which D3's first run suggested as a target action.

    """
    lines = (doc or "").splitlines()
    pattern = re.compile(r"^\s*%s(?:/\S+|\[[^\]]*\])*(\s+\S.*)?$" % re.escape(key), re.IGNORECASE)
    in_usage = False
    most = None
    for line in lines:
        if _USAGE_HEADING.match(line):
            in_usage = True
            continue
        if not in_usage:
            continue
        match = pattern.match(line)
        if not match:
            continue
        rest = (match.group(1) or "").strip()
        placeholders = re.findall(r"<[^>]+>", rest)
        count = len(placeholders) if placeholders else len(rest.split())
        most = count if most is None else max(most, count)
    return most


def game_commands(cmdsets, hierarchy=None, default_level=None):
    """
    Commands the game added that might be context actions.

    Args:
        cmdsets (iterable): Command sets, as Evennia built them.
        hierarchy (list, optional): Permission levels, lowest first. Defaults to
            `settings.PERMISSION_HIERARCHY`.
        default_level (str, optional): What a new account has. Defaults to
            `settings.PERMISSION_ACCOUNT_DEFAULT`.

    Returns:
        tuple: `(action candidates, problems)`.

    Notes:
        B.28 puts a command at MEDIUM at best: it exists, but whether its
        argument is the thing a menu was opened on is not something a scan can
        know. A usage line that takes an argument earns MEDIUM; no usage line,
        or one that takes nothing, is LOW.

    """
    hierarchy = [
        level.lower() for level in (hierarchy or getattr(settings, "PERMISSION_HIERARCHY", []))
    ]
    default_level = (
        default_level or getattr(settings, "PERMISSION_ACCOUNT_DEFAULT", "Player")
    ).lower()
    floor = hierarchy.index(default_level) if default_level in hierarchy else 0

    found, staff = {}, set()
    for cmdset in cmdsets:
        for command in list(getattr(cmdset, "commands", None) or []):
            cls = type(command)
            if is_core(cls.__module__):
                continue
            key = getattr(command, "key", "")
            if not isinstance(key, str) or not key.strip() or key.startswith("__"):
                continue
            if key in found or key in staff:
                continue
            if restricted(getattr(command, "locks", ""), hierarchy, floor):
                staff.add(key)
                continue

            takes = takes_argument(key, cls.__doc__)
            reasons = ["a command the game added, not one of Evennia's own"]
            warnings = []
            if takes and takes > 1:
                reasons.append(
                    "its usage line takes %d arguments, so the thing a menu was opened "
                    "on cannot be all of its input" % takes
                )
                level, template = confidence.LOW, "%s {target}" % key
            elif takes == 1:
                reasons.append("its usage line takes one argument")
                warnings.append(
                    "assumes the argument is the thing the menu was opened on -- check "
                    "the command's syntax"
                )
                level, template = confidence.MEDIUM, "%s {target}" % key
            elif takes == 0:
                reasons.append(
                    "its usage line takes no argument, so there is nothing for it to act on"
                )
                level, template = confidence.LOW, key
            else:
                reasons.append("it has no usage line to say whether it takes a target")
                level, template = confidence.LOW, key

            found[key] = ActionCandidate(
                key=key,
                command=template,
                evidence="%s in %s (%s)"
                % (key, getattr(cmdset, "key", type(cmdset).__name__), cls.__module__),
                confidence=level,
                reasons=tuple(reasons),
                warnings=tuple(warnings),
            )

    problems = []
    if staff:
        problems.append(
            "Not suggested as actions, because their locks need more than a new "
            "account has: %s" % ", ".join(sorted(staff))
        )
    return [found[key] for key in sorted(found)], problems


def cmdsets_of(character):
    """
    The command sets Evennia has built for a character.

    Args:
        character (Object): A character already fetched from the database.

    Returns:
        tuple: `(cmdsets, problems)`.

    """
    who = getattr(character, "id", "?")
    try:
        cmdsets = list(character.cmdset.all())
    except Exception as error:
        return [], ["could not read the command sets of #%s (%s)" % (who, error)]

    # When a command set will not import, Evennia does not raise: it substitutes
    # an empty set keyed `_CMDSET_ERROR` and logs the traceback. Taken at face
    # value that reads as "this game has no commands", which is how D3's first
    # run against the lab reported a game with a command as having none.
    broken = [cmdset for cmdset in cmdsets if getattr(cmdset, "key", "") == ERROR_CMDSET_KEY]
    if broken:
        return [c for c in cmdsets if c not in broken], [
            "Evennia could not load a command set for #%s and substituted its empty "
            "error set, so commands were not read. The game's command set module may "
            "not import -- `evennia shell`, then `me.cmdset.all()` on that character, "
            "shows the traceback." % who
        ]
    return cmdsets, []


def inspect(characters):
    """
    Everything the structural pass has to say about a set of characters.

    Args:
        characters (list): Characters the runtime scan read.

    Returns:
        dict: `candidates`, `actions`, `problems`, `lineages`, and
            `commands_from` (who the commands were read off, or None).

    Notes:
        Commands are read from the first character only -- the one the
        developer chose, or the newest. Command sets differ between characters
        (a builder has more), and one character's commands are a coherent
        answer where a union of twenty-five is not.

    """
    classes = []
    for character in characters:
        klass = type(character)
        if klass not in classes:
            classes.append(klass)

    result = {
        "candidates": [],
        "actions": [],
        "problems": [],
        "lineages": [],
        "commands_from": None,
    }
    for klass in classes[:MAX_CLASSES]:
        result["lineages"].append(lineage(klass))
        declared, problems = declared_attributes(klass)
        result["candidates"].extend(declared)
        result["problems"].extend(problems)
        result["problems"].extend(handler_notes(klass))
    if len(classes) > MAX_CLASSES:
        result["problems"].append(
            "%d character typeclasses were read; the first %d are described"
            % (len(classes), MAX_CLASSES)
        )

    if characters:
        first = characters[0]
        cmdsets, problems = cmdsets_of(first)
        actions, more = game_commands(cmdsets)
        result["actions"] = actions
        result["problems"].extend(problems + more)
        result["commands_from"] = "#%s %s" % (
            getattr(first, "id", "?"),
            getattr(first, "db_key", ""),
        )

    result["problems"] = list(dict.fromkeys(result["problems"]))
    return result
