from evennia import create_object
from evennia.utils.test_resources import BaseEvenniaCommandTest  # noqa
from evennia.utils.test_resources import BaseEvenniaTest

from .containers import CmdContainerGet, CmdContainerLook, CmdPut, ContribContainer


class TestContainer(BaseEvenniaTest):
    def setUp(self):
        super().setUp()
        # create a container to test with
        self.container = create_object(key="Box", typeclass=ContribContainer, location=self.room1)

    def test_capacity(self):
        # limit capacity to 1
        self.container.capacity = 1
        self.assertTrue(self.container.at_pre_put_in(self.char1, self.obj1))
        # put Obj2 in container to hit max capacity
        self.obj2.location = self.container
        self.assertFalse(self.container.at_pre_put_in(self.char1, self.obj1))


class TestContainerCmds(BaseEvenniaCommandTest):
    def setUp(self):
        super().setUp()
        # create a container to test with
        self.container = create_object(key="Box", typeclass=ContribContainer, location=self.room1)

    def test_look_in(self):
        # make sure the object is in the container so we can look at it
        self.obj1.location = self.container
        self.call(CmdContainerLook(), "obj in box", "Obj")
        # move it into a non-container object and look at it there too
        self.obj1.location = self.obj2
        self.call(CmdContainerLook(), "obj in obj2", "Obj")
        # make sure normal looking works too
        self.call(CmdContainerLook(), "obj2", "Obj2")
        self.call(CmdContainerLook(), "", "Room")

    def test_get_and_put(self):
        # get normally
        self.call(CmdContainerGet(), "Obj", "You pick up an Obj.")
        # put in the container
        self.call(
            CmdPut(),
            "obj in box",
            "You put an Obj in a Box.",
        )
        # get from the container
        self.call(
            CmdContainerGet(),
            "obj from box",
            "You get an Obj from a Box.",
        )

    def test_locked_get_put(self):
        # lock container
        self.container.locks.add("get_from:false()")
        # move object to container to try getting
        self.obj1.location = self.container
        self.call(CmdContainerGet(), "obj from box", "You can't get things from that.")
        # move object to character to try putting
        self.obj1.location = self.char1
        self.call(CmdPut(), "obj in box", "You can't put things in that.")

    def test_at_capacity_put(self):
        # set container capacity
        self.container.capacity = 1
        # move object to container to fill capacity
        self.obj2.location = self.container
        # move object to character to try putting
        self.obj1.location = self.char1
        self.call(CmdPut(), "obj in box", "You can't fit anything else in a Box.")
