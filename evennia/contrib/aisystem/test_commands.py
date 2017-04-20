"""
Tests for the tree-related commands in the aisystem.
"""
from evennia import ObjectDB, ScriptDB
from evennia.utils import create
from evennia.commands.default.tests import CommandTest
import evennia.contrib.aisystem.commands as commands
import evennia.contrib.aisystem.commands_view as commands_view
import evennia.contrib.aisystem.commands_build as commands_build
from evennia.contrib.aisystem.nodes import (
    SUCCESS, CompositeNode, Succeeder, DecoratorNode, LeafNode)
from evennia.contrib.aisystem.typeclasses import (
    AIPlayer, AIObject, AIScript, BehaviorTree)

# in commands_view, test that is_browsing, is_browsing_blackboard,
# tree_from_name(name | id | 'this'), node_from_name(name | hash) and
# agent_from_name(name | id | 'this') work as intended and fail gracefully


def tree_list_is_empty():
    tree_list = [
        x for x in ScriptDB.objects.all() if isinstance(x, BehaviorTree)]
    return not tree_list


def n_trees_in_list(n):
     tree_list = [
        x for x in ScriptDB.objects.all() if isinstance(x, BehaviorTree)]
     return len(tree_list) == n


def tree_in_list(tree_name):
    tree_list = [
        x for x in ScriptDB.objects.all() if isinstance(x, BehaviorTree)
        if x.name == tree_name]
    return True if tree_list else False


def tree_assigned(tree, agent):
    if (agent.db.ai and agent.db.ai.has_key("tree") and 
            agent.db.ai['tree'] == tree):
        return True
    else:
        return False


def nothing_set_up(test_case):
    p1 = (test_case.player.db.aiwizard['tree'] or 
          test_case.player.db.aiwizard['node'] or
          test_case.player.db.aiwizard['agent'])
    p2 = (test_case.player2.db.aiwizard['tree'] or 
          test_case.player2.db.aiwizard['node'] or
          test_case.player2.db.aiwizard['agent'])
    o1 = test_case.obj1.db.ai
    o2 = test_case.obj2.db.ai
    s = test_case.script.db.ai
    return not (p1 or p2 or o1 or o2 or s)


def is_set_up(agent):
    return (agent.attributes.has("ai") and agent.db.ai)


class TestTreeCommands(CommandTest):
    """
    Tests the @aisetup, @ainewtree, @aiclonetree, @airenametree, @aideltree
    and @aiassign commands.
    """

    player_typeclass = AIPlayer
    object_typeclass = AIObject
    script_typeclass = AIScript

    def test_setup(self):
        """
        Tests the @aisetup command
        """
        # check for failure when providing one argument that is not override.
        self.call(commands.CmdNewTree(), "tree")
        tree = ScriptDB.objects.get(db_key="tree")
        leaf = LeafNode("leaf", tree, tree.nodes[tree.root])
        assert(nothing_set_up(self))

        # check for failure when providing three arguments of which
        # the last one is not override
        self.call(commands.CmdSetup(), "")
        assert(nothing_set_up(self))

        # check for failure when providing a first argument that is not
        # player, object, script, tree or override
        self.call(commands.CmdSetup(), "invalid")
        self.call(commands.CmdSetup(), "'invalid'")
        assert(nothing_set_up(self))

        # check for failure when setting up an object without a default tree
        self.call(commands.CmdSetup(), "object 'Obj'")
        assert(nothing_set_up(self))

        # check for failure when setting up a script without a default tree
        self.call(commands.CmdSetup(), "script 'Script'")
        assert(nothing_set_up(self))

        # check for success when setting up a player
        self.player.tree = tree
        self.player.node = tree.root
        self.player.agent = self.obj1
        self.call(commands.CmdSetup(), "player 'TestPlayer' override")
        assert(nothing_set_up(self))

        # check for success when setting up an object with a tree
        self.obj1.aitree = tree
        assert(not is_set_up(self.obj1))
        self.call(commands.CmdSetup(), "object 'Obj'")
        assert(is_set_up(self.obj1))

        # check for success when setting up a script with a tree
        self.script.aitree = tree
        assert(not is_set_up(self.script))
        self.call(commands.CmdSetup(), "script 'Script'")
        assert(is_set_up(self.script))

        # check for success when setting up everything
        self.obj2.aitree = tree
        assert(not is_set_up(self.obj2))
        self.call(commands.CmdSetup(), "")
        assert(is_set_up(self.obj2))

        # check for success when setting up two objects via the tree argument
        self.obj1.db.ai['nodes'][tree.root]['test'] = 1
        self.obj2.db.ai['nodes'][tree.root]['test'] = 1
        self.call(commands.CmdSetup(), "tree 'tree' override")
        assert(not self.obj1.db.ai['nodes'][tree.root].has_key("test"))
        assert(not self.obj2.db.ai['nodes'][tree.root].has_key("test"))

    def test_new_tree(self):
        """
        Test the @ainewtree command
        """
        assert(tree_list_is_empty())

        # check for failure when not providing a name
        self.call(commands.CmdNewTree(), "")
        assert(tree_list_is_empty())

        # check for failure when putting single quotes in the name
        self.call(commands.CmdNewTree(), "'te'st'i''ng")      
        assert(tree_list_is_empty())

        # check for failure when giving a name composed entirely of digits
        self.call(commands.CmdNewTree(), "123")
        assert(tree_list_is_empty())

        # check for failure when using the name of an already existent script
        self.call(commands.CmdNewTree(), "Script")
        assert(tree_list_is_empty())

        self.call(commands.CmdNewTree(), "New tree")
        assert(tree_in_list("New tree"))

    def test_clone_tree(self):
        """
        Test the @aiclonetree command
        """
        self.call(commands.CmdNewTree(), "old")
        tree = ScriptDB.objects.get(db_key="old")        
        assert(n_trees_in_list(1))

        # add nodes to the tree
        dec = DecoratorNode('dec', tree, tree.nodes[tree.root])
        leaf = LeafNode('leaf', tree, dec)
        assert(len(tree.nodes.keys()) == 3)

        # check for failure when not providing a name for the new tree
        self.call(commands.CmdCloneTree(), "")
        assert(n_trees_in_list(1))

        # check for failure when providing more than 2 arguments
        self.call(commands.CmdCloneTree(), "'old' 'new' 'spurious argument'")
        assert(n_trees_in_list(1))

        # check for failure when providing one argument and not browsing
        self.call(commands.CmdCloneTree(), "'new'")
        assert(n_trees_in_list(1))

        # check for success when providing one argument and browsing
        self.char1.player.aiwizard.tree = tree
        self.char1.player.aiwizard.node = tree.root


        self.call(commands.CmdCloneTree(), "'new'")
        assert(n_trees_in_list(2))
        assert(tree_in_list("new"))
        tree2 = ScriptDB.objects.get(db_key="new")
        assert(len(tree2.nodes.keys()) == 3)

        tree2.delete()
        assert(n_trees_in_list(1))

        # check for success when providing two arguments regardless of browsing
        self.char1.player.aiwizard.tree = None
        self.char1.player.aiwizard.node = None

        assert(ScriptDB.objects.get(db_key="old") == tree)
        #print("tree list post-clone:", [
        #    x.name for x in ScriptDB.objects.all()
        #    if isinstance(x, BehaviorTree)])

        self.call(commands.CmdCloneTree(), "'old' 'new'")
        assert(n_trees_in_list(2))
        assert(tree_in_list("new"))
        tree2 = ScriptDB.objects.get(db_key="new")
        assert(len(tree2.nodes.keys()) == 3)

    def test_rename_tree(self):
        """
        Test the @airenametree command
        """
        self.call(commands.CmdNewTree(), "old")
        tree = ScriptDB.objects.get(db_key="old")

        # check for failure when not providing a name for the new tree
        self.call(commands.CmdRenameTree(), "")
        assert(tree.name == "old")

        # Check for failure when providing a single argument and not browsing
        self.call(commands.CmdRenameTree(), "'new'")
        assert(tree.name == "old")

        # check for failure when providing more than 2 arguments
        self.call(commands.CmdRenameTree(), "'old' 'new' 'spurious argument'")
        assert(tree.name == "old")

        # check for success when providing a single argument after browsing
        self.char1.player.aiwizard.tree = tree
        self.char1.player.aiwizard.node = tree.root

        self.call(commands.CmdRenameTree(), "'new'")
        assert(tree.name == "new")
        self.call(commands.CmdRenameTree(), "'old'")
        assert(tree.name == "old")

        # check for success when providing two arguments regardless of browsing
        self.char1.player.aiwizard.tree = None
        self.char1.player.aiwizard.node = None

        self.call(commands.CmdRenameTree(), "'old' 'new'")
        assert(tree.name == "new")

    def test_assign(self):
        """
        Test the @aiassign command
        """
        self.call(commands.CmdNewTree(), "tree1")
        self.call(commands.CmdNewTree(), "tree2")
        tree1 = ScriptDB.objects.get(db_key="tree1")
        tree2 = ScriptDB.objects.get(db_key="tree2")

        dec1 = DecoratorNode("dec1", tree1, tree1.nodes[tree1.root])
        leaf1 = LeafNode("leaf1", tree1, dec1)
        leaf2 = LeafNode("leaf2", tree2, tree2.nodes[tree2.root])

        # check for failure when not providing arguments and not browsing
        self.call(commands.CmdAssignTree(), "")
        assert(not tree_assigned(tree1, self.obj1))
        assert(not tree_assigned(tree1, self.obj2))

        # Check for failure when providing a single argument and not browsing
        # any blackboard.
        self.char1.player.aiwizard.tree = tree1
        self.char1.player.aiwizard.node = tree1.root
        self.call(commands.CmdAssignTree(), "'tree1'")
        assert(not tree_assigned(tree1, self.obj1))
        assert(not tree_assigned(tree1, self.obj2))
        self.char1.player.aiwizard.tree = None
        self.char1.player.aiwizard.node = None

        # Check for failure when providing two arguments, of which one is
        # object or script, and not browsing any tree.
        self.char1.player.aiwizard.agent = self.obj1
        self.call(commands.CmdAssignTree(), "object 'Obj'")
        self.call(commands.CmdAssignTree(), "script 'Script'")
        assert(not tree_assigned(tree1, self.obj1))
        assert(not tree_assigned(tree1, self.script))
        assert(not tree_assigned(tree2, self.obj1))
        assert(not tree_assigned(tree2, self.script))
        self.char1.player.aiwizard.agent = None

        # Check for failure when providing more than 3 arguments.
        self.call(commands.CmdAssignTree(), "'tree1' object 'Obj' 'spurious'")
        assert(not tree_assigned(tree1, self.obj1))

        # Check for failure when providing a tree of None if the target
        # object has neither an assigned tree nor a default tree.
        # Examine all 3 possible combinations of arguments that include a
        # tree name of "none".
        self.call(commands.CmdAssignTree(), "none")
        assert(not self.obj1.db.ai)
        self.call(commands.CmdAssignTree(), "none object 'Obj'")
        assert(not self.obj1.db.ai)
        self.call(commands.CmdAssignTree(), "all none")
        assert(not self.obj1.db.ai)
        assert(not self.obj2.db.ai)
        assert(not self.script.db.ai)

        # Check for success when providing no arguments and browsing both a
        # tree and a blackboard.
        self.char1.player.aiwizard.tree = tree1
        self.char1.player.aiwizard.node = tree1.root
        self.char1.player.aiwizard.agent = self.obj1
        self.call(commands.CmdAssignTree(), "")
        assert(tree_assigned(tree1, self.obj1))

        # Check for success when providing one argument and browsing a
        # blackboard.
        self.char1.player.aiwizard.tree = None
        self.char1.player.aiwizard.node = None
        self.char1.player.aiwizard.agent = self.obj1
        self.call(commands.CmdAssignTree(), "'tree2'")
        assert(tree_assigned(tree2, self.obj1))

        # Check for success when providing two arguments and browsing a 
        # tree
        self.char1.player.aiwizard.tree = tree1
        self.char1.player.aiwizard.node = tree1.root
        self.char1.player.aiwizard.agent = None
        self.call(commands.CmdAssignTree(), "object 'Obj2'")
        assert(tree_assigned(tree1, self.obj2))

        # Check for success when providing three arguments
        self.char1.player.aiwizard.tree = None
        self.char1.player.aiwizard.node = None
        self.char1.player.aiwizard.agent = None
        self.call(commands.CmdAssignTree(), "'tree2' object 'Obj2'")
        assert(tree_assigned(tree2, self.obj2))

        # Check that nothing happens when providing a tree of None if the
        # target has no default tree and already has a tree assigned
        self.call(commands.CmdAssignTree(), "none object 'Obj'")
        assert(tree_assigned(tree2, self.obj1))

        # Check for success when providing a tree of None if the target
        # has a tree's name string or BehaviorTree object as its default tree
        assert(tree_assigned(tree2, self.obj1))
        self.obj1.aitree = 'tree1'
        self.call(commands.CmdAssignTree(), "none object 'Obj'")
        assert(tree_assigned(tree1, self.obj1))

        assert(tree_assigned(tree2, self.obj2))
        self.obj2.aitree = tree1
        self.call(commands.CmdAssignTree(), "none object 'Obj2'")
        assert(tree_assigned(tree1, self.obj2))

        # Check for success when transferring all agents that use tree1 to tree2
        assert(tree_assigned(tree1, self.obj1))
        assert(tree_assigned(tree1, self.obj2))
        assert(not tree_assigned(tree1, self.script))
        assert(not tree_assigned(tree2, self.script))
        self.call(commands.CmdAssignTree(), "'tree1' 'tree2'")
        assert(tree_assigned(tree2, self.obj1))
        assert(tree_assigned(tree2, self.obj2))
        assert(not tree_assigned(tree1, self.script))
        assert(not tree_assigned(tree2, self.script))

        # Check for success when transferring all agents to tree2
        assert(tree_assigned(tree2, self.obj1))
        assert(tree_assigned(tree2, self.obj2))
        assert(not tree_assigned(tree1, self.script))
        assert(not tree_assigned(tree2, self.script))
        self.call(commands.CmdAssignTree(), "all 'tree1'")
        assert(tree_assigned(tree1, self.obj1))
        assert(tree_assigned(tree1, self.obj2))
        assert(tree_assigned(tree1, self.script))

    def test_del_tree(self):
        """
        Test the @aideltree command
        """
        self.call(commands.CmdNewTree(), "tree")
        tree = ScriptDB.objects.get(db_key="tree")
        leaf1 = LeafNode("leaf1", tree, tree.nodes[tree.root])
        self.call(commands.CmdNewTree(), "tree2")
        tree2 = ScriptDB.objects.get(db_key="tree2")
        leaf2 = LeafNode("leaf2", tree2, tree2.nodes[tree2.root])

        # Set up the blackboards of all objects and scripts.
        self.obj1.ai.setup(tree=tree)
        self.obj2.ai.setup(tree=tree2)
        self.script.ai.setup(tree=tree)

        # Set the browsing cursor to the tree and to a blackboard associated
        # with the tree.
        self.char1.player.aiwizard.tree = tree
        self.char1.player.aiwizard.node = tree.nodes[tree.root]
        self.char1.player.aiwizard.agent = self.obj1

        # check for failure when not providing a name
        self.call(commands.CmdDelTree(), "")
        assert(tree.is_valid())

        # check for failure when putting single quotes in the name
        self.call(commands.CmdDelTree(), "'tree'")
        assert(tree.is_valid())

        # check that no blackboards or browsing cursors have been modified
        assert(self.obj1.db.ai)
        assert(self.obj2.db.ai)
        assert(self.script.db.ai)
        assert(self.char1.player.aiwizard.tree == tree)
        assert(self.char1.player.aiwizard.node == tree.nodes[tree.root])
        assert(self.char1.player.aiwizard.agent == self.obj1)

        # check for success when providing a valid argument
        self.call(commands.CmdDelTree(), "tree")
        assert(not tree.is_valid())

        # check that all blackboards have been cleared
        assert(not self.obj1.db.ai)
        assert(self.obj2.db.ai)
        assert(not self.script.db.ai)

        # check that the browsing cursor has been set to None
        assert(self.char1.player.aiwizard.tree == None)
        assert(self.char1.player.aiwizard.node == "")
        assert(self.char1.player.aiwizard.agent == None)


# Tests for the commands in command_view.py
class SuccessLeaf(LeafNode):
    def update(self, bb):
        return SUCCESS

def n_watchlists(player, n):
    return len(player.db.aiwizard['watching']) == n

def is_watching(player, node_hash, agent):
    return (node_hash, agent) in player.aiwizard.watching

def n_watchers(node_hash, agent, n):
    return len(agent.db.ai['nodes'][node_hash]['watchers']) == n

def is_in_watchers(player, node_hash, agent):
    return player in agent.db.ai['nodes'][node_hash]['watchers']

def is_at(player, tree, node_hash, agent):
    return (player.aiwizard.tree == tree and player.aiwizard.node == node_hash
            and player.aiwizard.agent == agent)


class TestViewCommands(CommandTest):
    player_typeclass = AIPlayer
    object_typeclass = AIObject
    script_typeclass = AIScript

    def test_list(self):
        """
        Test the @ailist command; simply ensures no errors arise
        """
        # Check that the command raises no errors when no trees exist.
        self.call(commands_view.CmdList(), "")

        # Check that the command raises no errors when one tree exists.
        self.call(commands.CmdNewTree(), "tree1")
        self.call(commands_view.CmdList(), "")

        # Check that the command raises no errors when multiple trees exist.
        self.call(commands.CmdNewTree(), "tree2")
        self.call(commands.CmdNewTree(), "tree3")
        self.call(commands_view.CmdList(), "")

    def test_look(self):
        """
        Test the @ailook command; simply ensures no errors arise
        """
        # check that the command raises no errors when called on its own
        # but not browsing any node or tree
        self.call(commands_view.CmdLook(), "")

        # check that the command raises no errors when called with the bb
        # argument when not browsing any blackboard
        self.call(commands_view.CmdLook(), "bb")

        # check that the command raises no errors when called with the globals
        # argument when not browsing any blackboard
        self.call(commands_view.CmdLook(), "globals")

        # check that the command raises no errors when called with an
        # inexistent tree and node
        self.call(commands_view.CmdLook(), "'treex' 'nodex'")

        # check that the command raises no errors when called with an
        # inexistent blackboard
        self.call(commands_view.CmdLook(), "bb")
        self.call(commands_view.CmdLook(), "bb 'treex' 'nodex'")

        # check for success when looking at an existent root, decorator,
        # composite and leaf node with or without siblings
        self.call(commands.CmdNewTree(), "tree")
        tree = ScriptDB.objects.get(db_key="tree")
        comp = CompositeNode("comp", tree, tree.nodes[tree.root])
        leaf1 = LeafNode("leaf1", tree, comp)
        dec = DecoratorNode("dec", tree, comp)
        leaf2 = LeafNode("leaf2", tree, dec)
        leaf3 = LeafNode("leaf3", tree, comp)
        self.call(commands.CmdAssignTree(), "'tree' 'Obj'")
 
        self.call(commands_view.CmdLook(), "'tree' 'comp'")
        self.call(commands_view.CmdLook(), "'tree' 'leaf1'")
        self.call(commands_view.CmdLook(), "'tree' 'dec'")
        self.call(commands_view.CmdLook(), "'tree' 'leaf2'")
        self.call(commands_view.CmdLook(), "'tree' 'leaf3'")

        # check for success when looking at a node while browsing it
        self.char1.player.aiwizard.tree = tree
        self.char1.player.aiwizard.node = tree.root
        self.call(commands_view.CmdLook(), "")

        # check for success when using the bb command and browsing a
        # blackboard
        self.char1.player.aiwizard.agent = self.obj1
        self.obj1.ai.setup(tree=tree)

        self.call(commands_view.CmdLook(), "bb")
        self.call(commands_view.CmdLook(), "globals")

        self.char1.player.aiwizard.tree = None
        self.char1.player.aiwizard.node = ""
        self.call(commands_view.CmdLook(), "bb 'tree' 'dec'")
        self.call(commands_view.CmdLook(), "globals")

    def test_status(self):
        """
        Test that the @aistatus command raises no errors when browsing and not
        browsing nodes and blackboards, as well as when watching and not
        watching any nodes.
        """
        self.call(commands.CmdNewTree(), "tree")
        tree = ScriptDB.objects.get(db_key="tree")
        leaf = LeafNode("leaf", tree, tree.nodes[tree.root])

        # check that no errors arise regardless of browsing status
        self.char1.player.aiwizard.tree = None
        self.char1.player.aiwizard.node = ""
        self.char1.player.aiwizard.agent = None
        self.call(commands_view.CmdStatus(), "")

        self.char1.player.aiwizard.tree = tree
        self.char1.player.aiwizard.node = tree.root
        self.char1.player.aiwizard.agent = None
        self.call(commands_view.CmdStatus(), "")

        self.char1.player.aiwizard.tree = None
        self.char1.player.aiwizard.node = ""
        self.char1.player.aiwizard.agent = self.obj1
        self.call(commands_view.CmdStatus(), "")

        self.char1.player.aiwizard.tree = tree
        self.char1.player.aiwizard.node = tree.root
        self.char1.player.aiwizard.agent = self.obj1
        self.call(commands_view.CmdStatus(), "")

        # check that no errors arise when one or more watchlists exist
        self.call(commands_view.CmdWatch(), "'tree' 'root'")
        self.call(commands_view.CmdStatus(), "")

        self.call(commands_view.CmdWatch(), "'tree' 'leaf'")
        self.call(commands_view.CmdStatus(), "")

    def test_watch_unwatch(self):
        """
        Test the @aiwatch and @aiunwatch commands
        """
        self.call(commands.CmdNewTree(), "tree")
        tree = ScriptDB.objects.get(db_key="tree")
        root = tree.nodes[tree.root]
        dec1 = Succeeder("dec1", tree, root)
        dec2 = Succeeder("dec2", tree, dec1)
        leaf = SuccessLeaf("leaf", tree, dec2)
        self.obj1.ai.setup(tree=tree)
        self.obj2.ai.setup(tree=tree)

        self.call(commands.CmdAssignTree(), "'tree' 'Obj'")
        self.call(commands.CmdAssignTree(), "'tree' 'Obj2'")
        
        # check for failure when not browsing and not specifying arguments
        assert(n_watchlists(self.player, 0))
        self.call(commands_view.CmdWatch(), "")
        assert(n_watchlists(self.player, 0))
        self.call(commands_view.CmdWatch(), "'dec1'")
        assert(n_watchlists(self.player, 0))
        self.call(commands_view.CmdWatch(), "'tree' 'dec1'")
        assert(n_watchlists(self.player, 0))
        self.call(commands_view.CmdWatch(), "object 'Obj'")
        assert(n_watchlists(self.player, 0))

        assert(n_watchlists(self.player, 0))
        self.call(commands_view.CmdUnwatch(), "")
        assert(n_watchlists(self.player, 0))
        self.call(commands_view.CmdUnwatch(), "'dec1'")
        assert(n_watchlists(self.player, 0))
        self.call(commands_view.CmdUnwatch(), "'tree' 'dec1'")
        assert(n_watchlists(self.player, 0))
        self.call(commands_view.CmdUnwatch(), "object 'Obj'")
        assert(n_watchlists(self.player, 0))

        def set_both_players(tree, node, agent):
            self.char1.player.aiwizard.tree = tree
            self.char1.player.aiwizard.node = node
            self.char1.player.aiwizard.agent = agent
            self.char2.player.aiwizard.tree = tree
            self.char2.player.aiwizard.node = node
            self.char2.player.aiwizard.agent = agent

        def check_both_players(argstr, node_hash, agent):
            self.call(commands_view.CmdWatch(), argstr)
            assert(n_watchlists(self.player, 1))
            assert(n_watchlists(self.player2, 0))
            assert(n_watchers(node_hash, agent, 1))
            assert(is_in_watchers(self.player, node_hash, agent))
            assert(not is_in_watchers(self.player2, node_hash, agent))

            self.call(commands_view.CmdWatch(), argstr, caller=self.char2)
            assert(n_watchlists(self.player, 1))
            assert(n_watchlists(self.player2, 1))
            assert(n_watchers(node_hash, agent, 2))
            assert(is_in_watchers(self.player, node_hash, agent))
            assert(is_in_watchers(self.player2, node_hash, agent))

            self.call(commands_view.CmdUnwatch(), argstr)
            assert(n_watchlists(self.player, 0))
            assert(n_watchlists(self.player2, 1))
            assert(n_watchers(node_hash, agent, 1))
            assert(not is_in_watchers(self.player, node_hash, agent))
            assert(is_in_watchers(self.player2, node_hash, agent))

            self.call(commands_view.CmdUnwatch(), argstr, caller=self.char2)
            assert(n_watchlists(self.player, 0))
            assert(n_watchlists(self.player2, 0))
            assert(n_watchers(node_hash, agent, 0))
            assert(not is_in_watchers(self.player, node_hash, agent))
            assert(not is_in_watchers(self.player2, node_hash, agent))

        # check for success when specifying all arguments on a valid tree,
        # node and agent
        set_both_players(None, None, None) 
        check_both_players("'tree' 'leaf' object 'Obj'", leaf.hash, self.obj1)

        # check for success when browsing
        set_both_players(tree, dec2.hash, None)
        check_both_players("object 'Obj'", dec2.hash, self.obj1)

        set_both_players(None, None, self.obj1)
        check_both_players("'tree' 'dec1'", dec1.hash, self.obj1)

        set_both_players(tree, tree.root, self.obj1)
        check_both_players("", tree.root, self.obj1)

        # check that using the @aiwatch command on the same node instance 
        # multiple times in a row does not add it to the watchlist multiple
        # times
        self.call(commands_view.CmdWatch(), "'tree' 'leaf' object 'Obj'")
        self.call(commands_view.CmdWatch(), "'tree' 'leaf' object 'Obj'")
        self.call(commands_view.CmdWatch(), "'tree' 'leaf' object 'Obj'")
        assert(n_watchlists(self.player, 1))
        self.call(commands_view.CmdUnwatch(), "'tree' 'leaf' object 'Obj'")
        assert(n_watchlists(self.player, 0))

        # prepare for removal and deletion tests
        self.call(commands_view.CmdWatch(), "'tree' 'leaf' object 'Obj'")
        self.call(commands_view.CmdWatch(), "'tree' 'dec1' object 'Obj'")
        self.call(commands_view.CmdWatch(), "'tree' 'dec2' object 'Obj'")
        self.call(commands_view.CmdWatch(), "'tree' 'root' object 'Obj'")

        self.call(
            commands_view.CmdWatch(), "'tree' 'leaf' object 'Obj'",
            caller=self.char2)
        self.call(
            commands_view.CmdWatch(), "'tree' 'dec1' object 'Obj'",
            caller=self.char2)
        self.call(
            commands_view.CmdWatch(), "'tree' 'dec2' object 'Obj'",
            caller=self.char2)
        self.call(
            commands_view.CmdWatch(), "'tree' 'root' object 'Obj'",
            caller=self.char2)

        # check that removing a node from a tree removes it and its children
        # from all watchlists
        self.call(commands_build.CmdRemove(), "'tree' 'leaf'")
        self.call(commands_build.CmdRemove(), "'tree' 'dec2'")
        assert(n_watchlists(self.player, 2))
        assert(n_watchlists(self.player2, 2))
        assert(is_watching(self.player, root.hash, self.obj1))
        assert(is_watching(self.player, dec1.hash, self.obj1))
        assert(is_watching(self.player2, root.hash, self.obj1))
        assert(is_watching(self.player2, dec1.hash, self.obj1))

        # check that deleting a tree removes all its nodes from all watchlists
        self.call(commands.CmdDelTree(), "tree")
        assert(n_watchlists(self.player, 0))
        assert(n_watchlists(self.player2, 0))

#def n_watchlists(player, n):
#def is_watching(player, node_hash, agent):
#def n_watchers(node_hash, agent, n):
#def is_in_watchers(player, node_hash, agent):
        #@aiwatch
        #@aiwatch '<node name>'
        #@aiwatch <object|script> '<agent name>'
        #@aiwatch '<tree name>' '<node name>' <object|script> '<agent name>'

    def test_go(self):
        """
        Test the @aigo command
        """
        self.call(commands.CmdNewTree(), "tree1")
        self.call(commands.CmdNewTree(), "tree2")
        tree1 = ScriptDB.objects.get(db_key="tree1")
        tree2 = ScriptDB.objects.get(db_key="tree2")
        leaf1 = LeafNode("leaf1", tree1, tree1.nodes[tree1.root])
        leaf2 = LeafNode("leaf2", tree2, tree2.nodes[tree2.root])

        self.obj1.ai.setup(tree=tree1)
        self.obj2.ai.setup(tree=tree2)

        self.char1.player.aiwizard.tree = None
        self.char1.player.aiwizard.node = ""
        self.char1.player.aiwizard.agent = None

        # test that @aigo does nothing when called without arguments
        self.call(commands_view.CmdGo(), "")
        is_at(self.player, None, "", None)
        
        # test that @aigo bb does nothing when not browsing a blackboard
        self.call(commands_view.CmdGo(), "bb")
        is_at(self.player, None, "", None)
        self.call(commands_view.CmdGo(), "bb 'leaf1'")
        is_at(self.player, None, "", None)

        # test that @aigo works when called with the right arguments
        self.call(commands_view.CmdGo(), "'tree1'")
        assert(is_at(self.player, tree1, tree1.root, None))
        self.call(commands_view.CmdGo(), "'tree2' 'leaf2'")
        assert(is_at(self.player, tree2, leaf2.hash, None))

        # test that @aigo bb works when browsing a blackboard
        self.char1.player.aiwizard.agent = self.obj1
        self.call(commands_view.CmdGo(), "bb")
        assert(is_at(self.player, tree1, tree1.root, self.obj1))

        self.char1.player.aiwizard.agent = self.obj2
        self.call(commands_view.CmdGo(), "bb 'leaf2'")
        assert(is_at(self.player, tree2, leaf2.hash, self.obj2))

        # test that going to the same node twice has no effect
        self.call(commands_view.CmdGo(), "'tree1' 'leaf1'")
        self.call(commands_view.CmdGo(), "'tree1' 'leaf1'")
        assert(is_at(self.player, tree1, leaf1.hash, self.obj2))

    def test_bb(self):
        self.call(commands.CmdNewTree(), "tree1")
        self.call(commands.CmdNewTree(), "tree2")
        tree1 = ScriptDB.objects.get(db_key="tree1")
        tree2 = ScriptDB.objects.get(db_key="tree2")
        leaf1 = LeafNode("leaf1", tree1, tree1.nodes[tree1.root])
        leaf2 = LeafNode("leaf2", tree2, tree2.nodes[tree2.root])

        self.obj1.ai.setup(tree=tree1)
        self.script.ai.setup(tree=tree2)

        self.char1.player.aiwizard.tree = None
        self.char1.player.aiwizard.node = ""
        self.char1.player.aiwizard.agent = None

        # test that the command does not work with no arguments or with only
        # one argument
        self.call(commands_view.CmdBB(), "")
        assert(is_at(self.player, None, "", None))

        self.call(commands_view.CmdBB(), "script")
        assert(is_at(self.player, None, "", None))

        self.call(commands_view.CmdBB(), "'Obj'")
        assert(is_at(self.player, None, "", None))

        # test that the command works when provided with the right arguments
        self.call(commands_view.CmdBB(), "object 'Obj'")
        assert(is_at(self.player, None, "", self.obj1))
        self.call(commands_view.CmdBB(), "script 'Script'")
        assert(is_at(self.player, None, "", self.script))

    def test_up(self):
        self.call(commands.CmdNewTree(), "tree")
        tree = ScriptDB.objects.get(db_key="tree")
        leaf = LeafNode("leaf", tree, tree.nodes[tree.root])

        # check for failure when attempting to go up without browsing
        self.call(commands_view.CmdUp(), "")
        assert(is_at(self.player, None, "", None))

        # check for failure when attempting to go up the root
        self.call(commands_view.CmdGo(), "'tree' 'root'")
        assert(is_at(self.player, tree, tree.root, None))
        self.call(commands_view.CmdUp(), "")
        assert(is_at(self.player, tree, tree.root, None))

        # check for success when going up from a node with a parent
        self.call(commands_view.CmdGo(), "'tree' 'leaf'")
        assert(is_at(self.player, tree, leaf.hash, None))
        self.call(commands_view.CmdUp(), "")
        assert(is_at(self.player, tree, tree.root, None))

    def test_down(self):
        self.call(commands.CmdNewTree(), "tree")
        tree = ScriptDB.objects.get(db_key="tree")
        dec = DecoratorNode("dec", tree, tree.nodes[tree.root])
        compm = CompositeNode("compm", tree, dec) # multiple children
        leaf1 = LeafNode("leaf1", tree, compm)
        leaf2 = LeafNode("leaf2", tree, compm)
        compn = CompositeNode("compn", tree, compm) # no children
        comps = CompositeNode("comps", tree, compm) # singular child
        leaf3 = LeafNode("leaf3", tree, comps)

        # check for failure when attempting to go down without browsing
        self.call(commands_view.CmdDown(), "")
        assert(is_at(self.player, None, "", None))
        self.call(commands_view.CmdDown(), "3")
        assert(is_at(self.player, None, "", None))

        # check for failure when attempting to go down from a leaf
        self.call(commands_view.CmdGo(), "'tree' 'leaf3'")
        assert(is_at(self.player, tree, leaf3.hash, None))
        self.call(commands_view.CmdDown(), "")
        assert(is_at(self.player, tree, leaf3.hash, None))
        self.call(commands_view.CmdDown(), "5")
        assert(is_at(self.player, tree, leaf3.hash, None))

        # check for failure when attempting to go down a composite node without
        # children
        self.call(commands_view.CmdGo(), "'tree' 'compn'")
        assert(is_at(self.player, tree, compn.hash, None))
        self.call(commands_view.CmdDown(), "")
        assert(is_at(self.player, tree, compn.hash, None))
        self.call(commands_view.CmdDown(), "5")
        assert(is_at(self.player, tree, compn.hash, None))

        # check for failure when attempting to go down a composite node 
        # with multiple children without providing a position argument
        self.call(commands_view.CmdGo(), "'tree' 'compm'")
        assert(is_at(self.player, tree, compm.hash, None))
        self.call(commands_view.CmdDown(), "")
        assert(is_at(self.player, tree, compm.hash, None))

        # check for success when descending from a non-leaf node without
        # arguments
        self.call(commands_view.CmdGo(), "'tree' 'root'")
        assert(is_at(self.player, tree, tree.root, None))
        self.call(commands_view.CmdDown(), "")
        assert(is_at(self.player, tree, dec.hash, None))

        # check that descending with a position argument on a non-composite
        # node does not raise an error
        self.call(commands_view.CmdGo(), "'tree' 'root'")
        self.call(commands_view.CmdDown(), "-3")
        assert(is_at(self.player, tree, dec.hash, None))

        # check that the command accepts a name, a hash or a positive or 
        # negative index as a position argument
        self.call(commands_view.CmdGo(), "'tree' 'compm'")
        assert(is_at(self.player, tree, compm.hash, None))
        self.call(commands_view.CmdDown(), "1")
        assert(is_at(self.player, tree, leaf2.hash, None))

        self.call(commands_view.CmdGo(), "'tree' 'compm'")
        self.call(commands_view.CmdDown(), "'leaf1'")
        assert(is_at(self.player, tree, leaf1.hash, None))

        hash_str = "'{0}'".format(compn.hash[0:3])
        self.call(commands_view.CmdGo(), "'tree' 'compm'")
        self.call(commands_view.CmdDown(), hash_str)
        assert(is_at(self.player, tree, compn.hash, None))

        # check for success when going down from a composite node with a 
        # single child node, with or without arguments
        self.call(commands_view.CmdGo(), "'tree' 'comps'")
        self.call(commands_view.CmdDown(), "")
        assert(is_at(self.player, tree, leaf3.hash, None))

        self.call(commands_view.CmdGo(), "'tree' 'comps'")
        self.call(commands_view.CmdDown(), "1")
        assert(is_at(self.player, tree, leaf3.hash, None))


def n_nodes_in_tree(tree, n):
    return len(tree.nodes.keys()) == n


def node_in_tree(tree, node):
    return tree.nodes.has_key(node.hash)


def copy_move_swap_suite(test_case, cmd):
    self = test_case

    self.call(commands.CmdNewTree(), "tree1")
    tree1 = ScriptDB.objects.get(db_key="tree1")
    self.call(commands.CmdNewTree(), "tree2")
    tree2 = ScriptDB.objects.get(db_key="tree2")
    root1 = tree1.nodes[tree1.root]
    root2 = tree2.nodes[tree2.root]
    dec1 = DecoratorNode("dec1", tree1, root1)
    dec2 = DecoratorNode("dec2", tree2, root2)

    # test that the command fails when providing insufficient arguments
    # and not browsing
    self.call(cmd(), "")

    def check_failure():
        assert(n_nodes_in_tree(tree1, 2))
        assert(n_nodes_in_tree(tree2, 2))
        assert(dec1.parent == root1)
        assert(dec2.parent == root2)

    self.call(cmd(), "'dec1'")
    check_failure()

    self.call(cmd(), "'tree1' 'dec1'")
    check_failure()

    self.call(cmd(), "'dec1' 'tree2' 'dec2'")
    check_failure()

    # test that the command succeed when providing all arguments even if
    # not browsing
    def check_success_and_cleanup():
        if cmd == commands_build.CmdCopy:
            assert(n_nodes_in_tree(tree1, 2))
            assert(n_nodes_in_tree(tree2, 3))
            assert(dec2.children != None)
            del_args = "'tree2' '{0}'".format(dec2.children.hash[0:3])
            self.call(commands_build.CmdRemove(), del_args)

        elif cmd == commands_build.CmdMove:
            assert(n_nodes_in_tree(tree1, 1))
            assert(n_nodes_in_tree(tree2, 3))
            assert(dec1.parent == dec2)
            assert(root1.children == None)
            self.call(commands_build.CmdMove(), "'tree2' 'dec1' 'tree1' 'root'")

        else:
            assert(n_nodes_in_tree(tree1, 2))
            assert(n_nodes_in_tree(tree2, 2))
            assert(dec1.parent == root2)
            assert(dec2.parent == root1)
            self.call(commands_build.CmdSwap(), "'tree2' 'dec1' 'tree1' 'dec2'")

    self.call(cmd(), "'tree1' 'dec1' 'tree2' 'dec2'")
    check_success_and_cleanup()

    # check success when browsing
    self.player.aiwizard.tree = tree1
    self.player.aiwizard.node = tree1.root
    self.call(cmd(), "'dec1' 'tree2' 'dec2'")
    check_success_and_cleanup()

    self.player.aiwizard.node = dec1.hash
    self.call(cmd(), "'tree2' 'dec2'")
    check_success_and_cleanup()

    comp1 = CompositeNode("comp1", tree1, dec1)
    comp1x = CompositeNode("comp1x", tree1, comp1)
    leaf11 = LeafNode("leaf11", tree1, comp1)
    leaf12 = LeafNode("leaf12", tree1, comp1)
    comp2 = CompositeNode("comp2", tree2, dec2)
    comp2x = CompositeNode("comp2x", tree2, comp2)
    leaf21 = LeafNode("leaf21", tree2, comp2)
    leaf22 = LeafNode("leaf22", tree2, comp2)

    assert(n_nodes_in_tree(tree1, 6))
    assert(n_nodes_in_tree(tree2, 6))

    # check success when browsing and affecting nodes in the same tree
    self.call(commands_view.CmdGo(), "'tree1' 'leaf12'")
    #import pdb; pdb.set_trace()
    self.call(cmd(), "'comp1x'")

    if cmd == commands_build.CmdCopy:
        assert(n_nodes_in_tree(tree1, 7))
        assert(comp1x.children[0].name == "leaf12")        
        del_args = "'tree1' '{0}'".format(comp1x.children[0].hash[0:3])
        self.call(commands_build.CmdRemove(), del_args)

    elif cmd == commands_build.CmdMove:
        assert(n_nodes_in_tree(tree1, 6))
        assert(comp1x.children[0].name == "leaf12")
        move_args = "'leaf12' 'tree1' 'comp1'"
        self.call(commands_build.CmdMove(), move_args)

    else:
        assert(n_nodes_in_tree(tree1, 6))
        assert(comp1.children[0] == leaf12)
        assert(comp1.children[2] == comp1x)
        self.call(commands_build.CmdSwap(), 'comp1x' 'tree1' 'leaf12')

    # check success when using the "in" command
    if cmd == commands_build.CmdCopy:
        self.call(commands_build.CmdCopy(), "'comp1x' 'tree1' 'comp1' in")
        assert(n_nodes_in_tree(tree1, 7))
        assert(dec1.children.name == "comp1x")
        comp1x_new = dec1.children
        dec1.children = comp1
        comp1.parent = dec1
        comp1x_new.children = []
        del_args = "'tree1' '{0}'".format(comp1x_new.hash[0:3])
        self.call(commands_build.CmdRemove(), del_args)

    elif cmd == commands_build.CmdMove:
        self.call(commands_build.CmdMove(), "'comp1x' 'tree1' 'comp1' in")
        assert(n_nodes_in_tree(tree1, 6))
        assert(dec1.children.name == "comp1x")
        comp1x.parent = comp1
        dec1.children = comp1
        comp1.children.insert(0, comp1x)

    # check that the position argument works
    if cmd == commands_build.CmdCopy:
        self.call(commands_build.CmdCopy(), "'leaf12' 'tree2' 'comp2' 1")
        assert(n_nodes_in_tree(tree1, 6))
        assert(n_nodes_in_tree(tree2, 7))
        assert(comp2.children[1].name == "leaf12")
        del_args = "'tree1' '{0}'".format(comp2.children[1].hash[0:3])
        self.call(commands_build.CmdRemove(), del_args)

    elif cmd == commands_build.CmdMove:
        self.call(commands_build.CmdMove(), "'leaf12' 'tree2' 'comp2' 1")
        assert(n_nodes_in_tree(tree1, 5))
        assert(n_nodes_in_tree(tree2, 7))
        assert(comp2.children[1].name == "leaf12")
        self.call(commands_build.CmdMove(), "'tree2' 'leaf12' 'tree1' 'comp1'")


class TestBuildCommands(CommandTest):
    player_typeclass = AIPlayer
    object_typeclass = AIObject
    script_typeclass = AIScript

    def test_set_prop(self):
        """
        Test the @aisetprop command
        """
        self.call(commands.CmdNewTree(), "tree")
        tree = ScriptDB.objects.get(db_key="tree")
        root = tree.nodes[tree.root]
        leaf = LeafNode("leaf", tree, root)
        root.test = False
        leaf.test = False

        # check for failure when providing an agent that is not set up
        self.call(commands_build.CmdSetProp(), "object 'Obj' test=True")
        assert(not self.obj1.db.ai)
        self.call(commands_build.CmdSetProp(), "globals object 'Obj' test=True")
        assert(not self.obj1.db.ai)
        self.call(commands_build.CmdSetProp(), 
                  "'tree' 'root' object 'Obj' test=True")
        assert(not self.obj1.db.ai)

        self.obj1.ai.setup(tree=tree)

        # check for failure when providing no arguments and not browsing
        self.call(commands_build.CmdSetProp(), "test=True")
        assert(root.test == False and leaf.test == False)

        # check for failure when providing the bb or globals argument and not
        # browsing any blackboard
        self.call(commands_build.CmdSetProp(), "bb test=True")
        assert(root.test == False and leaf.test == False)
        assert(not self.obj1.db.ai['globals'].has_key("test"))

        self.call(commands_build.CmdSetProp(), "globals test=True")
        assert(root.test == False and leaf.test == False)
        assert(not self.obj1.db.ai['globals'].has_key("test"))

        # check for failure when providing an agent but not browsing any tree
        self.call(commands_build.CmdSetProp(), "object 'Obj' test=True")
        assert(root.test == False and leaf.test == False)
        assert(not self.obj1.db.ai['globals'].has_key("test"))

        # check for success when providing a tree and node even when not
        # browsing
        self.call(commands_build.CmdSetProp(), "'tree' 'leaf' test=True")
        assert(root.test == False and leaf.test == True)
        leaf.test = False

        # check for success when providing all arguments even when not
        # browsing
        self.call(commands_build.CmdSetProp(),
                  "'tree' 'leaf' object 'Obj' test=True")
        assert(root.test == False and leaf.test == False)
        assert(self.obj1.db.ai['nodes'][leaf.hash]['test'] == True)
        del self.obj1.db.ai['nodes'][leaf.hash]['test']

        # check for success when providing the required arguments for the
        # globals <object|script> <agent name> version of the command even
        # when not browsing
        self.call(commands_build.CmdSetProp(),
                  "globals object 'Obj' test=True")
        assert(root.test == False and leaf.test == False)
        assert(self.obj1.db.ai['globals']['test'] == True)
        del self.obj1.db.ai['globals']['test']

        # check for success when providing no arguments and browsing
        self.call(commands_view.CmdGo(), "'tree' 'root'")
        self.call(commands_build.CmdSetProp(), "test=True")
        assert(root.test == True and leaf.test == False)
        root.test = False

        # check for success when providing an agent and browsing
        self.call(commands_view.CmdGo(), "'tree' 'root'")
        self.call(commands_build.CmdSetProp(), "object 'Obj' test=True")
        assert(root.test == False and leaf.test == False)
        assert(self.obj1.db.ai['nodes'][root.hash]['test'] == True)
        del self.obj1.db.ai['nodes'][root.hash]['test']

        # check for success with the globals argument when browsing a blackboard
        # even when not browsing a tree
        self.char1.player.aiwizard.tree = None
        self.char1.player.aiwizard.node = ""

        self.call(commands_view.CmdBB(), "object 'Obj'")
        self.call(commands_build.CmdSetProp(), "globals test=True")
        assert(root.test == False and leaf.test == False)
        assert(self.obj1.db.ai['globals']['test'] == True)
        del self.obj1.db.ai['globals']['test']

        # check for success with the bb argument when browsing a blackboard
        # and a node in a tree
        self.call(commands_view.CmdGo(), "'tree' 'root'")
        self.call(commands_view.CmdBB(), "object 'Obj'")
        self.call(commands_build.CmdSetProp(), "bb test=True")
        assert(root.test == False and leaf.test == False)
        assert(self.obj1.db.ai['nodes'][root.hash]['test'] == True)
        del self.obj1.db.ai['nodes'][root.hash]['test']

        # check that the command works with a variety of right-hand arguments
        self.call(commands_view.CmdGo(), "'test' 'root'")
        self.call(commands_build.CmdSetProp(), "test='string'")
        assert(root.test == 'string')
        self.call(commands_build.CmdSetProp(), "test='string'")
        assert(root.test == 'string')
        self.call(commands_build.CmdSetProp(), "test=-4.5")
        assert(root.test == -4.5)
        self.call(commands_build.CmdSetProp(), "test={'a':[1,{'b':2}],'c':3}")
        assert(root.test == {'a':[1, {'b':2}], 'c':3})

        # check that the command works with a chain of indices
        self.call(commands_view.CmdGo(), "'test' 'root'")
        root.test = {'a':[1,{'b':2}],'c':3}
        self.call(commands_build.CmdSetProp(), "test['a'][1]['b']=5")
        assert(root.test == {'a':[1, {'b':5}],'c':3})
        self.call(commands_build.CmdSetProp(), "test['a'][1]={'x':2}")
        assert(root.test == {'a':[1, {'x':2}],'c':3})
        self.call(commands_build.CmdSetProp(), "test['a']=True")
        assert(root.test == {'a':True, 'c':3})

    def test_del_prop(self):
        """
        Test the @aidelprop command
        """
        self.call(commands.CmdNewTree(), "tree")
        tree = ScriptDB.objects.get(db_key="tree")
        root = tree.nodes[tree.root]
        leaf = LeafNode("leaf", tree, root)
        root.test = False
        leaf.test = False

        # check for failure when providing an agent that is not set up
        self.call(commands_build.CmdDelProp(), "object 'Obj' test")
        assert(not self.obj1.db.ai)
        self.call(commands_build.CmdDelProp(), "globals object 'Obj' test")
        assert(not self.obj1.db.ai)
        self.call(commands_build.CmdDelProp(), 
                  "'tree' 'root' object 'Obj' test")
        assert(not self.obj1.db.ai)

        self.obj1.ai.setup(tree=tree)
        self.obj1.db.ai['nodes'][leaf.hash]['test'] = False
        self.obj1.db.ai['globals']['test'] = False

        # check for failure when providing no arguments and not browsing
        self.call(commands_build.CmdDelProp(), "test")
        assert(root.test == False and leaf.test == False)

        # check for failure when providing the bb or globals argument and not
        # browsing any blackboard
        self.call(commands_build.CmdDelProp(), "bb test")
        assert(root.test == False and leaf.test == False)
        assert(self.obj1.db.ai['globals']['test'] == False)

        self.call(commands_build.CmdDelProp(), "globals test")
        assert(root.test == False and leaf.test == False)
        assert(self.obj1.db.ai['globals']['test'] == False)

        # check for failure when providing an agent but not browsing any tree
        self.call(commands_build.CmdDelProp(), "object 'Obj' test")
        assert(root.test == False and leaf.test == False)
        assert(self.obj1.db.ai['globals']['test'] == False)

        # check for success when providing a tree and node even when not
        # browsing
        self.call(commands_build.CmdDelProp(), "'tree' 'leaf' test")
        assert(root.test == False and not hasattr(leaf, 'test'))
        leaf.test = False

        # check for success when providing all arguments even when not
        # browsing
        self.call(commands_build.CmdDelProp(),
                  "'tree' 'leaf' object 'Obj' test")
        assert(root.test == False and leaf.test == False)
        assert(not self.obj1.db.ai['nodes'][leaf.hash].has_key("test"))
        self.obj1.db.ai['nodes'][leaf.hash]['test'] = False

        # check for success when providing the required arguments for the
        # globals <object|script> <agent name> version of the command even
        # when not browsing
        self.call(commands_build.CmdDelProp(),
                  "globals object 'Obj' test")
        assert(root.test == False and leaf.test == False)
        assert(not self.obj1.db.ai['globals'].has_key("test"))
        self.obj1.db.ai['globals']['test'] = False

        # check for success when providing no arguments and browsing
        self.call(commands_view.CmdGo(), "'tree' 'root'")
        self.call(commands_build.CmdDelProp(), "test")
        assert(not hasattr(root, 'test') and leaf.test == False)
        root.test = False

        # check for success when providing an agent and browsing
        self.call(commands_view.CmdGo(), "'tree' 'root'")
        self.call(commands_build.CmdDelProp(), "object 'Obj' test")
        assert(root.test == False and leaf.test == False)
        assert(not self.obj1.db.ai['nodes'][root.hash].has_key("test"))
        self.obj1.db.ai['nodes'][root.hash]['test'] = False

        # check for success with the globals argument when browsing a blackboard
        # even when not browsing a tree
        self.char1.player.aiwizard.tree = None
        self.char1.player.aiwizard.node = ""

        self.call(commands_view.CmdBB(), "object 'Obj'")
        self.call(commands_build.CmdDelProp(), "globals test")
        assert(root.test == False and leaf.test == False)
        assert(not self.obj1.db.ai['globals'].has_key("test"))
        self.obj1.db.ai['globals']['test'] = False

        # check for success with the bb argument when browsing a blackboard
        # and a node in a tree
        self.call(commands_view.CmdGo(), "'tree' 'root'")
        self.call(commands_view.CmdBB(), "object 'Obj'")
        self.call(commands_build.CmdDelProp(), "bb test")
        assert(root.test == False and leaf.test == False)
        assert(not self.obj1.db.ai['nodes'][root.hash].has_key("test"))
        self.obj1.db.ai['nodes'][root.hash]['test'] = False

        # check that the command works with a chain of indices
        self.call(commands_view.CmdGo(), "'test' 'root'")
        root.test = {'a':[1,{'b':2}],'c':3}
        self.call(commands_build.CmdDelProp(), "test['a'][1]['b']")
        assert(root.test == {'a':[1, {}],'c':3})

        root.test = {'a':[1,{'b':2}],'c':3}
        self.call(commands_build.CmdDelProp(), "test['a'][1]")
        assert(root.test == {'a':[1],'c':3})

        root.test = {'a':[1,{'b':2}],'c':3}
        self.call(commands_build.CmdDelProp(), "test['a']")
        assert(root.test == {'c':3})


    def test_add_remove(self):
        """
        Test the @aiadd and @airemove commands
        """
        self.call(commands.CmdNewTree(), "tree")
        tree = ScriptDB.objects.get(db_key="tree")
        assert(n_nodes_in_tree(tree, 1))

        # check for @aiadd failure when attempting to add a root
        self.call(commands_build.CmdAdd(), "'tree' 'root' RootNode 'root2'")
        assert(n_nodes_in_tree(tree, 1))

        # check for @airemove failure when attempting to remove a root
        self.call(commands_build.CmdRemove(), "'tree' 'root'")
        assert(n_nodes_in_tree(tree, 1))

        # check for @aiadd failure when providing no arguments or only a node
        # argument and not browsing
        self.call(commands_build.CmdAdd(), "LeafNode 'leaf'")
        assert(n_nodes_in_tree(tree, 1))
        self.call(commands_build.CmdAdd(), "'root' LeafNode 'leaf'")
        assert(n_nodes_in_tree(tree, 1))

        # check for @aiadd success when providing all arguments and not browsing
        self.call(commands_build.CmdAdd(), "'tree' 'root' LeafNode 'leaf'")
        assert(n_nodes_in_tree(tree, 2))

        # check for @airemove failure when providing no arguments or only a
        # node argument and not browsing
        self.call(commands_build.CmdRemove(), "")
        assert(n_nodes_in_tree(tree, 2))
        self.call(commands_build.CmdRemove(), "'leaf'")
        assert(n_nodes_in_tree(tree, 2))

        # check for @airemove success when providing all arguments and not
        # browsing
        self.call(commands_build.CmdRemove(), "'tree' 'leaf'")
        assert(n_nodes_in_tree(tree, 1))

        # check for @aiadd success when providing one or no arguments and
        # browsing
        self.call(commands_view.CmdGo(), "'tree' 'root'")
        self.call(commands_build.CmdAdd(), "DecoratorNode 'dec1'")
        assert(n_nodes_in_tree(tree, 2))
        self.call(commands_build.CmdAdd(), "'dec1' DecoratorNode 'dec2'")
        assert(n_nodes_in_tree(tree, 3))

        # check for @airemove success when providing one or no arguments and
        # browsing
        self.call(commands_view.CmdGo(), "'tree' 'dec2'")
        self.call(commands_build.CmdRemove(), "")
        assert(n_nodes_in_tree(tree, 2))

        # as an interlude, check that @airemove moves the browsing cursor to
        # the parent node
        dec1 = tree.nodes[tree.root].children
        assert(is_at(self.player, tree, dec1.hash, None))

        self.call(commands_view.CmdGo(), "'tree' 'root'")
        self.call(commands_build.CmdRemove(), "'dec1'")
        assert(n_nodes_in_tree(tree, 1))

        comp = CompositeNode("comp", tree, tree.nodes[tree.root])

        # check that adding nodes without a position argument adds them
        # to the end of the children list
        self.call(commands_build.CmdAdd(), "'comp' LeafNode 'leaf1'")
        self.call(commands_build.CmdAdd(), "'comp' LeafNode 'leaf2'")
        self.call(commands_build.CmdAdd(), "'comp' LeafNode 'leaf3'")
        assert(n_nodes_in_tree(tree, 5))
        assert(comp.children[1].name == "leaf2"
               and comp.children[2].name == "leaf3")

        # check that adding a positive or negative position arguments works
        self.call(commands_build.CmdAdd(), "'comp' LeafNode 'leaf4' 1")
        assert(n_nodes_in_tree(tree, 6))
        assert(comp.children[1].name == "leaf4")
        self.call(commands_build.CmdAdd(), "'comp' LeafNode 'leaf5' -3")
        assert(n_nodes_in_tree(tree, 7))
        assert(comp.children[1].name == "leaf5")

        # check that the in argument works without a position 
        self.call(commands_build.CmdAdd(), "'leaf5' DecoratorNode 'dec1' in")
        assert(n_nodes_in_tree(tree, 8))
        assert(comp.children[1].name == "dec1")
        assert(comp.children[1].children.name == "leaf5")

        # check that the in argument causes the position argument to be
        # ignored
        self.call(commands_build.CmdAdd(), "'leaf4' DecoratorNode 'dec2' 0 in")
        assert(comp.children[2].name == "dec2")
        assert(comp.children[2].children.name == "leaf4")


#n_nodes_in_tree(tree, n)
#node_in_tree(tree, node)

    def test_copy(self):
        """
        Test the @aicopy command
        """
        copy_move_swap_suite(self, commands_build.CmdCopy)

    def test_move(self):
        """
        Test the @aimove command
        """
        copy_move_swap_suite(self, commands_build.CmdMove)

    def test_swap(self):
        """
        Test the @aiswap command
        """
        copy_move_swap_suite(self, commands_build.CmdSwap)

    def test_shift(self):
        """
        Test the @aishift command
        """
        self.call(commands.CmdNewTree(), "tree")
        tree = ScriptDB.objects.get(db_key="tree")
        root = tree.nodes[tree.root]
        comp = CompositeNode("comp", tree, root)
        leaf1 = LeafNode("leaf1", tree, comp)
        leaf2 = LeafNode("leaf2", tree, comp)
        leaf3 = LeafNode("leaf3", tree, comp)

        # test for failure when providing insufficient arguments and not
        # browsing
        self.call(commands_build.CmdShift(), "")
        assert(comp.children == [leaf1, leaf2, leaf3])
        assert(n_nodes_in_tree(tree, 5))

        self.call(commands_build.CmdShift(), "'leaf1'")
        assert(comp.children == [leaf1, leaf2, leaf3])
        assert(n_nodes_in_tree(tree, 5))

        # test for failure when trying to shift the child of a non-composite
        # node
        self.call(commands_build.CmdShift(), "'tree' 'comp'")
        assert(root.children == comp)
        assert(n_nodes_in_tree(tree, 5))

        # test for success when shifting with all arguments
        self.call(commands_build.CmdShift(), "'tree' 'leaf1'")
        assert(comp.children == [leaf2, leaf3, leaf1])
        assert(n_nodes_in_tree(tree, 5))
        comp.children = [leaf1, leaf2, leaf3]

        # test for success when shifting while browsing
        self.call(commands_view.CmdGo(), "'tree'")
        self.call(commands_build.CmdShift(), "'leaf1'")
        assert(comp.children == [leaf2, leaf3, leaf1])
        assert(n_nodes_in_tree(tree, 5))
        comp.children = [leaf1, leaf2, leaf3]

        self.call(commands_view.CmdGo(), "'tree' 'leaf1'")
        self.call(commands_build.CmdShift(), "")
        assert(comp.children == [leaf2, leaf3, leaf1])
        assert(n_nodes_in_tree(tree, 5))
        comp.children = [leaf1, leaf2, leaf3]
        
        # test for success when shifting using the position argument
        self.call(commands_view.CmdGo(), "'tree' 'leaf1'")
        self.call(commands_build.CmdShift(), "1")
        assert(comp.children == [leaf2, leaf1, leaf3])
        assert(n_nodes_in_tree(tree, 5))
        comp.children = [leaf1, leaf2, leaf3]
