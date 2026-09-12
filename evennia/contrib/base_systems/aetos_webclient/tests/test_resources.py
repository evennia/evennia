"""
Tests for the Aetos generic resource system.

Two themes dominate:

* **Genre neutrality.** Nothing in Aetos may special-case a resource name. The
  tests deliberately use Sanity, Hull and Fuel rather than health and mana, so a
  hardcoded assumption would fail here.

* **Provider output is untrusted.** A resource provider is game-supplied code.
  Malformed output must degrade to "not shown" rather than reaching the client
  and breaking a widget.

"""

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import resources


class TestNormalizeResource(TestCase):
    """Validation of a single resource."""

    def test_accepts_a_minimal_resource(self):
        """Only id and value are genuinely required."""
        result = resources.normalize_resource({"id": "fuel", "value": 12})
        self.assertEqual(result["id"], "fuel")
        self.assertEqual(result["value"], 12)

    def test_label_defaults_to_the_id(self):
        """A resource with no label is still usable, not nameless."""
        result = resources.normalize_resource({"id": "fuel", "value": 1})
        self.assertEqual(result["label"], "fuel")

    def test_keeps_an_arbitrary_resource_name(self):
        """Sanity, Hull and Favour are as valid as anything else."""
        for name in ("sanity", "hull", "favour", "oxygen", "blood"):
            result = resources.normalize_resource({"id": name, "value": 1})
            self.assertEqual(result["id"], name)

    def test_rejects_a_missing_id(self):
        self.assertIsNone(resources.normalize_resource({"value": 1}))

    def test_rejects_a_missing_value(self):
        self.assertIsNone(resources.normalize_resource({"id": "fuel"}))

    def test_rejects_a_non_numeric_value(self):
        for value in ("50", None, [1], {"v": 1}):
            self.assertIsNone(resources.normalize_resource({"id": "fuel", "value": value}))

    def test_rejects_a_boolean_value(self):
        """
        bool subclasses int, so True would otherwise render as the number 1 and
        hide a provider bug behind a plausible-looking gauge.

        """
        self.assertIsNone(resources.normalize_resource({"id": "fuel", "value": True}))

    def test_rejects_nan_and_infinity(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            self.assertIsNone(resources.normalize_resource({"id": "fuel", "value": value}))

    def test_rejects_a_non_mapping(self):
        for entry in ([], "fuel", 7, None):
            self.assertIsNone(resources.normalize_resource(entry))

    def test_unknown_display_mode_falls_back(self):
        """A typo in a presentation hint must not stop the resource showing."""
        result = resources.normalize_resource({"id": "fuel", "value": 1, "display": "hologram"})
        self.assertEqual(result["display"], resources.DEFAULT_DISPLAY)

    def test_maximum_below_minimum_is_dropped(self):
        """
        A provider bug. Dropping the maximum leaves a usable unbounded counter
        rather than a gauge that renders nonsensically.

        """
        result = resources.normalize_resource(
            {"id": "fuel", "value": 5, "minimum": 10, "maximum": 2}
        )
        self.assertNotIn("maximum", result)

    def test_an_unbounded_resource_is_allowed(self):
        """Not every resource has a maximum; a counter is legitimate."""
        result = resources.normalize_resource({"id": "doses", "value": 7})
        self.assertNotIn("maximum", result)


class TestNormalizeThresholds(TestCase):
    """
    Thresholds are part of the schema from the start.

    Blueprint revision 2: announcing every change is unusable, so a game declares
    where the meaningful crossings are. A resource with no thresholds is simply
    never announced.

    """

    def test_thresholds_are_preserved(self):
        result = resources.normalize_resource(
            {
                "id": "sanity",
                "value": 50,
                "maximum": 100,
                "thresholds": [{"at": 0.5, "label": "Slipping."}],
            }
        )
        self.assertEqual(len(result["thresholds"]), 1)
        self.assertEqual(result["thresholds"][0]["label"], "Slipping.")

    def test_thresholds_are_sorted_descending(self):
        """
        So a client crossing several at once can report the most severe rather
        than whichever it happened to check first.

        """
        result = resources.normalize_resource(
            {
                "id": "sanity",
                "value": 50,
                "maximum": 100,
                "thresholds": [{"at": 0.2}, {"at": 0.8}, {"at": 0.5}],
            }
        )
        values = [entry["at"] for entry in result["thresholds"]]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_level_defaults_when_unrecognised(self):
        result = resources.normalize_resource(
            {
                "id": "sanity",
                "value": 1,
                "thresholds": [{"at": 0.5, "level": "catastrophic"}],
            }
        )
        self.assertEqual(result["thresholds"][0]["level"], resources.DEFAULT_THRESHOLD_LEVEL)

    def test_malformed_thresholds_are_dropped_individually(self):
        """One bad threshold must not discard the good ones."""
        result = resources.normalize_resource(
            {
                "id": "sanity",
                "value": 1,
                "thresholds": [{"at": 0.5}, {"no_at": True}, "nonsense", {"at": 0.2}],
            }
        )
        self.assertEqual(len(result["thresholds"]), 2)

    def test_threshold_count_is_bounded(self):
        result = resources.normalize_resource(
            {
                "id": "sanity",
                "value": 1,
                "thresholds": [{"at": i / 100.0} for i in range(100)],
            }
        )
        self.assertLessEqual(len(result["thresholds"]), resources.MAX_THRESHOLDS_PER_RESOURCE)

    def test_no_thresholds_means_never_announced(self):
        result = resources.normalize_resource({"id": "sanity", "value": 1})
        self.assertEqual(result["thresholds"], [])


class TestNormalizeResourceList(TestCase):
    """Validation of a provider's whole return value."""

    def test_drops_malformed_entries_individually(self):
        """One bad resource must not cost the player every other one."""
        result = resources.normalize_resources(
            [
                {"id": "good", "value": 1},
                {"broken": True},
                None,
                {"id": "also_good", "value": 2},
            ]
        )
        self.assertEqual([entry["id"] for entry in result], ["good", "also_good"])

    def test_drops_duplicate_ids(self):
        """Two resources with one id would make two widgets fight for a slot."""
        result = resources.normalize_resources(
            [
                {"id": "fuel", "value": 1},
                {"id": "fuel", "value": 2},
            ]
        )
        self.assertEqual(len(result), 1)

    def test_caps_the_list_length(self):
        result = resources.normalize_resources([{"id": "r%d" % i, "value": i} for i in range(500)])
        self.assertLessEqual(len(result), resources.MAX_RESOURCES)

    def test_a_non_list_yields_nothing(self):
        for value in (None, "fuel", 7, {"id": "fuel"}):
            self.assertEqual(resources.normalize_resources(value), [])

    def test_an_empty_list_is_fine(self):
        """A game with no resource system is the normal case, not an error."""
        self.assertEqual(resources.normalize_resources([]), [])


class TestFraction(TestCase):
    """Fill fraction, used for gauges and fractional thresholds."""

    def test_computes_a_fraction(self):
        resource = resources.normalize_resource({"id": "hull", "value": 25, "maximum": 100})
        self.assertAlmostEqual(resources.fraction(resource), 0.25)

    def test_respects_a_non_zero_minimum(self):
        resource = resources.normalize_resource(
            {"id": "temp", "value": 0, "minimum": -100, "maximum": 100}
        )
        self.assertAlmostEqual(resources.fraction(resource), 0.5)

    def test_unbounded_has_no_fraction(self):
        resource = resources.normalize_resource({"id": "doses", "value": 7})
        self.assertIsNone(resources.fraction(resource))

    def test_clamps_out_of_range_values(self):
        """
        A game may report a value beyond its own maximum during a transient.
        A gauge must not render past its own end.

        """
        over = resources.normalize_resource({"id": "hull", "value": 150, "maximum": 100})
        under = resources.normalize_resource({"id": "hull", "value": -50, "maximum": 100})
        self.assertEqual(resources.fraction(over), 1.0)
        self.assertEqual(resources.fraction(under), 0.0)
