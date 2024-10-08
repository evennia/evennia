from evennia.commands.default.tests import BaseEvenniaCommandTest
from evennia.utils.create import create_object

from . import storage


class TestStorage(BaseEvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.obj1.location = self.char1
        self.room1.tags.add("storage_1", "storage_location")
        self.room2.tags.add("shared_storage_2", "storage_location")

    def test_store_and_retrieve(self):
        self.call(
            storage.CmdStore(),
            "",
            "Store what?",
            caller=self.char1,
        )
        self.call(
            storage.CmdStore(),
            "obj",
            f"You store {self.obj1.get_display_name(self.char1)} here.",
            caller=self.char1,
        )
        self.call(
            storage.CmdList(),
            "",
            f"Stored here:\n{self.obj1.get_display_name(self.char1)}",
            caller=self.char1,
        )
        self.call(
            storage.CmdRetrieve(),
            "obj2",
            "Could not find 'obj2'.",
            caller=self.char1,
        )
        self.call(
            storage.CmdRetrieve(),
            "obj",
            f"You retrieve {self.obj1.get_display_name(self.char1)}.",
            caller=self.char1,
        )

    def test_store_retrieve_while_not_in_storeroom(self):
        self.char2.location = self.char1
        self.call(storage.CmdStore(), "obj", "You cannot store anything here.", caller=self.char2)
        self.call(
            storage.CmdRetrieve(), "obj", "You cannot retrieve anything here.", caller=self.char2
        )

    def test_store_retrieve_nonexistent_obj(self):
        self.call(storage.CmdStore(), "asdasd", "Could not find 'asdasd'.", caller=self.char1)
        self.call(storage.CmdRetrieve(), "asdasd", "Could not find 'asdasd'.", caller=self.char1)

    def test_list_nothing_stored(self):
        self.call(
            storage.CmdList(),
            "",
            "You find nothing stored here.",
            caller=self.char1,
        )

    def test_shared_storage(self):
        self.char1.location = self.room2
        self.char2.location = self.room2

        self.call(
            storage.CmdStore(),
            "obj",
            f"You store {self.obj1.get_display_name(self.char1)} here.",
            caller=self.char1,
        )
        self.call(
            storage.CmdRetrieve(),
            "obj",
            f"You retrieve {self.obj1.get_display_name(self.char1)}.",
            caller=self.char2,
        )

    def test_remove_add_storage(self):
        self.char1.permissions.add("builder")
        self.call(
            storage.CmdStorage(),
            "",
            "This is already a storage location: storage/delete to remove the tag.",
            caller=self.char1,
        )
        self.call(
            storage.CmdStore(),
            "obj",
            f"You store {self.obj1.get_display_name(self.char1)} here.",
            caller=self.char1,
        )
        self.assertEqual(self.obj1.location, None)
        self.call(
            storage.CmdStorage(),
            "/delete",
            "You remove the storage capabilities of the room.",
            caller=self.char1,
        )
        self.assertEqual(self.obj1.location, self.room1)
        self.call(
            storage.CmdStorage(),
            "",
            f"This is now a storage location with id: {self.room1.id}.",
            caller=self.char1,
        )
        self.call(
            storage.CmdStorage(),
            "/delete",
            "You remove the storage capabilities of the room.",
            caller=self.char1,
        )
        self.call(
            storage.CmdStorage(),
            "/shared",
            f"This is now a storage location with id: shared{self.room1.id}.",
            caller=self.char1,
        )
