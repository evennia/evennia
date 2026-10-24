"""
Tests for E3 -- automation groups.

Addendum C.15, A11Y-COG-007.

The gate: **group state never changes automatically without explicit player
configuration.** A player switching to a "Combat" layout has said something
about where their panels go, not that their combat triggers should start firing.

"""

import re
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR

JS_DIR = Path(AETOS_STATIC_DIR) / "aetos" / "js"


def _read(relative):
    """
    Read a client module.

    Args:
        relative (str): Path under the js directory.

    Returns:
        str: Contents.

    """
    return (JS_DIR / relative).read_text(encoding="utf-8")


GROUPS = _read("automation/groups.js")
SHELL = _read("aetos.js")
SETTINGS = _read("settings.js")
TRIGGERS = _read("triggers.js")
ALIASES = _read("aliases.js")
RULES = _read("presentation/rules.js")


class TestTheEffectiveStateRule(TestCase):
    """
    `effective = rule.enabled AND group.enabled`.

    Both halves matter and neither overrides the other.

    """

    def test_the_rule_lives_in_one_place(self):
        """
        Five copies of a two-term expression is five chances for one to drift.

        """
        self.assertIn("function allows(rule)", GROUPS)

    def test_a_disabled_rule_stays_disabled_when_its_group_is_on(self):
        """
        The player turned it off individually, and a group switch does not undo
        that decision.

        """
        start = GROUPS.index("function allows(rule)")
        window = GROUPS[start : start + 300]
        self.assertIn("rule.enabled === false", window)
        self.assertIn("return false", window)

    def test_an_unknown_group_counts_as_enabled(self):
        """
        A rule referencing a group the player deleted keeps working. Silent
        inertness is the failure mode this module exists to make visible, and
        introducing it here would be perverse.

        """
        start = GROUPS.index("function isEnabled(groupId)")
        window = GROUPS[start : start + 400]
        self.assertIn("group ? group.enabled !== false : true", window)

    def test_suppression_is_reportable(self):
        """
        A rule that silently does nothing is indistinguishable from one that is
        broken, and the player will debug the wrong thing.

        """
        self.assertIn("function suppressed(rules)", GROUPS)
        start = GROUPS.index("function suppressed(rules)")
        window = GROUPS[start : start + 300]
        self.assertIn("rule.enabled !== false && !isEnabled(rule.group)", window)


class TestGroupsNeverChangeThemselves(TestCase):
    """A11Y-COG-007, and the milestone's gate."""

    def test_nothing_in_the_shell_toggles_a_group_automatically(self):
        """
        The only callers are the settings dialog and the palette, both of which
        are the player acting.

        """
        for match in re.finditer(r"(setEnabled|toggle)\(", SHELL):
            start = max(0, match.start() - 400)
            context = SHELL[start : match.start()]
            self.assertNotIn(
                "workspaces",
                context,
                "a workspace change appears to toggle automation",
            )

    def test_the_workspace_module_does_not_touch_groups(self):
        workspaces = _read("workspaces.js")
        self.assertNotIn("automationGroups", workspaces)
        self.assertNotIn("setEnabled", workspaces)

    def test_no_pipeline_stage_toggles_a_group(self):
        """
        A game event must not be able to switch a player's automation on.

        """
        self.assertNotIn("groups.setEnabled", _read("events/pipeline.js"))
        self.assertNotIn("groups.toggle", _read("events/pipeline.js"))

    def test_groups_default_to_enabled(self):
        """
        A group arriving switched off would silently disable every rule just
        assigned to it, which reads as the assignment having broken them.

        """
        self.assertIn("enabled: raw.enabled !== false", GROUPS)

    def test_toggling_says_what_it_did(self):
        """
        A switch whose effect is invisible is a switch nobody trusts.

        """
        start = GROUPS.index("function setEnabled(")
        window = GROUPS[start : start + 900]
        self.assertIn("announce(", window)
        self.assertIn("affected", window)


class TestTheEnginesConsultIt(TestCase):
    """Wiring, not just existence."""

    def test_triggers_use_the_shared_gate(self):
        self.assertIn("function allowed(rule)", TRIGGERS)
        self.assertIn("groups.allows(rule)", TRIGGERS)
        self.assertIn("!allowed(trigger)", TRIGGERS)

    def test_aliases_use_the_shared_gate(self):
        self.assertIn("function allowed(rule)", ALIASES)
        self.assertIn("!allowed(alias)", ALIASES)

    def test_an_engine_without_the_module_behaves_as_before(self):
        """
        A client missing the groups module must not lose its automation.

        """
        start = TRIGGERS.index("function allowed(rule)")
        window = TRIGGERS[start : start + 400]
        self.assertIn("return !rule || rule.enabled !== false;", window)

    def test_rules_carry_a_group(self):
        for source, name in (
            (TRIGGERS, "triggers"),
            (ALIASES, "aliases"),
            (RULES, "display rules"),
        ):
            self.assertIn("group", source, "%s cannot be grouped" % name)

    def test_display_rules_receive_the_active_map(self):
        self.assertIn("automationGroups.activeMap()", SHELL)

    def test_the_service_is_created_before_the_engines(self):
        """
        Each engine takes it as a service, so it has to exist first. `var`
        hoisting would otherwise hand them `undefined` silently.

        """
        self.assertLess(
            SHELL.index("var automationGroups ="),
            SHELL.index("var aliases ="),
        )


class TestTheEditorsExist(TestCase):
    """
    Closing the gap E2 deliberately left.

    A feature reachable only from a browser console is not a feature a player
    has, and E2 shipped display rules with no editor on the explicit promise
    that E3 would bring one.

    """

    def test_there_is_a_group_manager(self):
        self.assertIn("function openGroups", SETTINGS)
        self.assertIn('"groups.open"', SHELL)

    def test_there_is_a_display_rule_editor(self):
        self.assertIn("function editDisplayRule", SETTINGS)
        self.assertIn('"displayrule.new"', SHELL)

    def test_the_rule_editor_explains_that_hiding_is_not_deleting(self):
        """
        "Filter" reads like "delete" to anyone who has used another client, and
        the difference is the entire point of E2.

        """
        start = SETTINGS.index("function editDisplayRule")
        window = SETTINGS[start : start + 900]
        self.assertIn("never changes what", window)
        self.assertIn("still triggers", window)

    def test_the_group_manager_states_that_nothing_changes_it_automatically(self):
        start = SETTINGS.index("function openGroups")
        window = SETTINGS[start : start + 1600]
        self.assertIn("Nothing changes a group except you", window)

    def test_the_toggle_exposes_pressed_state(self):
        """
        The switch has to be readable to somebody who cannot see the styling.

        """
        start = SETTINGS.index("function openGroups")
        window = SETTINGS[start : start + 2200]
        self.assertIn('"aria-pressed"', window)

    def test_member_counts_are_derived_not_stored(self):
        """
        A stored count can disagree with reality. A derived one cannot.

        """
        self.assertIn("function countMembers", SETTINGS)
        start = SETTINGS.index("function countMembers")
        window = SETTINGS[start : start + 700]
        self.assertIn("rule.group === groupId", window)

    def test_the_privacy_panel_names_them_groups(self):
        self.assertIn('automation_profiles: "Automation groups"', SETTINGS)
