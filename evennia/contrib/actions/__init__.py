from evennia import ObjectDB, DefaultCharacter, DefaultRoom
from evennia.contrib.actions.actions import Action
from evennia.contrib.actions.handlers import CharacterActionHandler, RoomActionHandler
from evennia.contrib.actions.scripts import ActionSystemScript
from evennia.contrib.actions.typeclasses import ActionCharacter, ActionRoom, ActionExit
from evennia.contrib.actions.commands import ActionCmdSet 
from evennia.contrib.actions.debug import ActionDebugCmdSet
from evennia.contrib.actions.setup import setup

__all__ = [Action, ActionCharacter, ActionRoom, ActionExit, ActionCmdSet, 
    ActionDebugCmdSet, setup]


def setup(override=False):
    """
    loads the action system on all rooms and characters

    only to be used in case of accidents, as all rooms and characters already
    have the handlers as properties and set them up when initialized
    """
    for obj in ObjectDB.objects.all():
        if isinstance(obj, DefaultCharacter):
            # add the actions list to the character
            if not hasattr(obj, "actions") or override:
                obj.actions = CharacterActionHandler(obj)
                obj.actions.setup(override=override)

        elif isinstance(obj, DefaultRoom):
            # add the actions list to the room
            if not hasattr(obj, "actions") or override:
                obj.actions = RoomActionHandler(obj)
                obj.actions.setup(override=override)

            # add the action system script to the room
            l = [x for x in obj.scripts.all() 
                 if type(x) == ActionSystemScript]
            if override:
                for x in l:
                    obj.scripts.delete(x)
                obj.scripts.add(ActionSystemScript)
            if not l:
                obj.scripts.add(ActionSystemScript)

