"""
Tests for the Aetos manifest.

The manifest drives progressive enhancement, so the defaults matter as much as
the configured behaviour: a game that has said nothing must get a clean client,
not a screen of dead controls.

Configuration errors are tested hard because they fail dangerously. A typo in an
automation key would otherwise leave a developer believing they had disabled
scripting while the client cheerfully offered it.

"""

from django.test import TestCase, override_settings

from evennia.contrib.base_systems.aetos_webclient import constants, manifest


class TestManifestDefaults(TestCase):
    """A pristine game with no Aetos settings at all."""

    #: Cleared explicitly rather than assumed absent.
    #:
    #: These tests assert what a game that has configured *nothing* receives.
    #: Read from the ambient settings, they instead assert something about
    #: whichever game dir the suite happens to run in -- and they failed the
    #: moment the lab game enabled a provider, which is precisely the
    #: configuration a maintainer is most likely to have.
    PRISTINE = {"AETOS_PROVIDERS": {}, "AETOS_FEATURES": {}}

    def test_declares_the_protocol_version(self):
        self.assertEqual(manifest.build_manifest()["protocol"], constants.PROTOCOL_VERSION)

    def test_all_features_default_to_off(self):
        """
        Progressive enhancement: a game that has told Aetos nothing exposes
        nothing, so no widget appears for data that does not exist.

        """
        with override_settings(**self.PRISTINE):
            features = manifest.build_manifest()["features"]
        self.assertTrue(features)
        self.assertFalse(any(features.values()))

    def test_scripting_defaults_to_disabled(self):
        """Scripting is the highest-risk capability; opt in, never opt out."""
        self.assertFalse(manifest.build_manifest()["automation"]["scripting"])

    def test_timers_default_to_disabled(self):
        self.assertFalse(manifest.build_manifest()["automation"]["timers"])

    def test_ordinary_automation_defaults_to_enabled(self):
        """Macros and aliases are player conveniences that send normal commands."""
        automation = manifest.build_manifest()["automation"]
        self.assertTrue(automation["macros"])
        self.assertTrue(automation["aliases"])

    def test_manifest_shape_is_stable(self):
        """
        A client may rely on these keys existing at protocol v1 even while the
        values are empty, so it need not special-case missing sections.

        """
        payload = manifest.build_manifest()
        for key in (
            "protocol",
            "features",
            "automation",
            "resources",
            "widgets",
            "actions",
            "map",
            "media",
        ):
            self.assertIn(key, payload)


class TestVoicePolicy(TestCase):
    """
    Voice is governed by the same policy mechanism as other automation.

    A game may reasonably want spoken commands previewed rather than executed
    directly, in the same way it governs macros and triggers.

    """

    def test_voice_is_part_of_the_automation_policy(self):
        self.assertIn("voice", manifest.build_manifest()["automation"])

    @override_settings(AETOS_AUTOMATION={"voice": False})
    def test_voice_can_be_disabled_by_the_game(self):
        self.assertFalse(manifest.build_manifest()["automation"]["voice"])

    @override_settings(AETOS_AUTOMATION={"voice": False})
    def test_disabling_voice_leaves_other_policy_at_defaults(self):
        """A partial policy dict must not silently disable everything else."""
        automation = manifest.build_manifest()["automation"]
        self.assertTrue(automation["macros"])
        self.assertTrue(automation["aliases"])


class TestConfiguredPolicy(TestCase):
    """Games overriding the defaults."""

    @override_settings(AETOS_AUTOMATION={"scripting": True, "timers": True})
    def test_capabilities_can_be_enabled(self):
        automation = manifest.build_manifest()["automation"]
        self.assertTrue(automation["scripting"])
        self.assertTrue(automation["timers"])

    @override_settings(AETOS_FEATURES={"resources": True, "map": True})
    def test_features_can_be_enabled(self):
        features = manifest.build_manifest()["features"]
        self.assertTrue(features["resources"])
        self.assertTrue(features["map"])
        self.assertFalse(features["media"])

    @override_settings(AETOS_AUTOMATION={"macros": False})
    def test_partial_policy_merges_over_defaults(self):
        automation = manifest.build_manifest()["automation"]
        self.assertFalse(automation["macros"])
        self.assertTrue(automation["aliases"])


class TestConfigurationValidation(TestCase):
    """
    Malformed configuration must fail loudly.

    Blueprint section 64: invalid configuration should produce a useful developer
    error rather than a client crash or, worse, a silently wrong policy.

    """

    @override_settings(AETOS_AUTOMATION={"scripting_enabled": True})
    def test_unknown_automation_key_is_an_error(self):
        """
        A typo must not be silently ignored. Ignoring it would leave a developer
        believing scripting was configured while the real flag kept its default.

        """
        with self.assertRaises(manifest.AetosManifestError):
            manifest.build_manifest()

    @override_settings(AETOS_FEATURES={"maps": True})
    def test_unknown_feature_key_is_an_error(self):
        with self.assertRaises(manifest.AetosManifestError):
            manifest.build_manifest()

    @override_settings(AETOS_AUTOMATION={"scripting": "yes"})
    def test_non_boolean_policy_value_is_an_error(self):
        """ "yes" is truthy; accepting it would enable scripting by accident."""
        with self.assertRaises(manifest.AetosManifestError):
            manifest.build_manifest()

    @override_settings(AETOS_AUTOMATION=["macros"])
    def test_non_dict_automation_setting_is_an_error(self):
        with self.assertRaises(manifest.AetosManifestError):
            manifest.build_manifest()

    @override_settings(AETOS_AUTOMATION={"scripting_enabled": True})
    def test_error_message_names_the_offending_key(self):
        """A useful developer error names what was wrong and what is valid."""
        with self.assertRaises(manifest.AetosManifestError) as ctx:
            manifest.build_manifest()
        message = str(ctx.exception)
        self.assertIn("scripting_enabled", message)
        self.assertIn("AETOS_AUTOMATION", message)
