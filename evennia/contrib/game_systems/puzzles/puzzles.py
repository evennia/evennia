"""
Puzzles System - Provides a typeclass and commands for
objects that can be combined (i.e. 'use'd) to produce
new objects.

Evennia contribution - Henddher 2018

A Puzzle is a recipe of what objects (aka parts) must
be combined by a player so a new set of objects
(aka results) are automatically created.

Installation:

Add the PuzzleSystemCmdSet to all players (e.g. in their Character typeclass).

Alternatively:

    py self.cmdset.add('evennia.contrib.game_systems.puzzles.PuzzleSystemCmdSet')

Usage:

Consider this simple Puzzle:

    orange, mango, yogurt, blender = fruit smoothie

As a Builder:

    create/drop orange
    create/drop mango
    create/drop yogurt
    create/drop blender
    create/drop fruit smoothie

    puzzle smoothie, orange, mango, yogurt, blender = fruit smoothie
    ...
    Puzzle smoothie(#1234) created successfuly.

    destroy/force orange, mango, yogurt, blender, fruit smoothie

    armpuzzle #1234
    Part orange is spawned at ...
    Part mango is spawned at ...
    ....
    Puzzle smoothie(#1234) has been armed successfully

As Player:

    use orange, mango, yogurt, blender
    ...
    Genius, you blended all fruits to create a fruit smoothie!

Details:

Puzzles are created from existing objects. The given
objects are introspected to create prototypes for the
puzzle parts and results. These prototypes become the
puzzle recipe. (See PuzzleRecipe and @puzzle
command). Once the recipe is created, all parts and result
can be disposed (i.e. destroyed).

At a later time, a Builder or a Script can arm the puzzle
and spawn all puzzle parts in their respective
locations (See armpuzzle).

A regular player can collect the puzzle parts and combine
them (See use command). If player has specified
all pieces, the puzzle is considered solved and all
its puzzle parts are destroyed while the puzzle results
are spawened on their corresponding location.


"""

import itertools
from random import choice

from evennia import (
    CmdSet,
    DefaultCharacter,
    DefaultExit,
    DefaultRoom,
    DefaultScript,
    create_script,
)
from evennia.commands.default.muxcommand import MuxCommand
from evennia.prototypes.spawner import spawn
from evennia.utils import logger, search, utils
from evennia.utils.utils import inherits_from

# Tag used by puzzles
_PUZZLES_TAG_CATEGORY = "puzzles"
_PUZZLES_TAG_RECIPE = "puzzle_recipe"
# puzzle part and puzzle result
_PUZZLES_TAG_MEMBER = "puzzle_member"

_PUZZLE_DEFAULT_FAIL_USE_MESSAGE = "You try to utilize %s but nothing happens ... something amiss?"
_PUZZLE_DEFAULT_SUCCESS_USE_MESSAGE = "You are a Genius!!!"
_PUZZLE_DEFAULT_SUCCESS_USE_LOCATION_MESSAGE = "|c{caller}|n performs some kind of tribal dance and |y{result_names}|n seems to appear from thin air"

# ----------- UTILITY FUNCTIONS ------------


def proto_def(obj, with_tags=True):
    """
    Basic properties needed to spawn
    and compare recipe with candidate part
    """
    protodef = {
        # TODO: Don't we need to honor ALL properties? attributes, contents, etc.
        "prototype_key": "%s(%s)" % (obj.key, obj.dbref),
        "key": obj.key,
        "typeclass": obj.typeclass_path,
        "desc": obj.db.desc,
        "location": obj.location,
        "home": obj.home,
        "locks": ";".join(obj.locks.all()),
        "permissions": obj.permissions.all()[:],
    }
    if with_tags:
        tags = obj.tags.all(return_key_and_category=True)
        tags = [(t[0], t[1], None) for t in tags]
        tags.append((_PUZZLES_TAG_MEMBER, _PUZZLES_TAG_CATEGORY, None))
        protodef["tags"] = tags
    return protodef


def maskout_protodef(protodef, mask):
    """
    Returns a new protodef after removing protodef values based on mask
    """
    protodef = dict(protodef)
    for m in mask:
        if m in protodef:
            protodef.pop(m)
    return protodef


# Colorize the default success message
def _colorize_message(msg):
    _i = 0
    _colors = ["|r", "|g", "|y"]
    _msg = []
    for l in msg:
        _msg += _colors[_i] + l
        _i = (_i + 1) % len(_colors)
    msg = "".join(_msg) + "|n"
    return msg


_PUZZLE_DEFAULT_SUCCESS_USE_MESSAGE = _colorize_message(_PUZZLE_DEFAULT_SUCCESS_USE_MESSAGE)

# ------------------------------------------


class PuzzleRecipe(DefaultScript):
    """
    Definition of a Puzzle Recipe
    """

    def save_recipe(self, puzzle_name, parts, results):
        self.db.puzzle_name = str(puzzle_name)
        self.db.parts = tuple(parts)
        self.db.results = tuple(results)
        self.db.mask = tuple()
        self.tags.add(_PUZZLES_TAG_RECIPE, category=_PUZZLES_TAG_CATEGORY)
        self.db.use_success_message = _PUZZLE_DEFAULT_SUCCESS_USE_MESSAGE
        self.db.use_success_location_message = _PUZZLE_DEFAULT_SUCCESS_USE_LOCATION_MESSAGE


class CmdCreatePuzzleRecipe(MuxCommand):
    """
    Creates a puzzle recipe. A puzzle consists of puzzle-parts that
    the player can 'use' together to create a specified result.

    Usage:
        @puzzle name,<part1[,part2,...>] = <result1[,result2,...]>

    Example:
        create/drop balloon
        create/drop glass of water
        create/drop water balloon
        @puzzle waterballon,balloon,glass of water = water balloon
        @del ballon, glass of water, water balloon
        @armpuzzle #1

    Notes:
    Each part and result are objects that must (temporarily) exist and be placed in their
    corresponding location in order to create the puzzle. After the creation of the puzzle,
    these objects are not needed anymore and can be deleted. Components of the puzzle
    will be re-created by use of the `@armpuzzle` command later.

    """

    key = "@puzzle"
    aliases = "@puzzlerecipe"
    locks = "cmd:perm(puzzle) or perm(Builder)"
    help_category = "Puzzles"

    confirm = True
    default_confirm = "no"

    def func(self):
        caller = self.caller

        if len(self.lhslist) < 2 or not self.rhs:
            string = "Usage: @puzzle name,<part1[,...]> = <result1[,...]>"
            caller.msg(string)
            return

        puzzle_name = self.lhslist[0]
        if len(puzzle_name) == 0:
            caller.msg("Invalid puzzle name %r." % puzzle_name)
            return

        # if there is another puzzle with same name
        # warn user that parts and results will be
        # interchangable
        _puzzles = search.search_script_attribute(key="puzzle_name", value=puzzle_name)
        _puzzles = list(filter(lambda p: isinstance(p, PuzzleRecipe), _puzzles))
        if _puzzles:
            confirm = (
                "There are %d puzzles with the same name.\n" % len(_puzzles)
                + "Its parts and results will be interchangeable.\n"
                + "Continue yes/[no]? "
            )
            answer = ""
            while answer.strip().lower() not in ("y", "yes", "n", "no"):
                answer = yield (confirm)
                answer = self.default_confirm if answer == "" else answer
            if answer.strip().lower() in ("n", "no"):
                caller.msg("Cancelled: no puzzle created.")
                return

        def is_valid_obj_location(obj):
            valid = True
            # Rooms are the only valid locations.
            # TODO: other valid locations could be added here.
            # Certain locations can be handled accordingly: e.g,
            # a part is located in a character's inventory,
            # perhaps will translate into the player character
            # having the part in his/her inventory while being
            # located in the same room where the builder was
            # located.
            # Parts and results may have different valid locations
            if not inherits_from(obj.location, DefaultRoom):
                caller.msg("Invalid location for %s" % (obj.key))
                valid = False
            return valid

        def is_valid_part_location(part):
            return is_valid_obj_location(part)

        def is_valid_result_location(part):
            return is_valid_obj_location(part)

        def is_valid_inheritance(obj):
            valid = (
                not inherits_from(obj, DefaultCharacter)
                and not inherits_from(obj, DefaultRoom)
                and not inherits_from(obj, DefaultExit)
            )
            if not valid:
                caller.msg("Invalid typeclass for %s" % (obj))
            return valid

        def is_valid_part(part):
            return is_valid_inheritance(part) and is_valid_part_location(part)

        def is_valid_result(result):
            return is_valid_inheritance(result) and is_valid_result_location(result)

        parts = []
        for objname in self.lhslist[1:]:
            obj = caller.search(objname)
            if not obj:
                return
            if not is_valid_part(obj):
                return
            parts.append(obj)

        results = []
        for objname in self.rhslist:
            obj = caller.search(objname)
            if not obj:
                return
            if not is_valid_result(obj):
                return
            results.append(obj)

        for part in parts:
            caller.msg("Part %s(%s)" % (part.name, part.dbref))

        for result in results:
            caller.msg("Result %s(%s)" % (result.name, result.dbref))

        proto_parts = [proto_def(obj) for obj in parts]
        proto_results = [proto_def(obj) for obj in results]

        puzzle = create_script(PuzzleRecipe, key=puzzle_name, persistent=True)
        puzzle.save_recipe(puzzle_name, proto_parts, proto_results)
        puzzle.locks.add("control:id(%s) or perm(Builder)" % caller.dbref[1:])

        caller.msg(
            "Puzzle |y'%s' |w%s(%s)|n has been created |gsuccessfully|n."
            % (puzzle.db.puzzle_name, puzzle.name, puzzle.dbref)
        )

        caller.msg(
            "You may now dispose of all parts and results. \n"
            "Use @puzzleedit #{dbref} to customize this puzzle further. \n"
            "Use @armpuzzle #{dbref} to arm a new puzzle instance.".format(dbref=puzzle.dbref)
        )


class CmdEditPuzzle(MuxCommand):
    """
    Edits puzzle properties

    Usage:
        @puzzleedit[/delete] <#dbref>
        @puzzleedit <#dbref>/use_success_message = <Custom message>
        @puzzleedit <#dbref>/use_success_location_message = <Custom message from {caller} producing {result_names}>
        @puzzleedit <#dbref>/mask = attr1[,attr2,...]>
        @puzzleedit[/addpart] <#dbref> = <obj[,obj2,...]>
        @puzzleedit[/delpart] <#dbref> = <obj[,obj2,...]>
        @puzzleedit[/addresult] <#dbref> = <obj[,obj2,...]>
        @puzzleedit[/delresult] <#dbref> = <obj[,obj2,...]>

    Switches:
      addpart - adds parts to the puzzle
      delpart - removes parts from the puzzle
      addresult - adds results to the puzzle
      delresult - removes results from the puzzle
      delete - deletes the recipe. Existing parts and results aren't modified

      mask - attributes to exclude during matching (e.g. location, desc, etc.)
      use_success_location_message containing {result_names} and {caller} will
        automatically be replaced with correct values. Both are optional.

      When removing parts/results, it's possible to remove all.

    """

    key = "@puzzleedit"
    locks = "cmd:perm(puzzleedit) or perm(Builder)"
    help_category = "Puzzles"

    def func(self):
        self._USAGE = "Usage: @puzzleedit[/switches] <dbref>[/attribute = <value>]"
        caller = self.caller

        if not self.lhslist:
            caller.msg(self._USAGE)
            return

        if "/" in self.lhslist[0]:
            recipe_dbref, attr = self.lhslist[0].split("/")
        else:
            recipe_dbref = self.lhslist[0]

        if not utils.dbref(recipe_dbref):
            caller.msg("A puzzle recipe's #dbref must be specified.\n" + self._USAGE)
            return

        puzzle = search.search_script(recipe_dbref)
        if not puzzle or not inherits_from(puzzle[0], PuzzleRecipe):
            caller.msg("%s(%s) is not a puzzle" % (puzzle[0].name, recipe_dbref))
            return

        puzzle = puzzle[0]
        puzzle_name_id = "%s(%s)" % (puzzle.name, puzzle.dbref)

        if "delete" in self.switches:
            if not (puzzle.access(caller, "control") or puzzle.access(caller, "delete")):
                caller.msg("You don't have permission to delete %s." % puzzle_name_id)
                return

            puzzle.delete()
            caller.msg("%s was deleted" % puzzle_name_id)
            return

        elif "addpart" in self.switches:
            objs = self._get_objs()
            if objs:
                added = self._add_parts(objs, puzzle)
                caller.msg("%s were added to parts" % (", ".join(added)))
            return

        elif "delpart" in self.switches:
            objs = self._get_objs()
            if objs:
                removed = self._remove_parts(objs, puzzle)
                caller.msg("%s were removed from parts" % (", ".join(removed)))
            return

        elif "addresult" in self.switches:
            objs = self._get_objs()
            if objs:
                added = self._add_results(objs, puzzle)
                caller.msg("%s were added to results" % (", ".join(added)))
            return

        elif "delresult" in self.switches:
            objs = self._get_objs()
            if objs:
                removed = self._remove_results(objs, puzzle)
                caller.msg("%s were removed from results" % (", ".join(removed)))
            return

        else:
            # edit attributes

            if not (puzzle.access(caller, "control") or puzzle.access(caller, "edit")):
                caller.msg("You don't have permission to edit %s." % puzzle_name_id)
                return

            if attr == "use_success_message":
                puzzle.db.use_success_message = self.rhs
                caller.msg(
                    "%s use_success_message = %s\n"
                    % (puzzle_name_id, puzzle.db.use_success_message)
                )
                return
            elif attr == "use_success_location_message":
                puzzle.db.use_success_location_message = self.rhs
                caller.msg(
                    "%s use_success_location_message = %s\n"
                    % (puzzle_name_id, puzzle.db.use_success_location_message)
                )
                return
            elif attr == "mask":
                puzzle.db.mask = tuple(self.rhslist)
                caller.msg("%s mask = %r\n" % (puzzle_name_id, puzzle.db.mask))
                return

    def _get_objs(self):
        if not self.rhslist:
            self.caller.msg(self._USAGE)
            return
        objs = []
        for o in self.rhslist:
            obj = self.caller.search(o)
            if obj:
                objs.append(obj)
        return objs

    def _add_objs_to(self, objs, to):
        """Adds propto objs to the given set (parts or results)"""
        added = []
        toobjs = list(to[:])
        for obj in objs:
            protoobj = proto_def(obj)
            toobjs.append(protoobj)
            added.append(obj.key)
        return added, toobjs

    def _remove_objs_from(self, objs, frm):
        """Removes propto objs from the given set (parts or results)"""
        removed = []
        fromobjs = list(frm[:])
        for obj in objs:
            protoobj = proto_def(obj)
            if protoobj in fromobjs:
                fromobjs.remove(protoobj)
                removed.append(obj.key)
        return removed, fromobjs

    def _add_parts(self, objs, puzzle):
        added, toobjs = self._add_objs_to(objs, puzzle.db.parts)
        puzzle.db.parts = tuple(toobjs)
        return added

    def _remove_parts(self, objs, puzzle):
        removed, fromobjs = self._remove_objs_from(objs, puzzle.db.parts)
        puzzle.db.parts = tuple(fromobjs)
        return removed

    def _add_results(self, objs, puzzle):
        added, toobjs = self._add_objs_to(objs, puzzle.db.results)
        puzzle.db.results = tuple(toobjs)
        return added

    def _remove_results(self, objs, puzzle):
        removed, fromobjs = self._remove_objs_from(objs, puzzle.db.results)
        puzzle.db.results = tuple(fromobjs)
        return removed


class CmdArmPuzzle(MuxCommand):
    """
    Arms a puzzle by spawning all its parts.

    Usage:
      @armpuzzle <puzzle #dbref>

    Notes:
        Create puzzles with `@puzzle`; get list of
        defined puzzles using `@lspuzzlerecipes`.

    """

    key = "@armpuzzle"
    locks = "cmd:perm(armpuzzle) or perm(Builder)"
    help_category = "Puzzles"

    def func(self):
        caller = self.caller

        if self.args is None or not utils.dbref(self.args):
            caller.msg("A puzzle recipe's #dbref must be specified")
            return

        puzzle = search.search_script(self.args)
        if not puzzle or not inherits_from(puzzle[0], PuzzleRecipe):
            caller.msg("Invalid puzzle %r" % (self.args))
            return

        puzzle = puzzle[0]
        caller.msg(
            "Puzzle Recipe %s(%s) '%s' found.\nSpawning %d parts ..."
            % (puzzle.name, puzzle.dbref, puzzle.db.puzzle_name, len(puzzle.db.parts))
        )

        for proto_part in puzzle.db.parts:
            part = spawn(proto_part)[0]
            caller.msg(
                "Part %s(%s) spawned and placed at %s(%s)"
                % (part.name, part.dbref, part.location, part.location.dbref)
            )
            part.tags.add(puzzle.db.puzzle_name, category=_PUZZLES_TAG_CATEGORY)
            part.db.puzzle_name = puzzle.db.puzzle_name

        caller.msg("Puzzle armed |gsuccessfully|n.")


def _lookups_parts_puzzlenames_protodefs(parts):
    # Create lookup dicts by part's dbref and by puzzle_name(tags)
    parts_dict = dict()
    puzzlename_tags_dict = dict()
    puzzle_ingredients = dict()
    for part in parts:
        parts_dict[part.dbref] = part
        protodef = proto_def(part, with_tags=False)
        # remove 'prototype_key' as it will prevent equality
        del protodef["prototype_key"]
        puzzle_ingredients[part.dbref] = protodef
        tags_categories = part.tags.all(return_key_and_category=True)
        for tag, category in tags_categories:
            if category != _PUZZLES_TAG_CATEGORY:
                continue
            if tag not in puzzlename_tags_dict:
                puzzlename_tags_dict[tag] = []
            puzzlename_tags_dict[tag].append(part.dbref)
    return parts_dict, puzzlename_tags_dict, puzzle_ingredients


def _puzzles_by_names(names):
    # Find all puzzles by puzzle name (i.e. tag name)
    puzzles = []
    for puzzle_name in names:
        _puzzles = search.search_script_attribute(key="puzzle_name", value=puzzle_name)
        _puzzles = list(filter(lambda p: isinstance(p, PuzzleRecipe), _puzzles))
        if not _puzzles:
            continue
        else:
            puzzles.extend(_puzzles)
    return puzzles


def _matching_puzzles(puzzles, puzzlename_tags_dict, puzzle_ingredients):
    # Check if parts can be combined to solve a puzzle
    matched_puzzles = dict()
    for puzzle in puzzles:
        puzzle_protoparts = list(puzzle.db.parts[:])
        puzzle_mask = puzzle.db.mask[:]
        # remove tags and prototype_key as they prevent equality
        for i, puzzle_protopart in enumerate(puzzle_protoparts[:]):
            del puzzle_protopart["tags"]
            del puzzle_protopart["prototype_key"]
            puzzle_protopart = maskout_protodef(puzzle_protopart, puzzle_mask)
            puzzle_protoparts[i] = puzzle_protopart

        matched_dbrefparts = []
        parts_dbrefs = puzzlename_tags_dict[puzzle.db.puzzle_name]
        for part_dbref in parts_dbrefs:
            protopart = puzzle_ingredients[part_dbref]
            protopart = maskout_protodef(protopart, puzzle_mask)
            if protopart in puzzle_protoparts:
                puzzle_protoparts.remove(protopart)
                matched_dbrefparts.append(part_dbref)
        else:
            if len(puzzle_protoparts) == 0:
                matched_puzzles[puzzle.dbref] = matched_dbrefparts
    return matched_puzzles


class CmdUsePuzzleParts(MuxCommand):
    """
    Use an object, or a group of objects at once.


    Example:
      You look around you and see a pole, a long string, and a needle.

      use pole, long string, needle

      Genius! You built a fishing pole.


    Usage:
        use <obj1> [,obj2,...]
    """

    # Technical explanation
    """
    Searches for all puzzles whose parts match the given set of objects. If there are matching
    puzzles, the result objects are spawned in their corresponding location if all parts have been
    passed in.
    """

    key = "use"
    aliases = "combine"
    locks = "cmd:pperm(use) or pperm(Player)"
    help_category = "Puzzles"

    def func(self):
        caller = self.caller

        if not self.lhs:
            caller.msg("Use what?")
            return

        many = "these" if len(self.lhslist) > 1 else "this"

        # either all are parts, or abort finding matching puzzles
        parts = []
        partnames = self.lhslist[:]
        for partname in partnames:
            part = caller.search(
                partname,
                multimatch_string="Which %s. There are many.\n" % (partname),
                nofound_string="There is no %s around." % (partname),
            )

            if not part:
                return

            if not part.tags.get(_PUZZLES_TAG_MEMBER, category=_PUZZLES_TAG_CATEGORY):

                # not a puzzle part ... abort
                caller.msg("You have no idea how %s can be used" % (many))
                return

            # a valid part
            parts.append(part)

        # Create lookup dicts by part's dbref and by puzzle_name(tags)
        parts_dict, puzzlename_tags_dict, puzzle_ingredients = _lookups_parts_puzzlenames_protodefs(
            parts
        )

        # Find all puzzles by puzzle name (i.e. tag name)
        puzzles = _puzzles_by_names(puzzlename_tags_dict.keys())

        logger.log_info("PUZZLES %r" % ([(p.dbref, p.db.puzzle_name) for p in puzzles]))

        # Create lookup dict of puzzles by dbref
        puzzles_dict = dict((puzzle.dbref, puzzle) for puzzle in puzzles)
        # Check if parts can be combined to solve a puzzle
        matched_puzzles = _matching_puzzles(puzzles, puzzlename_tags_dict, puzzle_ingredients)

        if len(matched_puzzles) == 0:
            # TODO: we could use part.fail_message instead, if there was one
            #    random part falls and lands on your feet
            #    random part hits you square on the face
            caller.msg(_PUZZLE_DEFAULT_FAIL_USE_MESSAGE % (many))
            return

        puzzletuples = sorted(matched_puzzles.items(), key=lambda t: len(t[1]), reverse=True)

        logger.log_info("MATCHED PUZZLES %r" % (puzzletuples))

        # sort all matched puzzles and pick largest one(s)
        puzzledbref, matched_dbrefparts = puzzletuples[0]
        nparts = len(matched_dbrefparts)
        puzzle = puzzles_dict[puzzledbref]
        largest_puzzles = list(itertools.takewhile(lambda t: len(t[1]) == nparts, puzzletuples))

        # if there are more than one, choose one at random.
        # we could show the names of all those that can be resolved
        # but that would give away that there are other puzzles that
        # can be resolved with the same parts.
        # just hint how many.
        if len(largest_puzzles) > 1:
            caller.msg(
                "Your gears start turning and %d different ideas come to your mind ...\n"
                % (len(largest_puzzles))
            )
            puzzletuple = choice(largest_puzzles)
            puzzle = puzzles_dict[puzzletuple[0]]
            caller.msg("You try %s ..." % (puzzle.db.puzzle_name))

        # got one, spawn its results
        result_names = []
        for proto_result in puzzle.db.results:
            result = spawn(proto_result)[0]
            result.tags.add(puzzle.db.puzzle_name, category=_PUZZLES_TAG_CATEGORY)
            result.db.puzzle_name = puzzle.db.puzzle_name
            result_names.append(result.name)

        # Destroy all parts used
        for dbref in matched_dbrefparts:
            parts_dict[dbref].delete()

        result_names = ", ".join(result_names)
        caller.msg(puzzle.db.use_success_message)
        caller.location.msg_contents(
            puzzle.db.use_success_location_message.format(caller=caller, result_names=result_names),
            exclude=(caller,),
        )


class CmdListPuzzleRecipes(MuxCommand):
    """
    Searches for all puzzle recipes

    Usage:
        @lspuzzlerecipes
    """

    key = "@lspuzzlerecipes"
    locks = "cmd:perm(lspuzzlerecipes) or perm(Builder)"
    help_category = "Puzzles"

    def func(self):
        caller = self.caller

        recipes = search.search_script_tag(_PUZZLES_TAG_RECIPE, category=_PUZZLES_TAG_CATEGORY)

        div = "-" * 60
        text = [div]
        msgf_recipe = "Puzzle |y'%s' %s(%s)|n"
        msgf_item = "%2s|c%15s|n: |w%s|n"
        for recipe in recipes:
            text.append(msgf_recipe % (recipe.db.puzzle_name, recipe.name, recipe.dbref))
            text.append("Success Caller message:\n" + recipe.db.use_success_message + "\n")
            text.append(
                "Success Location message:\n" + recipe.db.use_success_location_message + "\n"
            )
            text.append("Mask:\n" + str(recipe.db.mask) + "\n")
            text.append("Parts")
            for protopart in recipe.db.parts[:]:
                mark = "-"
                for k, v in protopart.items():
                    text.append(msgf_item % (mark, k, v))
                    mark = ""
            text.append("Results")
            for protoresult in recipe.db.results[:]:
                mark = "-"
                for k, v in protoresult.items():
                    text.append(msgf_item % (mark, k, v))
                    mark = ""
        else:
            text.append(div)
            text.append("Found |r%d|n puzzle(s)." % (len(recipes)))
            text.append(div)
        caller.msg("\n".join(text))


class CmdListArmedPuzzles(MuxCommand):
    """
    Searches for all armed puzzles

    Usage:
        @lsarmedpuzzles
    """

    key = "@lsarmedpuzzles"
    locks = "cmd:perm(lsarmedpuzzles) or perm(Builder)"
    help_category = "Puzzles"

    def func(self):
        caller = self.caller

        armed_puzzles = search.search_tag(_PUZZLES_TAG_MEMBER, category=_PUZZLES_TAG_CATEGORY)

        armed_puzzles = dict(
            (k, list(g)) for k, g in itertools.groupby(armed_puzzles, lambda ap: ap.db.puzzle_name)
        )

        div = "-" * 60
        msgf_pznm = "Puzzle name: |y%s|n"
        msgf_item = "|m%25s|w(%s)|n at |c%25s|w(%s)|n"
        text = [div]
        for pzname, items in armed_puzzles.items():
            text.append(msgf_pznm % (pzname))
            for item in items:
                text.append(
                    msgf_item % (item.name, item.dbref, item.location.name, item.location.dbref)
                )
        else:
            text.append(div)
            text.append("Found |r%d|n armed puzzle(s)." % (len(armed_puzzles)))
            text.append(div)
        caller.msg("\n".join(text))


class PuzzleSystemCmdSet(CmdSet):
    """
    CmdSet to create, arm and resolve Puzzles
    """

    def at_cmdset_creation(self):
        super().at_cmdset_creation()

        self.add(CmdCreatePuzzleRecipe())
        self.add(CmdEditPuzzle())
        self.add(CmdArmPuzzle())
        self.add(CmdListPuzzleRecipes())
        self.add(CmdListArmedPuzzles())
        self.add(CmdUsePuzzleParts())
