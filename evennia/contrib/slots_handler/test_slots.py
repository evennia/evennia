from evennia.utils.test_resources import EvenniaTest
from evennia.objects.objects import DefaultObject
from evennia.server.serversession import ServerSession
from evennia.server.sessionhandler import SESSIONS
from evennia.utils import create
from evennia.utils.idmapper.models import flush_cache
from evennia.utils.utils import lazy_property
from sr5.utils import *

class SlottedObject(DefaultObject):
    """
    This is a test object for SlotsHandler tests. All typeclassed objects
    *should* play nicely with SlotsHandler.
    """

    @lazy_property
    def slots(self):
        return SlotsHandler(self)

class SlottableObjectOne(DefaultObject):
    """
    This is a test object for SlotsHandler tests. All typeclassed objects
    *should* play nicely with SlotsHandler.
    """

    def at_object_creation(self):
        self.slots = {"addons": ["left"]}

class SlottableObjectTwo(DefaultObject):
    """
    This is a test object for SlotsHandler tests. All typeclassed objects
    *should* play nicely with SlotsHandler.
    """

    def at_object_creation(self):
        self.slots = {"addons": [1, "right"]}

class SlottableObjectThree(DefaultObject):
    """
    This is a test object for SlotsHandler tests. All typeclassed objects
    *should* play nicely with SlotsHandler.
    """

    def at_object_creation(self):
        self.slots = {"addons": ["left"]}

class TestSlotsHandler(EvenniaTest):
    "Test the class SlotsHandler."

    def setUp(self):
        super(TestSlotsHandler, self).setUp()
        self.obj = create.create_object(SlottedObject, key="slotted",
                                        location=self.room1, home=self.room1)
        self.slo1 = create.create_object(SlottableObjectOne, key="item 1",
                                         location=self.obj, home=self.obj)
        self.slo2 = create.create_object(SlottableObjectTwo, key="item 2",
                                         location=self.obj, home=self.obj)
        self.slo3 = create.create_object(SlottableObjectThree, key="item 3",
                                         location=self.obj, home=self.obj)

    def test_add(self):
        add = self.obj.slots.add("addons", 0, ["left", "right"])
        self.assertTrue(add)

        with self.assertRaises(ValueError):
            add = self.obj.slots.add("add-ons", 0, ["left", "right"])

        self.obj.slots.add("addons", 2)
        self.assertEqual(self.obj.attributes.get("addons", category="slots"),
                         {1: "", 2: "", "left": "", "right": ""})

    def test_delete(self):
        add = self.obj.slots.add("addons", 2, ["left", "right"])

        delete = self.obj.slots.delete("addons", 1, ["right"])
        self.assertIsInstance(delete, dict)
        self.assertEqual(self.obj.attributes.get("addons", category="slots"),
                         {1: "", "left": ""})

    def test_attach(self):
        # When no slots have been added first.
        attach = self.obj.slots.attach(self.slo1)
        self.assertIsInstance(attach, StatMsg)

        # Add the slots.
        add = self.obj.slots.add("addons", 2, ["left", "right"])

        # Successful attachment.
        attach = self.obj.slots.attach(self.slo1)
        expected = {"addons": {"left": self.slo1}}
        self.assertEqual(attach, expected)

        # Successful attachment in multiple slots.
        attach = self.obj.slots.attach(self.slo2)
        expected = {"addons": {1: self.slo2, "right": self.slo2}}
        self.assertEqual(attach, expected)

        # Failed attachment because the slot is occupied.
        attach = self.obj.slots.attach(self.slo3)
        self.assertIsInstance(attach, StatMsg)

        # Successful attachment while overriding slots.
        attach = self.obj.slots.attach(self.slo3, {"addons": [1]})
        expected = {"addons": {2: self.slo3}}
        self.assertEqual(attach, expected)

    def test_drop(self):
        self.test_attach()

        drop = self.obj.slots.drop(self.slo3)
        expected = {"addons": [2]}
        self.assertEqual(drop, expected)

        drop = self.obj.slots.drop(self.slo2, {"addons": ["right"]})
        expected = {"addons": ["right"]}
        self.assertEqual(drop, expected)
        self.assertEqual(self.obj.slots.where(self.slo2),
                         {"addons": [1]})

        drop = self.obj.slots.drop(self.slo3, "not here")
        self.assertIsInstance(drop, StatMsg)

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
