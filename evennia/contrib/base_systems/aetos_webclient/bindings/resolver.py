"""
Turning `db.hp` into a number, and refusing to turn it into anything else.

THIS IS THE PART THAT MUST NOT BECOME AN EVALUATOR.

The grammar in `schema` decides what may be written. This module decides what
actually happens when it is read, and the two failures are different: a grammar
that accepts too much is a bug you can see in a regular expression, and a
resolver that does too much is a bug you cannot see at all, because the setting
still looks like a path.

So resolution is deliberately small enough to describe in full:

1. The expression is re-validated here, at use, and not merely at startup. A
   caller that built one by string concatenation gets refused rather than
   trusted, and there is no path into this module that skips the check.
2. The first name is read through `character.attributes.get(name)` -- Evennia's
   own handler, by name, not `getattr` on anything.
3. A second name, if there is one, is a **key in a mapping**. Nothing else.

Step 3 is the interesting one. `db.stats.hp` could plausibly mean "the `hp`
attribute of whatever is stored at `stats`", and that reading is rejected: it
would have the resolver traversing arbitrary objects with `getattr`, which runs
`__getattr__`, which is the game's code, which is the thing this whole design is
avoiding. A dict lookup on a dict cannot run anything.

Games store `character.db.stats = {"hp": 50}` all the time, so the useful case is
covered. A game storing an *object* at `db.stats` and wanting a field off it has
outgrown a declaration and wants a provider class, and the error message says so.

MISSING IS NORMAL. NOT MISSING IS ALSO NORMAL.

A character with no `hp` yet is an ordinary state, not an error -- a new
character, a feature half-built, a binding written before the attribute exists.
Resolution returns `None` and the resource is simply not shown. What is *not*
normal is a malformed binding, and that is caught at startup by a Django check
rather than at read time, so a player never meets it.

"""

from collections.abc import Mapping

from evennia.contrib.base_systems.aetos_webclient.bindings import schema


class AetosBindingError(ValueError):
    """
    Raised when a game's `AETOS_BINDINGS` declaration is wrong.

    Beginner-readable on purpose. `AETOS_BINDINGS` exists for somebody who did
    not want to write Python, so its errors name the slot, the key, the field and
    the fix -- never a regular expression, and never "invalid configuration".

    """


class AetosBindingResolver:
    """
    Reads a value out of a character, given a binding expression.

    Stateless and cheap to make. It holds no character and no declaration, so
    there is nothing to invalidate when a character changes and nothing to keep
    in sync -- a resolver is a function with a docstring, and it is a class only
    because Addendum B names it as one and a game may want to subclass it.

    """

    #: What `db.` refers to. Named so a subclass could point at another handler
    #: without reimplementing the traversal, and so this file has one place that
    #: says which store is being read.
    ROOT = "db"

    def resolve(self, character, expression):
        """
        The value a binding expression names, or None.

        Args:
            character (Object): The character to read from.
            expression (str): A binding expression, e.g. `db.hp`.

        Returns:
            The stored value, or None if the attribute does not exist, the
            expression is not valid, or the character cannot be read.

        Raises:
            Nothing. This runs inside a websocket handler while a player is
            connected, and every reason it could fail -- a missing attribute, a
            deleted character, a game object that raises from `__getattr__` --
            is a reason to show one fewer widget rather than to drop the
            session.

        """
        if not schema.is_valid_expression(expression):
            # Re-checked at use, not only at startup. A caller that built an
            # expression by concatenation is refused rather than trusted, and
            # there is no way into the traversal below that skips this line.
            return None
        if character is None:
            return None

        names = schema.expression_parts(expression)

        try:
            value = character.attributes.get(names[0], default=None)
        except Exception:
            # A character mid-deletion, or a game whose AttributeHandler is
            # itself custom. One widget's worth of loss.
            return None

        if len(names) == 1:
            return value

        return self._child(value, names[1])

    def _child(self, value, name):
        """
        A key inside a stored mapping.

        Args:
            value: Whatever the first name resolved to.
            name (str): The second name in the expression.

        Returns:
            The value stored under `name`, or None.

        Notes:
            **Mapping only, and that is the whole safety of the second level.**
            `getattr(value, name)` would run the game's `__getattr__` on an
            arbitrary object; `value[name]` on a custom type would run its
            `__getitem__`. Restricting to a real `Mapping` -- which Evennia's
            saver-dicts register as -- means the second level is a dictionary
            lookup and can do nothing else.

            A game storing an object at `db.stats` gets None here, and the
            startup check cannot tell it so because the value only exists at
            runtime. That is the one place a binding fails quietly, and the
            trade is deliberate: the alternative is traversal.

        """
        if not isinstance(value, Mapping):
            return None
        try:
            return value.get(name)
        except Exception:
            return None

    def resolve_number(self, character, expression):
        """
        A binding's value as a number, or None.

        Args:
            character (Object): The character to read from.
            expression (str): A binding expression.

        Returns:
            float or int or None: The value, if it is or reads as a number.

        Notes:
            `bool` is refused rather than counted as 0 and 1. A game with
            `db.is_bleeding = True` bound to a resource meant something, and a
            bar reading "1 / 1" is not it.

            A numeric string is accepted, because Evennia attributes are
            whatever was assigned and `"50"` from a parsed command is common
            enough that refusing it would look like a bug in Aetos.

        """
        value = self.resolve(character, expression)
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            try:
                return float(value) if "." in value else int(value)
            except ValueError:
                return None
        return None
