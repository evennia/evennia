"""
Tests for the aisystem package.

In order to run these tests, you must add the aisystem package as an app
to your game's server/conf/settings.py file. See the README.md file for
information on how to do that.
"""
from unittest import TestCase
#from django.test import TestCase

from evennia.contrib.aisystem.models import BehaviorTreeDB, BehaviorBlackboardDB
from evennia.contrib.aisystem.nodes import (RootNode, CompositeNode, 
    DecoratorNode, LeafNode)

"""
Tests:
* add single, newly generated node to tree
* add newly generated subtree to tree
* move single node within the same tree
* move subtree within the same tree

* move single node from tree1 to tree2
* move subtree from tree1 to tree2
* copy single node from tree1 to tree2
* copy subtree from tree1 to tree2

* add node to leaf node (must return a string)
* add node to a non-composite node that already has a child (must return a string)
"""

class TestTransition(TestCase):
    def setUp(self):
        self.tree1 = BehaviorTreeDB()
        self.tree1.name = "tree1"
        self.tree1.setup()

        self.tree2 = BehaviorTreeDB()
        self.tree2.name = "tree2"
        self.tree2.setup()

        self.tree3 = BehaviorTreeDB()
        self.tree3.name = "tree3"
        self.tree3.setup()

    def tearDown(self):
        pass

    def test_root_exists(self):
        assert(isinstance(self.tree1.root, RootNode))
        assert(isinstance(self.tree2.root, RootNode))

    def test_add_and_remove_node(self):
        """
        Test the operation of adding, removing and then copying in the
        same node to/from the root node of a tree.

        Check that a newly created leaf node correctly inserts itself
        in its tree's hash dict, that it updates its parent correctly
        when added to the root node, and that it is removed correctly
        from its parent's children and its  via the tree's remove() method.
        Also check that re-adding it 
        """
        leafnode = LeafNode("Leaf node", self.tree1, self.tree1.root)
        # check that the node is added to the tree's nodes registry
        assert(leafnode.hash in self.tree1.db_nodes.keys())
        assert(self.tree1.db_nodes[leafnode.hash] == leafnode)
        # check that the parent-child relationship is established
        assert(isinstance(self.tree1.root.children, LeafNode))
        assert(self.tree1.root.children.parent == self.tree1.root)
        # check that there are only two nodes registered in the tree
        assert(len(self.tree1.db_nodes.keys()) == 2)

        err = self.tree1.remove(self.tree1.root.children)
        assert(not err)

        # check that the node is removed from the tree's nodes registry
        assert(leafnode.hash not in self.tree1.db_nodes.keys())
        # check that the parent-child relationship is erased
        assert(self.tree1.root.children == None)
        assert(leafnode.parent == None)
        # check that there is only one node registered in the tree
        assert(len(self.tree1.db_nodes.keys()) == 1)

        # test the add method of BehaviorTreeDB, copying in a new leaf node
        err = self.tree1.add(leafnode, self.tree1.root)
        assert(not err)

        # check that the copied node is in the tree's nodes registry
        assert(leafnode.hash in self.tree1.db_nodes.keys())
        assert(isinstance(self.tree1.db_nodes[leafnode.hash], LeafNode))
        # check that the parent-child relationship is established
        assert(isinstance(self.tree1.root.children, LeafNode))
        assert(self.tree1.root.children.parent == self.tree1.root)
        # check that there are only two nodes registered in the tree
        assert(len(self.tree1.db_nodes.keys()) == 2)

    def test_add_and_remove_from_composite(self):
        """
        Test the operations of adding three leaf nodes to a composite node,
        adding more leaf nodes to the composite node at the end of its
        children list and at a specific position in its children list,
        and moving one of its children to another position in its children
        list.
        """
        composite = CompositeNode("composite node", self.tree1, 
            self.tree1.root)
        leaf1 = LeafNode("leaf 1", self.tree1, composite)
        leaf2 = LeafNode("leaf 2", self.tree1, composite)
        leaf3 = LeafNode("leaf 3", self.tree1, composite)

        # check that all leaf nodes have been inserted
        assert(len(composite.children) == 3)
        assert(composite.children[0] == leaf1)
        assert(composite.children[1] == leaf2)
        assert(composite.children[2] == leaf3)        

        err = self.tree1.add(leaf1, composite, position=2, copying=True)
        assert(not err)
        err = self.tree1.add(leaf1, composite, position=None, copying=True)
        assert(not err)
        # check that leaf3 is now the 4th node, and new leaf1
        # nodes are in the 3rd and 5th positions
        assert(composite.children[2].name == "leaf 1")
        assert(composite.children[3] == leaf3)
        assert(composite.children[2].name == "leaf 1")

        err = self.tree1.add(leaf1, composite, position=None, copying=False)
        assert(not err)
        # check that leaf1 has moved away from position 0
        assert(composite.children[0] != leaf1)
        # check that leaf1 has moved to the end-position
        assert(composite.children[-1] == leaf1)
        # check that there are still only 7 nodes in the registry
        assert(len(self.tree1.db_nodes.keys()) == 7)

    def test_recursive_add_hash(self):
        """
        Test whether recursive_add_hash works recursively by copying
        a subtree of one composite node and its two child leaf nodes
        to the composite's node own parent composite node, as well as
        copying another subtree from a different tree. This other subtree
        is composed of a composite node with a leaf node and a second
        composite node as children; the second composite node has two
        leaf nodes of its own.

        In the former case, identical hashes are detected in the registry
        and new hashes are assigned to the new nodes to avoid duplicates.
        In the latter case, the same hashes as those in tree2 are unlikely
        to exist in tree1, so new hashes are not usually created.
        """
        composite1 = CompositeNode("composite1", self.tree1, self.tree1.root)    
        composite2 = CompositeNode("composite2", self.tree1, composite1)
        leaf1 = LeafNode("leaf1", self.tree1, composite2)
        leaf2 = LeafNode("leaf2", self.tree1, composite2)

        err = self.tree1.add(composite2, composite1)
        assert(not err)

        # check that there are now 8 nodes in the registry
        assert(len(self.tree1.db_nodes.keys()) == 8)

        # check that the original nodes have retained their entries in the
        # registry
        assert(self.tree1.db_nodes.has_key(composite1.hash))
        assert(self.tree1.db_nodes.has_key(composite2.hash))
        assert(self.tree1.db_nodes.has_key(leaf1.hash))
        assert(self.tree1.db_nodes.has_key(leaf2.hash))
        assert(self.tree1.db_nodes[composite1.hash] == composite1)
        assert(self.tree1.db_nodes[composite2.hash] == composite2)
        assert(self.tree1.db_nodes[leaf1.hash] == leaf1)
        assert(self.tree1.db_nodes[leaf2.hash] == leaf2)

        # check that the new nodes have entries in the registry
        composite3 = [x for x in composite1.children if x != composite2][0]        
        assert(len(composite3.children) == 2)
        leaf3 = composite3.children[0]
        leaf4 = composite3.children[1]

        assert(self.tree1.db_nodes.has_key(composite3.hash))
        assert(self.tree1.db_nodes.has_key(leaf3.hash))
        assert(self.tree1.db_nodes.has_key(leaf4.hash))
        assert(self.tree1.db_nodes[composite3.hash] == composite3)
        assert(self.tree1.db_nodes[leaf3.hash] == leaf3)
        assert(self.tree1.db_nodes[leaf4.hash] == leaf4)

        # copy a subtree from another tree
        tree2_composite1 = CompositeNode("tree2 composite1", self.tree2, 
            self.tree2.root)
        tree2_composite2 = CompositeNode("tree2 composite2", self.tree2,
            tree2_composite1)
        tree2_leaf1 = LeafNode("tree2 leaf1", self.tree2, tree2_composite1)
        tree2_leaf2 = LeafNode("tree2 leaf2", self.tree2, tree2_composite2)
        tree2_leaf3 = LeafNode("tree2 leaf3", self.tree2, tree2_composite2)

        # check if tree1 already has the hashes of some of the nodes in tree2
        # if so, new hashes will be created in tree1 upon copying the subtree
        # from tree2, and they should therefore not be checked for
        tree2_composite1_hash_in_tree1 = self.tree1.db_nodes.has_key(
            tree2_composite1.hash)
        tree2_composite2_hash_in_tree1 = self.tree1.db_nodes.has_key(
            tree2_composite2.hash)
        tree2_leaf1_hash_in_tree1 = self.tree1.db_nodes.has_key(
            tree2_leaf1.hash)
        tree2_leaf2_hash_in_tree1 = self.tree1.db_nodes.has_key(
            tree2_leaf2.hash)
        tree2_leaf3_hash_in_tree1 = self.tree1.db_nodes.has_key(
            tree2_leaf3.hash) 

        err = self.tree1.add(tree2_composite1, composite1)
        assert(not err)

        # check that there are now 13 nodes in tree1's registry 
        assert(len(self.tree1.db_nodes.keys()) == 13)
        
        # check that the new nodes have entries in the registry
        tree2_composite1_clone = [x for x in self.tree1.db_nodes.values() if
                                  x.name == tree2_composite1.name]
        assert(tree2_composite1_clone)
        assert(tree2_composite1_hash_in_tree1 or self.tree1.db_nodes.has_key(
            tree2_composite1_clone[0].hash))

        tree2_composite2_clone = [x for x in self.tree1.db_nodes.values() if
                                  x.name == tree2_composite2.name]
        assert(tree2_composite2_clone)
        assert(tree2_composite2_hash_in_tree1 or self.tree1.db_nodes.has_key(
            tree2_composite2_clone[0].hash))

        tree2_leaf1_clone = [x for x in self.tree1.db_nodes.values() if
                             x.name == tree2_leaf1.name]
        assert(tree2_leaf1_clone)
        assert(tree2_leaf1_hash_in_tree1 or self.tree1.db_nodes.has_key(
            tree2_leaf1_clone[0].hash))

        tree2_leaf2_clone = [x for x in self.tree1.db_nodes.values() if
                             x.name == tree2_leaf2.name]
        assert(tree2_leaf2_clone)
        assert(tree2_leaf2_hash_in_tree1 or self.tree1.db_nodes.has_key(
            tree2_leaf2_clone[0].hash))

        tree2_leaf3_clone = [x for x in self.tree1.db_nodes.values() if
                             x.name == tree2_leaf3.name]    
        assert(tree2_leaf3_clone)
        assert(tree2_leaf3_hash_in_tree1 or self.tree1.db_nodes.has_key(
            tree2_leaf3_clone[0].hash))

    def test_recursive_remove_hash(self):
        """
        Remove a subtree from the root node of a tree. The subtree consists of
        a composite node with a leaf node and a second composite node as its
        children; the second composite node has two leaf nodes as its children.
        """
        composite1 = CompositeNode("composite1", self.tree1, self.tree1.root)
        leaf1 = LeafNode("leaf1", self.tree1, composite1)
        composite2 = CompositeNode("composite2", self.tree1, composite1)
        leaf2 = LeafNode("leaf2", self.tree1, composite2)
        leaf3 = LeafNode("leaf3", self.tree1, composite2)

        # check that there are now 6 nodes in the registry
        assert(len(self.tree1.db_nodes.keys()) == 6)

        err = self.tree1.remove(composite1)
        assert(not err)        

        # check that there is now only 1 node in the registry
        assert(len(self.tree1.db_nodes.keys()) == 1)

    def test_copy_from_same_tree(self):
        """
        Test the operation of copying a leaf node from one composite node of
        the same tree to another
        """
        composite1 = CompositeNode("composite1", self.tree1, self.tree1.root)
        composite2 = CompositeNode("composite2", self.tree1, composite1)
        leafnode = LeafNode("leaf node", self.tree1, composite1)
        old_hashval = leafnode.hash
        hashes = self.tree1.db_nodes.keys()

        err = self.tree1.add(leafnode, composite2)
        assert(not err)

        # get the copied leaf node
        new_hashval = [x for x in self.tree1.db_nodes.keys() if not x in hashes]
        assert(new_hashval) # copied leaf node is in tree1's registry
        new_hashval = new_hashval[0]
        newnode = self.tree1.db_nodes[new_hashval] 

        # check that there are now five nodes in the tree, including the root node
        assert(len(self.tree1.db_nodes.keys()) == 5)

        # check that the original leaf node's original parent-child relationship
        # remains intact
        assert(leafnode in composite1.children)
        assert(leafnode.parent == composite1)

        # check that the copied leaf node's new parent-child relationship has been
        # established
        assert(newnode in composite2.children)
        assert(newnode.parent == composite2)

        # check that the original leaf node's hash remains unchanged in both
        # the node itself and the registry 
        assert(old_hashval == leafnode.hash)
        assert(self.tree1.db_nodes.has_key(old_hashval))
        assert(self.tree1.db_nodes[old_hashval] == leafnode)
        
    def test_move_from_same_tree(self):
        """
        Test the operation of moving a leaf node from one composite node
        of the same tree to another
        """
        composite1 = CompositeNode("composite1", self.tree1, self.tree1.root)
        composite2 = CompositeNode("composite2", self.tree1, composite1)
        leafnode = LeafNode("leaf node", self.tree1, composite1)
        hashval = leafnode.hash

        err = self.tree1.add(leafnode, composite2, copying=False)
        assert(not err)

        # check that there are still only four nodes in the tree, 
        # including the root node
        assert(len(self.tree1.db_nodes.keys()) == 4)

        # check that the leaf node's original parent-child relationship has
        # been terminated
        assert(leafnode not in composite1.children)
        assert(leafnode.parent != composite1)

        # check that the leaf node's new parent-child relationship has been
        # established
        assert(leafnode in composite2.children)
        assert(leafnode.parent == composite2)

        # check that the leaf node's hash remains unchanged in both
        # the node itself and the registry 
        assert(hashval == leafnode.hash)
        assert(self.tree1.db_nodes.has_key(hashval))
        assert(self.tree1.db_nodes[hashval] == leafnode)

    def test_copy_from_other_tree(self):
        """
        Test the operation of copying a leaf node from one tree's root node to
        another tree's root node
        """
        leafnode = LeafNode("leaf node", self.tree1, self.tree1.root)
        old_hashval = leafnode.hash
        hashes = self.tree2.db_nodes.keys()

        self.tree2.add(leafnode, self.tree2.root, source_tree=self.tree1)

        # get the copied leaf node
        new_hashval = [x for x in self.tree2.db_nodes.keys() if not x in hashes]
        assert(new_hashval) # copied leaf node is in tree2's registry
        new_hashval = new_hashval[0]
        newnode = self.tree2.db_nodes[new_hashval]

        # check that there are still two nodes in tree1, including the root node
        assert(len(self.tree1.db_nodes.keys()) == 2)

        # check that there are now two nodes in tree2, including the root node
        assert(len(self.tree2.db_nodes.keys()) == 2)

        # check that the original leaf node's original parent-child relationship
        # remains intact
        assert(leafnode == self.tree1.root.children)
        assert(leafnode.parent == self.tree1.root)

        # check that the copied leaf node's new parent-child relationship has been
        # established
        assert(newnode == self.tree2.root.children)
        assert(newnode.parent == self.tree2.root)

        # check that the original leaf node's hash remains unchanged in both
        # the node itself and the registry 
        assert(old_hashval == leafnode.hash)
        assert(self.tree1.db_nodes.has_key(old_hashval))
        assert(self.tree1.db_nodes[old_hashval] == leafnode)

    def test_move_from_other_tree(self):
        """
        Test the operation of moving a leaf node from one tree's root node to
        another tree's root node
        """
        leafnode = LeafNode("leaf node", self.tree1, self.tree1.root)
        hashval = leafnode.hash

        err = self.tree2.add(leafnode, self.tree2.root, copying=False, 
            source_tree=self.tree1)
        assert(not err)

        # check that there is now only one node in tree1, i.e. the root node
        assert(len(self.tree1.db_nodes.keys()) == 1)

        # check that there are now two nodes in tree2, including the root node
        assert(len(self.tree2.db_nodes.keys()) == 2)

        # check that the original leaf node's original parent-child relationship
        # has been terminated
        assert(leafnode != self.tree1.root.children)
        assert(leafnode.parent != self.tree1.root)

        # check that the leaf node's new parent-child relationship has been
        # established
        assert(leafnode == self.tree2.root.children)
        assert(leafnode.parent == self.tree2.root)

        # check that the leaf node's hash remains unchanged
        assert(hashval == leafnode.hash)

        # check that the leaf node's hash has been removed from tree1's registry
        assert(not self.tree1.db_nodes.has_key(hashval))

        # check that the original leaf node's hash remains unchanged in both
        # the node itself and the registry 
        assert(self.tree2.db_nodes.has_key(hashval))
        assert(self.tree2.db_nodes[hashval] == leafnode)

    def test_add_error_not_node(self):
        """
        Confirm that the attempt to copy or move something that is not a node, or
        to copy or move a node to something that is not a node, returns an error
        message and does not perform any copying or moving operation
        """
        leafnode = LeafNode("leaf node", self.tree1, self.tree1.root)

        err = self.tree1.add(self.tree1, self.tree2.root)
        assert(isinstance(err, str) or isinstance(err, unicode))
        
        err = self.tree1.add(leafnode, self.tree2)
        assert(isinstance(err, str) or isinstance(err, unicode)) 
         
        # check that tree1 and tree2 have 2 and 1 nodes in their registries
        # respectively
        assert(len(self.tree1.db_nodes.keys()) == 2)
        assert(len(self.tree2.db_nodes.keys()) == 1)

        # check that leafnode is still in the registry of tree1
        assert(self.tree1.db_nodes.has_key(leafnode.hash))
        assert(self.tree1.db_nodes[leafnode.hash] == leafnode)

    def test_add_error_root_node(self):
        """
        Confirm that the attempt to copy or move a root node to another root node
        returns an error string and does not copy or move of the root node being
        added
        """
        err = self.tree1.add(self.tree2.root, self.tree1.root, 
            source_tree=self.tree2)
        assert(isinstance(err, str) or isinstance(err, unicode))

        err = self.tree1.add(self.tree2.root, self.tree1.root, copying=False,
            source_tree=self.tree1)
        assert(isinstance(err, str) or isinstance(err, unicode))
        
        # check that no root node was created or moved
        assert(len(self.tree1.db_nodes.keys()) == 1)
        assert(len(self.tree2.db_nodes.keys()) == 1)
        assert(self.tree1.db_nodes.has_key(self.tree1.root.hash))
        assert(self.tree1.db_nodes[self.tree1.root.hash] == self.tree1.root)

    def test_add_error_wrong_tree(self):
        """
        Confirm that the attempt to copy or move a node from tree1 to tree2,
        when source_tree is designated as tree3, will return an error
        and fail to perform the copy or move operation
        """
        leafnode = LeafNode("leaf node", self.tree1, self.tree1.root)
        
        err = self.tree2.add(leafnode, self.tree2.root, copying=True,
            source_tree=self.tree3)
        assert(isinstance(err, str) or isinstance(err, unicode))

        err = self.tree2.add(leafnode, self.tree2.root, copying=False,
            source_tree=self.tree3)
        assert(isinstance(err, str) or isinstance(err, unicode))

        # check that no node was created or moved
        assert(len(self.tree1.db_nodes.keys()) == 2)
        assert(len(self.tree2.db_nodes.keys()) == 1)
        assert(self.tree1.db_nodes.has_key(leafnode.hash))
        assert(self.tree1.db_nodes[leafnode.hash] == leafnode) 

    def test_add_error_leaf_or_non_composite_w_child(self):
        """
        Confirm that the attempt to copy or move a node to a leaf node or
        non-composite node will return an error  string and fail to perform
        the copy or move operation
        """
        composite = CompositeNode("composite", self.tree1, self.tree1.root)
        leaf1 = LeafNode("leaf1", self.tree1, composite) 
        decorator = DecoratorNode("decorator", self.tree1, composite)
        leaf2 = LeafNode("leaf2", self.tree1, decorator)
        
        err = self.tree1.add(leaf1, leaf2)
        assert(isinstance(err, str) or isinstance(err, unicode))

        err = self.tree1.add(leaf1, decorator)
        assert(isinstance(err, str) or isinstance(err, unicode))

        err = self.tree1.add(leaf1, leaf2, copying=False)
        assert(isinstance(err, str) or isinstance(err, unicode))

        err = self.tree1.add(leaf1, decorator, copying=False)
        assert(isinstance(err, str) or isinstance(err, unicode))

        # check that there are still only 5 nodes in the registry,
        # including the root node
        assert(len(self.tree1.db_nodes.keys()) == 5)

        # check that leaf1 has not been moved
        assert(leaf1.parent == composite)
        assert(leaf1 in composite.children)

        # check that leaf1 remains in the registry
        assert(self.tree1.db_nodes.has_key(leaf1.hash))
        assert(self.tree1.db_nodes[leaf1.hash] == leaf1)

    def test_shift_same_node(self):
        """
        Test the operation of shifting a leaf node to its own position in the
        children list of its parent composite node.
        """
        composite = CompositeNode("composite", self.tree1, self.tree1.root) 
        leaf1 = LeafNode("leaf1", self.tree1, composite)
        leaf2 = LeafNode("leaf2", self.tree1, composite)

        # check that all nodes start out in the right positions
        assert(composite.children[0] == leaf1)
        assert(composite.children[1] == leaf2)

        err = self.tree1.shift(leaf1, position=0)
        assert(not err)
       
        # check that all nodes are in the same positions
        assert(composite.children[0] == leaf1)
        assert(composite.children[1] == leaf2)

    def test_shift_siblings(self):
        """
        Test the operation of shifting a leaf node from the second to the fourth
        position of its parent composite node's children list, as well as from
        the first to the last position of that children list.
        """
        composite = CompositeNode("composite", self.tree1, self.tree1.root)
        leaf1 = LeafNode("leaf1", self.tree1, composite)
        leaf2 = LeafNode("leaf2", self.tree1, composite)
        leaf3 = LeafNode("leaf3", self.tree1, composite)
        leaf4 = LeafNode("leaf4", self.tree1, composite)
        leaf5 = LeafNode("leaf5", self.tree1, composite)

        # check that all nodes start out in the right positions
        assert(composite.children[0] == leaf1)
        assert(composite.children[1] == leaf2)
        assert(composite.children[2] == leaf3)
        assert(composite.children[3] == leaf4)
        assert(composite.children[4] == leaf5)

        err = self.tree1.shift(leaf2, 4)
        assert(not err)        

        # check that leaf2 has been moved to the third position
        assert(composite.children[0] == leaf1)
        assert(composite.children[1] == leaf3)
        assert(composite.children[2] == leaf4)
        assert(composite.children[3] == leaf2)
        assert(composite.children[4] == leaf5)

        err = self.tree1.shift(leaf1)
        assert(not err)

        # check that leaf1 has been moved to the final position
        assert(composite.children[0] == leaf3)
        assert(composite.children[1] == leaf4)
        assert(composite.children[2] == leaf2)
        assert(composite.children[3] == leaf5)
        assert(composite.children[4] == leaf1)

    def test_shift_error_not_composite_node(self):
        """
        Confirm that the attempt to shift the child of a non-composite node
        returns an error string 
        """
        decorator = DecoratorNode("decorator", self.tree1, self.tree1.root)
        leafnode = LeafNode("leaf node", self.tree1, decorator)

        err = self.tree1.shift(leafnode)
        assert(isinstance(err, str) or isinstance(err, unicode))

        err = self.tree1.shift(self.tree1.root)
        assert(isinstance(err, str) or isinstance(err, unicode))

    def test_shift_error_not_node(self):
        """
        Confirm that the attempt to swap something that is not a node, or
        to swap a node with something that is not a node, returns an error
        message
        """
        err = self.tree1.shift(self.tree1)
        assert(isinstance(err, str) or isinstance(err, unicode))

    def test_swap_same_node(self):
        """
        Test the operation of swapping a node with itself, to ensure
        it is valid
        """
        leafnode = LeafNode("leaf node", self.tree1, self.tree1.root)
        
        self.tree1.swap(leafnode, leafnode)

        # check that there are still only two nodes in the registry,
        # including the root node
        assert(len(self.tree1.db_nodes.keys()) == 2)

        # check that the leaf node is present in the registry
        assert(self.tree1.db_nodes.has_key(leafnode.hash))
        assert(self.tree1.db_nodes[leafnode.hash] == leafnode)

    def test_swap_same_parent(self):
        """
        Test the operation of swapping two leaf nodes that have the same 
        composite node as their parent.
        """
        composite1 = CompositeNode("composite1", self.tree1, self.tree1.root)
        leaf1 = LeafNode("leaf1", self.tree1, composite1)
        leaf2 = LeafNode("leaf2", self.tree1, composite1)
        leaf3 = LeafNode("leaf3", self.tree1, composite1)

        # check that the children have been placed in the correct order
        assert(composite1.children[0] == leaf1)
        assert(composite1.children[1] == leaf2)
        assert(composite1.children[2] == leaf3)

        err = self.tree1.swap(leaf1, leaf3)
        assert(not err)

        # check that the two swapped nodes have switched places
        assert(composite1.children[0] == leaf3)
        assert(composite1.children[1] == leaf2)
        assert(composite1.children[2] == leaf1)

        # check that the swapped nodes are still in the registry 
        assert(self.tree1.db_nodes[leaf1.hash] == leaf1)
        assert(self.tree1.db_nodes[leaf3.hash] == leaf3)

    def test_swap_same_tree(self):
        """
        Test the operation of swapping two leaf nodes whose parents are
        composite nodes parented by the same composite node.

        This tests swapping between two nodes of the same tree and swapping
        between nodes whose parents are composite nodes.
        """
        composite1 = CompositeNode("composite1", self.tree1, self.tree1.root)
        composite2 = CompositeNode("composite2", self.tree1, composite1)
        composite3 = CompositeNode("composite3", self.tree1, composite1)
        leaf1 = LeafNode("leaf1", self.tree1, composite2)
        leaf2 = LeafNode("leaf2", self.tree1, composite3)

        # check that the parent-child relationships are correct
        assert(composite2.children[0] == leaf1)
        assert(composite3.children[0] == leaf2)
        assert(leaf1.parent == composite2)
        assert(leaf2.parent == composite3)

        err = self.tree1.swap(leaf1, leaf2)
        assert(not err)

        # check that the new parent-child relationships have been established
        assert(composite2.children[0] == leaf2)
        assert(composite3.children[0] == leaf1)
        assert(leaf2.parent == composite2)
        assert(leaf1.parent == composite3)

        # check that the swapped nodes are still in the registry
        assert(self.tree1.db_nodes[leaf1.hash] == leaf1)
        assert(self.tree1.db_nodes[leaf2.hash] == leaf2)

    def test_swap_other_tree(self):
        """
        Test the operation of swapping two leaf nodes whose parents are the root
        nodes of two different trees.

        This tests both swapping between two trees and swapping when the parents
        are both non-composite nodes.
        """
        leaf1 = LeafNode("leaf1", self.tree1, self.tree1.root)
        leaf2 = LeafNode("leaf2", self.tree2, self.tree2.root)

        assert(self.tree1.root.children == leaf1)
        assert(self.tree2.root.children == leaf2)        

        err = self.tree1.swap(leaf2, leaf1, source_tree=self.tree2)
        assert(not err)

        # check that the nodes have been swapped
        assert(self.tree1.root.children == leaf2)
        assert(self.tree2.root.children == leaf1)
        assert(leaf2.parent == self.tree1.root)        
        assert(leaf1.parent == self.tree2.root)

        # check that each tree's registry has only two nodes, including
        # the root node
        assert(len(self.tree1.db_nodes.keys()) == 2)
        assert(len(self.tree2.db_nodes.keys()) == 2)

        # check that the nodes are present in their trees' registries
        assert(self.tree1.db_nodes.has_key(leaf2.hash))
        assert(self.tree2.db_nodes.has_key(leaf1.hash))
        assert(self.tree1.db_nodes[leaf2.hash] == leaf2)
        assert(self.tree2.db_nodes[leaf1.hash] == leaf1)

        # swap the nodes again
        err = self.tree2.swap(leaf2, leaf1, source_tree=self.tree1)
        
        # check that the nodes have been swapped
        assert(self.tree1.root.children == leaf1)
        assert(self.tree2.root.children == leaf2)
        assert(leaf1.parent == self.tree1.root)
        assert(leaf2.parent == self.tree2.root)

        # check that the nodes are present in their trees' registries
        assert(self.tree1.db_nodes.has_key(leaf1.hash))
        assert(self.tree2.db_nodes.has_key(leaf2.hash))
        assert(self.tree1.db_nodes[leaf1.hash] == leaf1)
        assert(self.tree2.db_nodes[leaf2.hash] == leaf2)

    def test_swap_error_not_node(self):
        """
        Confirm that the attempt to swap something that is not a node, or
        to swap a node with something that is not a node, returns an error
        message and does not perform any swapping operation
        """
        leafnode = LeafNode("leaf node", self.tree1, self.tree1.root)

        err = self.tree1.swap(self.tree1, self.tree2.root)
        assert(isinstance(err, str) or isinstance(err, unicode))
        
        err = self.tree1.swap(leafnode, self.tree2)
        assert(isinstance(err, str) or isinstance(err, unicode)) 
         
        # check that tree1 and tree2 have 2 and 1 nodes in their registries
        # respectively
        assert(len(self.tree1.db_nodes.keys()) == 2)
        assert(len(self.tree2.db_nodes.keys()) == 1)

        # check that leafnode is still in the registry of tree1
        assert(self.tree1.db_nodes.has_key(leafnode.hash))
        assert(self.tree1.db_nodes[leafnode.hash] == leafnode)

    def test_swap_error_root_node(self):
        """
        Confirm that the attempt to swap a root node with another node,
        or a node with a root node, returns an error string and does
        not perform the swap
        """
        root1 = self.tree1.root
        root2 = self.tree2.root
        leaf1 = LeafNode("leaf1", self.tree1, root1)
        leaf2 = LeafNode("leaf2", self.tree2, root2)    

        err = self.tree1.swap(root1, leaf2)
        assert(isinstance(err, str) or isinstance(err, unicode))
        err = self.tree1.swap(leaf1, root2)
        assert(isinstance(err, str) or isinstance(err, unicode))       

        # check that the swap has not been performed
        assert(root1 == self.tree1.root)
        assert(root2 == self.tree2.root)

        # check that the leaf nodes have not been moved
        assert(self.tree1.db_nodes.has_key(leaf1.hash))
        assert(self.tree1.db_nodes[leaf1.hash] == leaf1)
        assert(self.tree2.db_nodes.has_key(leaf2.hash))
        assert(self.tree2.db_nodes[leaf2.hash] == leaf2)

    def test_interpose_same_tree(self):
        """
        Test the operation of copy-interposing and move-interposing a node
        to a different, non-composite node in the same tree.
        """
        composite = CompositeNode("composite", self.tree1, self.tree1.root)
        decorator1 = DecoratorNode("decorator1", self.tree1, composite)
        decorator2 = DecoratorNode("decorator2", self.tree1, composite)
        old_hashval = decorator1.hash
        hashes = self.tree1.db_nodes.keys()

        err = self.tree1.interpose(decorator1, decorator2)
        assert(not err)

        new_hashval = [x for x in self.tree1.db_nodes.keys() if
                       x not in hashes]
        assert(new_hashval) # copied decorator node is in tree1's registry
        new_hashval = new_hashval[0]
        decorator3 = self.tree1.db_nodes[new_hashval]

        # check that there are now 5 nodes in the registry
        assert(len(self.tree1.db_nodes.keys()) == 5)

        # check that decorator1 has not been moved
        assert(decorator1 in composite.children)
        assert(decorator1.parent == composite)

        # check that decorator1 is still in the registry
        assert(self.tree1.db_nodes.has_key(old_hashval))
        assert(self.tree1.db_nodes[old_hashval] == decorator1)

        # check that the new parent-child relationships for decorator3 have
        # been established
        assert(decorator3 in composite.children)
        assert(decorator3.parent == composite)
        assert(decorator3.children == decorator2)
        assert(decorator2.parent == decorator3)

        err = self.tree1.interpose(decorator1, decorator2, copying=False)
        assert(not err)

        # check that there are still 5 nodes in the registry
        assert(len(self.tree1.db_nodes.keys()) == 5)
        
        # check that the new parent-child relationships for decorator1 have
        # been established
        assert(decorator3.children == decorator1)
        assert(decorator1.parent == decorator3)
        assert(decorator1.children == decorator2)
        assert(decorator2.parent == decorator1)

        # check that the old parent-child relationship for decorator1 has been
        # terminated
        assert(decorator1 not in composite.children)

        # check that decorator1 is still in the registry
        assert(self.tree1.db_nodes.has_key(old_hashval))
        assert(self.tree1.db_nodes[old_hashval] == decorator1)

    def test_interpose_composite_node(self):
        """
        Test the operation of copy-interposing and move-interposing a
        composite node onto a target node in the same tree, placing that
        target node in a specific position in the composite node's list of
        children.
        """
        composite1 = CompositeNode("composite1", self.tree1, self.tree1.root)
        composite2 = CompositeNode("composite2", self.tree1, composite1)
        leaf1 = LeafNode("leaf1", self.tree1, composite1)
        leaf2 = LeafNode("leaf2", self.tree1, composite1)
        leaf3 = LeafNode("leaf3", self.tree1, composite2)
        leaf4 = LeafNode("leaf4", self.tree1, composite2)
        leaf5 = LeafNode("leaf5", self.tree1, composite2)
        hashes = self.tree1.db_nodes.keys()

        err = self.tree1.interpose(composite2, leaf1, position=1)
        assert(not err)

        # check that there are now 12 nodes in the tree's registry
        assert(len(self.tree1.db_nodes.keys()) == 12)

        # get the new composite node
        new_hashval = [x for x in self.tree1.db_nodes.keys() if
                       self.tree1.db_nodes[x].name == "composite2" 
                       and x not in hashes]
        assert(new_hashval) # copied composite node is in tree1's registry
        new_hashval = new_hashval[0]
        composite3 = self.tree1.db_nodes[new_hashval]

        # check that leaf1 is in the appropriate position in composite3's
        # list of children
        assert(composite3.children[1] == leaf1)
        assert(leaf1.parent == composite3)        

        err = self.tree1.interpose(composite2, leaf2, position=None, 
            copying=False)

        # check that there are still 12 nodes in the tree's registry
        assert(len(self.tree1.db_nodes.keys()) == 12)

        # check that leaf2 is in the appropriate position in composite3's
        # list of children
        assert(composite2.children[3] == leaf2)
        assert(leaf2.parent == composite2)

    def test_interpose_other_tree(self):
        """
        Test the operation of copy-interposing and move-interposing a
        node from one tree to another.
        """
        decorator1 = DecoratorNode("decorator1", self.tree1, self.tree1.root)
        decorator2 = DecoratorNode("decorator2", self.tree2, self.tree2.root)
        old_hashval = decorator1.hash
        hashes = self.tree2.db_nodes.keys()

        err = self.tree2.interpose(decorator1, decorator2,
            source_tree=self.tree1)
        assert(not err)

        # check that there are now 3 nodes in tree2 and 2 nodes in tree1
        assert(len(self.tree1.db_nodes.keys()) == 2)
        assert(len(self.tree2.db_nodes.keys()) == 3)

        # get the new decorator
        new_hashval = [x for x in self.tree2.db_nodes.keys() if
                       x not in hashes]
        assert(new_hashval)
        new_hashval = new_hashval[0]
        decorator3 = self.tree2.db_nodes[new_hashval]

        # check that the parent-child relationships of decorator3 have been
        # established
        assert(self.tree2.root.children == decorator3)
        assert(decorator3.parent == self.tree2.root)
        assert(decorator3.children == decorator2)
        assert(decorator2.parent == decorator3)

        err = self.tree2.interpose(decorator1, decorator2, copying=False,
            source_tree=self.tree1)
        assert(not err)

        # check that there are now 4 nodes in tree2 and 1 node in tree1
        assert(len(self.tree1.db_nodes.keys()) == 1)
        assert(len(self.tree2.db_nodes.keys()) == 4)

        # check that decorator1 has been added to the registry of tree2
        assert(self.tree2.db_nodes.has_key(decorator1.hash))
        assert(self.tree2.db_nodes[decorator1.hash] == decorator1)
       
        # check that the parent-child relationships of decorator1 have been
        # established
        assert(decorator3.children == decorator1)
        assert(decorator1.parent == decorator3)
        assert(decorator1.children == decorator2)
        assert(decorator2.parent == decorator1)

    def test_interpose_error_not_node(self):
        """
        Confirm that the attempt to copy-interpose or move-interpose something
        that is not a node, or to copy-interpose or move-interpose a node to
        something that is not a node, returns an error message and does not
        perform any copying or moving operation
        """
        leafnode = LeafNode("leaf node", self.tree1, self.tree1.root)
        decorator = DecoratorNode("decorator", self.tree2, self.tree2.root)

        err = self.tree1.interpose(self.tree1, decorator)
        assert(isinstance(err, str) or isinstance(err, unicode))
        
        err = self.tree1.interpose(leafnode, self.tree2)
        assert(isinstance(err, str) or isinstance(err, unicode)) 
         
        # check that tree1 and tree2 each have 2 nodes in their registries
        assert(len(self.tree1.db_nodes.keys()) == 2)
        assert(len(self.tree2.db_nodes.keys()) == 2)

        # check that leafnode is still in the registry of tree1
        assert(self.tree1.db_nodes.has_key(leafnode.hash))
        assert(self.tree1.db_nodes[leafnode.hash] == leafnode)

    def test_interpose_error_same_node(self):
        """
        Confirm that the attempt to interpose a node onto itself returns
        an error string and does not perform the interposition operation.
        """
        decorator = DecoratorNode("decorator", self.tree1, self.tree1.root)
        hashval = decorator.hash        

        err = self.tree1.interpose(decorator, decorator, copying=False)
        assert(isinstance(err, str) or isinstance(err, unicode))
        
        err = self.tree1.interpose(decorator, decorator)
        assert(isinstance(err, str) or isinstance(err, unicode))

        # check that there are still 2 nodes in the registry
        assert(len(self.tree1.db_nodes.keys()) == 2) 
        
        # check that the decorator node has not been moved
        assert(self.tree1.db_nodes.has_key(hashval))
        assert(self.tree1.db_nodes[hashval] == decorator)

    def test_interpose_error_root_node(self):
        """
        Confirm that the attempt to interpose a root node onto another
        node, or a node onto a root node, returns an error string and
        does not perform the interposition.
        """
        decorator = DecoratorNode("decorator1", self.tree1, self.tree1.root)

        err = self.tree1.interpose(self.tree1.root, decorator)
        assert(isinstance(err, str) or isinstance(err, unicode))
       
        err = self.tree1.interpose(decorator, self.tree2.root)
        assert(isinstance(err, str) or isinstance(err, unicode))

        # check that there are still only two nodes in the registry
        assert(len(self.tree1.db_nodes.keys()) == 2)

        # check that the parent-child relationships of the two nodes in the
        # registry have not changed
        assert(self.tree1.root.children == decorator)
        assert(self.tree1.root.parent == None)
        assert(decorator.children == None)
        assert(decorator.parent == self.tree1.root)

class TestFunctionality(TestCase):
    pass



#class TestNavigation(CommandTest):






#class TestModification(CommandTest):






