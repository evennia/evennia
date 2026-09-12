"""
Aetos provider base classes.

Providers are how Aetos stays genre-agnostic. Aetos never reaches into a game's
data directly; it asks a provider, and a game may replace any provider through
settings without touching Aetos itself.

The default providers in this package use nothing but ordinary Evennia concepts --
rooms, exits, contents, keys. They are deliberately conservative: a pristine game
gets a useful client, and a game that models health as `character.db.hp` gets
resource widgets by supplying twenty lines of provider rather than by patching
Aetos.

Design rules for every provider:

* **Never assume game structure.** No provider in core may reference a stat name,
  a combat system, an equipment slot, or a genre concept.
* **Degrade, never raise.** A game's provider is third-party code running inside a
  websocket handler. A provider that raises must not take down the client, so
  callers use the `safe_*` wrappers, which log and fall back.
* **Read-only.** Providers describe state. They never execute commands or mutate
  the game.

"""

from evennia.utils import logger


class AetosProvider:
    """
    Base class for all Aetos providers.

    Subclasses override the specific `get_*` method for their domain. The base
    class exists so that providers share identification and error semantics.

    """

    #: Human-readable name, used in error messages and the developer inspector.
    name = "provider"

    def describe(self):
        """
        Describe this provider for the developer inspector.

        Returns:
            dict: Identification of the provider class in use.

        """
        return {
            "name": self.name,
            "class": "%s.%s" % (type(self).__module__, type(self).__qualname__),
        }


class AetosResourceProvider(AetosProvider):
    """
    Supplies a character's resources.

    Resources are arbitrary. Aetos assigns no meaning to any of them: health,
    sanity, hull integrity, fuel and favour are all the same shape.

    """

    name = "resources"

    def get_resources(self, character):
        """
        Return the character's resources.

        Args:
            character (Object): The character to describe.

        Returns:
            list: Resource dicts. Each has at least `id`, `label` and `value`,
                and optionally `maximum`, `display` and `thresholds`.

        """
        return []


class AetosEntityProvider(AetosProvider):
    """Supplies the entities visible in a character's current location."""

    name = "entities"

    def get_room_entities(self, character):
        """
        Return entities in the character's location.

        Args:
            character (Object): The observing character.

        Returns:
            list: Entity dicts with at least `id`, `name` and `kind`.

        """
        return []


class AetosActionProvider(AetosProvider):
    """
    Supplies contextual actions for an entity.

    An action is a label plus an ordinary game command. Returning an action does
    not make it legal -- the server still decides when the command is sent.

    """

    name = "actions"

    def get_actions(self, character, target=None):
        """
        Return actions available to a character, optionally against a target.

        Args:
            character (Object): The acting character.
            target (Object, optional): The target entity.

        Returns:
            list: Action dicts with at least `label` and `command`.

        """
        return []


class AetosMapProvider(AetosProvider):
    """Supplies map data for a character's surroundings."""

    name = "map"

    def get_map(self, character):
        """
        Return map data around the character.

        Args:
            character (Object): The character to map around.

        Returns:
            dict: Map data with `rooms` and `exits` lists, and optionally
                `current`, `zone` and `levels`.

        """
        return {"rooms": [], "exits": []}


class AetosInventoryProvider(AetosProvider):
    """
    Supplies what a character is carrying.

    Unlike equipment, inventory *is* a stock Evennia concept -- every object has
    `contents` -- so this slot has a working default and a pristine game gets an
    inventory widget with no code at all.

    """

    name = "inventory"

    def get_inventory(self, character):
        """
        Return the character's carried items.

        Args:
            character (Object): The character to describe.

        Returns:
            list: Item dicts with at least `id` and `name`, and optionally
                `quantity`, `category` and `actions`.

        """
        return []


class AetosEquipmentProvider(AetosProvider):
    """
    Supplies a character's equipped items by slot.

    Deliberately inert by default. Evennia has no equipment system, and slots are
    a genre decision -- "head, chest, legs" is as much an assumption as "health".
    A game with equipment supplies twenty lines of provider; a game without one
    shows no equipment widget rather than an empty paper doll.

    """

    name = "equipment"

    def get_equipment(self, character):
        """
        Return the character's equipment slots.

        Args:
            character (Object): The character to describe.

        Returns:
            list: Slot dicts with at least `slot`, and `item` set to an item dict
                or None when the slot is empty.

        """
        return []


class AetosTargetProvider(AetosProvider):
    """
    Supplies the character's current target.

    Inert by default: a "current target" only exists in a game that tracks one,
    and Aetos guessing at one would be wrong in most genres.

    A target is not a command. Reporting a target does not select it, and
    selecting one in the client sends whatever ordinary command the game
    provides -- the server decides what the target actually is.

    """

    name = "target"

    def get_target(self, character):
        """
        Return the character's current target.

        Args:
            character (Object): The observing character.

        Returns:
            dict: Target data with at least `id` and `name`, and optionally
                `kind`, `resources`, `effects` and `actions`. Empty when there is
                no target.

        """
        return {}


class AetosEffectProvider(AetosProvider):
    """
    Supplies temporary effects on a character.

    An effect is anything temporarily true about the character: a buff, a poison,
    a stance, a weather exposure, a debt timer. Aetos assigns no meaning to any of
    them, exactly as it assigns none to resources.

    Inert by default, because Evennia models no such thing.

    """

    name = "effects"

    def get_effects(self, character):
        """
        Return the effects currently on a character.

        Args:
            character (Object): The character to describe.

        Returns:
            list: Effect dicts with at least `id` and `label`, and optionally
                `kind`, `remaining`, `duration`, `stacks` and `description`.

        """
        return []


class AetosMediaProvider(AetosProvider):
    """
    Supplies sound and imagery for the player's current situation.

    A media descriptor is a dict. `url` and `category` are required; everything
    else is metadata that decides what a player who cannot hear it, or cannot
    see it, is told instead.

    Inert by default. Evennia models no media, and a client that invented some
    would be guessing at a game's art direction.

    **No caption can be invented reliably.** Aetos cannot listen to a sound file
    and describe it, and it will not try. A game that supplies audio without a
    caption is supplying audio that some of its players simply do not receive --
    which is why `A11Y-MEDIA-001` makes it the game developer's obligation
    rather than a nicety (A.79).

    """

    name = "media"

    def get_media(self, character):
        """
        Return the media currently appropriate for a character.

        This is *ambient* media -- what should be playing or shown while the
        player is here. It is state, not an event: the client compares it with
        what is already playing and starts or stops the difference, so sending
        the same descriptor twice does not restart the track.

        For a one-off sound, use `state.push_media()` instead.

        Args:
            character (Object): The character to describe.

        Returns:
            list: Media dicts with at least `url` and `category`, and
                optionally `id`, `caption`, `description`, `decorative`,
                `loop` and `volume`.

        """
        return []


def safe_call(provider, method_name, default, *args, **kwargs):
    """
    Call a provider method, containing any failure.

    A provider is game-supplied code executing inside a websocket handler. If it
    raises, the player must still get a working client -- a broken resource
    provider should cost the resource widget, not the whole session.

    The traceback is logged so the developer can see the real error rather than
    silently receiving empty data.

    Args:
        provider (AetosProvider): The provider instance.
        method_name (str): Method to call.
        default: Value to return if the call fails.
        *args: Positional arguments for the method.
        **kwargs: Keyword arguments for the method.

    Returns:
        The provider's return value, or `default` if it raised.

    """
    method = getattr(provider, method_name, None)
    if method is None:
        logger.log_err(
            "Aetos: provider %r has no method %r; using fallback."
            % (type(provider).__name__, method_name)
        )
        return default
    try:
        return method(*args, **kwargs)
    except Exception:
        logger.log_trace(
            "Aetos: provider %r raised in %r. Falling back to safe default."
            % (type(provider).__name__, method_name)
        )
        return default
