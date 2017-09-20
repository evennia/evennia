from evennia.utils.test_resources import EvenniaTest
from evennia.objects.objects import DefaultObject
from evennia.server.serversession import ServerSession
from evennia.server.sessionhandler import SESSIONS
from evennia.utils import create
from evennia.utils.idmapper.models import flush_cache
from evennia.utils.utils import lazy_property
from sr5.utils import *


class ContribSHSlottedObject(DefaultObject):
    """
    This is a test object for SlotsHandler tests. All typeclassed objects
    *should* play nicely with SlotsHandler.
    """

    @lazy_property
    def slots(self):
        return SlotsHandler(self)


class ContribSHSlottableObjectOne(DefaultObject):
    """
    This is a test object for SlotsHandler tests. All typeclassed objects
    *should* play nicely with SlotsHandler.
    """

    def at_object_creation(self):
        self.db.slots = {"addons": ["left"]}


class ContribSHSlottableObjectTwo(DefaultObject):
    """
    This is a test object for SlotsHandler tests. All typeclassed objects
    *should* play nicely with SlotsHandler.
    """

    def at_object_creation(self):
        self.db.slots = {"addons": [1, "right"]}


class ContribSHSlottableObjectThree(DefaultObject):
    """
    This is a test object for SlotsHandler tests. All typeclassed objects
    *should* play nicely with SlotsHandler.
    """

    def at_object_creation(self):
        self.db.slots = {"addons": ["left"]}


class TestSlotsHandler(EvenniaTest):
    "Test the class SlotsHandler."

    def setUp(self):
        super(TestSlotsHandler, self).setUp()
        self.obj = create.create_object(ContribSHSlottedObject,
                                        key="slotted",
                                        location=self.room1, home=self.room1)
        self.slo1 = create.create_object(ContribSHSlottableObjectOne,
                                         key="item 1",
                                         location=self.obj, home=self.obj)
        self.slo2 = create.create_object(ContribSHSlottableObjectTwo,
                                         key="item 2",
                                         location=self.obj, home=self.obj)
        self.slo3 = create.create_object(ContribSHSlottableObjectThree,
                                         key="item 3",
                                         location=self.obj, home=self.obj)

    def test_add(self):
        add = self.obj.slots.add({"addons": ["left", "right"]})
        self.assertTrue(add)

        with self.assertRaises(ValueError):
            add = self.obj.slots.add({"add-ons": ["left", "right"]})

        self.obj.slots.add({"addons": [3, "y"]})
        self.assertEqual(self.obj.attributes.get("addons", category="slots"),
                         {1: "", 2: "", 3: "",
                         "left": "", "right": "", "y": ""})

    def test_delete(self):
        self.test_add()

        delete = self.obj.slots.delete({"addons": [1, "right"]})
        self.assertIsInstance(delete, dict)
        self.assertEqual(self.obj.attributes.get("addons", category="slots"),
                         {1: "", 2: "", "left": "", "y": ""})

    def test_attach(self):
        # When no slots have been added first.
        attach = self.obj.slots.attach(self.slo1)
        self.assertIsInstance(attach, StatMsg)

        # Add the slots.
        self.test_add()

        # Successful attachment.
        attach = self.obj.slots.attach(self.slo1)
        self.assertEqual(attach, {"addons": {"left": self.slo1}})

        # What does the attribute look like?
        real = self.obj.attributes.get("addons", category="slots")
        expected = {1: "", 2: "", 3: "",
                    "left": self.slo1, "right": "", "y": ""}
        self.assertEqual(expected, real)

        # Successful attachment in multiple slots.
        attach = self.obj.slots.attach(self.slo2)
        expected = {"addons": {1: self.slo2, "right": self.slo2}}
        self.assertEqual(attach, expected)

        # Failed attachment because the slot is occupied.
        attach = self.obj.slots.attach(self.slo3)
        self.assertIsInstance(attach, StatMsg)

        # Successful attachment while overriding slots.
        attach = self.obj.slots.attach(self.slo3, {"addons": [2, "y"]})
        expected = {"addons": {2: self.slo3, 3: self.slo3, "y": self.slo3}}
        self.assertEqual(attach, expected)

    def test_attach_extended(self):
        self.test_attach()

        # Attach to all open slots in category
        drop = self.obj.slots.drop(self.slo2, {"addons": ["right"]})
        attach = self.obj.slots.attach(self.slo1, ["addons"])
        self.assertEqual(attach, {"addons": {"right": self.slo1}})

        # Check the end result.
        real = self.obj.attributes.get("addons", category="slots")
        expected = {1: self.slo2, 2: self.slo3, 3: self.slo3,
                    "left": self.slo1, "right": self.slo1, "y": self.slo3}
        self.assertEqual(real, expected)

    def test_drop(self):
        self.test_attach()

        # Drop a specific object from all slots.
        drop = self.obj.slots.drop(self.slo3)
        expected = {"addons": {2: self.slo3, 3: self.slo3,
                    "y": self.slo3}}
        self.assertEqual(drop, expected)

        # Drop a specific object from specific slots.
        attach = self.obj.slots.attach(self.slo2, {"addons": [2]})
        drop = self.obj.slots.drop(self.slo2, {"addons": [1, "right"]})
        self.assertEqual(self.obj.slots.where(self.slo2),
                         {"addons": [1, 2]})

        # Try to drop an object with improper input.
        drop = self.obj.slots.drop(self.slo3, "not here")
        self.assertIsInstance(drop, StatMsg)

        # Drop any objects from specific slots.
        drop = self.obj.slots.drop(None, {"addons": ["left"]})
        self.assertEqual(drop, {"addons": {"left": self.slo1}})

    def test_replace(self):
        self.test_attach()

        # Try to replace the contents of a specific slot.
        drop, attach = self.obj.slots.replace(self.slo1, {"addons": ["y"]})
        self.assertEqual(drop, {"addons": {"y": self.slo3}})
        self.assertEqual(attach, {"addons": {"y": self.slo1}})

        # Try to replace the contents of all slots.
        self.obj.slots.replace(self.slo2, ["addons"])
        where = self.obj.slots.where(self.slo2)
        where = {"addons": {n: self.slo2 for n in where['addons']}}
        self.assertEqual(where, self.obj.slots.all())

    def test_defrag(self):
        self.test_add()

        # Set up a situation where there are non-contiguous numbered slots.
        attach_1 = self.obj.slots.attach(self.slo1, {"addons": [1]})
        attach_2 = self.obj.slots.attach(self.slo2, {"addons": [1]})
        drop = self.obj.slots.drop(self.slo1)

        self.obj.slots.defrag_nums("addons")
        self.assertEqual(self.obj.slots.where(self.slo2),
                         {"addons": [1]})

    def test_where(self):
        self.test_attach()

        self.assertEqual(self.obj.slots.where(self.slo2),
                         {"addons": [1, "right"]})

        self.obj.slots.drop(self.slo2)
        self.assertEqual(self.obj.slots.where(self.slo2),
                         {})

    def tearDown(self):
        flush_cache()
        self.obj.delete()
        self.slo1.delete()
        self.slo2.delete()
        self.slo3.delete()
        super(TestSlotsHandler, self).tearDown()
