"""
Testing puzzles.

"""

# Test of the Puzzles module

import itertools
import re

from mock import Mock

from evennia.commands.default.tests import BaseEvenniaCommandTest
from evennia.utils import search
from evennia.utils.create import create_object

from . import puzzles


class TestPuzzles(BaseEvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.steel = create_object(self.object_typeclass, key="steel", location=self.char1.location)
        self.flint = create_object(self.object_typeclass, key="flint", location=self.char1.location)
        self.fire = create_object(self.object_typeclass, key="fire", location=self.char1.location)
        self.steel.tags.add("tag-steel")
        self.steel.tags.add("tag-steel", category="tagcat")
        self.flint.tags.add("tag-flint")
        self.flint.tags.add("tag-flint", category="tagcat")
        self.fire.tags.add("tag-fire")
        self.fire.tags.add("tag-fire", category="tagcat")

    def _assert_msg_matched(self, msg, regexs, re_flags=0):
        matches = []
        for regex in regexs:
            m = re.search(regex, msg, re_flags)
            self.assertIsNotNone(m, "%r didn't match %r" % (regex, msg))
            matches.append(m)
        return matches

    def _assert_recipe(self, name, parts, results, and_destroy_it=True, expected_count=1):
        def _keys(items):
            return [item["key"] for item in items]

        recipes = search.search_script_tag("", category=puzzles._PUZZLES_TAG_CATEGORY)
        self.assertEqual(expected_count, len(recipes))
        self.assertEqual(name, recipes[expected_count - 1].db.puzzle_name)
        self.assertEqual(parts, _keys(recipes[expected_count - 1].db.parts))
        self.assertEqual(results, _keys(recipes[expected_count - 1].db.results))
        self.assertEqual(
            puzzles._PUZZLES_TAG_RECIPE,
            recipes[expected_count - 1].tags.get(category=puzzles._PUZZLES_TAG_CATEGORY),
        )
        recipe_dbref = recipes[expected_count - 1].dbref
        if and_destroy_it:
            recipes[expected_count - 1].delete()
        return recipe_dbref if not and_destroy_it else None

    def _assert_no_recipes(self):
        self.assertEqual(
            0, len(search.search_script_tag("", category=puzzles._PUZZLES_TAG_CATEGORY))
        )

    # good recipes
    def _good_recipe(self, name, parts, results, and_destroy_it=True, expected_count=1):
        regexs = []
        for p in parts:
            regexs.append(r"^Part %s\(#\d+\)$" % (p))
        for r in results:
            regexs.append(r"^Result %s\(#\d+\)$" % (r))
        regexs.append(r"^Puzzle '%s' %s\(#\d+\) has been created successfully.$" % (name, name))
        lhs = [name] + parts
        cmdstr = ",".join(lhs) + "=" + ",".join(results)
        msg = self.call(puzzles.CmdCreatePuzzleRecipe(), cmdstr, caller=self.char1)
        recipe_dbref = self._assert_recipe(name, parts, results, and_destroy_it, expected_count)
        self._assert_msg_matched(msg, regexs, re_flags=re.MULTILINE | re.DOTALL)
        return recipe_dbref

    def _check_room_contents(self, expected, check_test_tags=False):
        by_obj_key = lambda o: o.key
        room1_contents = sorted(self.room1.contents, key=by_obj_key)
        for key, grp in itertools.groupby(room1_contents, by_obj_key):
            if key in expected:
                grp = list(grp)
                self.assertEqual(
                    expected[key],
                    len(grp),
                    "Expected %d but got %d for %s" % (expected[key], len(grp), key),
                )
                if check_test_tags:
                    for gi in grp:
                        tags = gi.tags.all(return_key_and_category=True)
                        self.assertIn(("tag-" + gi.key, "tagcat"), tags)

    def _arm(self, recipe_dbref, name, parts):
        regexs = [
            r"^Puzzle Recipe %s\(#\d+\) '%s' found.$" % (name, name),
            r"^Spawning %d parts ...$" % (len(parts)),
        ]
        for p in parts:
            regexs.append(r"^Part %s\(#\d+\) spawned .*$" % (p))
        regexs.append(r"^Puzzle armed successfully.$")
        msg = self.call(puzzles.CmdArmPuzzle(), recipe_dbref, caller=self.char1)
        self._assert_msg_matched(msg, regexs, re_flags=re.MULTILINE | re.DOTALL)

    def test_cmdset_puzzle(self):
        self.char1.cmdset.add("evennia.contrib.game_systems.puzzles.PuzzleSystemCmdSet")
        # FIXME: testing nothing, this is just to bump up coverage

    def test_cmd_puzzle(self):
        self._assert_no_recipes()

        # bad syntax
        def _bad_syntax(cmdstr):
            self.call(
                puzzles.CmdCreatePuzzleRecipe(),
                cmdstr,
                "Usage: @puzzle name,<part1[,...]> = <result1[,...]>",
                caller=self.char1,
            )

        _bad_syntax("")
        _bad_syntax("=")
        _bad_syntax("nothing =")
        _bad_syntax("= nothing")
        _bad_syntax("nothing")
        _bad_syntax(",nothing")
        _bad_syntax("name, nothing")
        _bad_syntax("name, nothing =")

        self._assert_no_recipes()

        self._good_recipe("makefire", ["steel", "flint"], ["fire", "steel", "flint"])
        self._good_recipe("hot steels", ["steel", "fire"], ["steel", "fire"])
        self._good_recipe(
            "furnace",
            ["steel", "steel", "fire"],
            ["steel", "steel", "fire", "fire", "fire", "fire"],
        )

        # bad recipes
        def _bad_recipe(name, parts, results, fail_regex):
            cmdstr = ",".join([name] + parts) + "=" + ",".join(results)
            msg = self.call(puzzles.CmdCreatePuzzleRecipe(), cmdstr, caller=self.char1)
            self._assert_no_recipes()
            self.assertIsNotNone(re.match(fail_regex, msg), msg)

        _bad_recipe("name", ["nothing"], ["neither"], r"Could not find 'nothing'.")
        _bad_recipe("name", ["steel"], ["nothing"], r"Could not find 'nothing'.")
        _bad_recipe("", ["steel", "fire"], ["steel", "fire"], r"^Invalid puzzle name ''.")
        self.steel.location = self.char1
        _bad_recipe("name", ["steel"], ["fire"], r"^Invalid location for steel$")
        _bad_recipe("name", ["flint"], ["steel"], r"^Invalid location for steel$")
        _bad_recipe("name", ["self"], ["fire"], r"^Invalid typeclass for Char$")
        _bad_recipe("name", ["here"], ["fire"], r"^Invalid typeclass for Room$")

        self._assert_no_recipes()

    def test_cmd_armpuzzle(self):
        # bad arms
        self.call(
            puzzles.CmdArmPuzzle(),
            "1",
            "A puzzle recipe's #dbref must be specified",
            caller=self.char1,
        )
        self.call(puzzles.CmdArmPuzzle(), "#1", "Invalid puzzle '#1'", caller=self.char1)

        recipe_dbref = self._good_recipe(
            "makefire", ["steel", "flint"], ["fire", "steel", "flint"], and_destroy_it=False
        )

        # delete proto parts and proto result
        self.steel.delete()
        self.flint.delete()
        self.fire.delete()

        # good arm
        self._arm(recipe_dbref, "makefire", ["steel", "flint"])
        self._check_room_contents({"steel": 1, "flint": 1}, check_test_tags=True)

    def _use(self, cmdstr, expmsg):
        msg = self.call(puzzles.CmdUsePuzzleParts(), cmdstr, expmsg, caller=self.char1)
        return msg

    def test_cmd_use(self):

        self._use("", "Use what?")
        self._use("something", "There is no something around.")
        self._use("steel", "You have no idea how this can be used")
        self._use("steel flint", "There is no steel flint around.")
        self._use("steel, flint", "You have no idea how these can be used")

        recipe_dbref = self._good_recipe(
            "makefire", ["steel", "flint"], ["fire"], and_destroy_it=False
        )
        recipe2_dbref = self._good_recipe(
            "makefire2", ["steel", "flint"], ["fire"], and_destroy_it=False, expected_count=2
        )

        # although there is steel and flint
        # those aren't valid puzzle parts because
        # the puzzle hasn't been armed
        self._use("steel", "You have no idea how this can be used")
        self._use("steel, flint", "You have no idea how these can be used")
        self._arm(recipe_dbref, "makefire", ["steel", "flint"])
        self._check_room_contents({"steel": 2, "flint": 2}, check_test_tags=True)

        # there are duplicated objects now
        self._use("steel", "Which steel. There are many")
        self._use("flint", "Which flint. There are many")

        # delete proto parts and proto results
        self.steel.delete()
        self.flint.delete()
        self.fire.delete()

        # solve puzzle
        self._use("steel, flint", "You are a Genius")
        self.assertEqual(
            1,
            len(
                list(
                    filter(
                        lambda o: o.key == "fire"
                        and ("makefire", puzzles._PUZZLES_TAG_CATEGORY)
                        in o.tags.all(return_key_and_category=True)
                        and (puzzles._PUZZLES_TAG_MEMBER, puzzles._PUZZLES_TAG_CATEGORY)
                        in o.tags.all(return_key_and_category=True),
                        self.room1.contents,
                    )
                )
            ),
        )
        self._check_room_contents({"steel": 0, "flint": 0, "fire": 1}, check_test_tags=True)

        # trying again will fail as it was resolved already
        # and the parts were destroyed
        self._use("steel, flint", "There is no steel around")
        self._use("flint, steel", "There is no flint around")

        # arm same puzzle twice so there are duplicated parts
        self._arm(recipe_dbref, "makefire", ["steel", "flint"])
        self._arm(recipe_dbref, "makefire", ["steel", "flint"])
        self._check_room_contents({"steel": 2, "flint": 2, "fire": 1}, check_test_tags=True)

        # try solving with multiple parts but incomplete set
        self._use(
            "steel-1, steel-2", "You try to utilize these but nothing happens ... something amiss?"
        )

        # arm the other puzzle. Their parts are identical
        self._arm(recipe2_dbref, "makefire2", ["steel", "flint"])
        self._check_room_contents({"steel": 3, "flint": 3, "fire": 1}, check_test_tags=True)

        # solve with multiple parts for
        # multiple puzzles. Both can be solved but
        # only one is.
        self._use(
            "steel-1, flint-2, steel-3, flint-3",
            "Your gears start turning and 2 different ideas come to your mind ... ",
        )
        self._check_room_contents({"steel": 2, "flint": 2, "fire": 2}, check_test_tags=True)

        self.room1.msg_contents = Mock()

        # solve all
        self._use("steel-1, flint-1", "You are a Genius")
        self.room1.msg_contents.assert_called_once_with(
            "|cChar|n performs some kind of tribal dance and |yfire|n seems to appear from thin air",
            exclude=(self.char1,),
        )
        self._use("steel, flint", "You are a Genius")
        self._check_room_contents({"steel": 0, "flint": 0, "fire": 4}, check_test_tags=True)

    def test_puzzleedit(self):
        recipe_dbref = self._good_recipe(
            "makefire", ["steel", "flint"], ["fire"], and_destroy_it=False
        )

        def _puzzleedit(swt, dbref, args, expmsg):
            if (swt is None) and (dbref is None) and (args is None):
                cmdstr = ""
            else:
                cmdstr = "%s %s%s" % (swt, dbref, args)
            self.call(puzzles.CmdEditPuzzle(), cmdstr, expmsg, caller=self.char1)

        # delete proto parts and proto results
        self.steel.delete()
        self.flint.delete()
        self.fire.delete()

        sid = self.script.id
        # bad syntax
        _puzzleedit(
            None, None, None, "A puzzle recipe's #dbref must be specified.\nUsage: @puzzleedit"
        )
        _puzzleedit("", "1", "", "A puzzle recipe's #dbref must be specified.\nUsage: @puzzleedit")
        _puzzleedit("", "", "", "A puzzle recipe's #dbref must be specified.\nUsage: @puzzleedit")
        _puzzleedit(
            "",
            recipe_dbref,
            "dummy",
            "A puzzle recipe's #dbref must be specified.\nUsage: @puzzleedit",
        )
        _puzzleedit("", self.script.dbref, "", "Script(#{}) is not a puzzle".format(sid))

        # edit use_success_message and use_success_location_message
        _puzzleedit(
            "",
            recipe_dbref,
            "/use_success_message = Yes!",
            "makefire(%s) use_success_message = Yes!" % recipe_dbref,
        )
        _puzzleedit(
            "",
            recipe_dbref,
            "/use_success_location_message = {result_names} Yeah baby! {caller}",
            "makefire(%s) use_success_location_message = {result_names} Yeah baby! {caller}"
            % recipe_dbref,
        )

        self._arm(recipe_dbref, "makefire", ["steel", "flint"])
        self.room1.msg_contents = Mock()
        self._use("steel, flint", "Yes!")
        self.room1.msg_contents.assert_called_once_with(
            "fire Yeah baby! Char", exclude=(self.char1,)
        )
        self.room1.msg_contents.reset_mock()

        # edit mask: exclude location and desc during matching
        _puzzleedit(
            "",
            recipe_dbref,
            "/mask = location,desc",
            "makefire(%s) mask = ('location', 'desc')" % recipe_dbref,
        )

        self._arm(recipe_dbref, "makefire", ["steel", "flint"])
        # change location and desc
        self.char1.search("steel").db.desc = "A solid bar of steel"
        self.char1.search("steel").location = self.char1
        self.char1.search("flint").db.desc = "A flint steel"
        self.char1.search("flint").location = self.char1
        self._use("steel, flint", "Yes!")
        self.room1.msg_contents.assert_called_once_with(
            "fire Yeah baby! Char", exclude=(self.char1,)
        )

        # delete
        _puzzleedit("/delete", recipe_dbref, "", "makefire(%s) was deleted" % recipe_dbref)
        self._assert_no_recipes()

    def test_puzzleedit_add_remove_parts_results(self):
        recipe_dbref = self._good_recipe(
            "makefire", ["steel", "flint"], ["fire"], and_destroy_it=False
        )

        def _puzzleedit(swt, dbref, rhslist, expmsg):
            cmdstr = "%s %s = %s" % (swt, dbref, ", ".join(rhslist))
            self.call(puzzles.CmdEditPuzzle(), cmdstr, expmsg, caller=self.char1)

        red_steel = create_object(
            self.object_typeclass, key="red steel", location=self.char1.location
        )
        smoke = create_object(self.object_typeclass, key="smoke", location=self.char1.location)

        _puzzleedit("/addresult", recipe_dbref, ["smoke"], "smoke were added to results")
        _puzzleedit(
            "/addpart", recipe_dbref, ["red steel", "steel"], "red steel, steel were added to parts"
        )

        # create a box so we can put all objects in
        # so that they can't be found during puzzle resolution
        self.box = create_object(self.object_typeclass, key="box", location=self.char1.location)

        def _box_all():
            for o in self.room1.contents:
                if o not in [self.char1, self.char2, self.exit, self.obj1, self.obj2, self.box]:
                    o.location = self.box

        _box_all()

        self._arm(recipe_dbref, "makefire", ["steel", "flint", "red steel", "steel"])
        self._check_room_contents({"steel": 2, "red steel": 1, "flint": 1})
        self._use(
            "steel-1, flint", "You try to utilize these but nothing happens ... something amiss?"
        )
        self._use("steel-1, flint, red steel, steel-2", "You are a Genius")
        self._check_room_contents({"smoke": 1, "fire": 1})
        _box_all()

        self.fire.location = self.room1
        self.steel.location = self.room1

        _puzzleedit("/delresult", recipe_dbref, ["fire"], "fire were removed from results")
        _puzzleedit(
            "/delpart", recipe_dbref, ["steel", "steel"], "steel, steel were removed from parts"
        )

        _box_all()

        self._arm(recipe_dbref, "makefire", ["flint", "red steel"])
        self._check_room_contents({"red steel": 1, "flint": 1})
        self._use("red steel, flint", "You are a Genius")
        self._check_room_contents({"smoke": 1, "fire": 0})

    def test_lspuzzlerecipes_lsarmedpuzzles(self):
        msg = self.call(puzzles.CmdListPuzzleRecipes(), "", caller=self.char1)
        self._assert_msg_matched(
            msg, [r"^-+$", r"^Found 0 puzzle\(s\)\.$", r"-+$"], re.MULTILINE | re.DOTALL
        )

        recipe_dbref = self._good_recipe(
            "makefire", ["steel", "flint"], ["fire"], and_destroy_it=False
        )

        msg = self.call(puzzles.CmdListPuzzleRecipes(), "", caller=self.char1)
        self._assert_msg_matched(
            msg,
            [
                r"^-+$",
                r"^Puzzle 'makefire'.*$",
                r"^Success Caller message:$",
                r"^Success Location message:$",
                r"^Mask:$",
                r"^Parts$",
                r"^.*key: steel$",
                r"^.*key: flint$",
                r"^Results$",
                r"^.*key: fire$",
                r"^.*key: steel$",
                r"^.*key: flint$",
                r"^-+$",
                r"^Found 1 puzzle\(s\)\.$",
                r"^-+$",
            ],
            re.MULTILINE | re.DOTALL,
        )

        msg = self.call(puzzles.CmdListArmedPuzzles(), "", caller=self.char1)
        self._assert_msg_matched(
            msg,
            [r"^-+$", r"^-+$", r"^Found 0 armed puzzle\(s\)\.$", r"^-+$"],
            re.MULTILINE | re.DOTALL,
        )

        self._arm(recipe_dbref, "makefire", ["steel", "flint"])

        msg = self.call(puzzles.CmdListArmedPuzzles(), "", caller=self.char1)
        self._assert_msg_matched(
            msg,
            [
                r"^-+$",
                r"^Puzzle name: makefire$",
                r"^.*steel.* at \s+ Room.*$",
                r"^.*flint.* at \s+ Room.*$",
                r"^Found 1 armed puzzle\(s\)\.$",
                r"^-+$",
            ],
            re.MULTILINE | re.DOTALL,
        )

    def test_e2e(self):
        def _destroy_objs_in_room(keys):
            for obj in self.room1.contents:
                if obj.key in keys:
                    obj.delete()

        # parts don't survive resolution
        # but produce a large result set
        tree = create_object(self.object_typeclass, key="tree", location=self.char1.location)
        axe = create_object(self.object_typeclass, key="axe", location=self.char1.location)
        sweat = create_object(self.object_typeclass, key="sweat", location=self.char1.location)
        dull_axe = create_object(
            self.object_typeclass, key="dull axe", location=self.char1.location
        )
        timber = create_object(self.object_typeclass, key="timber", location=self.char1.location)
        log = create_object(self.object_typeclass, key="log", location=self.char1.location)
        parts = ["tree", "axe"]
        results = (["sweat"] * 10) + ["dull axe"] + (["timber"] * 20) + (["log"] * 50)
        recipe_dbref = self._good_recipe("lumberjack", parts, results, and_destroy_it=False)

        _destroy_objs_in_room(set(parts + results))

        sps = sorted(parts)
        expected = {key: len(list(grp)) for key, grp in itertools.groupby(sps)}
        expected.update({r: 0 for r in set(results)})

        self._arm(recipe_dbref, "lumberjack", parts)
        self._check_room_contents(expected)

        self._use(",".join(parts), "You are a Genius")
        srs = sorted(set(results))
        expected = {(key, len(list(grp))) for key, grp in itertools.groupby(srs)}
        expected.update({p: 0 for p in set(parts)})
        self._check_room_contents(expected)

        # parts also appear in results
        # causing a new puzzle to be armed 'automatically'
        # i.e. the puzzle is self-sustaining
        hole = create_object(self.object_typeclass, key="hole", location=self.char1.location)
        shovel = create_object(self.object_typeclass, key="shovel", location=self.char1.location)
        dirt = create_object(self.object_typeclass, key="dirt", location=self.char1.location)

        parts = ["shovel", "hole"]
        results = ["dirt", "hole", "shovel"]
        recipe_dbref = self._good_recipe(
            "digger", parts, results, and_destroy_it=False, expected_count=2
        )

        _destroy_objs_in_room(set(parts + results))

        nresolutions = 0

        sps = sorted(set(parts))
        expected = {key: len(list(grp)) for key, grp in itertools.groupby(sps)}
        expected.update({"dirt": nresolutions})

        self._arm(recipe_dbref, "digger", parts)
        self._check_room_contents(expected)

        for i in range(10):
            self._use(",".join(parts), "You are a Genius")
            nresolutions += 1
            expected.update({"dirt": nresolutions})
            self._check_room_contents(expected)

        # Uppercase puzzle name
        balloon = create_object(self.object_typeclass, key="Balloon", location=self.char1.location)
        parts = ["Balloon"]
        results = ["Balloon"]
        recipe_dbref = self._good_recipe(
            "boom!!!", parts, results, and_destroy_it=False, expected_count=3
        )

        _destroy_objs_in_room(set(parts + results))

        sps = sorted(parts)
        expected = {key: len(list(grp)) for key, grp in itertools.groupby(sps)}

        self._arm(recipe_dbref, "boom!!!", parts)
        self._check_room_contents(expected)

        self._use(",".join(parts), "You are a Genius")
        srs = sorted(set(results))
        expected = {(key, len(list(grp))) for key, grp in itertools.groupby(srs)}
        self._check_room_contents(expected)

    def test_e2e_accumulative(self):
        flashlight = create_object(
            self.object_typeclass, key="flashlight", location=self.char1.location
        )
        flashlight_w_1 = create_object(
            self.object_typeclass, key="flashlight-w-1", location=self.char1.location
        )
        flashlight_w_2 = create_object(
            self.object_typeclass, key="flashlight-w-2", location=self.char1.location
        )
        flashlight_w_3 = create_object(
            self.object_typeclass, key="flashlight-w-3", location=self.char1.location
        )
        battery = create_object(self.object_typeclass, key="battery", location=self.char1.location)

        battery.tags.add("flashlight-1", category=puzzles._PUZZLES_TAG_CATEGORY)
        battery.tags.add("flashlight-2", category=puzzles._PUZZLES_TAG_CATEGORY)
        battery.tags.add("flashlight-3", category=puzzles._PUZZLES_TAG_CATEGORY)

        # TODO: instead of tagging each flashlight,
        # arm and resolve each puzzle in order so they all
        # are tagged correctly
        # it will be necessary to add/remove parts/results because
        # each battery is supposed to be consumed during resolution
        # as the new flashlight has one more battery than before
        flashlight_w_1.tags.add("flashlight-2", category=puzzles._PUZZLES_TAG_CATEGORY)
        flashlight_w_2.tags.add("flashlight-3", category=puzzles._PUZZLES_TAG_CATEGORY)

        recipe_fl1_dbref = self._good_recipe(
            "flashlight-1",
            ["flashlight", "battery"],
            ["flashlight-w-1"],
            and_destroy_it=False,
            expected_count=1,
        )
        recipe_fl2_dbref = self._good_recipe(
            "flashlight-2",
            ["flashlight-w-1", "battery"],
            ["flashlight-w-2"],
            and_destroy_it=False,
            expected_count=2,
        )
        recipe_fl3_dbref = self._good_recipe(
            "flashlight-3",
            ["flashlight-w-2", "battery"],
            ["flashlight-w-3"],
            and_destroy_it=False,
            expected_count=3,
        )

        # delete protoparts
        for obj in [battery, flashlight, flashlight_w_1, flashlight_w_2, flashlight_w_3]:
            obj.delete()

        def _group_parts(parts, excluding=set()):
            group = dict()
            dbrefs = dict()
            for o in self.room1.contents:
                if o.key in parts and o.dbref not in excluding:
                    if o.key not in group:
                        group[o.key] = []
                    group[o.key].append(o.dbref)
                    dbrefs[o.dbref] = o
            return group, dbrefs

        # arm each puzzle and group its parts
        self._arm(recipe_fl1_dbref, "flashlight-1", ["battery", "flashlight"])
        fl1_parts, fl1_dbrefs = _group_parts(["battery", "flashlight"])
        self._arm(recipe_fl2_dbref, "flashlight-2", ["battery", "flashlight-w-1"])
        fl2_parts, fl2_dbrefs = _group_parts(
            ["battery", "flashlight-w-1"], excluding=list(fl1_dbrefs.keys())
        )
        self._arm(recipe_fl3_dbref, "flashlight-3", ["battery", "flashlight-w-2"])
        fl3_parts, fl3_dbrefs = _group_parts(
            ["battery", "flashlight-w-2"],
            excluding=set(list(fl1_dbrefs.keys()) + list(fl2_dbrefs.keys())),
        )

        self._check_room_contents(
            {
                "battery": 3,
                "flashlight": 1,
                "flashlight-w-1": 1,
                "flashlight-w-2": 1,
                "flashlight-w-3": 0,
            }
        )

        # all batteries have identical protodefs
        battery_1 = fl1_dbrefs[fl1_parts["battery"][0]]
        battery_2 = fl2_dbrefs[fl2_parts["battery"][0]]
        battery_3 = fl3_dbrefs[fl3_parts["battery"][0]]
        protodef_battery_1 = puzzles.proto_def(battery_1, with_tags=False)
        del protodef_battery_1["prototype_key"]
        protodef_battery_2 = puzzles.proto_def(battery_2, with_tags=False)
        del protodef_battery_2["prototype_key"]
        protodef_battery_3 = puzzles.proto_def(battery_3, with_tags=False)
        del protodef_battery_3["prototype_key"]
        assert protodef_battery_1 == protodef_battery_2 == protodef_battery_3

        # each battery can be used in every other puzzle

        b1_parts_dict, b1_puzzlenames, b1_protodefs = puzzles._lookups_parts_puzzlenames_protodefs(
            [battery_1]
        )
        _puzzles = puzzles._puzzles_by_names(b1_puzzlenames.keys())
        assert set(["flashlight-1", "flashlight-2", "flashlight-3"]) == set(
            [p.db.puzzle_name for p in _puzzles]
        )
        matched_puzzles = puzzles._matching_puzzles(_puzzles, b1_puzzlenames, b1_protodefs)
        assert 0 == len(matched_puzzles)

        b2_parts_dict, b2_puzzlenames, b2_protodefs = puzzles._lookups_parts_puzzlenames_protodefs(
            [battery_2]
        )
        _puzzles = puzzles._puzzles_by_names(b2_puzzlenames.keys())
        assert set(["flashlight-1", "flashlight-2", "flashlight-3"]) == set(
            [p.db.puzzle_name for p in _puzzles]
        )
        matched_puzzles = puzzles._matching_puzzles(_puzzles, b2_puzzlenames, b2_protodefs)
        assert 0 == len(matched_puzzles)
        b3_parts_dict, b3_puzzlenames, b3_protodefs = puzzles._lookups_parts_puzzlenames_protodefs(
            [battery_3]
        )
        _puzzles = puzzles._puzzles_by_names(b3_puzzlenames.keys())
        assert set(["flashlight-1", "flashlight-2", "flashlight-3"]) == set(
            [p.db.puzzle_name for p in _puzzles]
        )
        matched_puzzles = puzzles._matching_puzzles(_puzzles, b3_puzzlenames, b3_protodefs)
        assert 0 == len(matched_puzzles)

        assert battery_1 == list(b1_parts_dict.values())[0]
        assert battery_2 == list(b2_parts_dict.values())[0]
        assert battery_3 == list(b3_parts_dict.values())[0]
        assert b1_puzzlenames.keys() == b2_puzzlenames.keys() == b3_puzzlenames.keys()
        for puzzle_name in ["flashlight-1", "flashlight-2", "flashlight-3"]:
            assert puzzle_name in b1_puzzlenames
            assert puzzle_name in b2_puzzlenames
            assert puzzle_name in b3_puzzlenames
        assert (
            list(b1_protodefs.values())[0]
            == list(b2_protodefs.values())[0]
            == list(b3_protodefs.values())[0]
            == protodef_battery_1
            == protodef_battery_2
            == protodef_battery_3
        )

        # all flashlights have similar protodefs except their key
        flashlight_1 = fl1_dbrefs[fl1_parts["flashlight"][0]]
        flashlight_2 = fl2_dbrefs[fl2_parts["flashlight-w-1"][0]]
        flashlight_3 = fl3_dbrefs[fl3_parts["flashlight-w-2"][0]]
        protodef_flashlight_1 = puzzles.proto_def(flashlight_1, with_tags=False)
        del protodef_flashlight_1["prototype_key"]
        assert protodef_flashlight_1["key"] == "flashlight"
        del protodef_flashlight_1["key"]
        protodef_flashlight_2 = puzzles.proto_def(flashlight_2, with_tags=False)
        del protodef_flashlight_2["prototype_key"]
        assert protodef_flashlight_2["key"] == "flashlight-w-1"
        del protodef_flashlight_2["key"]
        protodef_flashlight_3 = puzzles.proto_def(flashlight_3, with_tags=False)
        del protodef_flashlight_3["prototype_key"]
        assert protodef_flashlight_3["key"] == "flashlight-w-2"
        del protodef_flashlight_3["key"]
        assert protodef_flashlight_1 == protodef_flashlight_2 == protodef_flashlight_3

        # each flashlight can only be used in its own puzzle

        f1_parts_dict, f1_puzzlenames, f1_protodefs = puzzles._lookups_parts_puzzlenames_protodefs(
            [flashlight_1]
        )
        _puzzles = puzzles._puzzles_by_names(f1_puzzlenames.keys())
        assert set(["flashlight-1"]) == set([p.db.puzzle_name for p in _puzzles])
        matched_puzzles = puzzles._matching_puzzles(_puzzles, f1_puzzlenames, f1_protodefs)
        assert 0 == len(matched_puzzles)
        f2_parts_dict, f2_puzzlenames, f2_protodefs = puzzles._lookups_parts_puzzlenames_protodefs(
            [flashlight_2]
        )
        _puzzles = puzzles._puzzles_by_names(f2_puzzlenames.keys())
        assert set(["flashlight-2"]) == set([p.db.puzzle_name for p in _puzzles])
        matched_puzzles = puzzles._matching_puzzles(_puzzles, f2_puzzlenames, f2_protodefs)
        assert 0 == len(matched_puzzles)
        f3_parts_dict, f3_puzzlenames, f3_protodefs = puzzles._lookups_parts_puzzlenames_protodefs(
            [flashlight_3]
        )
        _puzzles = puzzles._puzzles_by_names(f3_puzzlenames.keys())
        assert set(["flashlight-3"]) == set([p.db.puzzle_name for p in _puzzles])
        matched_puzzles = puzzles._matching_puzzles(_puzzles, f3_puzzlenames, f3_protodefs)
        assert 0 == len(matched_puzzles)

        assert flashlight_1 == list(f1_parts_dict.values())[0]
        assert flashlight_2 == list(f2_parts_dict.values())[0]
        assert flashlight_3 == list(f3_parts_dict.values())[0]
        for puzzle_name in set(
            list(f1_puzzlenames.keys()) + list(f2_puzzlenames.keys()) + list(f3_puzzlenames.keys())
        ):
            assert puzzle_name in ["flashlight-1", "flashlight-2", "flashlight-3", "puzzle_member"]
        protodef_flashlight_1["key"] = "flashlight"
        assert list(f1_protodefs.values())[0] == protodef_flashlight_1
        protodef_flashlight_2["key"] = "flashlight-w-1"
        assert list(f2_protodefs.values())[0] == protodef_flashlight_2
        protodef_flashlight_3["key"] = "flashlight-w-2"
        assert list(f3_protodefs.values())[0] == protodef_flashlight_3

        # each battery can be matched with every other flashlight
        # to potentially resolve each puzzle
        for batt in [battery_1, battery_2, battery_3]:
            parts_dict, puzzlenames, protodefs = puzzles._lookups_parts_puzzlenames_protodefs(
                [batt, flashlight_1]
            )
            assert set([batt.dbref, flashlight_1.dbref]) == set(puzzlenames["flashlight-1"])
            assert set([batt.dbref]) == set(puzzlenames["flashlight-2"])
            assert set([batt.dbref]) == set(puzzlenames["flashlight-3"])
            _puzzles = puzzles._puzzles_by_names(puzzlenames.keys())
            assert set(["flashlight-1", "flashlight-2", "flashlight-3"]) == set(
                [p.db.puzzle_name for p in _puzzles]
            )
            matched_puzzles = puzzles._matching_puzzles(_puzzles, puzzlenames, protodefs)
            assert 1 == len(matched_puzzles)
            parts_dict, puzzlenames, protodefs = puzzles._lookups_parts_puzzlenames_protodefs(
                [batt, flashlight_2]
            )
            assert set([batt.dbref]) == set(puzzlenames["flashlight-1"])
            assert set([batt.dbref, flashlight_2.dbref]) == set(puzzlenames["flashlight-2"])
            assert set([batt.dbref]) == set(puzzlenames["flashlight-3"])
            _puzzles = puzzles._puzzles_by_names(puzzlenames.keys())
            assert set(["flashlight-1", "flashlight-2", "flashlight-3"]) == set(
                [p.db.puzzle_name for p in _puzzles]
            )
            matched_puzzles = puzzles._matching_puzzles(_puzzles, puzzlenames, protodefs)
            assert 1 == len(matched_puzzles)
            parts_dict, puzzlenames, protodefs = puzzles._lookups_parts_puzzlenames_protodefs(
                [batt, flashlight_3]
            )
            assert set([batt.dbref]) == set(puzzlenames["flashlight-1"])
            assert set([batt.dbref]) == set(puzzlenames["flashlight-2"])
            assert set([batt.dbref, flashlight_3.dbref]) == set(puzzlenames["flashlight-3"])
            _puzzles = puzzles._puzzles_by_names(puzzlenames.keys())
            assert set(["flashlight-1", "flashlight-2", "flashlight-3"]) == set(
                [p.db.puzzle_name for p in _puzzles]
            )
            matched_puzzles = puzzles._matching_puzzles(_puzzles, puzzlenames, protodefs)
            assert 1 == len(matched_puzzles)

        # delete all parts
        for part in (
            list(fl1_dbrefs.values()) + list(fl2_dbrefs.values()) + list(fl3_dbrefs.values())
        ):
            part.delete()

        self._check_room_contents(
            {
                "battery": 0,
                "flashlight": 0,
                "flashlight-w-1": 0,
                "flashlight-w-2": 0,
                "flashlight-w-3": 0,
            }
        )

        # arm first puzzle 3 times and group its parts so we can solve
        # all puzzles with the parts from the 1st armed
        for i in range(3):
            self._arm(recipe_fl1_dbref, "flashlight-1", ["battery", "flashlight"])
        fl1_parts, fl1_dbrefs = _group_parts(["battery", "flashlight"])

        # delete the 2 extra flashlights so we can start solving
        for flashlight_dbref in fl1_parts["flashlight"][1:]:
            fl1_dbrefs[flashlight_dbref].delete()

        self._check_room_contents(
            {
                "battery": 3,
                "flashlight": 1,
                "flashlight-w-1": 0,
                "flashlight-w-2": 0,
                "flashlight-w-3": 0,
            }
        )

        self._use("battery-1, flashlight", "You are a Genius")
        self._check_room_contents(
            {
                "battery": 2,
                "flashlight": 0,
                "flashlight-w-1": 1,
                "flashlight-w-2": 0,
                "flashlight-w-3": 0,
            }
        )

        self._use("battery-1, flashlight-w-1", "You are a Genius")
        self._check_room_contents(
            {
                "battery": 1,
                "flashlight": 0,
                "flashlight-w-1": 0,
                "flashlight-w-2": 1,
                "flashlight-w-3": 0,
            }
        )

        self._use("battery, flashlight-w-2", "You are a Genius")
        self._check_room_contents(
            {
                "battery": 0,
                "flashlight": 0,
                "flashlight-w-1": 0,
                "flashlight-w-2": 0,
                "flashlight-w-3": 1,
            }
        )

    def test_e2e_interchangeable_parts_and_results(self):
        # Parts and Results can be used in multiple puzzles
        egg = create_object(self.object_typeclass, key="egg", location=self.char1.location)
        flour = create_object(self.object_typeclass, key="flour", location=self.char1.location)
        boiling_water = create_object(
            self.object_typeclass, key="boiling water", location=self.char1.location
        )
        boiled_egg = create_object(
            self.object_typeclass, key="boiled egg", location=self.char1.location
        )
        dough = create_object(self.object_typeclass, key="dough", location=self.char1.location)
        pasta = create_object(self.object_typeclass, key="pasta", location=self.char1.location)

        # Three recipes:
        # 1. breakfast: egg + boiling water = boiled egg & boiling water
        # 2. dough: egg + flour = dough
        # 3. entree: dough + boiling water = pasta & boiling water
        # tag interchangeable parts according to their puzzles' name
        egg.tags.add("breakfast", category=puzzles._PUZZLES_TAG_CATEGORY)
        egg.tags.add("dough", category=puzzles._PUZZLES_TAG_CATEGORY)
        dough.tags.add("entree", category=puzzles._PUZZLES_TAG_CATEGORY)
        boiling_water.tags.add("breakfast", category=puzzles._PUZZLES_TAG_CATEGORY)
        boiling_water.tags.add("entree", category=puzzles._PUZZLES_TAG_CATEGORY)

        # create recipes
        recipe1_dbref = self._good_recipe(
            "breakfast",
            ["egg", "boiling water"],
            ["boiled egg", "boiling water"],
            and_destroy_it=False,
        )
        recipe2_dbref = self._good_recipe(
            "dough", ["egg", "flour"], ["dough"], and_destroy_it=False, expected_count=2
        )
        recipe3_dbref = self._good_recipe(
            "entree",
            ["dough", "boiling water"],
            ["pasta", "boiling water"],
            and_destroy_it=False,
            expected_count=3,
        )

        # delete protoparts
        for obj in [egg, flour, boiling_water, boiled_egg, dough, pasta]:
            obj.delete()

        # arm each puzzle and group its parts
        def _group_parts(parts, excluding=set()):
            group = dict()
            dbrefs = dict()
            for o in self.room1.contents:
                if o.key in parts and o.dbref not in excluding:
                    if o.key not in group:
                        group[o.key] = []
                    group[o.key].append(o.dbref)
                    dbrefs[o.dbref] = o
            return group, dbrefs

        self._arm(recipe1_dbref, "breakfast", ["egg", "boiling water"])
        breakfast_parts, breakfast_dbrefs = _group_parts(["egg", "boiling water"])
        self._arm(recipe2_dbref, "dough", ["egg", "flour"])
        dough_parts, dough_dbrefs = _group_parts(
            ["egg", "flour"], excluding=list(breakfast_dbrefs.keys())
        )
        self._arm(recipe3_dbref, "entree", ["dough", "boiling water"])
        entree_parts, entree_dbrefs = _group_parts(
            ["dough", "boiling water"],
            excluding=set(list(breakfast_dbrefs.keys()) + list(dough_dbrefs.keys())),
        )

        # create a box so we can put all objects in
        # so that they can't be found during puzzle resolution
        self.box = create_object(self.object_typeclass, key="box", location=self.char1.location)

        def _box_all():
            # print "boxing all\n", "-"*20
            for o in self.room1.contents:
                if o not in [self.char1, self.char2, self.exit, self.obj1, self.obj2, self.box]:
                    o.location = self.box
                    # print o.key, o.dbref, "boxed"
                else:
                    # print "skipped", o.key, o.dbref
                    pass

        def _unbox(dbrefs):
            # print "unboxing", dbrefs, "\n", "-"*20
            for o in self.box.contents:
                if o.dbref in dbrefs:
                    o.location = self.room1
                    # print "unboxed", o.key, o.dbref

        # solve dough puzzle using breakfast's egg
        # and dough's flour. A new dough will be created
        _box_all()
        _unbox(breakfast_parts.pop("egg") + dough_parts.pop("flour"))
        self._use("egg, flour", "You are a Genius")

        # solve entree puzzle with newly created dough
        # and breakfast's boiling water. A new
        # boiling water and pasta will be created
        _unbox(breakfast_parts.pop("boiling water"))
        self._use("boiling water, dough", "You are a Genius")

        # solve breakfast puzzle with dough's egg
        # and newly created boiling water. A new
        # boiling water and boiled egg will be created
        _unbox(dough_parts.pop("egg"))
        self._use("boiling water, egg", "You are a Genius")

        # solve entree puzzle using entree's dough
        # and newly created boiling water. A new
        # boiling water and pasta will be created
        _unbox(entree_parts.pop("dough"))
        self._use("boiling water, dough", "You are a Genius")

        self._check_room_contents({"boiling water": 1, "pasta": 2, "boiled egg": 1})
