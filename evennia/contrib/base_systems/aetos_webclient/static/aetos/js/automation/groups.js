/*
 * Aetos automation groups.  Addendum C.15, A11Y-COG-007.
 *
 * One switch for a set of related automation: Combat, Exploration, Crafting,
 * Roleplay, Building -- whatever a player decides those are.
 *
 * THE PROBLEM. By the time somebody has thirty triggers, four timers and a
 * dozen aliases, "turn off my combat stuff" is a chore performed one checkbox at
 * a time, usually in a hurry and usually incompletely. A missed trigger then
 * fires in the wrong context, which is how people get into trouble in games
 * with rules about automation.
 *
 * THE RULE. `effective = rule.enabled AND group.enabled`
 *
 * Both halves matter and neither overrides the other. A disabled rule stays
 * disabled when its group is on -- the player turned it off individually and
 * that decision is not undone by a group switch. A rule in a disabled group is
 * inert regardless of its own flag.
 *
 * A GROUP SWITCH IS ALWAYS THE PLAYER'S (A11Y-COG-007). Nothing in Aetos
 * enables or disables a group on its own. A workspace does not, a game event
 * does not, and a route does not. Switching to a "Combat" layout is a statement
 * about where the panels go; it is not consent for combat triggers to start
 * firing, and a player discovering otherwise mid-fight is the worst possible
 * moment to find out.
 *
 * SUPPRESSION IS VISIBLE. A player must be able to see which rules are inert
 * because of a group rather than because of themselves. A rule that silently
 * does nothing is indistinguishable from a rule that is broken, and the player
 * will spend their time debugging the wrong thing.
 */

(function (window) {
    "use strict";

    //: Reuses the reserved `automation_profiles` namespace, which nothing had
    //: claimed. Repurposing avoids a schema bump; the privacy panel label moves
    //: with it so a player still sees a name that matches what they configured.
    var NAMESPACE = "automation_profiles";

    //: Kinds of thing a group can contain. Not a genre list -- these are the
    //: automation surfaces Aetos happens to have.
    var MEMBER_KINDS = [
        "aliases", "triggers", "timers", "macros", "scripts", "display_rules"
    ];

    var MAX_GROUPS = 40;

    function normalizeGroup(raw) {
        if (!raw || typeof raw !== "object") {
            return null;
        }
        var name = String(raw.name || "").trim();
        if (!name) {
            return null;
        }
        return {
            id: String(raw.id || name.toLowerCase()),
            name: name.slice(0, 40),
            description: String(raw.description || "").slice(0, 200),
            // Groups default to ON. A group that arrived switched off would
            // silently disable every rule a player had just assigned to it,
            // which reads as the assignment having broken them.
            enabled: raw.enabled !== false
        };
    }

    function createGroups(services) {
        var settings = services || {};
        var storage = settings.storage || null;
        var announce = settings.announce || function () {};

        var groups = [];
        var byId = {};

        function index() {
            byId = {};
            groups.forEach(function (group) { byId[group.id] = group; });
        }

        function load() {
            if (!storage) {
                return Promise.resolve([]);
            }
            return storage.all(NAMESPACE).then(function (rows) {
                groups = (rows || [])
                    .map(function (row) { return row.value; })
                    .slice(0, MAX_GROUPS)
                    .map(normalizeGroup)
                    .filter(Boolean);
                index();
                return groups.slice();
            }).catch(function () { return []; });
        }

        function save(raw) {
            var group = normalizeGroup(raw);
            if (!group) {
                return Promise.reject(new Error("A group needs a name."));
            }
            if (!storage) {
                return Promise.reject(new Error("No local storage available."));
            }
            return storage.put(NAMESPACE, group.id, group).then(function () {
                return load().then(function () { return group; });
            });
        }

        function remove(id) {
            if (!storage) {
                return Promise.resolve(false);
            }
            return storage.remove(NAMESPACE, id).then(function () {
                return load().then(function () { return true; });
            });
        }

        /*
         * Is this group currently on?
         *
         * An unknown group counts as **enabled**. A rule referencing a group
         * the player has since deleted should keep working rather than going
         * quietly inert -- silent inertness is the failure mode this whole
         * module exists to make visible, and it would be perverse to introduce
         * it here.
         */
        function isEnabled(groupId) {
            if (!groupId) {
                return true;
            }
            var group = byId[groupId];
            return group ? group.enabled !== false : true;
        }

        /*
         * The effective state of one rule.
         *
         * The single place this logic lives. Every engine consults it rather
         * than reimplementing `enabled && groupEnabled`, because five copies of
         * a two-term expression is five chances for one of them to drift.
         */
        function allows(rule) {
            if (!rule || rule.enabled === false) {
                return false;
            }
            return isEnabled(rule.group);
        }

        /*
         * Which rules are inert because of their group rather than themselves.
         *
         * This is what makes suppression visible. A player looking at a trigger
         * that is not firing needs to know whether they turned it off or their
         * group did, because the two have completely different fixes.
         */
        function suppressed(rules) {
            return (rules || []).filter(function (rule) {
                return rule.enabled !== false && !isEnabled(rule.group);
            });
        }

        /*
         * Turn a group on or off.
         *
         * Always in response to a player action -- there is no code path that
         * calls this from a game event, a workspace change or a route. The
         * announcement says which way it went and how many rules moved with it,
         * because a switch whose effect is invisible is a switch nobody trusts.
         */
        function setEnabled(id, enabled, affectedCount) {
            var group = byId[id];
            if (!group) {
                return Promise.resolve(false);
            }
            group.enabled = enabled !== false;
            return save(group).then(function () {
                var count = typeof affectedCount === "number" ? affectedCount : null;
                announce(
                    group.name + (group.enabled ? " enabled." : " disabled.") +
                    (count === null ? "" : " " + count +
                        (count === 1 ? " rule" : " rules") + " affected."),
                    { category: "system", priority: "important" }
                );
                return true;
            });
        }

        function toggle(id, affectedCount) {
            var group = byId[id];
            if (!group) {
                return Promise.resolve(false);
            }
            return setEnabled(id, !group.enabled, affectedCount);
        }

        /*
         * A map of group id to enabled, for callers that want to evaluate many
         * rules without a function call each -- the display-rule engine takes
         * one of these per event.
         */
        function activeMap() {
            var map = {};
            groups.forEach(function (group) { map[group.id] = group.enabled !== false; });
            return map;
        }

        return {
            load: load,
            save: save,
            remove: remove,
            isEnabled: isEnabled,
            allows: allows,
            suppressed: suppressed,
            setEnabled: setEnabled,
            toggle: toggle,
            activeMap: activeMap,
            all: function () { return groups.slice(); },
            get: function (id) { return byId[id] || null; },
            count: function () { return groups.length; }
        };
    }

    window.AetosAutomationGroups = {
        create: createGroups,
        normalizeGroup: normalizeGroup,
        NAMESPACE: NAMESPACE,
        MEMBER_KINDS: MEMBER_KINDS.slice(),
        MAX_GROUPS: MAX_GROUPS
    };

})(window);
