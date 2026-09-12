"""
Aetos provider registry.

A game replaces any provider through a single setting::

    AETOS_PROVIDERS = {
        "resources": "world.aetos.MyResourceProvider",
        "map": "world.aetos.MyMapProvider",
    }

Unlisted providers keep their defaults, so a game overrides one thing without
restating the rest.

Misconfiguration fails loudly and early with a message naming the setting, the
key and the import that failed (blueprint section 64). A provider that cannot be
imported is a developer error worth surfacing at startup; a provider that raises
at *runtime* is contained instead, because by then a player is connected and
losing one widget beats losing the session.

"""

from django.conf import settings

from evennia.contrib.base_systems.aetos_webclient.providers import base, defaults
from evennia.utils.utils import class_from_module

#: Provider slots and their base classes. A game-supplied provider must be a
#: subclass of the slot's base class, so a typo pointing "map" at a resource
#: provider is caught at load time rather than producing an empty map.
PROVIDER_SLOTS = {
    "resources": base.AetosResourceProvider,
    "entities": base.AetosEntityProvider,
    "actions": base.AetosActionProvider,
    "map": base.AetosMapProvider,
    "inventory": base.AetosInventoryProvider,
    "equipment": base.AetosEquipmentProvider,
    "target": base.AetosTargetProvider,
    "effects": base.AetosEffectProvider,
    "media": base.AetosMediaProvider,
}

#: Defaults used when a game does not override a slot.
#:
#: `resources` intentionally defaults to the inert base class. There is no
#: genre-neutral way to guess what a game's resources are, so Aetos exposes none
#: and simply shows no resource widgets. Inventing a "health" default would be
#: the exact genre assumption this project forbids.
#:
#: `actions` does have a default, because unlike resources there *are* commands
#: every stock Evennia game has -- look, get, drop. Offering those is not a genre
#: assumption, and blueprint section 11 promises basic context actions with zero
#: custom game code.
DEFAULT_PROVIDERS = {
    "resources": base.AetosResourceProvider,
    "entities": defaults.DefaultEntityProvider,
    "actions": defaults.DefaultActionProvider,
    "map": defaults.DefaultMapProvider,
    # `inventory` has a real default because `contents` is a stock Evennia
    # concept -- carrying things is not a genre assumption. `equipment`,
    # `target` and `effects` do not: slots, a current target and a buff list
    # are all genre decisions, so a game without them shows no widget rather
    # than an empty paper doll.
    "inventory": defaults.DefaultInventoryProvider,
    "equipment": base.AetosEquipmentProvider,
    "target": base.AetosTargetProvider,
    "effects": base.AetosEffectProvider,
    "media": base.AetosMediaProvider,
}


class AetosProviderError(ValueError):
    """Raised when a game's provider configuration is invalid."""


def _resolve_slot(slot, path):
    """
    Import and validate one configured provider.

    Args:
        slot (str): The provider slot name.
        path (str): Dotted path to the provider class.

    Returns:
        AetosProvider: An instance of the configured provider.

    Raises:
        AetosProviderError: If the path is unimportable or the wrong type.

    """
    if not isinstance(path, str):
        raise AetosProviderError(
            "AETOS_PROVIDERS[%r] must be a dotted path string, got %r" % (slot, type(path).__name__)
        )
    try:
        provider_class = class_from_module(path)
    except Exception as err:
        raise AetosProviderError(
            "AETOS_PROVIDERS[%r] could not import %r: %s" % (slot, path, err)
        ) from err

    expected = PROVIDER_SLOTS[slot]
    if not (isinstance(provider_class, type) and issubclass(provider_class, expected)):
        raise AetosProviderError(
            "AETOS_PROVIDERS[%r] must be a subclass of %s, got %r" % (slot, expected.__name__, path)
        )
    return provider_class()


def get_providers():
    """
    Resolve every provider for this game.

    Returns:
        dict: Slot name mapped to a provider instance.

    Raises:
        AetosProviderError: If `AETOS_PROVIDERS` is malformed.

    """
    configured = getattr(settings, "AETOS_PROVIDERS", None) or {}
    if not isinstance(configured, dict):
        raise AetosProviderError(
            "AETOS_PROVIDERS must be a dict, got %r" % type(configured).__name__
        )

    unknown = set(configured) - set(PROVIDER_SLOTS)
    if unknown:
        raise AetosProviderError(
            "AETOS_PROVIDERS contains unknown slot(s) %s. Valid slots: %s"
            % (sorted(unknown), sorted(PROVIDER_SLOTS))
        )

    """
    PRECEDENCE: custom > binding > default.  (D1)

    A game that wrote a provider class keeps it, whatever else it declared. A
    binding fills a slot no class has claimed. The stock default fills the rest.

    Stated in this order, in one place, because the alternative is a developer
    migrating from a class to a declaration and getting both -- or worse, getting
    the binding silently instead of the class they are still editing. The
    resolution order is also the order somebody would guess: the more specific
    thing wins.

    Imported inside the function: `bindings` imports this package for its
    provider base classes, and importing it back at module level would be a
    cycle.
    """
    from evennia.contrib.base_systems.aetos_webclient import bindings

    bound = bindings.bound_slots()

    resolved = {}
    for slot, default_class in DEFAULT_PROVIDERS.items():
        if slot in configured:
            resolved[slot] = _resolve_slot(slot, configured[slot])
            continue
        if slot in bound:
            declarative = bindings.provider_for(slot)
            if declarative is not None:
                resolved[slot] = declarative
                continue
        resolved[slot] = default_class()
    return resolved


def describe_providers():
    """
    Describe the active providers, for the developer inspector.

    Returns:
        dict: Slot name mapped to a provider description.

    """
    return {slot: provider.describe() for slot, provider in get_providers().items()}
