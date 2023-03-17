from evennia import create_object
from evennia.utils.test_resources import BaseEvenniaTest, BaseEvenniaCommandTest  # noqa
from .containers import ContribContainer, CmdContainerGet, CmdContainerLook, CmdPut


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

    def test_get_and_put(self):
        # get normally
        self.call(CmdContainerGet(), "Obj", "You pick up an Obj.")
        # put in the container
        self.call(CmdPut(), "obj in box", "You put an Obj in a Box.")
        # get from the container
        self.call(CmdContainerGet(), "obj from box", "You get an Obj from a Box.")
