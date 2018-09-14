"""
Puzzles System - Provides a typeclass and commands for
objects that can be combined (i.e. 'use'd) to produce
new objects.

Evennia contribution - Henddher 2018

A Puzzle is a recipe of what objects (aka parts) must
be combined by a player so a new set of objects
(aka results) are automatically created.

Consider this simple Puzzle:

    orange, mango, yogurt, blender = fruit smoothie

As a Builder:

    @create/drop orange
    @create/drop mango
    @create/drop yogurt
    @create/drop blender
    @create/drop fruit smoothie

    @puzzle smoothie, orange, mango, yogurt, blender = fruit smoothie
    ...
    Puzzle smoothie(#1234) created successfuly.

    @destroy/force orange, mango, yogurt, blender, fruit smoothie

    @armpuzzle #1234
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
and spawn all puzzle parts (PuzzlePartObject) in their
respective locations (See @armpuzzle).

A regular player can collect the puzzle parts and combine
them (See use command). If player has specified
all pieces, the puzzle is considered solved and all
its puzzle parts are destroyed while the puzzle results
are spawened on their corresponding location.

Installation:

Add the PuzzleSystemCmdSet to all players.
Alternatively:

    @py self.cmdset.add('evennia.contrib.puzzles.PuzzleSystemCmdSet')

"""

import itertools
from random import choice
from evennia import create_object, create_script
from evennia import CmdSet
from evennia import DefaultObject
from evennia import DefaultScript
from evennia import DefaultCharacter
from evennia import DefaultRoom
from evennia.commands.default.muxcommand import MuxCommand
from evennia.utils.utils import inherits_from
from evennia.utils import search, utils, logger
from evennia.utils.spawner import spawn

# Tag used by puzzles
_PUZZLES_TAG_CATEGORY = 'puzzles'
_PUZZLES_TAG_RECIPE = 'puzzle_recipe'
# puzzle part and puzzle result
_PUZZLES_TAG_MEMBER = 'puzzle_member'

# ----------- UTILITY FUNCTIONS ------------

def proto_def(obj, with_tags=True):
    """
    Basic properties needed to spawn
    and compare recipe with candidate part
    """
    protodef = {
        # FIXME: Don't we need to honor ALL properties? locks, perms, etc.
        'key': obj.key,
        'typeclass': 'evennia.contrib.puzzles.PuzzlePartObject',  # FIXME: what if obj is another typeclass
        'desc': obj.db.desc,
        'location': obj.location,
        # FIXME: Can tags be INVISIBLE? We don't want player to know an object belongs to a puzzle
        'tags': [(_PUZZLES_TAG_MEMBER, _PUZZLES_TAG_CATEGORY)],
    }
    if not with_tags:
        del(protodef['tags'])
    return protodef

# ------------------------------------------

class PuzzlePartObject(DefaultObject):
    """
    Puzzle Part, typically used by @armpuzzle command
    """

    def mark_as_puzzle_member(self, puzzle_name):
        """
        Marks this object as a member of puzzle named
        puzzle_name
        """
        # FIXME: if multiple puzzles have the same
        # puzzle_name, their ingredients may be
        # combined but leave other parts orphan
        # Similarly, if a puzzle_name were changed,
        # its parts will become orphan
        # Perhaps we should use #dbref but that will
        # force specific parts to be combined
        self.db.puzzle_name = puzzle_name


class PuzzleRecipe(DefaultScript):
    """
    Definition of a Puzzle Recipe
    """

    def save_recipe(self, puzzle_name, parts, results):
        self.db.puzzle_name = puzzle_name
        self.db.parts = tuple(parts)
        self.db.results = tuple(results)
        self.tags.add(_PUZZLES_TAG_RECIPE, category=_PUZZLES_TAG_CATEGORY)


class CmdCreatePuzzleRecipe(MuxCommand):
    """
    Creates a puzzle recipe.

    Each part and result must exist and be placed in their corresponding location.
    All parts and results are left intact. Caller must explicitly
    destroy them.

    Usage:
        @puzzle name,<part1[,part2,...>] = <result1[,result2,...]>
    """

    key = '@puzzle'
    aliases = '@puzzlerecipe'
    locks = 'cmd:perm(puzzle) or perm(Builder)'
    help_category = 'Puzzles'

    def func(self):
        caller = self.caller

        if len(self.lhslist) < 2 \
            or not self.rhs:
            string = "Usage: @puzzle name,<part1[,...]> = <result1[,...]>"
            caller.msg(string)
            return

        puzzle_name = self.lhslist[0]
        if len(puzzle_name) == 0:
            caller.msg('Invalid puzzle name %r.' % puzzle_name)
            return

        def is_valid_obj_location(obj):
            valid = True
            # Valid locations are: room, ...
            # TODO: other valid locations must be added here
            # Certain locations can be handled accordingly: e.g,
            # a part is located in a character's inventory,
            # perhaps will translate into the player character
            # having the part in his/her inventory while being
            # located in the same room where the builder was
            # located.
            # Parts and results may have different valid locations
            # TODO: handle contents of a given part
            if not inherits_from(obj.location, DefaultRoom):
                caller.msg('Invalid location for %s' % (obj.key))
                valid = False
            return valid

        def is_valid_part_location(part):
            return is_valid_obj_location(part)

        def is_valid_result_location(part):
            return is_valid_obj_location(part)

        parts = []
        for objname in self.lhslist[1:]:
            obj = caller.search(objname)
            if not obj:
                return
            if not is_valid_part_location(obj):
                return
            parts.append(obj)

        results = []
        for objname in self.rhslist:
            obj = caller.search(objname)
            if not obj:
                return
            if not is_valid_result_location(obj):
                return
            results.append(obj)

        for part in parts:
            caller.msg('Part %s(%s)' % (part.name, part.dbref))

        for result in results:
            caller.msg('Result %s(%s)' % (result.name, result.dbref))

        proto_parts = [proto_def(obj) for obj in parts]
        proto_results = [proto_def(obj) for obj in results]

        puzzle = create_script(PuzzleRecipe, key=puzzle_name)
        puzzle.save_recipe(puzzle_name, proto_parts, proto_results)

        caller.msg(
            "Puzzle |y'%s' |w%s(%s)|n has been created |gsuccessfully|n."
            % (puzzle.db.puzzle_name, puzzle.name, puzzle.dbref))
        caller.msg(
            'You may now dispose all parts and results. '
            'Typically, results and parts are useless afterwards.\n'
            'You are now able to arm this puzzle using Builder command:\n'
            '    @armpuzzle <puzzle #dbref>\n\n'
            'Or programmatically.\n'
        )

        # FIXME: puzzle recipe object exists but it has no location
        # should we create a PuzzleLibrary where all puzzles are
        # kept and cannot be reached by players?


class CmdArmPuzzle(MuxCommand):
    """
    Arms a puzzle by spawning all its parts
    """

    key = '@armpuzzle'
    # FIXME: permissions for scripts?
    locks = 'cmd:perm(armpuzzle) or perm(Builder)'
    help_category = 'Puzzles'

    def func(self):
        caller = self.caller

        if self.args is None or not utils.dbref(self.args):
            caller.msg("A puzzle recipe's #dbref must be specified")
            return

        puzzle = search.search_script(self.args)
        if not puzzle or not inherits_from(puzzle[0], PuzzleRecipe):
            caller.msg('Invalid puzzle %r'  % (self.args))
            return

        puzzle = puzzle[0]
        caller.msg(
            "Puzzle Recipe %s(%s) '%s' found.\nSpawning %d parts ..." % (
            puzzle.name, puzzle.dbref, puzzle.db.puzzle_name, len(puzzle.db.parts)))

        for proto_part in puzzle.db.parts:
            part = spawn(proto_part)[0]
            caller.msg("Part %s(%s) spawned and placed at %s(%s)" % (part.name, part.dbref, part.location, part.location.dbref))
            part.mark_as_puzzle_member(puzzle.db.puzzle_name)

        caller.msg("Puzzle armed |gsuccessfully|n.")


class CmdUsePuzzleParts(MuxCommand):
    """
    Searches for all puzzles whose parts
    match the given set of objects. If
    there are matching puzzles, the result
    objects are spawned in their corresponding
    location if all parts have been passed in.

    Usage:
        use <part1[,part2,...>]
    """

    # TODO: consider allowing builder to provide
    # messages and "hooks" that can be displayed
    # and/or fired whenever the resolver of the puzzle
    # enters the location where a result was spawned

    key = 'use'
    aliases = 'combine'
    locks = 'cmd:pperm(use) or pperm(Player)'
    help_category = 'Puzzles'

    def func(self):
        caller = self.caller

        if not self.lhs:
            caller.msg('Use what?')
            return

        many = 'these' if len(self.lhslist) > 1 else 'this'

        # either all are parts, or abort finding matching puzzles
        parts = []
        partnames = self.lhslist[:]
        for partname in partnames:
            part = caller.search(
                partname,
                multimatch_string='Which %s. There are many.\n' % (partname),
                nofound_string='There is no %s around.' % (partname)
            )

            if not part:
                return

            if not part.tags.get(_PUZZLES_TAG_MEMBER, category=_PUZZLES_TAG_CATEGORY) \
                or not inherits_from(part, PuzzlePartObject):

                # not a puzzle part ... abort
                caller.msg('You have no idea how %s can be used' % (many))
                return

            # a valid part
            parts.append(part)

        # Create lookup dict
        parts_dict = dict((part.dbref, part) for part in parts)

        # Group parts by their puzzle name
        puzzle_ingredients = dict()
        for part in parts:
            puzzle_name = part.db.puzzle_name
            if puzzle_name not in puzzle_ingredients:
                puzzle_ingredients[puzzle_name] = []
            puzzle_ingredients[puzzle_name].append(
                (part.dbref, proto_def(part, with_tags=False))
            )


        # Find all puzzles by puzzle name
        # FIXME: we rely on obj.db.puzzle_name which is visible and may be cnaged afterwards. Can we lock it and hide it?
        puzzles = []
        for puzzle_name, parts in puzzle_ingredients.items():
            _puzzles = search.search_script_attribute(
                    key='puzzle_name',
                    value=puzzle_name
            )
            _puzzles = list(filter(lambda p: isinstance(p, PuzzleRecipe), _puzzles))
            if not _puzzles:
                continue
            else:
                puzzles.extend(_puzzles)

        logger.log_info("PUZZLES %r" % ([p.dbref for p in puzzles]))

        # Create lookup dict
        puzzles_dict = dict((puzzle.dbref, puzzle) for puzzle in puzzles)
        # Check if parts can be combined to solve a puzzle
        matched_puzzles = dict()
        for puzzle in puzzles:
            puzzleparts = list(sorted(puzzle.db.parts[:], key=lambda p: p['key']))
            parts = list(sorted(puzzle_ingredients[puzzle.db.puzzle_name][:], key=lambda p: p[1]['key']))
            pz = 0
            p = 0
            matched_dbrefparts = set()
            while pz < len(puzzleparts) and p < len(parts):
                puzzlepart = puzzleparts[pz]
                if 'tags' in puzzlepart:
                    # remove 'tags' as they will prevent equality
                    del(puzzlepart['tags'])
                dbref, part = parts[p]
                if part == puzzlepart:
                    pz += 1
                    matched_dbrefparts.add(dbref)
                p += 1
            else:
                if len(puzzleparts) == len(matched_dbrefparts):
                    matched_puzzles[puzzle.dbref] = matched_dbrefparts

        if len(matched_puzzles) == 0:
            # FIXME: Add more random messages
            #    random part falls and lands on your feet
            #    random part hits you square on the face
            caller.msg("As you try to utilize %s, nothing happens." % (many))
            return

        puzzletuples = sorted(matched_puzzles.items(), key=lambda t: len(t[1]), reverse=True)

        logger.log_info("MATCHED PUZZLES %r" % (puzzletuples))

        # sort all matched puzzles and pick largest one(s)
        puzzledbref, matched_dbrefparts = puzzletuples[0]
        nparts = len(matched_dbrefparts)
        puzzle = puzzles_dict[puzzledbref]
        largest_puzzles = list(itertools.takewhile(lambda t: len(t[1]) == nparts, puzzletuples))

        # if there are more than one, ...
        if len(largest_puzzles) > 1:
            # FIXME: pick a random one or let user choose?
            # FIXME: do we show the puzzle name or something else?
            caller.msg(
                'Your gears start turning and a bunch of ideas come to your mind ...\n%s' % (
                ' ...\n'.join([puzzles_dict[lp[0]].db.puzzle_name for lp in largest_puzzles]))
            )
            puzzletuple = choice(largest_puzzles)
            puzzle = puzzles_dict[puzzletuple[0]]
            caller.msg("You try %s ..." % (puzzle.db.puzzle_name))

        # got one, spawn its results
        # FIXME: DRY with parts
        result_names = []
        for proto_result in puzzle.db.results:
            result = spawn(proto_result)[0]
            result.mark_as_puzzle_member(puzzle.db.puzzle_name)
            result_names.append(result.name)
            # FIXME: add 'ramdon' messages:
            # Hmmm ... did I search result.location?
            # What was that? ... I heard something in result.location?
            # Eureka! you built a result

        # Destroy all parts used
        for dbref in matched_dbrefparts:
            parts_dict[dbref].delete()

        # FIXME: Add random messages
        #    You are a genius ... no matter what your 2nd grade teacher told you
        #    You hear thunders and a cloud of dust raises leaving
        result_names = ', '.join(result_names)
        caller.msg(
            "You are a |wG|re|wn|ri|wu|rs|n!!!\nYou just created %s" % (
            result_names
        ))
        caller.location.msg_contents(
            "|c%s|n performs some kind of tribal dance"
            " and seems to create |y%s|n from thin air" % (
            caller, result_names), exclude=(caller,)
        )


class CmdListPuzzleRecipes(MuxCommand):
    """
    Searches for all puzzle recipes

    Usage:
        @lspuzzlerecipes
    """

    key = '@lspuzzlerecipes'
    locks = 'cmd:perm(lspuzzlerecipes) or perm(Builder)'
    help_category = 'Puzzles'

    def func(self):
        caller = self.caller

        recipes = search.search_script_tag(
            _PUZZLES_TAG_RECIPE, category=_PUZZLES_TAG_CATEGORY)

        div = "-" * 60
        text = [div]
        msgf_recipe = "Puzzle |y'%s' %s(%s)|n"
        msgf_item = "%2s|c%15s|n: |w%s|n"
        for recipe in recipes:
            text.append(msgf_recipe % (recipe.db.puzzle_name, recipe.name, recipe.dbref))
            text.append('Parts')
            for protopart in recipe.db.parts[:]:
                mark = '-'
                for k, v in protopart.items():
                    text.append(msgf_item % (mark, k, v))
                    mark = ''
            text.append('Results')
            for protoresult in recipe.db.results[:]:
                mark = '-'
                for k, v in protoresult.items():
                    text.append(msgf_item % (mark, k, v))
                    mark = ''
            text.append(div)
        caller.msg('\n'.join(text))


class CmdListArmedPuzzles(MuxCommand):
    """
    Searches for all armed puzzles

    Usage:
        @lsarmedpuzzles
    """

    key = '@lsarmedpuzzles'
    locks = 'cmd:perm(lsarmedpuzzles) or perm(Builder)'
    help_category = 'Puzzles'

    def func(self):
        caller = self.caller

        armed_puzzles = search.search_tag(
            _PUZZLES_TAG_MEMBER, category=_PUZZLES_TAG_CATEGORY)

        armed_puzzles = dict((k, list(g)) for k, g in itertools.groupby(
            armed_puzzles,
            lambda ap: ap.db.puzzle_name))

        div = '-' * 60
        msgf_pznm = "Puzzle name: |y%s|n"
        msgf_item = "|m%25s|w(%s)|n at |c%25s|w(%s)|n"
        text = [div]
        for pzname, items in armed_puzzles.items():
            text.append(msgf_pznm % (pzname))
            for item in items:
                text.append(msgf_item % (
                    item.name, item.dbref,
                    item.location.name, item.location.dbref))
            text.append(div)
        caller.msg('\n'.join(text))


class PuzzleSystemCmdSet(CmdSet):
    """
    CmdSet to create, arm and resolve Puzzles

    Add with @py self.cmdset.add("evennia.contrib.puzzles.PuzzlesCmdSet")
    """

    def at_cmdset_creation(self):
        super(PuzzleSystemCmdSet, self).at_cmdset_creation()

        self.add(CmdCreatePuzzleRecipe())
        self.add(CmdArmPuzzle())
        self.add(CmdListPuzzleRecipes())
        self.add(CmdListArmedPuzzles())
        self.add(CmdUsePuzzleParts())
