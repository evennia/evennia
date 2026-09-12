"""
Reading `AETOS_BINDINGS` out of settings, and handing back a provider for it.

Separate from `schema` because the schema is about *shape* and this is about
*this game* -- and separate from `providers` because the provider package must
not have to know that bindings exist in order to resolve a slot nobody bound.

"""

from django.conf import settings

from evennia.contrib.base_systems.aetos_webclient.bindings import schema
from evennia.contrib.base_systems.aetos_webclient.bindings.resolver import (
    AetosBindingError,
)


def get_bindings():
    """
    This game's validated binding declaration.

    Returns:
        dict: Slot name mapped to its entries. Empty if the game declared none.

    Raises:
        AetosBindingError: If `AETOS_BINDINGS` is malformed, naming the slot, the
            key and the fix.

    Notes:
        Read and validated on every call rather than cached. It is a small dict
        and this runs once per session handshake, and a cache would be one more
        thing to invalidate on `evennia reload` for no measurable gain.

    """
    return schema.validate_bindings(
        getattr(settings, "AETOS_BINDINGS", None), error_class=AetosBindingError
    )


def bound_slots():
    """
    Which slots this game has declared bindings for.

    Returns:
        set: Slot names with at least one entry.

    Notes:
        An empty slot -- `{"resources": {}}` -- does not count. A game that
        declared the key and then deleted its entries has bound nothing, and
        counting it would switch on a feature flag for a widget with no rows in
        it.

        Errors are swallowed here and nowhere else. This is asked by the manifest
        builder and the provider registry, both of which run while a player is
        connecting; a malformed setting is reported at startup by the system
        check, where the developer is looking. Raising here as well would turn a
        typo into a failed login.

    """
    try:
        declared = get_bindings()
    except AetosBindingError:
        return set()
    return {slot for slot, entries in declared.items() if entries}


def provider_for(slot):
    """
    A provider that serves one slot from this game's bindings.

    Args:
        slot (str): The provider slot name.

    Returns:
        AetosProvider or None: A provider instance, or None if this slot has no
            declarative implementation yet.

    Notes:
        D1 served `resources` alone, which was its gate. D2 added the other four,
        and this function did not change: it asks a table, so a slot is served
        the moment it has a row and falls through to the stock default until it
        does. That is the shape that made the second milestone cheap.

        `None` is still a real answer, and deliberately kept as one. A future
        slot -- `map`, say -- would be declarable and unserved for exactly as
        long as it took to write its provider, and during that time a game gets
        the same client it would have had anyway rather than something
        half-built.

        Imported inside the function because `providers` imports this module to
        decide precedence, and importing it back at module level would be a
        cycle.

    """
    from evennia.contrib.base_systems.aetos_webclient.bindings import bound_providers

    factory = bound_providers.PROVIDERS.get(slot)
    return factory() if factory else None
