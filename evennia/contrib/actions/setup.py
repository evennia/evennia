from evennia import ObjectDB
from evennia.contrib.actions.typeclasses import ActionCharacter, ActionRoom

def setup(override=False):
    """
    loads the action system on all rooms and characters

    only to be used in case of accidents, as all rooms and characters already
    have the handlers as properties and set them up when initialized
    """
    for obj in ObjectDB.objects.all():
        if isinstance(obj, ActionCharacter):
            # add the actions list to the character
            obj.actions.setup(override=override)

        elif isinstance(obj, ActionRoom):
            # add the actions list to the room
            obj.actions.setup(override=override)


