"""
Tests for M27 -- configuration validation.

Every Aetos setting was already validated, carefully, with messages naming the
setting and the key and what was wrong. What was missing was *when*: the
validation ran when a player connected, and reported to that player's browser and
to a log nobody was watching. A developer could misconfigure Aetos on Monday and
find out from a player on Friday.

These checks move the same validators to `evennia start`, through Django's
system-check framework.

Two decisions worth stating, because both are the kind a reviewer should
question:

- **Everything is a Warning, never an Error.** Django refuses to start on a check
  Error. Aetos is an optional webclient on a game that also serves telnet, and
  stopping a whole MUD because its web interface has a typo in a settings key
  would be a worse failure than the typo.
- **The checks call the runtime's own validators**, not copies. A check with its
  own idea of what is valid is worse than no check, because it disagrees with the
  code -- passing at startup and failing at request time, or the reverse.

"""

import os
import tempfile

from django.conf import settings
from django.core.checks import Warning as CheckWarning
from django.test import TestCase, override_settings

from evennia.contrib.base_systems.aetos_webclient import AETOS_TEMPLATE_DIR, checks

#: Every setting the table validates.
#:
#: Named here so a test for one of them can pin the others to something valid.
#: A test that let the surrounding game supply the rest would assert a fact
#: about this laboratory's settings file rather than about the code -- which has
#: caught this project out twice already, at A5 and at M23.
ALL_AETOS_SETTINGS = (
    "AETOS_PROVIDERS",
    "AETOS_FEATURES",
    "AETOS_AUTOMATION",
    "AETOS_UI",
    "AETOS_CSP",
)

#: A valid value for each, for use as the quiet background of a one-fault test.
VALID = {name: {} for name in ALL_AETOS_SETTINGS}


def _only(**broken):
    """
    Settings where exactly the named ones are broken and the rest are valid.

    Args:
        **broken: Setting name to malformed value.

    Returns:
        dict: A complete set of Aetos settings for `override_settings`.

    """
    combined = dict(VALID)
    combined.update(broken)
    return combined


def _templates(dirs):
    """
    A `TEMPLATES` setting with the given `DIRS`.

    Args:
        dirs (list): Template directories.

    Returns:
        list: A one-engine TEMPLATES setting.

    """
    return [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": list(dirs)}]


def _ids(results):
    """
    The check ids in a result list.

    Args:
        results (list): What a check returned.

    Returns:
        list: Check ids.

    """
    return [item.id for item in results]


class TestTheCheckThatMattersMost(TestCase):
    """
    Template precedence: the one misconfiguration with no symptom.

    The game starts, the webclient URL works, and it serves Evennia's stock
    client. Nothing is broken and nothing is Aetos, and there is no error
    anywhere to search for.

    """

    def test_a_correct_install_is_quiet(self):
        with override_settings(TEMPLATES=_templates([AETOS_TEMPLATE_DIR])):
            self.assertEqual(checks.check_template_precedence(None), [])

    def test_a_missing_template_directory_is_reported(self):
        with override_settings(TEMPLATES=_templates([])):
            results = checks.check_template_precedence(None)
        self.assertEqual(_ids(results), ["aetos.W001"])

    def test_that_warning_says_why_installing_the_app_was_not_enough(self):
        """
        The hint has to answer the question the developer is actually asking,
        which is "but I did install it". Django searches every DIRS entry before
        any installed app.

        """
        with override_settings(TEMPLATES=_templates([])):
            hint = checks.check_template_precedence(None)[0].hint
        self.assertIn("DIRS", hint)
        self.assertIn("insert(0, AETOS_TEMPLATE_DIR)", hint)
        # And the trap that sends people down the wrong path entirely.
        self.assertIn("WEBCLIENT_TEMPLATE", hint)

    def test_appending_instead_of_inserting_is_reported(self):
        """
        `.append(AETOS_TEMPLATE_DIR)` puts Aetos *after* Evennia's own directory.
        The setting looks right, the path is present, and the stock client is
        still served -- which is the same invisible failure one step further on.

        """
        with tempfile.TemporaryDirectory() as earlier:
            with open(os.path.join(earlier, "webclient.html"), "w", encoding="utf-8") as handle:
                handle.write("stock")
            with override_settings(TEMPLATES=_templates([earlier, AETOS_TEMPLATE_DIR])):
                results = checks.check_template_precedence(None)
        self.assertEqual(_ids(results), ["aetos.W002"])

    def test_the_warning_names_the_directory_that_wins(self):
        """
        "Something is ahead of you" is not actionable. The path is.

        """
        with tempfile.TemporaryDirectory() as earlier:
            with open(os.path.join(earlier, "webclient.html"), "w", encoding="utf-8") as handle:
                handle.write("stock")
            with override_settings(TEMPLATES=_templates([earlier, AETOS_TEMPLATE_DIR])):
                hint = checks.check_template_precedence(None)[0].hint
            # The leaf name, rather than the whole path: the check normalises
            # case and separators, and asserting on the exact rendering would
            # test the platform rather than the message.
            self.assertIn(os.path.basename(earlier), hint)

    def test_an_unrelated_directory_ahead_of_aetos_is_fine(self):
        """
        Games put their own template directories in DIRS for their own reasons.
        Only one that would answer a request for `webclient.html` competes.

        """
        with tempfile.TemporaryDirectory() as earlier:
            with override_settings(TEMPLATES=_templates([earlier, AETOS_TEMPLATE_DIR])):
                self.assertEqual(checks.check_template_precedence(None), [])

    def test_a_missing_templates_setting_does_not_crash_the_check(self):
        """
        A check that raises during `evennia start` is worse than the
        misconfiguration it was looking for.

        """
        with override_settings(TEMPLATES=[]):
            results = checks.check_template_precedence(None)
        self.assertEqual(_ids(results), ["aetos.W001"])


class TestTheInputHandlerCheck(TestCase):
    """
    Not fatal, and that is exactly what makes it worth a warning: the client
    loads, the game plays, and every feature the game configured is silently
    absent.

    """

    def test_a_registered_module_is_quiet(self):
        with override_settings(INPUT_FUNC_MODULES=[checks.INPUTFUNC_MODULE]):
            self.assertEqual(checks.check_inputfuncs_registered(None), [])

    def test_an_unregistered_module_is_reported(self):
        with override_settings(INPUT_FUNC_MODULES=[]):
            results = checks.check_inputfuncs_registered(None)
        self.assertEqual(_ids(results), ["aetos.W003"])

    def test_the_warning_describes_a_degraded_client_rather_than_a_broken_one(self):
        """
        Told accurately, because a developer who reads "broken" and sees a
        working client concludes the warning is wrong and stops reading the
        others.

        """
        with override_settings(INPUT_FUNC_MODULES=[]):
            warning = checks.check_inputfuncs_registered(None)[0]
        self.assertIn("still load", warning.hint)
        self.assertIn("Input command not recognized", warning.hint)

    def test_an_absent_setting_is_handled(self):
        with override_settings(INPUT_FUNC_MODULES=None):
            self.assertEqual(_ids(checks.check_inputfuncs_registered(None)), ["aetos.W003"])


class TestSettingsAreCheckedWithTheRuntimeValidators(TestCase):
    """
    The point of the table: one definition of valid.

    """

    def test_a_game_that_configures_nothing_is_quiet(self):
        """
        The zero-configuration client is the whole progressive-enhancement
        premise. An absent setting is not a finding.

        `override_settings` cannot remove a setting, so this deletes each name
        from the holder it installs -- the only way to make one genuinely absent
        for the duration of a test rather than present and empty. The two are
        different: `AETOS_UI = {}` is a game that configured nothing explicitly,
        and no `AETOS_UI` at all is a game that has never heard of it.

        """
        with override_settings():
            for name in ALL_AETOS_SETTINGS:
                if hasattr(settings, name):
                    delattr(settings, name)
            self.assertFalse(any(hasattr(settings, name) for name in ALL_AETOS_SETTINGS))
            self.assertEqual(checks.check_settings_are_valid(None), [])

    def test_a_bad_provider_path_is_reported(self):
        with override_settings(**_only(AETOS_PROVIDERS={"resources": "world.nope.Missing"})):
            results = checks.check_settings_are_valid(None)
        self.assertEqual(len(results), 1)
        self.assertIn("AETOS_PROVIDERS", results[0].msg)

    def test_an_unknown_provider_slot_is_reported(self):
        with override_settings(**_only(AETOS_PROVIDERS={"resourcs": "world.x.Y"})):
            results = checks.check_settings_are_valid(None)
        self.assertEqual(len(results), 1)

    def test_a_bad_feature_flag_is_reported(self):
        with override_settings(**_only(AETOS_FEATURES={"map": "yes please"})):
            results = checks.check_settings_are_valid(None)
        self.assertEqual(len(results), 1)
        self.assertIn("AETOS_FEATURES", results[0].msg)

    def test_a_bad_ui_manifest_is_reported(self):
        with override_settings(**_only(AETOS_UI={"resourcs": []})):
            results = checks.check_settings_are_valid(None)
        self.assertEqual(len(results), 1)
        self.assertIn("AETOS_UI", results[0].msg)

    def test_a_bad_policy_is_reported(self):
        with override_settings(**_only(AETOS_CSP={"frame-ancestors": ["'none'"]})):
            results = checks.check_settings_are_valid(None)
        self.assertEqual(len(results), 1)
        self.assertIn("AETOS_CSP", results[0].msg)

    def test_the_original_message_survives(self):
        """
        The runtime's message names the key and says what was wrong with it.
        A check that replaced it with "AETOS_UI is invalid" would be strictly
        less useful than the exception it was meant to surface earlier.

        """
        with override_settings(**_only(AETOS_UI={"resourcs": []})):
            message = checks.check_settings_are_valid(None)[0].msg
        self.assertIn("resourcs", message)
        self.assertIn("Valid sections", message)

    def test_several_bad_settings_are_all_reported(self):
        """
        One per run would mean fixing them one restart at a time.

        """
        with override_settings(
            **_only(AETOS_FEATURES={"map": 1}, AETOS_UI={"resourcs": []}, AETOS_CSP={"nope": []})
        ):
            results = checks.check_settings_are_valid(None)
        self.assertEqual(len(results), 3)
        self.assertEqual(len(set(_ids(results))), 3, "check ids collide: %s" % _ids(results))

    def test_every_finding_is_a_warning_and_not_an_error(self):
        """
        Django refuses to start on a check Error. A MUD serving telnet players
        must not be stopped by a typo in its webclient's settings.

        """
        with override_settings(
            INPUT_FUNC_MODULES=[], TEMPLATES=[], **_only(AETOS_UI={"resourcs": []})
        ):
            results = (
                checks.check_settings_are_valid(None)
                + checks.check_inputfuncs_registered(None)
                + checks.check_template_precedence(None)
            )
        self.assertTrue(results)
        for item in results:
            self.assertIsInstance(item, CheckWarning)


class TestTheChecksAreActuallyRegistered(TestCase):
    """
    A check module nothing imports is a file, not a check.

    """

    def test_the_app_config_imports_them(self):
        from pathlib import Path

        from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR

        source = (Path(AETOS_STATIC_DIR).parent / "apps.py").read_text(encoding="utf-8")
        self.assertIn("def ready(self):", source)
        self.assertIn("import checks", source)

    def test_django_knows_about_them(self):
        from django.core.checks import registry

        registered = {check.__name__ for check in registry.registry.get_checks()}
        for name in (
            "check_template_precedence",
            "check_inputfuncs_registered",
            "check_settings_are_valid",
        ):
            self.assertIn(name, registered)
