"""
Reading a game's source without running it.

THE WHOLE POINT IS THAT NOTHING IS IMPORTED. A game's
`typeclasses/characters.py` is ordinary Python and importing it runs it: it can
open a connection, read a file, take ten seconds, or raise. Discovery is a tool a
developer runs to find out what their game has, and it would be a poor one if
running it could change anything or fail because the game is mid-edit.

So the entire static scan is `ast.parse` on text. There is no `importlib`, no
`compile(..., "exec")`, no `eval`, and a test asserts none of those names appear
in this module -- because the natural way to make this "better" is to import the
module and use `dir()`, and that version cannot be made safe afterwards.

The cost is real and worth naming: a scan that does not run the code cannot see
what the code computes. `self.db.hp = starting_hp` yields a candidate whose kind
is `unknown`, and a game that sets its attributes in a loop over a table yields
nothing at all. That is what `runtime_scan` is for, and why neither scan is
offered on its own.

WHAT IT LOOKS FOR. Evennia has two ways to set an attribute and games use both::

    self.db.hp = 100                    # the attribute handler
    self.attributes.add("hp", 100)      # the explicit call

Both are recognised, and D4 adds the rest of Addendum B.23's list: a class-level
`hp = AttributeProperty(100)`, a *read* of `character.db.mana` (weaker evidence
-- it says the attribute is expected, not what it holds), and
`class CmdAttack(Command): key = "attack"`, which is where a game with no
characters yet keeps its commands.

It also recognises one thing in order to refuse it. `character.stats.get("hp")`
is a value behind a handler: a binding cannot call anything, so discovery names
the handler and points at a provider rather than inventing an expression that
would not resolve (B.66).

The receiver is recorded rather than assumed: `self.db.hp`
in a typeclass and `caller.db.hp` in a command are both real evidence, and which
one it was belongs in the report so a developer can tell a character attribute
from something set on a room.

"""

import ast
import os

from evennia.contrib.base_systems.aetos_webclient.discovery import confidence
from evennia.contrib.base_systems.aetos_webclient.discovery.candidates import (
    SOURCE_ONLY_REASON,
    ActionCandidate,
    Candidate,
)
from evennia.contrib.base_systems.aetos_webclient.discovery.roots import (
    game_directory,
    select_files,
)

#: Receiver names whose `.db` is taken to be a character's.
#:
#: A guess, and a narrow one on purpose. `self` inside a typeclass, and the two
#: names Evennia's own command docs use for the character running a command.
#: `obj.db.x` is not included: in a command, `obj` is usually the thing being
#: acted on rather than the actor, and a report full of a room's attributes
#: labelled as the character's is worse than a shorter report.
CHARACTER_RECEIVERS = ("self", "caller", "character")

#: The handlers a binding can read through. Everything else is a call.
#:
#: `db` and `attributes` are the attribute store, which is what a binding reads.
#: A game's own handler -- `character.stats`, `character.traits` -- is reached by
#: calling it, and the grammar has no way to say that.
BINDING_HANDLERS = ("db", "attributes")

#: Evennia's own members, which are never a game's handler.
#:
#: Found by running this against the lab game, which reported
#: `character.args` and `character.caller` as handlers and advised writing a
#: provider for them. They are a Command's own plumbing. Advice about a thing
#: that does not exist is worse than no advice: it sends a developer looking for
#: a feature they never wrote.
EVENNIA_MEMBERS = frozenset(
    {
        # Command
        "args",
        "caller",
        "cmdstring",
        "lhs",
        "lhslist",
        "obj",
        "raw_string",
        "rhs",
        "rhslist",
        "session",
        "switches",
        # Object and typeclass
        "account",
        "aliases",
        "cmdset",
        "contents",
        "exits",
        "home",
        "locks",
        "location",
        "ndb",
        "nattributes",
        "permissions",
        "scripts",
        "sessions",
        "tags",
    }
)

#: The most AST nodes one file may contain before it is reported and skipped.
#:
#: A ceiling on tree complexity, per B.53. A generated table with a hundred
#: thousand literals parses fine and says nothing about the game.
MAX_NODES = 200000


def _kind_of(node):
    """
    What an assigned value looks like, from the syntax alone.

    Args:
        node (ast.AST): The right-hand side of an assignment.

    Returns:
        str: One of `candidates.KINDS`.

    Notes:
        `bool` is tested before `int` because `True` is an `int` in Python, and
        reporting a flag as a number is the kind of small wrongness that makes a
        generated settings block need checking line by line.

    """
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool):
            return "boolean"
        if isinstance(node.value, (int, float)):
            return "number"
        if isinstance(node.value, str):
            return "text"
        return "unknown"
    if isinstance(node, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
        return "collection"
    if isinstance(node, ast.BinOp):
        # `100 * level` is still a number as far as anybody reading it cares.
        left = _kind_of(node.left)
        right = _kind_of(node.right)
        return "number" if "number" in (left, right) else "unknown"
    return "unknown"


def _attribute_target(node):
    """
    The receiver and attribute name of a `<receiver>.db.<name>` expression.

    Args:
        node (ast.AST): A node that may be an attribute access.

    Returns:
        tuple or None: `(receiver, name)`, or None if this is not the shape.

    Notes:
        Matches exactly two levels. `self.db.stats.hp` is an attribute of an
        attribute, which the binding grammar can express but the scan cannot
        verify from source -- so it is not claimed here. Under-reporting is the
        safe direction: a missing suggestion costs the developer a line of
        typing, and a wrong one costs them an afternoon.

    """
    if not isinstance(node, ast.Attribute):
        return None
    holder = node.value
    if not isinstance(holder, ast.Attribute) or holder.attr != "db":
        return None
    if not isinstance(holder.value, ast.Name):
        return None
    return holder.value.id, node.attr


def _attributes_add_call(node):
    """
    The receiver and key of an `<receiver>.attributes.add("key", ...)` call.

    Args:
        node (ast.AST): A node that may be such a call.

    Returns:
        tuple or None: `(receiver, key, value_node)`, or None.

    Notes:
        Only a literal string key is accepted. `attributes.add(name, value)` in
        a loop is exactly the case the static scan cannot see, and guessing at
        the variable's contents would produce candidates that do not exist.

    """
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        return None
    if node.func.attr != "add":
        return None
    handler = node.func.value
    if not isinstance(handler, ast.Attribute) or handler.attr != "attributes":
        return None
    if not isinstance(handler.value, ast.Name):
        return None
    if not node.args or not isinstance(node.args[0], ast.Constant):
        return None
    key = node.args[0].value
    if not isinstance(key, str) or not key.isidentifier():
        return None
    value = node.args[1] if len(node.args) > 1 else None
    return handler.value.id, key, value


def _attribute_property(node):
    """
    A class-level `name = AttributeProperty(default, category=...)`.

    Args:
        node (ast.Assign): An assignment.

    Returns:
        tuple or None: `(name, default node or None, category or None)`.

    Notes:
        Matched by the *called name* rather than by import, because a game may
        write `from evennia import AttributeProperty` or
        `evennia.AttributeProperty`, and following the import would mean
        resolving modules -- which means importing them.

    """
    if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
        return None
    call = node.value
    if not isinstance(call, ast.Call):
        return None
    func = call.func
    called = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
    if called != "AttributeProperty":
        return None
    name = node.targets[0].id
    if not name.isidentifier() or name.startswith("__"):
        return None
    default = call.args[0] if call.args else None
    category = None
    for keyword in call.keywords:
        if keyword.arg == "category" and isinstance(keyword.value, ast.Constant):
            category = keyword.value.value
    return name, default, category


def _handler_call(node, receivers):
    """
    A `<receiver>.<handler>.<method>(...)` call on something that is not `db`.

    Args:
        node (ast.AST): A node that may be such a call.
        receivers (tuple): Receiver names taken to be a character.

    Returns:
        str or None: The handler's name, e.g. `stats`.

    """
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        return None
    handler = node.func.value
    if not isinstance(handler, ast.Attribute) or not isinstance(handler.value, ast.Name):
        return None
    if handler.value.id not in receivers:
        return None
    if handler.attr in BINDING_HANDLERS or handler.attr in EVENNIA_MEMBERS:
        return None
    return handler.attr


def _handler_names(tree, receivers):
    """
    Every game handler a character's values are read through in this source.

    Args:
        tree (ast.AST): The parsed module.
        receivers (tuple): Receiver names taken to be a character.

    Returns:
        set: Handler names, e.g. `{"stats"}`.

    Notes:
        Scoped rather than flat, because **`self` means something different
        inside a Command**: there it is the command object, so `self.args` and
        `self.caller` are Evennia's plumbing and not the character's anything.
        Walking the whole file at once reported both as handlers of the game's
        own, which is advice about a feature the developer never wrote.

    """
    found = set()

    def visit(node, here):
        """
        Walk one scope, narrowing the receivers inside a Command class.

        Args:
            node (ast.AST): The node whose children to walk.
            here (tuple): Receiver names that mean a character in this scope.

        """
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                inner = (
                    tuple(name for name in here if name != "self")
                    if _command_class(child)
                    else here
                )
                visit(child, inner)
                continue
            handler = _handler_call(child, here)
            if handler:
                found.add(handler)
            visit(child, here)

    visit(tree, receivers)
    return found


def _class_constant(node, name):
    """
    A class-level `name = "literal"`.

    Args:
        node (ast.ClassDef): The class.
        name (str): The attribute to look for.

    Returns:
        The literal value, or None.

    """
    for statement in node.body:
        if not isinstance(statement, ast.Assign) or not isinstance(statement.value, ast.Constant):
            continue
        for target in statement.targets:
            if isinstance(target, ast.Name) and target.id == name:
                return statement.value.value
    return None


def _command_class(node):
    """
    Whether a class definition looks like an Evennia Command.

    Args:
        node (ast.ClassDef): The class.

    Returns:
        bool: True if any base's name ends in `Command`.

    Notes:
        By name, not by resolving the base class, for the same reason as
        `AttributeProperty`: resolving means importing. `MuxCommand`,
        `Command` and a game's own `CombatCommand` all end the same way.

    """
    for base in node.bases:
        named = base.id if isinstance(base, ast.Name) else getattr(base, "attr", "")
        if isinstance(named, str) and named.endswith("Command"):
            return True
    return False


def _action_from(node, label):
    """
    An action candidate from a Command class definition.

    Args:
        node (ast.ClassDef): The class.
        label (str): The file, for evidence.

    Returns:
        ActionCandidate or None: None when it has no key, or its lock keeps it
            away from ordinary players.

    """
    from evennia.contrib.base_systems.aetos_webclient.discovery import structure

    key = _class_constant(node, "key")
    if not isinstance(key, str) or not key.strip() or key.startswith("__"):
        return None

    hierarchy = structure.permission_hierarchy()
    if structure.restricted(_class_constant(node, "locks") or "", *hierarchy):
        return None

    takes = structure.takes_argument(key, ast.get_docstring(node))
    reasons = ["declared in the game's source as %s" % node.name]
    warnings = []
    if takes == 1:
        reasons.append("its usage line takes one argument")
        command = "%s {target}" % key
        warnings.append(
            "assumes the argument is the thing the menu was opened on -- check the "
            "command's syntax"
        )
    elif takes:
        reasons.append(
            "its usage line takes %d arguments, so the thing a menu was opened on "
            "cannot be all of its input" % takes
        )
        command = "%s {target}" % key
    else:
        reasons.append("nothing here says whether it takes a target")
        command = key

    # Always LOW: source says the class exists, not that it is in any character's
    # command set. B.28 -- "name appears only in source". The merge drops this
    # line if the runtime pass then finds the command on a real character.
    reasons.append(SOURCE_ONLY_REASON)
    return ActionCandidate(
        key=key,
        command=command,
        evidence="%s:%d, class %s" % (label, node.lineno, node.name),
        confidence=confidence.LOW,
        reasons=tuple(reasons),
        warnings=tuple(warnings),
    )


def scan_source(source, label, receivers=CHARACTER_RECEIVERS, max_nodes=MAX_NODES):
    """
    What one piece of Python source says about a game's characters.

    Args:
        source (str): Python source text.
        label (str): How to name this source in evidence, usually a path
            relative to the game directory.
        receivers (tuple, optional): Receiver names to accept.
        max_nodes (int, optional): Ceiling on the size of the parsed tree.

    Returns:
        tuple: `(candidates, actions, problems)`.

    Raises:
        SyntaxError: If the source does not parse. Callers decide what to do
            about a game file that is mid-edit; this does not swallow it,
            because a scan that silently skipped the Character typeclass and
            reported "no candidates" would be read as "your game has nothing".

    """
    tree = ast.parse(source)
    nodes = list(ast.walk(tree))
    if len(nodes) > max_nodes:
        return (
            [],
            [],
            [
                "%s was not read: %d syntax nodes, above the ceiling of %d. It is "
                "probably generated or a data table." % (label, len(nodes), max_nodes)
            ],
        )

    found, actions, problems = [], [], []
    handlers = _handler_names(tree, receivers)

    for node in nodes:
        if isinstance(node, ast.ClassDef):
            if _command_class(node):
                action = _action_from(node, label)
                if action is not None:
                    actions.append(action)

        elif isinstance(node, ast.Assign):
            declared = _attribute_property(node)
            if declared is not None:
                name, default, category = declared
                if category:
                    problems.append(
                        "%s:%d declares %s with category %r. The binding grammar "
                        "reaches uncategorised attributes only; a provider class in "
                        "AETOS_PROVIDERS can read it." % (label, node.lineno, name, category)
                    )
                    continue
                found.append(
                    Candidate(
                        expression="db.%s" % name,
                        name=name,
                        origin="typeclass",
                        evidence="%s:%d, declared as AttributeProperty" % (label, node.lineno),
                        kind=_kind_of(default) if default is not None else "unknown",
                    )
                )
                continue

            for target in node.targets:
                match = _attribute_target(target)
                if match and match[0] in receivers:
                    receiver, name = match
                    found.append(
                        Candidate(
                            expression="db.%s" % name,
                            name=name,
                            origin="static",
                            evidence="%s:%d, assigned as %s.db.%s"
                            % (label, node.lineno, receiver, name),
                            kind=_kind_of(node.value),
                        )
                    )

        elif isinstance(node, ast.Call):
            match = _attributes_add_call(node)
            if match and match[0] in receivers:
                receiver, name, value = match
                found.append(
                    Candidate(
                        expression="db.%s" % name,
                        name=name,
                        origin="static",
                        evidence="%s:%d, set by %s.attributes.add(%r)"
                        % (label, node.lineno, receiver, name),
                        kind=_kind_of(value) if value is not None else "unknown",
                    )
                )

        elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
            # A *read*: `if character.db.mana > 0`. Weaker than an assignment --
            # it says the attribute is expected to exist, not what it holds --
            # and often the only evidence in a game whose values are set from a
            # table the scan cannot follow.
            match = _attribute_target(node)
            if match and match[0] in receivers:
                receiver, name = match
                found.append(
                    Candidate(
                        expression="db.%s" % name,
                        name=name,
                        origin="static",
                        evidence="%s:%d, read as %s.db.%s" % (label, node.lineno, receiver, name),
                        kind="unknown",
                    )
                )

    for handler in sorted(handlers):
        problems.append(
            "%s reads values through character.%s, a handler. Reaching them means "
            "calling it, which a binding never does, so nothing is suggested for it. "
            "A provider class in AETOS_PROVIDERS is the supported route." % (label, handler)
        )

    return found, actions, problems


def scan_files(gamedir=None, stats=None):
    """
    Everything the static pass finds across the files it is allowed to read.

    Args:
        gamedir (str, optional): The game directory. Defaults to
            `settings.GAME_DIR`.
        stats (dict, optional): Filled in with `files_read`, for a report that
            wants to say how much was looked at (B.45). An out-parameter rather
            than another return value, because every caller wants the
            candidates and only the report wants the count.

    Returns:
        tuple: `(candidates, actions, problems)`.

    Notes:
        A file that does not parse is reported rather than raised, because one
        broken file in `world/` should not stop a developer discovering their
        Character (B.57). The problems go in the report, so "I got fewer results
        than I expected" has an answer on the same screen.

    """
    files, problems = select_files(gamedir)
    if stats is not None:
        stats["files_read"] = len(files)
    base = os.path.realpath(gamedir) if gamedir else game_directory()
    candidates, actions = [], []

    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                source = handle.read()
        except (OSError, UnicodeDecodeError) as error:
            problems.append("%s could not be read (%s)" % (path, error))
            continue

        # Forward slashes regardless of platform. The label goes into a comment
        # a developer reads and may paste into an issue, and `world\combat.py`
        # is a Windows detail nobody outside Windows should have to parse.
        label = os.path.relpath(path, base).replace(os.sep, "/")
        try:
            more, found_actions, issues = scan_source(source, label)
        except SyntaxError as error:
            problems.append("%s could not be parsed (line %s)" % (label, error.lineno))
            continue
        candidates.extend(more)
        actions.extend(found_actions)
        problems.extend(issues)

    return candidates, actions, problems
