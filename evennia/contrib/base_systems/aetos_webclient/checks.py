"""
Startup checks for the Aetos Web Client.

Every Aetos setting is already validated where it is used, and a bad one raises
with a message naming the setting, the key and what was wrong. The gap this
module fills is **when the developer finds out**: at the moment a player
connects, as an error delivered to that player's browser and a line in a log
nobody is watching.

These run at `evennia start` and `evennia reload` instead, through Django's
system-check framework, so a misconfiguration is reported to the person who
caused it while they are still looking.

**Everything here is a Warning, never an Error, and that is deliberate.** Django
refuses to start on a check Error. Aetos is an optional webclient on a game that
also serves telnet, and stopping a whole MUD because its web interface has a typo
in a settings key would be a worse failure than the typo. A warning at startup is
loud enough: it is printed every time, it names the fix, and the game stays up
for the players already connected.

**What cannot be checked here.** Aetos's checks are registered by its own
`AppConfig`, so they run only if the app is in `INSTALLED_APPS`. A game that
added the template directory and the inputfuncs but forgot `INSTALLED_APPS` gets
no warning at all -- the checks are not loaded to give one. That failure has its
own loud symptom (every static asset 404s and the client renders unstyled), and
it is in the README's troubleshooting. It is recorded here because it is the
obvious check to add, and the next person to try will find it cannot work.

"""

import os

from django.conf import settings
from django.core.checks import Warning as CheckWarning
from django.core.checks import register

from evennia.contrib.base_systems.aetos_webclient import AETOS_TEMPLATE_DIR

#: The dotted path a game must add to `INPUT_FUNC_MODULES`.
INPUTFUNC_MODULE = "evennia.contrib.base_systems.aetos_webclient.inputfuncs"

#: How the README says to install it. Quoted in warnings so a developer can fix
#: the problem from the message rather than going to find the documentation.
INSTALL_SNIPPET = (
    "    from evennia.contrib.base_systems.aetos_webclient import AETOS_TEMPLATE_DIR\n"
    "\n"
    '    INSTALLED_APPS += ["evennia.contrib.base_systems.aetos_webclient"]\n'
    '    TEMPLATES[0]["DIRS"].insert(0, AETOS_TEMPLATE_DIR)\n'
    "    INPUT_FUNC_MODULES.append(\n"
    '        "evennia.contrib.base_systems.aetos_webclient.inputfuncs"\n'
    "    )"
)


def _template_dirs():
    """
    The first template engine's `DIRS`, as normalised strings.

    Returns:
        list: Absolute paths, or an empty list if `TEMPLATES` is unusable.

    """
    engines = getattr(settings, "TEMPLATES", None) or []
    if not engines or not isinstance(engines[0], dict):
        return []
    return [os.path.normcase(os.path.abspath(str(entry))) for entry in engines[0].get("DIRS", [])]


def _supplies_a_webclient_template(path):
    """
    Whether a template directory would answer a request for `webclient.html`.

    Matched by looking for the file rather than by importing Evennia's own
    settings, because the question is which directory *wins* the lookup -- and a
    game that copied or moved Evennia's templates wins it just the same.

    Args:
        path (str): A normalised template directory path.

    Returns:
        bool: True if this directory supplies a webclient template.

    """
    return os.path.isfile(os.path.join(path, "webclient.html")) or os.path.isfile(
        os.path.join(path, "webclient", "webclient.html")
    )


@register()
def check_template_precedence(app_configs, **kwargs):
    """
    Check that Aetos's templates will actually be found.

    This is the misconfiguration worth catching above all the others, because it
    is the only one with no symptom: the game starts, the webclient URL works,
    and it serves Evennia's stock client. Nothing is broken and nothing is Aetos.

    Args:
        app_configs: Unused; Django's check signature.
        **kwargs: Unused.

    Returns:
        list: Check warnings.

    """
    dirs = _template_dirs()
    aetos = os.path.normcase(os.path.abspath(AETOS_TEMPLATE_DIR))

    if aetos not in dirs:
        return [
            CheckWarning(
                'Aetos templates are not in TEMPLATES[0]["DIRS"], so Evennia\'s '
                "stock webclient will be served instead.",
                hint=(
                    "Django searches every DIRS entry before any installed app, and "
                    "Evennia always has its own webclient template directory in DIRS "
                    "-- so registering the app is not enough on its own. Add:\n\n"
                    '    TEMPLATES[0]["DIRS"].insert(0, AETOS_TEMPLATE_DIR)\n\n'
                    "Note that WEBCLIENT_TEMPLATE does not work for this: Evennia "
                    "builds TEMPLATES at import time in settings_default, so "
                    "reassigning it later has no effect on the already-built list."
                ),
                id="aetos.W001",
            )
        ]

    # Present, but is it early enough? `.append` instead of `.insert(0, ...)`
    # puts Aetos after Evennia's own directory, which loses every time and looks
    # exactly like not having installed it.
    position = dirs.index(aetos)
    for earlier in dirs[:position]:
        if _supplies_a_webclient_template(earlier):
            return [
                CheckWarning(
                    'Aetos templates are in TEMPLATES[0]["DIRS"] but after a '
                    "directory that also supplies a webclient template, so Evennia's "
                    "stock client will still win.",
                    hint=(
                        "Use insert(0, AETOS_TEMPLATE_DIR) rather than append(...). "
                        "The first matching directory wins, and the entry ahead of "
                        "Aetos is %r." % earlier
                    ),
                    id="aetos.W002",
                )
            ]
    return []


@register()
def check_inputfuncs_registered(app_configs, **kwargs):
    """
    Check that the two server-side handlers are reachable.

    Without them the client still loads and the game is playable, so this is a
    warning about a degraded install rather than a broken one -- but it is a
    degradation nobody diagnoses, because the client looks fine and simply has
    none of the features the game configured.

    Args:
        app_configs: Unused; Django's check signature.
        **kwargs: Unused.

    Returns:
        list: Check warnings.

    """
    modules = getattr(settings, "INPUT_FUNC_MODULES", None) or []
    if INPUTFUNC_MODULE in modules:
        return []
    return [
        CheckWarning(
            "Aetos's input handlers are not registered, so no manifest is sent "
            "and no progressive-enhancement features will appear.",
            hint=(
                "The client will still load and the game is still playable, but the "
                "server logs 'Input command not recognized' on every connect and "
                "nothing this game configured through AETOS_PROVIDERS, AETOS_UI or "
                "AETOS_FEATURES reaches the browser. Add:\n\n"
                "    INPUT_FUNC_MODULES.append(%r)" % INPUTFUNC_MODULE
            ),
            id="aetos.W003",
        )
    ]


def _setting_validators():
    """
    Each Aetos setting, paired with the callable that validates it.

    A table rather than one check per setting, and the callables are the ones
    the *runtime* uses. A check with its own idea of what is valid is worse than
    no check at all, because it disagrees with the code -- accepting a setting
    at startup that fails at request time, or the reverse.

    Imported inside the function so that a module which fails to import cannot
    stop the other checks from registering -- a broken settings module is
    exactly when checks are most useful.

    Returns:
        list: Tuples of (setting name, callable, exception type).

    """
    from evennia.contrib.base_systems.aetos_webclient import (
        bindings,
        csp,
        manifest,
        providers,
        ui_manifest,
    )

    return [
        ("AETOS_PROVIDERS", providers.get_providers, providers.AetosProviderError),
        ("AETOS_FEATURES", manifest.get_features, manifest.AetosManifestError),
        ("AETOS_AUTOMATION", manifest.get_automation_policy, manifest.AetosManifestError),
        ("AETOS_UI", ui_manifest.get_ui_description, ui_manifest.AetosUIError),
        ("AETOS_CSP", csp.build_policy, csp.AetosCspError),
        # D1. This one matters more than the rest, because a malformed binding
        # fails *quietly* at runtime by design: `bound_slots()` swallows the
        # error so a typo in settings.py cannot turn into a failed login. That
        # trade only works if the developer is told somewhere, and this is
        # where.
        ("AETOS_BINDINGS", bindings.get_bindings, bindings.AetosBindingError),
    ]


@register()
def check_settings_are_valid(app_configs, **kwargs):
    """
    Run every Aetos setting through the validator the runtime uses.

    Args:
        app_configs: Unused; Django's check signature.
        **kwargs: Unused.

    Returns:
        list: Check warnings, one per malformed setting.

    """
    problems = []
    for index, (name, validate, error_type) in enumerate(_setting_validators()):
        if not hasattr(settings, name):
            # An absent setting is the zero-configuration client, which is the
            # whole progressive-enhancement premise. Not a finding.
            continue
        try:
            validate()
        except error_type as err:
            problems.append(
                CheckWarning(
                    "%s is invalid: %s" % (name, err),
                    hint=(
                        "The client will start without it, and players will see "
                        "whatever this setting was meant to configure simply "
                        "missing. Fix the setting or remove it."
                    ),
                    id="aetos.W%03d" % (10 + index),
                )
            )
        except Exception as err:  # pragma: no cover - defensive
            # A validator raising something it did not document is itself worth
            # reporting. Swallowing it would turn a bug in Aetos into a setting
            # that silently does nothing.
            problems.append(
                CheckWarning(
                    "%s could not be validated: %s: %s" % (name, type(err).__name__, err),
                    hint="This is unexpected. Please report it with the traceback.",
                    id="aetos.W%03d" % (10 + index),
                )
            )
    return problems
