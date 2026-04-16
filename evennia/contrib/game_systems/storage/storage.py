from evennia import CmdSet
from evennia.commands.default.muxcommand import MuxCommand
from evennia.utils import list_to_string
from evennia.utils.search import search_object_by_tag

SHARED_TAG_PREFIX = "shared"


class StorageCommand(MuxCommand):
    """
    Shared functionality for storage-related commands
    """

    def at_pre_cmd(self):
        """
        Check if the current location is tagged as a storage location
        Every stored object is tagged on storage, and untagged on retrieval

        Returns:
            bool: True if the command is to be stopped here
        """
        if super().at_pre_cmd():
            return True

        self.storage_location_id = self.caller.location.tags.get(category="storage_location")
        if not self.storage_location_id:
            self.caller.msg(f"You cannot {self.cmdstring} anything here.")
            return True

        self.object_tag = (
            SHARED_TAG_PREFIX
            if self.storage_location_id.startswith(SHARED_TAG_PREFIX)
            else self.caller.pk
        )
        self.currently_stored = search_object_by_tag(
            self.object_tag, category=self.storage_location_id
        )


class CmdStore(StorageCommand):
    """
    Store something in a storage location.

    Usage:
      store <obj>
    """

    key = "store"
    locks = "cmd:all()"
    help_category = "Storage"

    def func(self):
        """
        Find the item in question to store, then store it
        """
        caller = self.caller
        if not self.args:
            self.caller.msg("Store what?")
            return
        obj = caller.search(self.args.strip(), candidates=caller.contents)
        if not obj:
            return

        """
        We first check at_pre_move before setting the location to None, in case
        anything should stymie its movement.
        """
        if obj.at_pre_move(caller.location):
            obj.tags.add(self.object_tag, self.storage_location_id)
            obj.location = None
            caller.msg(f"You store {obj.get_display_name(caller)} here.")
        else:
            caller.msg(f"You fail to store {obj.get_display_name(caller)} here.")


class CmdRetrieve(StorageCommand):
    """
    Retrieve something from a storage location.

    Usage:
      retrieve <obj>
    """

    key = "retrieve"
    locks = "cmd:all()"
    help_category = "Storage"

    def func(self):
        """
        Retrieve the item in question if possible
        """
        caller = self.caller

        if not self.args:
            self.caller.msg("Retrieve what?")
            return

        obj = caller.search(self.args.strip(), candidates=self.currently_stored)
        if not obj:
            return

        if obj.at_pre_move(caller):
            obj.tags.remove(self.object_tag, self.storage_location_id)
            caller.msg(f"You retrieve {obj.get_display_name(caller)}.")
        else:
            caller.msg(f"You fail to retrieve {obj.get_display_name(caller)}.")


class CmdList(StorageCommand):
    """
    List items in the storage location.

    Usage:
      list
    """

    key = "list"
    locks = "cmd:all()"
    help_category = "Storage"

    def func(self):
        """
        List items in the storage
        """
        caller = self.caller
        if not self.currently_stored:
            caller.msg("You find nothing stored here.")
            return
        caller.msg(f"Stored here:\n{list_to_string(self.currently_stored)}")


class CmdStorage(MuxCommand):
    """
    Make the current location a storage room, or delete it as a storage and move all stored objects into the room contents.

    Shared storage locations can be used by all interchangeably.

    The default storage identifier will be its primary key in the database, but you can supply a new one in case you want linked storages.

    Usage:
      storage [= [storage identifier]]
      storage/shared [= [storage identifier]]
      storage/delete
    """

    key = "@storage"
    locks = "cmd:perm(Builder)"

    def func(self):
        """Set the storage location."""

        caller = self.caller
        location = caller.location
        current_storage_id = location.tags.get(category="storage_location")
        storage_id = self.lhs or location.pk

        if "delete" in self.switches:
            if not current_storage_id:
                caller.msg("This is not tagged as a storage location.")
                return
            # Move the stored objects, if any, into the room
            currently_stored_here = search_object_by_tag(category=current_storage_id)
            for obj in currently_stored_here:
                obj.tags.remove(category=current_storage_id)
                obj.location = location
            caller.msg("You remove the storage capabilities of the room.")
            location.tags.remove(current_storage_id, category="storage_location")
            return

        if current_storage_id:
            caller.msg("This is already a storage location: |wstorage/delete|n to remove the tag.")
            return

        new_storage_id = (
            f"{SHARED_TAG_PREFIX if SHARED_TAG_PREFIX in self.switches else ''}{storage_id}"
        )
        location.tags.add(new_storage_id, category="storage_location")
        caller.msg(f"This is now a storage location with id: {new_storage_id}.")


class StorageCmdSet(CmdSet):
    """
    CmdSet for all storage-related commands
    """

    def at_cmdset_creation(self):
        self.add(CmdStore)
        self.add(CmdRetrieve)
        self.add(CmdList)
        self.add(CmdStorage)
