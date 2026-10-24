"""
The Aetos manifest.

The manifest is how a game tells Aetos what it exposes. It is the mechanism
behind progressive enhancement: Aetos renders controls for what the manifest
declares and stays silent about everything else, so a pristine Evennia game gets
a clean client rather than a screen of dead buttons.

The manifest is descriptive, never permissive. Declaring an automation capability
tells the client it may show that editor; it grants no authority. Every command
the client ultimately sends still travels the ordinary Evennia command path and is
still subject to locks, permissions, cooldowns and game rules.

"""

from django.conf import settings

from evennia.contrib.base_systems.aetos_webclient import (
    constants,
    providers,
    ui_manifest,
)

# --- Automation policy ---------------------------------------------------

#: Automation capabilities a game may permit or forbid.
#:
#: These are *policy*, decided by the game developer. The client must honour
#: them: with "scripting" false, no scripting editor is offered at all.
#:
#: "voice" governs whether spoken input may execute a command directly. It is
#: listed here rather than treated as a client-only preference because a game
#: may reasonably want spoken commands previewed rather than executed, in the
#: same way it governs macros and triggers. Blueprint sections 32 and 87.
#:
#: **`voice` is reserved and nothing honours it yet.** Voice input is M33, which
#: ships after the upstream PR, and until it exists there is no spoken input for
#: the flag to govern -- `automationAllowed("voice")` has no caller anywhere in
#: the client.
#:
#: The key stays in the defaults rather than being removed, so that a game which
#: sets it is not met with an "unknown key" error for a setting the
#: documentation once described, and so M33 has its slot waiting. What it must
#: not do is *look* honoured: the README says plainly that this one is reserved,
#: and `test_documentation` ties that claim to whether the client actually
#: consults it -- so the day M33 lands, the test is what tells somebody to update
#: the sentence.
RESERVED_AUTOMATION = ("voice",)

DEFAULT_AUTOMATION = {
    "macros": True,
    "aliases": True,
    "triggers": True,
    "timers": False,
    "scripting": False,
    "voice": True,
}

#: Feature flags describing which structured subsystems the game exposes.
#: Everything defaults to False: a game that has told Aetos nothing gets the
#: zero-configuration experience, not broken widgets.
DEFAULT_FEATURES = {
    "resources": False,
    "map": False,
    "actions": False,
    "entities": False,
    "effects": False,
    "target": False,
    "inventory": False,
    "equipment": False,
    "media": False,
    "mode": False,
}


class AetosManifestError(ValueError):
    """Raised when a game's Aetos configuration is invalid."""


def _validate_policy(configured, defaults, setting_name):
    """
    Merge a game's policy dict over the defaults, rejecting bad configuration.

    A typo in a settings key is silent otherwise: the game believes it disabled
    scripting while the client happily offers it. Unknown keys are therefore an
    error rather than being ignored.

    Args:
        configured (dict): The game's setting value.
        defaults (dict): The default policy.
        setting_name (str): Setting name, used in error messages.

    Returns:
        dict: The merged policy.

    Raises:
        AetosManifestError: If the configuration is malformed.

    """
    if configured is None:
        return dict(defaults)
    if not isinstance(configured, dict):
        raise AetosManifestError(
            "%s must be a dict, got %r" % (setting_name, type(configured).__name__)
        )

    unknown = set(configured) - set(defaults)
    if unknown:
        raise AetosManifestError(
            "%s contains unknown key(s) %s. Valid keys: %s"
            % (setting_name, sorted(unknown), sorted(defaults))
        )

    merged = dict(defaults)
    for key, value in configured.items():
        if not isinstance(value, bool):
            raise AetosManifestError(
                "%s[%r] must be a boolean, got %r" % (setting_name, key, type(value).__name__)
            )
        merged[key] = value
    return merged


def get_automation_policy():
    """
    Resolve the game's automation policy.

    Returns:
        dict: Automation capability flags.

    Raises:
        AetosManifestError: If `AETOS_AUTOMATION` is malformed.

    """
    return _validate_policy(
        getattr(settings, "AETOS_AUTOMATION", None), DEFAULT_AUTOMATION, "AETOS_AUTOMATION"
    )


def get_features():
    """
    Resolve which structured subsystems the game exposes.

    Returns:
        dict: Feature flags.

    Raises:
        AetosManifestError: If `AETOS_FEATURES` is malformed.

    Notes:
        **A binding implies its capability.**  (D1)

        Declaring `AETOS_BINDINGS["resources"]` and then having to remember
        `AETOS_FEATURES = {"resources": True}` as well is exactly the kind of
        second step that makes a zero-code feature feel like it does not work.
        The developer has already said what they want, twice would be a chore
        and once is enough, so a bound slot switches its own flag on.

        **An explicit setting always wins, in both directions.** The derivation
        fills in a flag the game did not state; it never overrides one it did.
        A game that declared bindings and then set `"resources": False` is
        turning the widget off on purpose -- mid-migration, or behind a launch
        date -- and a helpful override would be Aetos arguing with it.

    """
    configured = getattr(settings, "AETOS_FEATURES", None)
    stated = set(configured) if isinstance(configured, dict) else set()

    features = _validate_policy(configured, DEFAULT_FEATURES, "AETOS_FEATURES")

    from evennia.contrib.base_systems.aetos_webclient import bindings

    for slot in bindings.bound_slots():
        if slot in features and slot not in stated:
            features[slot] = True

    return features


def build_manifest(character=None):
    """
    Build the `aetos_manifest` payload for a session.

    Args:
        character (Object, optional): The character the manifest is for. Accepted
            so that later milestones can vary the manifest per character (for
            example, exposing builder-only widgets). Unused at protocol v1.

    Returns:
        dict: The manifest payload.

    Raises:
        AetosManifestError: If the game's Aetos settings are malformed.

    """
    features = get_features()
    automation = get_automation_policy()

    # What the game says about its own interface (M23). Descriptive only --
    # labels, order and thresholds -- never a source of values.
    #
    # Translated to this function's own error type, and that is not tidiness.
    # `AetosUIError` is a sibling of `AetosManifestError`, not a subclass, and
    # the handshake in `inputfuncs.aetos_hello` catches only the latter -- so a
    # malformed `AETOS_UI` escaped the handshake as an unhandled exception
    # instead of the "server misconfiguration" reply the client is built to
    # receive. Every player connecting to that game hit it.
    #
    # The docstring above has always said this function raises
    # `AetosManifestError`. It was the code that did not keep the promise, so
    # the fix belongs here rather than in a longer `except` clause at the call
    # site -- a list of sibling exceptions to catch is a list that goes stale
    # the next time somebody adds a validator.
    try:
        described = ui_manifest.get_ui_description()
    except ui_manifest.AetosUIError as err:
        raise AetosManifestError(str(err)) from err

    payload = {
        "protocol": constants.PROTOCOL_VERSION,
        "features": features,
        "automation": automation,
        # A game may describe a resource before any provider supplies its
        # value, so a gauge can render labelled-and-pending rather than as an
        # empty panel somebody cannot interpret.
        "resources": described["resources"],
        "panels": described["panels"],
        # Declared so the shape is stable from protocol v1 onward and a client
        # can rely on the keys existing, even where nothing populates them yet.
        "widgets": [],
        "actions": [],
        "map": {},
        "media": {},
    }

    """
    Developer diagnostics.  Addendum C.17.

    Off by default and opt-in per game, because the payload names the game's own
    provider classes -- `world.aetos.MyResourceProvider` and the like. That is
    exactly what a maintainer needs in a bug report and exactly what a player has
    no business receiving, so a game says whether it wants to tell them.

    `AETOS_DIAGNOSTICS = True` is a development setting. It carries no secrets
    even when on -- class names and slot names only, never values, never source.
    """
    if getattr(settings, "AETOS_DIAGNOSTICS", False):
        try:
            payload["diagnostics"] = {"providers": providers.describe_providers()}
        except Exception as err:
            # A provider that cannot even describe itself is precisely the
            # situation a diagnostic report exists to explain, so the failure is
            # reported rather than swallowed.
            payload["diagnostics"] = {"providers": {}, "error": str(err)}

    return payload
