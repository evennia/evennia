"""
Commands for the aisystem. They allow for navigating, studying and
modifying behavior trees.
"""
import re
import string
from ast import literal_eval
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from evennia import CmdSet, PlayerDB, ObjectDB, ScriptDB, create_script
from evennia.utils import evmore
from evennia.utils.dbserialize import _SaverList, _SaverDict
from evennia.commands.command import Command

from evennia.contrib.aisystem.typeclasses import (BehaviorTree, 
    AIObject, AIScript, AIPlayer)
from evennia.contrib.aisystem.nodes import CompositeNode
from evennia.contrib.aisystem.utils import (setup, recursive_clear_watchlists,
    is_aiplayer, is_browsing, is_browsing_blackboard, get_all_agents_with_tree,
    player_from_name, tree_from_name, node_from_name, agent_from_name)
from evennia.contrib.aisystem.commands_build import AIBuildCmdSet
from evennia.contrib.aisystem.commands_view import AIViewCmdSet

#[WIP] TAKE NODES OUT OF ALL WATCH LISTS WHEN REMOVING THEM OR THEIR (IN)DIRECT
#      PARENTS!
#[WIP] Ensure everything is saved

class AICmdSet(CmdSet):
    """CmdSet for action-related commands."""
    key = "ai_cmdset"
    priority = -20

    def at_cmdset_creation(self):
        self.add(CmdSetup())
        self.add(CmdNewTree())
        self.add(CmdCloneTree())
        self.add(CmdRenameTree())
        self.add(CmdDelTree())
        self.add(CmdAssign())
        self.add(AIBuildCmdSet())
        self.add(AIViewCmdSet())


class CmdSetup(Command):
    """
    Sets up the AI-related database attributes of AIPlayer, AIObject and
    AIScript instances in the database. This must happen before these instances
    can make use of the AI system.

    When no argument or the override argument is provided, all AIPlayer, 
    AIObject and AIScript instances are affected.

    When the argument "player" (without quotes) followed by an AIPlayer's name 
    or id is provided, that player's AI builder data will be set up.

    When the argument "object" or "script" (without quotes) followed by an
    AIObject or AIScript's name or id is provided, that object or script's
    AI blackboard will be set up.

    When the argument "tree" (without quotes) followed by a BehaviorTree's name
    or id is provided, the AI blackboards of all agents that start their AI
    computations from the root of that tree will be set up.

    Whenever the override argument is provided, all attributes that were 
    previously set up are reset to the defaults.

    Instead of a name or id, the 'this' keyword may be provided to refer to
    the player using this command, the currently browsed blackboard or the
    currently browsed tree.

    The argument "player", "object", "script" or "tree" should proceed any other
    arguments. The argument "override" should follow all other arguments.

    The names / ids of players, objects, scripts and trees |w*must*|n be 
    enclosed in single quotes.

    Usage:
        @aisetup
        @aisetup override
        @aisetup player '<player name>'
        @aisetup player '<player name>' override
        @aisetup <object|script> '<agent name>'
        @aisetup <object|script> '<agent name>' override
        @aisetup tree '<tree name>'
        @aisetup tree '<tree name>' override

    Examples:
        @aisetup override
        @aisetup player 'John'
        @aisetup player '8'
        @aisetup object 'shambling horror'
        @aisetup script 'dark army strategy' override
        @aisetup script '215'
        @aisetup tree 'Fighter AI'
        @aisetup tree '24' override
    """
    key = "@aisetup"
    aliases = []
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        args = re.findall(r"(?:\b\w+\b)|(?:'[^']*')", self.args)

        override = False
        if len(args) != 0:
            override = args[-1] == "override"
        msg_act = "overridden" if override else "set up"

        if len(args) == 0 or (len(args) == 1 and override):
            setup(override=override)
            self.caller.msg("AI system database entries {0}.".format(msg_act))
            return True

        elif len(args) == 1:
            self.caller.msg("You have specified a single argument to " +
                "the @aisetup command, but that argument is not " +
                "\"override\" (without the quotes). Cannot perform setup.")
            return False

        elif not (len(args) == 2 or (len(args) == 3 and override)):
            self.caller.msg("Invalid combination of arguments for the " +
                "@aisetup command.")
            return False

        # We are dealing with two arguments or three arguments of which the
        # final one is override.

        obj_type_name = args[0]
        name = args[1][1:-1]

        if obj_type_name == "player":
            player = player_from_name(self.caller, name)
            if not player:
                return False

            player.aiwizard.setup(override=override)
            self.caller.msg("Player {0} (id {1}) ".format(player.name, 
                player.id) + "successfully {0}.".format(msg_act))

        elif obj_type_name == "object" or obj_type_name == "script":
            obj_type = AIObject if obj_type_name == "object" else AIScript
            agent = agent_from_name(self.caller, obj_type, name)
            if not agent:
                return False

            err = agent.ai.setup(override=override)
            if err:
                self.caller.msg(err)
                return False
            self.caller.msg("{0} '{1}' (id {2}) ".format(
                obj_type_name.capitalize(), agent.name, agent.id) +
                "successfully {0}.".format(msg_act))

        elif obj_type_name == "tree":
            tree = tree_from_name(self.caller, name)
            if not tree:
                return False

            agents = get_all_agents_with_tree(tree)
            for agent in agents:
                err = agent.ai.setup(override=override)
                if err:
                    self.caller.msg(err)
                    return False
            self.caller.msg("A total of |c{0}|n agents ".format(len(agents)) +
                "using tree {0} (id {1}) have ".format(tree.name, tree.id) +
                "been successfully {0}.".format(msg_act))
        else:
            self.caller.msg("Invalid object type. You specified " +
                "{0}, but the only acceptable options ".format(args[0]) +
                "are \"player\", \"object\", \"script\" and \"tree\" " +
                "(without the single quotes).")
            return False

        return True


class CmdNewTree(Command):
    """
    Generates a new tree with the given name. The name must not contain
    single quotes (the ' symbol).

    Usage:
        @ainewtree <tree name>

    Example:
        @ainewtree Fighter AI

    See also:
        @airenametree @aideltree
    """
    key = "@ainewtree"
    aliases = []
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        # check that a name has been provided
        name = self.args.strip()
        if not name:
            self.caller.msg("Please provide a name for the new tree.")
            return False

        if "'" in name:
            self.caller.msg("Please provide a name that does not contain " +
                "single quotes.")
            return False

        # check that the tree's name does not have the format of a database id
        if all([x in string.digits for x in name]):
            self.caller.msg("The name you provided is made entirely of " +
                "digits. You must supply a name that contains other types " +
                "of characters as well.")
            return False

        # check that a tree with the same name does not already exist
        tree_exists = True if [x for x in ScriptDB.objects.all() 
            if x.name == name] else False
        if tree_exists:
            self.caller.msg("A script with the name {0} has ".format(name) +
                "already been found. Cannot create a new tree with the " +
                "same name.")
            return False

        # create the new tree
        tree = create_script(BehaviorTree, key=name)
        self.caller.msg("Tree \"{0}\" with database id  ".format(name) +
            "{0} created.".format(tree.id))
        return True


class CmdCloneTree(Command):
    """
    Copies a given tree. To identify the tree, its original name or its
    database id must be specified. If the original name specified for the
    tree is 'this', the tree to be copied is considered to be the currently
    browsed tree.

    The <tree name> and <new tree name> |w*must*|n be enclosed in single 
    quotes.

    Usage:
        @aiclonetree '<original tree name>' '<new tree name>'

    Example:
        @aiclonetree 'fighter AI' 'warrior AI'
        @aiclonetree '216' 'warrior AI'
        @aiclonetree 'this' 'warrior AI'
    """
    key = "@aiclonetree"
    aliases = []
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        if not is_aiplayer(self.caller):
            return False

        # check that the original name and the new name have been provided
        names = re.findall(r"'[^']*'", self.args)
        if len(names) == 0:
            self.caller.msg("You have provided no names. You must " +
                "provide the name of the tree to be copied as well as the " +
                "name of the copy, both enclosed in single quotes (the ' " +
                "symbol).")
            return False
        elif len(names) == 1:
            self.caller.msg("You have provided only one name. You must " +
                "provide the name of the tree to be copied as well as the " +
                "name of the copy, both enclosed in single quotes (the ' " +
                "symbol).")
            return False
            
        # strip the names of their single quotes
        old_name = names[0][1:-1]
        new_name = names[1][1:-1]

        old_tree = tree_from_name(self.caller, old_name)
        if not old_tree:
            return False

        # generate the new behavior tree.
        new_tree = create_script(BehaviorTree, key=new_name)
        new_tree.root = old_tree.root
        new_tree.nodes = old_tree.nodes
        
        # Ensure that the hashes of all nodes are updated to include the
        # new tree's id as opposed to the old one's
        new_tree.recursive_add_hash(new_tree.nodes[new_tree.root])
        new_tree.nodes = new_tree.nodes # save tree

        self.caller.msg("Tree '{0}' (id {1}) ".format(new_name, new_tree.id) +
            "successfully copied from '{0}'.".format(old_name))
        return True


class CmdRenameTree(Command):
    """
    Renames a given tree. To identify the tree, its original name or its
    database id must be specified. If the original name specified for the
    tree is 'this', the tree to be renamed is considered to be the currently
    browsed tree.

    The <tree name> and <new tree name> |w*must*|n be enclosed in single 
    quotes.

    Usage:
        @airenametree '<original tree name>' '<new tree name>'

    Example:
        @airenametree 'fighter AI' 'warrior AI'
        @airenametree '216' 'warrior AI'
        @airenametree 'this' 'warrior AI'

    See also:
        @ainewtree @aideltree
    """
    key = "@airenametree"
    aliases = []
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        if not is_aiplayer(self.caller):
            return False

        # check that the original name and the new name have been provided
        names = re.findall(r"'[^']*'", self.args)
        if len(names) == 0:
            self.caller.msg("You have provided no names. You must provide " +
                "the original name of the tree as well as its new name, " +
                "both enclosed in single quotes (the ' symbol).")
            return False
        elif len(names) == 1:
            self.caller.msg("You have provided only one name. You must " +
                "provide the original name of the tree as well as its new " +
                "name, both enclosed in single quotes (the ' symbol).")
            return False
            
        # strip the names of their single quotes
        old_name = names[0][1:-1]
        new_name = names[1][1:-1]

        tree = tree_from_name(self.caller, old_name)
        if not tree:
            return False

        # give the tree the new name.
        tree.key = new_name
        self.caller.msg("Tree '{0}' (id {1}) ".format(old_name, tree.id) +
            "successfully renamed to '{0}'.".format(new_name))
        return True


class CmdDelTree(Command):
    """
    Delete a given tree completely, removing it from the database. You may
    specify the tree via its name, its database id or the keyword 'this'. If
    the specified tree name is 'this', the currently browsed tree will be
    deleted.

    Deleting a tree will also clear the blackboards of all AI agents that have
    been using it.

    Usage:
        @aideltree <tree name>

    Examples:
        @aideltree fighter AI
        @aideltree 47
        @aideltree this

    The <tree name> must |rnot|n be enclosed in single quotes.

    See also:
        @ainewtree @airenametree
    """
    key = "@aideltree"
    aliases = []
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        if not is_aiplayer(self.caller):
            return False

        name = self.args.strip()
        if not name:
            self.caller.msg("Please specify the name of the tree to be " +
                "deleted.")
            return False

        if "'" in name:
            self.caller.msg("Please specify a name that does not contain " +
                "single quotes.")
            return False

        tree = tree_from_name(self.caller, name)
        if not tree:
            return False

        if self.caller.player.aiwizard.tree == tree:
            self.caller.player.aiwizard.tree = None
            self.caller.player.aiwizard.node = ''

        # Take the tree's nodes out of every watch list
        objects = [x for x in ObjectDB.objects.all()
            if isinstance(x, AIObject) and x.db.ai['tree'] == tree]
        scripts = [x for x in ScriptDB.objects.all()
            if isinstance(x, AIScript) and x.db.ai['tree'] == tree]

        for obj in objects:
            recursive_clear_watchlists(tree.nodes[tree.root], obj.db.ai)
            obj.db.ai = {} # clear the blackboard
        for script in scripts:
            recursive_clear_watchlists(tree.nodes[tree.root], script.db.ai)
            script.db.ai = {} # clear the blackboard

        # Clear the blackboards of all agents that were using the tree
        agents = get_all_agents_with_tree(tree)
        for agent in agents:
            agent.db.ai = {}

        self.caller.msg("Tree '{0}'(\"{1}\") deleted. ".format(tree.id,
            tree.name) + "A total of |c{0}|n agents now ".format(len(agents)) +
            "have no tree and no blackboard.")

        agent = self.caller.player.aiwizard.agent
        if (agent and agent.db.ai.has_key('tree') 
            and agent.db.ai['tree'] == tree):
            self.caller.player.aiwizard.agent = None
            obj_type = "object" if isinstance(agent, AIObject) else "agent"
            self.caller.msg("You are no longer browsing the blackboard of " +
                "{0} '{1}' (id {2}) ".format(obj_type, agent.name, agent.id) +
                "as its origin tree was deleted.")

        tree.delete()
        return True


class CmdAssign(Command):
    """
    Assign a given tree to a given AIObject or AIScript if you specify that
    AI agent's type ("object" or "script", without quotes) and either its name 
    or its id, or to all the agents currently using another given tree if you
    specify that tree. You can use the 'this' keyword instead of a name or id
    to refer to the currently browsed tree or blackboard. 

    All names, ids and the 'this' keyword |w*must*|n be enclosed in single 
    quotes (the ' symbol).

    Usage:
        @aiassign <old tree name> <new tree name>
        @aiassign <new tree name> <object|script> <id or name of object/script>

    Examples:
        @aiassign 'fighter AI' object '13'
        @aiassign '82' object 'big orc masher'
        @aiassign 'strategy AI' script 'the orcs'
        @aiassign 'this' script '235'

    See also:
        @aiset
    """
    key = "@aiassign"
    aliases = []
    locks = "cmd:perm(Wizards)"
    arg_regex = r"\s.+|$"
    help_category = "AI"

    def func(self):
        if not is_aiplayer(self.caller):

            return False

        names = re.findall(r"(?:\b\w+\b)|(?:'[^']*')", self.args)
        source_tree = None

        n_names = len(names)
        if n_names < 2:
            self.caller.msg("@aiassign requires at least two arguments. " +
                "You have input {0}. Consult the helpfile ".format(n_names) +
                "for more information.")
            return False
        elif n_names > 3:
            self.caller.msg("@aiassign requires at most three arguments. " +
                "You have input {0}. Consult the helpfile ".format(n_names) +
                "for more information.")
            return False

        if names[1] == 'object':
            obj_type = AIObject
            obj_type_name = 'object'
        elif names[1] == 'script':
            obj_type = AIScript
            obj_type_name = 'script'
        else:
            source_tree = tree_from_name(self.caller, names[0][1:-1])
            if not source_tree:
                return False

        if source_tree:
            target_tree = tree_from_name(self.caller, names[1][1:-1])
            if not target_tree:
                return False

            agents = get_all_agents_with_tree(source_tree)
            for agent in agents:
                agent.ai.setup(tree=target_tree, override=True)
                
            self.caller.msg("assigned the tree '{0}' (id {1}) ".format(
                source_tree.name, source_tree.id) + "to a total of " +
                "|c{0}|n agents that were using tree ".format(len(agents)) +
                "'{0}' (id {1}).".format(target_tree.name, target_tree.id))

        else:
            target_tree = tree_from_name(self.caller, names[0][1:-1])
            if not target_tree:
                return False

            agent = agent_from_name(self.caller, obj_type, names[1][1:-1])
            if not agent:
                return False
            
            agent.ai.setup(tree=target_tree, overide=True)
            self.caller.msg("Assigned the tree '{0}' (id {1}) ".format(
                target_tree.name, target_tree.id) + "to {0} '{1}' ".format(
                obj_type_name, agent.name) + "(id {0})".format(agent.id))
        return True


