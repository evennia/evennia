"""
OLC fields describe how to edit and display a specific piece of data of a prototype within the OLC system.

The OLC system imports and adds these field classes to its prototype manipulation pages in order to
know what data to read and how to display it.

"""
from collections import deque
# from django.conf import settings

_OLC_VALIDATION_ERROR = """
Error storing data in {fieldname}:
 {value}
The reported error was
 {error}
"""

_LEN_HISTORY = 10     # settings.OLC_HISTORY_LENGTH


class OLCField(object):
    """
    This is the parent for all OLC fields. This docstring acts
    as the help text for the field.

    """
    # name of this field, for error reporting
    key = "Empty field"
    # if this field must have a value different than None
    required = False
    # used for displaying extra info in the OLC
    label = "Empty field"
    # initial value of field if not given
    initial = None
    # actions available on this field. Available actions
    # are replace, edit, append, remove, clear, help
    actions = ['replace', 'edit', 'remove', 'clear', 'help']

    def __init__(self, olcsession):
        self.olcsession = olcsession
        self._value_history = deque([self.initial], _LEN_HISTORY)
        self._history_pos = 0
        self._has_changed = False

    def __repr__(self):
        return self.display()

    # storing data to the field in a history-aware way
    @property
    def value(self):
        return self._value_history[self._history_pos]

    @value.setter
    def value(self, value):
        """
        Update field value by updating the history.
        """
        original_value = value
        try:
            value = self.validate(value)
        except Exception as err:
            errtext = _OLC_VALIDATION_ERROR.format(fieldname=self.key, value=original_value, error=err)
            self.olcsession.caller.msg(errtext)
            return
        if (self._value_history and isinstance(value, (basestring, bool, int, float)) and
                self._value_history[0] == value):
            # don't change/update history if re-adding the same thing
            return
        else:
            self._has_changed = True
            self._history_pos = 0
            self._value_history.appendleft(value)

    @value.deleter
    def value(self):
        self.history_pos = 0
        self._value_history.appendleft(self.initial)

    def history(self, step):
        """
        Change history position.

        Args:
            step (int): Step in the history stack. Positive movement
                means moving futher back in history (with a maximum
                of `settings.OLC_HISTORY_LENGTH`, negative steps
                moves towards recent history (with 0 being the latest
                value).

        """
        self._history_pos = min(len(self.value_history)-1, max(0, self._history_pos + step))

    def has_changed(self):
        """
        Check if this field has changed.

        Returns:
            changed (bool): If the field changed or not.

        """
        return bool(self._has_changed)

    # overloadable methods

    def from_entity(self, entity, **kwargs):
        """
        Populate this field from an entity.

        Args:
            entity (any): An object to use for
                populating this field (like an Object).
        """
        pass

    def to_prototype(self, prototype):
        """
        Store this field value in a prototype.

        Args:
            prototype (dict): The prototype dict
                to update with the value of this field.
        """
        pass

    def validate(self, value, **kwargs):
        """
        Validate/preprocess data to store in this field.

        Args:
            value (any): An input value to
                validate

        Kwargs:
            any (any): Optional info to send to field.

        Returns:
            validated_value (any): The value, correctly
                validated and/or processed to store in this field.

        Raises:
            Exception: If the field was given an
                invalid value to validate.

        """
        return str(value)

    def display(self):
        """
        How to display the field contents in the OLC display.

        """
        return self.value


# OLCFields for all the standard model properties
# key, location, destination, home, aliases,
# permissions, tags, attributes
# ...


class OLCKeyField(OLCField):
    """
    The name (key) of the object is its main identifier, used
    throughout listings even if may not always be visible to
    the end user.
    """
    key = 'Name'
    required = True
    label = "The object's name"

    def from_entity(self, entity, **kwargs):
        self.value = entity.db_key

    def to_prototype(self, prototype):
        prototype['key'] = self.value


class OLCLocationField(OLCField):
    """
    An object's location is usually a Room but could be any
    other in-game entity. By convention, Rooms themselves have
    a None location. Objects are otherwise only placed in a
    None location to take them out of the game.
    """
    key = 'Location'
    required = False
    label = "The object's current location"

    def validate(self, value):
        return self.olcsession.search_by_string(value)

    def from_entity(self, entity, **kwargs):
        self.value = entity.db_location

    def to_prototype(self, prototype):
        prototype['location'] = self.value


class OLCHomeField(OLCField):
    """
    An object's home location acts as a fallback when various
    extreme situations occur. An example is when a location is
    deleted - all its content (except exits) are then not deleted
    but are moved to each object's home location.
    """
    key = 'Home'
    required = True
    label = "The object's home location"

    def validate(self, value):
        return self.olcsession.search_by_string(value)

    def from_entity(self, entity, **kwargs):
        self.value = entity.db_home

    def to_prototype(self, prototype):
        prototype['home'] = self.value

class OLCDestinationField(OLCField):
    """
    An object's destination is usually not set unless the object
    represents an exit between game locations. If set, the
    destination should be set to the location you get to when
    passing through this exit.

    """
    key = 'Destination'
    required = False
    label = "The object's (usually exit's) destination"

    def validate(self, value):
        return self.olcsession.search_by_string(value)

    def from_entity(self, entity, **kwargs):
        self.value = entity.db_destination

    def to_prototype(self, prototype):
        prototype['destination'] = self.value


class OLCAliasField(OLCField):
    """
    Specify as a comma-separated list. Use quotes around the
    alias if the alias itself contains a comma.

    Aliases are alternate names for an object. An alias is just
    as fast to search for as a key and two objects are assumed
    to have the same name is *either* their name or any of their
    aliases match.

    """
    key = 'Aliases'
    required = False
    label = "The object's alternative name or names"
    actions = OLCField.actions + ['append']

    def validate(self, value):
        return split_by_comma(value)

    def from_entity(self, entity, **kwargs):
        self.value = list(entity.db_aliases.all())

    def to_prototype(self, prototype):
        prototype['aliases'] = self.value


class OLCTagField(OLCField):
    """
    Specify as a comma-separated list of tagname or tagname:category.

    Aliases are alternate names for an object. An alias is just
    as fast to search for as a key and two objects are assumed
    to have the same name is *either* their name or any of their
    aliases match.

    """
    key = 'Aliases'
    required = False
    label = "The object's (usually exit's) destination"
    actions = OLCField.actions + ['append']

    def validate(self, value):
        return [tagstr.split(':', 1) if ':' in tagstr else (tagstr, None)
                for tagstr in split_by_comma(value)]

    def from_entity(self, entity, **kwargs):
        self.value = entity.tags.all(return_key_and_category=True)

    def to_prototype(self, prototype):
        prototype['tags'] = self.value

