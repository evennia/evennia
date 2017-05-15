"""
OLC fields describe how to edit and display a specific piece of data of a prototype within the OLC system.

The OLC system imports and adds these field classes to its prototype manipulation pages in order to
know what data to read and how to display it.

"""
from collections import deque
from evennia.utils.utils import to_str, to_unicode
from evennia.utils.olc import olc_utils

# from django.conf import settings

_OLC_VALIDATION_ERROR = """
Error storing data in {fieldname}:
 {value}
The reported error was
 {error}
"""

_LEN_HISTORY = 10     # settings.OLC_HISTORY_LENGTH


class InvalidActionError(RuntimeError):
    """
    Raised when trying to perform a field action the field
    does not support.
    """
    pass


class ValidationError(RuntimeError):
    """
    Raised when failing to validate new data being entered
    into the field (from any source)
    """
    pass


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
    default = None
    # actions available on this field. Available actions
    # are replace, edit, append, remove, clear, help
    actions = ['replace', 'edit', 'clear', 'help']

    def __init__(self, olcsession):
        self.olcsession = olcsession
        self._value_history = deque([self.initial], _LEN_HISTORY)
        self._history_pos = 0
        self._has_changed = False

    def __repr__(self):
        return to_str(self.display())

    def __unicode__(self):
        return to_unicode(self.display())

    # perform actions
    # TODO - include editor in check!
    def action_replace(self, newval):
        """
        Replace field value.

        Args:
            newval (any): New value to replace existing one.

        Raises:
            InvalidActionError: If replacing is not allowed.

        """
        if 'replace' in self.actions:
            self.value = newval
        else:
            raise InvalidActionError('Replace {value}->{newval}'.format(value=self.value, newval))

    def action_edit(self):
        """
        Check if we may edit.

        Returns:
            can_edit (bool): If we can edit or not.

        """
        if 'edit' in self.actions:
            return self.value
        return False

    def action_clear(self):
        """
        Clear field back to default.

        Returns:
            default (any): The field'd default value, now set.

        Raises:
            InvalidActionError: If clearing is not allowed.

        """
        if 'clear' in self.actions:
            # don't validate this
            object.__setattr__(self, 'value', self.default)
            return self.value
        else:
            raise InvalidActionError('Clear')

    def action_help(self):
        """
        Get the help text for the field.

        Returns:
            help (str): Field help text.

        Raises:
            InvalidActionError: If help is not given for this field,
                either becuase it's disallowed or unset.

        """
        if 'help' not in self.actions or not self.__doc__:
            raise InvalidActioNError('Help')
        return self.__doc__

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
            raise ValidationError(errtxt)
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
        Populate this field by retrieving data from an entity.
        All fields on a page will have this called, so must
        be able to handle also incompatible entities.

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
        Validate/preprocess incoming data to store in this field.

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
        return olc_utils.search_by_string(self.olcsession, value)

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
        return olc_utils.search_by_string(self.olcsession, value)

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
        return olc_utils.search_by_string(self.olcsession, value)

    def from_entity(self, entity, **kwargs):
        self.value = entity.db_destination

    def to_prototype(self, prototype):
        prototype['destination'] = self.value


class OLCBatchField(OLCField):
    """
    A field managing multiple values that can be appended to and
    a given component popped out.
    """
    actions = OLCField.actions + ['append', 'pop']

    def action_append(self, value):
        """
        Append a new value to this field.

        Args:
            value (any): The value to append.

        """
        value = self.value
        value.append(value)
        self.value = value

    def action_pop(self, index=-1):
        """
        Pop an element from the field.

        Args:
            index (int, optional): Pop this index, otherwise pop the last
                element in the field.

        Returns:
            element (any or None): The popped element or None.

        """
        lst = self.value
        try:
            return lst.pop(int(index))
        except IndexError:
            return None


# setting single Alias
class OLCAliasField(OLCField):
    key = "Alias"
    required = False
    label = "An alternative name for the object"

    def from_entity(self, entity, **kwargs):
        if "index" in kwargs:
            self.value = entity.aliases.all()[int(kwargs)]

    def to_prototype(self, prototype):
        if is_iter(prototype["aliases"]):
            prototype["aliases"].append(self.value)
        else:
            prototype["aliases"] = [self.value]


# batch-setting aliases
class OLCAliasBatchField(OLCBatchField):
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

    def validate(self, value):
        return olc_utils.split_by_comma(value)

    def from_entity(self, entity, **kwargs):
        self.value = list(entity.aliases.all())

    def to_prototype(self, prototype):
        prototype['aliases'] = self.value


# setting single Tag
class OLCTagField(OLCField):
    """
    Specify as tagname or tagname:category

    Tags are used to identify groups of objects for later quick retrieval.
    This is very useful for anything from creating zones of rooms to
    easily find all Characters belonging a given group etc. A tag can also
    have a category for a second level of grouping.

    """
    key = "Tag"
    required = False
    label = "A single label for the object."

    def validate(self, value):

    def from_entity(self, entity, **kwargs):
        if "index" in kwargs:
            self.value = entity.tags.all()[int(kwargs)]

    def to_prototype(self, prototype):
        if is_iter(prototype["tags"]): prototype["tags"].append(self.value)
        else:
            prototype["tags"] = [self.value]


# batch-setting Tags
class OLCTagBatchField(OLCBatchField):
    """
    Specify as a comma-separated list of tagname or tagname:category.

    Tags are used to identify groups of objects for later quick retrieval.
    This is very useful for anything from creating zones of rooms to
    easily find all Characters belonging a given group etc.

    """
    key = 'Tags'
    required = False
    label = "Attach labels to objects to group and find them."

    def validate(self, value):
        if isinstance(value, basestring):
            return [tuple(tagstr.split(':', 1)) if ':' in tagstr else (tagstr, None)
                    for tagstr in olc_utils.split_by_comma(value)]
        else:
            # assume a list of (key, category) - just let it pass
            return value

    def from_entity(self, entity, **kwargs):
        self.value = entity.tags.all(return_key_and_category=True)

    def to_prototype(self, prototype):
        prototype['tags'] = self.value

    def display(self):
        outstr = []
        for key, category in self.value:
            outstr.append("{key}:{category}".format(key=key, category=category))
        return '\n'.join(outstr)


# setting single Attribute
class OLCAttributeField(OLCField):
    key = "Attribute"
    required = False
    label = "An alternative name for the object"

    def from_entity(self, entity, **kwargs):
        if "index" in kwargs:
            self.value = entity.attributes.all()[int(kwargs)]

    def to_prototype(self, prototype):
        if is_iter(prototype["attrs"]):
            prototype["attrs"].append(self.value)
        else:
            prototype["attrs"] = [self.value]


# batch-setting attributes
class OLCAttributeBatchField(OLCBatchField):
    """
    Specify as a comma-separated list of attrname=value or attrname:category=value.

    Attributes are arbitrary pieces of data attached to an object. They can
    contain references to other objects as well as simple Python structures such
    as lists and dicts.

    """
    key = 'Attributes'
    required = False
    label = "Additional data attached to this object."
    actions = OLCField.actions + ['append']

    def validate(self, value):
        if isinstance(value, basestring):
            return [tuple(lhs.split(':', 1) + [rhs]) if ':' in lhs else (lhs, None) + (rhs, )
                    for lhs, rhs in (attrstr.split('=', 1) if ':' in attrstr else ((attrstr, None),))
                    for attrstr in olc_utils.split_by_comma(value)]
        else:
            # we assume this is a list of Attributes
            return [(attr.key, attr.category, attr.value) for attr in value]

    def from_entity(self, entity, **kwargs):
        self.value = entity.attributes.all()

    def to_prototype(self, prototype):
        for key, category, value in self.value:
            prototype['attrs'] = (key, value, category)

    def display(self):
        outstr = []
        for key, category, value in self.value:
            outstr.append("{key}:{category} = {value}".format(key=key, category=category, value=value))
        return '\n'.join(outstr)


