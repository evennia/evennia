"""
Contains the typeclasses ActionCharacter, ActionRoom and ActionExit, which all
characters, rooms and exits in a given game should subclass if they are to be
part of the action system. If any room or exit does not subclass from these,
serious bugs will appear whenever ActionCharacters are in these rooms or
attempt to use these exits. If any character does not subclass from these,
it will at the very least be unable to cross ActionExits, so be sure to
subclass all of the character, room and exit classes in your game from these
if you intend to make use of the action system.
"""

from evennia import DefaultCharacter, DefaultRoom, DefaultExit
from evennia.utils import lazy_property
from evennia.contrib.actions.handlers import (CharacterActionHandler, 
    RoomActionHandler)
from evennia.contrib.actions.commands import ActionExitCommand


class ActionCharacter(DefaultCharacter):
    """
    A character that contains a CharacterActionHandler and sets up most of the
    character's action system properties on creation

    To assign a function that calculates the movement speed of the character,
    as well as a movement type (string) to the character, your class must
    provide the following lines in at_object_creation:

    self.actions.movespeed = <your function here>
    self.actions.movetype = <your string here>

    The movement speed function must have one argument, a reference to the
    character itself. If this function is not set or is set to None, 
    characters will move at a speed of one distance unit per second. 
    If the movement type is not set or is set to None, characters will skip
    checking whether the exits they go through can accommodate their movement
    type.

    To assign a function that sets the bodyparts for the character's movement
    action based on the movement type, your class must provide this line:

    self.actions.bodypart_movement_map = <your function here>

    This function has one argument: the movement type being performed (string). 
    If the function is not set or is set to None, the character will move 
    without using any bodyparts.
    """
    def at_object_creation(self):
        super(ActionCharacter, self).at_object_creation()
        self.actions.setup()

    def at_pre_unpuppet(self):
        super(ActionCharacter, self).at_pre_unpuppet()
        self.actions.unpuppet()

    @lazy_property
    def actions(self):
        """
        CharacterActionHandler that manages the character's actions queue.
        """
        return CharacterActionHandler(self)


class ActionRoom(DefaultRoom):
    """
    A room that contains a RoomActionHandler and sets up most of the room's
    action system properties on creation

    Sometimes, the action system sends messages to the characters. By default,
    these messages refer to these characters using their keys. If you would like
    to have the messages refer to them in a different way based on who is
    looking at them, you must supply a "view" function:

        self.actions.view = <your function here>
    
    This function has two arguments. The first argument is the object being
    viewed and the second argument argument is the character viewing it.
    The function must return a string that will be shown to the viewing 
    character, or return False if the object cannot be viewed. 
    If the function is not set or is set to None, the viewing
    character will always see the viewed character's key.
    """
    def at_object_creation(self):
        super(ActionRoom, self).at_object_creation()
        self.actions.setup()

    @lazy_property
    def actions(self):
        """RoomActionHandler that manages the actions in the room."""
        return RoomActionHandler(self)


class ActionExit(DefaultExit):
    """
    An exit that issues an ActionExitCommand when a character attempts to
    enter it. The ActionExitCommand issues a MoveOut action on behalf of the
    entering character, which causes the character to attempt to enter when
    the action's duration has passed. The duration equals the exit's distance
    value divided by the character's movement speed (if the character has a
    movement speed at all). 
    """
    exit_command = ActionExitCommand
    
    def at_object_creation(self):
        if not self.db.distance:
            self.db.distance = 1.0

